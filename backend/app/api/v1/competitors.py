"""Competitor intelligence endpoints."""
from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, func, and_

from app.api.deps import DbDep, CurrentUser
from app.models.orm import CompetitorCreative, CompetitorEmbedding


router = APIRouter(prefix="/competitors", tags=["competitors"])

KNOWN_COMPETITORS = [
    "Beardo", "Ustraa", "The Man Company", "Bombay Shaving Company",
    "Mars by GHC", "Nourish Mantra", "Sheopal's", "Wow Skin Science",
    "Mamaearth", "mCaffeine"
]


@router.get("")
async def list_competitor_creatives(
    db: DbDep,
    _: CurrentUser,
    competitor_name: Optional[str] = Query(None),
    narrative_type: Optional[str] = Query(None),
    hook_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    min_lifespan_days: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    """List competitor creatives with filtering."""
    query = select(CompetitorCreative)

    if competitor_name:
        query = query.where(CompetitorCreative.competitor_name.ilike(f"%{competitor_name}%"))
    if narrative_type:
        query = query.where(CompetitorCreative.narrative_type == narrative_type)
    if hook_type:
        query = query.where(CompetitorCreative.hook_type == hook_type)
    if is_active is not None:
        query = query.where(CompetitorCreative.is_active == is_active)
    if min_lifespan_days:
        query = query.where(CompetitorCreative.estimated_lifespan_days >= min_lifespan_days)

    query = query.order_by(CompetitorCreative.first_seen_date.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    creatives = result.scalars().all()

    return [
        {
            "id": str(c.id),
            "competitor_name": c.competitor_name,
            "competitor_page_name": c.competitor_page_name,
            "thumbnail_url": c.thumbnail_url,
            "media_type": c.media_type,
            "headline": c.headline,
            "first_seen_date": c.first_seen_date.isoformat() if c.first_seen_date else None,
            "last_seen_date": c.last_seen_date.isoformat() if c.last_seen_date else None,
            "estimated_lifespan_days": c.estimated_lifespan_days,
            "is_active": c.is_active,
            "narrative_type": c.narrative_type,
            "hook_type": c.hook_type,
            "visual_style": c.visual_style,
            "offer_type": c.offer_type,
            "creator_type": c.creator_type,
            "emotional_trigger": c.emotional_trigger,
            "analysis_status": c.analysis_status,
        }
        for c in creatives
    ]


@router.get("/emerging-patterns")
async def emerging_patterns(db: DbDep, _: CurrentUser, days: int = Query(30, le=90)):
    """
    Identify emerging narratives/hooks that are NEW in competitor ads
    and gaining traction (long-running new ads).
    """
    cutoff = date.today() - timedelta(days=days)

    # Narratives appearing in recently launched competitor ads that are still running
    result = await db.execute(
        select(
            CompetitorCreative.narrative_type,
            func.count(CompetitorCreative.id).label("ad_count"),
            func.count(func.distinct(CompetitorCreative.competitor_name)).label("competitor_count"),
            func.avg(CompetitorCreative.estimated_lifespan_days).label("avg_lifespan"),
            func.count(CompetitorCreative.id).filter(CompetitorCreative.is_active == True).label("active_count"),
        )
        .where(CompetitorCreative.first_seen_date >= cutoff)
        .where(CompetitorCreative.narrative_type.isnot(None))
        .where(CompetitorCreative.analysis_status == "completed")
        .group_by(CompetitorCreative.narrative_type)
        .having(func.count(CompetitorCreative.id) >= 2)
        .order_by(func.count(CompetitorCreative.id).desc())
    )

    emerging_narratives = [
        {
            "narrative_type": r.narrative_type,
            "ad_count": r.ad_count,
            "competitor_count": r.competitor_count,
            "avg_lifespan_days": float(r.avg_lifespan or 0),
            "active_count": r.active_count,
            "momentum_score": round(r.ad_count * (r.active_count / max(r.ad_count, 1)) * 10, 1),
        }
        for r in result
    ]

    # Longest-running competitor ads (proven formats)
    long_running = await db.execute(
        select(CompetitorCreative)
        .where(CompetitorCreative.estimated_lifespan_days >= 14)
        .where(CompetitorCreative.analysis_status == "completed")
        .order_by(CompetitorCreative.estimated_lifespan_days.desc())
        .limit(10)
    )

    return {
        "emerging_narratives": emerging_narratives,
        "longest_running": [
            {
                "id": str(c.id),
                "competitor_name": c.competitor_name,
                "headline": c.headline,
                "narrative_type": c.narrative_type,
                "hook_type": c.hook_type,
                "offer_type": c.offer_type,
                "estimated_lifespan_days": c.estimated_lifespan_days,
                "first_seen_date": c.first_seen_date.isoformat() if c.first_seen_date else None,
                "is_active": c.is_active,
            }
            for c in long_running.scalars()
        ],
    }


@router.get("/by-competitor")
async def by_competitor_summary(db: DbDep, _: CurrentUser):
    """Summarize ad activity per competitor."""
    result = await db.execute(
        select(
            CompetitorCreative.competitor_name,
            func.count(CompetitorCreative.id).label("total_ads"),
            func.count(CompetitorCreative.id).filter(CompetitorCreative.is_active == True).label("active_ads"),
            func.max(CompetitorCreative.first_seen_date).label("latest_ad"),
            func.avg(CompetitorCreative.estimated_lifespan_days).label("avg_lifespan"),
        )
        .where(CompetitorCreative.analysis_status == "completed")
        .group_by(CompetitorCreative.competitor_name)
        .order_by(func.count(CompetitorCreative.id).desc())
    )

    return [
        {
            "competitor_name": r.competitor_name,
            "total_ads": r.total_ads,
            "active_ads": r.active_ads,
            "latest_ad_date": r.latest_ad.isoformat() if r.latest_ad else None,
            "avg_lifespan_days": float(r.avg_lifespan or 0),
        }
        for r in result
    ]


@router.post("/search-ad-library")
async def search_ad_library(
    db: DbDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    search_terms: List[str],
    competitor_name: str,
):
    """
    Search Meta Ad Library and ingest competitor creatives.
    Runs analysis in background.
    """
    from app.services.meta_client import meta_client

    ads = meta_client.search_ad_library(search_terms=search_terms)
    new_count = 0

    for ad in ads:
        meta_ad_id = ad.get("id")
        if not meta_ad_id:
            continue

        # Check if already exists
        existing = await db.scalar(
            select(CompetitorCreative).where(CompetitorCreative.meta_ad_id == meta_ad_id)
        )
        if existing:
            continue

        # Build headline from creative bodies
        creative_bodies = ad.get("ad_creative_bodies", [])
        headline = creative_bodies[0] if creative_bodies else ""
        titles = ad.get("ad_creative_link_titles", [])
        title = titles[0] if titles else ""

        # Estimate lifespan
        start = ad.get("ad_delivery_start_time")
        end = ad.get("ad_delivery_stop_time")
        lifespan = None
        if start and end:
            from datetime import datetime
            try:
                s = datetime.fromisoformat(start.replace("Z", "+00:00"))
                e = datetime.fromisoformat(end.replace("Z", "+00:00"))
                lifespan = (e - s).days
            except Exception:
                pass
        elif start:
            from datetime import datetime
            try:
                s = datetime.fromisoformat(start.replace("Z", "+00:00"))
                lifespan = (datetime.now(s.tzinfo) - s).days
            except Exception:
                pass

        cc = CompetitorCreative(
            competitor_name=competitor_name,
            competitor_page_id=ad.get("page_id"),
            competitor_page_name=ad.get("page_name"),
            meta_ad_id=meta_ad_id,
            ad_archive_url=ad.get("ad_snapshot_url"),
            headline=title or headline[:500],
            body_text=headline[:1000],
            first_seen_date=date.today(),
            estimated_lifespan_days=lifespan,
            is_active=not bool(ad.get("ad_delivery_stop_time")),
            analysis_status="pending",
        )
        db.add(cc)
        new_count += 1

    await db.commit()

    # Queue analysis for new creatives
    if new_count > 0:
        background_tasks.add_task(_analyze_pending_competitors, db)

    return {"ingested": new_count, "total_found": len(ads)}


async def _analyze_pending_competitors(db):
    """Background task to analyze pending competitor creatives."""
    from app.services.creative_analyzer import analyze_competitor_creative
    from app.services.embedding_service import generate_competitor_embedding
    from datetime import datetime, timezone

    pending = await db.execute(
        select(CompetitorCreative)
        .where(CompetitorCreative.analysis_status == "pending")
        .limit(10)
    )
    for cc in pending.scalars():
        try:
            metadata = await analyze_competitor_creative(
                media_url=cc.media_url,
                media_type=cc.media_type or "image",
                headline=cc.headline or "",
                body_text=cc.body_text or "",
            )
            cc.narrative_type = metadata.get("narrative_type")
            cc.hook_type = metadata.get("hook_type")
            cc.visual_style = metadata.get("visual_style")
            cc.offer_type = metadata.get("offer_type")
            cc.creator_type = metadata.get("creator_type")
            cc.emotional_trigger = metadata.get("emotional_trigger")
            cc.human_presence = metadata.get("human_presence")
            cc.trust_signal = metadata.get("trust_signal")
            cc.raw_gemini_response = metadata
            cc.analysis_status = "completed"
            cc.analyzed_at = datetime.now(timezone.utc)
            db.add(cc)
            await db.flush()

            await generate_competitor_embedding(db, cc.id, metadata, cc.headline or "", cc.body_text or "")
        except Exception as e:
            cc.analysis_status = "failed"
            db.add(cc)

    await db.commit()
