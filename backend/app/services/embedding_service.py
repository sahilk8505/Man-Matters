"""
Embedding Service — Man Matters Creative OS

Generates 768-dim embeddings using Google text-embedding-004.
Stores in pgvector. Enables similarity search for:
- Finding winner/loser comps for new creatives
- Discovering similar narratives and hooks
- Competitor pattern matching
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import uuid

import google.generativeai as genai
import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.models.orm import (
    Creative, CreativeEmbedding, CompetitorCreative, CompetitorEmbedding,
    CreativeDailyMetrics, ProductBenchmark
)
from app.services.creative_analyzer import build_embedding_text


genai.configure(api_key=settings.GOOGLE_API_KEY)

EMBEDDING_MODEL = settings.EMBEDDING_MODEL
EMBEDDING_DIMENSION = settings.EMBEDDING_DIMENSION


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def _embed_text(text: str) -> List[float]:
    """Generate embedding for a text string using Google text-embedding-004."""
    if not text.strip():
        return [0.0] * EMBEDDING_DIMENSION

    result = genai.embed_content(
        model=f"models/{EMBEDDING_MODEL}",
        content=text,
        task_type="RETRIEVAL_DOCUMENT",
    )
    return result["embedding"]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def _embed_query(text: str) -> List[float]:
    """Generate query embedding (different task_type for ANN retrieval)."""
    if not text.strip():
        return [0.0] * EMBEDDING_DIMENSION

    result = genai.embed_content(
        model=f"models/{EMBEDDING_MODEL}",
        content=text,
        task_type="RETRIEVAL_QUERY",
    )
    return result["embedding"]


def _build_component_texts(metadata: Dict, headline: str = "", body_text: str = "") -> Dict[str, str]:
    """Build separate text descriptions for each embedding component."""

    narrative_text = " ".join(filter(None, [
        f"Narrative type: {metadata.get('narrative_type', '').replace('_', ' ')}",
        f"Story structure: {metadata.get('story_structure', '')}",
        f"Marketing angle: {metadata.get('marketing_angle', '')}",
        f"Emotional trigger: {metadata.get('emotional_trigger', '')}",
        f"Pain point: {metadata.get('pain_point', '')}",
        f"Benefit: {metadata.get('benefit_claimed', '')}",
        f"Audience intent: {metadata.get('audience_intent', '')}",
    ]))

    hook_text = " ".join(filter(None, [
        f"Hook type: {metadata.get('hook_type', '').replace('_', ' ')}",
        f"Hook opening: {metadata.get('hook_text', '')}",
        f"Opening duration: {metadata.get('hook_duration_seconds', '')} seconds",
    ]))

    visual_text = " ".join(filter(None, [
        f"Visual style: {metadata.get('visual_style', '').replace('_', ' ')}",
        f"Production quality: {metadata.get('production_quality', '')}",
        f"Creator type: {metadata.get('creator_type', '')}",
        f"Human presence: {'yes' if metadata.get('human_presence') else 'no'}",
        f"Color theme: {metadata.get('color_theme', '')}",
        f"Trust signal: {metadata.get('trust_signal', '')}",
    ]))

    offer_text = " ".join(filter(None, [
        f"Offer type: {metadata.get('offer_type', 'none').replace('_', ' ')}",
        f"Discount: {metadata.get('discount_percentage', 'none')}%",
        f"Price mentioned: {'yes' if metadata.get('price_mentioned') else 'no'}",
        f"CTA: {metadata.get('cta_text', '')}",
    ]))

    return {
        "narrative": narrative_text,
        "hook": hook_text,
        "visual": visual_text,
        "offer": offer_text,
    }


async def generate_and_store_embedding(
    db: AsyncSession,
    creative_id: uuid.UUID,
    metadata: Dict,
    headline: str = "",
    body_text: str = "",
) -> CreativeEmbedding:
    """
    Generate all embeddings for a creative and upsert into creative_embeddings.
    """
    # Build texts
    full_text = build_embedding_text(metadata, headline, body_text)
    components = _build_component_texts(metadata, headline, body_text)

    # Generate embeddings
    full_emb = _embed_text(full_text)
    narrative_emb = _embed_text(components["narrative"])
    hook_emb = _embed_text(components["hook"])
    visual_emb = _embed_text(components["visual"])
    offer_emb = _embed_text(components["offer"])

    # Upsert
    existing = await db.scalar(
        select(CreativeEmbedding).where(CreativeEmbedding.creative_id == creative_id)
    )

    if existing:
        existing.embedding = full_emb
        existing.narrative_embedding = narrative_emb
        existing.hook_embedding = hook_emb
        existing.visual_embedding = visual_emb
        existing.offer_embedding = offer_emb
        existing.input_text = full_text[:2000]
        existing.model_version = EMBEDDING_MODEL
        db.add(existing)
        await db.flush()
        return existing

    new_emb = CreativeEmbedding(
        creative_id=creative_id,
        embedding=full_emb,
        narrative_embedding=narrative_emb,
        hook_embedding=hook_emb,
        visual_embedding=visual_emb,
        offer_embedding=offer_emb,
        input_text=full_text[:2000],
        model_version=EMBEDDING_MODEL,
    )
    db.add(new_emb)
    await db.flush()
    return new_emb


async def find_similar_creatives(
    db: AsyncSession,
    query_embedding: List[float],
    product_id: Optional[uuid.UUID] = None,
    limit: int = 10,
    exclude_id: Optional[uuid.UUID] = None,
) -> List[Dict]:
    """
    Find most similar creatives using pgvector cosine similarity.
    Returns list with creative details + similarity score.
    """
    product_filter = f"AND c.product_id = '{product_id}'" if product_id else ""
    exclude_filter = f"AND c.id != '{exclude_id}'" if exclude_id else ""

    # Convert embedding to PostgreSQL vector literal
    emb_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    query = text(f"""
        SELECT
            c.id::text AS creative_id,
            c.name,
            c.product_id::text,
            c.launch_date,
            c.status,
            cm.narrative_type,
            cm.hook_type,
            cm.creator_type,
            cm.visual_style,
            1 - (ce.embedding <=> '{emb_str}'::vector) AS similarity,
            COALESCE(
                (SELECT AVG(m.roas)
                 FROM creative_daily_metrics m
                 WHERE m.creative_id = c.id
                   AND m.roas > 0
                   AND m.spend >= :min_spend),
                0
            ) AS avg_roas,
            COALESCE(
                (SELECT SUM(m.spend)
                 FROM creative_daily_metrics m
                 WHERE m.creative_id = c.id),
                0
            ) AS total_spend
        FROM creative_embeddings ce
        JOIN creatives c ON c.id = ce.creative_id
        LEFT JOIN creative_metadata cm ON cm.creative_id = c.id
        WHERE c.status != 'deleted'
        {product_filter}
        {exclude_filter}
        ORDER BY ce.embedding <=> '{emb_str}'::vector
        LIMIT :limit
    """)

    rows = await db.execute(query, {"min_spend": settings.MIN_SPEND_FOR_CLASSIFICATION, "limit": limit})
    results = []
    for row in rows:
        d = dict(row._mapping)
        d["is_winner"] = d["avg_roas"] > 3.0  # simplified threshold; use benchmarks in practice
        results.append(d)

    return results


async def find_similar_competitors(
    db: AsyncSession,
    query_embedding: List[float],
    limit: int = 10,
) -> List[Dict]:
    """Find most similar competitor creatives."""
    emb_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    query = text(f"""
        SELECT
            cc.id::text AS competitor_creative_id,
            cc.competitor_name,
            cc.headline,
            cc.first_seen_date,
            cc.last_seen_date,
            cc.estimated_lifespan_days,
            cc.narrative_type,
            cc.hook_type,
            cc.visual_style,
            cc.offer_type,
            cc.creator_type,
            cc.is_active,
            1 - (ce.embedding <=> '{emb_str}'::vector) AS similarity
        FROM competitor_embeddings ce
        JOIN competitor_creatives cc ON cc.id = ce.competitor_creative_id
        ORDER BY ce.embedding <=> '{emb_str}'::vector
        LIMIT :limit
    """)

    rows = await db.execute(query, {"limit": limit})
    return [dict(row._mapping) for row in rows]


async def classify_winner_loser(
    db: AsyncSession,
    creative_id: uuid.UUID,
    product_id: uuid.UUID,
) -> Tuple[bool, bool, float]:
    """
    Classify a creative as winner, loser, or neither.
    Uses product benchmarks for thresholds.
    Returns (is_winner, is_loser, avg_roas).
    """
    # Get product benchmarks
    benchmarks = await db.scalar(
        select(ProductBenchmark)
        .where(ProductBenchmark.product_id == product_id)
        .where(ProductBenchmark.period_days == 30)
    )

    # Get creative's average ROAS (from meaningful spend days)
    result = await db.execute(
        select(
            CreativeDailyMetrics.roas,
            CreativeDailyMetrics.spend,
        )
        .where(CreativeDailyMetrics.creative_id == creative_id)
        .where(CreativeDailyMetrics.roas > 0)
        .where(CreativeDailyMetrics.spend >= 100)
    )
    rows = result.all()

    if not rows:
        return False, False, 0.0

    total_spend = sum(r.spend for r in rows)
    if total_spend < settings.MIN_SPEND_FOR_CLASSIFICATION:
        return False, False, 0.0

    # Weighted average ROAS by spend
    avg_roas = sum(r.roas * r.spend for r in rows) / total_spend

    winner_threshold = (benchmarks.winner_roas_threshold if benchmarks else 3.0) or 3.0
    loser_threshold = (benchmarks.loser_roas_threshold if benchmarks else 1.5) or 1.5

    is_winner = avg_roas >= winner_threshold
    is_loser = avg_roas <= loser_threshold

    return is_winner, is_loser, avg_roas


async def generate_competitor_embedding(
    db: AsyncSession,
    competitor_id: uuid.UUID,
    metadata: Dict,
    headline: str = "",
    body_text: str = "",
) -> CompetitorEmbedding:
    """Generate and store embedding for a competitor creative."""
    full_text = build_embedding_text(metadata, headline, body_text)
    embedding = _embed_text(full_text)

    existing = await db.scalar(
        select(CompetitorEmbedding)
        .where(CompetitorEmbedding.competitor_creative_id == competitor_id)
    )

    if existing:
        existing.embedding = embedding
        existing.model_version = EMBEDDING_MODEL
        db.add(existing)
        await db.flush()
        return existing

    new_emb = CompetitorEmbedding(
        competitor_creative_id=competitor_id,
        embedding=embedding,
        model_version=EMBEDDING_MODEL,
    )
    db.add(new_emb)
    await db.flush()
    return new_emb
