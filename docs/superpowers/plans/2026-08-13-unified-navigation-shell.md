# Unified Navigation Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Join the light-theme app header and sidebar into one warm Notion-style navigation shell without changing the ANIFORCE Logo.

**Architecture:** Keep the change local to `AppHeader.vue`: reuse the sidebar's existing `#F7F7F5` navigation canvas and remove only the header's light-theme bottom divider. A source-contract test isolates the `.app-header` rule so menu shadows and dark-theme declarations remain free to evolve independently.

**Tech Stack:** Vue 3 single-file components, scoped CSS, Vitest, pnpm, Vite

---

## File Map

- Modify `frontend/packages/main-app/src/components/layout/AppHeader.spec.ts`: assert the approved shell background and seam removal while retaining the Logo contract.
- Modify `frontend/packages/main-app/src/components/layout/AppHeader.vue`: change only the light header surface and divider.
- Do not modify `SidebarNav.vue`, global styles, Logo assets, routing, auth/demo mode, APIs, or business logic.

### Task 1: Lock and Implement the Unified Header Surface

**Files:**
- Modify: `frontend/packages/main-app/src/components/layout/AppHeader.spec.ts:4-29`
- Modify: `frontend/packages/main-app/src/components/layout/AppHeader.vue:134-145`
- Test: `frontend/packages/main-app/src/components/layout/AppHeader.spec.ts`

- [ ] **Step 1: Add the failing surface-contract test**

Add a focused extraction beside the existing `source` constant:

```ts
const appHeaderRule = source.match(/\.app-header \{([\s\S]*?)\n\}/)?.[1] ?? ''
```

Remove the obsolete light-divider expectation from `uses the approved Notion-balanced header treatment`:

```ts
expect(source).toContain('border-bottom: 1px solid #e9e9e7;')
```

Add this test after the Notion-balanced treatment test:

```ts
it('joins the header and sidebar into the approved warm navigation shell', () => {
  expect(appHeaderRule).toContain('background: #f7f7f5;')
  expect(appHeaderRule).not.toContain('border-bottom')
  expect(appHeaderRule).not.toContain('box-shadow')
})
```

- [ ] **Step 2: Run the focused test and verify the red state**

Run from `frontend/`:

```bash
pnpm --filter main-app exec vitest run src/components/layout/AppHeader.spec.ts
```

Expected: FAIL because `.app-header` still contains `background: #ffffff;` and `border-bottom: 1px solid #e9e9e7;`.

- [ ] **Step 3: Apply the minimal production style change**

Change the light `.app-header` block from:

```css
padding: 8px 20px;
border-bottom: 1px solid #e9e9e7;
background: #ffffff;
color: #37352f;
```

to:

```css
padding: 8px 20px;
background: #f7f7f5;
color: #37352f;
```

Do not edit the `<img>` Logo line, `.logo-blue`, header padding, media queries, or dark-theme rule.

- [ ] **Step 4: Run the focused test and verify the green state**

Run from `frontend/`:

```bash
pnpm --filter main-app exec vitest run src/components/layout/AppHeader.spec.ts
```

Expected: all four AppHeader visual-contract tests pass.

- [ ] **Step 5: Commit the tested surface change**

Run from the repository root:

```bash
git add frontend/packages/main-app/src/components/layout/AppHeader.spec.ts frontend/packages/main-app/src/components/layout/AppHeader.vue
git diff --cached --check
git commit -m "style: unify header and sidebar surfaces"
```

Expected: one commit containing only the header component and its focused test.

### Task 2: Verify the Full UI Contract

**Files:**
- Verify: `frontend/packages/main-app/src/components/layout/AppHeader.vue`
- Verify: `frontend/packages/main-app/src/components/layout/SidebarNav.vue`

- [ ] **Step 1: Run repository formatting and production checks**

Run from the repository root and then `frontend/`:

```bash
git diff --check
pnpm --filter main-app build
```

Expected: no whitespace errors; Vue type checking and Vite production build complete successfully.

- [ ] **Step 2: Verify desktop computed styles in the running app**

Open `http://127.0.0.1:3010/home` at 1280×720 and inspect `.app-header`, `.sidebar-notion`, and the Logo image.

Expected:

- Header and sidebar backgrounds both equal `rgb(247, 247, 245)`.
- Header `border-bottom-width` is `0px` and `box-shadow` is `none`.
- Logo remains at x=40px with the same source, rendered size, filter, and y position as before the change.
- The white main content area remains unchanged.

- [ ] **Step 3: Verify collapsed and narrow layouts**

Click `.sidebar-collapse`, then verify the sidebar width is 52px and the warm shell remains continuous beneath the Logo. Resize to 390px wide and verify the header does not overflow.

Expected: no white strip or hard horizontal seam under the Logo area in either sidebar state; the 390px header has no horizontal overflow and the Logo rendering contract is unchanged.

- [ ] **Step 4: Check console and working-tree isolation**

Verify browser console errors and run from the repository root:

```bash
git status --short
git log -1 --oneline
```

Expected: no new browser console errors; the implementation commit is current; pre-existing unrelated changes remain unstaged and untouched.
