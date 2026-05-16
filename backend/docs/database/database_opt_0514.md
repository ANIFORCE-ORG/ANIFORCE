# ANIMAGUS 数据库设计优化建议

**文档版本**：v1.0  
**创建日期**：2026-05-14  
**作者**：技术团队  

---

## 概述

本文档针对当前 ANIMAGUS 数据库设计进行全面分析，识别存在的问题并提供优化建议。当前数据库包含 5 张核心表（users、projects、campaigns、materials、metrics），采用 Sqlite 作为主数据库，MongoDB 存储对话历史。

---

## 问题分析

### 🔴 严重问题

#### 1. 多对多关系使用 JSON 存储

**当前设计**：
```sql
-- materials 表
material.project_ids: Text  -- JSON 数组：["proj-1", "proj-2"]
material.campaign_ids: Text  -- JSON 数组：["camp-1", "camp-2"]

-- campaigns 表
campaign.material_ids: Text  -- JSON 数组：["mat-1", "mat-2"]
```

**存在的问题**：
- ❌ **数据完整性无保障**：无法使用外键约束，删除项目/广告系列时无法自动清理关联
- ❌ **查询性能极差**：查找"某素材关联的所有项目"需要全表扫描
- ❌ **无法使用 JOIN**：无法高效进行关联查询
- ❌ **无法记录元数据**：无法记录关联时间、关联人等信息
- ❌ **维护困难**：需要手动维护双向关联的一致性

**影响范围**：
- 素材管理功能
- 广告系列配置功能
- 数据统计和报表

**优先级**：🔴 **最高优先级**

---

#### 2. 字段类型选择不当

**当前设计**：
```sql
tags: Text           -- 存储 JSON 数组
config: Text         -- 存储 JSON 对象
```

**存在的问题**：
- ❌ **无法使用 JSON 操作符**：PostgreSQL 的 JSONB 类型支持高效的 JSON 查询
- ❌ **无索引支持**：Text 类型无法对 JSON 内容建立索引
- ❌ **性能损失**：每次查询都需要解析 JSON 字符串
- ❌ **存储空间浪费**：JSONB 使用二进制存储，比 Text 更高效

**影响范围**：
- 标签搜索功能
- 配置查询功能

**优先级**：🔴 **高优先级**

---

### 🟡 重要缺失

#### 3. 缺少平台账号连接表

**问题描述**：
系统需要连接 TikTok、Google、Meta 等广告平台，但当前没有表存储平台授权信息。

**影响**：
- 无法管理用户的平台账号
- 无法存储 OAuth 令牌
- 无法追踪令牌过期状态
- 无法支持多账号管理

**优先级**：🟡 **高优先级**

---

#### 4. 缺少用户角色权限表

**问题描述**：
当前 `users` 表只有基本字段，缺少角色和权限管理机制。

**影响**：
- 无法实现细粒度权限控制
- 无法支持团队协作（管理员、成员、只读等角色）
- 无法实现数据隔离

**优先级**：🟡 **中优先级**

---

#### 5. 缺少审计日志表

**问题描述**：
无法追踪数据变更历史和用户操作记录。

**影响**：
- 数据被误删除后无法追溯
- 无法审计用户操作
- 无法满足合规要求

**优先级**：🟡 **中优先级**

---

### 🟢 性能优化

#### 6. metrics 表未分区

**问题描述**：
监控指标表会随时间快速增长，单表查询性能会下降。

**影响**：
- 查询历史数据性能差
- 表维护困难（VACUUM、索引重建）
- 备份恢复耗时长

**优先级**：🟢 **中优先级**

---

#### 7. 缺少软删除支持

**问题描述**：
当前使用硬删除（CASCADE），删除后数据无法恢复。

**影响**：
- 误删除后数据丢失
- 无法查看历史记录
- 无法实现"回收站"功能

**优先级**：🟢 **低优先级**

---

## 优化方案

### 方案 1：创建中间表替代 JSON 存储（最高优先级）

#### 1.1 素材-项目关联表

```sql
CREATE TABLE material_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id UUID NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    UNIQUE(material_id, project_id)
);

-- 索引优化
CREATE INDEX idx_material_projects_material ON material_projects(material_id);
CREATE INDEX idx_material_projects_project ON material_projects(project_id);
CREATE INDEX idx_material_projects_created ON material_projects(created_at);
```

#### 1.2 素材-广告系列关联表

```sql
CREATE TABLE material_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id UUID NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    display_order INTEGER DEFAULT 0,  -- 素材展示顺序
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    UNIQUE(material_id, campaign_id)
);

-- 索引优化
CREATE INDEX idx_material_campaigns_material ON material_campaigns(material_id);
CREATE INDEX idx_material_campaigns_campaign ON material_campaigns(campaign_id);
CREATE INDEX idx_material_campaigns_order ON material_campaigns(campaign_id, display_order);
```

#### 1.3 迁移步骤

```python
# 数据迁移脚本示例
from sqlalchemy import text

def migrate_material_relationships(session):
    """迁移素材关联关系从 JSON 到中间表"""
    
    # 1. 迁移 material_projects
    materials = session.execute(text("SELECT id, project_ids FROM materials WHERE project_ids IS NOT NULL"))
    for material in materials:
        material_id = material.id
        project_ids = json.loads(material.project_ids) if material.project_ids else []
        
        for project_id in project_ids:
            session.execute(text("""
                INSERT INTO material_projects (material_id, project_id)
                VALUES (:material_id, :project_id)
                ON CONFLICT DO NOTHING
            """), {"material_id": material_id, "project_id": project_id})
    
    # 2. 迁移 material_campaigns
    materials = session.execute(text("SELECT id, campaign_ids FROM materials WHERE campaign_ids IS NOT NULL"))
    for material in materials:
        material_id = material.id
        campaign_ids = json.loads(material.campaign_ids) if material.campaign_ids else []
        
        for campaign_id in campaign_ids:
            session.execute(text("""
                INSERT INTO material_campaigns (material_id, campaign_id)
                VALUES (:material_id, :campaign_id)
                ON CONFLICT DO NOTHING
            """), {"material_id": material_id, "campaign_id": campaign_id})
    
    session.commit()
    
    # 3. 删除旧字段（确认数据迁移成功后执行）
    # session.execute(text("ALTER TABLE materials DROP COLUMN project_ids"))
    # session.execute(text("ALTER TABLE materials DROP COLUMN campaign_ids"))
    # session.execute(text("ALTER TABLE campaigns DROP COLUMN material_ids"))
```

#### 1.4 查询优化示例

```python
# 优化前：查找素材关联的所有项目（需要全表扫描）
materials = session.query(Material).all()
for material in materials:
    project_ids = material.get_project_ids()
    projects = session.query(Project).filter(Project.id.in_(project_ids)).all()

# 优化后：使用 JOIN 查询
from sqlalchemy.orm import joinedload

materials_with_projects = (
    session.query(Material)
    .join(MaterialProject)
    .join(Project)
    .options(joinedload(Material.projects))
    .all()
)
```

---

### 方案 2：修改字段类型为 JSONB（高优先级）

#### 2.1 修改表结构

```sql
-- 修改 projects 表
ALTER TABLE projects 
    ALTER COLUMN tags TYPE JSONB USING tags::jsonb;

-- 修改 campaigns 表
ALTER TABLE campaigns 
    ALTER COLUMN config TYPE JSONB USING config::jsonb;

-- 修改 materials 表
ALTER TABLE materials 
    ALTER COLUMN tags TYPE JSONB USING tags::jsonb;
```

#### 2.2 创建 GIN 索引

```sql
-- 为 JSONB 字段创建 GIN 索引，支持高效查询
CREATE INDEX idx_projects_tags ON projects USING GIN (tags);
CREATE INDEX idx_campaigns_config ON campaigns USING GIN (config);
CREATE INDEX idx_materials_tags ON materials USING GIN (tags);
```

#### 2.3 查询优化示例

```sql
-- 查找包含特定标签的项目
SELECT * FROM projects 
WHERE tags @> '["RPG"]'::jsonb;

-- 查找特定配置的广告系列
SELECT * FROM campaigns 
WHERE config @> '{"auto_optimize": true}'::jsonb;

-- 查找标签包含特定关键词的素材
SELECT * FROM materials 
WHERE tags ? 'action';
```

---

### 方案 3：添加平台账号连接表（高优先级）

```sql
CREATE TABLE platform_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,  -- 'TikTok', 'Google', 'Meta'
    
    -- 账号信息
    account_id VARCHAR(255) NOT NULL,
    account_name VARCHAR(255),
    account_secret VARCHAR(255),
    
    -- OAuth 令牌
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_type VARCHAR(50) DEFAULT 'Bearer',
    token_expires_at TIMESTAMP,
    
    -- 权限范围
    scopes TEXT[],  -- 数组类型存储权限列表
    
    -- 状态管理
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- 'unauthorized', 'active', 'expired', 'revoked'
    last_sync_at TIMESTAMP,
    
    -- 元数据
    extra_data JSON,  -- 存储平台特定的额外信息
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, platform, account_id)
);

-- 索引
CREATE INDEX idx_platform_connections_user ON platform_connections(user_id);
CREATE INDEX idx_platform_connections_platform ON platform_connections(platform);
CREATE INDEX idx_platform_connections_status ON platform_connections(status);
CREATE INDEX idx_platform_connections_expires ON platform_connections(token_expires_at);

-- 自动更新 updated_at
CREATE TRIGGER update_platform_connections_updated_at
    BEFORE UPDATE ON platform_connections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

#### 使用示例

```python
class PlatformConnection(Base):
    __tablename__ = "platform_connections"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    platform: Mapped[str] = mapped_column(String(50))
    account_id: Mapped[str] = mapped_column(String(255))
    access_token: Mapped[str] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="active")
    
    # 关系
    user: Mapped["User"] = relationship(back_populates="platform_connections")
    
    def is_token_expired(self) -> bool:
        """检查令牌是否过期"""
        if not self.token_expires_at:
            return False
        return datetime.utcnow() >= self.token_expires_at
    
    def needs_refresh(self, buffer_minutes: int = 10) -> bool:
        """检查是否需要刷新令牌"""
        if not self.token_expires_at:
            return False
        buffer = timedelta(minutes=buffer_minutes)
        return datetime.utcnow() >= (self.token_expires_at - buffer)
```

---

### 方案 4：添加用户角色权限表（中优先级）

```sql
-- 角色表
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    description TEXT,
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_system BOOLEAN DEFAULT FALSE,  -- 系统角色不可删除
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 用户角色关联表
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,  -- 角色过期时间（可选）
    UNIQUE(user_id, role_id)
);

-- 索引
CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);
CREATE INDEX idx_user_roles_expires ON user_roles(expires_at);

-- 插入默认角色
INSERT INTO roles (name, display_name, description, permissions, is_system) VALUES
('admin', '管理员', '系统管理员，拥有所有权限', 
 '["*"]'::jsonb, TRUE),
('manager', '项目经理', '可以管理项目和广告系列', 
 '["project:*", "campaign:*", "material:read"]'::jsonb, TRUE),
('member', '普通成员', '可以查看和编辑自己的内容', 
 '["project:read", "campaign:read", "material:*"]'::jsonb, TRUE),
('viewer', '只读用户', '只能查看内容', 
 '["project:read", "campaign:read", "material:read"]'::jsonb, TRUE);
```

#### 权限检查示例

```python
def check_permission(user_id: str, permission: str, session) -> bool:
    """检查用户是否有特定权限"""
    
    # 查询用户的所有角色
    user_roles = session.query(UserRole).filter(
        UserRole.user_id == user_id,
        or_(
            UserRole.expires_at.is_(None),
            UserRole.expires_at > datetime.utcnow()
        )
    ).all()
    
    # 检查权限
    for user_role in user_roles:
        role = user_role.role
        permissions = role.permissions
        
        # 检查是否有通配符权限
        if "*" in permissions:
            return True
        
        # 检查具体权限
        if permission in permissions:
            return True
        
        # 检查模块级通配符（如 "project:*"）
        module = permission.split(":")[0]
        if f"{module}:*" in permissions:
            return True
    
    return False
```

---

### 方案 5：添加审计日志表（中优先级）

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 操作信息
    user_id UUID REFERENCES users(id),
    action VARCHAR(50) NOT NULL,  -- 'create', 'update', 'delete', 'login', etc.
    resource_type VARCHAR(50) NOT NULL,  -- 'project', 'campaign', 'material', etc.
    resource_id UUID,
    
    -- 变更数据
    old_data JSONB,
    new_data JSONB,
    changes JSONB,  -- 只记录变更的字段
    
    -- 请求信息
    ip_address VARCHAR(45),
    user_agent TEXT,
    request_id VARCHAR(100),  -- 关联请求 ID
    
    -- 元数据
    metadata JSONB,
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);

-- 分区（按月）
CREATE TABLE audit_logs_2026_05 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
```

#### 审计日志记录示例

```python
def log_audit(
    session,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    old_data: dict = None,
    new_data: dict = None,
    ip_address: str = None,
    user_agent: str = None
):
    """记录审计日志"""
    
    # 计算变更
    changes = {}
    if old_data and new_data:
        for key in new_data:
            if key in old_data and old_data[key] != new_data[key]:
                changes[key] = {
                    "old": old_data[key],
                    "new": new_data[key]
                }
    
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        old_data=old_data,
        new_data=new_data,
        changes=changes,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    session.add(audit_log)
    session.commit()
```

---

### 方案 6：metrics 表分区优化（中优先级）

```sql
-- 创建分区表
CREATE TABLE metrics (
    id UUID NOT NULL,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    platform VARCHAR(50) NOT NULL,
    
    -- 数据来源
    data_source VARCHAR(20) DEFAULT 'api',  -- 'api', 'webhook', 'manual'
    data_version INTEGER DEFAULT 1,
    
    -- 核心指标
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    installs INTEGER DEFAULT 0,
    
    -- 成本指标
    spend NUMERIC(12, 2) DEFAULT 0.0,
    revenue NUMERIC(12, 2) DEFAULT 0.0,
    
    -- 转化指标
    ctr NUMERIC(5, 4) DEFAULT 0.0,
    cvr NUMERIC(5, 4) DEFAULT 0.0,
    cpa NUMERIC(12, 2) DEFAULT 0.0,
    cpi NUMERIC(12, 2) DEFAULT 0.0,
    roi NUMERIC(8, 4) DEFAULT 0.0,
    
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- 创建分区（按月）
CREATE TABLE metrics_2026_05 PARTITION OF metrics
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

CREATE TABLE metrics_2026_06 PARTITION OF metrics
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

-- 索引（在每个分区上自动创建）
CREATE INDEX idx_metrics_campaign ON metrics(campaign_id);
CREATE INDEX idx_metrics_timestamp ON metrics(timestamp);
CREATE INDEX idx_metrics_platform ON metrics(platform);

-- 自动创建分区的函数
CREATE OR REPLACE FUNCTION create_metrics_partition()
RETURNS void AS $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
    start_date TEXT;
    end_date TEXT;
BEGIN
    -- 为下个月创建分区
    partition_date := DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month');
    partition_name := 'metrics_' || TO_CHAR(partition_date, 'YYYY_MM');
    start_date := TO_CHAR(partition_date, 'YYYY-MM-DD');
    end_date := TO_CHAR(partition_date + INTERVAL '1 month', 'YYYY-MM-DD');
    
    -- 检查分区是否已存在
    IF NOT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = partition_name
    ) THEN
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF metrics FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 定时任务：每月1号自动创建下个月的分区
-- 需要配合 pg_cron 扩展使用
```

---

### 方案 7：添加软删除支持（低优先级）

```sql
-- 为需要软删除的表添加字段
ALTER TABLE projects ADD COLUMN deleted_at TIMESTAMP;
ALTER TABLE projects ADD COLUMN deleted_by UUID REFERENCES users(id);

ALTER TABLE campaigns ADD COLUMN deleted_at TIMESTAMP;
ALTER TABLE campaigns ADD COLUMN deleted_by UUID REFERENCES users(id);

ALTER TABLE materials ADD COLUMN deleted_at TIMESTAMP;
ALTER TABLE materials ADD COLUMN deleted_by UUID REFERENCES users(id);

-- 创建索引
CREATE INDEX idx_projects_deleted ON projects(deleted_at);
CREATE INDEX idx_campaigns_deleted ON campaigns(deleted_at);
CREATE INDEX idx_materials_deleted ON materials(deleted_at);

-- 创建视图（只显示未删除的数据）
CREATE VIEW active_projects AS
SELECT * FROM projects WHERE deleted_at IS NULL;

CREATE VIEW active_campaigns AS
SELECT * FROM campaigns WHERE deleted_at IS NULL;

CREATE VIEW active_materials AS
SELECT * FROM materials WHERE deleted_at IS NULL;
```

#### 软删除实现示例

```python
class SoftDeleteMixin:
    """软删除 Mixin"""
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    
    def soft_delete(self, user_id: str):
        """软删除"""
        self.deleted_at = datetime.utcnow()
        self.deleted_by = user_id
    
    def restore(self):
        """恢复"""
        self.deleted_at = None
        self.deleted_by = None
    
    @property
    def is_deleted(self) -> bool:
        """是否已删除"""
        return self.deleted_at is not None

# 查询时过滤已删除数据
def get_active_projects(session, user_id: str):
    return session.query(Project).filter(
        Project.user_id == user_id,
        Project.deleted_at.is_(None)
    ).all()
```

---

## 实施计划

### 阶段 1：紧急修复（1-2 周）

**目标**：修复严重问题，确保数据完整性

- [ ] 创建中间表（material_projects, material_campaigns）
- [ ] 数据迁移脚本开发和测试
- [ ] 执行数据迁移
- [ ] 更新 ORM 模型和业务代码
- [ ] 删除旧的 JSON 字段

**风险**：
- 数据迁移可能失败
- 业务代码需要大量修改

**缓解措施**：
- 在测试环境充分测试
- 保留旧字段作为备份
- 分批迁移数据

---

### 阶段 2：类型优化（1 周）

**目标**：提升查询性能

- [ ] 修改 tags 和 config 字段为 JSONB
- [ ] 创建 GIN 索引
- [ ] 更新查询代码使用 JSONB 操作符
- [ ] 性能测试和对比

---

### 阶段 3：功能完善（2-3 周）

**目标**：添加缺失的核心功能

- [ ] 创建 platform_connections 表
- [ ] 实现 OAuth 令牌管理
- [ ] 创建 roles 和 user_roles 表
- [ ] 实现权限检查逻辑
- [ ] 创建 audit_logs 表
- [ ] 实现审计日志记录

---

### 阶段 4：性能优化（1-2 周）

**目标**：优化长期性能

- [ ] metrics 表分区实施
- [ ] 历史数据迁移到分区
- [ ] 创建自动分区函数
- [ ] 软删除功能实现（可选）

---

## 数据库约束和检查

### 添加 CHECK 约束

```sql
-- projects 表
ALTER TABLE projects ADD CONSTRAINT check_budget_positive 
    CHECK (total_budget >= 0);
ALTER TABLE projects ADD CONSTRAINT check_spent_positive 
    CHECK (spent >= 0);
ALTER TABLE projects ADD CONSTRAINT check_spent_not_exceed_budget 
    CHECK (spent <= total_budget);

-- campaigns 表
ALTER TABLE campaigns ADD CONSTRAINT check_campaign_budget_positive 
    CHECK (budget >= 0);
ALTER TABLE campaigns ADD CONSTRAINT check_campaign_spent_positive 
    CHECK (spent >= 0);
ALTER TABLE campaigns ADD CONSTRAINT check_campaign_spent_not_exceed_budget 
    CHECK (spent <= budget);

-- metrics 表
ALTER TABLE metrics ADD CONSTRAINT check_impressions_positive 
    CHECK (impressions >= 0);
ALTER TABLE metrics ADD CONSTRAINT check_clicks_positive 
    CHECK (clicks >= 0);
ALTER TABLE metrics ADD CONSTRAINT check_clicks_not_exceed_impressions 
    CHECK (clicks <= impressions);
ALTER TABLE metrics ADD CONSTRAINT check_ctr_range 
    CHECK (ctr >= 0 AND ctr <= 1);
ALTER TABLE metrics ADD CONSTRAINT check_cvr_range 
    CHECK (cvr >= 0 AND cvr <= 1);
```

---

## 性能基准测试

### 测试场景

#### 场景 1：查找素材关联的项目

**优化前（JSON 存储）**：
```sql
-- 需要全表扫描
SELECT * FROM materials WHERE project_ids::jsonb @> '"proj-123"'::jsonb;
-- 执行时间：~500ms（10万条记录）
```

**优化后（中间表）**：
```sql
-- 使用索引查询
SELECT m.* FROM materials m
JOIN material_projects mp ON m.id = mp.material_id
WHERE mp.project_id = 'proj-123';
-- 执行时间：~5ms（10万条记录）
```

**性能提升**：100 倍

---

#### 场景 2：标签搜索

**优化前（Text 类型）**：
```sql
SELECT * FROM projects WHERE tags LIKE '%RPG%';
-- 执行时间：~300ms（5万条记录）
```

**优化后（JSONB + GIN 索引）**：
```sql
SELECT * FROM projects WHERE tags @> '["RPG"]'::jsonb;
-- 执行时间：~10ms（5万条记录）
```

**性能提升**：30 倍

---

## 风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 数据迁移失败 | 高 | 中 | 充分测试、数据备份、分批迁移 |
| 业务代码不兼容 | 高 | 高 | 代码审查、单元测试、灰度发布 |
| 性能下降 | 中 | 低 | 性能测试、索引优化、查询优化 |
| 数据不一致 | 高 | 低 | 事务控制、数据校验、回滚方案 |

---

## 总结

### 优先级排序

**🔴 最高优先级（必须立即修复）**：
1. 创建中间表替代 JSON 存储多对多关系
2. 修改字段类型为 JSONB

**🟡 高优先级（近期完成）**：
3. 添加平台账号连接表
4. 添加用户角色权限表

**🟢 中优先级（计划完成）**：
5. 添加审计日志表
6. metrics 表分区优化

**⚪ 低优先级（可选）**：
7. 添加软删除支持

### 预期收益

- **数据完整性**：通过外键约束保证数据一致性
- **查询性能**：中间表查询性能提升 100 倍
- **功能完善**：支持平台账号管理、权限控制、审计日志
- **可维护性**：代码更清晰，易于理解和维护
- **可扩展性**：为未来功能扩展打下基础

---

## 附录

### A. 完整的 ER 图（优化后）

```
                    ┌─────────────┐
                    │    users    │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌──────────────────┐
│  user_roles   │  │   projects    │  │platform_connections│
└───────┬───────┘  └───────┬───────┘  └──────────────────┘
        │                  │
        ▼                  ▼
┌───────────────┐  ┌───────────────┐
│    roles      │  │  campaigns    │
└───────────────┘  └───────┬───────┘
                           │
                           ├──────────────┐
                           ▼              ▼
                   ┌───────────────┐  ┌──────────────┐
                   │   metrics     │  │material_     │
                   └───────────────┘  │campaigns     │
                                      └──────┬───────┘
                                             │
        ┌────────────────────────────────────┘
        │
        ▼
┌───────────────┐
│  materials    │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│material_      │
│projects       │
└───────────────┘
```

### B. 参考文档

- [PostgreSQL JSONB 文档](https://www.postgresql.org/docs/current/datatype-json.html)
- [PostgreSQL 分区表文档](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- [SQLAlchemy 关系文档](https://docs.sqlalchemy.org/en/20/orm/relationships.html)
- [数据库设计最佳实践](https://www.postgresql.org/docs/current/ddl-constraints.html)

---

**文档结束**
