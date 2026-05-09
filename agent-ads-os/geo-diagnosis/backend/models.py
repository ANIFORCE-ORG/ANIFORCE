"""SQLAlchemy model template for persistent GEO audits."""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class GeoAuditMixin:
    """Mixin fields for integration with a host app SQLAlchemy Base."""

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"audit_{uuid.uuid4().hex[:12]}")
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    brand: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(160), nullable=False)
    market: Mapped[str | None] = mapped_column(String(180), nullable=True)
    report_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
