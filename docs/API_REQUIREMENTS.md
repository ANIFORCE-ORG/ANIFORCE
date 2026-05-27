# ANIFORCE SaaS 0.5 API And Database Requirements

更新时间：2026-05-27

## 1. 目标

这份文档用于前端、后端、数据和投放 API 开发协作。0.5 版本优先跑通：

```text
User -> Organization -> Platform Account -> Project -> Campaign -> Ad Group -> Material -> Publish Task -> Report Metrics
```

前端可以先用 Demo fallback 保证流程可演示，但后端需要按以下模型补齐接口和数据库结构。

## 2. 当前后端差距

当前已有基础对象：

- `users`
- `projects`
- `campaigns`
- `materials`
- `metrics`
- `platform_connections`

0.5 缺口：

- 组织和成员：`organizations`、`organization_members`
- 平台广告账户：`platform_accounts`
- 项目到账户绑定：`project_platform_accounts`
- 计划层：`ad_groups`
- 素材版本：`creative_versions`
- 广告实例：`ads`
- 发布任务：`publish_tasks`
- 多平台扩展表：Meta / Google / TikTok
- 报表聚合：按平台、项目、投放活动、素材的 metrics API

## 3. 数据库设计原则

- 通用表保存广告主视角的共性字段。
- 平台扩展表保存平台专有字段、外部 ID、原始响应、错误码和同步状态。
- `Project` 是业务项目，不直接等于 Meta Campaign。
- `Campaign` 是投放活动，对应 Meta Campaign / Google Campaign / TikTok Campaign。
- `AdGroup` 是计划层，对应 Meta Ad Set / Google Ad Group / TikTok Ad Group。
- `Material` 是素材资产，不直接等于 Creative。
- `CreativeVersion` 保存素材文件、文案、标题、链接、CTA 的组合版本。
- 真实创建、修改、上下线都通过异步 `publish_tasks` 执行。
- 所有业务数据都必须带 `org_id` 或可追溯到 `org_id`。

## 4. 核心表

### organizations

```text
id
name
type: advertiser | agency
owner_user_id
status: active | disabled
created_at
updated_at
```

### organization_members

```text
id
org_id
user_id
role: owner | manager | operator
status: active | invited | requested | disabled
invited_by
created_at
updated_at
```

### platform_connections

现有表需要补充 `org_id`。

```text
id
org_id
user_id
platform: meta | google | tiktok
account_id
account_name
access_token_ref
refresh_token_ref
scopes
status: unauthorized | active | expired | revoked
last_sync_at
extra_data
created_at
updated_at
```

### platform_accounts

```text
id
org_id
connection_id
platform: meta | google | tiktok
external_account_id
account_name
business_name
currency
timezone
auth_status: authorized | expired | revoked | missing_scope
account_status: active | disabled | restricted | unknown
readiness_status: ready | warning | blocked
last_sync_at
raw_payload
created_at
updated_at
```

### project_platform_accounts

```text
id
org_id
project_id
platform_account_id
platform
status: active | disabled
created_at
updated_at
```

### projects

现有表需要补充 `org_id`。

```text
id
org_id
owner_user_id
name
description
target_market
total_budget
budget_strategy
status
created_at
updated_at
```

### campaigns

```text
id
org_id
project_id
platform
platform_account_id
name
objective
budget_mode
daily_budget
lifetime_budget
bid_strategy
desired_status
configured_status
effective_status
review_status
sync_status
platform_payload
created_at
updated_at
```

### ad_groups

```text
id
org_id
campaign_id
platform
platform_account_id
name
daily_budget
lifetime_budget
start_time
end_time
optimization_goal
billing_event
targeting
placement
attribution_spec
bid_amount
desired_status
configured_status
effective_status
review_status
sync_status
platform_payload
created_at
updated_at
```

### materials

现有表需要补充 `org_id`，并把素材类型扩展到图片/视频/文案组合。

```text
id
org_id
owner_user_id
name
type: image | video | text | mixed
status: draft | ready | processing | failed | archived
url
thumbnail_url
storage_provider
storage_key
duration
file_size
width
height
tags
created_at
updated_at
```

### creative_versions

```text
id
org_id
material_id
name
version
headline
primary_text
description
landing_url
cta
url_params
status: draft | ready | submitted | rejected | archived
created_at
updated_at
```

### ads

```text
id
org_id
campaign_id
ad_group_id
creative_version_id
platform
external_ad_id
name
desired_status
configured_status
effective_status
review_status
sync_status
platform_payload
created_at
updated_at
```

### publish_tasks

```text
id
org_id
task_type: create_campaign | update_campaign | pause | resume | sync_status
platform
project_id
campaign_id
ad_group_id
ad_id
status: queued | running | succeeded | failed | partial | cancelled
attempt_count
request_payload
response_payload
error_code
error_message
next_retry_at
created_by
created_at
updated_at
```

### report_metrics

```text
id
org_id
platform
platform_account_id
project_id
campaign_id
ad_group_id
ad_id
material_id
date
spend
impressions
clicks
ctr
conversions
cpa
cpi
roas
budget_pacing
fatigue_score
raw_payload
created_at
updated_at
```

## 5. 平台扩展表

Meta 第一版必须落表：

```text
meta_campaigns
meta_ad_sets
meta_creatives
meta_ads
meta_insights
meta_sync_tasks
```

Google / TikTok 0.5 可以先建能力占位，真实发布等 Meta 跑通后再接：

```text
google_campaigns
google_ad_groups
google_assets
google_ads
google_insights
google_sync_tasks

tiktok_campaigns
tiktok_ad_groups
tiktok_creatives
tiktok_ads
tiktok_reports
tiktok_sync_tasks
```

扩展表至少包含：

```text
id
org_id
common_object_id
external_id
platform_account_id
raw_request
raw_response
last_error_code
last_error_message
created_at
updated_at
```

## 6. API 需求

### Auth And Email

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `POST /auth/email/send-code`
- `POST /auth/email/verify`
- `POST /auth/password/forgot`
- `POST /auth/password/reset`

### Organizations

- `GET /organizations`
- `POST /organizations`
- `GET /organizations/:id`
- `PATCH /organizations/:id`
- `GET /organizations/:id/members`
- `POST /organizations/:id/invitations`
- `POST /organizations/:id/join-requests`
- `PATCH /organizations/:id/members/:memberId`
- `POST /me/current-organization`
- `GET /me/context`

### Platform Auth And Accounts

- `GET /platform-auth/connections`
- `POST /platform-auth/meta/config`
- `GET /platform-auth/meta/authorize_url/:connectionId`
- `POST /platform-auth/google/config`
- `GET /platform-auth/google/authorize_url/:connectionId`
- `DELETE /platform-auth/connections/:connectionId`
- `POST /platform-accounts/sync`
- `GET /platform-accounts?org_id=&platform=&status=`
- `GET /platform-accounts/:id/readiness`
- `POST /projects/:projectId/platform-accounts`
- `GET /projects/:projectId/platform-accounts`
- `DELETE /projects/:projectId/platform-accounts/:platformAccountId`

### Platform Capabilities

- `GET /platforms/capabilities`
- `GET /platforms/:platform/form-config`

Frontend uses these endpoints to render platform-specific fields without hardcoding every future platform into the page.

### Campaign Drafts And Publishing

- `POST /campaign-drafts`
- `PATCH /campaign-drafts/:id`
- `GET /campaign-drafts/:id`
- `POST /campaign-drafts/:id/submit`
- `GET /publish-tasks/:id`
- `GET /publish-tasks?campaign_id=`

### Campaign Runtime

- `GET /campaigns`
- `GET /campaigns/:id`
- `GET /campaigns/:id/ad-groups`
- `GET /campaigns/:id/tasks`
- `PATCH /campaigns/:id/status`

### Materials And OSS

- `POST /materials/upload-token`
- `POST /materials`
- `GET /materials?org_id=&project_id=&type=&status=`
- `GET /materials/:id`
- `PATCH /materials/:id`
- `POST /materials/:id/projects/:projectId`
- `DELETE /materials/:id/projects/:projectId`
- `POST /creative-versions`
- `GET /materials/:id/creative-versions`

### Reports

- `GET /reports/overview`
- `GET /reports/platforms`
- `GET /reports/projects`
- `GET /reports/campaigns`
- `GET /reports/materials`
- `GET /reports/insights`
- `GET /reports/alerts`

## 7. Frontend Development Rules

- Frontend pages show business concepts, not raw platform object names.
- Form rendering is platform-config driven after platform/account selection.
- Demo fallback is allowed only for local preview.
- Empty API response must not create blank first-level pages.
- Publish results are never assumed synchronous.
- Every page that reads business data must be ready for `org_id` context.

## 8. Open Questions

1. Organization role model: `owner / manager / operator` or only `manager / operator`.
2. Whether Google and TikTok 0.5 only support account binding and reports.
3. Whether project management and campaign management remain two first-level entries in 0.5.
4. OSS provider: Aliyun OSS or Tencent COS.
5. Email provider: Aliyun DirectMail, Tencent SES, or third-party email service.

## 9. Frontend Placeholders Implemented

2026-05-27 frontend branch has implemented Demo-compatible UI for the following contracts:

- Organization context:
  - `GET /organizations`
  - `POST /organizations`
  - `GET /organizations/:id/members`
  - `POST /organizations/:id/invitations`
  - `POST /me/current-organization`
- Platform account readiness:
  - `GET /platform-accounts?org_id=&platform=&status=`
  - `POST /platform-accounts/sync`
  - `GET /platform-accounts/:id/readiness`
- Campaign draft creation:
  - Existing `POST /campaigns` is still used as fallback.
  - Frontend now sends `platform_account_id` and structured `config` for Campaign / Ad Group / Creative.
  - Backend should replace this with `POST /campaign-drafts` and `POST /campaign-drafts/:id/submit`.
- Material upload:
  - Frontend attempts `POST /materials/upload-token`.
  - If unavailable, frontend creates local Demo material so campaign creation can continue.
- Reports:
  - `/monitor` is still Demo data.
  - UI now expects filters for time range, platform, and project.

These placeholders are intentionally frontend-only and should be replaced incrementally as backend endpoints become available.
