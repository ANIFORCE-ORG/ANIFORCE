"""平台广告账户模型"""
import enum
import json
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base


class PlatformAccountStatus(str, enum.Enum):
    ACTIVE = "active"
    CLEARING = "clearing"
    BANNED = "banned"
    CLEARED = "cleared"
    RECYCLED = "recycled"
    DISCONNECTED = "disconnected"


class PlatformAccount(Base):
    __tablename__ = "platform_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=PlatformAccountStatus.ACTIVE.value, index=True)

    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    business_manager_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    account_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    account_property: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    balance: Mapped[float] = mapped_column(Float, default=0.0)
    amount_spent: Mapped[float] = mapped_column(Float, default=0.0)
    available_balance: Mapped[float] = mapped_column(Float, default=0.0)
    frozen_balance: Mapped[float] = mapped_column(Float, default=0.0)
    survival_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    meta_account_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    operations: Mapped[list["PlatformAccountOperation"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )
    project_links: Mapped[list["ProjectPlatformAccount"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )

    def to_dict(self, include_token: bool = False) -> dict:
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "platform": self.platform,
            "account_id": self.account_id,
            "account_name": self.account_name,
            "status": self.status,
            "currency": self.currency,
            "timezone": self.timezone,
            "business_manager_id": self.business_manager_id,
            "account_type": self.account_type,
            "account_property": self.account_property,
            "source_type": self.source_type,
            "remark": self.remark,
            "balance": self.balance,
            "amount_spent": self.amount_spent,
            "available_balance": self.available_balance,
            "frozen_balance": self.frozen_balance,
            "survival_days": self.survival_days,
            "usage_days": self.usage_days,
            "meta_account_status": self.meta_account_status,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "connected_at": self.connected_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "has_token": bool(self.access_token),
        }
        if include_token:
            data["access_token"] = self.access_token
            data["refresh_token"] = self.refresh_token
        return data


class PlatformConnection(Base):
    __tablename__ = "platform_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="not_configured", index=True)
    app_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    app_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    redirect_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    scopes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_connected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_scopes(self) -> list[str]:
        if not self.scopes:
            return []
        return json.loads(self.scopes)

    def set_scopes(self, scopes: list[str]) -> None:
        self.scopes = json.dumps(scopes)

    def to_dict(self, include_secret: bool = False) -> dict:
        data = {
            "id": self.id,
            "platform": self.platform,
            "status": self.status,
            "app_id": self.app_id,
            "has_app_secret": bool(self.app_secret),
            "redirect_uri": self.redirect_uri,
            "scopes": self.get_scopes(),
            "last_error": self.last_error,
            "last_connected_at": self.last_connected_at.isoformat() if self.last_connected_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_secret:
            data["app_secret"] = self.app_secret
        return data


class ProjectPlatformAccount(Base):
    __tablename__ = "project_platform_accounts"
    __table_args__ = (
        UniqueConstraint("project_id", "platform_account_id", name="uq_project_platform_account"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    platform_account_id: Mapped[str] = mapped_column(ForeignKey("platform_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), default="primary", index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    spend_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    daily_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    account: Mapped[PlatformAccount] = relationship(back_populates="project_links")

    def to_dict(self) -> dict:
        data = {
            "id": self.id,
            "project_id": self.project_id,
            "platform_account_id": self.platform_account_id,
            "role": self.role,
            "status": self.status,
            "spend_cap": self.spend_cap,
            "daily_cap": self.daily_cap,
            "note": self.note,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if self.account:
            data["account"] = self.account.to_dict()
        return data


class AgentAction(Base):
    __tablename__ = "agent_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    platform_account_id: Mapped[str | None] = mapped_column(ForeignKey("platform_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(8), default="L1", index=True)
    status: Mapped[str] = mapped_column(String(32), default="suggested", index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_impact_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(32), default="agent")
    confirmed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    executed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    execution_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def _loads(self, value: str | None) -> dict:
        if not value:
            return {}
        return json.loads(value)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "platform_account_id": self.platform_account_id,
            "campaign_id": self.campaign_id,
            "action_type": self.action_type,
            "risk_level": self.risk_level,
            "status": self.status,
            "title": self.title,
            "summary": self.summary,
            "evidence": self._loads(self.evidence_json),
            "payload": self._loads(self.payload_json),
            "expected_impact": self._loads(self.expected_impact_json),
            "created_by": self.created_by,
            "confirmed_by": self.confirmed_by,
            "executed_by": self.executed_by,
            "execution_result": self._loads(self.execution_result_json),
            "outcome": self._loads(self.outcome_json),
            "created_at": self.created_at.isoformat(),
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
        }


class PlatformAccountOperation(Base):
    __tablename__ = "platform_account_operations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_pk: Mapped[str] = mapped_column(ForeignKey("platform_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="completed", index=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    account: Mapped[PlatformAccount] = relationship(back_populates="operations")

    def set_payload(self, payload: dict | None) -> None:
        self.payload = json.dumps(payload or {})

    def get_payload(self) -> dict:
        if not self.payload:
            return {}
        return json.loads(self.payload)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "account_pk": self.account_pk,
            "operation_type": self.operation_type,
            "status": self.status,
            "amount": self.amount,
            "currency": self.currency,
            "target_id": self.target_id,
            "note": self.note,
            "payload": self.get_payload(),
            "created_at": self.created_at.isoformat(),
        }
