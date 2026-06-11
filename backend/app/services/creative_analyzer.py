"""
Creative Analyzer — Man Matters Creative OS

Uses Gemini 2.5 Pro to extract structured metadata from creative assets.
Handles images, videos (via frames), and text content.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import google.generativeai as genai
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


# Initialize Gemini
genai.configure(api_key=settings.GOOGLE_API_KEY)

GEMINI_MODEL = settings.GEMINI_MODEL

ANALYSIS_PROMPT = """You are a senior performance marketing strategist analyzing a Meta ad creative for Man Matters, an Indian D2C men's grooming and wellness brand.

Man Matters product categories: hair (Biotin Gummies, Stage 1/2/3 Serum, Advance Regime), wellness (Magnesium Gummies, Shilajit Gummies), fitness (Creatine Powder, Creatine Electrolyte).

Analyze this creative and extract ALL of the following attributes. Return ONLY valid JSON — no markdown, no explanations.

{
  "narrative_type": <one of: myth_busting, expert_recommendation, doctor_recommendation, product_demo, before_after, ugc, testimonial, educational, comparison, problem_solution, founder_story, transformation_story, authority_based, social_proof, lifestyle, humour, challenge, news_jacking, seasonal, other>,
  "story_structure": <e.g., linear, problem_solution, before_after, hero_journey, listicle>,
  "marketing_angle": <e.g., ingredient_efficacy, speed_of_results, clinical_proof, value_for_money, convenience, lifestyle_upgrade, social_proof, fear_of_loss>,
  "stage_of_funnel": <one of: awareness, consideration, conversion, retention>,
  "content_category": <e.g., hair_loss, hair_growth, energy, performance, recovery, sleep, stress>,
  "hook_type": <one of: authority, problem, curiosity, social_proof, question, statistic, shock, transformation, urgency, relatability, myth_bust, challenge, announcement, comparison>,
  "hook_text": "<first 5-10 words or opening visual hook>",
  "hook_duration_seconds": <float, 0 if static>,
  "visual_style": <one of: talking_head, product_demo, lifestyle, animation, screen_recording, text_only, split_screen, voiceover_broll, interview, documentary, meme>,
  "production_quality": <one of: professional, semi_professional, ugc>,
  "creator_type": <one of: doctor, customer, founder, actor, influencer, expert, celebrity, animated, none>,
  "ugc_type": <one of: selfie, scripted, candid, talking_head, null if not UGC>,
  "human_presence": <true/false>,
  "offer_type": <one of: none, discount, bundle, free_shipping, trial, buy_one_get_one, gift_with_purchase, subscription>,
  "discount_percentage": <number or null>,
  "price_mentioned": <true/false>,
  "cta_text": "<visible CTA text if any>",
  "emotional_trigger": <one of: fear, aspiration, trust, curiosity, urgency, pride, guilt, excitement, nostalgia, social_approval>,
  "pain_point": "<specific pain point addressed>",
  "benefit_claimed": "<primary benefit or transformation promised>",
  "objection_handled": "<any objection addressed, or null>",
  "trust_signal": <one of: doctor, customer_review, award, ingredient_proof, clinical_study, before_after, celebrity_endorsement, null>,
  "authority_figure": "<name or type of authority figure, or null>",
  "product_visibility": <one of: high, medium, low, none>,
  "brand_visibility": <one of: high, medium, low>,
  "color_theme": "<dominant color palette, e.g., dark_professional, bright_energetic, natural_organic>",
  "has_captions": <true/false>,
  "has_music": <true/false>,
  "audience_intent": <one of: browse, research, purchase>,
  "target_pain_keywords": ["<keyword1>", "<keyword2>"],
  "analysis_confidence": <float 0-1, how confident you are in this analysis>,
  "analysis_notes": "<any important observations about this creative>"
}

Additional context:
- Ad headline: {headline}
- Ad body text: {body_text}
- CTA button: {cta_type}

Be precise. If something is unclear, make your best assessment and lower the confidence score."""


COMPETITOR_ANALYSIS_PROMPT = """Analyze this competitor Meta ad from an Indian men's grooming/wellness/fitness brand.

Extract the same attributes as Man Matters creatives to enable direct comparison.

Return ONLY valid JSON:
{
  "narrative_type": <narrative>,
  "hook_type": <hook>,
  "hook_text": "<opening>",
  "visual_style": <style>,
  "production_quality": <quality>,
  "creator_type": <type>,
  "human_presence": <bool>,
  "offer_type": <offer>,
  "discount_percentage": <number or null>,
  "price_mentioned": <bool>,
  "emotional_trigger": <trigger>,
  "pain_point": "<pain>",
  "benefit_claimed": "<benefit>",
  "trust_signal": <signal or null>,
  "stage_of_funnel": <stage>,
  "story_structure": "<structure>",
  "has_captions": <bool>,
  "has_music": <bool>,
  "analysis_confidence": <float 0-1>,
  "key_differentiator": "<what makes this ad unique or effective>"
}

Headline: {headline}
Body: {body_text}"""


async def _download_media(url: str) -> Tuple[bytes, str]:
    """Download media from URL and return (bytes, mime_type)."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "image/jpeg").split(";")[0]
        return response.content, content_type


def _build_prompt(headline: str, body_text: str, cta_type: str) -> str:
    return ANALYSIS_PROMPT.format(
        headline=headline or "N/A",
        body_text=body_text or "N/A",
        cta_type=cta_type or "N/A",
    )


def _parse_gemini_json(text: str) -> Dict[str, Any]:
    """Extract JSON from Gemini response, handling markdown code blocks."""
    # Remove markdown code fences if present
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = re.sub(r"```\s*$", "", text).strip()
    return json.loads(text)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def analyze_creative(
    media_url: Optional[str],
    media_type: str,  # "image" or "video"
    headline: str = "",
    body_text: str = "",
    cta_type: str = "",
    storage_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze a creative using Gemini 2.5 Pro.

    Downloads the media, sends to Gemini with structured prompt,
    returns parsed metadata dict.
    """
    model = genai.GenerativeModel(GEMINI_MODEL)
    prompt = _build_prompt(headline, body_text, cta_type)

    # Use storage_url as fallback if media_url fails
    url = storage_url or media_url

    if url and media_type == "image":
        try:
            media_bytes, mime_type = await _download_media(url)
            if len(media_bytes) > 10 * 1024 * 1024:  # 10MB limit
                media_bytes = media_bytes[:10 * 1024 * 1024]

            image_part = {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": base64.b64encode(media_bytes).decode("utf-8"),
                }
            }
            response = model.generate_content([image_part, prompt])
        except Exception as e:
            # Fall back to text-only analysis
            response = model.generate_content(
                f"Analyze this ad creative (image unavailable due to: {e}).\n\n{prompt}"
            )
    elif url and media_type == "video":
        # For videos, use the File API or extract thumbnail
        try:
            # Try to upload via Files API for video analysis
            import tempfile
            import aiofiles

            media_bytes, mime_type = await _download_media(url)
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                tmp.write(media_bytes)
                tmp_path = tmp.name

            video_file = genai.upload_file(tmp_path, mime_type="video/mp4")

            # Wait for processing
            import time
            for _ in range(10):
                if video_file.state.name == "ACTIVE":
                    break
                time.sleep(2)
                video_file = genai.get_file(video_file.name)

            response = model.generate_content([video_file, prompt])
        except Exception:
            # Fall back to text-only
            response = model.generate_content(
                f"Analyze this video ad creative (video analysis unavailable).\n\n{prompt}"
            )
    else:
        # Text-only analysis (for when media URL is unavailable)
        response = model.generate_content(
            f"Analyze this ad creative based on its copy.\n\n{prompt}"
        )

    raw_text = response.text
    result = _parse_gemini_json(raw_text)
    result["gemini_model_version"] = GEMINI_MODEL
    result["raw_response_length"] = len(raw_text)

    return result


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def analyze_competitor_creative(
    media_url: Optional[str],
    media_type: str,
    headline: str = "",
    body_text: str = "",
) -> Dict[str, Any]:
    """Analyze a competitor creative."""
    model = genai.GenerativeModel(GEMINI_MODEL)
    prompt = COMPETITOR_ANALYSIS_PROMPT.format(
        headline=headline or "N/A",
        body_text=body_text or "N/A",
    )

    if media_url and media_type == "image":
        try:
            media_bytes, mime_type = await _download_media(media_url)
            image_part = {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": base64.b64encode(media_bytes).decode("utf-8"),
                }
            }
            response = model.generate_content([image_part, prompt])
        except Exception:
            response = model.generate_content(prompt)
    else:
        response = model.generate_content(prompt)

    result = _parse_gemini_json(response.text)
    result["gemini_model_version"] = GEMINI_MODEL
    return result


def build_embedding_text(metadata: Dict[str, Any], headline: str = "", body_text: str = "") -> str:
    """
    Construct a rich text description of the creative for embedding generation.
    This text captures all semantic dimensions for similarity search.
    """
    parts = []

    if metadata.get("narrative_type"):
        parts.append(f"Narrative: {metadata['narrative_type'].replace('_', ' ').title()}")

    if metadata.get("hook_type"):
        parts.append(f"Hook type: {metadata['hook_type'].replace('_', ' ').title()}")

    if metadata.get("hook_text"):
        parts.append(f"Hook: {metadata['hook_text']}")

    if metadata.get("visual_style"):
        parts.append(f"Visual style: {metadata['visual_style'].replace('_', ' ').title()}")

    if metadata.get("creator_type"):
        parts.append(f"Creator: {metadata['creator_type'].replace('_', ' ').title()}")

    if metadata.get("offer_type") and metadata["offer_type"] != "none":
        parts.append(f"Offer: {metadata['offer_type'].replace('_', ' ').title()}")

    if metadata.get("emotional_trigger"):
        parts.append(f"Emotional trigger: {metadata['emotional_trigger'].replace('_', ' ').title()}")

    if metadata.get("pain_point"):
        parts.append(f"Pain point: {metadata['pain_point']}")

    if metadata.get("benefit_claimed"):
        parts.append(f"Benefit: {metadata['benefit_claimed']}")

    if metadata.get("trust_signal"):
        parts.append(f"Trust signal: {metadata['trust_signal'].replace('_', ' ').title()}")

    if metadata.get("stage_of_funnel"):
        parts.append(f"Funnel stage: {metadata['stage_of_funnel'].replace('_', ' ').title()}")

    if metadata.get("production_quality"):
        parts.append(f"Production quality: {metadata['production_quality'].replace('_', ' ').title()}")

    if headline:
        parts.append(f"Headline: {headline}")

    if body_text:
        # Truncate to avoid token limits
        parts.append(f"Body: {body_text[:300]}")

    return ". ".join(parts)
