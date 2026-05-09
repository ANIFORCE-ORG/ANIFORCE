"""平台账号连接、广告账户运营和真实平台执行 API"""
from datetime import datetime, timedelta
from typing import Any, Literal
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config.database import get_db
from app.config.settings import get_settings
from app.connectors.meta_adapter import MetaAdsAdapter
from app.models.platform_account import PlatformAccount, PlatformAccountOperation, PlatformConnection, ProjectPlatformAccount
from app.repositories.factory import get_campaign_repo, get_project_repo
from app.repositories.protocols import CampaignRepository, ProjectRepository


router = APIRouter()


class ConnectResponse(BaseModel):
    auth_url: str
    state: str


class TokenConnectRequest(BaseModel):
    platform: Literal["meta", "google", "tiktok"]
    access_token: str = Field(..., min_length=8)
    refresh_token: str | None = None
    account_id: str | None = None
    account_name: str | None = None
    currency: str | None = None
    timezone: str | None = None
    business_manager_id: str | None = None
    source_type: str | None = "client-owned"
    remark: str | None = None


class PlatformAccountOperationRequest(BaseModel):
    operation_type: Literal["open", "recharge", "clear", "bind", "recycle"]
    amount: float | None = None
    currency: str | None = "USD"
    target_id: str | None = None
    note: str | None = None
    payload: dict[str, Any] | None = None


class CreateMetaCampaignRequest(BaseModel):
    platform_account_id: str
    project_id: str
    name: str
    objective: str = "OUTCOME_TRAFFIC"
    status: str = "PAUSED"
    budget: float = Field(..., gt=0)
    budget_type: Literal["daily", "lifetime"] = "daily"
    special_ad_categories: list[str] = Field(default_factory=list)
    bid_strategy: str | None = None
    create_local_record: bool = True


class PlatformConnectionConfigRequest(BaseModel):
    app_id: str = Field(..., min_length=3)
    app_secret: str | None = None
    redirect_uri: str | None = None
    scopes: list[str] | None = None


META_SCOPES = ["ads_management", "ads_read", "business_management"]
OAUTH_STATE_TTL_MINUTES = 15
_oauth_states: dict[str, dict[str, Any]] = {}


def _meta_adapter(account: PlatformAccount, connection: PlatformConnection | None = None) -> MetaAdsAdapter:
    settings = get_settings()
    adapter = MetaAdsAdapter({
        "app_id": connection.app_id if connection and connection.app_id else settings.META_APP_ID,
        "app_secret": connection.app_secret if connection and connection.app_secret else settings.META_APP_SECRET,
        "access_token": account.access_token,
        "proxy_url": settings.META_PROXY_URL,
    })
    adapter.set_ad_account(account.account_id)
    return adapter


async def _get_account(session: AsyncSession, account_pk: str, user_id: str) -> PlatformAccount:
    result = await session.execute(
        select(PlatformAccount).where(
            PlatformAccount.id == account_pk,
            PlatformAccount.user_id == user_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Platform account not found")
    return account


async def _get_connection(
    session: AsyncSession,
    user_id: str,
    platform: str,
) -> PlatformConnection | None:
    result = await session.execute(
        select(PlatformConnection).where(
            PlatformConnection.user_id == user_id,
            PlatformConnection.platform == platform,
        )
    )
    return result.scalar_one_or_none()


async def _get_or_create_connection(
    session: AsyncSession,
    user_id: str,
    platform: str,
) -> PlatformConnection:
    connection = await _get_connection(session, user_id, platform)
    if connection:
        return connection
    connection = PlatformConnection(user_id=user_id, platform=platform)
    connection.set_scopes(META_SCOPES if platform == "meta" else [])
    session.add(connection)
    await session.flush()
    return connection


def _default_redirect_uri(platform: str) -> str:
    settings = get_settings()
    if platform == "meta":
        return settings.META_OAUTH_REDIRECT_URI
    return ""


async def _upsert_account(
    session: AsyncSession,
    user_id: str,
    payload: dict[str, Any],
) -> PlatformAccount:
    result = await session.execute(
        select(PlatformAccount).where(
            PlatformAccount.user_id == user_id,
            PlatformAccount.platform == payload["platform"],
            PlatformAccount.account_id == payload["account_id"],
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        account = PlatformAccount(
            user_id=user_id,
            platform=payload["platform"],
            account_id=payload["account_id"],
            account_name=payload["account_name"],
        )
        session.add(account)

    for key, value in payload.items():
        if hasattr(account, key) and value is not None:
            setattr(account, key, value)

    account.status = payload.get("status") or "active"
    account.last_sync_at = datetime.utcnow()
    await session.flush()
    return account


def _cleanup_oauth_states() -> None:
    now = datetime.utcnow()
    expired = [
        state for state, payload in _oauth_states.items()
        if payload["created_at"] + timedelta(minutes=OAUTH_STATE_TTL_MINUTES) < now
    ]
    for state in expired:
        _oauth_states.pop(state, None)


async def _sync_meta_accounts_from_token(
    session: AsyncSession,
    user_id: str,
    access_token: str,
    connection: PlatformConnection | None = None,
    refresh_token: str | None = None,
    token_expires_at: datetime | None = None,
    source_type: str = "oauth",
) -> list[PlatformAccount]:
    adapter = MetaAdsAdapter({
        "app_id": connection.app_id if connection and connection.app_id else get_settings().META_APP_ID,
        "app_secret": connection.app_secret if connection and connection.app_secret else get_settings().META_APP_SECRET,
        "access_token": access_token,
        "proxy_url": get_settings().META_PROXY_URL,
    })
    remote_accounts = await adapter.get_ad_accounts()
    accounts: list[PlatformAccount] = []

    for remote in remote_accounts:
        account_id = remote.get("id")
        if not account_id:
            continue
        account = await _upsert_account(session, user_id, {
            "platform": "meta",
            "account_id": account_id,
            "account_name": remote.get("name") or account_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expires_at": token_expires_at,
            "currency": remote.get("currency"),
            "timezone": remote.get("timezone_name"),
            "source_type": source_type,
            "meta_account_status": remote.get("account_status"),
            "amount_spent": float(remote.get("amount_spent") or 0),
        })
        accounts.append(account)

    return accounts


@router.post("/connect", response_model=ConnectResponse)
async def connect_platform(
    platform: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """获取平台 OAuth 授权 URL。生产主流程使用 server-side code flow。"""
    settings = get_settings()
    _cleanup_oauth_states()
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "platform": platform,
        "user_id": current_user["id"],
        "created_at": datetime.utcnow(),
    }

    if platform == "meta":
        connection = await _get_connection(session, current_user["id"], "meta")
        app_id = connection.app_id if connection and connection.app_id else settings.META_APP_ID
        app_secret = connection.app_secret if connection and connection.app_secret else settings.META_APP_SECRET
        redirect_uri = connection.redirect_uri if connection and connection.redirect_uri else settings.META_OAUTH_REDIRECT_URI
        scopes = connection.get_scopes() if connection and connection.get_scopes() else META_SCOPES
        if not app_id or not app_secret:
            raise HTTPException(status_code=400, detail="Meta connection is not configured")
        query = urlencode({
            "client_id": app_id,
            "redirect_uri": redirect_uri,
            "scope": ",".join(scopes),
            "state": state,
            "response_type": "code",
        })
        auth_url = f"https://www.facebook.com/v19.0/dialog/oauth?{query}"
    elif platform == "google":
        if not settings.GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=400, detail="GOOGLE_CLIENT_ID is not configured")
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={settings.GOOGLE_CLIENT_ID}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=token&"
            f"scope=https://www.googleapis.com/auth/adwords&"
            f"state={state}"
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    return ConnectResponse(auth_url=auth_url, state=state)


@router.get("/connections/{platform}/config")
async def get_platform_connection_config(
    platform: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if platform not in {"meta", "google", "tiktok"}:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    connection = await _get_or_create_connection(session, current_user["id"], platform)
    if not connection.redirect_uri:
        connection.redirect_uri = _default_redirect_uri(platform)
    if not connection.get_scopes() and platform == "meta":
        connection.set_scopes(META_SCOPES)
    await session.commit()
    return connection.to_dict()


@router.put("/connections/{platform}/config")
async def save_platform_connection_config(
    platform: str,
    request: PlatformConnectionConfigRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if platform != "meta":
        raise HTTPException(status_code=400, detail="Only Meta connection config is supported now")
    connection = await _get_or_create_connection(session, current_user["id"], platform)
    app_secret = request.app_secret.strip() if request.app_secret else ""
    if not app_secret and not connection.app_secret:
        raise HTTPException(status_code=400, detail="Meta App Secret is required")
    connection.app_id = request.app_id.strip()
    if app_secret:
        connection.app_secret = app_secret
    connection.redirect_uri = (request.redirect_uri or _default_redirect_uri(platform)).strip()
    connection.set_scopes(request.scopes or META_SCOPES)
    connection.status = "configured"
    connection.last_error = None
    await session.commit()
    return connection.to_dict()


@router.get("/status")
async def get_platform_status(platform: str):
    settings = get_settings()
    if platform == "meta":
        return {
            "platform": "meta",
            "configured": bool(settings.META_APP_ID and settings.META_APP_SECRET),
            "redirect_uri": settings.META_OAUTH_REDIRECT_URI,
            "required_permissions": META_SCOPES,
        }
    if platform == "google":
        return {
            "platform": "google",
            "configured": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
            "redirect_uri": "",
            "required_permissions": ["https://www.googleapis.com/auth/adwords"],
        }
    raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")


@router.get("/meta/oauth/callback")
async def meta_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    """Meta OAuth 回调：换 token、同步广告账户，然后跳回前端状态页。"""
    settings = get_settings()
    frontend_callback = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/platform-accounts/callback"

    if error:
        return RedirectResponse(
            f"{frontend_callback}?{urlencode({'status': 'error', 'message': error_description or error})}"
        )
    if not code or not state:
        return RedirectResponse(
            f"{frontend_callback}?{urlencode({'status': 'error', 'message': 'Missing code or state'})}"
        )

    _cleanup_oauth_states()
    state_payload = _oauth_states.pop(state, None)
    if not state_payload or state_payload["platform"] != "meta":
        return RedirectResponse(
            f"{frontend_callback}?{urlencode({'status': 'error', 'message': 'Invalid or expired OAuth state'})}"
        )

    connection = await _get_connection(session, state_payload["user_id"], "meta")
    app_id = connection.app_id if connection and connection.app_id else settings.META_APP_ID
    app_secret = connection.app_secret if connection and connection.app_secret else settings.META_APP_SECRET
    redirect_uri = connection.redirect_uri if connection and connection.redirect_uri else settings.META_OAUTH_REDIRECT_URI
    if not app_id or not app_secret:
        return RedirectResponse(
            f"{frontend_callback}?{urlencode({'status': 'error', 'message': 'Meta connection is not configured'})}"
        )

    adapter = MetaAdsAdapter({
        "app_id": app_id,
        "app_secret": app_secret,
        "proxy_url": settings.META_PROXY_URL,
    })

    try:
        token_data = await adapter.exchange_code_for_token(code, redirect_uri)
        short_token = token_data["access_token"]
        if app_secret:
            token_data = await adapter.get_long_lived_token(short_token)
        access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in")
        token_expires_at = (
            datetime.utcnow() + timedelta(seconds=int(expires_in))
            if expires_in else None
        )
        accounts = await _sync_meta_accounts_from_token(
            session=session,
            user_id=state_payload["user_id"],
            access_token=access_token,
            connection=connection,
            token_expires_at=token_expires_at,
            source_type="oauth",
        )
        if connection:
            connection.status = "connected"
            connection.last_connected_at = datetime.utcnow()
            connection.last_error = None
        await session.commit()
    except Exception as exc:
        if connection:
            connection.status = "error"
            connection.last_error = str(exc)
        await session.rollback()
        return RedirectResponse(
            f"{frontend_callback}?{urlencode({'status': 'error', 'message': f'Meta authorization failed: {exc}'})}"
        )

    return RedirectResponse(
        f"{frontend_callback}?{urlencode({'status': 'success', 'count': str(len(accounts))})}"
    )


@router.post("/connect-token")
async def connect_with_token(
    request: TokenConnectRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """内部导入已有 token，并尝试同步平台广告账户。生产主流程使用 /connect OAuth。"""
    accounts: list[PlatformAccount] = []

    if request.platform == "meta":
        try:
            accounts = await _sync_meta_accounts_from_token(
                session=session,
                user_id=current_user["id"],
                access_token=request.access_token,
                refresh_token=request.refresh_token,
                source_type=request.source_type or "token-import",
            )
        except Exception as exc:
            if not request.account_id:
                raise HTTPException(status_code=400, detail=f"Meta token validation failed: {exc}")
            account = await _upsert_account(session, current_user["id"], {
                "platform": "meta",
                "account_id": request.account_id,
                "account_name": request.account_name or request.account_id,
                "access_token": request.access_token,
                "refresh_token": request.refresh_token,
                "currency": request.currency,
                "timezone": request.timezone,
                "business_manager_id": request.business_manager_id,
                "source_type": request.source_type or "token-import",
                "remark": request.remark,
            })
            accounts.append(account)
    else:
        if not request.account_id:
            raise HTTPException(status_code=400, detail="account_id is required for this platform")
        account = await _upsert_account(session, current_user["id"], {
            "platform": request.platform,
            "account_id": request.account_id,
            "account_name": request.account_name or request.account_id,
            "access_token": request.access_token,
            "refresh_token": request.refresh_token,
            "currency": request.currency,
            "timezone": request.timezone,
            "business_manager_id": request.business_manager_id,
            "source_type": request.source_type,
            "remark": request.remark,
        })
        accounts.append(account)

    await session.commit()
    return {"accounts": [account.to_dict() for account in accounts]}


@router.get("/accounts")
async def get_connected_accounts(
    platform: str | None = None,
    status: str | None = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    query = select(PlatformAccount).where(PlatformAccount.user_id == current_user["id"])
    if platform:
        query = query.where(PlatformAccount.platform == platform)
    if status:
        query = query.where(PlatformAccount.status == status)
    query = query.order_by(PlatformAccount.updated_at.desc())
    result = await session.execute(query)
    accounts = result.scalars().all()
    return [account.to_dict() for account in accounts]


@router.get("/accounts/{account_id}/operations")
async def get_account_operations(
    account_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await _get_account(session, account_id, current_user["id"])
    result = await session.execute(
        select(PlatformAccountOperation)
        .where(PlatformAccountOperation.account_pk == account_id)
        .order_by(PlatformAccountOperation.created_at.desc())
    )
    return [operation.to_dict() for operation in result.scalars().all()]


@router.post("/accounts/{account_id}/operations")
async def create_account_operation(
    account_id: str,
    request: PlatformAccountOperationRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    account = await _get_account(session, account_id, current_user["id"])
    operation = PlatformAccountOperation(
        account_pk=account.id,
        operation_type=request.operation_type,
        amount=request.amount,
        currency=request.currency,
        target_id=request.target_id,
        note=request.note,
    )
    operation.set_payload(request.payload)
    session.add(operation)

    if request.operation_type == "recharge" and request.amount:
        account.balance += request.amount
        account.available_balance += request.amount
    elif request.operation_type == "clear":
        account.balance = 0
        account.available_balance = 0
        account.frozen_balance = 0
        account.status = "cleared"
    elif request.operation_type == "bind" and request.target_id:
        account.business_manager_id = request.target_id
    elif request.operation_type == "recycle":
        account.available_balance = 0
        account.status = "recycled"
    elif request.operation_type == "open":
        account.status = "active"

    await session.commit()
    return {"account": account.to_dict(), "operation": operation.to_dict()}


@router.delete("/accounts/{account_id}")
async def disconnect_account(
    account_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    account = await _get_account(session, account_id, current_user["id"])
    account.status = "disconnected"
    account.access_token = None
    await session.commit()
    return {"message": "Account disconnected successfully"}


@router.post("/accounts/test")
async def add_test_account(
    platform: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if not get_settings().DEMO_MODE:
        raise HTTPException(status_code=404, detail="Not found")
    account = await _upsert_account(session, current_user["id"], {
        "platform": platform,
        "account_id": f"test_{platform}_123456",
        "account_name": f"Test {platform.title()} Account",
        "access_token": f"DEMO_{platform.upper()}_TOKEN",
        "currency": "USD",
        "timezone": "America/Los_Angeles",
        "source_type": "test/sandbox",
    })
    await session.commit()
    return account.to_dict()


@router.post("/meta/campaigns")
async def create_meta_campaign(
    request: CreateMetaCampaignRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """在 Meta 广告账户真实创建一条 Campaign，并可同步创建本地计划记录。"""
    account = await _get_account(session, request.platform_account_id, current_user["id"])
    if account.platform != "meta":
        raise HTTPException(status_code=400, detail="Selected account is not a Meta account")
    if not account.access_token:
        raise HTTPException(status_code=400, detail="Meta account has no token")

    project = await project_repo.get_by_id(request.project_id)
    if not project or project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    adapter = _meta_adapter(account)
    budget_cents = int(round(request.budget * 100))
    params = {
        "name": request.name,
        "objective": request.objective,
        "status": request.status,
        "special_ad_categories": request.special_ad_categories,
        "bid_strategy": request.bid_strategy,
    }
    if request.budget_type == "daily":
        params["daily_budget"] = budget_cents
    else:
        params["lifetime_budget"] = budget_cents

    try:
        remote = await adapter.create_campaign(params)
    except Exception as exc:
        message = str(exc) or exc.__class__.__name__
        raise HTTPException(status_code=502, detail=f"Meta campaign creation failed: {message}")

    local_campaign = None
    if request.create_local_record:
        link_result = await session.execute(
            select(ProjectPlatformAccount).where(
                ProjectPlatformAccount.project_id == request.project_id,
                ProjectPlatformAccount.platform_account_id == account.id,
            )
        )
        link = link_result.scalar_one_or_none()
        if not link:
            session.add(ProjectPlatformAccount(
                project_id=request.project_id,
                platform_account_id=account.id,
                role="primary",
                status="active",
                note="Auto-linked when creating a Meta campaign",
            ))
        local_campaign = await campaign_repo.create(
            project_id=request.project_id,
            name=request.name,
            platform="Meta",
            budget=request.budget,
            platform_account_id=account.id,
            external_campaign_id=remote.get("id"),
            external_status=request.status,
            objective=request.objective,
            budget_type=request.budget_type,
            daily_budget=request.budget if request.budget_type == "daily" else None,
            lifetime_budget=request.budget if request.budget_type == "lifetime" else None,
            bid_strategy=request.bid_strategy,
            last_synced_at=datetime.utcnow(),
            status="draft" if request.status == "PAUSED" else "running",
            config={
                "platform_account_id": account.id,
                "remote_campaign_id": remote.get("id"),
                "remote_platform": "meta",
                "objective": request.objective,
                "budget_type": request.budget_type,
            },
            pipeline_step="created_on_platform",
            learning_phase="not_started",
            auto_optimize_enabled=True,
        )

    account.last_sync_at = datetime.utcnow()
    await session.commit()
    return {
        "remote_campaign": remote,
        "local_campaign": local_campaign,
        "account": account.to_dict(),
    }
