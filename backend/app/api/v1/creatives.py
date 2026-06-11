"""Creative CRUD and analysis endpoints."""
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.api.deps import DbDep, CurrentUser
from app.models.orm import (
    Creative, CreativeMetadata, FatigueScore, Product,
    CreativeDailyMetrics, Narrative, Format, Hook, Archetype
)


router = APIRouter(prefix="/creatives", tags=["creatives"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreativeListItem(BaseModel):
    id: str
    name: Optional[str]
    product_id: str
    product_name: Optional[str]
    status: str
    media_type: Optional[str]
    thumbnail_url: Optional[str]
    launch_date: Optional[date]
    analysis_status: str
    narrative_type: Optional[str]
    hook_type: Optional[str]
    creator_type: Optional[str]
    visual_style: Optional[str]
    offer_type: Optional[str]
    stage_of_funnel: Optional[str]
    fatigue_score: Optional[float]
    fatigue_stage: Optional[str]
    expected_remaining_days: Optional[int]
    spend_7d: Optional[float]
    roas_7d: Optional[float]
    ctr_7d: Optional[float]
    cpa_7d: Optional[float]
    purchases_7d: Optional[int]
    creative_success_score: Optional[float]
    recommendation: Optional[str]

    class Config:
        from_attributes = True


class CreativeDetail(CreativeListItem):
    headline: Optional[str]
    body_text: Optional[str]
    cta_type: Optional[str]
    duration_seconds: Optional[int]
    aspect_ratio: Optional[str]
    media_url: Optional[str]
    storage_url: Optional[str]
    pain_point: Optional[str]
    benefit_claimed: Optional[str]
    trust_signal: Optional[str]
    emotional_trigger: Optional[str]
    production_quality: Optional[str]
    analysis_confidence: Optional[float]
    peak_performance_date: Optional[date]
    fatigue_start_date: Optional[date]


class CreativeMetricsPoint(BaseModel):
    date: date
    spend: float
    ctr: float
    roas: float
    cpa: float
    hook_rate: float
    hold_rate: float
    frequency: float
    purchases: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=List[CreativeListItem])
async def list_creatives(
    db: DbDep,
    _: CurrentUser,
    product_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    narrative_type: Optional[str] = Query(None),
    hook_type: Optional[str] = Query(None),
    creator_type: Optional[str] = Query(None),
    fatigue_stage: Optional[str] = Query(None),
    media_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    """List creatives with full health data. Supports filtering and search."""
    # Query from the v_creative_health view
    from sqlalchemy import text

    filters = []
    params: dict = {"limit": limit, "offset": offset}

    if product_id:
        filters.append("c.product_id = :product_id::uuid")
        params["product_id"] = product_id
    if status:
        filters.append("c.status = :status")
        params["status"] = status
    if narrative_type:
        filters.append("cm.narrative_type = :narrative_type")
        params["narrative_type"] = narrative_type
    if hook_type:
        filters.append("cm.hook_type = :hook_type")
        params["hook_type"] = hook_type
    if creator_type:
        filters.append("cm.creator_type = :creator_type")
        params["creator_type"] = creator_type
    if fatigue_stage:
        filters.append("fs.fatigue_stage = :fatigue_stage")
        params["fatigue_stage"] = fatigue_stage
    if media_type:
        filters.append("c.media_type = :media_type")
        params["media_type"] = media_type
    if search:
        filters.append("(c.name ILIKE :search OR c.headline ILIKE :search)")
        params["search"] = f"%{search}%"

    where_clause = "WHERE " + " AND ".join(filters) if filters else ""

    query = text(f"""
        SELECT
            c.id::text AS id,
            c.name,
            c.product_id::text,
            p.name AS product_name,
            c.status,
            c.media_type,
            c.thumbnail_url,
            c.launch_date,
            c.analysis_status,
            cm.narrative_type,
            cm.hook_type,
            cm.creator_type,
            cm.visual_style,
            cm.offer_type,
            cm.stage_of_funnel,
            fs.fatigue_score,
            fs.fatigue_stage,
            fs.expected_remaining_days,
            (SELECT SUM(m.spend) FROM creative_daily_metrics m
             WHERE m.creative_id = c.id AND m.date >= CURRENT_DATE - 7
               AND m.attribution_window = '7d_click') AS spend_7d,
            (SELECT AVG(m.roas) FROM creative_daily_metrics m
             WHERE m.creative_id = c.id AND m.date >= CURRENT_DATE - 7
               AND m.attribution_window = '7d_click' AND m.roas > 0) AS roas_7d,
            (SELECT AVG(m.ctr) FROM creative_daily_metrics m
             WHERE m.creative_id = c.id AND m.date >= CURRENT_DATE - 7
               AND m.attribution_window = '7d_click' AND m.ctr > 0) AS ctr_7d,
            (SELECT AVG(m.cpa) FROM creative_daily_metrics m
             WHERE m.creative_id = c.id AND m.date >= CURRENT_DATE - 7
               AND m.attribution_window = '7d_click' AND m.cpa > 0) AS cpa_7d,
            (SELECT SUM(m.purchases) FROM creative_daily_metrics m
             WHERE m.creative_id = c.id AND m.date >= CURRENT_DATE - 7
               AND m.attribution_window = '7d_click') AS purchases_7d,
            pred.creative_success_score,
            pred.recommendation
        FROM creatives c
        JOIN products p ON p.id = c.product_id
        LEFT JOIN creative_metadata cm ON cm.creative_id = c.id
        LEFT JOIN LATERAL (
            SELECT fs.fatigue_score, fs.fatigue_stage, fs.expected_remaining_days
            FROM fatigue_scores fs WHERE fs.creative_id = c.id
            ORDER BY fs.calculated_date DESC LIMIT 1
        ) fs ON TRUE
        LEFT JOIN LATERAL (
            SELECT pred.creative_success_score, pred.recommendation
            FROM creative_predictions pred WHERE pred.creative_id = c.id
            ORDER BY pred.created_at DESC LIMIT 1
        ) pred ON TRUE
        {where_clause}
        ORDER BY c.created_at DESC
        LIMIT :limit OFFSET :offset
    """)

    result = await db.execute(query, params)
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.get("/{creative_id}", response_model=CreativeDetail)
async def get_creative(creative_id: str, db: DbDep, _: CurrentUser):
    """Get full creative details with all metadata."""
    creative = await db.scalar(
        select(Creative)
        .options(
            selectinload(Creative.creative_metadata),
            selectinload(Creative.product),
        )
        .where(Creative.id == UUID(creative_id))
    )
    if not creative:
        raise HTTPException(status_code=404, detail="Creative not found")

    meta = creative.creative_metadata
    return {
        "id": str(creative.id),
        "name": creative.name,
        "product_id": str(creative.product_id),
        "product_name": creative.product.name if creative.product else None,
        "status": creative.status,
        "media_type": creative.media_type,
        "thumbnail_url": creative.thumbnail_url,
        "media_url": creative.media_url,
        "storage_url": creative.storage_url,
        "launch_date": creative.launch_date,
        "analysis_status": creative.analysis_status,
        "headline": creative.headline,
        "body_text": creative.body_text,
        "cta_type": creative.cta_type,
        "duration_seconds": creative.duration_seconds,
        "aspect_ratio": creative.aspect_ratio,
        "peak_performance_date": creative.peak_performance_date,
        "fatigue_start_date": creative.fatigue_start_date,
        # Metadata
        "narrative_type": meta.narrative_type if meta else None,
        "hook_type": meta.hook_type if meta else None,
        "creator_type": meta.creator_type if meta else None,
        "visual_style": meta.visual_style if meta else None,
        "offer_type": meta.offer_type if meta else None,
        "stage_of_funnel": meta.stage_of_funnel if meta else None,
        "pain_point": meta.pain_point if meta else None,
        "benefit_claimed": meta.benefit_claimed if meta else None,
        "trust_signal": meta.trust_signal if meta else None,
        "emotional_trigger": meta.emotional_trigger if meta else None,
        "production_quality": meta.production_quality if meta else None,
        "analysis_confidence": meta.analysis_confidence if meta else None,
        # Will be joined by list endpoint
        "fatigue_score": None,
        "fatigue_stage": None,
        "expected_remaining_days": None,
        "spend_7d": None,
        "roas_7d": None,
        "ctr_7d": None,
        "cpa_7d": None,
        "purchases_7d": None,
        "creative_success_score": None,
        "recommendation": None,
    }


@router.get("/{creative_id}/metrics", response_model=List[CreativeMetricsPoint])
async def get_creative_metrics(
    creative_id: str,
    db: DbDep,
    _: CurrentUser,
    days: int = Query(30, le=90),
):
    """Get daily metrics time series for a creative."""
    from datetime import timedelta
    cutoff = date.today() - timedelta(days=days)

    result = await db.execute(
        select(CreativeDailyMetrics)
        .where(CreativeDailyMetrics.creative_id == UUID(creative_id))
        .where(CreativeDailyMetrics.date >= cutoff)
        .where(CreativeDailyMetrics.attribution_window == "7d_click")
        .order_by(CreativeDailyMetrics.date)
    )
    rows = result.scalars().all()

    return [
        {
            "date": m.date,
            "spend": float(m.spend or 0),
            "ctr": float(m.ctr or 0) * 100,  # Return as percentage
            "roas": float(m.roas or 0),
            "cpa": float(m.cpa or 0),
            "hook_rate": float(m.hook_rate or 0) * 100,
            "hold_rate": float(m.hold_rate or 0) * 100,
            "frequency": float(m.frequency or 0),
            "purchases": int(m.purchases or 0),
        }
        for m in rows
    ]


@router.post("/{creative_id}/reanalyze")
async def reanalyze_creative(
    creative_id: str,
    db: DbDep,
    _: CurrentUser,
    background_tasks: BackgroundTasks,
):
    """Trigger re-analysis of a creative with Gemini."""
    creative = await db.get(Creative, UUID(creative_id))
    if not creative:
        raise HTTPException(status_code=404, detail="Creative not found")

    creative.analysis_status = "pending"
    creative.analysis_error = None
    db.add(creative)
    await db.commit()

    from app.workers.tasks import analyze_single_creative
    analyze_single_creative.delay(creative_id)

    return {"status": "queued", "creative_id": creative_id}


@router.get("/{creative_id}/similar")
async def get_similar_creatives(
    creative_id: str,
    db: DbDep,
    _: CurrentUser,
    limit: int = Query(10, le=20),
):
    """Find creatives most similar to this one using embedding similarity."""
    from app.models.orm import CreativeEmbedding
    from app.services.embedding_service import find_similar_creatives

    emb = await db.scalar(
        select(CreativeEmbedding).where(CreativeEmbedding.creative_id == UUID(creative_id))
    )
    if not emb or emb.embedding is None:
        raise HTTPException(status_code=404, detail="Embedding not yet generated for this creative")

    similar = await find_similar_creatives(
        db,
        query_embedding=list(emb.embedding),
        limit=limit + 1,  # +1 to exclude self
        exclude_id=UUID(creative_id),
    )
    return similar[:limit]
