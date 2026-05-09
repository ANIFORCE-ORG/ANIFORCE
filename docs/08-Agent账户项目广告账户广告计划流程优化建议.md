# Agent 账户 / 项目 / 广告账户 / 广告计划流程优化建议

## 1. 参考文档结论

本次对照了以下规划和现有实现：

- `agent-ads-os/docs/agent-driven-media-buying-os-plan.md`
- `agent-ads-os/docs/platform-account-and-real-campaign-development-plan.md`
- `agent-ads-os/docs/bluewhale-feature-migration-phase1-design.md`
- `docs/07-信优媒介运营系统接入规划.md`

这些文档的共同方向是：不要把系统做成重组织管理系统，而是做成投放团队的 Agent 决策和执行系统。

目标业务链路应是：

```text
平台账户连接 / 账户资源运营
-> 项目聚合预算、目标、限制和历史
-> 广告账户承载真实平台资产和资金状态
-> 广告计划绑定真实平台账户并产生外部 ID
-> 指标同步和归一化
-> Agent 诊断
-> Action Queue
-> 人确认或规则自动执行
-> 执行结果和项目记忆沉淀
```

核心对象关系建议保持简洁：

```text
Workspace
  User
  Project
    PlatformAccount
      Campaign
        AdSet / AdGroup
          Ad / Creative
    MetricSnapshot
    AgentAction
    ProjectMemory
    Playbook
```

早期不建议做复杂组织层级和完整 RBAC。真正需要控制的是：

- 用户能操作哪些项目
- 用户能操作哪些广告账户
- 单次预算调整上限
- 每日预算操作上限
- Agent 能否自动暂停
- Agent 能否自动加预算
- Agent 能否自动发布新 Campaign
- 哪些动作必须人工确认

## 2. 当前系统现状

### 2.1 已经具备的基础

当前主系统已经具备：

- `User -> Project -> Campaign -> Material` 主链路
- `PlatformAccount` / `PlatformConnection` / `PlatformAccountOperation`
- Meta OAuth / Token 导入 / Meta Sandbox Campaign 创建
- `/platform-accounts` 广告账户首页
- `/platform-accounts/manage` 账户操作页
- `/platform-connections` 设置内的平台连接页
- `/campaigns/create` 广告计划创建流程
- Campaign 可以通过 `config` 存储：
  - `platform_account_id`
  - `remote_campaign_id`
  - `remote_platform`
  - `objective`
  - `budget_type`
- 广告账户操作支持：
  - 开户
  - 充值
  - 清零
  - 绑定
  - 回收

### 2.2 当前主要问题

#### 问题 1：Project 和 PlatformAccount 没有正式关系

当前：

```text
Project.user_id -> User
PlatformAccount.user_id -> User
Campaign.project_id -> Project
```

但缺少：

```text
Project <-> PlatformAccount
Campaign.platform_account_id
```

影响：

- 创建广告计划时能选择广告账户，但选择结果只进入 Campaign `config`
- 项目详情无法天然知道“这个项目有哪些可用广告账户”
- Agent 无法准确判断项目预算和账户余额、账户状态之间的关系
- 多项目共用同一个广告账户时，没有明确分配或可用边界

#### 问题 2：Campaign 的远端平台字段还不是一等字段

当前远端信息放在 `campaign.config`：

```json
{
  "platform_account_id": "...",
  "remote_campaign_id": "...",
  "remote_platform": "meta",
  "objective": "OUTCOME_TRAFFIC",
  "budget_type": "daily"
}
```

短期可用，但长期不利于：

- 列表筛选
- 同步平台状态
- 查询远端 Campaign
- 统计真实平台创建成功率
- Agent 执行动作时快速定位平台对象

#### 问题 3：广告账户首页和账户操作仍是两套数据语义

当前广告账户首页来自 `media_ops` 内存数据：

- 下户订单
- 水单
- 账号交付
- 售后工单
- 知识库

账户操作页来自 `platform_accounts` 数据库：

- 授权广告账户
- 充值
- 清零
- 绑定
- 回收

虽然页面已合并到一个栏目，但数据尚未真正合并。

影响：

- 首页看到的“账号交付”和操作页里的真实广告账户不能互相跳转
- 下户订单完成后不能自动生成或关联 `PlatformAccount`
- Agent 很难跨订单、账户、计划做诊断

#### 问题 4：缺少 MetricSnapshot 和平台同步层

当前 Campaign 有模拟或本地指标字段，Meta 也能创建 Campaign，但还没有稳定的：

- 从 Meta / Google / TikTok 拉取 Campaign 指标
- 把不同平台指标归一化
- 保存多窗口快照，例如 1d / 3d / 7d

影响：

- Agent 无法基于真实数据做诊断
- Today View 和 Action Queue 只能停留在静态页面或本地模拟

#### 问题 5：缺少 AgentAction / Action Queue

文档中明确指出 Action Queue 是产品核心表面，但当前系统还没有：

- AgentAction 模型
- 风险等级 L0-L4
- 建议、确认、拒绝、执行、失败、过期状态
- 行动证据
- 执行结果
- 结果复盘

影响：

- Agent 只能聊天或展示建议，不能沉淀为可追踪的业务动作
- 投手无法从“每天检查后台”切换到“处理行动队列”

#### 问题 6：缺少项目记忆和自动化边界

当前 Project 有预算、目标市场、标签，但没有：

- 项目禁用动作
- 项目预算调整上限
- 目标 CPI / CPA / ROAS 规则
- 学习期保护
- 冷却时间
- 历史有效策略
- 历史失败策略

影响：

- Agent 每次诊断缺少项目上下文
- 难以形成长期壁垒

## 3. 推荐调整后的产品流程

### 3.1 系统设置 / 平台连接

入口：

```text
设置 -> 平台连接
```

职责：

- 配置 Meta / Google / TikTok App 凭证
- OAuth 授权
- 同步广告账户
- 管理平台级连接状态

不建议放在一级业务导航。

### 3.2 广告账户

入口：

```text
广告账户
```

建议拆成同一栏目下的三个层级：

```text
广告账户首页
  今日待办 / 账户健康 / 交付异常 / 充值异常 / 封禁冻结 / 同步异常

账户列表
  真实 PlatformAccount 列表
  支持来源、平台、状态、余额、消耗、BMID、项目绑定筛选

账户操作
  开户 / 充值 / 清零 / 绑定 / 回收 / 操作历史
```

关键调整：

- 把 `media_ops.accounts` 的“交付账号”正式转成或关联 `PlatformAccount`
- `PlatformAccount.source_type` 标识：
  - `oauth`
  - `client-owned`
  - `agency-provided`
  - `rented`
  - `internal-supply`
  - `sandbox-token-import`
- 增加 `project_id` 或关联表，将广告账户分配到项目

推荐使用关联表，支持一个账户跨项目或一个项目多账户：

```text
project_platform_accounts
  id
  project_id
  platform_account_id
  role: primary | backup | testing | historical
  spend_cap
  daily_cap
  status
  created_at
```

### 3.3 项目

Project 应成为投放 Agent 的业务上下文中心。

建议 Project 增加或关联：

- KPI 目标：
  - target_cpi
  - target_cpa
  - target_roas
- 预算边界：
  - total_budget
  - daily_budget_cap
  - single_action_budget_change_limit
- 自动化边界：
  - auto_pause_enabled
  - auto_scale_enabled
  - auto_create_draft_enabled
  - require_owner_confirm_for_publish
- 关联广告账户
- 项目记忆
- 项目规则 / Playbook

项目详情页应从“信息展示页”升级为：

```text
项目总览
预算与消耗
关联广告账户
广告计划
Agent 行动队列
项目记忆
自动化规则
```

### 3.4 广告计划创建

当前流程：

```text
选择项目 -> 选择平台 -> 选择 Meta 广告账户 -> 填预算和素材 -> 创建
```

建议调整为：

```text
选择项目
-> 系统自动加载该项目已绑定广告账户
-> 选择平台账户
-> 选择创建方式：本地草稿 / 平台草稿 / 平台暂停 Campaign
-> 设置目标、预算、素材、定向
-> 风险确认
-> 创建
```

关键规则：

- 如果项目没有绑定任何广告账户，提示去“广告账户 -> 账户列表”分配账户
- 不能从全量用户账户里直接选，默认只显示项目绑定账户
- 创建真实平台 Campaign 时必须写入一等字段：
  - `platform_account_id`
  - `external_campaign_id`
  - `external_status`
  - `objective`
  - `budget_type`
  - `daily_budget`
  - `lifetime_budget`
  - `last_synced_at`

短期可以继续兼容 `config`，但新字段必须补齐。

### 3.5 广告计划列表

广告计划列表应不仅展示本地 Campaign，还要展示远端同步状态：

- 本地状态
- 平台状态
- 平台账户
- 外部 Campaign ID
- 最近同步时间
- 同步错误
- 素材数
- 预算进度
- Agent 建议

推荐增加筛选：

- 项目
- 平台
- 广告账户
- 本地状态
- 平台状态
- 是否有 Agent 待处理动作
- 是否同步异常

### 3.6 Agent Action Queue

建议新增一级工作流，但可以先放在 Dashboard 或项目详情里。

Action Queue 的每条动作必须包含：

- 动作类型
- 资源对象：项目 / 广告账户 / Campaign / 素材
- 风险等级：L0-L4
- 证据
- 预期影响
- 当前状态
- 操作按钮：确认 / 拒绝 / 执行 / 查看详情

风险等级默认：

```text
L0 只读分析：自动
L1 草稿建议：自动
L2 低风险执行：项目开启自动化后自动
L3 中风险执行：投手确认
L4 高风险执行：负责人确认
```

## 4. 推荐数据模型调整

### 4.1 Workspace

短期可以不做复杂组织，但建议加轻量 Workspace：

```text
workspaces
  id
  name
  owner_user_id
  settings_json
  created_at
  updated_at
```

后续 User / Project / PlatformAccount 都归属 Workspace。

### 4.2 PlatformAccount 补强

当前已有表，建议新增：

```text
workspace_id
project_id nullable 或使用关联表
external_account_id 统一替代 / 映射 account_id
token_encrypted
refresh_token_encrypted
scopes_json
sync_status
last_sync_error
credit_limit
daily_spend_cap
single_action_cap
```

### 4.3 Campaign 补强

建议新增一等字段：

```text
platform_account_id
external_campaign_id
external_status
objective
budget_type
daily_budget
lifetime_budget
bid_strategy
last_synced_at
last_sync_error
```

### 4.4 MetricSnapshot

新增：

```text
metric_snapshots
  id
  workspace_id
  project_id
  platform_account_id
  campaign_id nullable
  external_resource_type
  external_resource_id
  date
  window
  impressions
  clicks
  spend
  conversions
  revenue
  ctr
  cvr
  cpa
  roas
  cpi
  raw_json
  created_at
```

### 4.5 AgentAction

新增：

```text
agent_actions
  id
  workspace_id
  project_id
  platform_account_id nullable
  campaign_id nullable
  action_type
  risk_level
  status
  title
  summary
  evidence_json
  payload_json
  expected_impact_json
  created_by
  confirmed_by nullable
  executed_by nullable
  execution_result_json
  outcome_json
  created_at
  confirmed_at
  executed_at
  evaluated_at
```

### 4.6 ProjectMemory

新增：

```text
project_memories
  id
  project_id
  memory_type
  content
  source_type
  confidence
  created_at
  updated_at
```

## 5. 推荐前端信息架构

当前导航建议保持：

```text
数据概览
项目管理
广告投放
广告账户
创意素材
数据报表

底部：
设置
```

设置内：

```text
Agent 系统账号
系统设置
平台连接
```

广告账户栏目：

```text
/platform-accounts
  广告账户首页：账户健康、待办、订单/交付/售后摘要

/platform-accounts/manage
  账户列表和账户操作

/platform-accounts/:id
  账户详情：消耗、余额、绑定项目、关联 Campaign、操作历史、同步日志
```

项目栏目：

```text
/projects
  项目列表

/projects/:id
  项目总览
  预算 / 账户 / Campaign / Action Queue / Project Memory / Rules
```

广告投放栏目：

```text
/campaign
  跨项目广告计划列表

/campaigns/create
  创建本地或真实平台 Campaign

/campaigns/:id
  Campaign 详情、素材、远端状态、Agent 建议、执行历史
```

## 6. 分阶段开发节奏

### Phase 0：整理当前信息架构

目标：让现有系统逻辑一致。

任务：

1. 保持平台连接只在设置内出现。
2. 广告账户首页使用统一文案和统一入口。
3. 账户操作页补操作历史抽屉。
4. 广告计划创建页显示远端 Campaign ID 创建结果。
5. Campaign 详情页展示 `config.remote_campaign_id` 和 `config.platform_account_id`。

验收：

- 用户能从设置连接平台。
- 用户能在广告账户看到账户。
- 用户能创建 Meta Campaign。
- 用户能在 Campaign 详情看到 Meta Campaign ID。

### Phase 1：打通 Project 和 PlatformAccount

目标：项目有明确可用广告账户。

任务：

1. 新增 `project_platform_accounts` 关联表。
2. 在项目详情页增加“关联广告账户”模块。
3. 在账户操作页增加“分配到项目”。
4. 广告计划创建时默认只显示项目绑定账户。
5. 新建 Campaign 时写入 `platform_account_id` 一等字段。

验收：

- 一个项目可以绑定多个广告账户。
- 创建广告计划不能误选无关账户。
- 广告账户详情可以反查关联项目和 Campaign。

### Phase 2：Campaign 远端字段一等化

目标：真实平台对象可查询、可同步、可诊断。

任务：

1. Campaign 增加远端字段 migration。
2. 历史 `config.remote_campaign_id` 回填到新字段。
3. Campaign 列表展示外部 Campaign ID、平台状态、最近同步时间。
4. Meta 创建接口直接写新字段。
5. 保留 `config` 仅存非结构化配置。

验收：

- 所有真实创建的 Meta Campaign 都有外部 ID。
- 列表和详情均可复制 / 查看外部 ID。
- 后续平台同步无需解析 `config`。

### Phase 3：MetricSnapshot 和平台同步

目标：Agent 诊断基于真实指标。

任务：

1. 新增 `metric_snapshots`。
2. 增加 Meta Campaign 指标同步。
3. 增加手动同步按钮。
4. 增加 1d / 3d / 7d 聚合。
5. 数据报表切换为读取归一化指标。

验收：

- 用户可手动同步 Meta 指标。
- Campaign 列表数据来自最新快照。
- 项目页能展示项目级真实消耗和效果。

### Phase 4：AgentAction 和行动队列

目标：从“看报表”转向“处理 Agent 行动”。

任务：

1. 新增 `agent_actions`。
2. 增加规则诊断：
   - CPA 超目标
   - 花费无转化
   - 创意疲劳
   - 预算接近耗尽
   - 学习期卡住
   - 平台账户同步异常
3. 在 Dashboard / 项目详情增加 Action Queue。
4. 支持确认 / 拒绝。
5. 暂不自动执行平台写操作。

验收：

- 系统每天能生成可解释行动建议。
- 投手可以确认或拒绝。
- 每条行动有证据和风险等级。

### Phase 5：低风险执行和项目记忆

目标：形成 Agent 产品壁垒。

任务：

1. 新增执行服务。
2. 支持 L2 自动执行。
3. L3/L4 需要确认。
4. 新增 `project_memories`。
5. 行动结果 1/3/7 天后自动复盘。
6. 成功和失败经验进入项目记忆。

验收：

- Agent 不只是建议，还能在边界内执行。
- 每次执行有结果追踪。
- 项目越用越懂业务。

## 7. 当前最应该优先做的 6 个改动

按投入产出排序：

1. Campaign 详情展示 Meta Campaign ID 和平台账户。
2. Campaign 表新增 `platform_account_id` / `external_campaign_id` / `external_status`。
3. 项目绑定广告账户。
4. 创建广告计划时只展示项目绑定账户。
5. 账户操作页增加操作历史和同步状态。
6. 增加最小版 AgentAction 表和项目 Action Queue。

这 6 项完成后，系统会从“能创建真实 Campaign 的工具”进入“围绕项目和账户做 Agent 投放管理”的阶段。
