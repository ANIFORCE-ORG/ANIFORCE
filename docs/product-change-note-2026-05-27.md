# 产品变更纪要：主流程合并与本地测试闭环

更新时间：2026-05-27

## 1. 用户反馈

1. 项目创建无法完成提交提示，本地测试需要完整接口服务或可完整走通的本地闭环。
2. 一级菜单中的“数据概览”和“数据复盘/数据报表”需要合并成同一套数据复盘能力，但保留两个入口。
3. “项目管理”和“广告计划/广告投放”需要合并，先有项目，项目下才有计划。
4. 创建投放项目应与新手引导的核心创建流程合并，形成完整的广告计划创建路径。

## 2. 与 05-26 会议纪要对齐

不冲突。

会议纪要已明确：

- “数据概览”合并为单一数据报表，强化时间区间筛选、周期趋势与实时/夜间数据。
- 项目管理与广告投放两个入口建议合并。
- 0.5 版本优先跑通单条广告创建全流程。
- Project/Campaign/Ad Set/Ad 层级需要重梳，先保证最小单元可跑通。
- 新手引导应串联项目、平台授权、广告账户绑定、创建第一条计划。

## 3. 本次前端修改原则

- 本地测试必须能在后端接口不可用时完整走通 Demo fallback。
- 不删除入口，先把入口指向统一核心页面，降低用户认知成本。
- “项目”作为广告计划上层容器；广告计划创建必须从项目上下文进入。
- `/home` 新手引导暂不做复杂弹窗，但创建项目、平台账户、创建计划的核心流程要与项目工作台保持一致。

## 4. 需要后端/API 协同

### Project

- `POST /projects` 必须可在本地认证环境下稳定创建。
- 当前前端临时 fallback 会生成 `demo-project-*`，用于本地测试，不替代真实接口。

### Campaign Draft

- `POST /campaign-drafts`
- `PATCH /campaign-drafts/:id`
- `POST /campaign-drafts/:id/submit`

当前前端仍使用 `POST /campaigns` 作为 fallback，并在 `config` 中传 Campaign / Ad Group / Creative 结构。

### Reports

- `GET /reports/overview?range=&platform=&project_id=`
- `GET /reports/timeseries?range=&platform=&project_id=`
- `GET /reports/platforms?range=&project_id=`
- `GET /reports/insights?range=&project_id=`

报表需要支持时间段、平台、项目维度，并返回趋势数据用于折线图。

## 5. 待继续确认

1. 一级菜单是否显示两个入口但同页：`数据概览` 和 `数据复盘` 都到 `/monitor`。
2. 一级菜单是否显示两个入口但同页：`项目管理` 和 `广告计划` 都到 `/projects`。
3. `/campaign` 是否保留为兼容路由并自动跳转 `/projects`。
4. `/dashboard` 是否保留为兼容路由并自动跳转 `/monitor`。
