# Codex-Inspired Workspace Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the approved Codex-inspired rail hierarchy to ANIFORCE workspace routes while preserving the existing brand colors, Logo asset, top-right controls, and business behavior.

**Architecture:** Workspace routes opt into the shell through route metadata. `SidebarNav` owns the fixed rail, its flow spacer, collapse width, Logo, and left-cast boundary fade; `AppHeader` conditionally hides only its workspace Logo and draws the lighter header hairline; `AppFooter` offsets itself by the live rail width and removes its border on Home.

**Tech Stack:** Vue 3 `<script setup>`, TypeScript, Vue Router, scoped CSS, Vitest source-contract tests, pnpm/Vite.

---

### Task 1: Lock the approved shell contract in a failing test

**Files:**
- Create: `frontend/packages/main-app/src/components/layout/WorkspaceShell.spec.ts`

- [ ] **Step 1: Write the failing source-contract test**

```ts
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const readSource = (path: string) =>
  readFileSync(fileURLToPath(new URL(path, import.meta.url)), 'utf8')

describe('Codex-inspired workspace shell', () => {
  const routerSource = readSource('../../router/index.ts')
  const headerSource = readSource('./AppHeader.vue')
  const sidebarSource = readSource('./SidebarNav.vue')
  const footerSource = readSource('./AppFooter.vue')

  it('opts the fifteen SidebarNav routes into the workspace shell', () => {
    expect(routerSource.match(/meta: \{ workspaceShell: true \}/g)).toHaveLength(15)
    expect(routerSource).toMatch(/name: 'market-analysis',\s+component: \(\) => import\('@\/pages\/MarketAnalysis\.vue'\),\s+\},/)
  })

  it('keeps the public header Logo and applies only workspace hairline behavior', () => {
    expect(headerSource).toContain('const isWorkspaceShell = computed(() => route.meta.workspaceShell === true)')
    expect(headerSource).toContain('v-if="!isWorkspaceShell"')
    expect(headerSource).toContain('class="h-10 w-auto max-w-[176px] object-contain logo-blue"')
    expect(headerSource).toContain('border-bottom: 0.5px solid rgba(55, 53, 47, 0.09)')
  })

  it('renders a fixed rail with a flow spacer, compact Logo, and a left-cast fade', () => {
    expect(sidebarSource).toContain('sidebar-rail-spacer')
    expect(sidebarSource).toContain('fixed bottom-0 left-0 top-0 z-50')
    expect(sidebarSource).toContain("--workspace-sidebar-width")
    expect(sidebarSource).toContain('height: 30px')
    expect(sidebarSource).toContain('rgba(55, 53, 47, 0.068) 100%')
  })

  it('offsets workspace footer content and removes only the Home divider', () => {
    expect(footerSource).toContain("route.meta.workspaceShell === true")
    expect(footerSource).toContain("route.name === 'home'")
    expect(footerSource).toContain('var(--workspace-sidebar-width, 205px)')
    expect(footerSource).toContain('border-top: 0 !important')
  })
})
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `pnpm --filter main-app exec vitest run src/components/layout/WorkspaceShell.spec.ts`

Expected: FAIL because workspace metadata, the fixed rail contract, and route-aware footer/header behavior do not exist yet.

- [ ] **Step 3: Commit the test after implementation with Task 2**

The failing test is kept unstaged until the matching implementation is green.

### Task 2: Implement the workspace rail and route-aware header/footer

**Files:**
- Modify: `frontend/packages/main-app/src/router/index.ts`
- Modify: `frontend/packages/main-app/src/components/layout/AppHeader.vue`
- Modify: `frontend/packages/main-app/src/components/layout/SidebarNav.vue`
- Modify: `frontend/packages/main-app/src/components/layout/AppFooter.vue`
- Test: `frontend/packages/main-app/src/components/layout/WorkspaceShell.spec.ts`

- [ ] **Step 1: Add route metadata to the fifteen direct SidebarNav routes**

Add this property to `home`, `campaign`, `material`, `monitor`, `dashboard`, `projects`, `project-detail`, `campaign-detail`, `create-campaign`, `create-ad-unit`, `settings`, `account-config`, `ai-usage-config`, `platform-connections`, and `system-admin`:

```ts
meta: { workspaceShell: true },
```

Do not add it to `market-analysis`, starting, auth, or legal routes.

- [ ] **Step 2: Make AppHeader route-aware without changing its public Logo or controls**

```ts
const route = useRoute()
const isWorkspaceShell = computed(() => route.meta.workspaceShell === true)
```

Bind `app-header--workspace`, hide only the existing left Logo with `v-if="!isWorkspaceShell"`, and add:

```css
.app-header--workspace {
  border-bottom: 0.5px solid rgba(55, 53, 47, 0.09);
}
```

- [ ] **Step 3: Convert SidebarNav into fixed rail plus flow spacer**

Import `watch`, `onBeforeUnmount`, and the existing SVG Logo. Synchronize collapse width to the root:

```ts
const sidebarWidth = computed(() => isCollapsed.value ? '52px' : '205px')
const syncSidebarWidth = () => {
  document.documentElement.style.setProperty('--workspace-sidebar-width', sidebarWidth.value)
}

syncSidebarWidth()
watch(sidebarWidth, syncSidebarWidth)
onBeforeUnmount(() => {
  document.documentElement.style.removeProperty('--workspace-sidebar-width')
})
```

Render a `52px`/`205px` flow spacer followed by a `fixed bottom-0 left-0 top-0 z-50` aside. Move the existing Logo asset into a 57px brand row, display it only when expanded, and keep it at:

```css
.sidebar-brand-logo {
  width: auto;
  height: 30px;
  max-width: 94px;
  object-fit: contain;
}
```

Remove the rail border and place the approved 16px shadow transition inside the rail:

```css
.sidebar-notion::after {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 16px;
  background: linear-gradient(90deg, rgba(55, 53, 47, 0) 0, rgba(55, 53, 47, 0.012) 34%, rgba(55, 53, 47, 0.032) 66%, rgba(55, 53, 47, 0.068) 100%);
  content: '';
  pointer-events: none;
}
```

- [ ] **Step 4: Offset AppFooter and remove only the Home border**

```ts
const route = useRoute()
const isWorkspaceShell = computed(() => route.meta.workspaceShell === true)
const isHomeWorkspace = computed(() => route.name === 'home')
```

Apply route classes and:

```css
.app-footer--workspace {
  padding-left: calc(var(--workspace-sidebar-width, 205px) + 40px) !important;
}

.app-footer--home {
  border-top: 0 !important;
}
```

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `pnpm --filter main-app exec vitest run src/components/layout/WorkspaceShell.spec.ts src/components/layout/AppHeader.spec.ts`

Expected: both files PASS.

- [ ] **Step 6: Commit the isolated shell implementation**

```bash
git add docs/superpowers/plans/2026-08-13-codex-workspace-shell.md frontend/packages/main-app/src/components/layout/WorkspaceShell.spec.ts frontend/packages/main-app/src/components/layout/AppHeader.vue frontend/packages/main-app/src/components/layout/SidebarNav.vue frontend/packages/main-app/src/components/layout/AppFooter.vue frontend/packages/main-app/src/router/index.ts
git commit -m "style: apply Codex-inspired workspace shell"
```

### Task 3: Verify the running local UI and production build

**Files:**
- Verify only: `frontend/packages/main-app`

- [ ] **Step 1: Run all main-app tests**

Run: `pnpm --filter main-app test`

Expected: PASS, including the user's existing `material-symbols.test.ts`.

- [ ] **Step 2: Build production assets**

Run: `pnpm --filter main-app build`

Expected: exit 0 with Vite build output.

- [ ] **Step 3: Check patch hygiene and preserved edits**

Run: `git diff --check HEAD^..HEAD && git status --short`

Expected: no whitespace errors; pre-existing `index.html`, `global.css`, `public/fonts/`, and `material-symbols.test.ts` remain uncommitted and unchanged by this work.

- [ ] **Step 4: Inspect the live Home route at desktop and 390px**

Open `http://127.0.0.1:3010/home`, wait for `domcontentloaded` plus a short render delay, and verify: small left-aligned Logo, full-height warm rail, right-over-left boundary fade, lighter top line beginning at the rail edge, unchanged top-right actions, no footer divider, collapse behavior, and no horizontal overflow at 390px.
