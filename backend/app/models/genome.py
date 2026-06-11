"""Additional ORM models: Genome, Narrative/Format performance."""
from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class GenomePattern(Base):
    __tablename__ = "genome_patterns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    hook_type: Mapped[Optional[str]] = mapped_column(String(100))
    narrative_type: Mapped[Optional[str]] = mapped_column(String(100))
    format_type: Mapped[Optional[str]] = mapped_column(String(50))
    creator_type: Mapped[Optional[str]] = mapped_column(String(100))
    offer_type: Mapped[Optional[str]] = mapped_column(String(100))
    visual_style: Mapped[Optional[str]] = mapped_column(String(100))
    trust_signal: Mapped[Optional[str]] = mapped_column(String(100))
    funnel_stage: Mapped[Optional[str]] = mapped_column(String(50))

    pattern_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))

    total_creatives: Mapped[int] = mapped_column(Integer, default=0)
    avg_ctr: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))
    avg_cpa: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    avg_roas: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    avg_lifespan_days: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    avg_fatigue_days: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    win_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 3))
    total_spend: Mapped[float] = mapped_column(Numeric(14, 4), default=0)
    total_purchases: Mapped[int] = mapped_column(Integer, default=0)

    last_calculated_at: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class NarrativePerformance(Base):
    __tablename__ = "narrative_performance"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    narrative_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("narratives.id"), nullable=False)

    total_creatives: Mapped[int] = mapped_column(Integer, default=0)
    active_creatives: Mapped[int] = mapped_column(Integer, default=0)
    winner_count: Mapped[int] = mapped_column(Integer, default=0)
    loser_count: Mapped[int] = mapped_column(Integer, default=0)

    avg_ctr: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))
    avg_cpc: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    avg_cpa: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    avg_roas: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    avg_hook_rate: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))
    avg_hold_rate: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))
    avg_thumb_stop_rate: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))
    total_spend: Mapped[Optional[float]] = mapped_column(Numeric(14, 4))
    total_purchases: Mapped[Optional[int]] = mapped_column(Integer)
    total_purchase_value: Mapped[Optional[float]] = mapped_column(Numeric(14, 4))

    avg_lifespan_days: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    median_lifespan_days: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    avg_peak_day: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    avg_fatigue_start_day: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    max_frequency_at_fatigue: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))

    ctr_decay_rate_pct: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    cpa_increase_rate_pct: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    roas_decay_rate_pct: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))

    is_oversaturated: Mapped[bool] = mapped_column(Boolean, default=False)
    saturation_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)

    spend_share_pct: Mapped[Optional[float]] = mapped_column(Numeric(6, 3))
    purchase_share_pct: Mapped[Optional[float]] = mapped_column(Numeric(6, 3))
    volume_share_pct: Mapped[Optional[float]] = mapped_column(Numeric(6, 3))

    last_calculated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("product_id", "narrative_id"),)


class FormatPerformance(Base):
    __tablename__ = "format_performance"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    format_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("formats.id"), nullable=False)

    total_creatives: Mapped[int] = mapped_column(Integer, default=0)
    active_creatives: Mapped[int] = mapped_column(Integer, default=0)

    avg_ctr: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))
    avg_cpc: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    avg_cpa: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    avg_roas: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    avg_lifespan_days: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    avg_hook_rate: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))
    avg_hold_rate: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))

    benchmark_ctr_p25: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))
    benchmark_ctr_p50: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))
    benchmark_ctr_p75: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))
    benchmark_roas_p25: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    benchmark_roas_p50: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    benchmark_roas_p75: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))

    last_calculated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("product_id", "format_id"),)


class MetaAccount(Base):
    __tablename__ = "meta_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    account_name: Mapped[Optional[str]] = mapped_column(String(255))
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata")
    business_id: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    access_token: Mapped[Optional[str]] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
