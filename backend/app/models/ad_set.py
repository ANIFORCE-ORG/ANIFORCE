"""Advertising ad set and ad-set-level performance models."""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class AdSetStatus(str, enum.Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class AdSet(Base):
    __tablename__ = "ad_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[str] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform_ad_set_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    placements: Mapped[str | None] = mapped_column(Text, nullable=True)
    optimization_goal: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bid_strategy: Mapped[str | None] = mapped_column(String(100), nullable=True)
    daily_budget: Mapped[float] = mapped_column(Float, nullable=False)
    spent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[AdSetStatus] = mapped_column(
        Enum(AdSetStatus, native_enum=False), nullable=False, default=AdSetStatus.DRAFT, index=True
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="ad_sets")
    metrics: Mapped[list["AdSetMetric"]] = relationship(
        back_populates="ad_set", cascade="all, delete-orphan"
    )
    material_metrics: Mapped[list["MaterialPerformance"]] = relationship(
        back_populates="ad_set", cascade="all, delete-orphan"
    )


class AdSetMetric(Base):
    __tablename__ = "ad_set_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ad_set_id: Mapped[str] = mapped_column(
        ForeignKey("ad_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    installs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    spend: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ctr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cvr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cpa: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cpi: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    roi: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    ad_set: Mapped["AdSet"] = relationship(back_populates="metrics")
