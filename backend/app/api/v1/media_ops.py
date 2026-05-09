"""Media operations workflow API.

This module models the offline media-buying workflow collected from the
Xinyou media SOP and exposes a self-contained demo API. It is intentionally
kept independent from the current campaign agent loop so it can be merged into
the unified Agent OS later without disturbing existing platform-account code.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_current_user


router = APIRouter(prefix="/media-ops", tags=["media-ops"])


OrderStatus = Literal[
    "draft",
    "pending_payment",
    "payment_review",
    "pending_opening",
    "opening",
    "binding_card",
    "pending_delivery",
    "delivered",
    "exception",
]


class MediaCustomer(BaseModel):
    id: str
    name: str
    industry: str
    level: str
    payment_preference: str
    contact_group: str
    owner: str
    risk_note: str | None = None


class MediaProduct(BaseModel):
    id: str
    platform: str
    name: str
    account_type: str
    account_property: str
    eligible_industries: list[str]
    min_recharge_usd: float
    delivery_sla_minutes: int
    selling_points: list[str]


class AccountOrder(BaseModel):
    id: str
    customer_id: str
    customer_name: str
    product_id: str
    product_name: str
    platform: str
    account_type: str
    timezone: str
    email: str
    quantity: int
    ad_industry: str
    payment_method: Literal["USD", "USDT"]
    receivable_amount: float
    status: OrderStatus
    owner: str
    created_at: str
    updated_at: str
    next_action: str
    delivered_accounts: list[str] = Field(default_factory=list)
    remark: str | None = None


class PaymentVoucher(BaseModel):
    id: str
    order_id: str
    customer_name: str
    amount: float
    currency: Literal["USD", "USDT"]
    status: Literal["pending_review", "approved", "amount_mismatch", "rejected"]
    transaction_hash: str | None = None
    screenshot_url: str | None = None
    submitted_at: str
    reviewed_by: str | None = None
    reviewed_at: str | None = None


class MediaAccount(BaseModel):
    id: str
    account_id: str
    account_name: str
    customer_name: str
    platform: str
    account_type: str
    account_property: str
    timezone: str
    email: str
    business_manager_id: str | None = None
    status: Literal["pending_delivery", "active", "verifying", "frozen", "banned", "recycled"]
    spend: float
    balance: float
    delivered_at: str | None = None
    owner: str
    operation_flags: list[str] = Field(default_factory=list)


class ServiceTicket(BaseModel):
    id: str
    customer_name: str
    account_id: str | None = None
    ticket_type: Literal[
        "pixel_binding",
        "account_verification",
        "freeze_unfreeze",
        "migration",
        "recharge_delay",
        "limit_adjustment",
        "appeal",
    ]
    priority: Literal["low", "normal", "high", "urgent"]
    status: Literal["open", "processing", "waiting_customer", "resolved"]
    owner: str
    sla_due_at: str
    summary: str


class KnowledgeArticle(BaseModel):
    id: str
    category: str
    title: str
    trigger_keywords: list[str]
    answer: str


class MediaOpsDashboard(BaseModel):
    metrics: dict[str, Any]
    status_funnel: list[dict[str, Any]]
    pending_tasks: list[dict[str, Any]]
    alerts: list[dict[str, Any]]


class AccountOrderCreateRequest(BaseModel):
    customer_id: str
    product_id: str
    timezone: str
    email: str
    quantity: int = Field(gt=0)
    ad_industry: str
    payment_method: Literal["USD", "USDT"] = "USDT"
    remark: str | None = None


NOW = datetime(2026, 5, 9, 10, 30, 0)


CUSTOMERS: list[MediaCustomer] = [
    MediaCustomer(
        id="cust_xinyou_001",
        name="EASTAR Games",
        industry="游戏",
        level="A",
        payment_preference="USDT",
        contact_group="Telegram / 飞书群：EASTAR投放",
        owner="Sea Satr",
        risk_note="非金融客户，优先分配 club/adforce 户",
    ),
    MediaCustomer(
        id="cust_xinyou_002",
        name="NKH Growth",
        industry="工具应用",
        level="B",
        payment_preference="USD",
        contact_group="飞书群：NKH开户&充值",
        owner="Lijuci",
    ),
]


PRODUCTS: list[MediaProduct] = [
    MediaProduct(
        id="prod_fb_3_unlimited",
        platform="Facebook",
        name="Facebook 三不限账户",
        account_type="三不限账户",
        account_property="BM",
        eligible_industries=["游戏", "工具应用", "电商", "内容订阅"],
        min_recharge_usd=1000,
        delivery_sla_minutes=60,
        selling_points=["不限制广告预算", "不限制域名", "不限制主页", "适合快速起量"],
    ),
    MediaProduct(
        id="prod_fb_club",
        platform="Facebook",
        name="Facebook Club 账户",
        account_type="Club账户",
        account_property="BM",
        eligible_industries=["游戏", "工具应用", "非金融普通业务"],
        min_recharge_usd=1000,
        delivery_sla_minutes=90,
        selling_points=["适合非金融客户", "交付稳定", "支持后续像素绑定"],
    ),
    MediaProduct(
        id="prod_fb_eu",
        platform="Facebook",
        name="欧洲海外户",
        account_type="海外户",
        account_property="Agency",
        eligible_industries=["游戏", "跨境电商", "SaaS"],
        min_recharge_usd=1000,
        delivery_sla_minutes=120,
        selling_points=["海外主体资源", "适合欧洲市场", "风控策略独立"],
    ),
]


ORDERS: list[AccountOrder] = [
    AccountOrder(
        id="AO-260509-001",
        customer_id="cust_xinyou_001",
        customer_name="EASTAR Games",
        product_id="prod_fb_3_unlimited",
        product_name="Facebook 三不限账户",
        platform="Facebook",
        account_type="三不限账户",
        timezone="UTC+8",
        email="media-eastar@example.com",
        quantity=3,
        ad_industry="游戏",
        payment_method="USDT",
        receivable_amount=3000,
        status="payment_review",
        owner="Lijuci",
        created_at=(NOW - timedelta(hours=2)).isoformat(),
        updated_at=(NOW - timedelta(minutes=25)).isoformat(),
        next_action="财务审核客户上传水单，审核后进入开户队列",
        remark="客户已在群内上传付款截图",
    ),
    AccountOrder(
        id="AO-260509-002",
        customer_id="cust_xinyou_002",
        customer_name="NKH Growth",
        product_id="prod_fb_club",
        product_name="Facebook Club 账户",
        platform="Facebook",
        account_type="Club账户",
        timezone="UTC+0",
        email="ops-nkh@example.com",
        quantity=2,
        ad_industry="工具应用",
        payment_method="USD",
        receivable_amount=2200,
        status="binding_card",
        owner="Sea Satr",
        created_at=(NOW - timedelta(hours=5)).isoformat(),
        updated_at=(NOW - timedelta(minutes=12)).isoformat(),
        next_action="卡台绑卡并设置限额，完成后进入待交付",
        delivered_accounts=["act_2010406203167307"],
    ),
    AccountOrder(
        id="AO-260508-006",
        customer_id="cust_xinyou_001",
        customer_name="EASTAR Games",
        product_id="prod_fb_eu",
        product_name="欧洲海外户",
        platform="Facebook",
        account_type="海外户",
        timezone="UTC+1",
        email="eu-eastar@example.com",
        quantity=1,
        ad_industry="游戏",
        payment_method="USDT",
        receivable_amount=1500,
        status="delivered",
        owner="Lijuci",
        created_at=(NOW - timedelta(days=1, hours=3)).isoformat(),
        updated_at=(NOW - timedelta(days=1, hours=1)).isoformat(),
        next_action="客户已接收，等待后续充值或像素工单",
        delivered_accounts=["act_1000179599235178"],
    ),
]


VOUCHERS: list[PaymentVoucher] = [
    PaymentVoucher(
        id="PV-260509-001",
        order_id="AO-260509-001",
        customer_name="EASTAR Games",
        amount=3000,
        currency="USDT",
        status="pending_review",
        transaction_hash="0x7e...a91",
        screenshot_url="/mock/vouchers/eastar-3000.png",
        submitted_at=(NOW - timedelta(minutes=28)).isoformat(),
    ),
    PaymentVoucher(
        id="PV-260509-002",
        order_id="AO-260509-002",
        customer_name="NKH Growth",
        amount=2200,
        currency="USD",
        status="approved",
        screenshot_url="/mock/vouchers/nkh-2200.png",
        submitted_at=(NOW - timedelta(hours=4)).isoformat(),
        reviewed_by="Finance",
        reviewed_at=(NOW - timedelta(hours=3, minutes=45)).isoformat(),
    ),
]


ACCOUNTS: list[MediaAccount] = [
    MediaAccount(
        id="macc_001",
        account_id="act_2010406203167307",
        account_name="JL-NKH+8-260428-055",
        customer_name="NKH Growth",
        platform="Facebook",
        account_type="Club账户",
        account_property="BM",
        timezone="UTC+0",
        email="ops-nkh@example.com",
        business_manager_id="1270987855007796",
        status="pending_delivery",
        spend=0,
        balance=1000,
        owner="Sea Satr",
        operation_flags=["待客户接收广告账户", "待像素绑定"],
    ),
    MediaAccount(
        id="macc_002",
        account_id="act_1000179599235178",
        account_name="JL-EU-EASTAR-260508-001",
        customer_name="EASTAR Games",
        platform="Facebook",
        account_type="海外户",
        account_property="Agency",
        timezone="UTC+1",
        email="eu-eastar@example.com",
        business_manager_id="928731736297373",
        status="active",
        spend=286.4,
        balance=713.6,
        delivered_at=(NOW - timedelta(days=1, hours=1)).isoformat(),
        owner="Lijuci",
        operation_flags=["SMIT插件已安装"],
    ),
    MediaAccount(
        id="macc_003",
        account_id="act_822637597553048",
        account_name="JL-EASTAR-FROZEN-260506",
        customer_name="EASTAR Games",
        platform="Facebook",
        account_type="三不限账户",
        account_property="BM",
        timezone="UTC+8",
        email="media-eastar@example.com",
        business_manager_id="1270987855007796",
        status="frozen",
        spend=1240.2,
        balance=0,
        delivered_at=(NOW - timedelta(days=3)).isoformat(),
        owner="Lijuci",
        operation_flags=["待解冻处理", "客户已提交截图"],
    ),
]


TICKETS: list[ServiceTicket] = [
    ServiceTicket(
        id="TCK-260509-001",
        customer_name="EASTAR Games",
        account_id="act_822637597553048",
        ticket_type="freeze_unfreeze",
        priority="urgent",
        status="processing",
        owner="Lijuci",
        sla_due_at=(NOW + timedelta(minutes=40)).isoformat(),
        summary="客户反馈账户冻结，需核查风控提示并给出解冻路径",
    ),
    ServiceTicket(
        id="TCK-260509-002",
        customer_name="NKH Growth",
        account_id="act_2010406203167307",
        ticket_type="pixel_binding",
        priority="normal",
        status="open",
        owner="Sea Satr",
        sla_due_at=(NOW + timedelta(hours=3)).isoformat(),
        summary="客户需要绑定像素并确认事件权限",
    ),
]


ARTICLES: list[KnowledgeArticle] = [
    KnowledgeArticle(
        id="KA-001",
        category="开户",
        title="开户工单必填字段",
        trigger_keywords=["下户", "开户", "户类型", "时区"],
        answer="请客户提供户类型、时区、邮箱、数量、投放行业。非金融客户优先分配 club 或 adforce 户。",
    ),
    KnowledgeArticle(
        id="KA-002",
        category="充值",
        title="充值对接规则",
        trigger_keywords=["充值", "USDT", "美金", "到账"],
        answer="充值对接时间为 10:00-24:00，单次单户最低 1000 美金。客户上传水单后财务审核，目标 10 分钟内到账。",
    ),
    KnowledgeArticle(
        id="KA-003",
        category="售后",
        title="像素绑定处理话术",
        trigger_keywords=["像素", "分享", "绑定"],
        answer="请客户提供 BMID、像素 ID 和目标广告账户 ID。媒介确认资产权限后发起绑定，并回传处理结果截图。",
    ),
]


def _status_label(status: str) -> str:
    return {
        "draft": "草稿",
        "pending_payment": "待付款",
        "payment_review": "水单审核",
        "pending_opening": "待开户",
        "opening": "开户中",
        "binding_card": "绑卡设限额",
        "pending_delivery": "待交付",
        "delivered": "已交付",
        "exception": "异常",
    }.get(status, status)


@router.get("/dashboard", response_model=MediaOpsDashboard)
async def get_media_ops_dashboard(current_user: dict = Depends(get_current_user)):
    del current_user
    pending_orders = [order for order in ORDERS if order.status != "delivered"]
    pending_vouchers = [voucher for voucher in VOUCHERS if voucher.status == "pending_review"]
    open_tickets = [ticket for ticket in TICKETS if ticket.status != "resolved"]
    abnormal_accounts = [account for account in ACCOUNTS if account.status in {"frozen", "banned", "verifying"}]

    status_order = [
        "pending_payment",
        "payment_review",
        "pending_opening",
        "opening",
        "binding_card",
        "pending_delivery",
        "delivered",
        "exception",
    ]
    status_funnel = [
        {
            "status": status,
            "label": _status_label(status),
            "count": len([order for order in ORDERS if order.status == status]),
        }
        for status in status_order
    ]

    return MediaOpsDashboard(
        metrics={
            "today_orders": len([order for order in ORDERS if order.created_at.startswith("2026-05-09")]),
            "pending_orders": len(pending_orders),
            "pending_payment_reviews": len(pending_vouchers),
            "accounts_to_deliver": len([account for account in ACCOUNTS if account.status == "pending_delivery"]),
            "open_tickets": len(open_tickets),
            "abnormal_accounts": len(abnormal_accounts),
            "today_receivable_usd": sum(order.receivable_amount for order in ORDERS if order.created_at.startswith("2026-05-09")),
        },
        status_funnel=status_funnel,
        pending_tasks=[
            {"type": "payment_review", "title": "审核 EASTAR 3000 USDT 水单", "owner": "Finance", "priority": "high"},
            {"type": "account_delivery", "title": "NKH Club 账户绑卡设限额后交付", "owner": "Sea Satr", "priority": "normal"},
            {"type": "ticket", "title": "EASTAR 冻结账户解冻处理", "owner": "Lijuci", "priority": "urgent"},
        ],
        alerts=[
            {"level": "warning", "message": "有 1 个账户处于冻结状态，需在 SLA 内处理。"},
            {"level": "info", "message": "充值窗口为 10:00-24:00，系统将对超时水单标记风险。"},
        ],
    )


@router.get("/customers", response_model=list[MediaCustomer])
async def list_customers(current_user: dict = Depends(get_current_user)):
    del current_user
    return CUSTOMERS


@router.get("/products", response_model=list[MediaProduct])
async def list_products(current_user: dict = Depends(get_current_user)):
    del current_user
    return PRODUCTS


@router.get("/orders", response_model=list[AccountOrder])
async def list_orders(status: str | None = None, current_user: dict = Depends(get_current_user)):
    del current_user
    if status:
        return [order for order in ORDERS if order.status == status]
    return ORDERS


@router.post("/orders", response_model=AccountOrder, status_code=201)
async def create_order(request: AccountOrderCreateRequest, current_user: dict = Depends(get_current_user)):
    del current_user
    customer = next((item for item in CUSTOMERS if item.id == request.customer_id), None)
    product = next((item for item in PRODUCTS if item.id == request.product_id), None)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    amount = product.min_recharge_usd * request.quantity
    order = AccountOrder(
        id=f"AO-{NOW.strftime('%y%m%d')}-{len(ORDERS) + 1:03d}",
        customer_id=customer.id,
        customer_name=customer.name,
        product_id=product.id,
        product_name=product.name,
        platform=product.platform,
        account_type=product.account_type,
        timezone=request.timezone,
        email=request.email,
        quantity=request.quantity,
        ad_industry=request.ad_industry,
        payment_method=request.payment_method,
        receivable_amount=amount,
        status="pending_payment",
        owner=customer.owner,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
        next_action="等待客户付款并上传水单",
        remark=request.remark,
    )
    ORDERS.insert(0, order)
    return order


@router.get("/payments", response_model=list[PaymentVoucher])
async def list_payment_vouchers(current_user: dict = Depends(get_current_user)):
    del current_user
    return VOUCHERS


@router.get("/accounts", response_model=list[MediaAccount])
async def list_media_accounts(status: str | None = None, current_user: dict = Depends(get_current_user)):
    del current_user
    if status:
        return [account for account in ACCOUNTS if account.status == status]
    return ACCOUNTS


@router.get("/tickets", response_model=list[ServiceTicket])
async def list_service_tickets(current_user: dict = Depends(get_current_user)):
    del current_user
    return TICKETS


@router.get("/knowledge", response_model=list[KnowledgeArticle])
async def list_knowledge_articles(keyword: str | None = None, current_user: dict = Depends(get_current_user)):
    del current_user
    if not keyword:
        return ARTICLES
    query = keyword.lower()
    return [
        article for article in ARTICLES
        if query in article.title.lower()
        or query in article.answer.lower()
        or any(query in item.lower() for item in article.trigger_keywords)
    ]
