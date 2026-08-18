# ANIFORCE Workspace Canvas Background Design

**Date:** 2026-08-14

**Status:** Approved through option A

**Scope:** Light-theme page canvas backgrounds for the fifteen workspace business routes

## Problem

The workspace shell already uses the Home page as its visual reference: a warm `#F7F7F5` sidebar sits above a pure white (`#FFFFFF`) content canvas. The fifteen business routes do not currently share that canvas consistently.

Observed page-level distribution:

- Home, Dashboard, Project Detail, Settings, Account Config, AI Usage Config, and the primary Platform Connections surface already use white.
- Projects keeps a `#F7F7F5` outer shell even though its main content is white.
- Monitor, Campaign, Campaign Detail, Create Campaign, Create Ad Unit, and System Admin use Tailwind `bg-slate-50` (`#F8FAFC`) on their page-level shell or main content.
- Material uses `#F6F7F9` on its page-level shell.

The result is a visible canvas shift when users move between sidebar destinations, while the navigation shell itself remains unchanged.

## Approved Direction

Use option A, **shared workspace canvas token with explicit page-level adoption**:

- Introduce one light-theme workspace canvas token whose value is `#FFFFFF`.
- Apply that token only to each business page's root canvas and, where a second full-height main wrapper currently paints the canvas, to that wrapper as well.
- Remove or replace only conflicting page-level `bg-slate-50`, `#F7F7F5`, and `#F6F7F9` declarations.
- Preserve the sidebar canvas at `#F7F7F5` and preserve its current right-edge shadow treatment.
- Preserve all component-level surface colors, including cards, table headers, empty states, input fields, drawers, dialogs, status chips, hover states, and loading panels.

The implementation must not use a broad descendant override or `!important` rule. The page canvas contract must remain explicit and auditable at page roots.

## Route Contract

The following fifteen routes are in scope:

1. `/home`
2. `/dashboard`
3. `/projects`
4. `/projects/:id`
5. `/campaign`
6. `/campaigns/:id`
7. `/campaigns/create`
8. `/campaigns/:campaignId/ad-units/create`
9. `/material`
10. `/monitor`
11. `/settings`
12. `/account-config`
13. `/ai-usage-config`
14. `/platform-connections`
15. `/system-admin`

Public routes such as login, registration, onboarding, contact, privacy, and terms are explicitly outside this change.

## Component and Code Scope

Expected shared style change:

- `frontend/packages/main-app/src/styles/global.css`

Expected page-root review or change:

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

Pages already honoring the white canvas need only adopt the shared contract if required for a consistent testable marker; their internal styles must not be rewritten.

## Styling Boundaries

The canvas layer includes:

- The full-height page root next to the sidebar.
- The primary main element when it independently paints the remaining viewport.
- Empty space around content sections and below short page content.

The canvas layer excludes:

- `SidebarNav` and `AccountControls`.
- Sticky page bars and headers whose translucent or white surface is already intentional.
- Cards, panels, tables, forms, modals, drawers, toasts, skeletons, and business-status elements.
- Embedded workspace modules rendered inside Home conversations.

## Dark Theme

This request establishes the light-theme contract. Existing `dark:` page behavior must not be removed or broadened. If a reusable utility is introduced, it must either defer to existing dark utilities or define an equivalent dark canvas without forcing white in dark mode.

## Testing Strategy

Follow test-first implementation:

1. Add a focused source-contract test that enumerates the fifteen `workspaceShell` routes and their page components.
2. Assert that the shared light canvas token resolves to `#FFFFFF`.
3. Assert that every in-scope page root participates in the canvas contract.
4. Assert that known conflicting page-level backgrounds no longer paint the workspace canvas.
5. Include representative protection assertions showing that internal soft surfaces such as table headers or cards retain their existing colors.
6. Run the focused test and observe it fail before editing production styles.

## Browser Verification

At the local demo URL, verify every in-scope route in light mode:

- The page root and any full-height main canvas compute to `rgb(255, 255, 255)`.
- The sidebar remains `rgb(247, 247, 245)` with its existing right-edge shadow.
- Representative cards and soft table/header surfaces retain their pre-change computed colors.
- No white strip, gray gap, horizontal overflow, or new console error appears.
- Detail and creation routes may use demo identifiers; their page shell must still be measurable even when business data is empty or unavailable.

After the focused regression passes, run `git diff --check` and the main-app production build.

## Non-goals

- Redesigning page layouts, typography, spacing, cards, tables, dialogs, or navigation.
- Changing the ANIFORCE logo or illustration assets.
- Changing authentication, demo login behavior, APIs, routing, or business logic.
- Standardizing every internal use of `bg-slate-50` or other soft surface colors.
- Altering public pages or defining a new dark-theme design.
