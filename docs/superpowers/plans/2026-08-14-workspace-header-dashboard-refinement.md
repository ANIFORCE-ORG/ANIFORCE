# Workspace Header and Dashboard Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify all independent workspace page headers at 57px, refine Dashboard chart/card/header details, and move Projects search/filter controls into its primary header.

**Architecture:** Add one global, opt-in workspace header token/class and mark only the real first-level page headers. Keep Home and embedded Dashboard as explicit exceptions. Protect the contract with source-level Vitest tests, then verify actual geometry and responsive behavior in the local browser.

**Tech Stack:** Vue 3 SFCs, TypeScript, Tailwind utility classes, scoped CSS, Vitest, Vite, pnpm.

---

## Baseline and execution context

- Repository: `/Users/chenhui/Documents/Codex/2026-07-28/awesome-design-md-skill-notion-html/ANIFORCE-cc_uxui_v2-frontend`
- Branch: `cc_uxui_v2`
- Frontend workspace: `frontend/`
- Local preview: `http://127.0.0.1:3010`
- The checkout is already separate from the original `cc_uxui` checkout; do not create or switch to another branch.
- Preserve untracked `.superpowers/` preview files and never stage them.
- Known pre-existing full-suite failure: `src/pages/HomeLandingLayout.spec.ts` expects the old `clamp(154px, ...)` padding while `Home.vue` contains the previously approved `clamp(260px, 38vh, 720px)`. Do not modify either file for this work.

## File map

### New test contract

- Create: `frontend/packages/main-app/src/styles/workspace-page-header.test.ts`
  - Owns the 57px global header contract, exact first-level header markers, Dashboard refinement assertions, and Projects header integration assertions.

### Shared contract and 12 non-Dashboard/Projects pages

- Modify: `frontend/packages/main-app/src/styles/global.css`
- Modify: `frontend/packages/main-app/src/pages/projects/ProjectDetail.vue`
- Modify: `frontend/packages/main-app/src/pages/campaigns/Campaign.vue`
- Modify: `frontend/packages/main-app/src/pages/campaigns/CampaignDetail.vue`
- Modify: `frontend/packages/main-app/src/pages/campaigns/CreateCampaign.vue`
- Modify: `frontend/packages/main-app/src/pages/campaigns/CreateAdUnit.vue`
- Modify: `frontend/packages/main-app/src/pages/creatives/Material.vue`
- Modify: `frontend/packages/main-app/src/pages/Monitor.vue`
- Modify: `frontend/packages/main-app/src/pages/settings/Settings.vue`
- Modify: `frontend/packages/main-app/src/pages/settings/AccountConfig.vue`
- Modify: `frontend/packages/main-app/src/pages/settings/AIUsageConfig.vue`
- Modify: `frontend/packages/main-app/src/pages/settings/PlatformConnections.vue`
- Modify: `frontend/packages/main-app/src/pages/system/SystemAdmin.vue`
- Modify: `frontend/packages/main-app/src/styles/settings-notion.css`

### Dashboard

- Modify: `frontend/packages/main-app/src/pages/Dashboard.vue`
- Modify test: `frontend/packages/main-app/src/styles/workspace-page-header.test.ts`

### Projects

- Modify: `frontend/packages/main-app/src/pages/projects/Projects.vue`
- Modify test: `frontend/packages/main-app/src/styles/workspace-page-header.test.ts`

---

### Task 1: Establish the shared 57px header contract on 12 pages

**Files:**

- Create: `frontend/packages/main-app/src/styles/workspace-page-header.test.ts`
- Modify: `frontend/packages/main-app/src/styles/global.css`
- Modify the 12 page files and `settings-notion.css` listed in the file map above.

- [ ] **Step 1: Write the failing shared contract test**

Create `workspace-page-header.test.ts` with these helpers and cases:

```ts
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const readSource = (relativePath: string) =>
  readFileSync(fileURLToPath(new URL(relativePath, import.meta.url)), 'utf8')

const templateSource = (source: string) => {
  const match = source.match(/<template>([\s\S]*?)<\/template>/)
  expect(match, 'expected a Vue <template>').not.toBeNull()
  return match?.[1] ?? ''
}

const workspaceHeaderTag = (source: string) => {
  const template = templateSource(source)
  const matches = [...template.matchAll(/<([a-z][\w-]*)\b[^>]*\sdata-workspace-page-header(?:="")?[^>]*>/gi)]
  expect(matches, 'expected exactly one first-level workspace page header marker').toHaveLength(1)
  return matches[0][0]
}

const staticClassTokens = (openingTag: string) => {
  const match = openingTag.match(/(?:^|\s)class="([^"]*)"/)
  return new Set((match?.[1] ?? '').split(/\s+/).filter(Boolean))
}

const sharedHeaderPages = [
  '../pages/projects/ProjectDetail.vue',
  '../pages/campaigns/Campaign.vue',
  '../pages/campaigns/CampaignDetail.vue',
  '../pages/campaigns/CreateCampaign.vue',
  '../pages/campaigns/CreateAdUnit.vue',
  '../pages/creatives/Material.vue',
  '../pages/Monitor.vue',
  '../pages/settings/Settings.vue',
  '../pages/settings/AccountConfig.vue',
  '../pages/settings/AIUsageConfig.vue',
  '../pages/settings/PlatformConnections.vue',
  '../pages/system/SystemAdmin.vue',
] as const

describe('workspace page header contract', () => {
  it('defines one opt-in 57px workspace page header token', () => {
    const globalSource = readSource('./global.css')
    expect(globalSource).toContain('--workspace-page-header-height: 57px;')
    expect(globalSource).toMatch(/\.workspace-page-header\s*\{[\s\S]*?height:\s*var\(--workspace-page-header-height\);[\s\S]*?min-height:\s*var\(--workspace-page-header-height\);[\s\S]*?flex:\s*0 0 var\(--workspace-page-header-height\);[\s\S]*?\}/)
  })

  it.each(sharedHeaderPages)('%s marks exactly one real first-level header', path => {
    const tag = workspaceHeaderTag(readSource(path))
    const tokens = staticClassTokens(tag)
    expect(tokens).toContain('workspace-page-header')
    expect([...tokens].some(token => /^(?:h|min-h)-\[\d+px\]$/.test(token))).toBe(false)
  })

  it('removes local min-height rules that would override the shared contract', () => {
    expect(readSource('../pages/projects/ProjectDetail.vue')).not.toMatch(/\.detail-page-bar\s*\{[^}]*min-height:/)
    expect(readSource('../pages/settings/Settings.vue')).not.toMatch(/\.settings-page-head\s*\{[^}]*min-height:/)
    expect(readSource('./settings-notion.css')).not.toMatch(/\.sn-page-head\s*\{[^}]*min-height:/)
  })

  it('keeps Home as the only route without an injected page header', () => {
    expect(readSource('../pages/Home.vue')).not.toContain('data-workspace-page-header')
    expect(readSource('../pages/Home.vue')).not.toContain('workspace-page-header')
  })
})
```

- [ ] **Step 2: Run the focused test and verify RED**

Run from `frontend/`:

```bash
pnpm --filter main-app test src/styles/workspace-page-header.test.ts
```

Expected: FAIL because the global token/class and page markers do not exist.

- [ ] **Step 3: Add the global opt-in contract**

In `global.css`, add to `:root`:

```css
--workspace-page-header-height: 57px;
```

Add next to `.workspace-page-canvas`:

```css
.workspace-page-header {
  box-sizing: border-box;
  height: var(--workspace-page-header-height);
  min-height: var(--workspace-page-header-height);
  flex: 0 0 var(--workspace-page-header-height);
}
```

- [ ] **Step 4: Mark the 12 real first-level headers and remove local height overrides**

Use exactly one `data-workspace-page-header` marker per page and add the static `workspace-page-header` class to the same element.

| File | Target | Required change |
|---|---|---|
| `ProjectDetail.vue` | `<header class="detail-page-bar">` | Add marker/class; remove `.detail-page-bar { min-height: 54px; }`. |
| `Campaign.vue` | first main header `<div class="h-[50px] ...">` | Add marker/class; remove `h-[50px]`. |
| `CampaignDetail.vue` | first main header `<div class="h-[50px] ...">` | Add marker/class; remove `h-[50px]`. |
| `CreateCampaign.vue` | outer white header before Steps Navigation | Add marker/class. Change inner wrapper to `max-w-7xl mx-auto flex h-full items-center px-[19px]`, removing `py-[12px]`. Do not mark Steps Navigation. |
| `CreateAdUnit.vue` | first main header `<div class="h-[50px] ...">` | Add marker/class; remove `h-[50px]`. |
| `Material.vue` | first-level `<header class="... min-h-[54px] ...">` | Add marker/class; remove `min-h-[54px]`. |
| `Monitor.vue` | first main header `<div class="flex h-[58px] ...">` | Add marker/class; remove `h-[58px]`. |
| `Settings.vue` | `<header class="settings-page-head">` | Add marker/class; remove scoped `min-height: 54px`. |
| `AccountConfig.vue` | `<header class="sn-page-head">` | Add marker/class. |
| `AIUsageConfig.vue` | `<header class="sn-page-head">` | Add marker/class. |
| `PlatformConnections.vue` | `<header class="sn-page-head">` | Add marker/class. |
| `SystemAdmin.vue` | first main header `<div class="... min-h-[54px] ...">` | Add marker/class; remove `min-h-[54px]`. |

In `settings-notion.css`, remove `min-height: 72px` and `flex: 0 0 auto` from `.sn-page-head`; keep its alignment, gap, padding, border, typography, and backgrounds unchanged.

- [ ] **Step 5: Run focused and existing layout tests**

```bash
pnpm --filter main-app test src/styles/workspace-page-header.test.ts src/styles/workspace-canvas.test.ts src/components/layout/WorkspaceShell.spec.ts src/components/layout/AppHeader.spec.ts src/components/layout/AccountControls.spec.ts
```

Expected: all selected files pass.

- [ ] **Step 6: Check scope and commit**

```bash
git diff --check
git status --short
git add frontend/packages/main-app/src/styles/workspace-page-header.test.ts frontend/packages/main-app/src/styles/global.css frontend/packages/main-app/src/pages/projects/ProjectDetail.vue frontend/packages/main-app/src/pages/campaigns/Campaign.vue frontend/packages/main-app/src/pages/campaigns/CampaignDetail.vue frontend/packages/main-app/src/pages/campaigns/CreateCampaign.vue frontend/packages/main-app/src/pages/campaigns/CreateAdUnit.vue frontend/packages/main-app/src/pages/creatives/Material.vue frontend/packages/main-app/src/pages/Monitor.vue frontend/packages/main-app/src/pages/settings/Settings.vue frontend/packages/main-app/src/pages/settings/AccountConfig.vue frontend/packages/main-app/src/pages/settings/AIUsageConfig.vue frontend/packages/main-app/src/pages/settings/PlatformConnections.vue frontend/packages/main-app/src/pages/system/SystemAdmin.vue frontend/packages/main-app/src/styles/settings-notion.css
git commit -m "style: unify workspace page header height"
```

---

### Task 2: Refine Dashboard header, chart, source note, and platform cards

**Files:**

- Modify: `frontend/packages/main-app/src/pages/Dashboard.vue`
- Modify: `frontend/packages/main-app/src/styles/workspace-page-header.test.ts`

- [ ] **Step 1: Add failing Dashboard contract tests**

Append these cases inside the existing describe block, using `workspaceHeaderTag` and `staticClassTokens` from Task 1:

```ts
it('applies the shared header only to standalone Dashboard mode', () => {
  const source = readSource('../pages/Dashboard.vue')
  const tag = workspaceHeaderTag(source)
  const tokens = staticClassTokens(tag)
  expect(tokens).toContain('page-bar')
  expect(tokens).toContain('replay-bar')
  expect(tag).toContain(`:class="{ 'workspace-page-header': !props.embedded }"`)
})

it('removes visible filter captions while preserving Dashboard controls', () => {
  const source = readSource('../pages/Dashboard.vue')
  expect(source).not.toMatch(/<label class="filter-field">\s*(时间范围|平台|项目)\s*<select/)
  for (const [model, label, handler] of [
    ['period', '时间范围', 'changePeriod'],
    ['platform', '平台', 'changePlatform'],
    ['project', '项目', 'changeProject'],
  ]) {
    expect(source).toContain(`v-model="${model}"`)
    expect(source).toContain(`aria-label="${label}"`)
    expect(source).toContain(`@change="${handler}"`)
  }
})

it('removes the Dashboard data source note and its dead update state', () => {
  const source = readSource('../pages/Dashboard.vue')
  expect(source).not.toContain('class="data-note"')
  expect(source).not.toContain('ANIFORCE Demo 数据集')
  expect(source).not.toContain('updatedText')
  expect(source).not.toMatch(/\.data-note\s*\{/)
})

it('uses thin lines and true circular Dashboard markers', () => {
  const source = readSource('../pages/Dashboard.vue')
  expect(source).toContain('preserveAspectRatio="xMidYMid meet"')
  expect(source).toContain('stroke="#4f8fe8" stroke-width="1.4"')
  expect(source).toContain('stroke="#dd7d00" stroke-width="1.35"')
  expect(source).toContain('stroke-width="1"><circle cx="91" cy="106" r="2.1"')
  expect(source).toContain('class="spend" :cx="activeTrendPoint.x" :cy="activeTrendPoint.spendY" r="3.5"')
  expect(source).toContain(':x="activeTrendPoint.x - 10"')
  expect(source).toContain('width="20"')
  expect(source).toContain('rx="3"')
  expect(source).toMatch(/\.legend-dot\s*\{\s*width:\s*5px;\s*height:\s*5px;/)
  expect(source).toMatch(/\.chart-active-markers line\s*\{[^}]*stroke-width:\s*\.75;/)
  expect(source).toMatch(/\.chart-active-markers rect\s*\{[^}]*stroke-width:\s*1\.2;/)
  expect(source).toMatch(/\.chart-active-markers circle\s*\{[^}]*stroke-width:\s*1\.5;/)
})

it('keeps the three platform cards structurally equal', () => {
  const source = readSource('../pages/Dashboard.vue')
  expect(source).not.toContain('insight:')
  expect(source).not.toContain('insightValue')
  expect(source).not.toContain('class="platform-insight"')
  expect(source).not.toMatch(/\.platform-insight\s*\{/)
  expect(source).toMatch(/\.platform-grid\s*\{[^}]*align-items:\s*stretch;/)
  expect(source).toMatch(/\.platform-card\s*\{[^}]*align-self:\s*stretch;/)
})
```

- [ ] **Step 2: Run the Dashboard-focused test and verify RED**

```bash
pnpm --filter main-app test src/styles/workspace-page-header.test.ts
```

Expected: Dashboard cases fail for missing marker, visible labels/data note, old SVG sizes, and unequal card structure.

- [ ] **Step 3: Implement the standalone 57px Dashboard header**

Change the header opening tag to:

```vue
<header
  class="page-bar replay-bar"
  data-workspace-page-header
  :class="{ 'workspace-page-header': !props.embedded }"
>
```

Remove the visible text nodes from each `.filter-field` label, keeping select bindings and accessibility attributes unchanged. Wrap the refresh text in `<span class="refresh-label">刷新</span>` so narrow screens can hide only the text.

Remove `.replay-bar { min-height: 64px; }`, change `.filter-field` to a one-line flex container, and remove `align-self: end` from `.refresh-button`.

Replace the current `@media (max-width: 900px)` header stacking rule with a single-row rule that hides `.replay-title p`, allows `.replay-actions` to shrink/scroll internally, and never changes header height. At `max-width: 620px`, hide `.replay-title h1`, make `.refresh-button` 31px square, and hide `.refresh-label`. Preserve the existing embedded selectors, which may remain vertical.

- [ ] **Step 4: Remove the data source note and dead state**

Delete:

- `const updatedText = ref(...)`
- all assignments to `updatedText.value`
- the entire `<section class="data-note">`
- `.data-note` and `.data-note strong` CSS

Do not delete `.quiet-badge` because segment rows still use it.

- [ ] **Step 5: Apply the confirmed chart dimensions**

Use these exact production values:

```vue
<svg viewBox="60 24 830 138" preserveAspectRatio="xMidYMid meet" ...>
...
<path ... stroke="#4f8fe8" stroke-width="1.4" />
<path ... stroke="#dd7d00" stroke-width="1.35" />
<g ... stroke-width="1"><circle ... r="2.1" />...</g>
...
<rect :x="activeTrendPoint.x - 10" ... width="20" ... rx="3" />
<circle class="spend" ... r="3.5" />
<circle class="roas" ... r="3.5" />
```

CSS:

```css
.legend-dot { width: 5px; height: 5px; border-radius: 50%; }
.chart-active-markers line { stroke-width: .75; }
.chart-active-markers rect { stroke-width: 1.2; }
.chart-active-markers circle { stroke-width: 1.5; }
```

Keep hit areas, keyboard handling, tooltip values, points, bars, and axes unchanged.

- [ ] **Step 6: Equalize platform cards**

Remove `insight` and `insightValue` from the Google object, remove the conditional `.platform-insight` DOM, and remove all `.platform-insight` CSS including responsive references.

Change:

```css
.platform-grid { align-items: stretch; }
.platform-card { align-self: stretch; }
```

Do not change card metrics, tables, colors, health gauges, or platform data.

- [ ] **Step 7: Run tests and commit**

```bash
pnpm --filter main-app test src/styles/workspace-page-header.test.ts src/styles/workspace-canvas.test.ts src/components/layout/WorkspaceShell.spec.ts src/components/layout/AppHeader.spec.ts src/components/layout/AccountControls.spec.ts
git diff --check
git add frontend/packages/main-app/src/pages/Dashboard.vue frontend/packages/main-app/src/styles/workspace-page-header.test.ts
git commit -m "style: refine dashboard header and chart"
```

---

### Task 3: Integrate Projects search and filter into the 57px header

**Files:**

- Modify: `frontend/packages/main-app/src/pages/projects/Projects.vue`
- Modify: `frontend/packages/main-app/src/styles/workspace-page-header.test.ts`

- [ ] **Step 1: Add failing Projects integration tests**

Append:

```ts
it('places Projects search and filter inside the primary workspace header', () => {
  const source = readSource('../pages/projects/Projects.vue')
  const template = templateSource(source)
  const headerMatch = template.match(/<header\b[^>]*data-workspace-page-header[^>]*>([\s\S]*?)<\/header>/)
  expect(headerMatch).not.toBeNull()
  const header = headerMatch?.[0] ?? ''
  expect(staticClassTokens(header)).toContain('workspace-page-header')
  expect(header).toContain('class="projects-toolbar"')
  expect(header).toContain('v-model="searchQuery"')
  expect(header).toContain('aria-label="搜索项目名称或标签"')
  expect(header).toContain('v-model="filterStatus"')
  expect(header).toContain('aria-label="按项目状态筛选"')
  expect((template.match(/class="projects-toolbar"/g) ?? [])).toHaveLength(1)
})

it('keeps the Projects header fixed to one row at narrow widths', () => {
  const source = readSource('../pages/projects/Projects.vue')
  expect(source).not.toMatch(/\.projects-page-bar\s*\{[^}]*min-height:/)
  expect(source).not.toMatch(/@media \(max-width: 520px\)[\s\S]*?\.projects-page-bar\s*\{[^}]*min-height:/)
  expect(source).toMatch(/\.projects-toolbar\s*\{[^}]*padding:\s*0;/)
  expect(source).toMatch(/\.projects-toolbar\s*\{[^}]*background:\s*transparent;/)
  expect(source).toMatch(/\.projects-toolbar\s*\{[^}]*border:\s*0;/)
})

it('preserves Projects filtering and actions', () => {
  const source = readSource('../pages/projects/Projects.vue')
  expect(source).toContain("p.name.toLowerCase().includes(query)")
  expect(source).toContain("p.tags.some(tag => tag.toLowerCase().includes(query))")
  expect(source).toContain("filterStatus.value !== 'all'")
  expect(source).toContain('@input="handleSearch"')
  expect(source).toContain('@change="handleSearch"')
  expect(source).toContain('@click="handleCreateProject"')
})
```

- [ ] **Step 2: Run focused test and verify RED**

```bash
pnpm --filter main-app test src/styles/workspace-page-header.test.ts
```

Expected: FAIL because Projects still uses a div header and a second toolbar row.

- [ ] **Step 3: Move the existing toolbar into the page header**

Convert the page bar to:

```vue
<header class="projects-page-bar workspace-page-header" data-workspace-page-header>
  <div class="projects-page-title-wrap">...</div>
  <div class="projects-toolbar">
    <!-- move the existing search field and status select here unchanged -->
  </div>
  <div class="projects-page-actions">...</div>
</header>
```

Delete the original toolbar block after the page bar. Do not duplicate controls or change bindings/handlers.

- [ ] **Step 4: Convert Projects CSS to a single-row 57px layout**

Use:

```css
.projects-page-bar {
  flex: 0 0 auto;
  display: grid;
  grid-template-columns: auto minmax(180px, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 0 clamp(24px, 3vw, 48px);
  border-bottom: 1px solid #e5e3df;
  background: rgba(255, 255, 255, .88);
}

.projects-toolbar {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(140px, 1fr) 112px;
  align-items: center;
  gap: 7px;
  padding: 0;
  border: 0;
  background: transparent;
}
```

Set search/select height to 34px.

Responsive rules must never set a page-bar min-height or create a second row:

- `max-width: 1180px`: hide `.projects-page-subtitle`.
- `max-width: 900px`: hide `.projects-view-switch`; hide `.projects-create-label`; make create button 34px square.
- `max-width: 620px`: hide `.projects-page-title-content`; reduce page-bar horizontal padding to 14px; use toolbar columns `minmax(120px, 1fr) 104px`.
- `max-width: 520px`: hide `.projects-status-filter`; change toolbar to one column; keep header at 57px.

Preserve dark rules, focus states, card layout, scrolling, search/filter logic, and create/view actions.

- [ ] **Step 5: Run selected tests and commit**

```bash
pnpm --filter main-app test src/styles/workspace-page-header.test.ts src/styles/workspace-canvas.test.ts src/components/layout/WorkspaceShell.spec.ts src/components/layout/AppHeader.spec.ts src/components/layout/AccountControls.spec.ts
git diff --check
git add frontend/packages/main-app/src/pages/projects/Projects.vue frontend/packages/main-app/src/styles/workspace-page-header.test.ts
git commit -m "style: integrate projects controls into header"
```

---

### Task 4: Full verification and browser geometry audit

**Files:** No production edits expected. If verification exposes a real regression, return it to the owning Task 1/2/3 implementer with a failing test.

- [ ] **Step 1: Run formatting, build, and selected tests**

From the repository root and `frontend/` as indicated:

```bash
git diff --check 6b7f6a3..HEAD
cd frontend
pnpm --filter main-app build
pnpm --filter main-app test src/styles/workspace-page-header.test.ts src/styles/workspace-canvas.test.ts src/components/layout/WorkspaceShell.spec.ts src/components/layout/AppHeader.spec.ts src/components/layout/AccountControls.spec.ts
pnpm --filter main-app test
```

Expected:

- build succeeds;
- selected tests pass;
- full suite has no new failure; the only allowed failure is the pre-existing `HomeLandingLayout.spec.ts` old padding assertion.

- [ ] **Step 2: Audit 14 independent headers in the browser**

At desktop width, inspect:

`/dashboard`, `/projects`, `/projects/demo-project`, `/campaign`, `/campaigns/demo-campaign`, `/campaigns/create`, `/campaigns/demo-campaign/ad-units/create`, `/material`, `/monitor`, `/settings`, `/account-config`, `/ai-usage-config`, `/platform-connections`, `/system-admin`.

For each route:

```js
const header = document.querySelector('[data-workspace-page-header]')
header && header.getBoundingClientRect().height === 57
```

Also require exactly one marker per page, no document horizontal overflow, original sidebar/Logo intact, and no console error introduced by this work.

- [ ] **Step 3: Audit explicit exceptions and target details**

- `/home`: no `[data-workspace-page-header]`, no new empty strip.
- Embedded Dashboard inside Home workspace: retains its non-fixed internal layout.
- `/dashboard`: visible filter captions and data note absent; selects/refresh work; normal and active circles render as circles; platform card outer heights are equal.
- `/projects`: toolbar is inside the primary header; search, status filter, view toggle, and create button still work.
- 390px viewport: Dashboard and Projects headers remain 57px with no document-level horizontal overflow.

- [ ] **Step 4: Final status evidence**

```bash
git status --short --branch
git log --oneline 6b7f6a3..HEAD
```

Expected: only `.superpowers/` remains untracked; all implementation files are committed.
