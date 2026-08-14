# Dashboard Width Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Constrain the analytics Dashboard to the reference image's visual width so wide screens no longer flatten cards and charts horizontally.

**Architecture:** Keep the existing Vue template and data flow unchanged. Implement the alignment entirely in `Dashboard.vue` scoped CSS by centering a 1080px content canvas and calculating the full-width header's horizontal padding from the same canvas width.

**Tech Stack:** Vue 3 Single-File Component, scoped CSS, Vite, vue-tsc

---

### Task 1: Align the Dashboard content canvas

**Files:**
- Modify: `packages/main-app/src/pages/Dashboard.vue:291-304`
- Verify: `packages/main-app/src/pages/Dashboard.vue`

- [x] **Step 1: Confirm the current wide-layout baseline**

Run:

```bash
rg -n "replay-bar \{|replay-content \{" packages/main-app/src/pages/Dashboard.vue
```

Expected: `.replay-bar` has no content-grid-aware horizontal padding and `.replay-content` contains `max-width: 1500px`.

- [x] **Step 2: Apply the minimal CSS implementation**

Replace the two relevant declarations with:

```css
.replay-bar {
  min-height: 64px;
  align-items: center;
  padding-inline: max(24px, calc((100% - 1080px) / 2 + 18px));
}

.replay-content {
  width: 100%;
  max-width: 1080px;
  margin-inline: auto;
  padding: 14px 18px 54px;
}
```

Do not modify the template, script, chart geometry, responsive breakpoints, page content, or `packages/main-app/src/router/index.ts`.

- [x] **Step 3: Run static assertions for the exact layout contract**

Run:

```bash
node -e "const fs=require('fs');const s=fs.readFileSync('packages/main-app/src/pages/Dashboard.vue','utf8');if(!s.includes('max-width: 1080px')||!s.includes('margin-inline: auto')||!s.includes('calc((100% - 1080px) / 2 + 18px)')||s.includes('max-width: 1500px'))process.exit(1)"
```

Expected: exit code 0 with no output.

- [x] **Step 4: Verify formatting and compile the frontend**

Run:

```bash
git diff --check
pnpm --filter main-app build
```

Expected: `git diff --check` exits 0; vue-tsc and Vite finish successfully with no build errors.

- [x] **Step 5: Verify scope and local layout behavior**

Run:

```bash
git diff -- packages/main-app/src/pages/Dashboard.vue
git status --short
```

Expected: the Dashboard diff contains only the two scoped CSS adjustments. The existing local Demo login change in `packages/main-app/src/router/index.ts` remains present and untouched. At a CSS viewport near 1590px, the Dashboard content stops at 1080px, remains centered, and platform cards stay in three columns.

- [x] **Step 6: Commit only the Dashboard implementation**

Run:

```bash
git add packages/main-app/src/pages/Dashboard.vue
git commit -m "fix(frontend): align dashboard canvas width"
```

Expected: the commit contains only `Dashboard.vue`; the pre-existing router modification remains unstaged.
