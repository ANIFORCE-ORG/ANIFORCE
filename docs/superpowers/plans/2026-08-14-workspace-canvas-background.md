# Workspace Canvas Background Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the page canvas of all fifteen workspace business routes use the Home page's light `#FFFFFF` background while preserving the warm sidebar and every internal component surface.

**Architecture:** Define one inherited `--workspace-canvas` token and one explicit `workspace-page-canvas` root marker in `global.css`. Every in-scope page root adopts the marker; page families that already define local canvas variables delegate those variables to the shared token. Legacy full-height gray utility classes are removed only from page-level shells and main canvases, never from cards, tables, drawers, dialogs, or hover states.

**Tech Stack:** Vue 3 SFCs, scoped CSS, Tailwind CSS 3, Vitest source-contract tests, Vite, TypeScript.

---

## File Map

**Create**

- `frontend/packages/main-app/src/styles/workspace-canvas.test.ts` — enumerates the fifteen workspace page components, enforces the shared canvas contract, blocks known page-level gray backgrounds, and protects representative internal soft surfaces.

**Modify — shared contract**

- `frontend/packages/main-app/src/styles/global.css` — owns `--workspace-canvas: #ffffff` and `.workspace-page-canvas`.

**Modify — page root markers and canvas delegation**

- `frontend/packages/main-app/src/pages/Home.vue`
- `frontend/packages/main-app/src/pages/Dashboard.vue`
- `frontend/packages/main-app/src/pages/Monitor.vue`
- `frontend/packages/main-app/src/pages/projects/Projects.vue`
- `frontend/packages/main-app/src/pages/projects/ProjectDetail.vue`
- `frontend/packages/main-app/src/pages/campaigns/Campaign.vue`
- `frontend/packages/main-app/src/pages/campaigns/CampaignDetail.vue`
- `frontend/packages/main-app/src/pages/campaigns/CreateCampaign.vue`
- `frontend/packages/main-app/src/pages/campaigns/CreateAdUnit.vue`
- `frontend/packages/main-app/src/pages/creatives/Material.vue`
- `frontend/packages/main-app/src/pages/settings/Settings.vue`
- `frontend/packages/main-app/src/pages/settings/AccountConfig.vue`
- `frontend/packages/main-app/src/pages/settings/AIUsageConfig.vue`
- `frontend/packages/main-app/src/pages/settings/PlatformConnections.vue`
- `frontend/packages/main-app/src/pages/system/SystemAdmin.vue`
- `frontend/packages/main-app/src/styles/settings-notion.css` — delegates the settings family canvas to the shared token.

**Read but do not modify**

- `frontend/packages/main-app/src/router/index.ts` — authoritative list of the fifteen `workspaceShell` routes.
- `frontend/packages/main-app/src/components/layout/SidebarNav.vue` — protected warm sidebar and right-edge shadow.
- `frontend/packages/main-app/src/pages/HomeLandingLayout.spec.ts` — known pre-existing failure; the stale vertical-position assertion is outside this change.

---

### Task 1: Establish the shared canvas contract and mark all fifteen page roots

**Files:**

- Create: `frontend/packages/main-app/src/styles/workspace-canvas.test.ts`
- Modify: `frontend/packages/main-app/src/styles/global.css:35-48`
- Modify: the root template element in each of the fifteen page files listed in the File Map
- Test: `frontend/packages/main-app/src/styles/workspace-canvas.test.ts`

- [ ] **Step 1: Write the failing route and root-marker contract**

Create `frontend/packages/main-app/src/styles/workspace-canvas.test.ts` with this content:

```ts
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const readSource = (path: string) =>
  readFileSync(new URL(path, import.meta.url), 'utf8')

const routerSource = readSource('../router/index.ts')
const globalSource = readSource('./global.css')

const workspacePages = [
  ['Home', '../pages/Home.vue'],
  ['Dashboard', '../pages/Dashboard.vue'],
  ['Monitor', '../pages/Monitor.vue'],
  ['Projects', '../pages/projects/Projects.vue'],
  ['ProjectDetail', '../pages/projects/ProjectDetail.vue'],
  ['Campaign', '../pages/campaigns/Campaign.vue'],
  ['CampaignDetail', '../pages/campaigns/CampaignDetail.vue'],
  ['CreateCampaign', '../pages/campaigns/CreateCampaign.vue'],
  ['CreateAdUnit', '../pages/campaigns/CreateAdUnit.vue'],
  ['Material', '../pages/creatives/Material.vue'],
  ['Settings', '../pages/settings/Settings.vue'],
  ['AccountConfig', '../pages/settings/AccountConfig.vue'],
  ['AIUsageConfig', '../pages/settings/AIUsageConfig.vue'],
  ['PlatformConnections', '../pages/settings/PlatformConnections.vue'],
  ['SystemAdmin', '../pages/system/SystemAdmin.vue'],
] as const

describe('workspace page canvas contract', () => {
  it('keeps exactly fifteen routes in the workspace shell', () => {
    expect(routerSource.match(/meta: \{ workspaceShell: true \}/g)).toHaveLength(15)
  })

  it('defines the Home-aligned light canvas token and reusable root class', () => {
    expect(globalSource).toContain('--workspace-canvas: #ffffff;')
    expect(globalSource).toContain('.workspace-page-canvas {')
    expect(globalSource).toContain('background-color: var(--workspace-canvas);')
  })

  it.each(workspacePages)('%s explicitly adopts the workspace canvas root', (_name, path) => {
    expect(readSource(path)).toContain('workspace-page-canvas')
  })
})
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
pnpm --filter main-app test -- src/styles/workspace-canvas.test.ts
```

Expected: FAIL because `global.css` does not yet define `--workspace-canvas` or `.workspace-page-canvas`, and the page roots do not contain the marker.

- [ ] **Step 3: Add the shared token and root class**

In `frontend/packages/main-app/src/styles/global.css`, extend the existing `:root` block and add the utility immediately after it:

```css
:root {
  --workspace-canvas: #ffffff;
  --status-running-bg: #ecfdf5;
  --status-running-text: #059669;
  --status-paused-bg: #fff7ed;
  --status-paused-text: #ea580c;
  --status-paused-border: #fdba74;
}

.workspace-page-canvas {
  background-color: var(--workspace-canvas);
}
```

Do not add `!important`. Existing `dark:` rules keep their greater `.dark .dark\:*` specificity.

- [ ] **Step 4: Add the root marker to all fifteen page components**

Make these exact root-class changes:

```vue
<!-- Home.vue -->
<div class="home-shell workspace-page-canvas" :class="hasContent ? 'is-conversation' : 'is-landing'">

<!-- Dashboard.vue -->
<div class="dashboard-shell workspace-page-canvas" :class="{ embedded: props.embedded }">

<!-- Monitor.vue -->
<div class="workspace-page-canvas flex h-screen w-full overflow-hidden dark:bg-slate-950">

<!-- Projects.vue -->
<div class="projects-shell workspace-page-canvas">

<!-- ProjectDetail.vue -->
<div class="project-detail-shell workspace-page-canvas">

<!-- Campaign.vue -->
<div class="workspace-page-canvas flex h-screen w-full overflow-hidden dark:bg-slate-950">

<!-- CampaignDetail.vue -->
<div class="workspace-page-canvas flex h-screen w-full overflow-hidden dark:bg-slate-950">

<!-- CreateCampaign.vue -->
<div class="workspace-page-canvas flex h-screen w-full overflow-hidden dark:bg-slate-950">

<!-- CreateAdUnit.vue -->
<div class="workspace-page-canvas flex h-screen w-full overflow-hidden dark:bg-slate-950">

<!-- Material.vue -->
<div class="workspace-page-canvas flex h-screen w-full overflow-hidden dark:bg-slate-950">

<!-- Settings.vue -->
<div class="settings-shell workspace-page-canvas">

<!-- AccountConfig.vue -->
<div class="settings-notion workspace-page-canvas">

<!-- AIUsageConfig.vue -->
<div class="settings-notion workspace-page-canvas">

<!-- PlatformConnections.vue -->
<div class="settings-notion workspace-page-canvas">

<!-- SystemAdmin.vue -->
<div class="workspace-page-canvas flex h-screen w-full overflow-hidden dark:bg-slate-950">
```

For the seven Tailwind roots that currently contain `bg-slate-50` or `bg-[#f6f7f9]`, the snippets above intentionally remove only that page-root light background while retaining `dark:bg-slate-950`.

- [ ] **Step 5: Run the focused test and verify GREEN**

Run:

```bash
pnpm --filter main-app test -- src/styles/workspace-canvas.test.ts
```

Expected: PASS, 17 tests total: one route-count test, one token test, and fifteen parameterized page-root tests.

- [ ] **Step 6: Commit the shared contract**

```bash
git add frontend/packages/main-app/src/styles/global.css \
  frontend/packages/main-app/src/styles/workspace-canvas.test.ts \
  frontend/packages/main-app/src/pages
git commit -m "style: establish workspace canvas contract"
```

---

### Task 2: Remove the remaining full-height gray canvases without flattening internal surfaces

**Files:**

- Modify: `frontend/packages/main-app/src/styles/workspace-canvas.test.ts`
- Modify: `frontend/packages/main-app/src/pages/Monitor.vue:44-46`
- Modify: `frontend/packages/main-app/src/pages/projects/Projects.vue:493-510`
- Modify: `frontend/packages/main-app/src/pages/campaigns/CreateCampaign.vue:258-267`
- Test: `frontend/packages/main-app/src/styles/workspace-canvas.test.ts`

- [ ] **Step 1: Extend the test with legacy-canvas and protected-surface assertions**

Append these tests inside the existing `describe` block:

```ts
  it('removes legacy gray only from full-height page canvases', () => {
    const monitor = readSource('../pages/Monitor.vue')
    const projects = readSource('../pages/projects/Projects.vue')
    const createCampaign = readSource('../pages/campaigns/CreateCampaign.vue')
    const material = readSource('../pages/creatives/Material.vue')

    expect(monitor).not.toContain(
      '<main class="flex flex-1 flex-col overflow-hidden bg-slate-50 dark:bg-slate-950">',
    )
    expect(createCampaign).not.toContain(
      '<div class="flex-1 flex flex-col bg-slate-50 dark:bg-slate-950 overflow-hidden">',
    )
    expect(projects).not.toContain('background: #f7f7f5;')
    expect(material).not.toContain(
      '<div class="flex h-screen w-full overflow-hidden bg-[#f6f7f9] dark:bg-slate-950">',
    )
  })

  it('preserves representative component-level soft surfaces', () => {
    const monitor = readSource('../pages/Monitor.vue')
    const material = readSource('../pages/creatives/Material.vue')

    expect(monitor).toContain('<thead class="bg-slate-50 text-slate-500 dark:bg-slate-800/50">')
    expect(material).toContain('border-dashed border-slate-300 bg-slate-50')
    expect(material).toContain('border-l border-slate-200 bg-[#f6f7f9] shadow-2xl')
  })
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
pnpm --filter main-app test -- src/styles/workspace-canvas.test.ts
```

Expected: FAIL because Monitor's main canvas, Create Campaign's inner full-height canvas, and Projects' scoped shell still paint legacy gray backgrounds.

- [ ] **Step 3: Convert only the remaining full-height canvases**

Apply these exact changes:

```vue
<!-- Monitor.vue -->
<main class="workspace-page-canvas flex flex-1 flex-col overflow-hidden dark:bg-slate-950">

<!-- CreateCampaign.vue -->
<div class="workspace-page-canvas flex-1 flex flex-col dark:bg-slate-950 overflow-hidden">
```

In `Projects.vue`, replace only the root shell declaration:

```css
.projects-shell {
  display: flex;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  background: var(--workspace-canvas);
}
```

Do not change Material's drawer declaration containing `border-l ... bg-[#f6f7f9] shadow-2xl`; it is an internal surface protected by the test.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run:

```bash
pnpm --filter main-app test -- src/styles/workspace-canvas.test.ts
```

Expected: PASS, including both protected-surface assertions.

- [ ] **Step 5: Commit the legacy-canvas cleanup**

```bash
git add frontend/packages/main-app/src/styles/workspace-canvas.test.ts \
  frontend/packages/main-app/src/pages/Monitor.vue \
  frontend/packages/main-app/src/pages/projects/Projects.vue \
  frontend/packages/main-app/src/pages/campaigns/CreateCampaign.vue
git commit -m "style: align legacy workspace page canvases"
```

---

### Task 3: Delegate existing page-family canvas variables to the shared token

**Files:**

- Modify: `frontend/packages/main-app/src/styles/workspace-canvas.test.ts`
- Modify: `frontend/packages/main-app/src/pages/Home.vue:729-759`
- Modify: `frontend/packages/main-app/src/pages/Dashboard.vue:425-444`
- Modify: `frontend/packages/main-app/src/pages/projects/Projects.vue:493-520`
- Modify: `frontend/packages/main-app/src/pages/projects/ProjectDetail.vue:360-385`
- Modify: `frontend/packages/main-app/src/pages/settings/Settings.vue:126-141`
- Modify: `frontend/packages/main-app/src/styles/settings-notion.css:1-25`
- Test: `frontend/packages/main-app/src/styles/workspace-canvas.test.ts`

- [ ] **Step 1: Add failing delegation assertions**

Append this test inside the existing `describe` block:

```ts
  it('delegates existing page-family canvas variables to the shared token', () => {
    expect(readSource('../pages/Home.vue')).toContain(
      '--notion-canvas: var(--workspace-canvas);',
    )
    expect(readSource('../pages/Dashboard.vue')).toContain(
      '--canvas: var(--workspace-canvas);',
    )
    expect(readSource('../pages/projects/Projects.vue')).toContain(
      'background: var(--workspace-canvas);',
    )
    expect(readSource('../pages/projects/ProjectDetail.vue')).toContain(
      'background: var(--workspace-canvas);',
    )
    expect(readSource('../pages/settings/Settings.vue')).toContain(
      'background: var(--workspace-canvas);',
    )
    expect(readSource('./settings-notion.css')).toContain(
      '--sn-canvas: var(--workspace-canvas);',
    )
  })
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
pnpm --filter main-app test -- src/styles/workspace-canvas.test.ts
```

Expected: FAIL because Home, Dashboard, Project Detail, Settings, and the shared settings stylesheet still hard-code white locally.

- [ ] **Step 3: Delegate the family variables and direct page canvases**

Apply these exact single-value substitutions and leave every adjacent declaration unchanged:

```text
Home.vue
  --notion-canvas: #ffffff;
  → --notion-canvas: var(--workspace-canvas);

Dashboard.vue
  --canvas: #fff;
  → --canvas: var(--workspace-canvas);

Projects.vue, inside .projects-main
  background: #ffffff;
  → background: var(--workspace-canvas);

ProjectDetail.vue, inside .project-detail-shell and .project-detail-main
  background: #fff;
  → background: var(--workspace-canvas);

Settings.vue, inside .settings-shell and .settings-main
  background: #ffffff;
  → background: var(--workspace-canvas);

settings-notion.css, inside .settings-notion
  --sn-canvas: #fff;
  → --sn-canvas: var(--workspace-canvas);

settings-notion.css, inside the single-line .sn-main rule
  background: #fff;
  → background: var(--sn-canvas);
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run:

```bash
pnpm --filter main-app test -- src/styles/workspace-canvas.test.ts
```

Expected: PASS.

- [ ] **Step 5: Run the workspace-shell protection tests**

Run:

```bash
pnpm --filter main-app test -- \
  src/styles/workspace-canvas.test.ts \
  src/components/layout/WorkspaceShell.spec.ts \
  src/components/layout/AppHeader.spec.ts \
  src/components/layout/AccountControls.spec.ts
```

Expected: PASS. These tests protect the route count, sidebar structure, header behavior, account dock, and Logo contract.

- [ ] **Step 6: Commit the family delegation**

```bash
git add frontend/packages/main-app/src/styles/workspace-canvas.test.ts \
  frontend/packages/main-app/src/pages/Home.vue \
  frontend/packages/main-app/src/pages/Dashboard.vue \
  frontend/packages/main-app/src/pages/projects/Projects.vue \
  frontend/packages/main-app/src/pages/projects/ProjectDetail.vue \
  frontend/packages/main-app/src/pages/settings/Settings.vue \
  frontend/packages/main-app/src/styles/settings-notion.css
git commit -m "style: share workspace canvas token across page families"
```

---

### Task 4: Verify every route in the browser and report the known baseline test

**Files:**

- No production file changes expected
- Inspect: the fifteen routes listed in the design spec

- [ ] **Step 1: Run syntax and production-build checks**

Run:

```bash
git diff --check
pnpm --filter main-app build
```

Expected: `git diff --check` produces no output and the Vite production build succeeds.

- [ ] **Step 2: Run the focused contract suite**

Run:

```bash
pnpm --filter main-app test -- \
  src/styles/workspace-canvas.test.ts \
  src/components/layout/WorkspaceShell.spec.ts \
  src/components/layout/AppHeader.spec.ts \
  src/components/layout/AccountControls.spec.ts
```

Expected: all focused tests PASS.

- [ ] **Step 3: Re-run the full suite and compare with the recorded baseline**

Run:

```bash
pnpm --filter main-app test
```

Expected after the twenty new workspace-canvas assertions are added: 32/33 tests pass. The only failure remains `src/pages/HomeLandingLayout.spec.ts`, which expects the obsolete `154px` landing padding while production uses the previously approved `260px` value. Confirm no new test failure appears. Do not edit that unrelated test in this task.

- [ ] **Step 4: Inspect all fifteen routes in light mode**

Use the existing local demo server at `http://127.0.0.1:3010`. Visit:

```text
/home
/dashboard
/projects
/projects/demo-project
/campaign
/campaigns/demo-campaign
/campaigns/create
/campaigns/demo-campaign/ad-units/create
/material
/monitor
/settings
/account-config
/ai-usage-config
/platform-connections
/system-admin
```

For each route, evaluate the `.workspace-page-canvas` element and any full-height main canvas. Expected light computed background: `rgb(255, 255, 255)`.

- [ ] **Step 5: Verify protected surfaces and navigation**

On representative routes:

- Sidebar background remains `rgb(247, 247, 245)` and its existing right-edge gradient shadow remains present.
- Monitor table header remains `rgb(248, 250, 252)`.
- Material upload/drop-zone soft surface remains `rgb(248, 250, 252)`.
- Material detail drawer retains its `#F6F7F9` surface.
- No horizontal overflow or new console error appears.
- The ANIFORCE Logo asset, dimensions, filter, and position remain unchanged.

- [ ] **Step 6: Record verification and final repository state**

Run:

```bash
git status --short
git log -5 --oneline
```

Expected: only `.superpowers/` visual-companion artifacts remain untracked unless they were locally ignored; production and test changes are committed. Report focused tests, production build, browser route count, and the single known pre-existing full-suite failure separately.
