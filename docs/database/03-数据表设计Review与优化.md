# 数据表设计 Review 与优化方案

## 一、前端页面分析

### 1.1 Projects 页面分析 (`Projects.vue`)

**核心数据结构**:
```javascript
{
  id: 'proj_001',
  name: 'Candy Blast - 全球推广',
  status: 'active' | 'paused' | 'completed',
  platform: 'Meta' | 'TikTok' | 'Google Ads' | 'Unity Ads',
  budget: '$80,000',
  spent: '$52,300',
  roi: '1.88x',
  installs: '15,420',
  cpi: '$3.39',
  progress: 65,              // 预算使用进度百分比
  startDate: '2024-01-15',
  endDate: '2024-03-15',
  manager: '李明',           // 项目负责人
  tags: ['休闲游戏', '三消', '北美']
}
```

**关键功能**:
- 项目列表展示（按状态筛选）
- 项目搜索（名称、标签）
- 项目创建
- 项目详情查看

### 1.2 Campaign 页面分析 (`Campaign.vue`)

**核心数据结构**:
```javascript
{
  id: 'camp_g001',
  name: 'CB_US_Android_Install_001',
  project_id: 'proj_game_001',        // ⭐ 关键：关联到项目
  project_name: 'Candy Blast 美加英投放',
  platform: 'Google' | 'TikTok' | 'Meta',
  status: 'running' | 'review' | 'paused',
  spend: 22800,
  installs: 8750,
  roi: 1.85,
  budget: 30000,
  start_date: '2026-02-01'
}
```

**关键关系**:
- Campaign 通过 `project_id` 关联到 Project
- 支持按项目筛选 Campaign
- 一个 Project 可以有多个 Campaign

## 二、当前数据表设计问题

### 2.1 现有表结构

#### users 表 ✅
```sql
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```
**评估**: 合理，无需修改

#### campaigns 表 ❌ 缺少 project_id
```sql
CREATE TABLE campaigns (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),  -- ❌ 直接关联用户
    name VARCHAR(255) NOT NULL,
    game_type VARCHAR(50) NOT NULL,
    budget DECIMAL(12,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```
**问题**:
1. ❌ 缺少 `project_id` 字段
2. ❌ 直接关联 `user_id`，应该通过 Project 间接关联
3. ❌ 缺少 `platform` 字段
4. ❌ 缺少 `start_date`、`end_date` 字段
5. ❌ `game_type` 字段应该在 Project 层级

#### materials 表 ⚠️ 需要调整
```sql
CREATE TABLE materials (
    id VARCHAR(36) PRIMARY KEY,
    campaign_id VARCHAR(36) NOT NULL REFERENCES campaigns(id),
    type VARCHAR(20) NOT NULL,
    url TEXT NOT NULL,
    ctr_estimate DECIMAL(5,2),
    tags TEXT[],
    created_at TIMESTAMP
);
```
**问题**:
1. ⚠️ 关联 `campaign_id` 合理，但可能需要同时关联 `project_id`（便于项目级素材管理）

#### metrics 表 ✅
```sql
CREATE TABLE metrics (
    id VARCHAR(36) PRIMARY KEY,
    campaign_id VARCHAR(36) NOT NULL REFERENCES campaigns(id),
    timestamp TIMESTAMP,
    platform VARCHAR(50) NOT NULL,
    impressions INTEGER,
    clicks INTEGER,
    conversions INTEGER,
    spend DECIMAL(12,2),
    revenue DECIMAL(12,2),
    ctr DECIMAL(5,2),
    cvr DECIMAL(5,2),
    cpa DECIMAL(12,2),
    roi DECIMAL(8,2)
);
```
**评估**: 合理，无需修改

### 2.2 核心问题总结

| 问题 | 影响 | 优先级 |
|------|------|--------|
| **缺少 projects 表** | 无法管理项目层级，Campaign 直接挂在用户下 | 🔴 高 |
| Campaign 缺少 project_id | 无法按项目筛选 Campaign | 🔴 高 |
| Campaign 缺少 platform | 无法按平台筛选 | 🟡 中 |
| Campaign 缺少时间字段 | 无法管理投放周期 | 🟡 中 |
| 数据层级混乱 | User → Campaign 应该是 User → Project → Campaign | 🔴 高 |

## 三、优化后的数据表设计

### 3.1 数据层级关系

```
User (用户)
  ↓ 1:N
Project (项目)
  ↓ 1:N
Campaign (广告投放)
  ↓ 1:N
Material (素材)

Campaign → Metrics (监控数据)
```

### 3.2 新增 projects 表

```sql
CREATE TABLE projects (
    -- 基础字段
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- 项目信息
    game_type VARCHAR(50),                    -- 游戏类型：RPG、休闲、短剧等
    target_market VARCHAR(100),               -- 目标市场：北美、东南亚等
    tags TEXT,                                -- JSON 数组：['休闲游戏', '三消', '北美']
    
    -- 预算和状态
    total_budget DECIMAL(12,2) NOT NULL,      -- 总预算
    spent DECIMAL(12,2) DEFAULT 0,            -- 已消耗
    status VARCHAR(20) DEFAULT 'active',      -- active, paused, completed
    
    -- 负责人和时间
    manager VARCHAR(100),                     -- 项目负责人
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_projects_user_id (user_id),
    INDEX idx_projects_status (status),
    INDEX idx_projects_dates (start_date, end_date)
);
```

**字段说明**:
- `user_id`: 项目所属用户
- `name`: 项目名称（如 "Candy Blast - 全球推广"）
- `game_type`: 游戏类型（RPG、休闲、短剧等）
- `target_market`: 目标市场（北美、东南亚等）
- `tags`: JSON 数组存储标签
- `total_budget`: 项目总预算
- `spent`: 已消耗金额（聚合所有 Campaign）
- `status`: 项目状态（active, paused, completed）
- `manager`: 项目负责人
- `start_date`/`end_date`: 项目周期

### 3.3 优化 campaigns 表

```sql
CREATE TABLE campaigns (
    -- 基础字段
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,  -- ⭐ 关联项目
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- 投放配置
    platform VARCHAR(50) NOT NULL,            -- Meta, TikTok, Google, Unity Ads
    budget DECIMAL(12,2) NOT NULL,            -- 广告预算
    spent DECIMAL(12,2) DEFAULT 0,            -- 已消耗
    status VARCHAR(20) DEFAULT 'draft',       -- draft, running, review, paused, completed
    
    -- 投放周期
    start_date DATE,
    end_date DATE,
    
    -- 配置和元数据
    config TEXT,                              -- JSON 配置
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_campaigns_project_id (project_id),
    INDEX idx_campaigns_platform (platform),
    INDEX idx_campaigns_status (status),
    INDEX idx_campaigns_dates (start_date, end_date)
);
```

**关键变更**:
1. ✅ 添加 `project_id` 外键（关联 projects 表）
2. ✅ 添加 `platform` 字段
3. ✅ 添加 `start_date`、`end_date` 字段
4. ✅ 移除 `user_id`（通过 project 间接关联）
5. ✅ 移除 `game_type`（移到 project 层级）
6. ✅ 将 `config` 改为 TEXT（SQLite 用 TEXT 存储 JSON）

### 3.4 优化 materials 表

```sql
CREATE TABLE materials (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,  -- ⭐ 关联项目
    campaign_id VARCHAR(36) REFERENCES campaigns(id) ON DELETE SET NULL,       -- 可选关联 Campaign
    
    -- 素材信息
    name VARCHAR(255),
    type VARCHAR(20) NOT NULL,                -- a_segment, b_segment, c_segment, full_video
    url TEXT NOT NULL,
    thumbnail_url TEXT,
    
    -- 预估数据
    ctr_estimate DECIMAL(5,2),
    tags TEXT,                                -- JSON 数组
    
    -- 元数据
    duration INTEGER,                         -- 视频时长（秒）
    file_size INTEGER,                        -- 文件大小（字节）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_materials_project_id (project_id),
    INDEX idx_materials_campaign_id (campaign_id),
    INDEX idx_materials_type (type)
);
```

**关键变更**:
1. ✅ 添加 `project_id` 外键（项目级素材管理）
2. ✅ `campaign_id` 改为可选（素材可以先创建，后关联 Campaign）
3. ✅ 添加 `name` 字段
4. ✅ 添加 `thumbnail_url`（缩略图）
5. ✅ 添加 `duration`、`file_size` 元数据

### 3.5 metrics 表（无需修改）

```sql
CREATE TABLE metrics (
    id VARCHAR(36) PRIMARY KEY,
    campaign_id VARCHAR(36) NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    platform VARCHAR(50) NOT NULL,
    
    -- 核心指标
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    installs INTEGER DEFAULT 0,              -- ⭐ 添加安装数
    
    -- 成本指标
    spend DECIMAL(12,2) DEFAULT 0,
    revenue DECIMAL(12,2) DEFAULT 0,
    
    -- 转化指标
    ctr DECIMAL(5,2) DEFAULT 0,
    cvr DECIMAL(5,2) DEFAULT 0,
    cpa DECIMAL(12,2) DEFAULT 0,
    cpi DECIMAL(12,2) DEFAULT 0,             -- ⭐ 添加 CPI
    roi DECIMAL(8,2) DEFAULT 0,
    
    -- 索引
    INDEX idx_metrics_campaign_timestamp (campaign_id, timestamp)
);
```

**关键变更**:
1. ✅ 添加 `installs` 字段（安装数）
2. ✅ 添加 `cpi` 字段（每安装成本）

## 四、完整 ER 图

```
┌─────────────────┐
│     users       │
│─────────────────│
│ id (PK)         │
│ email           │
│ password_hash   │
│ name            │
│ created_at      │
│ updated_at      │
└─────────────────┘
        │ 1
        │
        │ N
┌─────────────────┐
│    projects     │
│─────────────────│
│ id (PK)         │
│ user_id (FK)    │◄─────────┐
│ name            │          │
│ game_type       │          │
│ target_market   │          │
│ tags            │          │
│ total_budget    │          │
│ spent           │          │
│ status          │          │
│ manager         │          │
│ start_date      │          │
│ end_date        │          │
│ created_at      │          │
│ updated_at      │          │
└─────────────────┘          │
        │ 1                  │
        │                    │
        │ N                  │
┌─────────────────┐          │
│   campaigns     │          │
│─────────────────│          │
│ id (PK)         │          │
│ project_id (FK) │──────────┘
│ name            │
│ platform        │
│ budget          │
│ spent           │
│ status          │
│ start_date      │
│ end_date        │
│ config          │
│ created_at      │
│ updated_at      │
└─────────────────┘
        │ 1
        ├──────────────┐
        │ N            │ N
┌─────────────────┐  ┌─────────────────┐
│   materials     │  │    metrics      │
│─────────────────│  │─────────────────│
│ id (PK)         │  │ id (PK)         │
│ project_id (FK) │  │ campaign_id (FK)│
│ campaign_id (FK)│  │ timestamp       │
│ name            │  │ platform        │
│ type            │  │ impressions     │
│ url             │  │ clicks          │
│ thumbnail_url   │  │ conversions     │
│ ctr_estimate    │  │ installs        │
│ tags            │  │ spend           │
│ duration        │  │ revenue         │
│ file_size       │  │ ctr             │
│ created_at      │  │ cvr             │
└─────────────────┘  │ cpa             │
                     │ cpi             │
                     │ roi             │
                     └─────────────────┘

┌─────────────────────────────┐
│      chat_sessions          │
│      (MongoDB)              │
│─────────────────────────────│
│ session_id                  │
│ user_id                     │
│ messages: [...]             │
│ game_info: {...}            │
│ analysis: {...}             │
│ created_at                  │
│ updated_at                  │
└─────────────────────────────┘
```

## 五、SQLAlchemy ORM 模型定义

### 5.1 Project 模型

```python
# app/models/project.py
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Float, DateTime, Enum, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base

class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"

class Project(Base):
    __tablename__ = "projects"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # 项目信息
    game_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_market: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    
    # 预算和状态
    total_budget: Mapped[float] = mapped_column(Float, nullable=False)
    spent: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE)
    
    # 负责人和时间
    manager: Mapped[str | None] = mapped_column(String(100), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    materials: Mapped[list["Material"]] = relationship(back_populates="project", cascade="all, delete-orphan")
```

### 5.2 Campaign 模型（更新）

```python
# app/models/campaign.py
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Float, DateTime, Enum, Text, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base

class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    RUNNING = "running"
    REVIEW = "review"
    PAUSED = "paused"
    COMPLETED = "completed"

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # 投放配置
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    budget: Mapped[float] = mapped_column(Float, nullable=False)
    spent: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[CampaignStatus] = mapped_column(Enum(CampaignStatus), default=CampaignStatus.DRAFT, index=True)
    
    # 投放周期
    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    
    # 配置
    config: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    project: Mapped["Project"] = relationship(back_populates="campaigns")
    materials: Mapped[list["Material"]] = relationship(back_populates="campaign")
    metrics: Mapped[list["Metric"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
```

### 5.3 Material 模型（更新）

```python
# app/models/material.py
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Float, DateTime, Enum, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base

class MaterialType(str, enum.Enum):
    A_SEGMENT = "a_segment"
    B_SEGMENT = "b_segment"
    C_SEGMENT = "c_segment"
    FULL_VIDEO = "full_video"

class Material(Base):
    __tablename__ = "materials"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # 素材信息
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type: Mapped[MaterialType] = mapped_column(Enum(MaterialType), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # 预估数据
    ctr_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    
    # 元数据
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关系
    project: Mapped["Project"] = relationship(back_populates="materials")
    campaign: Mapped["Campaign | None"] = relationship(back_populates="materials")
```

### 5.4 Metric 模型（更新）

```python
# app/models/metric.py
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base

class Metric(Base):
    __tablename__ = "metrics"
    __table_args__ = (
        Index("ix_metrics_campaign_timestamp", "campaign_id", "timestamp"),
    )
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # 核心指标
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    installs: Mapped[int] = mapped_column(Integer, default=0)
    
    # 成本指标
    spend: Mapped[float] = mapped_column(Float, default=0.0)
    revenue: Mapped[float] = mapped_column(Float, default=0.0)
    
    # 转化指标
    ctr: Mapped[float] = mapped_column(Float, default=0.0)
    cvr: Mapped[float] = mapped_column(Float, default=0.0)
    cpa: Mapped[float] = mapped_column(Float, default=0.0)
    cpi: Mapped[float] = mapped_column(Float, default=0.0)
    roi: Mapped[float] = mapped_column(Float, default=0.0)
    
    # 关系
    campaign: Mapped["Campaign"] = relationship(back_populates="metrics")
```

## 六、Repository Protocol 更新

### 6.1 新增 ProjectRepository

```python
# app/repositories/protocols.py
from typing import Protocol, runtime_checkable

@runtime_checkable
class ProjectRepository(Protocol):
    """项目数据访问协议"""
    async def create(
        self, user_id: str, name: str, total_budget: float, **kwargs
    ) -> dict: ...
    
    async def get_by_id(self, project_id: str) -> dict | None: ...
    
    async def list_by_user(
        self, user_id: str, status: str | None = None, limit: int = 20
    ) -> list[dict]: ...
    
    async def update(self, project_id: str, **kwargs) -> None: ...
    
    async def update_spent(self, project_id: str, amount: float) -> None: ...
    
    async def delete(self, project_id: str) -> None: ...
```

### 6.2 更新 CampaignRepository

```python
@runtime_checkable
class CampaignRepository(Protocol):
    """投放数据访问协议"""
    async def create(
        self, project_id: str, name: str, platform: str, budget: float, **kwargs
    ) -> dict: ...
    
    async def get_by_id(self, campaign_id: str) -> dict | None: ...
    
    async def list_by_project(
        self, project_id: str, status: str | None = None, limit: int = 20
    ) -> list[dict]: ...
    
    async def update_status(self, campaign_id: str, status: str) -> None: ...
    
    async def update_spent(self, campaign_id: str, amount: float) -> None: ...
    
    async def delete(self, campaign_id: str) -> None: ...
```

## 七、数据迁移策略

### 7.1 Alembic 迁移脚本

```python
# alembic/versions/xxx_add_projects_table.py
"""Add projects table and update campaigns

Revision ID: xxx
Revises: xxx
Create Date: 2024-03-22

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # 1. 创建 projects 表
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('game_type', sa.String(50), nullable=True),
        sa.Column('target_market', sa.String(100), nullable=True),
        sa.Column('tags', sa.Text, nullable=True),
        sa.Column('total_budget', sa.Float, nullable=False),
        sa.Column('spent', sa.Float, default=0.0),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('manager', sa.String(100), nullable=True),
        sa.Column('start_date', sa.Date, nullable=True),
        sa.Column('end_date', sa.Date, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_projects_user_id', 'projects', ['user_id'])
    op.create_index('idx_projects_status', 'projects', ['status'])
    
    # 2. 添加 campaigns.project_id 字段
    op.add_column('campaigns', sa.Column('project_id', sa.String(36), nullable=True))
    op.add_column('campaigns', sa.Column('platform', sa.String(50), nullable=True))
    op.add_column('campaigns', sa.Column('start_date', sa.Date, nullable=True))
    op.add_column('campaigns', sa.Column('end_date', sa.Date, nullable=True))
    
    # 3. 数据迁移：为每个 campaign 创建对应的 project
    # （需要根据实际数据情况编写迁移逻辑）
    
    # 4. 设置 project_id 为 NOT NULL
    op.alter_column('campaigns', 'project_id', nullable=False)
    op.create_foreign_key('fk_campaigns_project_id', 'campaigns', 'projects', ['project_id'], ['id'], ondelete='CASCADE')
    op.create_index('idx_campaigns_project_id', 'campaigns', ['project_id'])
    
    # 5. 删除 campaigns.user_id 字段
    op.drop_column('campaigns', 'user_id')
    op.drop_column('campaigns', 'game_type')
    
    # 6. 更新 materials 表
    op.add_column('materials', sa.Column('project_id', sa.String(36), nullable=True))
    op.add_column('materials', sa.Column('name', sa.String(255), nullable=True))
    op.add_column('materials', sa.Column('thumbnail_url', sa.Text, nullable=True))
    op.add_column('materials', sa.Column('duration', sa.Integer, nullable=True))
    op.add_column('materials', sa.Column('file_size', sa.Integer, nullable=True))
    
    # 7. 设置 materials.project_id 为 NOT NULL
    op.alter_column('materials', 'project_id', nullable=False)
    op.create_foreign_key('fk_materials_project_id', 'materials', 'projects', ['project_id'], ['id'], ondelete='CASCADE')
    op.alter_column('materials', 'campaign_id', nullable=True)
    
    # 8. 更新 metrics 表
    op.add_column('metrics', sa.Column('installs', sa.Integer, default=0))
    op.add_column('metrics', sa.Column('cpi', sa.Float, default=0.0))

def downgrade():
    # 回滚操作
    pass
```

## 八、实施建议

### 8.1 实施步骤

1. **创建 Project 模型和 Repository**
2. **更新 Campaign、Material、Metric 模型**
3. **创建 Alembic 迁移脚本**
4. **更新 Service 层逻辑**
5. **更新 API 接口**
6. **前后端联调测试**

### 8.2 向后兼容性

- Mock Repository 需要同步更新
- API 接口保持向后兼容（可选）
- 前端逐步迁移到新的数据结构

---

**总结**: 添加 projects 表是必要的，可以更好地组织数据层级，符合前端页面的业务逻辑。建议立即实施。
