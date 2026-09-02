"""Normalize sparse Meta Insights payloads for the single meta_facts table."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any


LEVEL_FIELDS = {
    "account": ("account_id", "account_name", None, None),
    "campaign": ("campaign_id", "campaign_name", "account_id", "account_name"),
    "adset": ("adset_id", "adset_name", "campaign_id", "campaign_name"),
    "ad": ("ad_id", "ad_name", "adset_id", "adset_name"),
}


def normalize_account_id(value: Any) -> str:
    normalized = str(value or "").strip()
    if normalized.startswith("act_"):
        normalized = normalized[4:]
    if not normalized:
        raise ValueError("Meta account_id is required")
    return normalized


def _integer(payload: dict[str, Any], field: str) -> int | None:
    value = payload.get(field)
    if value in (None, ""):
        return None
    try:
        return int(Decimal(str(value)))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid Meta integer field {field}: {value!r}") from exc


def _decimal(payload: dict[str, Any], field: str) -> Decimal | None:
    value = payload.get(field)
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid Meta decimal field {field}: {value!r}") from exc


def _date(payload: dict[str, Any], field: str, *, required: bool = False) -> date | None:
    value = payload.get(field)
    if value in (None, ""):
        if required:
            raise ValueError(f"Meta {field} is required")
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"Invalid Meta date field {field}: {value!r}") from exc


def normalize_meta_fact(
    payload: dict[str, Any],
    *,
    connection_id: str,
    level: str,
    business_manager_id: str | None = None,
    account_timezone: str | None = None,
    sync_run_id: str | None = None,
    status: str = "accessible_with_rows",
) -> dict[str, Any]:
    """Convert one sparse Insights row to MetaFact constructor values."""
    if level not in LEVEL_FIELDS:
        raise ValueError(f"Unsupported Meta fact level: {level}")
    if not connection_id:
        raise ValueError("connection_id is required")

    entity_id_field, entity_name_field, parent_id_field, parent_name_field = LEVEL_FIELDS[level]
    account_id = normalize_account_id(payload.get("account_id"))
    entity_id = account_id if level == "account" else str(payload.get(entity_id_field) or "").strip()
    if not entity_id:
        raise ValueError(f"Meta {entity_id_field} is required for level {level}")

    attribution = str(payload.get("attribution_setting") or "default").strip() or "default"
    return {
        "connection_id": connection_id,
        "level": level,
        "account_id": account_id,
        "account_name": payload.get("account_name"),
        "business_manager_id": business_manager_id,
        "entity_id": entity_id,
        "entity_name": payload.get(entity_name_field) if entity_name_field else payload.get("account_name"),
        "parent_entity_id": (
            normalize_account_id(payload.get(parent_id_field))
            if parent_id_field == "account_id"
            else (str(payload.get(parent_id_field)).strip() if parent_id_field and payload.get(parent_id_field) else None)
        ),
        "parent_entity_name": payload.get(parent_name_field) if parent_name_field else None,
        "metric_date": _date(payload, "date_start", required=True),
        "date_stop": _date(payload, "date_stop"),
        "attribution_setting": attribution,
        "account_currency": payload.get("account_currency"),
        "account_timezone": account_timezone,
        "objective": payload.get("objective"),
        "optimization_goal": payload.get("optimization_goal"),
        "impressions": _integer(payload, "impressions"),
        "reach": _integer(payload, "reach"),
        "frequency": _decimal(payload, "frequency"),
        "clicks": _integer(payload, "clicks"),
        "inline_link_clicks": _integer(payload, "inline_link_clicks"),
        "spend": _decimal(payload, "spend"),
        "ctr": _decimal(payload, "ctr"),
        "cpc": _decimal(payload, "cpc"),
        "cpm": _decimal(payload, "cpm"),
        "actions_json": payload.get("actions"),
        "action_values_json": payload.get("action_values"),
        "cost_per_action_type_json": payload.get("cost_per_action_type"),
        "conversion_values_json": payload.get("conversion_values"),
        "raw_payload_json": dict(payload),
        "status": status,
        "sync_run_id": sync_run_id,
    }
