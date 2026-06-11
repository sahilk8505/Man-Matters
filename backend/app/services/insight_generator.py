"""
AI Insight Generator — Man Matters Creative OS

Uses Gemini to synthesize performance data into actionable insights.
Runs daily to surface opportunities, fatigue alerts, and strategic recommendations.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional
import uuid

import google.generativeai as genai
from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.models.orm import (
    Product, Creative, CreativeMetadata, CreativeDailyMetrics,
    FatigueScore, NarrativePerformance, Narrative, Insight
)


logger = logging.getLogger(__name__)
genai.configure(api_key=settings.GOOGLE_API_KEY)


INSIGHT_GENERATION_PROMPT = """You are a senior performance marketing strategist for Man Matters, an Indian D2C men's grooming brand spending ₹10Cr+ monthly on Meta Ads.

Analyze the following performance data and generate 3-5 actionable insights. Focus on what will move the needle — not observations, but decisions.

Product: {product_name}
Period: Last 30 days

Performance Summary:
{performance_summary}

Narrative Performance:
{narrative_data}

Fatigue Status:
{fatigue_data}

Creative Gaps:
{gap_data}

For each insight, respond in this JSON format (array of insights):
[
  {{
    "insight_type": <one of: fatigue_alert, opportunity, narrative_learning, performance_anomaly, saturation_warning, budget_recommendation, creative_gap, winner_pattern, loser_pattern>,
    "priority": <critical, high, medium, low>,
    "title": "<20-40 word title that states the finding and implication>",
    "body": "<2-3 sentence explanation with specific numbers>",
    "recommended_action": "<specific, actionable next step>",
    "action_type": <create_creative, pause_creative, reallocate_budget, test_narrative, scale_winner, refresh_creative, monitor>
  }}
]

Rules:
- Cite specific numbers (CTR%, ROAS, CPA in ₹, lifespan days)
- Each insight must lead to a clear action
- Prioritize insights by revenue impact
- Flag creatives actively losing money
- Surface the single highest-opportunity gap
- Return ONLY valid JSON, no markdown"""


async def _get_product_performance_summary(
    db: AsyncSession,
    product_id: uuid.UUID,
    days: int = 30,
) -> Dict[str, Any]:
    """Aggregate product-level performance metrics."""
    cutoff = date.today() - timedelta(days=days)

    result = await db.execute(
        select(
            func.count(func.distinct(CreativeDailyMetrics.creative_id)).label("active_creatives"),
            func.sum(CreativeDailyMetrics.spend).label("total_spend"),
            func.sum(CreativeDailyMetrics.purchases).label("total_purchases"),
            func.sum(CreativeDailyMetrics.purchase_value).label("total_revenue"),
            func.avg(CreativeDailyMetrics.roas).label("avg_roas"),
            func.avg(CreativeDailyMetrics.ctr).label("avg_ctr"),
            func.avg(CreativeDailyMetrics.cpa).label("avg_cpa"),
            func.avg(CreativeDailyMetrics.hook_rate).label("avg_hook_rate"),
        )
        .where(CreativeDailyMetrics.product_id == product_id)
        .where(CreativeDailyMetrics.date >= cutoff)
        .where(CreativeDailyMetrics.attribution_window == "7d_click")
        .where(CreativeDailyMetrics.spend > 0)
    )
    row = result.one()
    return {
        "active_creatives": row.active_creatives or 0,
        "total_spend_inr": float(row.total_spend or 0),
        "total_purchases": int(row.total_purchases or 0),
        "total_revenue_inr": float(row.total_revenue or 0),
        "avg_roas": round(float(row.avg_roas or 0), 2),
        "avg_ctr_pct": round(float(row.avg_ctr or 0) * 100, 3),
        "avg_cpa_inr": round(float(row.avg_cpa or 0), 0),
        "avg_hook_rate_pct": round(float(row.avg_hook_rate or 0) * 100, 2),
    }


async def _get_narrative_breakdown(
    db: AsyncSession,
    product_id: uuid.UUID,
    days: int = 30,
) -> List[Dict]:
    """Get performance broken down by narrative type."""
    cutoff = date.today() - timedelta(days=days)

    result = await db.execute(
        select(
            CreativeMetadata.narrative_type,
            func.count(func.distinct(CreativeDailyMetrics.creative_id)).label("creative_count"),
            func.sum(CreativeDailyMetrics.spend).label("spend"),
            func.sum(CreativeDailyMetrics.purchases).label("purchases"),
            func.avg(CreativeDailyMetrics.roas).label("avg_roas"),
            func.avg(CreativeDailyMetrics.ctr).label("avg_ctr"),
            func.avg(CreativeDailyMetrics.cpa).label("avg_cpa"),
        )
        .join(Creative, Creative.id == CreativeDailyMetrics.creative_id)
        .join(CreativeMetadata, CreativeMetadata.creative_id == Creative.id)
        .where(CreativeDailyMetrics.product_id == product_id)
        .where(CreativeDailyMetrics.date >= cutoff)
        .where(CreativeDailyMetrics.attribution_window == "7d_click")
        .where(CreativeDailyMetrics.spend >= 100)
        .where(CreativeMetadata.narrative_type.isnot(None))
        .group_by(CreativeMetadata.narrative_type)
        .order_by(func.sum(CreativeDailyMetrics.purchases).desc())
    )

    rows = result.all()
    total_spend = sum(float(r.spend or 0) for r in rows)
    total_purchases = sum(int(r.purchases or 0) for r in rows)

    return [
        {
            "narrative": r.narrative_type.replace("_", " ").title() if r.narrative_type else "Unknown",
            "creative_count": r.creative_count,
            "spend_inr": round(float(r.spend or 0), 0),
            "spend_pct": round(float(r.spend or 0) / total_spend * 100, 1) if total_spend else 0,
            "purchases": int(r.purchases or 0),
            "purchase_pct": round(int(r.purchases or 0) / total_purchases * 100, 1) if total_purchases else 0,
            "avg_roas": round(float(r.avg_roas or 0), 2),
            "avg_ctr_pct": round(float(r.avg_ctr or 0) * 100, 3),
            "avg_cpa_inr": round(float(r.avg_cpa or 0), 0),
        }
        for r in rows
    ]


async def _get_fatigue_summary(
    db: AsyncSession,
    product_id: uuid.UUID,
) -> Dict[str, Any]:
    """Summarize current fatigue status for the product."""
    today = date.today()

    result = await db.execute(
        select(
            FatigueScore.fatigue_stage,
            func.count(FatigueScore.creative_id).label("count"),
        )
        .join(Creative, Creative.id == FatigueScore.creative_id)
        .where(FatigueScore.product_id == product_id)
        .where(FatigueScore.calculated_date == today)
        .where(Creative.status == "active")
        .group_by(FatigueScore.fatigue_stage)
    )

    stage_counts = {r.fatigue_stage: r.count for r in result}

    # Get top fatiguing creatives
    fatiguing = await db.execute(
        select(
            Creative.name,
            FatigueScore.fatigue_score,
            FatigueScore.expected_remaining_days,
            FatigueScore.fatigue_stage,
        )
        .join(Creative, Creative.id == FatigueScore.creative_id)
        .where(FatigueScore.product_id == product_id)
        .where(FatigueScore.calculated_date == today)
        .where(FatigueScore.fatigue_stage.in_(["fatiguing", "fatigued"]))
        .where(Creative.status == "active")
        .order_by(FatigueScore.fatigue_score.desc())
        .limit(5)
    )

    return {
        "healthy": stage_counts.get("healthy", 0),
        "watch": stage_counts.get("watch", 0),
        "fatiguing": stage_counts.get("fatiguing", 0),
        "fatigued": stage_counts.get("fatigued", 0),
        "top_fatiguing": [
            {
                "name": r.name,
                "fatigue_score": float(r.fatigue_score),
                "stage": r.fatigue_stage,
                "remaining_days": r.expected_remaining_days,
            }
            for r in fatiguing
        ],
    }


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=2, min=3, max=20))
async def generate_product_insights(
    db: AsyncSession,
    product: Product,
) -> List[Dict]:
    """
    Generate AI insights for a specific product.
    Returns list of insight dicts ready for database insertion.
    """
    # Gather data
    perf_summary = await _get_product_performance_summary(db, product.id)
    narrative_breakdown = await _get_narrative_breakdown(db, product.id)
    fatigue_summary = await _get_fatigue_summary(db, product.id)

    # Build gap data (high-performing narratives with low volume)
    gap_data = [
        n for n in narrative_breakdown
        if n["avg_roas"] > (perf_summary.get("avg_roas", 2.0) * 1.2)  # 20% above average
        and n["spend_pct"] < 10  # But less than 10% of spend
    ]

    prompt = INSIGHT_GENERATION_PROMPT.format(
        product_name=product.name,
        performance_summary=json.dumps(perf_summary, indent=2),
        narrative_data=json.dumps(narrative_breakdown[:10], indent=2),
        fatigue_data=json.dumps(fatigue_summary, indent=2),
        gap_data=json.dumps(gap_data[:5], indent=2),
    )

    model = genai.GenerativeModel(settings.GEMINI_MODEL)
    response = model.generate_content(prompt)

    # Parse response
    import re
    text = response.text
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = re.sub(r"```\s*$", "", text).strip()
    raw_insights = json.loads(text)

    # Format for database
    result = []
    for ins in raw_insights[:5]:  # Cap at 5 insights
        result.append({
            "product_id": str(product.id),
            "insight_type": ins.get("insight_type", "performance_anomaly"),
            "priority": ins.get("priority", "medium"),
            "title": ins.get("title", ""),
            "body": ins.get("body", ""),
            "recommended_action": ins.get("recommended_action"),
            "action_type": ins.get("action_type"),
            "data": {
                "performance_summary": perf_summary,
                "narrative_breakdown": narrative_breakdown[:5],
                "fatigue_summary": fatigue_summary,
            },
            "generated_by": settings.GEMINI_MODEL,
        })

    return result


async def generate_global_insights(db: AsyncSession) -> List[Dict]:
    """Generate cross-product global insights."""
    # Get top opportunity: product with best ROAS but lowest creative volume
    result = await db.execute(
        select(
            Product.id,
            Product.name,
            func.count(func.distinct(Creative.id)).label("active_creatives"),
            func.avg(CreativeDailyMetrics.roas).label("avg_roas"),
            func.sum(CreativeDailyMetrics.spend).label("total_spend"),
        )
        .join(Creative, Creative.product_id == Product.id)
        .join(CreativeDailyMetrics, CreativeDailyMetrics.creative_id == Creative.id)
        .where(CreativeDailyMetrics.date >= date.today() - timedelta(days=30))
        .where(CreativeDailyMetrics.spend > 0)
        .where(Creative.status == "active")
        .group_by(Product.id, Product.name)
        .order_by(func.avg(CreativeDailyMetrics.roas).desc())
    )

    rows = result.all()
    insights = []

    if rows:
        top = rows[0]
        insights.append({
            "product_id": None,
            "insight_type": "opportunity",
            "priority": "high",
            "title": f"{top.name} has the highest ROAS but may need more creative volume to scale",
            "body": (
                f"{top.name} is generating {float(top.avg_roas or 0):.1f}x ROAS with only "
                f"{top.active_creatives} active creatives. This is the highest-performing product "
                f"but creative inventory may be limiting scale."
            ),
            "recommended_action": f"Prioritize creative production for {top.name} — target 3-5 new creatives",
            "action_type": "create_creative",
            "data": {"product_id": str(top.id), "avg_roas": float(top.avg_roas or 0)},
            "generated_by": settings.GEMINI_MODEL,
        })

    return insights


async def create_fatigue_alert(
    db: AsyncSession,
    creative: Creative,
    fatigue_result: Any,
) -> Optional[Insight]:
    """Create an immediate fatigue alert insight for a critical creative."""
    if fatigue_result.fatigue_stage not in ("fatiguing", "fatigued"):
        return None

    priority = "critical" if fatigue_result.fatigue_stage == "fatigued" else "high"
    remaining = fatigue_result.expected_remaining_days or 0

    title = (
        f"URGENT: {creative.name or 'Creative'} is fatigued — "
        f"{'pause immediately' if fatigue_result.fatigue_stage == 'fatigued' else f'~{remaining} days remaining'}"
    )

    body = (
        f"Fatigue score: {fatigue_result.fatigue_score:.0f}/100 ({fatigue_result.fatigue_stage}). "
    )
    if fatigue_result.alerts:
        body += " ".join(fatigue_result.alerts[:2])

    insight = Insight(
        product_id=creative.product_id,
        creative_id=creative.id,
        insight_type="fatigue_alert",
        priority=priority,
        title=title,
        body=body,
        recommended_action=(
            "Pause this creative and replace with a fresh variant using a different narrative or hook."
            if fatigue_result.fatigue_stage == "fatigued"
            else f"Monitor closely. Prepare replacement creative within {remaining} days."
        ),
        action_type="pause_creative" if fatigue_result.fatigue_stage == "fatigued" else "monitor",
        data={
            "fatigue_score": fatigue_result.fatigue_score,
            "fatigue_stage": fatigue_result.fatigue_stage,
            "component_scores": fatigue_result.component_scores,
            "alerts": fatigue_result.alerts,
        },
        generated_by="fatigue-engine-v1",
    )

    db.add(insight)
    await db.flush()
    return insight
