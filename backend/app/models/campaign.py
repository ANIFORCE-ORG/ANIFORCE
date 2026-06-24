"""广告投放模型"""
import uuid
import enum
import json
from datetime import datetime
from sqlalchemy import String, Float, DateTime, Enum, Text, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base


class CampaignStatus(str, enum.Enum):
    """广告投放状态"""
    DRAFT = "draft"
    RUNNING = "running"
    REVIEW = "review"
    PAUSED = "paused"
    COMPLETED = "completed"


class Platform(str, enum.Enum):
    """投放平台"""
    TikTok = "TikTok"
    Google = "Google"
    Meta = "Meta"


class Campaign(Base):
    """广告系列模型 - 对应 Meta Ad Set 层级"""
    __tablename__ = "campaigns"

    # 主键和外键
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="广告系列唯一标识")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属项目ID")

    # 基本信息
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="广告系列名称，对应前端的Campaign名称字段")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="广告系列描述")

    # 投放平台配置
    platform: Mapped[Platform] = mapped_column(Enum(Platform, native_enum=False), nullable=False, index=True, comment="投放平台: TikTok, Google, Meta")
    account_id: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="广告账户ID，对应 sub_account_bindings.sub_account_id")
    platform_campaign_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True, comment="平台广告系列ID，用于与Meta/Google/TikTok平台创建的Campaign ID进行绑定同步")
    countries: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="投放国家，例如：美国 / 加拿大")

    # Meta广告特定字段（对应前端表单）
    objective: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="广告目标，例如：App promotion, Conversions, Traffic")
    buying_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="购买类型，例如：Auction, Reserved")
    special_ad_categories: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="特殊广告类别，例如：None, Credit, Employment, Housing")
    special_ad_category_country: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="特殊广告类别国家列表，JSON数组格式，例如：[\"US\", \"CA\"]")
    promoted_object: Mapped[str | None] = mapped_column(Text, nullable=True, comment="推广对象配置，JSON格式，包含 application_id, pixel_id, page_id 等")

    # A/B测试和预算配置
    ab_test: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="A/B测试开关：开启/关闭")
    campaign_budget_optimization: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Campaign预算优化开关：开启/关闭")
    budget_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="预算类型：Daily budget / Lifetime budget")
    budget: Mapped[float] = mapped_column(Float, nullable=False, comment="预算金额")
    budget_schedule_specs: Mapped[str | None] = mapped_column(Text, nullable=True, comment="预算排期规格，JSON数组格式")
    pacing_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="投放节奏类型：standard, day_parting")

    # 出价策略
    bid_strategy: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="出价策略：Lowest cost, Cost cap, Bid cap, ROAS goal")
    spend_limit: Mapped[float | None] = mapped_column(Float, nullable=True, comment="花费限制金额")

    # 投放周期
    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True, comment="投放开始日期")
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True, comment="投放结束日期")

    # 状态和花费
    spent: Mapped[float] = mapped_column(Float, default=0.0, comment="已花费金额")
    status: Mapped[CampaignStatus] = mapped_column(Enum(CampaignStatus, native_enum=False), default=CampaignStatus.DRAFT, index=True, comment="广告系列状态: draft, running, review, paused, completed")

    # 素材管理
    material_ids: Mapped[str | None] = mapped_column(Text, nullable=True, comment="关联的素材ID列表，JSON数组格式")

    # 扩展配置
    config: Mapped[str | None] = mapped_column(Text, nullable=True, comment="其他配置信息，JSON格式")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关系
    project: Mapped["Project"] = relationship(back_populates="campaigns")
    metrics: Mapped[list["Metric"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")

    # 辅助方法
    def get_material_ids(self) -> list[str]:
        """获取素材 ID 列表"""
        if not self.material_ids:
            return []
        return json.loads(self.material_ids)

    def set_material_ids(self, ids: list[str]) -> None:
        """设置素材 ID 列表"""
        self.material_ids = json.dumps(ids)

    def add_material(self, material_id: str) -> None:
        """添加素材"""
        ids = self.get_material_ids()
        if material_id not in ids:
            ids.append(material_id)
            self.set_material_ids(ids)

    def remove_material(self, material_id: str) -> None:
        """移除素材"""
        ids = self.get_material_ids()
        if material_id in ids:
            ids.remove(material_id)
            self.set_material_ids(ids)
