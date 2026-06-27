"""Simplified side effect event model for Agent MVP."""

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


SideEffectType = Literal["entity_changed", "content_ready", "data_ready", "action_required", "run_status"]


class SideEffect(BaseModel):
    """Semantic event used by frontend to refresh workspace projections."""

    id: str = Field(default_factory=lambda: f"evt_{uuid4().hex}")
    type: SideEffectType
    domain: str | None = None
    action: str | None = None
    message: str
    affected_entities: list[dict] = Field(default_factory=list)
    refresh_panels: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
