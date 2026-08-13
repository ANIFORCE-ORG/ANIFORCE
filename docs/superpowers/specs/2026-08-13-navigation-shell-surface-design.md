# ANIFORCE Unified Navigation Shell Surface Design

**Date:** 2026-08-13

**Status:** Approved through visual option A

**Scope:** Light-theme application header surface and its boundary with the existing sidebar

## Problem

The current header uses pure white (`#FFFFFF`) while the sidebar directly below it uses Notion's warm navigation canvas (`#F7F7F5`). The header also draws a full-width bottom divider. At the left edge this creates a hard horizontal break at 57px: the logo area reads as a separate bar placed above the sidebar instead of the top of one continuous navigation shell.

Measured current state at 1280px:

- Header: 1280px × 57px, `#FFFFFF`, bottom divider `#E9E9E7`.
- Expanded sidebar: 205px wide, `#F7F7F5`, right divider `#E5E3DF`.
- Main content: starts at x=205px and remains white.

## Approved Direction

Use option A, **Unified Navigation Shell**:

- Change the light-theme header canvas to the sidebar canvas color, `#F7F7F5`.
- Remove the header's hard full-width bottom border so the logo area and sidebar join without a horizontal seam.
- Keep the white main content area unchanged. Its color contrast against the warm navigation shell provides the content boundary without an added shadow.
- Keep transitions functional and restrained. The existing color transition may remain, but no gradient, glow, or drop shadow is introduced.
- Preserve the existing dark-theme header treatment unless verification finds an equivalent seam in dark mode.

This direction stays visually stable when the sidebar changes between 205px and 52px because it does not depend on a synchronized split point or new cross-component state.

## Protected Logo Contract

The logo is out of scope. The implementation must not change:

- SVG asset or source path.
- DOM placement or markup.
- `h-10`, width behavior, maximum width, or object-fit classes.
- Blue `logo-blue` filter.
- Current desktop or narrow-screen x/y position.

## Component and Code Scope

Expected production change:

- `frontend/packages/main-app/src/components/AppHeader.vue`

Expected test change:

- `frontend/packages/main-app/src/components/AppHeader.spec.ts`

No change is planned for `SidebarNav.vue`, routing, authentication/demo mode, APIs, business logic, global styles, or logo assets.

## Verification

Automated:

- Add a regression assertion for the approved light header surface and removed hard divider.
- Keep existing logo-contract tests passing.
- Run the focused header test suite.
- Run `git diff --check` and the main-app production build.

Browser visual QA:

- At desktop width, header computed background equals sidebar computed background (`rgb(247, 247, 245)`).
- Header has no visible bottom border or shadow.
- Logo resource, filter, dimensions, and position equal the pre-change measurements.
- Expanded and collapsed sidebar states do not reveal a white strip or hard horizontal seam under the logo area.
- Narrow-screen header continues to fit without overflow.
- No new browser console errors are introduced.

## Non-goals

- Redesigning header controls, sidebar items, or page content.
- Changing the logo in any way.
- Adding decorative gradients, shadows, translucency, or animations.
- Synchronizing header layout with sidebar collapse state.
- Editing existing unrelated local changes.
