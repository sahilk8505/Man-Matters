"""AI Insights endpoints."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, BackgroundTasks
from sqlalchemy import select, func, and_

from app.api.deps import DbDep, CurrentUser
from app.models.orm import Insight, Product


router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("")
async def list_insights(
    db: DbDep,
    _: CurrentUser,
    product_id: Optional[str] = Query(None),
    insight_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
):
    """List insights with filtering."""
    query = select(Insight).where(Insight.is_dismissed == False)

    if product_id:
        query = query.where(Insight.product_id == UUID(product_id))
    if insight_type:
        query = query.where(Insight.insight_type == insight_type)
    if priority:
        query = query.where(Insight.priority == priority)
    if is_read is not None:
        query = query.where(Insight.is_read == is_read)

    query = query.order_by(
        Insight.is_read.asc(),  # Unread first
        Insight.priority.asc(),  # critical first (alphabetical: critical < high < low < medium)
        Insight.created_at.desc(),
    ).limit(limit).offset(offset)

    result = await db.execute(query)
    insights = result.scalars().all()

    return [
        {
            "id": str(ins.id),
            "product_id": str(ins.product_id) if ins.product_id else None,
            "creative_id": str(ins.creative_id) if ins.creative_id else None,
            "insight_type": ins.insight_type,
            "priority": ins.priority,
            "title": ins.title,
            "body": ins.body,
            "recommended_action": ins.recommended_action,
            "action_type": ins.action_type,
            "is_read": ins.is_read,
            "is_actioned": ins.is_actioned,
            "is_dismissed": ins.is_dismissed,
            "data": ins.data,
            "created_at": ins.created_at.isoformat() if ins.created_at else None,
        }
        for ins in insights
    ]


@router.get("/count")
async def insight_counts(db: DbDep, _: CurrentUser):
    """Get counts by priority for badge display."""
    result = await db.execute(
        select(
            Insight.priority,
            func.count(Insight.id).label("count"),
        )
        .where(Insight.is_read == False)
        .where(Insight.is_dismissed == False)
        .group_by(Insight.priority)
    )

    counts = {r.priority: r.count for r in result}
    return {
        "total_unread": sum(counts.values()),
        "critical": counts.get("critical", 0),
        "high": counts.get("high", 0),
        "medium": counts.get("medium", 0),
        "low": counts.get("low", 0),
    }


@router.post("/{insight_id}/read")
async def mark_read(insight_id: str, db: DbDep, _: CurrentUser):
    ins = await db.get(Insight, UUID(insight_id))
    if ins:
        ins.is_read = True
        db.add(ins)
        await db.commit()
    return {"status": "ok"}


@router.post("/{insight_id}/dismiss")
async def dismiss(insight_id: str, db: DbDep, _: CurrentUser):
    ins = await db.get(Insight, UUID(insight_id))
    if ins:
        ins.is_dismissed = True
        db.add(ins)
        await db.commit()
    return {"status": "ok"}


@router.post("/{insight_id}/action")
async def mark_actioned(insight_id: str, db: DbDep, _: CurrentUser):
    ins = await db.get(Insight, UUID(insight_id))
    if ins:
        ins.is_actioned = True
        ins.is_read = True
        db.add(ins)
        await db.commit()
    return {"status": "ok"}


@router.post("/generate")
async def trigger_insight_generation(
    db: DbDep,
    _: CurrentUser,
    background_tasks: BackgroundTasks,
    product_id: Optional[str] = Query(None),
):
    """Manually trigger AI insight generation for a product or all products."""
    from app.workers.tasks import generate_all_insights
    generate_all_insights.delay()
    return {"status": "queued", "message": "Insight generation started in background"}
