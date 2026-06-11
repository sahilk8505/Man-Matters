"""Creative Genome endpoints — pattern analysis and combinations."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select, func

from app.api.deps import DbDep, CurrentUser
from app.models.orm import GenomePattern


router = APIRouter(prefix="/genome", tags=["genome"])


@router.get("/patterns")
async def get_genome_patterns(
    db: DbDep,
    _: CurrentUser,
    product_id: Optional[str] = Query(None),
    min_creatives: int = Query(2),
    limit: int = Query(20, le=50),
    sort_by: str = Query("avg_roas", regex="^(avg_roas|win_rate|avg_ctr|total_creatives)$"),
):
    """Get top-performing genome patterns (creative building block combinations)."""
    from app.services.genome_service import get_winning_patterns

    pid = UUID(product_id) if product_id else None
    patterns = await get_winning_patterns(db, product_id=pid, min_creatives=min_creatives, limit=limit)

    # Sort by requested field
    if sort_by == "win_rate":
        patterns = sorted(patterns, key=lambda p: p.get("win_rate") or 0, reverse=True)
    elif sort_by == "avg_ctr":
        patterns = sorted(patterns, key=lambda p: p.get("avg_ctr") or 0, reverse=True)

    return patterns


@router.get("/winning-combinations")
async def winning_combinations(
    db: DbDep,
    _: CurrentUser,
    product_id: Optional[str] = Query(None),
    top_n: int = Query(5, le=20),
):
    """
    Get the specific winning creative combinations with human-readable descriptions.
    Example: "Doctor Authority Hook + Myth Busting + Reel = 4.2x ROAS, 92% win rate"
    """
    from app.services.genome_service import get_winning_patterns

    pid = UUID(product_id) if product_id else None
    patterns = await get_winning_patterns(db, product_id=pid, min_creatives=3, limit=top_n * 2)

    # Format as human-readable combinations
    combinations = []
    for p in patterns[:top_n]:
        parts = []
        if p.get("hook_type"):
            parts.append(p["hook_type"].replace("_", " ").title() + " Hook")
        if p.get("narrative_type"):
            parts.append(p["narrative_type"].replace("_", " ").title())
        if p.get("format_type"):
            parts.append(p["format_type"].replace("_", " ").title())
        if p.get("creator_type") and p["creator_type"] != "none":
            parts.append("by " + p["creator_type"].replace("_", " ").title())
        if p.get("offer_type") and p["offer_type"] != "none":
            parts.append("+ " + p["offer_type"].replace("_", " ").title() + " Offer")

        combinations.append({
            "description": " + ".join(parts) if parts else "Unclassified Pattern",
            "pattern_hash": p["pattern_hash"],
            "total_creatives": p["total_creatives"],
            "avg_roas": p.get("avg_roas"),
            "win_rate_pct": round((p.get("win_rate") or 0) * 100, 1),
            "avg_lifespan_days": p.get("avg_lifespan_days"),
            "avg_ctr_pct": round((p.get("avg_ctr") or 0) * 100, 3) if p.get("avg_ctr") else None,
            "avg_cpa": p.get("avg_cpa"),
            "total_spend": p.get("total_spend", 0),
            "total_purchases": p.get("total_purchases", 0),
            **{k: v for k, v in p.items() if k not in ("description",)},
        })

    return combinations


@router.get("/losing-patterns")
async def losing_patterns(
    db: DbDep,
    _: CurrentUser,
    product_id: Optional[str] = Query(None),
    limit: int = Query(10, le=20),
):
    """Get consistently underperforming genome patterns to avoid."""
    query = (
        select(GenomePattern)
        .where(GenomePattern.total_creatives >= 2)
        .where(GenomePattern.avg_roas.isnot(None))
        .where(GenomePattern.avg_roas < 1.5)
    )
    if product_id:
        query = query.where(GenomePattern.product_id == UUID(product_id))

    query = query.order_by(GenomePattern.avg_roas.asc()).limit(limit)
    result = await db.execute(query)
    patterns = result.scalars().all()

    return [
        {
            "pattern_hash": p.pattern_hash,
            "hook_type": p.hook_type,
            "narrative_type": p.narrative_type,
            "format_type": p.format_type,
            "creator_type": p.creator_type,
            "offer_type": p.offer_type,
            "visual_style": p.visual_style,
            "total_creatives": p.total_creatives,
            "avg_roas": float(p.avg_roas) if p.avg_roas else None,
            "avg_cpa": float(p.avg_cpa) if p.avg_cpa else None,
            "win_rate": float(p.win_rate) if p.win_rate else None,
        }
        for p in patterns
    ]


@router.get("/product-learnings/{product_id}")
async def product_learnings(product_id: str, db: DbDep, _: CurrentUser):
    """
    Comprehensive product-specific creative learnings:
    - Best patterns for this product
    - Worst patterns for this product
    - Unique patterns that work only for this product
    """
    pid = UUID(product_id)
    from app.services.genome_service import get_winning_patterns

    winners = await get_winning_patterns(db, product_id=pid, min_creatives=2, limit=10)

    losing_result = await db.execute(
        select(GenomePattern)
        .where(GenomePattern.product_id == pid)
        .where(GenomePattern.total_creatives >= 2)
        .where(GenomePattern.avg_roas < 1.5)
        .order_by(GenomePattern.avg_roas.asc())
        .limit(5)
    )
    losers = [
        {
            "hook_type": p.hook_type,
            "narrative_type": p.narrative_type,
            "format_type": p.format_type,
            "creator_type": p.creator_type,
            "avg_roas": float(p.avg_roas) if p.avg_roas else None,
            "total_creatives": p.total_creatives,
        }
        for p in losing_result.scalars()
    ]

    return {
        "product_id": product_id,
        "winning_patterns": winners[:5],
        "losing_patterns": losers,
        "key_insights": _generate_pattern_insights(winners, losers),
    }


def _generate_pattern_insights(winners, losers):
    """Generate text-based insights from pattern data."""
    insights = []

    if winners:
        top = winners[0]
        parts = []
        if top.get("hook_type"):
            parts.append(top["hook_type"].replace("_", " ").title())
        if top.get("narrative_type"):
            parts.append(top["narrative_type"].replace("_", " ").title())
        if top.get("format_type"):
            parts.append(top["format_type"].replace("_", " ").title())

        if parts and top.get("avg_roas"):
            insights.append(
                f"Best combination: {' + '.join(parts)} generates {top['avg_roas']:.1f}x ROAS "
                f"across {top['total_creatives']} creatives"
            )

    if losers:
        bottom = losers[0]
        parts = []
        if bottom.get("hook_type"):
            parts.append(bottom["hook_type"].replace("_", " ").title())
        if bottom.get("narrative_type"):
            parts.append(bottom["narrative_type"].replace("_", " ").title())

        if parts:
            insights.append(
                f"Avoid: {' + '.join(parts)} consistently underperforms "
                f"(avg ROAS: {(bottom.get('avg_roas') or 0):.1f}x)"
            )

    return insights
