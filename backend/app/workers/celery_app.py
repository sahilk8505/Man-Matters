from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "man_matters_cos",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # One task at a time per worker (AI tasks are heavy)
    task_soft_time_limit=300,       # 5 min soft limit
    task_time_limit=600,            # 10 min hard limit
    beat_schedule={
        "meta-sync-every-6h": {
            "task": "app.workers.tasks.sync_meta_data",
            "schedule": settings.META_SYNC_INTERVAL_HOURS * 3600,
        },
        "recalculate-fatigue-daily": {
            "task": "app.workers.tasks.recalculate_all_fatigue",
            "schedule": 86400,  # daily
        },
        "generate-insights-daily": {
            "task": "app.workers.tasks.generate_all_insights",
            "schedule": 86400,
        },
        "update-benchmarks-daily": {
            "task": "app.workers.tasks.update_product_benchmarks",
            "schedule": 86400,
        },
        "aggregate-genome-daily": {
            "task": "app.workers.tasks.aggregate_genome_patterns",
            "schedule": 86400,
        },
        "analyze-pending-creatives-every-15m": {
            "task": "app.workers.tasks.analyze_pending_creatives",
            "schedule": 900,  # every 15 minutes
        },
    },
)
