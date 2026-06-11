"""
Man Matters Creative Operating System — FastAPI Backend
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.database import init_db


# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME}")
    await init_db()
    logger.info("Database connection established")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    description="Creative Intelligence Platform for Man Matters Meta Ads",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Register routers
from app.api.v1.auth import router as auth_router
from app.api.v1.products import router as products_router
from app.api.v1.creatives import router as creatives_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.fatigue import router as fatigue_router
from app.api.v1.predictions import router as predictions_router
from app.api.v1.competitors import router as competitors_router
from app.api.v1.genome import router as genome_router
from app.api.v1.insights import router as insights_router
from app.api.v1.sync import router as sync_router

prefix = settings.API_PREFIX

app.include_router(auth_router, prefix=prefix)
app.include_router(products_router, prefix=prefix)
app.include_router(creatives_router, prefix=prefix)
app.include_router(analytics_router, prefix=prefix)
app.include_router(fatigue_router, prefix=prefix)
app.include_router(predictions_router, prefix=prefix)
app.include_router(competitors_router, prefix=prefix)
app.include_router(genome_router, prefix=prefix)
app.include_router(insights_router, prefix=prefix)
app.include_router(sync_router, prefix=prefix)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": settings.APP_NAME}


@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
    }
