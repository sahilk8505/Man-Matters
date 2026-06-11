"""Meta sync and upload endpoints."""
from datetime import date, timedelta
from typing import List, Optional
import csv
import io

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from sqlalchemy import select, desc

from app.api.deps import DbDep, CurrentUser
from app.models.orm import SyncLog, Creative, Product, CreativeDailyMetrics


router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/meta/trigger")
async def trigger_meta_sync(
    db: DbDep,
    _: CurrentUser,
    background_tasks: BackgroundTasks,
    lookback_days: int = Query(7, le=90),
):
    """Trigger a manual Meta Ads data sync."""
    from app.workers.tasks import sync_meta_data
    sync_meta_data.delay()
    return {"status": "queued", "message": f"Meta sync started for last {lookback_days} days"}


@router.get("/logs")
async def sync_logs(db: DbDep, _: CurrentUser, limit: int = Query(20, le=100)):
    """Get recent sync logs."""
    result = await db.execute(
        select(SyncLog)
        .order_by(SyncLog.started_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()

    return [
        {
            "id": str(log.id),
            "sync_type": log.sync_type,
            "status": log.status,
            "account_id": log.account_id,
            "records_fetched": log.records_fetched,
            "records_processed": log.records_processed,
            "records_failed": log.records_failed,
            "error_message": log.error_message,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "duration_seconds": (
                (log.completed_at - log.started_at).total_seconds()
                if log.completed_at and log.started_at else None
            ),
        }
        for log in logs
    ]


@router.post("/upload/csv-metrics")
async def upload_csv_metrics(
    db: DbDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    product_id: str = Form(...),
    attribution_window: str = Form("7d_click"),
):
    """
    Upload a Meta Ads export CSV with performance metrics.

    Expected CSV columns:
    Ad ID, Ad Name, Date, Spend, Impressions, Reach, Frequency, Clicks, CTR,
    Link Clicks, CPC, CPM, Purchases, Purchase Value, ROAS,
    Video 3s Views, Video 25% Views, Video 75% Views
    """
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    content = await file.read()
    text = content.decode("utf-8-sig")  # Handle BOM
    reader = csv.DictReader(io.StringIO(text))

    # Column name normalization map (Meta export uses various column names)
    COL_MAP = {
        "ad id": "meta_ad_id",
        "ad name": "name",
        "reporting starts": "date",
        "date": "date",
        "amount spent (inr)": "spend",
        "amount spent": "spend",
        "impressions": "impressions",
        "reach": "reach",
        "frequency": "frequency",
        "clicks (all)": "clicks",
        "ctr (all)": "ctr",
        "link clicks": "link_clicks",
        "ctr (link click-through rate)": "link_ctr",
        "cost per link click": "cpc",
        "cpm (cost per 1,000 impressions)": "cpm",
        "purchases": "purchases",
        "purchase roas (return on ad spend)": "roas",
        "3-second video views": "three_sec_video_views",
        "video plays at 25%": "video_p25_watched",
        "video plays at 75%": "video_p75_watched",
    }

    rows_processed = 0
    rows_failed = 0

    for row in reader:
        try:
            # Normalize column names
            normalized = {}
            for k, v in row.items():
                k_lower = k.strip().lower()
                if k_lower in COL_MAP:
                    normalized[COL_MAP[k_lower]] = v.strip()

            if not normalized.get("meta_ad_id"):
                continue

            # Find or create creative
            creative = await db.scalar(
                select(Creative).where(Creative.meta_ad_id == normalized["meta_ad_id"])
            )
            if not creative:
                creative = Creative(
                    meta_ad_id=normalized["meta_ad_id"],
                    product_id=product.id,
                    name=normalized.get("name", normalized["meta_ad_id"]),
                    status="active",
                    source="csv",
                    analysis_status="pending",
                )
                db.add(creative)
                await db.flush()

            # Parse date
            date_str = normalized.get("date", "")
            try:
                from datetime import datetime
                metrics_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except Exception:
                try:
                    metrics_date = datetime.strptime(date_str, "%d/%m/%Y").date()
                except Exception:
                    continue

            def to_float(v, default=0.0):
                try:
                    return float(str(v).replace(",", "").replace("%", "")) if v else default
                except Exception:
                    return default

            def to_int(v, default=0):
                try:
                    return int(float(str(v).replace(",", ""))) if v else default
                except Exception:
                    return default

            # Check existing
            existing = await db.scalar(
                select(CreativeDailyMetrics)
                .where(CreativeDailyMetrics.creative_id == creative.id)
                .where(CreativeDailyMetrics.date == metrics_date)
                .where(CreativeDailyMetrics.attribution_window == attribution_window)
            )

            spend = to_float(normalized.get("spend"))
            impressions = to_int(normalized.get("impressions"))
            link_clicks = to_int(normalized.get("link_clicks"))
            purchases = to_int(normalized.get("purchases"))
            purchase_value = spend * to_float(normalized.get("roas"))
            p25 = to_int(normalized.get("video_p25_watched"))
            p75 = to_int(normalized.get("video_p75_watched"))
            three_sec = to_int(normalized.get("three_sec_video_views"))
            ctr_raw = to_float(normalized.get("ctr"))
            ctr = ctr_raw / 100 if ctr_raw > 1 else ctr_raw  # Normalize to decimal

            metrics_data = {
                "spend": spend,
                "impressions": impressions,
                "reach": to_int(normalized.get("reach")),
                "frequency": to_float(normalized.get("frequency")),
                "clicks": to_int(normalized.get("clicks")),
                "ctr": ctr,
                "link_clicks": link_clicks,
                "link_ctr": link_clicks / impressions if impressions > 0 else 0,
                "cpc": to_float(normalized.get("cpc")),
                "cpm": to_float(normalized.get("cpm")),
                "purchases": purchases,
                "purchase_value": purchase_value,
                "cpa": spend / purchases if purchases > 0 else 0,
                "roas": to_float(normalized.get("roas")),
                "conversion_rate": purchases / link_clicks if link_clicks > 0 else 0,
                "video_p25_watched": p25,
                "video_p75_watched": p75,
                "three_sec_video_views": three_sec,
                "hook_rate": three_sec / impressions if impressions > 0 else 0,
                "hold_rate": p75 / p25 if p25 > 0 else 0,
                "thumb_stop_rate": three_sec / impressions if impressions > 0 else 0,
                "attribution_window": attribution_window,
            }

            if existing:
                for k, v in metrics_data.items():
                    setattr(existing, k, v)
                db.add(existing)
            else:
                m = CreativeDailyMetrics(
                    creative_id=creative.id,
                    product_id=product.id,
                    date=metrics_date,
                    **metrics_data,
                )
                db.add(m)

            rows_processed += 1

        except Exception as e:
            rows_failed += 1

    await db.commit()

    # Queue analysis for any pending creatives
    from app.workers.tasks import analyze_pending_creatives
    analyze_pending_creatives.delay()

    # Create sync log
    log = SyncLog(
        sync_type="csv_upload",
        status="completed",
        records_processed=rows_processed,
        records_failed=rows_failed,
        records_fetched=rows_processed + rows_failed,
    )
    from datetime import datetime, timezone
    log.completed_at = datetime.now(timezone.utc)
    db.add(log)
    await db.commit()

    return {
        "status": "completed",
        "rows_processed": rows_processed,
        "rows_failed": rows_failed,
        "product_id": product_id,
    }


@router.post("/upload/creative")
async def upload_creative_file(
    db: DbDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    product_id: str = Form(...),
    headline: str = Form(""),
    body_text: str = Form(""),
    cta_type: str = Form(""),
    launch_date: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    """
    Upload a creative asset (image or video) for a product.
    Stores in Supabase, creates creative record, queues Gemini analysis.
    """
    from app.core.config import settings as cfg
    import uuid

    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Determine media type
    content_type = file.content_type or ""
    if "video" in content_type:
        media_type = "video"
    elif "image" in content_type:
        media_type = "image"
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # Upload to Supabase Storage
    from supabase import create_client
    supabase = create_client(cfg.SUPABASE_URL, cfg.SUPABASE_SERVICE_KEY)

    file_content = await file.read()
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
    storage_path = f"creatives/{product.slug}/{uuid.uuid4()}.{ext}"

    try:
        supabase.storage.from_(cfg.SUPABASE_STORAGE_BUCKET).upload(
            storage_path, file_content, {"content-type": content_type}
        )
        storage_url = supabase.storage.from_(cfg.SUPABASE_STORAGE_BUCKET).get_public_url(storage_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {e}")

    # Create creative record
    launch = None
    if launch_date:
        from datetime import datetime
        launch = datetime.strptime(launch_date, "%Y-%m-%d").date()

    creative = Creative(
        product_id=product.id,
        name=file.filename or f"{product.name} Creative",
        media_type=media_type,
        storage_url=storage_url,
        headline=headline or None,
        body_text=body_text or None,
        cta_type=cta_type or None,
        launch_date=launch,
        status="active",
        source="manual",
        analysis_status="pending",
    )
    db.add(creative)
    await db.commit()
    await db.refresh(creative)

    # Queue analysis
    from app.workers.tasks import analyze_single_creative
    analyze_single_creative.delay(str(creative.id))

    return {
        "creative_id": str(creative.id),
        "storage_url": storage_url,
        "status": "analyzing",
        "message": "Creative uploaded. Gemini analysis queued.",
    }
