# 前端表单字段与后端数据库字段映射文档

## 概述

本文档描述了前端 `CreateProjectModal.vue` 表单字段与后端数据库 `Project` 和 `Campaign` 模型字段的映射关系。

## 数据架构说明

根据 Meta 广告架构，系统采用以下层级结构：
- **Project（项目）** - 对应 Meta Campaign 层级，包含多个 Campaign
- **Campaign（广告系列）** - 对应 Meta Ad Set 层级，包含多个 Ad
- **Ad（广告）** - 对应 Meta Ad 层级，包含具体的广告创意

前端表单在创建项目时，会同时创建一个 Project 和一个初始 Campaign。

## 字段映射表

### Project 模型字段

| 前端字段 | 前端字段名 | 后端字段 | 数据类型 | 说明 | 示例值 |
|---------|----------|---------|---------|------|--------|
| 项目名称 | name | name | String(255) | 项目名称 | "CB_US_Meta_AppPromotion" |
| 产品 | product | product | String(255) | 产品名称 | "休闲消除手游" |
| - | - | user_id | String(36) | 所属用户ID（自动填充） | "user_test_001" |
| - | - | description | Text | 项目描述（可选） | null |
| - | - | game_type | String(50) | 游戏类型（可选） | null |
| - | - | target_market | String(100) | 目标市场（可选） | null |
| - | - | tags | Text | 标签，JSON数组格式（可选） | null |
| - | - | total_budget | Float | 总预算金额（必填） | 10000.0 |
| - | - | spent | Float | 已花费金额（默认0） | 0.0 |
| - | - | status | Enum | 项目状态（默认active） | "active" |
| - | - | manager | String(100) | 项目负责人（可选） | null |
| 开始时间 | start | start_date | Date | 项目开始日期 | "2026-06-22" |
| 结束时间 | end | end_date | Date | 项目结束日期 | "2026-12-31" |

### Campaign 模型字段

| 前端字段 | 前端字段名 | 后端字段 | 数据类型 | 说明 | 示例值 |
|---------|----------|---------|---------|------|--------|
| Campaign 名称 | campaignName | name | String(255) | 广告系列名称 | "Meta Campaign Name" |
| 投放渠道 | channel | platform | Enum | 投放平台 | "Meta" |
| 广告账户 | account | account_id | String(100) | 广告账户ID，对应 sub_account_bindings.sub_account_id | "act_2194875301" |
| 投放国家 | countries | countries | String(500) | 投放国家，多个国家用逗号分隔 | "美国 / 加拿大" |
| - | - | platform_campaign_id | String(100) | 平台广告系列ID，用于与Meta/Google/TikTok平台创建的Campaign ID进行绑定同步 | "120210000000000000" |
| Objective | objective | objective | String(100) | 广告目标 | "App promotion" |
| Buying type | buyingType | buying_type | String(50) | 购买类型 | "Auction" |
| Special ad categories | specialAdCategories | special_ad_categories | String(100) | 特殊广告类别 | "None" |
| A/B test | abTest | ab_test | String(50) | A/B测试开关 | "关闭" |
| Campaign budget 开关 | campaignBudget | campaign_budget_optimization | String(50) | Campaign预算优化开关 | "开启" |
| Budget type | budgetType | budget_type | String(50) | 预算类型 | "Daily budget" |
| Budget | budget | budget | Float | 预算金额 | 1000.0 |
| Bid strategy | bidStrategy | bid_strategy | String(100) | 出价策略 | "Lowest cost" |
| Spend limit | spendLimit | spend_limit | Float | 花费限制金额 | null |
| 状态 | campaignStatus | status | Enum | 广告系列状态（默认Draft） | "draft" |
| 开始时间 | start | start_date | Date | 投放开始日期 | "2026-06-22" |
| 结束时间 | end | end_date | Date | 投放结束日期 | "2026-12-31" |
| - | - | project_id | String(36) | 所属项目ID（自动填充） | "project_uuid" |
| - | - | description | Text | 广告系列描述（可选） | null |
| - | - | spent | Float | 已花费金额（默认0） | 0.0 |
| - | - | material_ids | Text | 关联的素材ID列表，JSON数组（可选） | null |
| - | - | config | Text | 其他配置信息，JSON格式（可选） | null |

## 字段详细说明

### Project 字段

#### product（产品）
- **类型**: String(255)
- **示例**: "休闲消除手游", "策略战争手游"
- **必填**: 否
- **说明**: 推广的产品名称

### Campaign 字段

#### account_id（广告账户ID）
- **类型**: String(100)
- **示例**: "act_2194875301"
- **必填**: 是
- **说明**: 关联的广告账户ID，对应 sub_account_bindings 表中的 sub_account_id

#### countries（投放国家）
- **类型**: String(500)
- **示例**: "美国 / 加拿大", "美国", "全球"
- **必填**: 否
- **说明**: 目标投放国家或地区，多个国家用 " / " 分隔

#### platform_campaign_id（平台广告系列ID）
- **类型**: String(100)
- **示例**: "120210000000000000" (Meta Campaign ID)
- **必填**: 否
- **说明**: 用于与Meta/Google/TikTok平台创建的Campaign ID进行绑定同步。当通过API在平台上创建广告系列后，平台会返回一个唯一的Campaign ID，该ID存储在此字段中，用于后续的数据同步、状态更新等操作
- **使用场景**:
  - 创建广告系列后，存储平台返回的Campaign ID
  - 同步广告数据时，通过此ID查询平台的广告系列信息
  - 更新广告状态时，通过此ID定位平台上的广告系列

#### objective（广告目标）
- **类型**: String(100)
- **可选值**: "App promotion", "Conversions", "Traffic", "Brand awareness", "Reach", "Lead generation"
- **必填**: 是
- **说明**: Meta 广告的营销目标

#### buying_type（购买类型）
- **类型**: String(50)
- **可选值**: "Auction", "Reserved"
- **必填**: 是
- **说明**: 广告购买方式

#### special_ad_categories（特殊广告类别）
- **类型**: String(100)
- **可选值**: "None", "Credit", "Employment", "Housing", "Social issues"
- **必填**: 是
- **说明**: 特殊广告类别声明，某些行业需要特殊标注

#### ab_test（A/B测试）
- **类型**: String(50)
- **可选值**: "开启", "关闭"
- **必填**: 是
- **说明**: 是否启用A/B测试功能

#### campaign_budget_optimization（Campaign预算优化）
- **类型**: String(50)
- **可选值**: "开启", "关闭"
- **必填**: 是
- **说明**: 是否启用Campaign级别的预算优化（CBO）

#### budget_type（预算类型）
- **类型**: String(50)
- **可选值**: "Daily budget", "Lifetime budget"
- **必填**: 是
- **说明**: 预算分配方式

#### bid_strategy（出价策略）
- **类型**: String(100)
- **可选值**: "Lowest cost", "Cost cap", "Bid cap", "ROAS goal"
- **必填**: 是
- **说明**: 广告出价优化策略

#### spend_limit（花费限制）
- **类型**: Float
- **必填**: 否
- **说明**: 广告系列的总花费上限

#### status（状态）
- **类型**: Enum(CampaignStatus)
- **可选值**: "draft", "running", "review", "paused", "completed"
- **默认值**: "draft"
- **必填**: 是
- **说明**: 广告系列当前状态，前端默认为Draft且不可修改

## 数据流程

### 创建项目流程

1. **前端提交表单数据**
   ```typescript
   {
     channel: "Meta",
     name: "CB_US_Meta_AppPromotion",
     product: "休闲消除手游",
     countries: "美国 / 加拿大",
     account: "act_2194875301",
     campaignName: "Meta Campaign Name",
     objective: "App promotion",
     buyingType: "Auction",
     // ... 其他字段
   }
   ```

2. **后端创建 Project 记录**
   ```python
   project = Project(
       user_id=current_user["id"],
       name=data.name,
       product=data.product,
       total_budget=data.budget,  # 或计算得出
       start_date=data.start,
       end_date=data.end,
       status=ProjectStatus.ACTIVE
   )
   ```

3. **后端创建 Campaign 记录**
   ```python
   campaign = Campaign(
       project_id=project.id,
       name=data.campaignName,
       platform=Platform[data.channel],
       account_id=data.account,
       countries=data.countries,
       platform_campaign_id=None,  # 创建后由平台返回并更新
       objective=data.objective,
       buying_type=data.buyingType,
       special_ad_categories=data.specialAdCategories,
       ab_test=data.abTest,
       campaign_budget_optimization=data.campaignBudget,
       budget_type=data.budgetType,
       budget=float(data.budget),
       bid_strategy=data.bidStrategy,
       spend_limit=float(data.spendLimit) if data.spendLimit else None,
       status=CampaignStatus.DRAFT,
       start_date=data.start,
       end_date=data.end
   )
   ```

4. **调用平台API创建广告系列并更新platform_campaign_id**
   ```python
   # 调用Meta/Google/TikTok API创建广告系列
   platform_response = create_campaign_on_platform(campaign)

   # 更新platform_campaign_id
   campaign.platform_campaign_id = platform_response['id']
   db.commit()
   ```

## 数据库迁移

执行以下命令应用数据库变更：

```bash
cd /Users/micolin/Documents/MProjects/ANIFORCE/ANIFORCE/backend
alembic upgrade head
```

这将添加以下字段：

**projects 表**:
- product - 产品名称

**campaigns 表**:
- account_id - 广告账户ID
- platform_campaign_id - 平台广告系列ID（带索引）
- countries - 投放国家
- objective - 广告目标
- buying_type - 购买类型
- special_ad_categories - 特殊广告类别
- ab_test - A/B测试开关
- campaign_budget_optimization - Campaign预算优化开关
- budget_type - 预算类型
- bid_strategy - 出价策略
- spend_limit - 花费限制

## 注意事项

1. **字段验证**: 前端应该验证所有必填字段，后端也需要进行二次验证
2. **枚举值**: 确保前端的选项值与后端的枚举值完全匹配
3. **日期格式**: 前端日期字符串需要转换为后端的 Date 类型
4. **数值类型**: budget 和 spendLimit 需要从字符串转换为 Float
5. **状态管理**: Campaign 的 status 字段前端默认为 "Draft" 且不可修改
6. **账户关联**: account_id 必须是 sub_account_bindings 表中存在的有效账户ID，且该账户必须绑定到 campaigns 表中
7. **平台同步**: platform_campaign_id 在创建Campaign时为空，调用平台API创建广告系列后，需要将平台返回的ID存储到此字段
8. **数据绑定**: 通过 platform_campaign_id 可以实现本地Campaign与平台广告系列的双向同步

## 更新历史

- 2026-06-21: 初始版本，添加 Project 和 Campaign 的 Meta 广告字段映射
