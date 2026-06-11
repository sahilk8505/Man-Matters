"""Analytics and performance reporting endpoints."""
from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select, func, text

from app.api.deps import DbDep, CurrentUser
from app.models.orm import (
    Product, Creative, CreativeDailyMetrics, FatigueScore,
    NarrativePerformance, Narrative, FormatPerformance, Format,
    Insight, CreativeMetadata
)


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/executive-summary")
async def executive_summary(db: DbDep, _: CurrentUser):
    """
    Top-level executive dashboard data.
    Returns portfolio health, active fatigue alerts, top products, recent insights.
    """
    today = date.today()
    last_30 = today - timedelta(days=30)
    last_7 = today - timedelta(days=7)

    # Portfolio-wide metrics (last 30 days)
    metrics = await db.execute(
        select(
            func.sum(CreativeDailyMetrics.spend).label("total_spend"),
            func.sum(CreativeDailyMetrics.purchases).label("total_purchases"),
            func.sum(CreativeDailyMetrics.purchase_value).label("total_revenue"),
            func.avg(CreativeDailyMetrics.roas).filter(CreativeDailyMetrics.roas > 0).label("avg_roas"),
            func.avg(CreativeDailyMetrics.ctr).filter(CreativeDailyMetrics.ctr > 0).label("avg_ctr"),
            func.avg(CreativeDailyMetrics.cpa).filter(CreativeDailyMetrics.cpa > 0).label("avg_cpa"),
        )
        .where(CreativeDailyMetrics.date >= last_30)
        .where(CreativeDailyMetrics.attribution_window == "7d_click")
        .where(CreativeDailyMetrics.spend > 0)
    )
    m = metrics.one()

    # Creative health counts
    health = await db.execute(
        select(
            FatigueScore.fatigue_stage,
            func.count(FatigueScore.creative_id).label("count"),
        )
        .join(Creative, Creative.id == FatigueScore.creative_id)
        .where(FatigueScore.calculated_date == today)
        .where(Creative.status == "active")
        .group_by(FatigueScore.fatigue_stage)
    )
    health_counts = {r.fatigue_stage: r.count for r in health}

    # Active creatives
    total_active = await db.scalar(
        select(func.count(Creative.id))
        .where(Creative.status == "active")
    )

    # Unread insights count
    unread_insights = await db.scalar(
        select(func.count(Insight.id))
        .where(Insight.is_read == False)
        .where(Insight.is_dismissed == False)
    )

    # Recent critical insights
    recent_insights = await db.execute(
        select(Insight)
        .where(Insight.is_dismissed == False)
        .where(Insight.priority.in_(["critical", "high"]))
        .order_by(Insight.created_at.desc())
        .limit(5)
    )
    insights_list = [
        {
            "id": str(ins.id),
            "title": ins.title,
            "body": ins.body,
            "priority": ins.priority,
            "insight_type": ins.insight_type,
            "is_read": ins.is_read,
            "action_type": ins.action_type,
            "created_at": ins.created_at.isoformat() if ins.created_at else None,
        }
        for ins in recent_insights.scalars()
    ]

    # Spend by product (last 7 days)
    product_spend = await db.execute(
        select(
            Product.name,
            Product.id,
            Product.category,
            func.sum(CreativeDailyMetrics.spend).label("spend_7d"),
            func.avg(CreativeDailyMetrics.roas).filter(CreativeDailyMetrics.roas > 0).label("roas_7d"),
            func.sum(CreativeDailyMetrics.purchases).label("purchases_7d"),
        )
        .join(Creative, Creative.product_id == Product.id)
        .join(CreativeDailyMetrics, CreativeDailyMetrics.creative_id == Creative.id)
        .where(CreativeDailyMetrics.date >= last_7)
        .where(CreativeDailyMetrics.attribution_window == "7d_click")
        .where(Product.is_active == True)
        .group_by(Product.id, Product.name, Product.category)
        .order_by(func.sum(CreativeDailyMetrics.spend).desc())
    )

    products_data = [
        {
            "product_id": str(r.id),
            "product_name": r.name,
            "category": r.category,
            "spend_7d": float(r.spend_7d or 0),
            "roas_7d": float(r.roas_7d or 0),
            "purchases_7d": int(r.purchases_7d or 0),
        }
        for r in product_spend
    ]

    return {
        "period": {"start": last_30.isoformat(), "end": today.isoformat()},
        "portfolio": {
            "total_spend_30d": float(m.total_spend or 0),
            "total_purchases_30d": int(m.total_purchases or 0),
            "total_revenue_30d": float(m.total_revenue or 0),
            "avg_roas_30d": round(float(m.avg_roas or 0), 2),
            "avg_ctr_pct_30d": round(float(m.avg_ctr or 0) * 100, 3),
            "avg_cpa_30d": round(float(m.avg_cpa or 0), 0),
        },
        "creative_health": {
            "total_active": total_active or 0,
            "healthy": health_counts.get("healthy", 0),
            "watch": health_counts.get("watch", 0),
            "fatiguing": health_counts.get("fatiguing", 0),
            "fatigued": health_counts.get("fatigued", 0),
            "unscored": (total_active or 0) - sum(health_counts.values()),
        },
        "insights": {
            "unread_count": unread_insights or 0,
            "recent_critical": insights_list,
        },
        "products": products_data,
    }


@router.get("/products/{product_id}/performance")
async def product_performance(
    product_id: str,
    db: DbDep,
    _: CurrentUser,
    days: int = Query(30, le=90),
):
    """Detailed performance breakdown for a product."""
    pid = UUID(product_id)
    cutoff = date.today() - timedelta(days=days)

    product = await db.get(Product, pid)
    if not product:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Product not found")

    # Narrative breakdown
    narrative_data = await db.execute(
        select(
            CreativeMetadata.narrative_type,
            func.count(func.distinct(CreativeDailyMetrics.creative_id)).label("creative_count"),
            func.sum(CreativeDailyMetrics.spend).label("spend"),
            func.sum(CreativeDailyMetrics.purchases).label("purchases"),
            func.sum(CreativeDailyMetrics.purchase_value).label("revenue"),
            func.avg(CreativeDailyMetrics.roas).filter(CreativeDailyMetrics.roas > 0).label("avg_roas"),
            func.avg(CreativeDailyMetrics.ctr).filter(CreativeDailyMetrics.ctr > 0).label("avg_ctr"),
            func.avg(CreativeDailyMetrics.cpa).filter(CreativeDailyMetrics.cpa > 0).label("avg_cpa"),
        )
        .select_from(CreativeDailyMetrics)
        .join(Creative, Creative.id == CreativeDailyMetrics.creative_id)
        .join(CreativeMetadata, CreativeMetadata.creative_id == Creative.id)
        .where(CreativeDailyMetrics.product_id == pid)
        .where(CreativeDailyMetrics.date >= cutoff)
        .where(CreativeDailyMetrics.attribution_window == "7d_click")
        .where(CreativeDailyMetrics.spend >= 100)
        .where(CreativeMetadata.narrative_type.isnot(None))
        .group_by(CreativeMetadata.narrative_type)
        .order_by(func.sum(CreativeDailyMetrics.purchases).desc())
    )

    narratives = narrative_data.all()
    total_purchases = sum(int(r.purchases or 0) for r in narratives)
    total_spend = sum(float(r.spend or 0) for r in narratives)

    narrative_breakdown = [
        {
            "narrative_type": r.narrative_type,
            "creative_count": r.creative_count,
            "spend": float(r.spend or 0),
            "spend_pct": round(float(r.spend or 0) / total_spend * 100, 1) if total_spend else 0,
            "purchases": int(r.purchases or 0),
            "purchase_pct": round(int(r.purchases or 0) / total_purchases * 100, 1) if total_purchases else 0,
            "revenue": float(r.revenue or 0),
            "avg_roas": round(float(r.avg_roas or 0), 2),
            "avg_ctr_pct": round(float(r.avg_ctr or 0) * 100, 3),
            "avg_cpa": round(float(r.avg_cpa or 0), 0),
        }
        for r in narratives
    ]

    # Daily trend
    daily = await db.execute(
        select(
            CreativeDailyMetrics.date,
            func.sum(CreativeDailyMetrics.spend).label("spend"),
            func.sum(CreativeDailyMetrics.purchases).label("purchases"),
            func.avg(CreativeDailyMetrics.roas).filter(CreativeDailyMetrics.roas > 0).label("roas"),
            func.avg(CreativeDailyMetrics.ctr).filter(CreativeDailyMetrics.ctr > 0).label("ctr"),
        )
        .where(CreativeDailyMetrics.product_id == pid)
        .where(CreativeDailyMetrics.date >= cutoff)
        .where(CreativeDailyMetrics.attribution_window == "7d_click")
        .group_by(CreativeDailyMetrics.date)
        .order_by(CreativeDailyMetrics.date)
    )
    daily_trend = [
        {
            "date": r.date.isoformat(),
            "spend": float(r.spend or 0),
            "purchases": int(r.purchases or 0),
            "roas": round(float(r.roas or 0), 2),
            "ctr_pct": round(float(r.ctr or 0) * 100, 3),
        }
        for r in daily
    ]

    # Fatigue summary
    fatigue_dist = await db.execute(
        select(
            FatigueScore.fatigue_stage,
            func.count(FatigueScore.creative_id).label("count"),
        )
        .join(Creative, Creative.id == FatigueScore.creative_id)
        .where(FatigueScore.product_id == pid)
        .where(FatigueScore.calculated_date == date.today())
        .where(Creative.status == "active")
        .group_by(FatigueScore.fatigue_stage)
    )
    fatigue_by_stage = {r.fatigue_stage: r.count for r in fatigue_dist}

    return {
        "product": {"id": str(product.id), "name": product.name, "category": product.category},
        "period_days": days,
        "narrative_breakdown": narrative_breakdown,
        "daily_trend": daily_trend,
        "fatigue_distribution": fatigue_by_stage,
    }


@router.get("/products/{product_id}/gaps")
async def creative_gaps(product_id: str, db: DbDep, _: CurrentUser):
    """
    Get creative gaps — high-performing areas with insufficient creative supply.
    """
    from sqlalchemy import text
    result = await db.execute(
        text("""SELECT * FROM get_narrative_saturation(CAST(:product_id AS uuid))"""),
        {"product_id": product_id},
    )
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.get("/products/{product_id}/top-creatives")
async def top_creatives(
    product_id: str,
    db: DbDep,
    _: CurrentUser,
    days: int = Query(30),
    limit: int = Query(10, le=30),
):
    """Get top-performing creatives for a product by ROAS."""
    pid = UUID(product_id)
    cutoff = date.today() - timedelta(days=days)

    result = await db.execute(
        select(
            Creative.id,
            Creative.name,
            Creative.thumbnail_url,
            Creative.launch_date,
            func.sum(CreativeDailyMetrics.spend).label("total_spend"),
            func.avg(CreativeDailyMetrics.roas).filter(CreativeDailyMetrics.roas > 0).label("avg_roas"),
            func.avg(CreativeDailyMetrics.ctr).filter(CreativeDailyMetrics.ctr > 0).label("avg_ctr"),
            func.avg(CreativeDailyMetrics.cpa).filter(CreativeDailyMetrics.cpa > 0).label("avg_cpa"),
            func.sum(CreativeDailyMetrics.purchases).label("total_purchases"),
        )
        .join(CreativeDailyMetrics, CreativeDailyMetrics.creative_id == Creative.id)
        .where(Creative.product_id == pid)
        .where(CreativeDailyMetrics.date >= cutoff)
        .where(CreativeDailyMetrics.attribution_window == "7d_click")
        .where(CreativeDailyMetrics.spend >= 200)
        .group_by(Creative.id, Creative.name, Creative.thumbnail_url, Creative.launch_date)
        .having(func.sum(CreativeDailyMetrics.spend) >= 1000)
        .order_by(func.avg(CreativeDailyMetrics.roas).desc())
        .limit(limit)
    )

    return [
        {
            "creative_id": str(r.id),
            "name": r.name,
            "thumbnail_url": r.thumbnail_url,
            "launch_date": r.launch_date.isoformat() if r.launch_date else None,
            "total_spend": float(r.total_spend or 0),
            "avg_roas": round(float(r.avg_roas or 0), 2),
            "avg_ctr_pct": round(float(r.avg_ctr or 0) * 100, 3),
            "avg_cpa": round(float(r.avg_cpa or 0), 0),
            "total_purchases": int(r.total_purchases or 0),
        }
        for r in result
    ]
