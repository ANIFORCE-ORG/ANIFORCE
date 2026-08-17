# ANIFORCE Codex-Inspired Workspace Shell Design

**Date:** 2026-08-13

**Status:** Approved through visual preview V5

**Scope:** Routes that render the shared `SidebarNav` workspace navigation

## Goal

Adopt Codex's workspace-shell structure while preserving ANIFORCE's current color system and existing top-right controls. The left navigation becomes a full-height rail that owns the ANIFORCE brand. The content plane on the right visually sits above the rail through a left-falling boundary fade. The top control bar remains white and keeps its existing user, notification, and language treatment.

## Approved Visual Contract

### Structure

- Workspace routes use a full-height left rail from viewport top to bottom.
- Expanded rail width remains 205px; collapsed width remains 52px.
- The Logo moves from the global header into the rail's 57px brand row on workspace routes.
- The right-side top controls begin visually after the rail. Their markup, size, spacing, colors, and behavior remain unchanged.
- Routes without `SidebarNav` keep the current full-width header and the current 144.34×40 Logo at x=40 on desktop.

### Logo

- Reuse `aniforce-logo-transparent.svg`. Apply the same literal filter value in `SidebarNav`; leave the standard header's `.logo-blue` rule unchanged.
- Expanded workspace rail: Logo height 30px with automatic width (93.375px for the current asset), x=16px.
- The Logo remains vertically centered in the 57px brand row.
- Move the existing collapse control into the brand row's right side, matching the Codex structural reference.
- Collapsed rail: hide the wordmark and center the collapse control. Do not add or generate another Logo asset.

### Existing ANIFORCE Colors

- Rail canvas remains `#F7F7F5`.
- Active navigation surface remains `#EFEFED`.
- Existing warm-neutral text colors remain in use.
- Main display canvas and top bar remain white.
- No Codex blue-gray palette is transferred into production.

### Vertical Boundary: Right Plane Over Left Rail

The display area is the foreground plane. Its depth cue falls leftward into the rail:

- Remove the ordinary right border from the rail.
- Add an internal 16px fade at the rail's right edge.
- Gradient direction, from the rail interior toward the display boundary:

```css
linear-gradient(
  90deg,
  rgba(55, 53, 47, 0) 0,
  rgba(55, 53, 47, 0.012) 34%,
  rgba(55, 53, 47, 0.032) 66%,
  rgba(55, 53, 47, 0.068) 100%
)
```

- The fade stays inside the rail. It must not dim the white display area.
- The fade follows both the 205px expanded edge and the 52px collapsed edge automatically.

### Horizontal Boundary

- On workspace routes, the header bottom rule is `0.5px solid rgba(55, 53, 47, 0.09)`.
- The full-height rail covers the left portion, so the visible rule begins only at the current rail edge.
- Do not add a header drop shadow.
- Non-workspace routes retain the current `1px solid #E9E9E7` header boundary.

### Footer / Composer Boundary

- On `/home`, remove `AppFooter`'s top border. The composer already defines its own boundary and shadow.
- Offset workspace footer content by the live rail width so text never renders underneath the fixed rail.
- Other routes retain the current footer border; non-workspace routes also retain the current padding.

## Architecture

### Route Ownership

Mark every route that directly renders `SidebarNav` with:

```ts
meta: { workspaceShell: true }
```

`AppHeader` and `AppFooter` use this route metadata to apply workspace-only variants. This prevents path lists from being duplicated across components and preserves the standard shell on landing, authentication, legal, and contact routes.

### Sidebar Layout

`SidebarNav` renders two root siblings:

1. A flow spacer whose width follows the existing expanded/collapsed state.
2. A fixed `<aside>` at `top: 0; bottom: 0; left: 0` with the same width and `z-index: 50`.

The spacer preserves every existing page's flex layout; the fixed rail supplies full-height structural ownership without editing each of the 15 workspace page layouts.

`SidebarNav` publishes the live width through `--workspace-sidebar-width` on `document.documentElement` so `AppFooter` can offset its content. The value is 205px or 52px and is updated whenever collapse state changes. It is removed when the sidebar unmounts.

### Components

- `router/index.ts`: workspace route metadata only.
- `AppHeader.vue`: route-aware Logo ownership and workspace hairline; top-right controls unchanged.
- `SidebarNav.vue`: full-height fixed rail, flow spacer, brand row, Logo, relocated collapse control, internal left-falling fade, and width variable synchronization.
- `AppFooter.vue`: live-width padding on workspace routes and Home-only top-border removal.

No page business component, API, store, session behavior, auth/demo behavior, or navigation event contract changes.

## Collapse and Responsive Behavior

- Expanded and collapsed widths keep the existing 300ms transition.
- Spacer and fixed rail transition together to prevent the content plane from jumping or overlapping.
- Expanded state shows the 30px-high wordmark and right-aligned collapse control.
- Collapsed state hides the wordmark and centers the collapse control.
- At 390px, the existing header control compaction remains unchanged and horizontal document overflow must remain absent.
- The vertical fade remains 16px wide inside whichever rail width is active.

## Dark Mode

- Preserve the existing dark header and sidebar colors.
- Apply the same foreground-direction rule in dark mode with this internal fade:

```css
linear-gradient(
  90deg,
  rgba(0, 0, 0, 0) 0,
  rgba(0, 0, 0, 0.05) 34%,
  rgba(0, 0, 0, 0.12) 66%,
  rgba(0, 0, 0, 0.2) 100%
)
```

- Do not transfer the light warm canvas into dark mode.

## Testing and Verification

Automated source-contract tests must cover:

- Workspace routes carry `meta.workspaceShell` and non-workspace routes do not.
- The standard header Logo contract remains unchanged for non-workspace routes.
- Workspace header hides its Logo, retains the existing right controls, and uses the scoped hairline.
- Sidebar uses the same Logo source/filter, 30px expanded height, fixed full-height positioning, a matching spacer, the 16px internal fade, and collapsed Logo hiding.
- Footer removes only the workspace top border and consumes `--workspace-sidebar-width`.

Browser QA must cover:

- `/home`, `/projects`, and `/settings` at 1280×720.
- Expanded width 205px and collapsed width 52px.
- Logo x=16 and height 30px in expanded state.
- Top-right controls match pre-change metrics.
- Header rule computes to the thinnest supported rendering for 0.5px and begins visually at the rail edge.
- Vertical fade is contained inside the rail and is darkest at the display boundary.
- No footer rule appears below the Home composer.
- No horizontal overflow at 390px.
- No new browser console errors.
- Focused tests, full `main-app` tests, `git diff --check`, and the production build pass.

## Non-goals

- Recoloring the rail to Codex blue-gray.
- Changing the top-right control styling or behavior.
- Replacing or editing the Logo asset or filter.
- Changing sidebar navigation, session, routing, API, auth, or business logic.
- Redesigning page content, cards, composer, or workspace panels.
- Adding a divider below the Home composer.
