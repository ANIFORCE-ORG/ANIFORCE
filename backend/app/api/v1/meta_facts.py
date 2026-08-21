"""Controlled Meta facts synchronization and Dashboard reads."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.meta_ads import MetaAdsAdapter
from app.api.deps import get_current_user
from app.config.database import get_db
from app.config.settings import get_settings
from app.models.platform_connection import PlatformConnection
from app.models.sub_account_binding import SubAccountBinding
from app.repositories.impl.sqlite_meta_fact_repo import SqliteMetaFactRepository
from app.services.meta_dashboard_service import MetaDashboardService
from app.services.meta_fact_normalizer import normalize_account_id
from app.services.meta_insights_collector import MetaInsightsCollector

router = APIRouter(tags=["meta-facts"])


class MetaFactsSyncRequest(BaseModel):
    connection_id: str
    account_ids: list[str] = Field(min_length=1, max_length=5)
    since: date
    until: date


def validate_sync_window(since: date, until: date, *, max_days: int = 31) -> None:
    if since > until:
        raise ValueError("since must not be after until")
    if (until - since).days + 1 > max_days:
        raise ValueError(f"date window must not exceed {max_days} days")


def normalize_requested_accounts(account_ids: list[str]) -> list[str]:
    normalized = list(dict.fromkeys(normalize_account_id(value) for value in account_ids))
    if len(normalized) > 5:
        raise ValueError("at most 5 unique accounts are allowed")
    return normalized


async def owned_meta_connection(
    db: AsyncSession, connection_id: str, user_id: str
) -> PlatformConnection:
    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.id == connection_id,
            PlatformConnection.user_id == user_id,
            PlatformConnection.platform == "Meta",
        )
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        raise HTTPException(status_code=404, detail="Meta connection not found")
    if connection.status != "active" or not connection.access_token:
        raise HTTPException(status_code=400, detail="Meta connection is not active")
    return connection


@router.post("/meta-facts/sync")
async def sync_meta_facts(
    request: MetaFactsSyncRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        validate_sync_window(request.since, request.until)
        account_ids = normalize_requested_accounts(request.account_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    connection = await owned_meta_connection(db, request.connection_id, current_user["id"])
    result = await db.execute(
        select(SubAccountBinding).where(
            SubAccountBinding.parent_connection_id == connection.id,
            SubAccountBinding.status == "active",
            func.replace(SubAccountBinding.sub_account_id, "act_", "").in_(account_ids),
        )
    )
    bindings = {
        normalize_account_id(binding.sub_account_id): binding
        for binding in result.scalars().all()
    }
    missing = [account_id for account_id in account_ids if account_id not in bindings]
    if missing:
        raise HTTPException(
            status_code=400,
            detail={"message": "Accounts are not active bindings", "account_ids": missing},
        )

    settings = get_settings()
    if not settings.META_APP_ID or not settings.META_APP_SECRET:
        raise HTTPException(status_code=500, detail="Meta application is not configured")

    adapter = MetaAdsAdapter({
        "app_id": settings.META_APP_ID,
        "app_secret": settings.META_APP_SECRET,
        "api_version": "v19.0",
    })
    adapter.set_access_token(connection.access_token)
    repository = SqliteMetaFactRepository(db)
    collector = MetaInsightsCollector(adapter, repository, account_ids)
    accounts = []
    for account_id in account_ids:
        binding = bindings[account_id]
        counts = await collector.collect_account(
            connection_id=connection.id,
            account_id=account_id,
            since=request.since.isoformat(),
            until=request.until.isoformat(),
            business_manager_id=binding.bm_customer_id,
            max_pages=1,
        )
        accounts.append({
            "account_id": account_id,
            "account_name": binding.sub_account_name,
            "counts": counts,
        })
    return {
        "connection_id": connection.id,
        "window": {"since": request.since, "until": request.until},
        "accounts": accounts,
    }


@router.get("/dashboard/meta-overview")
async def get_meta_dashboard_overview(
    connection_id: str,
    since: date,
    until: date,
    result_action_type: Literal["lead", "purchase", "mobile_app_install"] = "lead",
    account_id: str | None = None,
    click_type: Literal["clicks", "inline_link_clicks"] = Query(default="inline_link_clicks"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        validate_sync_window(since, until, max_days=90)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await owned_meta_connection(db, connection_id, current_user["id"])
    return await MetaDashboardService(SqliteMetaFactRepository(db)).overview(
        connection_id=connection_id,
        account_id=account_id,
        since=since,
        until=until,
        result_action_type=result_action_type,
        use_link_clicks=click_type == "inline_link_clicks",
    )
