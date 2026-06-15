"""Fatigue monitoring and analysis endpoints."""
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Query
from sqlalchemy import select, func

from app.api.deps import DbDep, CurrentUser
from app.models.orm import (
    Creative, FatigueScore, Product, NarrativePerformance,
    Narrative, CreativeDailyMetrics
)


router = APIRouter(prefix="/fatigue", tags=["fatigue"])


@router.post("/recalculate")
async def trigger_fatigue_recalculate(background_tasks: BackgroundTasks):
    """Trigger a fatigue score recalculation for all active creatives."""
    from app.workers.tasks import _recalculate_fatigue_async
    background_tasks.add_task(_recalculate_fatigue_async)
    return {"status": "started", "message": "Fatigue recalculation running in background (~30s)"}


@router.get("/dashboard")
async def fatigue_dashboard(db: DbDep, _: CurrentUser, product_id: Optional[str] = Query(None)):
    """Full fatigue dashboard data."""
    # Use the most recent calculated_date rather than today() to handle gaps
    # between data syncs and the current date.
    latest_date_row = await db.execute(select(func.max(FatigueScore.calculated_date)))
    latest_date = latest_date_row.scalar() or date.today()

    filters = [
        FatigueScore.calculated_date == latest_date,
    ]
    if product_id:
        filters.append(FatigueScore.product_id == UUID(product_id))

    # Current stage distribution
    dist = await db.execute(
        select(
            FatigueScore.fatigue_stage,
            func.count(FatigueScore.creative_id).label("count"),
            func.avg(FatigueScore.fatigue_score).label("avg_score"),
        )
        .join(Creative, Creative.id == FatigueScore.creative_id)
        .where(*filters)
        .where(Creative.status == "active")
        .group_by(FatigueScore.fatigue_stage)
    )
    distribution = {r.fatigue_stage: {"count": r.count, "avg_score": round(float(r.avg_score or 0), 1)}
                    for r in dist}

    # Fatiguing / fatigued creatives that need attention
    urgent = await db.execute(
        select(
            Creative.id,
            Creative.name,
            Creative.thumbnail_url,
            Creative.product_id,
            Product.name.label("product_name"),
            FatigueScore.fatigue_score,
            FatigueScore.fatigue_stage,
            FatigueScore.expected_remaining_days,
            FatigueScore.days_since_launch,
            FatigueScore.current_frequency,
            FatigueScore.ctr_decay_score,
            FatigueScore.roas_decay_score,
        )
        .join(Creative, Creative.id == FatigueScore.creative_id)
        .join(Product, Product.id == Creative.product_id)
        .where(*filters)
        .where(Creative.status == "active")
        .where(FatigueScore.fatigue_stage.in_(["fatiguing", "fatigued"]))
        .order_by(FatigueScore.fatigue_score.desc())
        .limit(20)
    )

    urgent_list = [
        {
            "creative_id": str(r.id),
            "name": r.name,
            "thumbnail_url": r.thumbnail_url,
            "product_id": str(r.product_id),
            "product_name": r.product_name,
            "fatigue_score": float(r.fatigue_score),
            "fatigue_stage": r.fatigue_stage,
            "expected_remaining_days": r.expected_remaining_days,
            "days_since_launch": r.days_since_launch,
            "current_frequency": float(r.current_frequency) if r.current_frequency else None,
            "ctr_decay_score": float(r.ctr_decay_score) if r.ctr_decay_score else None,
            "roas_decay_score": float(r.roas_decay_score) if r.roas_decay_score else None,
        }
        for r in urgent
    ]

    return {
        "as_of_date": latest_date.isoformat(),
        "distribution": distribution,
        "urgent_creatives": urgent_list,
    }


@router.get("/creatives/{creative_id}/curve")
async def fatigue_curve(
    creative_id: str,
    db: DbDep,
    _: CurrentUser,
    days: int = Query(60, le=120),
):
    """Get the fatigue score time series for charting the fatigue curve."""
    cutoff = date.today() - timedelta(days=days)

    scores = await db.execute(
        select(FatigueScore)
        .where(FatigueScore.creative_id == UUID(creative_id))
        .where(FatigueScore.calculated_date >= cutoff)
        .order_by(FatigueScore.calculated_date)
    )

    return [
        {
            "date": s.calculated_date.isoformat(),
            "fatigue_score": float(s.fatigue_score),
            "fatigue_stage": s.fatigue_stage,
            "ctr_decay": float(s.ctr_decay_score or 0),
            "roas_decay": float(s.roas_decay_score or 0),
            "cpa_inflation": float(s.cpa_inflation_score or 0),
            "hook_decay": float(s.hook_decay_score or 0),
            "frequency_score": float(s.frequency_score or 0),
            "expected_remaining_days": s.expected_remaining_days,
            "confidence": float(s.confidence_score or 0),
        }
        for s in scores.scalars()
    ]


@router.get("/narrative-lifespans")
async def narrative_lifespans(
    db: DbDep,
    _: CurrentUser,
    product_id: Optional[str] = Query(None),
):
    """Get average narrative lifespans per product (the fatigue profile for each narrative)."""
    query = (
        select(
            Product.name.label("product_name"),
            Product.id.label("product_id"),
            Narrative.name.label("narrative_name"),
            Narrative.narrative_type,
            NarrativePerformance.avg_lifespan_days,
            NarrativePerformance.median_lifespan_days,
            NarrativePerformance.avg_fatigue_start_day,
            NarrativePerformance.ctr_decay_rate_pct,
            NarrativePerformance.cpa_increase_rate_pct,
            NarrativePerformance.roas_decay_rate_pct,
            NarrativePerformance.active_creatives,
            NarrativePerformance.is_oversaturated,
            NarrativePerformance.avg_roas,
        )
        .join(Product, Product.id == NarrativePerformance.product_id)
        .join(Narrative, Narrative.id == NarrativePerformance.narrative_id)
        .where(Product.is_active == True)
    )

    if product_id:
        query = query.where(NarrativePerformance.product_id == UUID(product_id))

    result = await db.execute(query.order_by(Product.name, NarrativePerformance.avg_lifespan_days.desc()))

    return [
        {
            "product_id": str(r.product_id),
            "product_name": r.product_name,
            "narrative_name": r.narrative_name,
            "narrative_type": r.narrative_type,
            "avg_lifespan_days": float(r.avg_lifespan_days) if r.avg_lifespan_days else None,
            "median_lifespan_days": float(r.median_lifespan_days) if r.median_lifespan_days else None,
            "avg_fatigue_start_day": float(r.avg_fatigue_start_day) if r.avg_fatigue_start_day else None,
            "ctr_decay_rate_pct": float(r.ctr_decay_rate_pct) if r.ctr_decay_rate_pct else None,
            "active_creatives": r.active_creatives,
            "is_oversaturated": r.is_oversaturated,
            "avg_roas": float(r.avg_roas) if r.avg_roas else None,
        }
        for r in result
    ]
