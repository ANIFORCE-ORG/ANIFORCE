# Block 11 剧本回放原型（固定资产）

> 本文件是前端设计阶段的静态原型存档，用于后续真实前后端串联时对照设计意图。

## 来源

- 源码：[`block11_playback_prototype.vue`](./block11_playback_prototype.vue)（1000 行，Vue 3 + Tailwind）
- 数据来源：`aniforce-agent/logs/block11_long_task_260618.log`（Block 11 真实执行轨迹，10 幕）
- 设计基线：对齐主站设计语言（`#137fec` primary、Inter、Material Symbols、slate 中性、`rounded-md`）

## 这个原型解决了什么

把后端 Block 11 验证过的 10 幕长程任务流程（创建项目 → 建计划 → AI 生图 → 建文案 → 发起投放 → 模拟 7 天 → 取数据 → 对比分析 → 预算调整 → 总结），用纯前端 mock 常量驱动，可视化呈现 Agent 的真实执行轨迹。

## 设计要点（真实串联时必须保留）

1. **工具卡不堆叠**：一幕 = 一条 Agent 消息 + 可折叠 trace（默认收起 `N 步 · N 审批 · N 工具 ✓`，展开是细线时间线）。主信息是 Agent 文本，工具过程是辅助层。
2. **stat chips**：Chat header 右侧 `↑input  ↓output  $cost`（cost≥$0.01 高亮），运行中实时显示 `tok/s` 和 phase 文案。
3. **step pip 进度**：10 段细条，已完成满色 / 当前半透明 / 未来灰。
4. **HITL inline 徽标**：单行 `✓ 标题 · 详情`，不是大块卡。真实串联时需改成可点确认的弹窗（原型里是已批准静态态）。
5. **Workspace = SaaS 投影**：项目卡照抄 `ProjectDetail.vue`、素材网格照抄 `Material.vue`、指标卡照抄 `Monitor.vue` 结构，视觉 1:1。
6. **数字 mono + tabular-nums**：预算/ROI/CTR/CPC/CPA 全用 `font-mono`。
7. **状态色减负**：1px 边框 + 字色，不用大块彩色背景。

## 如何重新挂载查看

需要对照时，临时挂回路由：

```ts
// router/index.ts
{
  path: '/prototype/block11',
  name: 'prototype-block11',
  component: () => import('@/pages/prototype/Block11Playback.vue')
}
```

将 `docs/design/block11_playback_prototype.vue` 复制到 `frontend/packages/main-app/src/pages/prototype/Block11Playback.vue` 即可。

## 状态

- ✅ 设计已定稿（2026-06-18）
- ⏭️ Home.vue 已转为真实后端串联开发，此原型仅作对照资产保留
