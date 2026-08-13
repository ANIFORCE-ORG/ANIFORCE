# Notion App Header Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the ANIFORCE application header to the approved Notion-balanced direction while preserving the Logo and every existing interaction.

**Architecture:** Keep all changes inside the existing Vue single-file component. Replace presentation-only Tailwind class bundles with scoped semantic header classes, protect the Logo and approved visual contract with a Vitest source-contract test, and verify behavior and appearance in the running Vite app.

**Tech Stack:** Vue 3 SFC, TypeScript, scoped CSS, Vitest 2, Vite 5, pnpm workspace

---

## File map

- Create `frontend/packages/main-app/src/components/layout/AppHeader.spec.ts`: source-contract regression tests for the approved Notion styling and unchanged Logo rendering.
- Modify `frontend/packages/main-app/src/components/layout/AppHeader.vue`: presentation-only template classes and scoped styles; the script logic and Logo rendering contract stay unchanged.

## Existing worktree changes to preserve

The following files were already modified or untracked before implementation and are outside this plan. Do not edit, format, stage, revert, or commit them:

- `frontend/packages/main-app/index.html`
- `frontend/packages/main-app/src/styles/global.css`
- `frontend/packages/main-app/public/fonts/material-symbols-outlined.woff2`
- `frontend/packages/main-app/src/styles/material-symbols.test.ts`

Every Git command in this plan must use the two exact header paths from the file map. A non-clean overall `git status` is expected because the unrelated files above must remain untouched.

### Task 1: Add the failing header style contract

**Files:**
- Create: `frontend/packages/main-app/src/components/layout/AppHeader.spec.ts`
- Test: `frontend/packages/main-app/src/components/layout/AppHeader.spec.ts`

- [ ] **Step 1: Create the contract test**

```ts
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./AppHeader.vue', import.meta.url), 'utf8')

describe('AppHeader visual contract', () => {
  it('preserves the existing ANIFORCE Logo rendering contract', () => {
    expect(source).toContain(
      '<img :src="logoSvg" alt="ANIFORCE" class="h-10 w-auto max-w-[176px] object-contain logo-blue" />',
    )
    expect(source).toContain(
      'filter: brightness(0) saturate(100%) invert(45%) sepia(98%) saturate(1845%) hue-rotate(205deg) brightness(102%) contrast(98%);',
    )
  })

  it('uses the approved Notion-balanced header treatment', () => {
    expect(source).toContain('<header class="app-header">')
    expect(source).toContain('class="header-user"')
    expect(source).toContain('class="header-avatar"')
    expect(source).toContain('class="header-icon-button"')
    expect(source).toContain('class="language-switcher"')
    expect(source).toContain('border-bottom: 1px solid #e9e9e7;')
    expect(source).toContain(':global(.dark) .app-header')
    expect(source).toContain('.header-user:focus-visible')
    expect(source).not.toContain('backdrop-blur-md')
    expect(source).not.toContain('bg-primary/10')
    expect(source).not.toContain('border-2 border-primary/30')
  })
})
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
pnpm --filter main-app test -- src/components/layout/AppHeader.spec.ts
```

Expected: one Logo contract test passes and the Notion-balanced treatment test fails because `AppHeader.vue` does not yet contain `<header class="app-header">`.

- [ ] **Step 3: Confirm no production file changed before RED**

Run:

```bash
git status --short
```

Expected: `frontend/packages/main-app/src/components/layout/AppHeader.spec.ts` is newly untracked. The pre-existing `index.html`, `global.css`, `public/fonts/`, and `material-symbols.test.ts` entries also remain visible. Confirm their status is unchanged from the baseline above; do not stage or edit them.

### Task 2: Implement the approved Notion-balanced header

**Files:**
- Modify: `frontend/packages/main-app/src/components/layout/AppHeader.vue:51-160`
- Test: `frontend/packages/main-app/src/components/layout/AppHeader.spec.ts`

- [ ] **Step 1: Keep the entire `<script setup>` block unchanged and replace the template with the semantic presentation classes below**

```vue
<template>
  <header class="app-header">
    <!-- Logo -->
    <div class="flex items-center gap-2 cursor-pointer shrink-0" @click="handleLogoClick">
      <img :src="logoSvg" alt="ANIFORCE" class="h-10 w-auto max-w-[176px] object-contain logo-blue" />
    </div>

    <!-- Right Actions -->
    <div class="header-actions">
      <!-- 已登录状态 -->
      <template v-if="auth.isLoggedIn">
        <!-- User Info -->
        <div class="relative">
          <button
            class="header-user"
            type="button"
            aria-haspopup="menu"
            :aria-expanded="showUserMenu"
            @click="handleUserClick"
          >
            <div class="header-avatar">
              <span>{{ auth.user?.name?.charAt(0) }}</span>
            </div>
            <div class="header-identity">
              <div class="header-user-name">{{ auth.user?.name }}</div>
              <div class="header-user-email">{{ auth.user?.email }}</div>
            </div>
          </button>

          <!-- User Dropdown Menu -->
          <Transition name="fade">
            <div v-if="showUserMenu" class="header-user-menu" role="menu">
              <div class="header-menu-summary">
                <p>{{ auth.user?.name }}</p>
                <span>{{ auth.user?.email }}</span>
              </div>
              <button class="header-menu-logout" type="button" role="menuitem" @click="handleLogout">
                <span class="material-symbols-outlined">logout</span>
                {{ t.logout }}
              </button>
            </div>
          </Transition>
        </div>

        <button class="header-icon-button" type="button" aria-label="通知">
          <span class="material-symbols-outlined">notifications</span>
        </button>
      </template>

      <!-- 未登录状态 -->
      <template v-else>
        <button class="header-start-button" type="button" @click="handleUserClick">
          {{ t.getStartButton }}
        </button>
      </template>

      <!-- Language Segmented Control -->
      <div class="language-switcher" role="group" aria-label="Language">
        <button
          type="button"
          :class="['language-option', { 'is-active': language === 'cn' }]"
          :aria-pressed="language === 'cn'"
          @click="() => language === 'en' && toggleLanguage()"
        >
          中文
        </button>
        <button
          type="button"
          :class="['language-option', { 'is-active': language === 'en' }]"
          :aria-pressed="language === 'en'"
          @click="() => language === 'cn' && toggleLanguage()"
        >
          EN
        </button>
      </div>
    </div>
  </header>

  <!-- Click outside to close menu -->
  <div v-if="showUserMenu" class="fixed inset-0 z-40" @click="showUserMenu = false" />
</template>
```

- [ ] **Step 2: Replace the scoped style block with the approved Notion tokens while preserving the existing Logo filter exactly**

```css
<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px;
  border-bottom: 1px solid #e9e9e7;
  background: #ffffff;
  color: #37352f;
}

.header-actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 6px;
}

.header-user,
.header-icon-button,
.header-start-button,
.language-option,
.header-menu-logout {
  font: inherit;
}

.header-user {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  transition: background-color 120ms ease;
}

.header-user:hover,
.header-icon-button:hover {
  background: #f1f1ef;
}

.header-user:focus-visible,
.header-icon-button:focus-visible,
.header-start-button:focus-visible,
.language-option:focus-visible,
.header-menu-logout:focus-visible {
  outline: 2px solid #a8a29e;
  outline-offset: 2px;
}

.header-avatar {
  display: grid;
  width: 28px;
  height: 28px;
  flex: none;
  place-items: center;
  border: 1px solid #d9d9d6;
  border-radius: 50%;
  background: #f7f7f5;
  color: #37352f;
  font-size: 11px;
  font-weight: 600;
}

.header-identity {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: flex-start;
}

.header-user-name {
  color: #37352f;
  font-size: 12px;
  font-weight: 600;
  line-height: 15px;
}

.header-user-email {
  max-width: 180px;
  overflow: hidden;
  color: #787774;
  font-size: 10px;
  line-height: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-icon-button {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #787774;
  cursor: pointer;
  transition: background-color 120ms ease, color 120ms ease;
}

.header-icon-button .material-symbols-outlined {
  font-size: 18px;
}

.language-switcher {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-left: 1px;
  padding-left: 7px;
  border-left: 1px solid #e9e9e7;
}

.language-option {
  height: 28px;
  padding: 0 8px;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: #787774;
  cursor: pointer;
  font-size: 10px;
  font-weight: 600;
  transition: background-color 120ms ease, color 120ms ease;
}

.language-option:hover {
  color: #37352f;
}

.language-option.is-active {
  background: #f1f1ef;
  color: #37352f;
}

.header-user-menu {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 50;
  width: 176px;
  margin-top: 6px;
  padding: 4px;
  border: 1px solid #deddd9;
  border-radius: 6px;
  background: #ffffff;
  box-shadow: 0 4px 12px rgb(15 15 15 / 12%);
  color: #37352f;
}

.header-menu-summary {
  padding: 7px 8px 8px;
  border-bottom: 1px solid #eeeeec;
}

.header-menu-summary p {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  line-height: 16px;
}

.header-menu-summary span {
  display: block;
  overflow: hidden;
  color: #787774;
  font-size: 10px;
  line-height: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-menu-logout {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  padding: 6px 8px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #eb5757;
  cursor: pointer;
  font-size: 11px;
  text-align: left;
  transition: background-color 120ms ease;
}

.header-menu-logout:hover {
  background: rgb(235 87 87 / 8%);
}

.header-menu-logout .material-symbols-outlined {
  font-size: 15px;
}

.header-start-button {
  padding: 6px 10px;
  border: 0;
  border-radius: 5px;
  background: #37352f;
  color: #ffffff;
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* Keep the existing ANIFORCE Logo rendering unchanged. */
.logo-blue {
  filter: brightness(0) saturate(100%) invert(45%) sepia(98%) saturate(1845%) hue-rotate(205deg) brightness(102%) contrast(98%);
}

:global(.dark) .app-header {
  border-color: #2f2f2f;
  background: #191919;
  color: #e6e6e5;
}

:global(.dark) .header-user:hover,
:global(.dark) .header-icon-button:hover,
:global(.dark) .language-option.is-active {
  background: #252525;
}

:global(.dark) .header-avatar {
  border-color: #3a3a3a;
  background: #252525;
  color: #e6e6e5;
}

:global(.dark) .header-user-name,
:global(.dark) .language-option:hover,
:global(.dark) .language-option.is-active {
  color: #e6e6e5;
}

:global(.dark) .header-user-email,
:global(.dark) .header-icon-button,
:global(.dark) .language-option,
:global(.dark) .header-menu-summary span {
  color: #9b9a97;
}

:global(.dark) .language-switcher {
  border-color: #2f2f2f;
}

:global(.dark) .header-user-menu {
  border-color: #373737;
  background: #202020;
  color: #e6e6e5;
  box-shadow: 0 4px 14px rgb(0 0 0 / 35%);
}

:global(.dark) .header-menu-summary {
  border-color: #2f2f2f;
}

:global(.dark) .header-start-button {
  background: #e6e6e5;
  color: #191919;
}

@media (min-width: 768px) {
  .app-header {
    padding-right: 40px;
    padding-left: 40px;
  }
}

@media (max-width: 520px) {
  .app-header {
    padding-right: 12px;
    padding-left: 12px;
  }

  .header-actions {
    gap: 3px;
  }

  .header-user {
    gap: 6px;
    padding-right: 4px;
    padding-left: 4px;
  }

  .header-user-email {
    max-width: 112px;
  }

  .language-switcher {
    padding-left: 4px;
  }

  .language-option {
    padding-right: 6px;
    padding-left: 6px;
  }
}
</style>
```

- [ ] **Step 3: Run the focused test and verify GREEN**

Run:

```bash
pnpm --filter main-app test -- src/components/layout/AppHeader.spec.ts
```

Expected: `2 passed`, with no failed tests.

- [ ] **Step 4: Run all main-app tests**

Run:

```bash
pnpm --filter main-app test
```

Expected: all tests pass.

- [ ] **Step 5: Build the main application**

Run:

```bash
pnpm --filter main-app build
```

Expected: `vue-tsc -b` and `vite build` both exit 0.

- [ ] **Step 6: Check formatting and the exact implementation diff**

Run:

```bash
git diff --check
git diff -- frontend/packages/main-app/src/components/layout/AppHeader.vue frontend/packages/main-app/src/components/layout/AppHeader.spec.ts
```

Expected: `git diff --check` emits no output; the diff contains only the header presentation and its contract test. The Logo `<img>` line and `.logo-blue` filter remain byte-for-byte identical.

- [ ] **Step 7: Commit the green implementation**

```bash
git add frontend/packages/main-app/src/components/layout/AppHeader.vue frontend/packages/main-app/src/components/layout/AppHeader.spec.ts
git commit -m "style: align app header with Notion"
```

### Task 3: Browser acceptance and final verification

**Files:**
- Verify: `frontend/packages/main-app/src/components/layout/AppHeader.vue`
- Verify: `frontend/packages/main-app/src/components/layout/AppHeader.spec.ts`

- [ ] **Step 1: Confirm the existing Vite server hot-reloaded the component**

Run:

```bash
curl -fsS -o /private/tmp/notion-header-home.html -w 'frontend_http=%{http_code}\n' http://127.0.0.1:3010/home
lsof -nP -iTCP:3010 -sTCP:LISTEN
```

Expected: HTTP 200 and a Node listener on port 3010.

- [ ] **Step 2: Verify the desktop header in the browser**

Open `http://127.0.0.1:3010/home` and verify:

- solid white top bar with a neutral `#e9e9e7` bottom border;
- Logo appearance, width, height and left position match the pre-change header;
- neutral avatar, preserved Admin name and email, square notification hover target, and non-capsule language switcher;
- no header height jump or horizontal overflow.

- [ ] **Step 3: Verify interactions**

In the browser:

- click the user button and confirm the neutral Notion-style menu opens;
- click outside and confirm the menu closes;
- click `EN`, confirm the interface language changes, then return to `中文`;
- focus the user, notification and language buttons with keyboard navigation and confirm visible focus rings.

- [ ] **Step 4: Verify dark mode styles without changing app logic**

Temporarily add the existing `dark` class to the document root through browser inspection, verify neutral dark background, border, menu and text contrast, then remove the temporary class. Do not persist any dark-mode state change.

- [ ] **Step 5: Capture a final screenshot and inspect browser errors**

Expected: the screenshot matches visual option A and the browser console contains no new errors caused by `AppHeader.vue`.

- [ ] **Step 6: Run the completion gate**

```bash
pnpm --filter main-app test
pnpm --filter main-app build
git diff --check
git status --short --branch
git log -1 --format='%H%n%s'
```

Expected: tests and build pass, diff check is clean, and the branch contains the implementation commit. The unrelated baseline changes in `index.html`, `global.css`, `public/fonts/`, and `material-symbols.test.ts` remain uncommitted and unchanged; no header implementation files remain uncommitted.
