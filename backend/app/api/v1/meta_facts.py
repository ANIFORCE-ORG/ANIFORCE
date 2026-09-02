"""Controlled Meta facts synchronization and Dashboard reads."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.meta_ads import MetaAdsAdapter
from app.api.deps import get_current_user
from app.config.database import get_db, get_session_maker
from app.config.settings import get_settings
from app.models.meta_fact import MetaFact
from app.models.meta_insights_sync_run import MetaInsightsSyncRun
from app.models.platform_connection import PlatformConnection
from app.models.sub_account_binding import SubAccountBinding
from app.repositories.impl.sqlite_meta_fact_repo import SqliteMetaFactRepository
from app.services.meta_dashboard_service import MetaDashboardService
from app.services.meta_fact_normalizer import normalize_account_id
from app.services.meta_insights_batch_gate import get_meta_insights_batch_gate
from app.services.meta_insights_collector import MetaInsightsCollector

router = APIRouter(tags=["meta-facts"])
logger = logging.getLogger(__name__)


def classify_meta_sync_error(exc: Exception) -> tuple[str, str]:
    """Map low-level failures to an actionable, non-sensitive sync reason."""
    message = str(exc).lower()
    error_type = type(exc).__name__.lower()
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)) or "timeout" in error_type or "timeout" in message:
        return "META_INSIGHTS_TIMEOUT", "Meta Insights 请求超时。"
    if "database is locked" in message or "operationalerror" in error_type and "locked" in message:
        return "META_INSIGHTS_DATABASE_LOCKED", "本地数据库写入繁忙，未能保存该账号结果。"
    status = getattr(exc, "status", None)
    if status == 429 or "rate limit" in message or "too many requests" in message:
        return "META_INSIGHTS_RATE_LIMITED", "Meta API 请求频率受限。"
    return "META_INSIGHTS_API_ERROR", "Meta Insights 读取失败。"


class MetaFactsSyncRequest(BaseModel):
    connection_id: str
    account_ids: list[str] = Field(min_length=1, max_length=200)
    since: date
    until: date
    level: Literal["adset"] = "adset"


def validate_sync_window(since: date, until: date, *, max_days: int = 31) -> None:
    if since > until:
        raise ValueError("since must not be after until")
    if (until - since).days + 1 > max_days:
        raise ValueError(f"date window must not exceed {max_days} days")


def normalize_requested_accounts(account_ids: list[str]) -> list[str]:
    normalized = list(dict.fromkeys(normalize_account_id(value) for value in account_ids))
    if len(normalized) > 200:
        raise ValueError("at most 200 unique accounts are allowed")
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
    """Synchronously refresh AdSet facts for explicitly selected active accounts."""
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
        normalize_account_id(binding.sub_account_id): {
            "account_name": binding.sub_account_name,
            "business_manager_id": binding.bm_customer_id,
        }
        for binding in result.scalars().all()
    }
    missing = [account_id for account_id in account_ids if account_id not in bindings]
    if missing:
        raise HTTPException(
            status_code=400,
            detail={"message": "Accounts are not active bindings", "account_ids": missing},
        )

    now = datetime.utcnow()
    stale_before = now - timedelta(minutes=15)
    await db.execute(
        update(MetaInsightsSyncRun)
        .where(
            MetaInsightsSyncRun.connection_id == connection.id,
            MetaInsightsSyncRun.account_id.in_(account_ids),
            MetaInsightsSyncRun.level == request.level,
            MetaInsightsSyncRun.status == "running",
            MetaInsightsSyncRun.started_at < stale_before,
        )
        .values(
            status="failed",
            error_code="STALE_RUN",
            error_message="同步进程中断，请重新同步。",
            finished_at=now,
        )
    )
    await db.commit()

    running_result = await db.execute(
        select(MetaInsightsSyncRun.account_id).where(
            MetaInsightsSyncRun.connection_id == connection.id,
            MetaInsightsSyncRun.account_id.in_(account_ids),
            MetaInsightsSyncRun.level == request.level,
            MetaInsightsSyncRun.status == "running",
        )
    )
    running_accounts = sorted(set(running_result.scalars().all()))
    if running_accounts:
        raise HTTPException(
            status_code=409,
            detail={"message": "Accounts are already syncing", "account_ids": running_accounts},
        )

    runs: dict[str, MetaInsightsSyncRun] = {}
    for account_id in account_ids:
        binding = bindings[account_id]
        run = MetaInsightsSyncRun(
            user_id=current_user["id"],
            connection_id=connection.id,
            account_id=account_id,
            account_name=binding["account_name"],
            level=request.level,
            requested_since=request.since,
            requested_until=request.until,
            status="running",
        )
        db.add(run)
        runs[account_id] = run
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="One or more accounts are already syncing") from exc

    settings = get_settings()
    if not settings.META_APP_ID or not settings.META_APP_SECRET:
        for run in runs.values():
            persisted = await db.get(MetaInsightsSyncRun, run.id)
            if persisted:
                persisted.status = "failed"
                persisted.error_code = "META_APP_NOT_CONFIGURED"
                persisted.error_message = "Meta application is not configured."
                persisted.finished_at = datetime.utcnow()
        await db.commit()
        raise HTTPException(status_code=500, detail="Meta application is not configured")

    request_gate = get_meta_insights_batch_gate(
        settings.META_INSIGHTS_BATCH_MIN_INTERVAL_SECONDS
    )
    max_pages = max(1, settings.META_INSIGHTS_BATCH_MAX_PAGES_PER_ACCOUNT)
    concurrency = max(1, settings.META_INSIGHTS_BATCH_CONCURRENCY)
    session_maker = get_session_maker()
    connection_id = connection.id
    access_token = connection.access_token
    since = request.since.isoformat()
    until = request.until.isoformat()
    semaphore = asyncio.Semaphore(concurrency)
    write_lock = asyncio.Lock()

    async def sync_one(account_id: str) -> dict:
        binding = bindings[account_id]
        run_id = runs[account_id].id
        async with semaphore:
            async with session_maker() as worker_db:
                try:
                    current_run = await worker_db.get(MetaInsightsSyncRun, run_id)
                    if current_run and current_run.status == "failed":
                        return {
                            "account_id": account_id, "account_name": binding["account_name"],
                            "sync_run_id": run_id, "status": "failed",
                            "rows_written": current_run.rows_written,
                            "error_code": current_run.error_code or "SYNC_CANCELLED",
                            "message": current_run.error_message or "同步已停止。",
                        }
                    adapter = MetaAdsAdapter({
                        "app_id": settings.META_APP_ID,
                        "app_secret": settings.META_APP_SECRET,
                        "api_version": "v19.0",
                        "insights_request_timeout_seconds": settings.META_INSIGHTS_REQUEST_TIMEOUT_SECONDS,
                    })
                    adapter.set_access_token(access_token)
                    repository = SqliteMetaFactRepository(worker_db)

                    class LockedRepository:
                        async def upsert_many(self, rows):
                            async with write_lock:
                                written = await repository.upsert_many(rows)
                                await worker_db.commit()
                                return written

                    collector = MetaInsightsCollector(
                        adapter, LockedRepository(), [account_id]
                    )
                    counts = await collector.collect_account(
                        connection_id=connection_id,
                        account_id=account_id,
                        since=since,
                        until=until,
                        business_manager_id=binding["business_manager_id"],
                        sync_run_id=run_id,
                        max_pages=max_pages,
                        levels=(request.level,),
                        before_page_request=request_gate.wait_turn,
                    )
                    rows_written = counts.get(request.level, 0)
                    persisted = await worker_db.get(MetaInsightsSyncRun, run_id)
                    if persisted and persisted.status == "failed":
                        return {
                            "account_id": account_id, "account_name": binding["account_name"],
                            "sync_run_id": run_id, "status": "failed",
                            "rows_written": persisted.rows_written,
                            "error_code": persisted.error_code or "SYNC_CANCELLED",
                            "message": persisted.error_message or "同步已停止。",
                        }
                    if persisted:
                        persisted.status = "succeeded"
                        persisted.rows_written = rows_written
                        persisted.finished_at = datetime.utcnow()
                    async with write_lock:
                        await worker_db.commit()
                    return {
                        "account_id": account_id, "account_name": binding["account_name"],
                        "sync_run_id": run_id, "status": "succeeded",
                        "rows_written": rows_written,
                    }
                except Exception as exc:
                    logger.warning(
                        "Meta Insights sync failed: connection_id=%s account_id=%s level=%s error_type=%s",
                        connection_id, account_id, request.level, type(exc).__name__,
                    )
                    await worker_db.rollback()
                    async with write_lock:
                        await worker_db.execute(
                            delete(MetaFact).where(MetaFact.sync_run_id == run_id)
                        )
                        persisted = await worker_db.get(MetaInsightsSyncRun, run_id)

                    error_code, error_message = classify_meta_sync_error(exc)
                    if persisted and persisted.status == "running":
                        persisted.status = "failed"
                        persisted.error_code = error_code
                        persisted.error_message = error_message
                        persisted.finished_at = datetime.utcnow()
                    async with write_lock:
                        await worker_db.commit()
                    return {
                        "account_id": account_id, "account_name": binding["account_name"],
                        "sync_run_id": run_id, "status": "failed", "rows_written": 0,
                        "error_code": error_code,
                        "message": error_message,
                    }

    accounts = await asyncio.gather(*(sync_one(account_id) for account_id in account_ids))

    return {
        "connection_id": connection.id,
        "level": request.level,
        "window": {"since": request.since, "until": request.until},
        "accounts": accounts,
    }


@router.post("/meta-facts/sync/cancel")
async def cancel_meta_facts_sync(
    request: MetaFactsSyncRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account_ids = normalize_requested_accounts(request.account_ids)
    connection = await owned_meta_connection(db, request.connection_id, current_user["id"])
    now = datetime.utcnow()
    result = await db.execute(
        update(MetaInsightsSyncRun)
        .where(
            MetaInsightsSyncRun.user_id == current_user["id"],
            MetaInsightsSyncRun.connection_id == connection.id,
            MetaInsightsSyncRun.account_id.in_(account_ids),
            MetaInsightsSyncRun.level == request.level,
            MetaInsightsSyncRun.requested_since == request.since,
            MetaInsightsSyncRun.requested_until == request.until,
            MetaInsightsSyncRun.status == "running",
        )
        .values(
            status="failed",
            error_code="SYNC_CANCELLED",
            error_message="用户已停止本次同步。",
            finished_at=now,
        )
    )
    await db.commit()
    return {"cancelled": result.rowcount or 0}


@router.post("/meta-facts/sync/progress")
async def get_meta_facts_sync_progress(
    request: MetaFactsSyncRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return real account-level progress for the latest matching batch."""
    account_ids = normalize_requested_accounts(request.account_ids)
    connection = await owned_meta_connection(db, request.connection_id, current_user["id"])
    result = await db.execute(
        select(MetaInsightsSyncRun)
        .where(
            MetaInsightsSyncRun.user_id == current_user["id"],
            MetaInsightsSyncRun.connection_id == connection.id,
            MetaInsightsSyncRun.account_id.in_(account_ids),
            MetaInsightsSyncRun.level == request.level,
            MetaInsightsSyncRun.requested_since == request.since,
            MetaInsightsSyncRun.requested_until == request.until,
        )
        .order_by(MetaInsightsSyncRun.started_at.desc())
    )
    latest_by_account: dict[str, MetaInsightsSyncRun] = {}
    for run in result.scalars().all():
        latest_by_account.setdefault(run.account_id, run)
    completed = sum(
        run.status in {"succeeded", "failed"} for run in latest_by_account.values()
    )
    succeeded = sum(run.status == "succeeded" for run in latest_by_account.values())
    failed = sum(run.status == "failed" for run in latest_by_account.values())
    rows_written = sum(run.rows_written for run in latest_by_account.values())
    total = len(account_ids)
    return {
        "total": total,
        "completed": completed,
        "succeeded": succeeded,
        "failed": failed,
        "running": max(0, total - completed),
        "rows_written": rows_written,
        "percent": round(completed / total * 100, 2) if total else 0,
    }


@router.get("/dashboard/meta-overview")
async def get_meta_dashboard_overview(
    since: date,
    until: date,
    connection_id: str | None = None,
    result_action_type: Literal["lead", "purchase", "mobile_app_install"] = "lead",
    account_id: str | None = None,
    objective: str | None = Query(default=None),
    click_type: Literal["clicks", "inline_link_clicks"] = Query(default="inline_link_clicks"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        validate_sync_window(since, until, max_days=90)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if connection_id:
        connections = [await owned_meta_connection(db, connection_id, current_user["id"])]
    else:
        connection_result = await db.execute(
            select(PlatformConnection).where(
                PlatformConnection.user_id == current_user["id"],
                PlatformConnection.platform == "Meta",
                PlatformConnection.status == "active",
            )
        )
        connections = list(connection_result.scalars().all())
        if not connections:
            raise HTTPException(status_code=404, detail="Active Meta connection not found")
    connection_ids = [connection.id for connection in connections]
    binding_result = await db.execute(
        select(SubAccountBinding).where(
            SubAccountBinding.parent_connection_id.in_(connection_ids),
            SubAccountBinding.status == "active",
        )
    )
    expected_accounts = [
        {
            "account_id": normalize_account_id(binding.sub_account_id),
            "account_name": binding.sub_account_name or normalize_account_id(binding.sub_account_id),
        }
        for binding in binding_result.scalars().all()
    ]
    expected_ids = [item["account_id"] for item in expected_accounts]
    latest_result = await db.execute(
        select(MetaInsightsSyncRun).where(
            MetaInsightsSyncRun.connection_id.in_(connection_ids),
            MetaInsightsSyncRun.level == "adset",
            MetaInsightsSyncRun.requested_since == since,
            MetaInsightsSyncRun.requested_until == until,
            MetaInsightsSyncRun.account_id.in_(expected_ids),
        ).order_by(MetaInsightsSyncRun.started_at.desc())
    )
    sync_accounts: dict[str, dict] = {}
    for run in latest_result.scalars().all():
        normalized_id = normalize_account_id(run.account_id)
        if normalized_id not in sync_accounts:
            sync_accounts[normalized_id] = {
                "status": run.status,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "error_code": run.error_code,
                "error_message": run.error_message,
            }
    return await MetaDashboardService(SqliteMetaFactRepository(db)).overview(
        connection_id=connection_ids if len(connection_ids) > 1 else connection_ids[0],
        account_id=account_id,
        since=since,
        until=until,
        result_action_type=result_action_type,
        use_link_clicks=click_type == "inline_link_clicks",
        expected_accounts=expected_accounts if account_id is None else None,
        sync_accounts=sync_accounts if account_id is None else None,
        objective=objective,
    )
