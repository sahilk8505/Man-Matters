"""SQLAlchemy ORM models for Man Matters Creative OS."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, Enum, Float,
    ForeignKey, Index, Integer, Numeric, String, Text, ARRAY,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creatives: Mapped[List["Creative"]] = relationship(back_populates="product")
    benchmarks: Mapped[List["ProductBenchmark"]] = relationship(back_populates="product")


# ---------------------------------------------------------------------------
# Taxonomy
# ---------------------------------------------------------------------------

class Narrative(Base):
    __tablename__ = "narratives"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    narrative_type: Mapped[Optional[str]] = mapped_column(String(100))
    is_auto_discovered: Mapped[bool] = mapped_column(Boolean, default=False)
    example_hook: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Hook(Base):
    __tablename__ = "hooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    hook_type: Mapped[Optional[str]] = mapped_column(String(50))
    example: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Format(Base):
    __tablename__ = "formats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    format_type: Mapped[str] = mapped_column(String(50), nullable=False)
    primary_metrics: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    uses_video_metrics: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Archetype(Base):
    __tablename__ = "archetypes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    typical_hook_type: Mapped[Optional[str]] = mapped_column(String(50))
    typical_narrative: Mapped[Optional[str]] = mapped_column(String(100))
    typical_format: Mapped[Optional[str]] = mapped_column(String(50))
    typical_creator: Mapped[Optional[str]] = mapped_column(String(50))
    is_auto_discovered: Mapped[bool] = mapped_column(Boolean, default=False)
    cluster_id: Mapped[Optional[int]] = mapped_column(Integer)
    centroid_embedding = mapped_column(Vector(768))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------------
# Creative (master)
# ---------------------------------------------------------------------------

class Creative(Base):
    __tablename__ = "creatives"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    meta_ad_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    meta_campaign_id: Mapped[Optional[str]] = mapped_column(String(100))
    meta_adset_id: Mapped[Optional[str]] = mapped_column(String(100))
    meta_account_id: Mapped[Optional[str]] = mapped_column(String(100))
    meta_creative_id: Mapped[Optional[str]] = mapped_column(String(100))

    format_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("formats.id"))
    narrative_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("narratives.id"))
    hook_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("hooks.id"))
    archetype_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("archetypes.id"))

    name: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(50), default="active")

    media_type: Mapped[Optional[str]] = mapped_column(String(20))
    media_url: Mapped[Optional[str]] = mapped_column(Text)
    storage_url: Mapped[Optional[str]] = mapped_column(Text)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    aspect_ratio: Mapped[Optional[str]] = mapped_column(String(20))
    width_px: Mapped[Optional[int]] = mapped_column(Integer)
    height_px: Mapped[Optional[int]] = mapped_column(Integer)

    headline: Mapped[Optional[str]] = mapped_column(Text)
    body_text: Mapped[Optional[str]] = mapped_column(Text)
    cta_type: Mapped[Optional[str]] = mapped_column(String(100))
    destination_url: Mapped[Optional[str]] = mapped_column(Text)

    launch_date: Mapped[Optional[date]] = mapped_column(Date)
    peak_performance_date: Mapped[Optional[date]] = mapped_column(Date)
    fatigue_start_date: Mapped[Optional[date]] = mapped_column(Date)
    fatigue_acceleration_date: Mapped[Optional[date]] = mapped_column(Date)
    death_date: Mapped[Optional[date]] = mapped_column(Date)
    days_to_peak: Mapped[Optional[int]] = mapped_column(Integer)

    analysis_status: Mapped[str] = mapped_column(String(50), default="pending")
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    analysis_error: Mapped[Optional[str]] = mapped_column(Text)

    source: Mapped[str] = mapped_column(String(50), default="meta")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    product: Mapped["Product"] = relationship(back_populates="creatives")
    creative_metadata: Mapped[Optional["CreativeMetadata"]] = relationship(back_populates="creative", uselist=False)
    embedding: Mapped[Optional["CreativeEmbedding"]] = relationship(back_populates="creative", uselist=False)
    daily_metrics: Mapped[List["CreativeDailyMetrics"]] = relationship(back_populates="creative")
    fatigue_scores: Mapped[List["FatigueScore"]] = relationship(back_populates="creative")
    predictions: Mapped[List["CreativePrediction"]] = relationship(back_populates="creative")


# ---------------------------------------------------------------------------
# Creative Metadata (AI-extracted)
# ---------------------------------------------------------------------------

class CreativeMetadata(Base):
    __tablename__ = "creative_metadata"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creative_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("creatives.id", ondelete="CASCADE"), unique=True, nullable=False)

    narrative_type: Mapped[Optional[str]] = mapped_column(String(100))
    story_structure: Mapped[Optional[str]] = mapped_column(String(100))
    marketing_angle: Mapped[Optional[str]] = mapped_column(String(100))
    stage_of_funnel: Mapped[Optional[str]] = mapped_column(String(50))
    content_category: Mapped[Optional[str]] = mapped_column(String(100))

    hook_type: Mapped[Optional[str]] = mapped_column(String(100))
    hook_text: Mapped[Optional[str]] = mapped_column(Text)
    hook_duration_seconds: Mapped[Optional[float]] = mapped_column(Float)

    visual_style: Mapped[Optional[str]] = mapped_column(String(100))
    production_quality: Mapped[Optional[str]] = mapped_column(String(50))

    creator_type: Mapped[Optional[str]] = mapped_column(String(100))
    ugc_type: Mapped[Optional[str]] = mapped_column(String(100))
    human_presence: Mapped[Optional[bool]] = mapped_column(Boolean)

    offer_type: Mapped[str] = mapped_column(String(100), default="none")
    discount_percentage: Mapped[Optional[float]] = mapped_column(Float)
    price_mentioned: Mapped[bool] = mapped_column(Boolean, default=False)
    cta_text: Mapped[Optional[str]] = mapped_column(String(255))

    emotional_trigger: Mapped[Optional[str]] = mapped_column(String(100))
    pain_point: Mapped[Optional[str]] = mapped_column(Text)
    benefit_claimed: Mapped[Optional[str]] = mapped_column(Text)
    objection_handled: Mapped[Optional[str]] = mapped_column(Text)

    trust_signal: Mapped[Optional[str]] = mapped_column(String(100))
    authority_figure: Mapped[Optional[str]] = mapped_column(String(100))

    product_visibility: Mapped[Optional[str]] = mapped_column(String(50))
    brand_visibility: Mapped[Optional[str]] = mapped_column(String(50))

    color_theme: Mapped[Optional[str]] = mapped_column(String(100))
    has_captions: Mapped[Optional[bool]] = mapped_column(Boolean)
    has_music: Mapped[Optional[bool]] = mapped_column(Boolean)

    audience_intent: Mapped[Optional[str]] = mapped_column(String(100))
    target_pain_keywords: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))

    analysis_confidence: Mapped[Optional[float]] = mapped_column(Float)
    gemini_model_version: Mapped[Optional[str]] = mapped_column(String(50))
    raw_gemini_response: Mapped[Optional[dict]] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creative: Mapped["Creative"] = relationship(back_populates="creative_metadata")


# ---------------------------------------------------------------------------
# Creative Embeddings
# ---------------------------------------------------------------------------

class CreativeEmbedding(Base):
    __tablename__ = "creative_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creative_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("creatives.id", ondelete="CASCADE"), unique=True, nullable=False)

    embedding = mapped_column(Vector(768), nullable=False)
    narrative_embedding = mapped_column(Vector(768))
    hook_embedding = mapped_column(Vector(768))
    visual_embedding = mapped_column(Vector(768))
    offer_embedding = mapped_column(Vector(768))

    model_version: Mapped[str] = mapped_column(String(50), default="text-embedding-004")
    input_text: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creative: Mapped["Creative"] = relationship(back_populates="embedding")


# ---------------------------------------------------------------------------
# Daily Metrics
# ---------------------------------------------------------------------------

class CreativeDailyMetrics(Base):
    __tablename__ = "creative_daily_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creative_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("creatives.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)

    spend: Mapped[float] = mapped_column(Numeric(14, 4), default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    reach: Mapped[int] = mapped_column(Integer, default=0)
    frequency: Mapped[float] = mapped_column(Numeric(8, 4), default=0)

    clicks: Mapped[int] = mapped_column(Integer, default=0)
    ctr: Mapped[float] = mapped_column(Numeric(8, 6), default=0)
    link_clicks: Mapped[int] = mapped_column(Integer, default=0)
    link_ctr: Mapped[float] = mapped_column(Numeric(8, 6), default=0)
    outbound_clicks: Mapped[int] = mapped_column(Integer, default=0)
    outbound_ctr: Mapped[float] = mapped_column(Numeric(8, 6), default=0)
    cpc: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    cpm: Mapped[float] = mapped_column(Numeric(10, 4), default=0)

    purchases: Mapped[int] = mapped_column(Integer, default=0)
    purchase_value: Mapped[float] = mapped_column(Numeric(14, 4), default=0)
    add_to_cart: Mapped[int] = mapped_column(Integer, default=0)
    initiate_checkout: Mapped[int] = mapped_column(Integer, default=0)
    cpa: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    roas: Mapped[float] = mapped_column(Numeric(8, 4), default=0)
    conversion_rate: Mapped[float] = mapped_column(Numeric(8, 6), default=0)

    video_views: Mapped[int] = mapped_column(Integer, default=0)
    video_p25_watched: Mapped[int] = mapped_column(Integer, default=0)
    video_p50_watched: Mapped[int] = mapped_column(Integer, default=0)
    video_p75_watched: Mapped[int] = mapped_column(Integer, default=0)
    video_p100_watched: Mapped[int] = mapped_column(Integer, default=0)
    three_sec_video_views: Mapped[int] = mapped_column(Integer, default=0)
    hook_rate: Mapped[float] = mapped_column(Numeric(8, 6), default=0)
    hold_rate: Mapped[float] = mapped_column(Numeric(8, 6), default=0)
    thumb_stop_rate: Mapped[float] = mapped_column(Numeric(8, 6), default=0)

    attribution_window: Mapped[str] = mapped_column(String(20), default="7d_click")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    creative: Mapped["Creative"] = relationship(back_populates="daily_metrics")

    __table_args__ = (
        UniqueConstraint("creative_id", "date", "attribution_window"),
    )


# ---------------------------------------------------------------------------
# Fatigue Scores
# ---------------------------------------------------------------------------

class FatigueScore(Base):
    __tablename__ = "fatigue_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creative_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("creatives.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    calculated_date: Mapped[date] = mapped_column(Date, nullable=False)

    fatigue_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    fatigue_stage: Mapped[str] = mapped_column(String(30), default="healthy")

    ctr_decay_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    cpc_inflation_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    cpm_inflation_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    cpa_inflation_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    roas_decay_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    hook_decay_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    hold_decay_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    frequency_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    conversion_decay_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)

    days_since_launch: Mapped[int] = mapped_column(Integer, default=0)
    days_to_peak: Mapped[Optional[int]] = mapped_column(Integer)
    expected_remaining_days: Mapped[Optional[int]] = mapped_column(Integer)
    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3), default=0)

    baseline_ctr: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))
    baseline_cpc: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    baseline_cpm: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    baseline_cpa: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    baseline_roas: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    baseline_hook_rate: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))
    current_frequency: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    creative: Mapped["Creative"] = relationship(back_populates="fatigue_scores")

    __table_args__ = (
        UniqueConstraint("creative_id", "calculated_date"),
    )


# ---------------------------------------------------------------------------
# Creative Predictions
# ---------------------------------------------------------------------------

class CreativePrediction(Base):
    __tablename__ = "creative_predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creative_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("creatives.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)

    creative_success_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    narrative_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    hook_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    visual_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    offer_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    novelty_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    launch_confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    fatigue_risk_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))

    winner_similarity_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    loser_similarity_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))

    predicted_ctr: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))
    predicted_cpa: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    predicted_roas: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    predicted_lifespan_days: Mapped[Optional[int]] = mapped_column(Integer)

    recommendation: Mapped[Optional[str]] = mapped_column(String(50))
    recommendation_reason: Mapped[Optional[str]] = mapped_column(Text)

    similar_winner_ids: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    similar_loser_ids: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    comparable_narratives: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    risk_factors: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    opportunity_factors: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))

    model_version: Mapped[Optional[str]] = mapped_column(String(50))
    prediction_confidence: Mapped[Optional[float]] = mapped_column(Numeric(4, 3))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    creative: Mapped["Creative"] = relationship(back_populates="predictions")


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------

class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    creative_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("creatives.id"))

    insight_type: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="medium")

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    recommended_action: Mapped[Optional[str]] = mapped_column(Text)
    action_type: Mapped[Optional[str]] = mapped_column(String(50))

    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_actioned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)

    generated_by: Mapped[str] = mapped_column(String(100), default="gemini-2.5-pro")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------------
# Competitor Creatives
# ---------------------------------------------------------------------------

class CompetitorCreative(Base):
    __tablename__ = "competitor_creatives"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    competitor_page_id: Mapped[Optional[str]] = mapped_column(String(100))
    competitor_page_name: Mapped[Optional[str]] = mapped_column(String(255))
    meta_ad_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    ad_archive_url: Mapped[Optional[str]] = mapped_column(Text)

    media_type: Mapped[Optional[str]] = mapped_column(String(20))
    media_url: Mapped[Optional[str]] = mapped_column(Text)
    storage_url: Mapped[Optional[str]] = mapped_column(Text)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    headline: Mapped[Optional[str]] = mapped_column(Text)
    body_text: Mapped[Optional[str]] = mapped_column(Text)
    cta_type: Mapped[Optional[str]] = mapped_column(String(100))
    destination_url: Mapped[Optional[str]] = mapped_column(Text)

    first_seen_date: Mapped[Optional[date]] = mapped_column(Date)
    last_seen_date: Mapped[Optional[date]] = mapped_column(Date)
    estimated_lifespan_days: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    narrative_type: Mapped[Optional[str]] = mapped_column(String(100))
    hook_type: Mapped[Optional[str]] = mapped_column(String(100))
    visual_style: Mapped[Optional[str]] = mapped_column(String(100))
    offer_type: Mapped[Optional[str]] = mapped_column(String(100))
    creator_type: Mapped[Optional[str]] = mapped_column(String(100))
    emotional_trigger: Mapped[Optional[str]] = mapped_column(String(100))
    trust_signal: Mapped[Optional[str]] = mapped_column(String(100))
    human_presence: Mapped[Optional[bool]] = mapped_column(Boolean)

    analysis_status: Mapped[str] = mapped_column(String(50), default="pending")
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    raw_gemini_response: Mapped[Optional[dict]] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    embedding: Mapped[Optional["CompetitorEmbedding"]] = relationship(back_populates="competitor_creative", uselist=False)


class CompetitorEmbedding(Base):
    __tablename__ = "competitor_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_creative_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("competitor_creatives.id", ondelete="CASCADE"), unique=True, nullable=False)
    embedding = mapped_column(Vector(768), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="text-embedding-004")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    competitor_creative: Mapped["CompetitorCreative"] = relationship(back_populates="embedding")


# ---------------------------------------------------------------------------
# Product Benchmarks
# ---------------------------------------------------------------------------

class ProductBenchmark(Base):
    __tablename__ = "product_benchmarks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    period_days: Mapped[int] = mapped_column(Integer, default=30)

    median_ctr: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))
    median_cpc: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    median_cpm: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    median_cpa: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    median_roas: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    median_hook_rate: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))
    median_hold_rate: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))
    median_frequency: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    median_lifespan: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))

    winner_ctr_threshold: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))
    winner_roas_threshold: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    winner_cpa_threshold: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))

    loser_ctr_threshold: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))
    loser_roas_threshold: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    loser_cpa_threshold: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))

    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped["Product"] = relationship(back_populates="benchmarks")

    __table_args__ = (
        UniqueConstraint("product_id", "period_days"),
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="analyst")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------------
# Sync Logs
# ---------------------------------------------------------------------------

class SyncLog(Base):
    __tablename__ = "sync_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="running")
    account_id: Mapped[Optional[str]] = mapped_column(String(100))
    date_range_start: Mapped[Optional[date]] = mapped_column(Date)
    date_range_end: Mapped[Optional[date]] = mapped_column(Date)
    records_fetched: Mapped[int] = mapped_column(Integer, default=0)
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


# Re-export genome models so all existing imports work
from app.models.genome import GenomePattern, NarrativePerformance, FormatPerformance, MetaAccount  # noqa: E402, F401
