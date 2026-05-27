# ANIFORCE SaaS 0.5 迭代规划

更新时间：2026-05-27

## 1. 版本目标

SaaS 0.5 的目标不是一次性做完整广告投放平台，而是先让广告主能完成第一条广告计划的真实闭环：

```text
注册/登录 -> 创建或加入组织 -> 授权广告平台 -> 绑定广告账户 -> 创建项目 -> 创建单条广告计划 -> 上传/选择素材 -> 提交发布任务 -> 查看状态和数据
```

产品表达上保持广告主视角：

```text
项目 / 投放活动 / 计划 / 素材 / 状态 / 数据
```

内部结构保留跨平台扩展能力：

```text
Org -> User -> Platform Account -> Project -> Campaign -> Ad Group -> Material -> Report Metrics -> Task
```

Meta 适配层对应：

```text
Business / Ad Account -> Campaign -> Ad Set -> Asset + Creative + Ad -> Insights -> Sync Task
```

## 2. 当前分支状态

当前开发分支：

```text
feature/frontend-marketing-home-upgrade
```

已完成并提交到远程分支的内容：

- 官网首页双语、马上体验页面、登录入口联动。
- `/home` 新用户配置流程雏形。
- `/campaigns/create` 三栏布局、右侧 Agent 固定、项目/账户/素材选择、素材为空时跳转素材模块。
- 全局业务 Agent 会话，不再按一级菜单分别缓存。
- `/projects` 项目管理 Demo 数据和广告账户/计划聚合展示。
- `/campaign` 广告投放 Demo 数据和计划列表展示。
- `/monitor` 数据报表 Demo 数据和上下结构展示。
- 已补充一版前后端 API 协作需求文档。

未跟踪的本地文件不纳入提交：

```text
agent-ads-os/
backend/certs/
backend/data/ai_provider_config.json
backend/data/visual_provider_config.json
```

## 3. 总体优先级

### P0：主流程必须跑通

1. 正式登录与邮箱能力。
2. 组织、用户、角色、账户层级。
3. 广告平台授权与广告账户绑定。
4. 多广告平台对象模型和数据库结构。
5. 单条广告创建流程：Project / Campaign / Ad Group / Material。
6. 素材真实上传到 OSS。
7. 发布任务状态和错误回写。

### P1：可运营和可复盘

1. 数据报表信息架构和真实数据接入。
2. 项目管理与广告投放列表的筛选、状态、详情。
3. Agent 提醒、异常解释、下一步动作建议。
4. 官网首页继续优化为更高级的产品展示。
5. Google MA 授权。

### P2：效率提升

1. 批量创建广告。
2. 自动调优和回退策略。
3. 多平台扩展：TikTok、Google、国内平台。
4. 任务中心、审计日志、权限高级配置。

## 4. 模块迭代规划

### 4.1 登录、邮箱和身份基础

目标：

- 登录页从 Demo 状态进入正式可用。
- 邮箱作为主登录方式，Google/Facebook 作为辅助登录。
- Apple 暂不接入。

前端任务：

- 优化 `/login`、`/register`、忘记密码页面的正式交互。
- 增加邮箱验证码、重置密码、登录异常状态。
- 增加组织选择或创建后的跳转逻辑。

后端/API 需求：

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `POST /auth/email/send-code`
- `POST /auth/email/verify`
- `POST /auth/password/forgot`
- `POST /auth/password/reset`
- 邮箱验证码有效期、频控、错误次数限制、黑名单/白名单策略。

非代码事项：

- 调研并采购邮箱服务：阿里云邮件推送、腾讯云 SES、SendGrid 等。
- 确认发信域名、SPF/DKIM/DMARC 配置。

验收：

- 新用户可通过真实邮箱注册。
- 已注册用户可登录。
- 忘记密码流程可完成。
- 无真实邮箱服务时，前端清晰显示当前环境限制。

### 4.2 组织、角色和账户层级

目标：

- 引入组织概念，支持广告主团队和代理商多组织场景。
- 最小模型为 `组织 -> 用户 -> 广告账户`。
- 角色先支持 Manager 和 Operator。

前端任务：

- 新增组织创建/加入流程。
- Settings 增加组织管理、成员管理、邀请成员、加入请求。
- 业务页全局显示当前组织上下文。
- 项目、素材、广告账户都归属组织，避免个人账号数据混用。

建议数据模型：

```text
Organization
- id
- name
- type: advertiser | agency
- owner_user_id
- created_at

OrganizationMember
- org_id
- user_id
- role: manager | operator
- status: active | invited | requested | disabled

PlatformAccount
- org_id
- platform
- account_id
- account_name
- auth_status
- account_status
- currency
- timezone
```

后端/API 需求：

- `GET /organizations`
- `POST /organizations`
- `GET /organizations/:id/members`
- `POST /organizations/:id/invitations`
- `POST /organizations/:id/join-requests`
- `PATCH /organizations/:id/members/:memberId`
- `GET /me/context`
- `POST /me/current-organization`

验收：

- 用户首次登录必须进入一个组织。
- Manager 可邀请和审核成员。
- Operator 只能看到被授权组织下的数据。
- 多组织之间项目、素材、广告账户隔离。

### 4.3 平台授权和广告账户绑定

目标：

- Settings 页完成 Meta / Google 授权配置和广告账户同步。
- 创建广告前必须选择可投放账户。
- 授权连接和广告账户分开管理。

前端任务：

- 完善 `/platform-connections`：连接状态、授权入口、同步账户、断开连接。
- 增加广告账户列表和账户资产完整度展示。
- 在 `/campaigns/create` 和项目管理中复用账户选择逻辑。
- Google 授权先预留 UI，真实能力受备案和 OAuth 审核影响。

广告账户前置检查：

```text
账户授权状态
币种 / 时区
Page / IG
Pixel / Dataset
App / Store URL
支付状态
最近同步时间
```

后端/API 需求：

- `GET /platform-auth/connections`
- `POST /platform-auth/meta/config`
- `GET /platform-auth/meta/authorize_url/:connectionId`
- `POST /platform-auth/google/config`
- `GET /platform-auth/google/authorize_url/:connectionId`
- `POST /platform-accounts/sync`
- `GET /platform-accounts?org_id=&platform=&status=`
- `POST /projects/:projectId/platform-accounts`
- `GET /projects/:projectId/platform-accounts`
- `GET /platform-accounts/:id/readiness`

验收：

- Meta 授权后能同步广告账户。
- 项目可以绑定一个或多个平台广告账户。
- 创建广告时只能选择已授权且满足基础条件的账户。

### 4.4 多广告平台、数据库结构和前端适配

目标：

- 先把跨平台的通用模型和平台差异边界定义清楚，再开发复杂页面。
- 数据库不强行把 Meta / Google / TikTok 的字段塞进一张大表。
- 前端用统一业务心智展示，但表单、校验、发布任务按平台适配。

建议架构：

```text
通用业务层：
Org / User / Project / PlatformAccount / Campaign / AdGroup / Material / ReportMetric / Task

平台适配层：
MetaCampaign / MetaAdSet / MetaCreative / MetaAd / MetaInsight / MetaSyncTask
GoogleCampaign / GoogleAdGroup / GoogleAsset / GoogleAd / GoogleInsight / GoogleSyncTask
TikTokCampaign / TikTokAdGroup / TikTokCreative / TikTokAd / TikTokReport / TikTokSyncTask
```

数据库设计原则：

- 通用表保存广告主视角和跨平台共性字段。
- 平台表保存平台专有字段、外部 ID、原始响应、错误码和同步状态。
- `Project` 是业务项目，不直接等于任何平台 Campaign。
- `Campaign` 对应一次投放活动，可映射 Meta Campaign / Google Campaign / TikTok Campaign。
- `AdGroup` 对应计划层，可映射 Meta Ad Set / Google Ad Group / TikTok Ad Group。
- `Material` 是素材资产，不直接等于 Creative；Creative 应支持版本化。
- 所有真实创建、修改、上下线都通过异步 `Task` 执行。

建议核心表：

```text
organizations
organization_members
platform_connections
platform_accounts
projects
project_platform_accounts
campaigns
ad_groups
materials
creative_versions
ads
publish_tasks
report_metrics
agent_events
```

平台扩展表：

```text
meta_campaigns / meta_ad_sets / meta_creatives / meta_ads / meta_insights / meta_sync_tasks
google_campaigns / google_ad_groups / google_assets / google_ads / google_insights / google_sync_tasks
tiktok_campaigns / tiktok_ad_groups / tiktok_creatives / tiktok_ads / tiktok_reports / tiktok_sync_tasks
```

前端跟随方式：

- 一级导航保持广告主视角：项目管理、广告投放、创意素材、数据报表、账户设置。
- 创建广告页使用平台配置驱动字段：先选平台，再加载对应字段、校验和默认值。
- 列表页展示通用字段，详情页增加平台专有状态和错误解释。
- 表单组件分层：通用段落组件 + 平台字段组件。
- API 类型先定义通用响应，再通过 `platform_config` 或 `platform_payload` 承载差异。

前端需要的配置结构：

```ts
interface PlatformFormConfig {
  platform: 'meta' | 'google' | 'tiktok'
  campaignFields: FieldConfig[]
  adGroupFields: FieldConfig[]
  creativeFields: FieldConfig[]
  readinessChecks: ReadinessCheck[]
  defaults: Record<string, unknown>
}
```

后端/API 需求：

- `GET /platforms/capabilities`
- `GET /platforms/:platform/form-config`
- `GET /platform-accounts/:id/readiness`
- `POST /campaign-drafts`
- `PATCH /campaign-drafts/:id`
- `POST /campaign-drafts/:id/submit`
- `GET /publish-tasks/:id`
- `GET /publish-tasks?campaign_id=`

开发顺序：

1. 先评审数据库对象和 API 契约。
2. 前端补类型和 mock config。
3. 创建广告页按 config 渲染 Meta 第一版。
4. Google / TikTok 先只做能力占位，不做真实发布。
5. 后端完成 Meta 发布链路后，前端替换 Demo fallback。

验收：

- 同一个项目下可以绑定不同平台账户。
- 创建广告时先选择平台和账户，再进入平台表单。
- Meta 表单可完整创建草稿。
- Google / TikTok 在未接入时明确显示“待接入”，不伪装成已可发布。

### 4.5 Project / Campaign / Ad Group / Ad 创建流程

目标：

- 先跑通单条广告创建。
- 分平台表单，不强行做一个完全统一表单。
- 保存草稿和提交发布分开。

前端流程：

```text
Step 1 项目和广告账户
Step 2 投放活动目标和预算模式
Step 3 计划预算、人群、地区、版位
Step 4 素材、文案、链接、CTA
Step 5 确认并保存草稿 / 提交发布
```

页面要求：

- 保持三栏结构：左侧导航、中间业务、右侧 Agent。
- 右侧 Agent 固定，不随页面下沉。
- 点击下一步后，中间内容回到顶部。
- 项目为空时允许先创建项目，再继续创建广告。
- 按钮和表单遵循当前蓝色 SaaS UI，不出现文字换行。

前端任务：

- 把当前 `/campaigns/create` 拆清 Campaign 字段和 Ad Group 字段。
- 增加草稿状态、发布任务状态、错误提示。
- 增加平台差异字段配置，先实现 Meta，Google/TikTok 预留。
- 广告投放一级页补齐列表、状态、筛选和详情入口。

后端/API 需求：

- `POST /campaign-drafts`
- `PATCH /campaign-drafts/:id`
- `POST /campaign-drafts/:id/submit`
- `GET /campaigns`
- `GET /campaigns/:id`
- `GET /campaigns/:id/ad-groups`
- `GET /campaigns/:id/tasks`
- `PATCH /campaigns/:id/status`

Meta 发布任务后端能力：

```text
创建 Campaign
创建 Ad Set
创建 Asset / Creative
创建 Ad
回写 external ids
回写 configured_status / effective_status / review_status / sync_status
失败重试和错误解释
```

验收：

- 无素材时可跳转素材模块创建素材，返回后继续。
- 可保存草稿。
- 可提交发布任务。
- 发布后列表能看到任务状态和平台状态。

### 4.6 素材创建和 OSS 上传

目标：

- 素材模块从 Demo/静态能力升级为真实上传和可复用素材库。
- 素材在组织维度共享，可绑定项目和计划。

前端任务：

- 素材模块增加真实上传入口。
- 支持图片/视频基础预览、标签、项目绑定。
- 创建广告时可选择素材并补充文案、标题、链接、CTA。
- 素材为空时在弹窗中提供清晰创建入口。

后端/API 需求：

- `POST /materials/upload-token`
- `POST /materials`
- `GET /materials?org_id=&project_id=&type=&status=`
- `GET /materials/:id`
- `PATCH /materials/:id`
- `POST /materials/:id/projects/:projectId`
- `DELETE /materials/:id/projects/:projectId`

OSS 需求：

- 调研阿里云 OSS / 腾讯云 COS。
- 支持前端直传签名。
- 区分原文件、缩略图、转码结果。
- 设置访问权限、生命周期、CDN 预留。

验收：

- 前端能真实上传素材。
- 上传后素材库立即可见。
- 创建广告时可选择刚上传的素材。

### 4.7 数据展示和报表模块

目标：

- 数据概览合并到数据报表。
- 报表先做广告主能看懂的经营视角，再补平台细节。

前端信息架构：

```text
总体表现
平台表现
项目表现
投放活动表现
素材表现
异常提醒
AI 洞察和下一步动作
```

前端任务：

- `/monitor` 保持上下结构，不做拥挤左右结构。
- 增加时间区间、平台、项目筛选。
- 平台表现、AI 洞察、素材排行使用真实数据 fallback 到 Demo 数据。
- 数据为空时展示业务解释和下一步动作，不展示空白页。

后端/API 需求：

- `GET /reports/overview`
- `GET /reports/platforms`
- `GET /reports/projects`
- `GET /reports/campaigns`
- `GET /reports/materials`
- `GET /reports/insights`
- `GET /reports/alerts`

核心指标：

```text
spend
impressions
clicks
ctr
conversions
cpa / cpi
roas
budget_pacing
fatigue_score
anomaly_type
```

验收：

- 报表页没有空白入口。
- 可按时间、平台、项目查看数据。
- Agent 提醒能对应报表异常。

### 4.8 官网首页和产品首页

目标：

- 官网首页更高级，但不脱离真实系统 UI。
- 产品首页从“数据概览”转为主会话/任务入口。

前端任务：

- 官网首页继续优化首屏：使用真实后台 UI 缩放展示或高质量系统截图，不再做假 mock。
- CN/EN 切换覆盖导航、页尾、示意图文字、Agent 对话。
- 产品 `/home` 首次进入弹窗放到组织、账户、平台对象和创建广告结构稳定后开发。
- 首页 Agent 会话成为主入口，但保留 SaaS 页面结构。

验收：

- 官网一眼知道 aniforce 是广告 AI 引擎。
- 示例 UI 不出现假字段、文字截断、菜单换行。
- 登录后进入产品系统，能开始创建第一条广告。

## 5. 基础设施和非前端事项

### 域名备案 / 域名绑定

事项：

- 跟进备案进度。
- 确认域名解析、HTTPS 证书、前端站点和 API 域名规划。
- Google 授权依赖备案和 OAuth 回调域名。

建议负责人：

- 产品/运营负责资料。
- 后端/运维负责域名、证书、回调地址。

### 新加坡服务器

事项：

- 采购新加坡节点服务器。
- 区分测试环境和生产环境。
- 配置日志、监控、备份和部署流程。

建议：

- 先采购一台可承载 0.5 Demo 的应用服务器。
- 数据库、OSS、邮件服务使用云服务托管。

### OSS 服务

事项：

- 调研阿里云 OSS、腾讯云 COS。
- 确认海外访问速度、费用、权限模型、图片/视频处理能力。

前端关注：

- 需要上传签名接口。
- 不在前端保存永久密钥。

### 邮箱服务

事项：

- 调研阿里云邮件推送、腾讯云 SES、SendGrid。
- 完成发信域名认证。
- 支持验证码、邀请、重置密码、授权提醒。

## 6. 开发节奏建议

### Sprint 1：结构和模型先行

范围：

- 组织模型 UI。
- Settings 平台授权和广告账户同步 UI。
- 多平台对象模型、数据库结构、API 契约文档。
- `/campaigns/create` 按平台、账户、Campaign、Ad Group、Material 重构字段。

验收：

- 使用 Demo 数据可以走通 Meta 第一条广告创建草稿流程。
- 所有一级入口不为空。
- 三栏结构和 Agent 固定逻辑不回退。

### Sprint 2：真实素材和账户接入

范围：

- OSS 上传。
- 素材库真实上传和选择。
- Meta 授权账户同步。
- 项目绑定账户。

验收：

- 能上传素材。
- 能选择真实或模拟授权账户。
- 创建广告时项目、账户、素材数据都来自统一结构。

### Sprint 3：Meta 单条发布链路

范围：

- 保存草稿。
- 提交发布任务。
- Meta Campaign / Ad Set / Creative / Ad 异步创建。
- 任务状态回写。

验收：

- 可以从前端提交一条 Meta 发布任务。
- 成功/失败状态能在广告投放页展示。
- 失败原因可读，并有下一步建议。

### Sprint 4：产品首页和首次进入流程

范围：

- `/home` 首次进入弹窗：新手指导流程 / 熟悉模式。
- 产品首页作为主对话和任务入口。
- 根据已确定的组织、账户、平台对象结构，串联新手配置流程。
- 官网首页继续优化首屏展示。

验收：

- 首次进入不会提前写死错误流程。
- 新手引导能复用真实组织、平台账户、项目和广告创建结构。
- 熟悉模式可直接进入产品工作台。

### Sprint 5：报表和复盘

范围：

- 报表真实 API 接入。
- 项目、平台、素材表现。
- 异常提醒和 Agent 下一步动作。

验收：

- 报表页可看真实投放数据。
- Agent 提醒和报表数据能对应。

## 7. 近期可立即开工的前端任务

建议从以下顺序开始：

1. 补充多平台对象模型、数据库结构和 API 契约文档。
2. 新增组织上下文 UI 和 Settings 组织管理入口。
3. 完善平台授权和广告账户绑定 UI。
4. 重构 `/campaigns/create` 中间表单，明确平台、账户、Campaign、Ad Group、素材五段。
5. 补齐 `/projects`、`/campaign` 和 `/monitor` 的 Demo 数据与空状态逻辑，保证演示完整。
6. 素材模块增加上传 UI 和 OSS 接口占位。
7. 输出 `API_REQUIREMENTS.md`，把邮箱、组织、平台账户、素材、投放发布、报表接口集中列清楚。
8. 最后再开发 `/home` 首次进入弹窗和新手引导，避免在结构未稳定前返工。

## 8. 协作规则

- 前端可以先用 Demo fallback 保证流程可演示，但必须在页面和文档标注接口替换点。
- 后端接口未满足时，不在前端硬编码真实业务结论，只展示“待同步 / 待授权 / 待发布”等状态。
- 所有广告平台真实发布都走异步任务，不做同步成功假设。
- 组织、广告账户、素材、项目必须带 `org_id` 或等价上下文。
- 每次提交前执行：

```bash
cd frontend/packages/main-app
npm run build
```

- 每次提交同步更新：

```text
docs/frontend-collaboration-progress-2026-05-25.md
docs/saas-0.5-iteration-plan-2026-05-27.md
```

## 9. 待确认问题

1. 组织角色是否只保留 Manager / Operator，还是需要 Owner 单独拆出。
2. 0.5 第一版真实发布平台是否只做 Meta。
3. Google MA 授权在备案完成前是否只做 UI 和接口占位。
4. OSS 服务优先选阿里云还是腾讯云。
5. 邮箱服务优先选阿里云还是腾讯云。
6. 项目管理和广告投放两个一级入口是否在 0.5 保持分开，还是合并为一个“广告管理”。
7. 任务中心是否进入 0.5，还是放到 1.0 前的效率增强阶段。
8. 数据库采用“通用表 + 平台扩展表”，还是每个平台完全独立表后再聚合。
9. Google / TikTok 是否只做账户绑定和报表，发布能力放到 Meta 跑通之后。
