# Sidebar Account Dock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the signed-in account controls from the workspace header into a reusable Codex-style dock at the bottom of the shared sidebar while preserving the existing public header experience.

**Architecture:** Extract account, notification, language, and logout behavior from `AppHeader.vue` into a focused `AccountControls.vue`. `AppHeader` renders the shared control only on non-workspace routes, while `SidebarNav` renders its sidebar variant beneath the scrollable navigation and passes the rail collapse state.

**Tech Stack:** Vue 3 Composition API, TypeScript, Vue Router, Pinia auth/language stores, scoped CSS, Vitest source-contract tests, Vite.

---

## File Map

- Create `frontend/packages/main-app/src/components/layout/AccountControls.vue`: shared header/sidebar account UI and menu behavior.
- Create `frontend/packages/main-app/src/components/layout/AccountControls.spec.ts`: source contract for variants, controls, accessibility, and right-opening popover.
- Modify `frontend/packages/main-app/src/components/layout/AppHeader.vue`: preserve the logo and shell hairline while delegating non-workspace account rendering.
- Modify `frontend/packages/main-app/src/components/layout/AppHeader.spec.ts`: assert workspace suppression and public-header delegation.
- Modify `frontend/packages/main-app/src/components/layout/SidebarNav.vue`: add the bottom dock and expose popover overflow.
- Modify `frontend/packages/main-app/src/components/layout/WorkspaceShell.spec.ts`: assert the dock and unchanged shell geometry.

### Task 1: Lock the shared account-control contract

**Files:**
- Create: `frontend/packages/main-app/src/components/layout/AccountControls.spec.ts`
- Modify: `frontend/packages/main-app/src/components/layout/AppHeader.spec.ts`
- Modify: `frontend/packages/main-app/src/components/layout/WorkspaceShell.spec.ts`

- [ ] **Step 1: Write the failing source-contract tests**

Create assertions requiring `variant`, `collapsed`, the existing auth/language stores, semantic menu attributes, Escape handling, the sidebar dock, and route-aware header suppression:

```ts
expect(accountSource).toContain("variant: 'header' | 'sidebar'")
expect(accountSource).toContain("collapsed: false")
expect(accountSource).toContain("aria-haspopup=\"menu\"")
expect(accountSource).toContain("event.key === 'Escape'")
expect(accountSource).toContain('account-popover--sidebar')
expect(headerSource).toContain('<AccountControls v-if="!isWorkspaceShell" variant="header" />')
expect(sidebarSource).toContain('<AccountControls variant="sidebar" :collapsed="isCollapsed" />')
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
pnpm --filter main-app exec vitest run src/components/layout/AccountControls.spec.ts src/components/layout/AppHeader.spec.ts src/components/layout/WorkspaceShell.spec.ts
```

Expected: FAIL because `AccountControls.vue` and its integration do not exist.

### Task 2: Extract account behavior and preserve the public header

**Files:**
- Create: `frontend/packages/main-app/src/components/layout/AccountControls.vue`
- Modify: `frontend/packages/main-app/src/components/layout/AppHeader.vue`

- [ ] **Step 1: Implement the shared component API**

Define the component boundary and menu state:

```ts
interface Props {
  variant: 'header' | 'sidebar'
  collapsed?: boolean
}

const props = withDefaults(defineProps<Props>(), { collapsed: false })
const showMenu = ref(false)
const isSidebar = computed(() => props.variant === 'sidebar')
```

Reuse `useAuthStore`, `useLanguage`, and `useRouter`; keep logout and language mutations unchanged. Add a window keydown listener that closes the menu on Escape.

- [ ] **Step 2: Render the two variants**

For `header`, reproduce the existing avatar/name/email, notification button, language selector, guest start button, and dropdown. For `sidebar`, render a lower-left trigger with avatar and name when expanded and avatar only when collapsed; place email, notification, language, and logout inside a popover opening to the right.

- [ ] **Step 3: Delegate from AppHeader**

Keep the public logo markup unchanged and replace the existing action block with:

```vue
<AccountControls v-if="!isWorkspaceShell" variant="header" />
```

Give `.app-header--workspace` a `min-height: 57px` so removing the actions does not change the top rail height.

- [ ] **Step 4: Run focused tests and keep working until the extraction tests pass**

Run the Task 1 command. Expected: account and header tests progress to PASS; the sidebar integration assertion remains RED until Task 3.

### Task 3: Add the sidebar bottom dock

**Files:**
- Modify: `frontend/packages/main-app/src/components/layout/SidebarNav.vue`

- [ ] **Step 1: Mount the dock below the scroll region**

Import `AccountControls` and place it after `</nav>`:

```vue
<AccountControls variant="sidebar" :collapsed="isCollapsed" />
```

The navigation keeps `flex-1` and vertical scrolling, making the new component a fixed lower rail item without changing page-level markup.

- [ ] **Step 2: Allow the right-opening popover without changing rail geometry**

Remove the `overflow-hidden` utility from the fixed `aside`; keep `overflow-x-hidden` on the scroll region. The account component popover uses `position: absolute; left: calc(100% + 8px); bottom: 8px` and a restrained neutral shadow.

- [ ] **Step 3: Run focused tests and verify GREEN**

Run the Task 1 command. Expected: all focused test files PASS.

- [ ] **Step 4: Refactor only duplicated account styles**

Remove account-only state and CSS from `AppHeader.vue`; retain header shell, logo, public layout, and dark-mode shell rules. Re-run focused tests after refactoring.

### Task 4: Full verification and visual acceptance

**Files:**
- Verify only; no planned production changes.

- [ ] **Step 1: Run whitespace and diff checks**

```bash
git diff --check
git diff -- frontend/packages/main-app/src/components/layout/AccountControls.vue frontend/packages/main-app/src/components/layout/AppHeader.vue frontend/packages/main-app/src/components/layout/SidebarNav.vue
```

Expected: no whitespace errors and no unrelated files in the feature diff.

- [ ] **Step 2: Run the complete test suite**

```bash
pnpm --filter main-app test
```

Expected: all test files and tests PASS.

- [ ] **Step 3: Run the production build**

```bash
pnpm --filter main-app build
```

Expected: Vue type checking and Vite build exit 0.

- [ ] **Step 4: Inspect the live app**

At `http://127.0.0.1:3010/home`, confirm the workspace header no longer contains the account block, the dock sits at the sidebar bottom, expanded and collapsed triggers open the same right-side popover, the popover is not clipped, and the page has no horizontal overflow or console errors. Inspect one additional workspace route and one non-workspace route to confirm global coverage and public-header preservation.

- [ ] **Step 5: Commit only feature files**

```bash
git add docs/superpowers/plans/2026-08-13-sidebar-account-dock.md \
  frontend/packages/main-app/src/components/layout/AccountControls.vue \
  frontend/packages/main-app/src/components/layout/AccountControls.spec.ts \
  frontend/packages/main-app/src/components/layout/AppHeader.vue \
  frontend/packages/main-app/src/components/layout/AppHeader.spec.ts \
  frontend/packages/main-app/src/components/layout/SidebarNav.vue \
  frontend/packages/main-app/src/components/layout/WorkspaceShell.spec.ts
git commit -m "feat: move account controls to sidebar dock"
```

Do not stage the existing `index.html`, `global.css`, font files, or `material-symbols.test.ts` changes.
