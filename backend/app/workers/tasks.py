"""
Celery Tasks — Man Matters Creative OS

Background task pipeline:
1. sync_meta_data: Pull latest metrics from Meta API
2. analyze_pending_creatives: Run Gemini on unanalyzed creatives
3. recalculate_all_fatigue: Refresh fatigue scores for all active creatives
4. generate_all_insights: Run AI insight generation for each product
5. update_product_benchmarks: Recalculate product benchmark percentiles
6. aggregate_genome_patterns: Update genome pattern performance stats
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any, Dict, List

from celery import shared_task
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.models.orm import (
    Creative, Product, CreativeDailyMetrics,
    FatigueScore, ProductBenchmark, SyncLog
)
from app.models.genome import MetaAccount
from app.workers.celery_app import celery_app


logger = logging.getLogger(__name__)


def run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="app.workers.tasks.analyze_single_creative")
def analyze_single_creative(self, creative_id: str):
    """
    Analyze a single creative with Gemini.
    Triggered immediately after creative upload or Meta sync discovers new creatives.
    """
    return run_async(_analyze_single_creative_async(creative_id))


async def _analyze_single_creative_async(creative_id: str):
    from app.services.creative_analyzer import analyze_creative
    from app.services.embedding_service import generate_and_store_embedding
    from app.services.genome_service import extract_creative_genome
    import uuid

    async with AsyncSessionLocal() as db:
        creative = await db.get(Creative, uuid.UUID(creative_id))
        if not creative:
            logger.error(f"Creative {creative_id} not found")
            return {"status": "not_found"}

        # Mark as processing
        creative.analysis_status = "processing"
        db.add(creative)
        await db.commit()

        try:
            # Run Gemini analysis
            metadata_dict = await analyze_creative(
                media_url=creative.media_url,
                media_type=creative.media_type or "image",
                headline=creative.headline or "",
                body_text=creative.body_text or "",
                cta_type=creative.cta_type or "",
                storage_url=creative.storage_url,
            )

            # Store metadata
            from app.models.orm import CreativeMetadata
            existing_meta = await db.scalar(
                select(CreativeMetadata).where(CreativeMetadata.creative_id == creative.id)
            )

            if existing_meta:
                for key, value in metadata_dict.items():
                    if hasattr(existing_meta, key) and key not in ("id", "creative_id"):
                        setattr(existing_meta, key, value)
                db.add(existing_meta)
            else:
                clean = {k: v for k, v in metadata_dict.items() if hasattr(CreativeMetadata, k)}
                meta = CreativeMetadata(creative_id=creative.id, **clean)
                db.add(meta)

            await db.flush()

            # Generate embeddings
            await generate_and_store_embedding(
                db=db,
                creative_id=creative.id,
                metadata=metadata_dict,
                headline=creative.headline or "",
                body_text=creative.body_text or "",
            )

            # Update taxonomy IDs (narrative, hook, archetype) based on analysis
            await _update_creative_taxonomy(db, creative, metadata_dict)

            # Extract genome pattern
            await extract_creative_genome(db, creative.id, creative.product_id)

            # Mark complete
            from datetime import datetime, timezone
            creative.analysis_status = "completed"
            creative.analyzed_at = datetime.now(timezone.utc)
            creative.analysis_error = None
            db.add(creative)
            await db.commit()

            logger.info(f"Creative {creative_id} analyzed successfully")
            return {"status": "completed", "creative_id": creative_id}

        except Exception as e:
            logger.exception(f"Failed to analyze creative {creative_id}: {e}")
            creative.analysis_status = "failed"
            creative.analysis_error = str(e)[:500]
            db.add(creative)
            await db.commit()
            return {"status": "failed", "error": str(e)}


async def _update_creative_taxonomy(db, creative: Creative, metadata: Dict):
    """Link creative to narrative, hook, archetype records based on AI analysis."""
    from app.models.orm import Narrative, Hook, Archetype

    narrative_type = metadata.get("narrative_type")
    hook_type = metadata.get("hook_type")

    if narrative_type:
        narrative = await db.scalar(
            select(Narrative).where(Narrative.narrative_type == narrative_type)
        )
        if narrative:
            creative.narrative_id = narrative.id

    if hook_type:
        hook = await db.scalar(
            select(Hook).where(Hook.hook_type == hook_type)
        )
        if hook:
            creative.hook_id = hook.id

    db.add(creative)
    await db.flush()


@celery_app.task(bind=True, name="app.workers.tasks.analyze_pending_creatives")
def analyze_pending_creatives(self):
    """Batch process all creatives with pending analysis status."""
    return run_async(_analyze_pending_async())


async def _analyze_pending_async():
    async with AsyncSessionLocal() as db:
        pending = await db.execute(
            select(Creative.id)
            .where(Creative.analysis_status == "pending")
            .limit(20)  # Process 20 at a time
        )
        creative_ids = [str(row.id) for row in pending]

        for cid in creative_ids:
            # Queue individual tasks
            analyze_single_creative.delay(cid)

        logger.info(f"Queued {len(creative_ids)} creatives for analysis")
        return {"queued": len(creative_ids)}


@celery_app.task(bind=True, name="app.workers.tasks.sync_meta_data")
def sync_meta_data(self):
    """Pull latest Meta Ads metrics for all active accounts."""
    return run_async(_sync_meta_async())


async def _sync_meta_async():
    from app.services.meta_client import meta_client
    from app.models.genome import MetaAccount

    async with AsyncSessionLocal() as db:
        # Create sync log
        sync_log = SyncLog(sync_type="meta_api", status="running")
        db.add(sync_log)
        await db.commit()

        try:
            # Get active accounts
            accounts = await db.execute(
                select(MetaAccount).where(MetaAccount.is_active == True)
            )
            account_list = accounts.scalars().all()

            if not account_list:
                logger.warning("No active Meta accounts configured")
                return {"status": "no_accounts"}

            date_end = date.today()
            date_start = date_end - timedelta(days=settings.META_SYNC_LOOKBACK_DAYS)

            total_fetched = 0
            total_processed = 0
            total_failed = 0

            for account in account_list:
                try:
                    # Fetch insights
                    insights = meta_client.get_insights(
                        account_id=account.account_id,
                        date_start=date_start,
                        date_stop=date_end,
                        attribution_window="7d_click",
                    )
                    total_fetched += len(insights)

                    # Get creative-to-product mapping
                    creative_map = await _build_creative_map(db, account.account_id)

                    # Upsert metrics
                    for insight in insights:
                        try:
                            creative_id = creative_map.get(insight["meta_ad_id"])
                            if not creative_id:
                                # Try to create/find the creative
                                creative_id = await _ensure_creative_exists(
                                    db, insight, account.account_id
                                )

                            if creative_id:
                                await _upsert_daily_metrics(db, creative_id, insight)
                                total_processed += 1
                        except Exception as e:
                            logger.error(f"Failed to process insight row: {e}")
                            total_failed += 1

                    # Update last synced
                    account.last_synced_at = date.today()
                    db.add(account)
                    await db.commit()

                except Exception as e:
                    logger.error(f"Failed to sync account {account.account_id}: {e}")

            # Update sync log
            sync_log.status = "completed"
            sync_log.records_fetched = total_fetched
            sync_log.records_processed = total_processed
            sync_log.records_failed = total_failed
            from datetime import datetime, timezone
            sync_log.completed_at = datetime.now(timezone.utc)
            db.add(sync_log)
            await db.commit()

            logger.info(f"Meta sync complete: {total_processed}/{total_fetched} records processed")
            return {
                "status": "completed",
                "fetched": total_fetched,
                "processed": total_processed,
                "failed": total_failed,
            }

        except Exception as e:
            sync_log.status = "failed"
            sync_log.error_message = str(e)
            db.add(sync_log)
            await db.commit()
            raise


async def _build_creative_map(db, account_id: str) -> Dict[str, str]:
    """Build a mapping of meta_ad_id → creative_id for quick lookup."""
    result = await db.execute(
        select(Creative.meta_ad_id, Creative.id)
        .where(Creative.meta_account_id == account_id)
        .where(Creative.meta_ad_id.isnot(None))
    )
    return {row.meta_ad_id: str(row.id) for row in result}


async def _ensure_creative_exists(db, insight: Dict, account_id: str) -> Any:
    """Create a minimal creative record if it doesn't exist yet."""
    from app.models.orm import Product
    meta_ad_id = insight.get("meta_ad_id")
    if not meta_ad_id:
        return None

    # Can't create without product association; skip
    # In practice, creatives should be pre-synced from ad management
    return None


async def _upsert_daily_metrics(db, creative_id: str, insight: Dict):
    """Insert or update daily metrics for a creative."""
    import uuid
    from sqlalchemy.dialects.postgresql import insert

    creative = await db.get(Creative, uuid.UUID(creative_id))
    if not creative:
        return

    metrics_date = date.fromisoformat(insight["date"]) if isinstance(insight["date"], str) else insight["date"]

    # Check if record exists
    existing = await db.scalar(
        select(CreativeDailyMetrics)
        .where(CreativeDailyMetrics.creative_id == creative.id)
        .where(CreativeDailyMetrics.date == metrics_date)
        .where(CreativeDailyMetrics.attribution_window == insight.get("attribution_window", "7d_click"))
    )

    if existing:
        for key, value in insight.items():
            if hasattr(existing, key) and key not in ("creative_id", "product_id", "date", "attribution_window"):
                setattr(existing, key, value)
        db.add(existing)
    else:
        metrics = CreativeDailyMetrics(
            creative_id=creative.id,
            product_id=creative.product_id,
            date=metrics_date,
            **{k: v for k, v in insight.items()
               if k not in ("meta_ad_id", "meta_campaign_id", "meta_adset_id") and hasattr(CreativeDailyMetrics, k)}
        )
        db.add(metrics)

    await db.flush()


@celery_app.task(bind=True, name="app.workers.tasks.recalculate_all_fatigue")
def recalculate_all_fatigue(self):
    """Recalculate fatigue scores for all active creatives."""
    return run_async(_recalculate_fatigue_async())


async def _recalculate_fatigue_async():
    from app.services.fatigue_engine import calculate_fatigue_score, DailyMetricRow
    import uuid

    async with AsyncSessionLocal() as db:
        # Get all active creatives
        active = await db.execute(
            select(Creative)
            .join(Product, Product.id == Creative.product_id)
            .where(Creative.status == "active")
            .where(Creative.launch_date.isnot(None))
        )
        creatives = active.scalars().all()

        updated = 0
        for creative in creatives:
            try:
                # Get format type
                format_type = "default"
                if creative.format_id:
                    from app.models.orm import Format
                    fmt = await db.get(Format, creative.format_id)
                    format_type = fmt.format_type if fmt else "default"

                # Get daily metrics (last 60 days)
                cutoff = date.today() - timedelta(days=60)
                metrics_result = await db.execute(
                    select(CreativeDailyMetrics)
                    .where(CreativeDailyMetrics.creative_id == creative.id)
                    .where(CreativeDailyMetrics.date >= cutoff)
                    .where(CreativeDailyMetrics.attribution_window == "7d_click")
                    .order_by(CreativeDailyMetrics.date)
                )
                metrics_rows = metrics_result.scalars().all()

                # Convert to DailyMetricRow
                metric_objects = [
                    DailyMetricRow(
                        date=m.date,
                        spend=float(m.spend or 0),
                        ctr=float(m.ctr or 0),
                        link_ctr=float(m.link_ctr or 0),
                        cpc=float(m.cpc or 0),
                        cpm=float(m.cpm or 0),
                        cpa=float(m.cpa or 0),
                        roas=float(m.roas or 0),
                        hook_rate=float(m.hook_rate or 0),
                        hold_rate=float(m.hold_rate or 0),
                        thumb_stop_rate=float(m.thumb_stop_rate or 0),
                        frequency=float(m.frequency or 0),
                        purchases=int(m.purchases or 0),
                        conversion_rate=float(m.conversion_rate or 0),
                        impressions=int(m.impressions or 0),
                    )
                    for m in metrics_rows
                ]

                if not metric_objects:
                    continue

                # Calculate fatigue
                result = calculate_fatigue_score(metric_objects, format_type=format_type)

                # Upsert score
                today = date.today()
                existing = await db.scalar(
                    select(FatigueScore)
                    .where(FatigueScore.creative_id == creative.id)
                    .where(FatigueScore.calculated_date == today)
                )

                score_data = {
                    "fatigue_score": result.fatigue_score,
                    "fatigue_stage": result.fatigue_stage,
                    "ctr_decay_score": result.component_scores.get("ctr_decay", 0),
                    "cpc_inflation_score": result.component_scores.get("cpc_inflation", 0),
                    "cpm_inflation_score": result.component_scores.get("cpm_inflation", 0),
                    "cpa_inflation_score": result.component_scores.get("cpa_inflation", 0),
                    "roas_decay_score": result.component_scores.get("roas_decay", 0),
                    "hook_decay_score": result.component_scores.get("hook_decay", 0),
                    "hold_decay_score": result.component_scores.get("hold_decay", 0),
                    "frequency_score": result.component_scores.get("frequency", 0),
                    "conversion_decay_score": result.component_scores.get("conversion_decay", 0),
                    "days_since_launch": result.days_since_launch,
                    "days_to_peak": result.days_to_peak,
                    "expected_remaining_days": result.expected_remaining_days,
                    "confidence_score": result.confidence,
                    "baseline_ctr": result.baseline_ctr,
                    "baseline_cpc": result.baseline_cpc,
                    "baseline_cpm": result.baseline_cpm,
                    "baseline_cpa": result.baseline_cpa,
                    "baseline_roas": result.baseline_roas,
                    "baseline_hook_rate": result.baseline_hook_rate,
                    "current_frequency": result.current_frequency,
                }

                if existing:
                    for k, v in score_data.items():
                        setattr(existing, k, v)
                    db.add(existing)
                else:
                    score = FatigueScore(
                        creative_id=creative.id,
                        product_id=creative.product_id,
                        calculated_date=today,
                        **score_data,
                    )
                    db.add(score)

                # Update creative lifecycle dates
                if result.fatigue_stage in ("fatiguing", "fatigued") and not creative.fatigue_start_date:
                    creative.fatigue_start_date = today
                    db.add(creative)

                # Auto-generate fatigue alert insights for fatigued creatives
                if result.fatigue_stage == "fatigued" and result.fatigue_score > 80:
                    from app.services.insight_generator import create_fatigue_alert
                    await create_fatigue_alert(db, creative, result)

                updated += 1

            except Exception as e:
                logger.error(f"Failed to calculate fatigue for creative {creative.id}: {e}")

        await db.commit()
        logger.info(f"Fatigue recalculated for {updated}/{len(creatives)} active creatives")
        return {"updated": updated, "total": len(creatives)}


@celery_app.task(bind=True, name="app.workers.tasks.generate_all_insights")
def generate_all_insights(self):
    """Generate daily AI insights for all products."""
    return run_async(_generate_insights_async())


async def _generate_insights_async():
    from app.services.insight_generator import generate_product_insights, generate_global_insights
    from app.models.orm import Insight

    async with AsyncSessionLocal() as db:
        products = await db.execute(
            select(Product).where(Product.is_active == True)
        )
        product_list = products.scalars().all()

        total_insights = 0
        for product in product_list:
            try:
                insights = await generate_product_insights(db, product)
                for insight_data in insights:
                    from datetime import datetime, timezone, timedelta as td
                    import uuid
                    ins = Insight(
                        **{k: (uuid.UUID(v) if k in ("product_id", "creative_id") and v else v)
                           for k, v in insight_data.items()},
                        valid_until=datetime.now(timezone.utc) + td(days=7),
                    )
                    db.add(ins)
                total_insights += len(insights)
            except Exception as e:
                logger.error(f"Failed to generate insights for {product.name}: {e}")

        # Global insights
        global_insights = await generate_global_insights(db)
        for ins_data in global_insights:
            import uuid
            from datetime import datetime, timezone, timedelta as td
            ins = Insight(
                **{k: (uuid.UUID(v) if k in ("product_id", "creative_id") and v else v)
                   for k, v in ins_data.items()},
                valid_until=datetime.now(timezone.utc) + td(days=7),
            )
            db.add(ins)
        total_insights += len(global_insights)

        await db.commit()
        logger.info(f"Generated {total_insights} insights")
        return {"total_insights": total_insights}


@celery_app.task(bind=True, name="app.workers.tasks.update_product_benchmarks")
def update_product_benchmarks(self):
    """Recalculate product benchmark percentiles (p25, p50, p75)."""
    return run_async(_update_benchmarks_async())


async def _update_benchmarks_async():
    import numpy as np
    from sqlalchemy import text

    async with AsyncSessionLocal() as db:
        products = await db.execute(select(Product).where(Product.is_active == True))
        product_list = products.scalars().all()

        for product in product_list:
            try:
                cutoff = date.today() - timedelta(days=30)

                # Get all metrics for this product in window
                metrics = await db.execute(
                    select(
                        CreativeDailyMetrics.roas,
                        CreativeDailyMetrics.ctr,
                        CreativeDailyMetrics.cpc,
                        CreativeDailyMetrics.cpm,
                        CreativeDailyMetrics.cpa,
                        CreativeDailyMetrics.hook_rate,
                        CreativeDailyMetrics.hold_rate,
                        CreativeDailyMetrics.frequency,
                    )
                    .where(CreativeDailyMetrics.product_id == product.id)
                    .where(CreativeDailyMetrics.date >= cutoff)
                    .where(CreativeDailyMetrics.attribution_window == "7d_click")
                    .where(CreativeDailyMetrics.spend >= 100)
                )
                rows = metrics.all()
                if not rows:
                    continue

                def pct(values, p):
                    v = [float(x) for x in values if x and float(x) > 0]
                    return float(np.percentile(v, p)) if v else None

                roas_vals = [r.roas for r in rows]
                ctr_vals = [r.ctr for r in rows]
                cpc_vals = [r.cpc for r in rows]
                cpm_vals = [r.cpm for r in rows]
                cpa_vals = [r.cpa for r in rows]

                existing = await db.scalar(
                    select(ProductBenchmark)
                    .where(ProductBenchmark.product_id == product.id)
                    .where(ProductBenchmark.period_days == 30)
                )

                benchmark_data = {
                    "median_ctr": pct(ctr_vals, 50),
                    "median_cpc": pct(cpc_vals, 50),
                    "median_cpm": pct(cpm_vals, 50),
                    "median_cpa": pct(cpa_vals, 50),
                    "median_roas": pct(roas_vals, 50),
                    "winner_roas_threshold": pct(roas_vals, 75),
                    "winner_ctr_threshold": pct(ctr_vals, 75),
                    "winner_cpa_threshold": pct(cpa_vals, 25),  # lower CPA = better
                    "loser_roas_threshold": pct(roas_vals, 25),
                    "loser_ctr_threshold": pct(ctr_vals, 25),
                    "loser_cpa_threshold": pct(cpa_vals, 75),
                }

                if existing:
                    for k, v in benchmark_data.items():
                        setattr(existing, k, v)
                    from datetime import datetime, timezone
                    existing.calculated_at = datetime.now(timezone.utc)
                    db.add(existing)
                else:
                    bench = ProductBenchmark(
                        product_id=product.id,
                        period_days=30,
                        **benchmark_data,
                    )
                    db.add(bench)

            except Exception as e:
                logger.error(f"Failed to update benchmarks for {product.name}: {e}")

        await db.commit()
        logger.info(f"Benchmarks updated for {len(product_list)} products")
        return {"products_updated": len(product_list)}


@celery_app.task(bind=True, name="app.workers.tasks.aggregate_genome_patterns")
def aggregate_genome_patterns(self):
    """Aggregate genome pattern performance stats."""
    return run_async(_aggregate_genome_async())


async def _aggregate_genome_async():
    from app.services.genome_service import aggregate_genome_performance

    async with AsyncSessionLocal() as db:
        products = await db.execute(select(Product).where(Product.is_active == True))
        product_list = products.scalars().all()

        total = 0
        for product in product_list:
            try:
                count = await aggregate_genome_performance(db, product.id)
                total += count
            except Exception as e:
                logger.error(f"Genome aggregation failed for {product.name}: {e}")

        await db.commit()
        return {"patterns_updated": total}
