# Workspace 顶栏与数据概览细节优化设计

日期：2026-08-14
分支：`cc_uxui_v2`
已确认方向：A · 57px 紧凑统一

## 目标

统一 workspace 业务页面的一级顶部导航高度，并精简 Dashboard 与 Projects 的顶部信息层级。Dashboard 图表需要使用更细的线条和更小的真实圆点；平台卡片等高；数据源提示条移除。Projects 的搜索与状态筛选合并进一级顶部导航，不再独占第二行。

完成标准：

1. 14 个具有一级页面顶栏的 workspace 页面，其顶栏在桌面和窄屏均为 57px；Home 维持现有无一级顶栏布局，不新增空白条。
2. 公共登录、注册、起始页与法律页面的 `AppHeader` 不改变。
3. Dashboard 三个筛选器不再显示“时间范围 / 平台 / 项目”小字，但保留现有 `aria-label`、双向绑定与 change 逻辑。
4. Dashboard 的数据源/更新时间/Report Monitor 区块完全移除。
5. Dashboard 图表常态与 hover 圆点保持真圆形，线条与描边减细。
6. Meta、Google、TikTok 三个平台卡片等高，不再由 Google 独有洞察条向下凸出。
7. Projects 搜索框和“全部项目”筛选位于 57px 顶栏内；搜索、筛选、视图切换、创建按钮逻辑保持不变。
8. 不修改侧栏 Logo、侧栏 57px 品牌区、侧栏颜色/阴影、业务数据请求、弹窗、表格、抽屉、状态色或暗色行为。

## 范围

### Workspace 顶栏契约

在 `global.css` 中新增：

```css
:root {
  --workspace-page-header-height: 57px;
}

.workspace-page-header {
  box-sizing: border-box;
  height: var(--workspace-page-header-height);
  min-height: var(--workspace-page-header-height);
  flex: 0 0 var(--workspace-page-header-height);
}
```

`workspace-page-header` 只添加到 workspace 页面真正的一级顶栏，禁止使用 `.workspace-page-canvas header` 等泛选择器。以下页面纳入：

- Dashboard
- Projects
- ProjectDetail
- Campaign
- CampaignDetail
- CreateCampaign
- CreateAdUnit
- Material
- Monitor
- Settings
- AccountConfig
- AIUsageConfig
- PlatformConnections
- SystemAdmin

Home 是唯一例外，因为当前首页直接进入对话/文档画布，没有一级页面顶栏。

AccountConfig、AIUsageConfig、PlatformConnections 共用 `settings-notion.css` 的 `.sn-page-head`，该规则改为 57px；其余页面在真实一级顶栏上添加共享类，并移除会覆盖 57px 的局部 `h-*` / `min-height` 声明。

Dashboard 的 embedded 模式属于 Home 内嵌工作台，不应用固定 57px。Dashboard 顶栏使用条件类：仅独立路由添加 `workspace-page-header`，embedded 布局继续使用现有纵向结构。

## Dashboard 设计

### 顶栏

- 独立 Dashboard 顶栏固定 57px，与侧栏 Logo 区下沿对齐。
- 保留标题、图标、副标题、三个 select 和刷新按钮。
- 删除三个 `<label>` 的可见文字，仅保留 select 的 `aria-label`。
- `.filter-field` 改为单行容器；刷新按钮取消 `align-self: end`。
- 桌面控件保持 31px 高；窄屏不换行、不增高。空间不足时按顺序隐藏副标题、刷新文字和标题文字，但保留控件及可访问名称。
- embedded Dashboard 不套用固定高度，避免破坏 Home 右侧工作台。

### 数据源条

删除整个 `section.data-note` 及只为它服务的 `.data-note` 样式。保留 `.quiet-badge`，因为分群列表仍使用它。

### 趋势图

采用以下确定值：

- SVG：`preserveAspectRatio="xMidYMid meet"`，避免非等比缩放把 circle 拉成椭圆。
- 蓝线：`stroke-width="1.4"`。
- 橙线：`stroke-width="1.35"`。
- 常态圆点：`r="2.1"`，白色描边 `stroke-width="1"`。
- hover 圆点：`r="3.5"`，描边 `1.5`。
- hover 竖线：`stroke-width: .75`。
- hover 柱轮廓：宽 20、圆角 3、描边 1.2。
- 图例圆点：5px × 5px。
- 保持命中区域、键盘焦点、tooltip 数据和点击选择逻辑不变。

### 平台卡片等高

Google 独有的 `insight` / `insightValue` 和条件渲染 `.platform-insight` 被移除，三张卡片使用完全相同的内容结构。`.platform-grid` 与 `.platform-card` 改为 stretch 契约，防止未来单卡内容差异再次造成外框高度不齐。

不调整平台指标、每日数据表、健康度、颜色或交互。

## Projects 设计

将现有 `.projects-toolbar` 的搜索框和状态筛选原样移入 `.projects-page-bar`，形成单行结构：

```text
[图标 + 项目管理] [搜索项目……] [全部项目] [视图切换] [创建项目]
```

具体规则：

- `.projects-page-bar` 添加 `workspace-page-header`，不再拥有独立高度值。
- `.projects-toolbar` 保留为顶栏内部逻辑容器，但移除独立背景、底线、外层上下 padding。
- 搜索框和筛选器由 36px 收紧为 34px。
- `v-model="searchQuery"`、`v-model="filterStatus"`、`handleSearch`、placeholder 和 aria-label 全部保留。
- 标题栏之后不再存在第二个 toolbar 行。
- 窄屏保持单行：先隐藏副标题，再隐藏视图切换与创建按钮文字；极窄宽度隐藏状态筛选，但保留搜索和创建图标。不得通过换行增加顶栏高度。

## 响应式与无障碍

- 57px 是所有独立 workspace 一级顶栏的硬高度契约。
- 顶栏内部使用 `min-width: 0`、受控 shrink 和必要的 overflow 处理，不允许 header 自身换行。
- 所有被隐藏的文字必须由现有或新增 `aria-label` 继续表达。
- Home 不增加顶栏；embedded Dashboard 不强制 57px。
- 公共 `AppHeader`、侧栏品牌区、Logo 文件及尺寸完全不修改。

## 测试与验证

新增源码契约测试 `workspace-page-header.test.ts`：

1. 全局 token 和 `.workspace-page-header` 同时锁定 height、min-height、flex-basis。
2. 路由清单锁定 14 个真实一级顶栏，Home 明确为唯一例外。
3. Dashboard 独立模式使用共享类，embedded 模式不强制共享类。
4. Dashboard 不再存在三个可见筛选小字和 `data-note`，但 select 的 `aria-label`、v-model 和 change handler 保留。
5. 图表锁定 SVG 等比策略、线宽、常态/hover 点尺寸和细描边。
6. 平台卡片不再包含 insight DOM，且使用 stretch 高度契约。
7. Projects 搜索/筛选位于 `.projects-page-bar` 内，不再形成页面级第二行；绑定与无障碍属性保持。
8. 继续运行 WorkspaceShell、AppHeader、AccountControls 与 workspace canvas 套件，确认公共顶栏、Logo、侧栏和画布契约不回归。

浏览器验证：

- 逐路由验证 14 个一级顶栏 `getBoundingClientRect().height === 57`。
- `/home` 无空白顶栏；Dashboard embedded 未被压成 57px。
- Dashboard 图表常态和 hover 圆点为圆形；线宽与预览一致。
- 三个平台卡片外框等高。
- Projects 顶栏为单行且搜索/筛选可用。
- 390px 窄屏无 header 换行或横向页面溢出。
- 控制台无本次新增 error。

## 明确不做

- 不重构为新的通用 Header Vue 组件。
- 不改变 Home 布局。
- 不修改公共 AppHeader 或侧栏。
- 不改业务 API、过滤逻辑、平台数据、KPI、tooltip 内容或项目操作。
- 不顺带修复既有 `HomeLandingLayout.spec.ts` padding 旧断言。
