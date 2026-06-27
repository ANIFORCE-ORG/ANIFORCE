# 素材管理条式预览与数据评估开发计划

## 目标

参考 `docs/design/aniforce-素材-增加条式预览和数据评估-v1.1.html`，把当前素材管理页从卡片素材库升级为：

- 素材周期看板：展示消耗、展示、点击、CTR、ROAS、CPC 等周期汇总。
- 素材智能分析：基于当前筛选和周期给出放量、预算、疲劳、短视频表现提示。
- 条式素材列表：用表格/条形行展示素材名称、缩略图、来源、创建时间、时长、消耗、展示、点击、CTR、ROAS、转化成本。
- 右侧详情预览：点击素材后打开详情面板，直接使用 OSS 签名 URL 或素材 URL 预览图片/视频。
- 保留现有能力：OSS 上传、素材刷新、登录态、当前 backend API 权限校验。

## 现状判断

### 当前前端

文件：`frontend/packages/main-app/src/pages/creatives/Material.vue`

当前页面已经具备：

- 登录后加载 `/api/v1/materials`。
- 上传文件到 `/api/v1/materials/upload`。
- 通过 `/api/v1/materials/{id}/image?thumbnail=true` 获取预览源。
- `previewData.url || previewData.data || material.thumbnail_url || material.url` 的预览回退链路。
- 卡片网格展示、上传弹窗、基础详情预览。
- 前端 API 层已有 `createMaterial`、`deleteMaterial`、项目关联/移除方法，但页面未完整暴露这些管理操作。

主要缺口：

- 页面结构不是设计稿里的条式表格。
- 缺少周期筛选、平台/来源/比例/表现筛选。
- 缺少周期指标汇总和智能分析区。
- 缺少详情面板里的平台、版位、审核、绑定计划、授权、疲劳度、评分等字段。
- 缺少素材编辑、删除确认、批量归档/删除、批量打标签、绑定/解绑项目和广告计划等管理能力。
- 缺少素材生命周期状态设计，例如草稿、可投放、投放中、审核中、已归档、已删除。
- 缺少上传后的处理状态展示，例如上传中、转码中、缩略图生成中、处理失败。
- 当前有大量 mock 卡片数据，正式改造时应去掉或降级为开发兜底。

### 当前 API 和数据模型

文件：

- `frontend/packages/main-app/src/api/materials.ts`
- `backend/app/api/v1/materials.py`
- `backend/app/models/material.py`
- `backend/app/repositories/impl/sqlite_material_repo.py`

当前 `Material` 已有字段：

- `id`
- `user_id`
- `project_ids`
- `campaign_ids`
- `name`
- `type`
- `status`
- `url`
- `thumbnail_url`
- `ctr_estimate`
- `tags`
- `duration`
- `file_size`
- `created_at`

设计稿需要但当前缺少的字段：

- 素材元信息：`format`、`width`、`height`、`ratio`、`source`、`creator`、`rights`。
- 平台信息：`platforms`、`review_status`、`source_account`、`placements`。
- 绑定信息：`campaign_name`、`plan_name`、`objective`、`associated_account_count`、`associated_plan_count`、`associated_unit_count`。
- 表现数据：`spend`、`impressions`、`clicks`、`conversions`、`revenue`、`ctr`、`cvr`、`roas`、`cpc`、`cpa`。
- 评估数据：`score`、`fatigue`、`last_used_at`。

当前 CRUD 缺口：

- `POST /materials/upload` 已有，用于文件上传并创建素材。
- `POST /materials` 已有，但参数是 query/body 混用风格，后续应改成明确 request body schema。
- `GET /materials` 和 `GET /materials/{id}` 已有。
- `DELETE /materials/{id}` 已有，但当前是硬删除语义，是否同步删除 OSS 对象、是否保留投放引用需要重新定义。
- 缺少 `PATCH /materials/{id}`：编辑名称、标签、状态、来源、授权、平台、审核、绑定信息等。
- 缺少批量接口：批量删除、批量归档、批量打标签、批量加入项目/广告计划。
- 缺少素材处理接口：生成缩略图、生成视频 poster、生成低码率预览、重试处理。

## 开发原则

- 不破坏现有 OSS 上传和预览：素材媒体仍以 backend 返回的签名 URL 为首选。
- 第一版不引入复杂投放数据同步系统，先做可验证的数据展示合约。
- 新字段优先用兼容方式扩展，避免一次性重构素材表和投放指标表。
- 前端先实现真实接口驱动，缺失字段由 adapter 统一补默认值，不在模板里散落判断。
- 表现指标计算放在前端 adapter 或 backend summary endpoint 中，避免在 Vue 模板中写复杂计算。
- 素材预览必须分层：列表用缩略图或 poster，详情优先用压缩预览资源，下载/查看原文件才使用原始素材。
- 删除默认应优先软删除或归档，避免误删仍被广告计划引用的素材和 OSS 原文件。

## 代码、表结构和样本审计

### SQLite 表结构事实

当前 `backend/data/sqlite/animagus.db`：

- `materials`：8 条。
- `campaigns`：22 条。
- `metrics`：56 条。
- `projects`：15 条。
- `users`：7 条。

`materials` 当前字段：

| 字段 | 类型 | 设计稿承接情况 |
|---|---|---|
| `id` | VARCHAR(36) | 可直接用于素材 ID。 |
| `user_id` | VARCHAR(36) | 权限过滤使用，不直接展示。 |
| `project_ids` | TEXT JSON | 可用于关联项目数量，但当前是 JSON 文本。 |
| `campaign_ids` | TEXT JSON | 可用于关联计划数量和 campaign metrics 粗略归因。 |
| `name` | VARCHAR(255) | 可直接展示。 |
| `type` | VARCHAR(10) | 当前值如 `FULL_VIDEO`，需要 adapter 映射为 `video/image`。 |
| `status` | VARCHAR(7) | 当前值如 `RUNNING/READY/FATIGUE`，需要映射为设计稿状态。 |
| `url` | TEXT | 当前已是 OSS URL，可作为 original URL。 |
| `thumbnail_url` | TEXT | 当前与 `url` 相同，未真正区分缩略图。 |
| `ctr_estimate` | FLOAT | 可作为无真实 CTR 时的兜底展示。 |
| `tags` | TEXT JSON | 可直接展示和搜索。 |
| `duration` | INTEGER | 可展示秒数，但设计稿是 `00:18` 格式。 |
| `file_size` | INTEGER | 可格式化为 KB/MB。 |
| `created_at` | DATETIME | 可展示创建时间、最近上传排序。 |

`campaigns` 当前可利用字段：

| 字段 | 用途 |
|---|---|
| `id` | 与 `materials.campaign_ids` 对齐。 |
| `name` | 详情里的绑定 Campaign/计划名称。 |
| `platform` | 可推导素材平台集合。 |
| `status` | 可辅助推导投放状态。 |
| `material_ids` | 反向素材关联，当前部分 sample 为空。 |
| `account_id` | 可作为来源账号兜底。 |
| `objective` | 详情中的广告目标。 |
| `spent` | campaign 当前已花费，但不能精确归因到素材。 |

`metrics` 当前是 campaign 粒度：

- 有 `campaign_id`、`timestamp`、`platform`、`impressions`、`clicks`、`conversions`、`installs`、`spend`、`revenue`、`ctr`、`cvr`、`cpa`、`cpi`、`roi`。
- 没有 `material_id`，所以无法严格计算单素材表现。
- MVP 可以用 `materials.campaign_ids` 找到关联 campaign，把 campaign metrics 按关联素材数量均摊；这必须在 UI 标注为“按关联计划估算”或仅用于 demo。
- 正式方案需要新增 `material_metrics`，否则设计稿里的素材级 ROAS/CPC/疲劳度没有可靠来源。

### 当前样本特征

8 条素材都属于 `user_test_001`，示例：

- `mat_001`：`Candy Blast - Boss 战高光`，`FULL_VIDEO`，`RUNNING`，关联 `camp_g001/camp_m001`。
- `mat_006`：`DramaBox - 霸总钩子`，`FULL_VIDEO`，`RUNNING`，关联 `camp_d001/camp_d002`。
- `mat_008`：`DramaBox - 霸总浪漫`，`FULL_VIDEO`，`FATIGUE`，关联 `camp_d002/camp_d004`。

重要问题：

- 虽然 `type=FULL_VIDEO`，当前 `url/thumbnail_url` 指向的是 `.jpg` OSS 对象。这说明旧样本更像“视频素材的封面图/演示图”，不是可播放视频原文件。
- 不能只根据 `type=FULL_VIDEO` 就在列表里渲染 `<video>`。前端必须结合 `mime_type`、URL 扩展名或后端返回的 `media_kind`/`preview_variant` 决定渲染 `img` 还是 `video`。

### 当前前端承接差距

`frontend/packages/main-app/src/pages/creatives/Material.vue` 当前模板：

- 中间内容是三张功能卡片 + 搜索 + 卡片网格。
- 列表中视频素材会直接渲染 `<video :src="getMaterialImageSrc(creative)" autoplay loop muted>`。
- 详情弹窗也会对视频素材直接用 `<video :src="getMaterialImageSrc(previewMaterial)" controls autoplay>`。
- 这与设计稿的条式列表、右侧抽屉、周期看板不一致，也有预览性能风险。

`frontend/packages/main-app/src/api/http.ts` 当前问题：

- 有 `get/post/put/delete`，没有 `patch`。
- 如果新增 `PATCH /materials/{id}`，需要先补 `http.patch<T>()`。

`frontend/packages/main-app/src/api/materials.ts` 当前问题：

- `Material` 类型字段少于设计稿。
- `getMaterialImage()` 注释仍写“Base64 编码”，但后端对 OSS 会返回 signed URL。
- 有 `createMaterial/deleteMaterial` API 方法，但页面没有接入编辑、删除、归档。

### 当前后端承接差距

`backend/app/api/v1/materials.py`：

- 有 `GET /materials`、`GET /materials/{id}`、`GET /materials/{id}/image`、`POST /materials/upload`、`POST /materials`、`DELETE /materials/{id}`。
- 缺少 `PATCH /materials/{id}`。
- `POST /materials` 当前用函数参数声明，不是 Pydantic request body，不利于前端标准 JSON 调用。
- `DELETE /materials/{id}` 是硬删除 repository 记录，没有软删除/归档语义。
- `/materials/{id}/image` 只有 `thumbnail=true/false`，无法表达 `thumbnail/preview/poster/original`。

`backend/app/services/object_storage.py`：

- 上传只保存一个 OSS object。
- 没有生成缩略图、poster 或压缩 preview。
- 没有独立上传派生资源的方法，后续可新增 `upload_bytes()` 或 `upload_derivative()`。

## 具体改动方案

### 数据模型方案

第一步建议在 `materials` 表上做兼容扩展，不立即拆多张复杂表：

| 新字段 | 类型建议 | 说明 |
|---|---|---|
| `media_kind` | String | `image/video`，前端渲染依据，不再只依赖 `type`。 |
| `format` | String | `JPG/PNG/WEBP/MP4/MOV`。 |
| `width` | Integer nullable | 图片/视频宽度。 |
| `height` | Integer nullable | 图片/视频高度。 |
| `ratio` | String nullable | `9:16/1:1/4:5/16:9/1.91:1/unknown`。 |
| `original_url` | Text nullable | 原始素材 URL；迁移时用现有 `url` 回填。 |
| `preview_url` | Text nullable | 中等尺寸图片或低码率视频 URL。 |
| `poster_url` | Text nullable | 视频封面图 URL。 |
| `source` | String nullable | `OSS 上传/Meta 导入/TikTok Spark/AI 生成/本地上传`。 |
| `creator` | String nullable | 创建人/上传人。 |
| `rights` | Text nullable | 授权说明。 |
| `platforms_json` | Text nullable | 平台集合 JSON。 |
| `review_status` | String nullable | 平台审核状态。 |
| `source_account` | String nullable | 来源账号。 |
| `placements_json` | Text nullable | 版位集合 JSON。 |
| `score` | Integer nullable | 素材评分。 |
| `fatigue` | Integer nullable | 疲劳度 0-100。 |
| `last_used_at` | DateTime nullable | 最近投放/使用时间。 |
| `deleted_at` | DateTime nullable | 软删除。 |
| `processing_status` | String nullable | `ready/processing/failed`。 |
| `processing_error` | Text nullable | 处理失败原因。 |

为了支持真实素材级数据，新增 `material_metrics`：

| 字段 | 类型建议 | 说明 |
|---|---|---|
| `id` | String PK | 指标记录 ID。 |
| `material_id` | String FK | 素材 ID。 |
| `campaign_id` | String nullable | 来源 campaign。 |
| `timestamp` | DateTime index | 指标时间。 |
| `platform` | String | 平台。 |
| `impressions` | Integer | 展示。 |
| `clicks` | Integer | 点击。 |
| `conversions` | Integer | 转化。 |
| `spend` | Float | 消耗。 |
| `revenue` | Float | 收入。 |

MVP 可先不导入真实 `material_metrics`，但接口结构先按它设计；没有数据时使用 campaign 均摊估算或返回 0。

### 后端接口方案

新增/调整接口：

- `GET /api/v1/materials`
  - 新增参数：`include_metrics=true`、`period=7d|14d|30d|all`、`platform`、`source`、`status`、`ratio`、`metric`、`sort`。
  - 返回素材列表时带 `metrics_summary` 和 `associations`。
- `GET /api/v1/materials/overview`
  - 返回当前筛选下的周期汇总和智能分析基础数据。
- `PATCH /api/v1/materials/{material_id}`
  - 编辑名称、标签、状态、来源、授权、平台、审核、版位。
- `POST /api/v1/materials/{material_id}/archive`
  - 软归档，推荐替代直接删除。
- `DELETE /api/v1/materials/{material_id}`
  - 第一版改为软删除或只允许无引用素材硬删。
- `GET /api/v1/materials/{material_id}/preview?variant=thumbnail|preview|poster|original`
  - 返回 `{ url, mime_type, variant, expires_at }`。
  - 旧 `/image?thumbnail=true` 保留兼容。
- `POST /api/v1/materials/{material_id}/retry-processing`
  - 后续用于重试缩略图/转码处理。

推荐响应结构：

```json
{
  "id": "mat_001",
  "name": "Candy Blast - Boss 战高光",
  "media_kind": "video",
  "status": "running",
  "source": "OSS 上传",
  "platforms": ["Google", "Meta"],
  "ratio": "unknown",
  "duration": 15,
  "file_size": 159532,
  "thumbnail_url": "...signed...",
  "preview_url": "...signed...",
  "original_url": "...signed...",
  "tags": ["Boss挑战", "高奖励"],
  "associations": {
    "project_count": 1,
    "campaign_count": 2,
    "campaign_names": ["..."],
    "account_count": 1,
    "unit_count": 0
  },
  "metrics_summary": {
    "spend": 0,
    "impressions": 0,
    "clicks": 0,
    "conversions": 0,
    "revenue": 0,
    "ctr": 0,
    "cvr": 0,
    "roas": 0,
    "cpc": 0,
    "cpa": 0,
    "estimated": true
  }
}
```

### 后端实现文件

必须改：

- `backend/app/models/material.py`
  - 增加字段、JSON helper、软删除状态。
- `backend/app/models/material_metric.py`
  - 新增素材指标模型。
- `backend/app/models/__init__.py`
  - 导出新模型。
- `backend/alembic/versions/*_add_material_management_fields.py`
  - 增加字段和 `material_metrics` 表。
- `backend/app/repositories/protocols.py`
  - MaterialRepository 增加 `update/archive/list_with_metrics`。
- `backend/app/repositories/impl/sqlite_material_repo.py`
  - `_to_dict()` 输出新字段。
  - `list_by_user()` 默认过滤 `deleted_at is null`。
  - 新增 `update()`、`archive()`。
- `backend/app/api/v1/materials.py`
  - Pydantic request/response schema。
  - `PATCH`、archive、preview variant、overview。
- `backend/app/services/object_storage.py`
  - 增加派生资源上传能力。
- `backend/app/services/material_preview_service.py`
  - 负责 thumbnail/poster/preview 资源选择和后续生成。

可后置：

- 真正的视频转码任务队列。
- 与 Meta/TikTok/Google 同步素材审核状态。
- 精确素材级归因导入。

### 前端类型和数据承接

`frontend/packages/main-app/src/api/http.ts`：

- 新增：

```ts
async patch<T>(endpoint: string, body?: any, options?: RequestOptions): Promise<T> {
  return this.request<T>(endpoint, { ...options, method: 'PATCH', body })
}
```

`frontend/packages/main-app/src/api/materials.ts`：

- 扩展 `Material` 或新增 `MaterialListItemResponse`。
- 新增：
  - `updateMaterial(materialId, data)`
  - `archiveMaterial(materialId)`
  - `getMaterialPreview(materialId, variant)`
  - `getMaterialOverview(params)`
  - `retryMaterialProcessing(materialId)`

新增 adapter：

- `frontend/packages/main-app/src/pages/creatives/materialsAdapter.ts`

职责：

- 把后端 `RUNNING/READY/FATIGUE` 映射到设计稿状态文案。
- 把 `FULL_VIDEO` + URL/mime 信息映射为 `mediaKind`。
- 格式化秒数、文件大小、日期。
- 汇总 metrics，避免模板中计算 NaN。
- 提供搜索字段 `searchText`。
- 提供设计稿需要的 `MaterialTableRow`。

### 前端组件如何承接设计稿

当前 `Material.vue` 不建议继续堆大文件，按设计稿拆组件：

| 设计稿模块 | Vue 组件 | 当前代码替换点 |
|---|---|---|
| Header actions | `MaterialHeader.vue` | 替换当前 50px header。 |
| 素材周期看板 | `MaterialMetricsPanel.vue` | 新增，位于 header 下方。 |
| 素材智能分析 | `MaterialAnalysisPanel.vue` | 新增，使用 adapter/overview 数据。 |
| 搜索筛选工具栏 | `MaterialFilters.vue` | 替换当前搜索 + 状态 select。 |
| 条式素材表 | `MaterialTable.vue` | 替换当前卡片网格。 |
| 详情预览抽屉 | `MaterialDetailDrawer.vue` | 替换当前居中 modal。 |
| 上传弹窗 | `MaterialUploadModal.vue` | 从当前 `Material.vue` 抽出并增强。 |
| 编辑弹窗 | `MaterialEditModal.vue` | 新增。 |
| 删除确认 | `MaterialDeleteConfirm.vue` 或通用确认弹窗 | 新增。 |

`Material.vue` 保留职责：

- 登录兜底。
- 拉取素材列表和 overview。
- 管理筛选状态、选中素材、上传/编辑/删除弹窗开关。
- 把数据传给子组件。

### 前端预览承接规则

列表：

- 永远用 `<img>` 展示 `thumbnailUrl/posterUrl`。
- 视频素材只叠加播放图标，不 autoplay。
- `loading="lazy"`，固定缩略图尺寸，避免列表抖动。

详情抽屉：

- 图片：用 `previewUrl`，无则 `thumbnailUrl`，最后才 `originalUrl`。
- 视频：有 `previewUrl` 才渲染 `<video controls>`；否则展示 `posterUrl/thumbnailUrl` 和“视频预览处理中”。
- 原始素材放在“打开原文件/下载”按钮中请求。

上传后：

- 刷新列表后如果 `processing_status=processing`，显示处理中状态。
- 处理完成前不假装视频可播放。

### 设计稿字段映射

| 设计稿字段 | 当前可用来源 | MVP 策略 | 正式策略 |
|---|---|---|---|
| 素材名称/ID | `materials.name/id` | 直接展示 | 直接展示 |
| 缩略图 | `thumbnail_url` | OSS signed URL | 真 thumbnail/poster |
| 类型 | `type` + mime/url | adapter 判断 | `media_kind` |
| 来源 | 无 | 默认 `OSS 上传` | `source` 字段 |
| 创建时间 | `created_at` | 直接格式化 | 直接格式化 |
| 时长 | `duration` | 秒转 `00:ss` | 上传解析 |
| 平台 | 关联 campaigns.platform | 从 `campaign_ids` 推导 | `platforms_json` + 同步 |
| Campaign/计划 | 关联 campaigns.name | 从 `campaign_ids` 查 | 关联表或 JSON |
| 消耗/展示/点击 | metrics by campaign | 均摊估算或 0 | `material_metrics` |
| CTR/CVR/ROAS/CPC/CPA | metrics 计算 | 均摊估算或 0 | `material_metrics` 计算 |
| 评分 | 无 | 用 ctr_estimate 简单映射 | `score` 字段/算法 |
| 疲劳度 | `status=FATIGUE` | FATIGUE 给高值，否则低值 | `fatigue` 字段/算法 |
| 审核状态 | 无 | 由 status 映射 | `review_status` |
| 授权 | 无 | 默认 `自有素材` | `rights` |
| 版位 | 无 | 根据平台默认 | `placements_json` |

### 推荐执行顺序更新

1. 先补后端只读增强接口：`GET /materials?include_metrics=true`、preview variant、字段 adapter，不立刻做复杂转码。
2. 前端按设计稿拆组件并接真实接口，列表只用图片 thumbnail/poster。
3. 补 `PATCH`、archive、页面编辑/删除/批量操作。
4. 增加 Alembic 字段扩展，迁移旧 `url -> original_url/thumbnail_url`。
5. 增加 `material_metrics`，把当前 campaign metrics 的估算逻辑替换为真实素材指标。
6. 再做 thumbnail/poster/preview 生成服务和异步处理。

## 分阶段计划

### Phase 1：数据合约与页面骨架

目标：先把设计稿的页面结构落到现有素材数据上，保证 OSS 预览不回退。

前端修改：

- 新增素材 UI 类型：
  - `MaterialListItem`
  - `MaterialMetricSummary`
  - `MaterialAnalysisCard`
  - `MaterialFilterState`
- 在 `frontend/packages/main-app/src/api/materials.ts` 中扩展类型，但保持原 `Material` 兼容。
- 在 `Material.vue` 内或拆分到 `src/pages/creatives/materialsAdapter.ts`：
  - 把 backend `Material` 转成设计稿需要的列表项。
  - 对缺失字段给明确默认值，例如 `source = "OSS 上传"`、`ratio = "未知"`、`spend = 0`。
  - 计算 `previewUrl`，优先级为 `signed image url > thumbnail_url > url`。
- 重构 `Material.vue` 模板：
  - 顶部标题与操作按钮。
  - 周期指标区。
  - 智能分析区。
  - 筛选工具栏。
  - 条式素材表。
  - 右侧详情抽屉。

后端修改：

- 不强制改表。
- 确认 `/materials/{id}/image` 对 OSS URL 返回签名 URL。
- 保留当前 `/materials/upload` 创建素材记录流程。
- 增加或确认详情抽屉需要的最小管理动作：
  - 删除素材入口使用 `DELETE /materials/{id}`，前端必须有二次确认。
  - 编辑动作第一版可以只做前端入口和接口设计，不在 Phase 1 强制落库。

验收：

- `test@animagus.com` 能看到旧 DB 合并后的 8 个 OSS 素材。
- 列表缩略图和详情预览都指向可访问的 OSS 签名 URL。
- 上传新图片后能刷新进入条式列表，并能预览。

### Phase 2：素材元信息补齐

目标：让列表和详情字段从“默认值”升级为真实素材元数据。

后端修改：

- 新增 Alembic migration，给 `materials` 增加可空字段：
  - `format`
  - `width`
  - `height`
  - `ratio`
  - `source`
  - `creator`
  - `rights`
  - `platforms_json`
  - `review_status`
  - `source_account`
  - `placements_json`
  - `score`
  - `fatigue`
  - `last_used_at`
- 更新 `Material` model、repository `_to_dict()`、create/update 入参。
- 新增 `PATCH /materials/{id}`：
  - 可编辑 `name`、`status`、`tags`、`source`、`rights`、`platforms_json`、`review_status`、`source_account`、`placements_json`。
  - 禁止直接编辑 `user_id`、原始 `url` 所属权、系统生成字段。
  - 每次更新校验当前用户权限。
- 上传时解析文件基础信息：
  - 图片：宽高、比例、格式。
  - 视频：优先保存格式、大小、时长；宽高可以后续补。
- 删除语义调整：
  - 第一版建议把删除做成 `archived/deleted` 状态或 `deleted_at` 软删除。
  - 仅当素材没有被任何广告计划引用，且用户二次确认“删除源文件”时，才考虑删除 OSS 对象。

前端修改：

- adapter 从真实字段读取：
  - 类型、尺寸、比例、来源、平台、审核、版位、授权。
- 详情抽屉展示完整基础信息。
- 增加素材编辑弹窗：
  - 名称。
  - 标签。
  - 状态。
  - 来源。
  - 授权说明。
  - 平台和版位。
- 增加删除/归档交互：
  - 单个素材删除确认。
  - 已被项目或广告计划引用时提示影响范围。
  - 支持归档代替删除。

验收：

- 旧素材没有新字段时页面不崩。
- 新上传图片能显示宽高和比例。
- 筛选项来源、平台、比例能正常工作。
- 编辑素材后刷新页面字段仍保留。
- 删除或归档素材后列表、详情、筛选数量同步更新。

### Phase 2.5：预览资源处理

目标：把“能打开原素材”升级为“前端高性能预览”，避免列表和详情直接加载大图或原视频。

正常前端预览策略：

- 列表行缩略图：
  - 图片使用小尺寸 thumbnail，例如 320px 宽 WebP/JPEG。
  - 视频使用 poster 图片，不直接播放原视频。
- 详情预览：
  - 图片优先使用中等尺寸 preview，例如 1280px 内。
  - 视频优先使用低码率 MP4/HLS preview，例如 720p 或更低码率。
  - 用户点击“查看原文件/下载”时才请求原始 OSS URL。
- 上传完成后应生成并保存：
  - `thumbnail_url`
  - `preview_url`
  - `poster_url`
  - `original_url`
  - `transcode_status`
  - `processing_error`

后端修改：

- 扩展素材字段：
  - `original_url`
  - `preview_url`
  - `poster_url`
  - `thumbnail_url`
  - `transcode_status`
  - `processing_error`
- 修改 `/materials/{id}/image` 或新增 `/materials/{id}/preview`：
  - `variant=thumbnail|preview|original|poster`
  - 返回对应 OSS 签名 URL。
- 上传图片后生成 thumbnail/preview。
- 上传视频后生成 poster，视频转码可以先异步占位，MVP 可先只保存原视频和 poster。

前端修改：

- 列表只使用 `thumbnail_url` 或 `poster_url`。
- 详情优先使用 `preview_url`，没有时再回退 `original_url`。
- 视频未转码完成时展示 poster 和“处理中”状态。
- 对大文件不要在列表中使用 `<video src=original>`。

验收：

- 列表滚动时不批量加载原视频。
- 详情打开视频素材时优先请求 preview/poster，不直接请求大体积原文件。
- 缩略图缺失时有稳定 fallback，不出现破图或布局跳动。

### Phase 3：表现数据与智能分析

目标：让周期看板、排序、筛选和智能分析接近设计稿真实体验。

推荐后端接口：

- `GET /api/v1/materials/overview?period=7d|30d|90d&project_id=&campaign_id=`
  - 返回汇总指标：`spend`、`impressions`、`clicks`、`ctr`、`roas`、`cpc`。
- `GET /api/v1/materials?include_metrics=true&period=7d`
  - 每个素材返回当前周期表现字段。

数据来源策略：

- MVP：从现有 `metrics` 表或 campaign 维度数据做可解释聚合。
- 如果现有 metrics 无法按 material 归因，则新增 `material_metrics` 表：
  - `id`
  - `material_id`
  - `date`
  - `platform`
  - `spend`
  - `impressions`
  - `clicks`
  - `conversions`
  - `revenue`
  - `created_at`
- `ctr`、`cpc`、`cpa`、`roas` 由后端或前端统一计算。

前端修改：

- 周期切换触发重新拉取或重新计算。
- 指标排序支持：
  - 消耗最高
  - 展示最高
  - 点击最高
  - CTR 最高
  - 成本最低
  - 评分最高
  - 疲劳最高
  - 最近上传
- 智能分析基于当前筛选结果计算：
  - 优先放量素材。
  - 高消耗低 ROAS 预警。
  - 高疲劳素材预警。
  - 视频素材整体表现。

验收：

- 周期切换后看板、列表指标、分析卡片同步变化。
- 指标为空时显示 `-` 或 `暂无数据`，不显示 NaN。
- 排序和筛选结果数量一致。

### Phase 4：交互完善与工程化

目标：让页面达到可长期维护状态。

前端拆分建议：

- `frontend/packages/main-app/src/pages/creatives/Material.vue`
  - 页面容器和数据加载。
- `frontend/packages/main-app/src/pages/creatives/components/MaterialMetricsPanel.vue`
  - 周期看板。
- `frontend/packages/main-app/src/pages/creatives/components/MaterialAnalysisPanel.vue`
  - 智能分析。
- `frontend/packages/main-app/src/pages/creatives/components/MaterialFilters.vue`
  - 搜索和筛选。
- `frontend/packages/main-app/src/pages/creatives/components/MaterialTable.vue`
  - 条式列表。
- `frontend/packages/main-app/src/pages/creatives/components/MaterialDetailDrawer.vue`
  - 详情预览。
- `frontend/packages/main-app/src/pages/creatives/materialsAdapter.ts`
  - 数据转换和指标计算。

交互补齐：

- 复制素材 ID。
- 加入待投放。
- CSV 导出。
- 编辑素材信息。
- 删除/归档素材。
- 批量选择、批量归档、批量打标签。
- 绑定/解绑项目和广告计划。
- 平台审核同步按钮先接 mock toast，后续接真实平台状态。
- 移动端详情抽屉全屏化。

验收：

- `npm_config_cache=./npm_cache npm --prefix frontend/packages/main-app run build`
- 浏览器检查素材页无控制台错误。
- 桌面宽屏和移动视口下表格、抽屉、按钮不重叠。

## 推荐实施顺序

1. 先做 Phase 1：只改前端结构和 adapter，不动 DB schema。
2. 确认 OSS URL 预览链路稳定。
3. 再做 Phase 2：补素材元信息字段和上传解析。
4. 最后做 Phase 3：接入表现指标和智能分析。

原因：

- 当前最影响体验的是素材页结构和预览链路，不是复杂指标归因。
- OSS 上传/预览已经有可用基础，应该优先保留并复用。
- 设计稿很多表现数据当前 DB 没有，直接硬改页面会产生大量假数据。
- 分阶段做可以每一步都有可验证产物。

## 关键文件清单

前端：

- `frontend/packages/main-app/src/pages/creatives/Material.vue`
- `frontend/packages/main-app/src/api/materials.ts`
- `frontend/packages/main-app/src/pages/creatives/materialsAdapter.ts`
- `frontend/packages/main-app/src/pages/creatives/components/MaterialMetricsPanel.vue`
- `frontend/packages/main-app/src/pages/creatives/components/MaterialAnalysisPanel.vue`
- `frontend/packages/main-app/src/pages/creatives/components/MaterialFilters.vue`
- `frontend/packages/main-app/src/pages/creatives/components/MaterialTable.vue`
- `frontend/packages/main-app/src/pages/creatives/components/MaterialDetailDrawer.vue`

后端：

- `backend/app/api/v1/materials.py`
- `backend/app/models/material.py`
- `backend/app/repositories/impl/sqlite_material_repo.py`
- `backend/app/repositories/protocols.py`
- `backend/alembic/versions/*_add_material_metadata_fields.py`
- `backend/app/services/object_storage.py`
- `backend/app/services/material_preview_service.py`

测试和校验：

- `frontend/packages/main-app` build。
- `backend` Python compile。
- `/api/v1/materials` API smoke test。
- `/api/v1/materials/{id}/image?thumbnail=true` OSS signed URL smoke test。
- `PATCH /api/v1/materials/{id}` 编辑 smoke test。
- `DELETE /api/v1/materials/{id}` 删除/归档 smoke test。
- thumbnail/preview/original 三种素材 URL 签名 smoke test。
- 浏览器手工检查素材页。

## 风险与注意事项

- 设计稿里的表现数据目前不完全存在于 `materials` 表，不能只靠前端样式实现真实评估。
- 如果要按素材维度统计 ROAS/CPC/CPA，需要明确投放数据如何关联到 material。
- OSS 预览应以 backend 签名 URL 为准，前端不要直接拼 OSS 私有对象地址，也不要在列表直接加载原视频。
- 硬删除素材可能破坏历史投放记录和广告计划引用，默认建议软删除/归档。
- 视频转码、poster、thumbnail 生成如果走同步流程，会拖慢上传接口，建议异步处理或 MVP 先只生成轻量 poster。
- 当前工作区已有未提交 DB、alembic、start-dev、materials API 相关变更，正式开发前建议先确认是否全部属于当前分支目标。
- 如果当前 dev 服务仍持有旧的 deleted sqlite fd，需要重启服务后再做最终验收，否则浏览器看到的数据可能和磁盘 DB 不一致。
