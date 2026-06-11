"""
Prediction Engine — Man Matters Creative OS

Pre-launch scoring for new creatives. Answers:
"Will this creative win before we spend money on it?"

Scoring architecture:
- Winner similarity (35%): How similar to proven winners
- Loser distance (20%): How different from proven losers
- Narrative fitness (20%): How well the narrative performs for this product
- Format fitness (10%): How well this format performs for this product
- Novelty / saturation (15%): Not oversaturating a narrative

Returns 0-100 Creative Success Score + predicted metrics.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.orm import (
    Creative, CreativeDailyMetrics, NarrativePerformance,
    FormatPerformance, ProductBenchmark, CreativeEmbedding,
    CreativeMetadata
)
from app.services.embedding_service import (
    find_similar_creatives,
    _embed_query,
    build_embedding_text,
)


@dataclass
class PredictionResult:
    # Composite scores (0-100)
    creative_success_score: float
    narrative_score: float
    hook_score: float
    visual_score: float
    offer_score: float
    novelty_score: float
    launch_confidence_score: float
    fatigue_risk_score: float

    # Similarity
    winner_similarity_pct: float
    loser_similarity_pct: float

    # Predicted metrics
    predicted_ctr: Optional[float]
    predicted_cpa: Optional[float]
    predicted_roas: Optional[float]
    predicted_lifespan_days: Optional[int]

    # Recommendation
    recommendation: str  # launch_immediately, launch_with_caution, test, iterate, avoid
    recommendation_reason: str

    # Evidence
    similar_winner_ids: List[str] = field(default_factory=list)
    similar_loser_ids: List[str] = field(default_factory=list)
    comparable_narratives: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    opportunity_factors: List[str] = field(default_factory=list)

    model_version: str = "prediction-engine-v1"
    prediction_confidence: float = 0.5


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))


def _narrative_to_score(narrative_perf: Optional[Any], product_benchmarks: Optional[Any]) -> float:
    """
    Convert narrative performance data into a 0-100 score.
    Compares narrative's avg ROAS vs product median ROAS.
    """
    if not narrative_perf or not narrative_perf.avg_roas:
        return 50.0  # unknown narrative = neutral

    if not product_benchmarks or not product_benchmarks.median_roas:
        return 50.0

    roas_ratio = narrative_perf.avg_roas / product_benchmarks.median_roas
    # roas_ratio of 1.5 = 50% better than median = score ~75
    # roas_ratio of 2.0 = 100% better = score ~100
    # roas_ratio of 0.5 = 50% worse = score ~25
    score = min(100.0, max(0.0, (roas_ratio - 0.5) / 1.5 * 100.0))
    return round(score, 2)


def _saturation_to_novelty(
    narrative_perf: Optional[Any],
    active_narrative_count: int,
    total_active_creatives: int,
) -> Tuple[float, List[str]]:
    """
    Calculate novelty score: higher = fresher/less saturated narrative.
    Returns (novelty_score, risk_factors).
    """
    risk_factors = []

    if not narrative_perf:
        return 80.0, []  # Unknown narrative = high novelty

    volume_share = (active_narrative_count / total_active_creatives * 100) if total_active_creatives > 0 else 0
    is_oversaturated = narrative_perf.is_oversaturated if narrative_perf else False
    saturation_score = narrative_perf.saturation_score or 0

    if is_oversaturated or saturation_score > 70:
        risk_factors.append(
            f"This narrative is oversaturated for this product "
            f"({volume_share:.0f}% of active creatives)"
        )
        novelty = max(0.0, 30.0 - saturation_score * 0.3)
    elif saturation_score > 40:
        risk_factors.append(
            f"Moderate saturation for this narrative ({volume_share:.0f}% of active creatives)"
        )
        novelty = 50.0
    else:
        novelty = min(100.0, 80.0 + (40.0 - saturation_score) * 0.5)

    return round(novelty, 2), risk_factors


def _format_score_from_perf(
    format_perf: Optional[Any],
    product_benchmarks: Optional[Any],
) -> float:
    """Score how well this format performs for the product."""
    if not format_perf or not format_perf.avg_roas:
        return 50.0
    if not product_benchmarks or not product_benchmarks.median_roas:
        return 50.0

    roas_ratio = format_perf.avg_roas / product_benchmarks.median_roas
    return min(100.0, max(0.0, round((roas_ratio - 0.5) / 1.5 * 100.0, 2)))


def _offer_score(offer_type: str, narrative_type: str, stage_of_funnel: str) -> float:
    """Score the offer based on funnel stage alignment."""
    # Discount/bundle offers are great for conversion stage
    conversion_boosters = {"discount", "bundle", "trial", "buy_one_get_one"}
    awareness_neutral = {"none", "lifestyle_upgrade"}

    if stage_of_funnel == "conversion" and offer_type in conversion_boosters:
        return 80.0
    elif stage_of_funnel == "awareness" and offer_type in conversion_boosters:
        # Hard sell in awareness = slightly misaligned
        return 60.0
    elif offer_type == "none" and stage_of_funnel == "conversion":
        # No offer in conversion stage = slight penalty
        return 55.0
    return 65.0


def _compute_predicted_metrics(
    winner_similarity: float,
    narrative_perf: Optional[Any],
    format_perf: Optional[Any],
    product_benchmarks: Optional[Any],
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[int]]:
    """
    Compute predicted CTR, CPA, ROAS, and lifespan based on similarity
    to winners and historical narrative/format performance.
    """
    if not product_benchmarks:
        return None, None, None, None

    # Blend: weighted average of narrative perf + product median, weighted by winner similarity
    w = winner_similarity / 100.0  # 0-1

    # CTR prediction
    pred_ctr = None
    if product_benchmarks.median_ctr:
        base_ctr = product_benchmarks.median_ctr
        narrative_ctr = (narrative_perf.avg_ctr if narrative_perf and narrative_perf.avg_ctr else base_ctr)
        pred_ctr = (1 - w) * base_ctr + w * narrative_ctr * 1.1  # winners perform ~10% better

    # CPA prediction
    pred_cpa = None
    if product_benchmarks.median_cpa:
        base_cpa = float(product_benchmarks.median_cpa)
        narrative_cpa = float(narrative_perf.avg_cpa) if narrative_perf and narrative_perf.avg_cpa else base_cpa
        pred_cpa = (1 - w) * base_cpa + w * narrative_cpa * 0.9  # winners have lower CPA

    # ROAS prediction
    pred_roas = None
    if product_benchmarks.median_roas:
        base_roas = float(product_benchmarks.median_roas)
        narrative_roas = float(narrative_perf.avg_roas) if narrative_perf and narrative_perf.avg_roas else base_roas
        pred_roas = (1 - w) * base_roas + w * narrative_roas * 1.1

    # Lifespan prediction
    pred_lifespan = None
    if narrative_perf and narrative_perf.avg_lifespan_days:
        base_lifespan = float(narrative_perf.avg_lifespan_days)
        # Winners typically last longer
        pred_lifespan = int(base_lifespan * (1 + w * 0.3))

    return pred_ctr, pred_cpa, pred_roas, pred_lifespan


def _determine_recommendation(
    success_score: float,
    fatigue_risk: float,
    novelty_score: float,
    winner_similarity: float,
    loser_similarity: float,
) -> Tuple[str, str]:
    """Classify recommendation and generate reason."""
    reasons = []

    if success_score >= 80 and fatigue_risk < 40:
        rec = "launch_immediately"
        reasons.append(f"High success score ({success_score:.0f}/100)")
        reasons.append(f"{winner_similarity:.0f}% similar to proven winners")
        if novelty_score > 70:
            reasons.append("Fresh narrative with low saturation risk")
    elif success_score >= 65 and fatigue_risk < 60:
        rec = "launch_with_caution"
        reasons.append(f"Good success score ({success_score:.0f}/100)")
        if fatigue_risk >= 40:
            reasons.append(f"Moderate fatigue risk ({fatigue_risk:.0f}/100) — monitor frequency closely")
    elif success_score >= 50:
        rec = "test"
        reasons.append(f"Moderate success score ({success_score:.0f}/100) — test with limited budget first")
        if loser_similarity > 40:
            reasons.append(f"Some similarity to poor performers ({loser_similarity:.0f}%)")
    elif success_score >= 35:
        rec = "iterate"
        reasons.append(f"Below-average success score ({success_score:.0f}/100)")
        reasons.append("Consider refining hook or narrative before launch")
    else:
        rec = "avoid"
        reasons.append(f"Low success score ({success_score:.0f}/100)")
        if loser_similarity > 60:
            reasons.append(f"High similarity to historical losers ({loser_similarity:.0f}%)")

    return rec, ". ".join(reasons)


async def predict_creative(
    db: AsyncSession,
    creative_id: str,
    metadata: Dict,
    headline: str = "",
    body_text: str = "",
    product_id: Optional[str] = None,
) -> PredictionResult:
    """
    Full prediction pipeline for a creative.

    1. Embed the creative
    2. Find similar winners and losers
    3. Score against narrative/format benchmarks
    4. Calculate novelty/saturation
    5. Produce composite score and recommendation
    """
    import uuid as uuid_mod
    pid = uuid_mod.UUID(product_id) if product_id else None
    cid = uuid_mod.UUID(creative_id)

    # Build embedding text and generate embedding
    full_text = build_embedding_text(metadata, headline, body_text)
    query_embedding = _embed_query(full_text)

    # Find similar creatives
    similar = await find_similar_creatives(
        db, query_embedding, product_id=pid, limit=20, exclude_id=cid
    )

    winners = [s for s in similar if s.get("is_winner")]
    losers = [s for s in similar if not s.get("is_winner") and s.get("avg_roas", 0) < 1.5]
    top_winners = winners[:5]
    top_losers = losers[:5]

    winner_sim_pct = (
        np.mean([s["similarity"] for s in top_winners]) * 100
        if top_winners else 0.0
    )
    loser_sim_pct = (
        np.mean([s["similarity"] for s in top_losers]) * 100
        if top_losers else 0.0
    )

    # Get narrative performance
    narrative_type = metadata.get("narrative_type")
    narrative_perf = None
    format_type = metadata.get("creative_format") or metadata.get("visual_style")

    if pid and narrative_type:
        from sqlalchemy import select as sa_select
        from app.models.orm import NarrativePerformance, Narrative
        perf = await db.execute(
            sa_select(NarrativePerformance)
            .join(Narrative, Narrative.id == NarrativePerformance.narrative_id)
            .where(NarrativePerformance.product_id == pid)
            .where(Narrative.narrative_type == narrative_type)
        )
        narrative_perf = perf.scalar_one_or_none()

    # Get format performance
    format_perf = None
    if pid and format_type:
        from app.models.orm import FormatPerformance, Format
        fp = await db.execute(
            sa_select(FormatPerformance)
            .join(Format, Format.id == FormatPerformance.format_id)
            .where(FormatPerformance.product_id == pid)
            .where(Format.format_type == format_type)
        )
        format_perf = fp.scalar_one_or_none()

    # Get product benchmarks
    benchmarks = None
    if pid:
        benchmarks = await db.scalar(
            select(ProductBenchmark)
            .where(ProductBenchmark.product_id == pid)
            .where(ProductBenchmark.period_days == 30)
        )

    # Get active creative counts for saturation calculation
    total_active = 0
    narrative_active = 0
    if pid:
        total_active_result = await db.execute(
            select(func.count(Creative.id))
            .where(Creative.product_id == pid)
            .where(Creative.status == "active")
        )
        total_active = total_active_result.scalar() or 0

        if narrative_type:
            narrative_active_result = await db.execute(
                select(func.count(Creative.id))
                .join(CreativeMetadata, CreativeMetadata.creative_id == Creative.id)
                .where(Creative.product_id == pid)
                .where(Creative.status == "active")
                .where(CreativeMetadata.narrative_type == narrative_type)
            )
            narrative_active = narrative_active_result.scalar() or 0

    # Compute individual scores
    narrative_score = _narrative_to_score(narrative_perf, benchmarks)
    format_score = _format_score_from_perf(format_perf, benchmarks)
    novelty_score, saturation_risks = _saturation_to_novelty(
        narrative_perf, narrative_active, total_active
    )
    offer_score = _offer_score(
        metadata.get("offer_type", "none"),
        metadata.get("narrative_type", ""),
        metadata.get("stage_of_funnel", "consideration"),
    )

    # Hook score: based on similarity to winning hooks
    hook_score = min(95.0, winner_sim_pct * 0.7 + narrative_score * 0.3)

    # Visual score: weighted by winner similarity and production quality
    prod_quality_bonus = {"professional": 10, "semi_professional": 5, "ugc": 0}
    visual_score = min(95.0, winner_sim_pct * 0.6 + 40 + prod_quality_bonus.get(
        metadata.get("production_quality", "ugc"), 0
    ))

    # Fatigue risk: high if narrative is saturated + loser similarity is high
    fatigue_risk = min(100.0, (
        (100 - novelty_score) * 0.5 +
        loser_sim_pct * 0.3 +
        max(0, (narrative_active / max(total_active, 1) * 100) - 20) * 0.2
    ))

    # Composite Creative Success Score
    success_score = min(100.0, max(0.0, (
        winner_sim_pct * 0.35 +
        (100 - loser_sim_pct) * 0.20 +
        narrative_score * 0.20 +
        format_score * 0.10 +
        novelty_score * 0.15
    )))

    # Launch confidence: penalize low data confidence
    data_confidence = min(1.0, (len(top_winners) + len(top_losers)) / 10.0)
    launch_confidence = success_score * (0.5 + data_confidence * 0.5)

    # Predicted metrics
    pred_ctr, pred_cpa, pred_roas, pred_lifespan = _compute_predicted_metrics(
        winner_sim_pct, narrative_perf, format_perf, benchmarks
    )

    # Recommendation
    recommendation, reason = _determine_recommendation(
        success_score, fatigue_risk, novelty_score, winner_sim_pct, loser_sim_pct
    )

    # Opportunity factors
    opportunity_factors = []
    if winner_sim_pct > 70:
        opportunity_factors.append(f"Strong alignment with proven winners ({winner_sim_pct:.0f}% similar)")
    if narrative_perf and narrative_perf.avg_roas and narrative_perf.avg_roas > (benchmarks.median_roas if benchmarks and benchmarks.median_roas else 2.0):
        opportunity_factors.append(f"Narrative historically performs above product median")
    if novelty_score > 75:
        opportunity_factors.append("Fresh narrative with room to scale")

    # Risk factors
    risk_factors = saturation_risks.copy()
    if loser_sim_pct > 50:
        risk_factors.append(f"Shares {loser_sim_pct:.0f}% similarity with historical losers")
    if fatigue_risk > 60:
        risk_factors.append("High narrative saturation — fatigue likely within 7-10 days")

    return PredictionResult(
        creative_success_score=round(success_score, 2),
        narrative_score=round(narrative_score, 2),
        hook_score=round(hook_score, 2),
        visual_score=round(visual_score, 2),
        offer_score=round(offer_score, 2),
        novelty_score=round(novelty_score, 2),
        launch_confidence_score=round(launch_confidence, 2),
        fatigue_risk_score=round(fatigue_risk, 2),
        winner_similarity_pct=round(winner_sim_pct, 2),
        loser_similarity_pct=round(loser_sim_pct, 2),
        predicted_ctr=round(pred_ctr, 6) if pred_ctr else None,
        predicted_cpa=round(pred_cpa, 2) if pred_cpa else None,
        predicted_roas=round(pred_roas, 2) if pred_roas else None,
        predicted_lifespan_days=pred_lifespan,
        recommendation=recommendation,
        recommendation_reason=reason,
        similar_winner_ids=[str(w["creative_id"]) for w in top_winners],
        similar_loser_ids=[str(l["creative_id"]) for l in top_losers],
        comparable_narratives=[narrative_type] if narrative_type else [],
        risk_factors=risk_factors,
        opportunity_factors=opportunity_factors,
        prediction_confidence=round(data_confidence, 3),
        model_version="prediction-engine-v1",
    )
