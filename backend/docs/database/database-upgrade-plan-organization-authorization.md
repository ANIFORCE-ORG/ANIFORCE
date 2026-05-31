# 数据库升级方案：组织层级与账号授权

## 📋 需求概述

### 1. 组织层级结构
- 引入 **Organization（组织）** 概念
- 组织内用户分为两种角色：
  - **管理员（Admin）**：可以管理组织成员
  - **成员（Member）**：普通成员

### 2. 账号授权机制
- 平台连接的**创建者**可以将账号授权给其他用户
- 支持**多层级授权**：
  - **母账号级别授权**：授权整个平台连接，被授权用户可使用该连接下的所有子账号
  - **子账号级别授权**：授权特定的子账号，被授权用户只能使用被授权的子账号
- 被授权用户拥有**使用权**（只读 + 执行）
- 被授权用户**没有修改和查看敏感信息的权利**

---

## 🏗️ 数据库设计方案

### 新增表结构

#### 1. `organizations` - 组织表

```sql
CREATE TABLE organizations (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    org_code VARCHAR(50) UNIQUE NOT NULL,  -- 组织代码，用于加入团队检索
    description TEXT,
    owner_id VARCHAR(36) NOT NULL,  -- 组织创建者
    invite_code VARCHAR(100) ,  -- 邀请码
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'dismissed'
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_owner_id (owner_id),
    INDEX idx_status (status)
);
```

**字段说明**：
- `id`: 组织唯一标识（UUID）
- `name`: 组织名称
- `description`: 组织描述
- `owner_id`: 组织创建者/拥有者
- `status`: 组织状态（活跃、停用、暂停）
- `created_at/updated_at`: 时间戳

---

#### 2. `organization_members` - 组织成员表

```sql
CREATE TABLE organization_members (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    role VARCHAR(20) NOT NULL,  -- 'admin', 'member'
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'invited'
    invited_by VARCHAR(36),  -- 邀请人
    joined_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (invited_by) REFERENCES users(id) ON DELETE SET NULL,
    
    UNIQUE KEY uq_org_user (organization_id, user_id),
    INDEX idx_organization_id (organization_id),
    INDEX idx_user_id (user_id),
    INDEX idx_role (role)
);
```

**字段说明**：
- `id`: 成员关系唯一标识
- `organization_id`: 所属组织
- `user_id`: 用户ID
- `role`: 角色（admin 管理员 / member 成员）
- `status`: 成员状态（活跃、停用、已邀请）
- `invited_by`: 邀请人ID
- `joined_at`: 加入时间

**约束**：
- 唯一约束：一个用户在一个组织中只能有一个角色
- 级联删除：删除组织或用户时，自动删除成员关系

---

#### 3. `platform_connection_authorizations` - 平台连接授权表（多态设计）

**设计说明**：采用多态授权设计，支持母账号级别和子账号级别的授权。

```sql
CREATE TABLE platform_connection_authorizations (
    id VARCHAR(36) PRIMARY KEY,
    
    -- 多态授权资源
    resource_type VARCHAR(50) NOT NULL,  -- 'platform_connection' 或 'sub_account'
    resource_id VARCHAR(36) NOT NULL,    -- PlatformConnection.id 或 SubAccountBinding.id
    
    -- 授权关系
    owner_id VARCHAR(36) NOT NULL,  -- 资源的创建者/拥有者
    authorized_user_id VARCHAR(36) NOT NULL,  -- 被授权的用户
    
    -- 权限信息
    permission_level VARCHAR(20) NOT NULL,  -- 'read', 'execute', 'read_execute'
    scope TEXT,  -- 授权范围（JSON 格式，可选）
    
    -- 状态管理
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'revoked', 'expired'
    expires_at DATETIME,  -- 授权过期时间（可选）
    revoked_at DATETIME,  -- 撤销时间
    revoked_by VARCHAR(36),  -- 撤销人
    
    -- 时间戳
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    
    -- 外键约束
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (authorized_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (revoked_by) REFERENCES users(id) ON DELETE SET NULL,
    
    -- 唯一约束和索引
    UNIQUE KEY uq_resource_user (resource_type, resource_id, authorized_user_id),
    INDEX ix_resource (resource_type, resource_id),
    INDEX idx_owner_id (owner_id),
    INDEX idx_authorized_user_id (authorized_user_id),
    INDEX idx_status (status)
);
```

**字段说明**：
- `id`: 授权记录唯一标识
- `resource_type`: 授权资源类型
  - `platform_connection`: 母账号级别授权（授权整个平台连接及其所有子账号）
  - `sub_account`: 子账号级别授权（仅授权特定子账号）
- `resource_id`: 资源ID（根据 resource_type 指向不同的表）
- `owner_id`: 资源的创建者/拥有者
- `authorized_user_id`: 被授权的用户ID
- `permission_level`: 权限级别
  - `read`: 只读（查看基本信息）
  - `execute`: 执行（使用账号进行操作）
  - `read_execute`: 读取 + 执行
- `scope`: 授权范围（JSON 格式，可定义具体权限）
- `status`: 授权状态（活跃、已撤销、已过期）
- `expires_at`: 授权过期时间
- `revoked_at/revoked_by`: 撤销信息

**约束**：
- 唯一约束：同一资源对同一用户只能有一个授权记录
- 级联删除：删除用户时，自动删除授权记录
- 复合索引：`(resource_type, resource_id)` 提高查询效率

**授权场景示例**：

1. **授权整个母账号**：
   ```sql
   INSERT INTO platform_connection_authorizations 
   (resource_type, resource_id, owner_id, authorized_user_id, permission_level)
   VALUES ('platform_connection', 'conn_123', 'user_a', 'user_b', 'read_execute');
   ```
   效果：用户 B 可以使用该母账号下的所有子账号

2. **授权特定子账号**：
   ```sql
   INSERT INTO platform_connection_authorizations 
   (resource_type, resource_id, owner_id, authorized_user_id, permission_level)
   VALUES ('sub_account', 'sub_456', 'user_a', 'user_c', 'read_execute');
   ```
   效果：用户 C 只能使用该特定子账号

3. **混合授权**：
   - 用户 A 授权整个母账号 X 给用户 B（B 可使用 X 的所有子账号）
   - 用户 A 授权母账号 Y 的子账号 Y1、Y2 给用户 C（C 只能使用 Y1、Y2）

---

### 修改现有表结构

#### 修改 `platform_connections` 表

添加 `owner_id` 字段，明确标识连接的创建者：

```sql
ALTER TABLE platform_connections 
ADD COLUMN owner_id VARCHAR(36) NOT NULL DEFAULT user_id;

ALTER TABLE platform_connections
ADD CONSTRAINT fk_platform_connections_owner 
FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE;

CREATE INDEX idx_platform_connections_owner_id ON platform_connections(owner_id);
```

**说明**：
- `owner_id`: 连接的创建者/拥有者
- 默认值为 `user_id`，保持向后兼容
- 为未来支持组织级别的连接预留空间

---

## 📊 更新后的数据库关系图

### 完整 ER 图

```
┌─────────────────────┐
│   Organization      │ (组织)
│   - id (PK)         │
│   - name            │
│   - owner_id (FK)   │
│   - status          │
└──────────┬──────────┘
           │ 1
           │ owns
           │
           │ N
┌──────────▼──────────────────┐
│  OrganizationMember         │ (组织成员)
│  - id (PK)                  │
│  - organization_id (FK)     │
│  - user_id (FK)             │
│  - role (admin/member)      │
│  - status                   │
└─────────────────────────────┘
           │
           │
           │
┌──────────▼──────────┐
│       User          │ (用户)
│  - id (PK)          │
│  - email            │
│  - password_hash    │
│  - name             │
└──────────┬──────────┘
           │ 1
           │ owns
           │
           │ N
┌──────────▼──────────────────────┐
│   PlatformConnection            │ (平台连接/母账号)
│   - id (PK)                     │
│   - user_id (FK)                │
│   - owner_id (FK)               │
│   - platform                    │
│   - account_id                  │
│   - access_token                │
│   - refresh_token               │
│   - status                      │
└──────────┬──────────────────────┘
           │ 1
           │ has
           │
           │ N
┌──────────▼──────────────────────┐
│   SubAccountBinding             │ (子账号绑定)
│   - id (PK)                     │
│   - parent_connection_id (FK)   │
│   - sub_account_name            │
│   - customer_id                 │
│   - status                      │
└─────────────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│         PlatformConnectionAuthorization (多态授权)           │
│         - id (PK)                                           │
│         - resource_type ('platform_connection'/'sub_account')│
│         - resource_id (PK of resource)                      │
│         - owner_id (FK → users.id)                          │
│         - authorized_user_id (FK → users.id)                │
│         - permission_level                                  │
│         - status                                            │
│         - expires_at                                        │
└─────────────────────────────────────────────────────────────┘
           │                              │
           │ authorizes                   │ authorizes
           │                              │
           ▼                              ▼
  PlatformConnection              SubAccountBinding
  (母账号授权)                     (子账号授权)
```

### 授权关系详解

```
授权层级关系：

User A (拥有者)
    │
    ├─ PlatformConnection X (母账号)
    │       │
    │       ├─ SubAccount X1
    │       ├─ SubAccount X2
    │       └─ SubAccount X3
    │
    └─ PlatformConnection Y (母账号)
            │
            ├─ SubAccount Y1
            ├─ SubAccount Y2
            └─ SubAccount Y3

授权场景示例：

1. 母账号授权：
   User A → [授权整个 Connection X] → User B
   结果：User B 可使用 X1, X2, X3 所有子账号

2. 子账号授权：
   User A → [授权 SubAccount Y1, Y2] → User C
   结果：User C 只能使用 Y1, Y2，看不到 Y3

3. 混合授权：
   User A → [授权 Connection X] → User B
   User A → [授权 SubAccount Y1] → User C
   结果：
   - User B 可使用 X1, X2, X3
   - User C 只能使用 Y1
```

### 多态授权工作原理

```
PlatformConnectionAuthorization 表支持两种授权类型：

┌─────────────────────────────────────────────────────────┐
│ resource_type = 'platform_connection'                   │
│ resource_id = PlatformConnection.id                     │
│ → 授权整个母账号及其所有子账号                            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ resource_type = 'sub_account'                           │
│ resource_id = SubAccountBinding.id                      │
│ → 仅授权特定子账号                                        │
└─────────────────────────────────────────────────────────┘

权限检查优先级：
1. 拥有者 (owner_id) → 完全访问权限
2. 子账号直接授权 → 使用权限
3. 母账号授权（继承） → 使用权限
```

---

## 🔐 权限控制逻辑

### 1. 组织权限

#### 管理员权限
- ✅ 查看组织信息
- ✅ 修改组织信息
- ✅ 邀请/移除成员
- ✅ 修改成员角色
- ✅ 查看所有成员

#### 成员权限
- ✅ 查看组织信息
- ✅ 查看成员列表
- ❌ 修改组织信息
- ❌ 邀请/移除成员
- ❌ 修改成员角色

### 2. 平台连接授权权限

#### 创建者/拥有者权限
- ✅ 完全控制权（查看、修改、删除、授权）
- ✅ 查看所有敏感信息（token、secret）
- ✅ 授权给其他用户
- ✅ 撤销授权

#### 被授权用户权限（read_execute）
- ✅ 查看基本信息（账号名称、平台类型、状态）
- ✅ 使用账号进行广告投放等操作
- ❌ 查看敏感信息（access_token、refresh_token、account_secret）
- ❌ 修改连接配置
- ❌ 删除连接
- ❌ 授权给其他用户

---

## 📝 SQLAlchemy 模型定义

### 1. Organization 模型

```python
"""组织模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base


class Organization(Base):
    """组织模型"""
    __tablename__ = "organizations"
    
    # 主键
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 基本信息
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # 拥有者
    owner_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # 状态
    status: Mapped[str] = mapped_column(
        String(20), 
        default="active", 
        nullable=False,
        index=True
    )  # 'active', 'inactive', 'suspended'
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系
    owner: Mapped["User"] = relationship(back_populates="owned_organizations")
    members: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
```

### 2. OrganizationMember 模型

```python
"""组织成员模型"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base


class OrganizationMember(Base):
    """组织成员模型"""
    __tablename__ = "organization_members"
    
    # 主键
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 外键
    organization_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("organizations.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # 角色和状态
    role: Mapped[str] = mapped_column(
        String(20), 
        nullable=False,
        index=True
    )  # 'admin', 'member'
    status: Mapped[str] = mapped_column(
        String(20), 
        default="active", 
        nullable=False
    )  # 'active', 'inactive', 'invited'
    
    # 邀请信息
    invited_by: Mapped[Optional[str]] = mapped_column(
        String(36), 
        ForeignKey("users.id", ondelete="SET NULL"), 
        nullable=True
    )
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系
    organization: Mapped["Organization"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    inviter: Mapped[Optional["User"]] = relationship(foreign_keys=[invited_by])
    
    # 约束
    __table_args__ = (
        UniqueConstraint('organization_id', 'user_id', name='uq_org_user'),
    )
```

### 3. PlatformConnectionAuthorization 模型（多态授权）

```python
"""平台连接授权模型 - 支持多层级授权"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base


class PlatformConnectionAuthorization(Base):
    """平台连接授权模型 - 支持母账号和子账号授权"""
    __tablename__ = "platform_connection_authorizations"
    
    # 主键
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 多态授权资源
    resource_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        index=True
    )  # 'platform_connection' 或 'sub_account'
    
    resource_id: Mapped[str] = mapped_column(
        String(36), 
        nullable=False,
        index=True
    )  # PlatformConnection.id 或 SubAccountBinding.id
    
    # 授权关系
    owner_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    authorized_user_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # 权限信息
    permission_level: Mapped[str] = mapped_column(
        String(20), 
        nullable=False
    )  # 'read', 'execute', 'read_execute'
    scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON 格式
    
    # 状态管理
    status: Mapped[str] = mapped_column(
        String(20), 
        default="active", 
        nullable=False,
        index=True
    )  # 'active', 'revoked', 'expired'
    
    # 过期和撤销信息
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked_by: Mapped[Optional[str]] = mapped_column(
        String(36), 
        ForeignKey("users.id", ondelete="SET NULL"), 
        nullable=True
    )
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系
    owner: Mapped["User"] = relationship(foreign_keys=[owner_id])
    authorized_user: Mapped["User"] = relationship(foreign_keys=[authorized_user_id])
    revoker: Mapped[Optional["User"]] = relationship(foreign_keys=[revoked_by])
    
    # 约束和索引
    __table_args__ = (
        UniqueConstraint('resource_type', 'resource_id', 'authorized_user_id', name='uq_resource_user'),
        Index('ix_resource', 'resource_type', 'resource_id'),
    )
```

---

## 🔄 数据迁移步骤

### 步骤 1: 创建新表

```bash
# 创建 Alembic 迁移文件
alembic revision -m "add_organization_and_authorization_tables"
```

### 步骤 2: 修改现有表

```sql
-- 为 platform_connections 添加 owner_id
ALTER TABLE platform_connections 
ADD COLUMN owner_id VARCHAR(36);

-- 将现有数据的 owner_id 设置为 user_id
UPDATE platform_connections 
SET owner_id = user_id 
WHERE owner_id IS NULL;

-- 设置 NOT NULL 约束
ALTER TABLE platform_connections 
MODIFY COLUMN owner_id VARCHAR(36) NOT NULL;

-- 添加外键约束
ALTER TABLE platform_connections
ADD CONSTRAINT fk_platform_connections_owner 
FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE;

-- 添加索引
CREATE INDEX idx_platform_connections_owner_id ON platform_connections(owner_id);
```

### 步骤 3: 更新模型关系

在 `User` 模型中添加新的关系：

```python
# 在 User 模型中添加
owned_organizations: Mapped[list["Organization"]] = relationship(
    back_populates="owner",
    cascade="all, delete-orphan"
)
organization_memberships: Mapped[list["OrganizationMember"]] = relationship(
    foreign_keys="OrganizationMember.user_id",
    back_populates="user"
)
```

在 `PlatformConnection` 模型中添加：

```python
# 在 PlatformConnection 模型中添加
owner_id: Mapped[str] = mapped_column(
    String(36), 
    ForeignKey("users.id", ondelete="CASCADE"), 
    nullable=False, 
    index=True
)
owner: Mapped["User"] = relationship(foreign_keys=[owner_id])
authorizations: Mapped[list["PlatformConnectionAuthorization"]] = relationship(
    back_populates="connection",
    cascade="all, delete-orphan"
)
```

---

## 🎯 API 设计建议

### 组织管理 API

```python
# 创建组织
POST /api/v1/organizations
{
    "name": "ACME Corp",
    "description": "广告营销团队"
}

# 获取组织列表
GET /api/v1/organizations

# 获取组织详情
GET /api/v1/organizations/{organization_id}

# 更新组织信息（仅管理员）
PUT /api/v1/organizations/{organization_id}

# 删除组织（仅拥有者）
DELETE /api/v1/organizations/{organization_id}

# 邀请成员（管理员）
POST /api/v1/organizations/{organization_id}/members
{
    "user_email": "user@example.com",
    "role": "member"
}

# 获取成员列表
GET /api/v1/organizations/{organization_id}/members

# 更新成员角色（管理员）
PUT /api/v1/organizations/{organization_id}/members/{member_id}
{
    "role": "admin"
}

# 移除成员（管理员）
DELETE /api/v1/organizations/{organization_id}/members/{member_id}
```

### 账号授权 API

#### 母账号授权

```python
# 授权整个母账号给用户（包含所有子账号）
POST /api/v1/platform-connections/{connection_id}/authorizations
{
    "authorized_user_id": "user_123",
    "permission_level": "read_execute",
    "expires_at": "2026-12-31T23:59:59Z"  # 可选
}

# 获取母账号的授权列表
GET /api/v1/platform-connections/{connection_id}/authorizations
```

#### 子账号授权

```python
# 授权特定子账号给用户
POST /api/v1/sub-accounts/{sub_account_id}/authorizations
{
    "authorized_user_id": "user_123",
    "permission_level": "read_execute",
    "expires_at": "2026-12-31T23:59:59Z"  # 可选
}

# 获取子账号的授权列表
GET /api/v1/sub-accounts/{sub_account_id}/authorizations
```

#### 批量授权

```python
# 批量授权多个子账号给用户
POST /api/v1/authorizations/batch
{
    "authorizations": [
        {
            "resource_type": "sub_account",
            "resource_id": "sub_1",
            "authorized_user_id": "user_123",
            "permission_level": "read_execute"
        },
        {
            "resource_type": "sub_account",
            "resource_id": "sub_2",
            "authorized_user_id": "user_123",
            "permission_level": "read_execute"
        }
    ]
}
```

#### 查询授权

```python
# 获取我被授权的所有资源（母账号 + 子账号）
GET /api/v1/authorizations/authorized-to-me

# 获取我可访问的所有子账号
GET /api/v1/sub-accounts/accessible

# 检查用户对特定子账号的访问权限
GET /api/v1/sub-accounts/{sub_account_id}/check-access
```

#### 管理授权

```python
# 撤销授权
DELETE /api/v1/authorizations/{authorization_id}

# 更新授权
PUT /api/v1/authorizations/{authorization_id}
{
    "permission_level": "read",
    "expires_at": "2027-01-31T23:59:59Z"
}
```

---

## 🔐 权限检查逻辑示例

### 检查用户是否有权访问子账号

```python
async def check_sub_account_access(
    user_id: str, 
    sub_account_id: str,
    db: AsyncSession
) -> bool:
    """
    检查用户是否有权访问子账号
    支持多层级授权检查：拥有者 > 子账号授权 > 母账号授权
    """
    from sqlalchemy import select, and_
    from datetime import datetime
    
    # 1. 获取子账号信息
    sub_account = await db.get(SubAccountBinding, sub_account_id)
    if not sub_account:
        return False
    
    # 2. 检查是否是拥有者
    connection = await db.get(PlatformConnection, sub_account.parent_connection_id)
    if connection.owner_id == user_id:
        return True  # 拥有者有完全访问权限
    
    # 3. 检查是否有子账号级别的授权
    stmt = select(PlatformConnectionAuthorization).where(
        PlatformConnectionAuthorization.resource_type == "sub_account",
        PlatformConnectionAuthorization.resource_id == sub_account_id,
        PlatformConnectionAuthorization.authorized_user_id == user_id,
        PlatformConnectionAuthorization.status == "active"
    )
    result = await db.execute(stmt)
    sub_auth = result.scalar_one_or_none()
    if sub_auth:
        # 检查是否过期
        if not sub_auth.expires_at or sub_auth.expires_at > datetime.utcnow():
            return True
    
    # 4. 检查是否有母账号级别的授权
    stmt = select(PlatformConnectionAuthorization).where(
        PlatformConnectionAuthorization.resource_type == "platform_connection",
        PlatformConnectionAuthorization.resource_id == sub_account.parent_connection_id,
        PlatformConnectionAuthorization.authorized_user_id == user_id,
        PlatformConnectionAuthorization.status == "active"
    )
    result = await db.execute(stmt)
    conn_auth = result.scalar_one_or_none()
    if conn_auth:
        if not conn_auth.expires_at or conn_auth.expires_at > datetime.utcnow():
            return True
    
    return False
```

### 获取用户可访问的所有子账号

```python
async def get_accessible_sub_accounts(
    user_id: str,
    db: AsyncSession
) -> List[SubAccountBinding]:
    """
    获取用户可访问的所有子账号
    包括：拥有的子账号 + 通过母账号授权的子账号 + 直接授权的子账号
    """
    from sqlalchemy import select, and_, or_
    
    # 1. 获取用户拥有的所有母账号的子账号
    stmt = select(SubAccountBinding).join(
        PlatformConnection,
        SubAccountBinding.parent_connection_id == PlatformConnection.id
    ).where(
        PlatformConnection.owner_id == user_id
    )
    result = await db.execute(stmt)
    owned_sub_accounts = result.scalars().all()
    
    # 2. 获取通过母账号授权的子账号
    stmt = select(SubAccountBinding).join(
        PlatformConnectionAuthorization,
        and_(
            PlatformConnectionAuthorization.resource_type == "platform_connection",
            PlatformConnectionAuthorization.resource_id == SubAccountBinding.parent_connection_id
        )
    ).where(
        PlatformConnectionAuthorization.authorized_user_id == user_id,
        PlatformConnectionAuthorization.status == "active",
        or_(
            PlatformConnectionAuthorization.expires_at.is_(None),
            PlatformConnectionAuthorization.expires_at > datetime.utcnow()
        )
    )
    result = await db.execute(stmt)
    connection_authorized_sub_accounts = result.scalars().all()
    
    # 3. 获取直接授权的子账号
    stmt = select(SubAccountBinding).join(
        PlatformConnectionAuthorization,
        and_(
            PlatformConnectionAuthorization.resource_type == "sub_account",
            PlatformConnectionAuthorization.resource_id == SubAccountBinding.id
        )
    ).where(
        PlatformConnectionAuthorization.authorized_user_id == user_id,
        PlatformConnectionAuthorization.status == "active",
        or_(
            PlatformConnectionAuthorization.expires_at.is_(None),
            PlatformConnectionAuthorization.expires_at > datetime.utcnow()
        )
    )
    result = await db.execute(stmt)
    directly_authorized_sub_accounts = result.scalars().all()
    
    # 4. 合并去重
    all_sub_accounts = list(set(
        owned_sub_accounts + 
        connection_authorized_sub_accounts + 
        directly_authorized_sub_accounts
    ))
    
    return all_sub_accounts
```

### 获取用户对资源的权限级别

```python
async def get_user_permission_level(
    user_id: str,
    resource_type: str,
    resource_id: str,
    db: AsyncSession
) -> Optional[str]:
    """
    获取用户对资源的权限级别
    返回：'owner', 'read_execute', 'execute', 'read', None
    """
    from sqlalchemy import select
    
    # 1. 检查是否是拥有者
    if resource_type == "platform_connection":
        connection = await db.get(PlatformConnection, resource_id)
        if connection and connection.owner_id == user_id:
            return "owner"
    elif resource_type == "sub_account":
        sub_account = await db.get(SubAccountBinding, resource_id)
        if sub_account:
            connection = await db.get(PlatformConnection, sub_account.parent_connection_id)
            if connection and connection.owner_id == user_id:
                return "owner"
    
    # 2. 检查授权
    stmt = select(PlatformConnectionAuthorization).where(
        PlatformConnectionAuthorization.resource_type == resource_type,
        PlatformConnectionAuthorization.resource_id == resource_id,
        PlatformConnectionAuthorization.authorized_user_id == user_id,
        PlatformConnectionAuthorization.status == "active"
    )
    result = await db.execute(stmt)
    auth = result.scalar_one_or_none()
    
    if auth:
        # 检查是否过期
        if not auth.expires_at or auth.expires_at > datetime.utcnow():
            return auth.permission_level
    
    # 3. 如果是子账号，检查母账号授权
    if resource_type == "sub_account":
        sub_account = await db.get(SubAccountBinding, resource_id)
        if sub_account:
            stmt = select(PlatformConnectionAuthorization).where(
                PlatformConnectionAuthorization.resource_type == "platform_connection",
                PlatformConnectionAuthorization.resource_id == sub_account.parent_connection_id,
                PlatformConnectionAuthorization.authorized_user_id == user_id,
                PlatformConnectionAuthorization.status == "active"
            )
            result = await db.execute(stmt)
            parent_auth = result.scalar_one_or_none()
            if parent_auth:
                if not parent_auth.expires_at or parent_auth.expires_at > datetime.utcnow():
                    return parent_auth.permission_level
    
    return None
```

---

## ✅ 实施检查清单

- [ ] 创建 `organizations` 表
- [ ] 创建 `organization_members` 表
- [ ] 创建 `platform_connection_authorizations` 表
- [ ] 修改 `platform_connections` 表，添加 `owner_id`
- [ ] 创建 SQLAlchemy 模型
- [ ] 更新现有模型的关系
- [ ] 编写数据迁移脚本
- [ ] 实现组织管理 API
- [ ] 实现账号授权 API
- [ ] 实现权限控制中间件
- [ ] 编写单元测试
- [ ] 编写集成测试
- [ ] 更新 API 文档
- [ ] 前端 UI 适配

---

## 🚀 后续优化建议

1. **审计日志**
   - 记录组织和授权的所有操作
   - 便于追踪和审计

2. **权限模板**
   - 预定义常用的权限组合
   - 简化授权流程

3. **批量授权**
   - 支持一次性授权多个账号给多个用户
   - 提高效率

4. **授权通知**
   - 被授权时发送通知
   - 授权即将过期时提醒

5. **组织层级连接**
   - 支持组织级别的平台连接
   - 组织内成员共享连接

---

## 📚 参考资料

- [SQLAlchemy Relationships](https://docs.sqlalchemy.org/en/20/orm/relationships.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [RBAC (Role-Based Access Control)](https://en.wikipedia.org/wiki/Role-based_access_control)
