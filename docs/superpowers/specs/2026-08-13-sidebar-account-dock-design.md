# Sidebar Account Dock Design

## Goal

Move the signed-in account controls out of the workspace header and into a persistent account dock at the lower-left of the shared sidebar. Apply the change across all routes using the workspace shell, preserve the current ANIFORCE logo, and keep non-workspace routes functional.

## Selected Approach

Extract the existing account behavior into one reusable account-controls component and render it in two route-aware locations:

- Workspace routes: a compact Codex-style account dock at the bottom of `SidebarNav`.
- Non-workspace routes: the existing right-side placement in `AppHeader`.

This keeps authentication, language switching, notification access, and logout behavior in one component while avoiding a large application-shell rewrite.

## Alternatives Considered

1. **Move the existing header block with CSS positioning.** Smallest diff, but it would remain owned by the header, overlap the sidebar, and behave poorly when the sidebar collapses.
2. **Duplicate the account markup in the header and sidebar.** Visually direct, but creates two independent menus and risks behavior and accessibility drift.
3. **Rebuild the entire application shell around a single global sidebar.** Architecturally clean long-term, but unnecessarily broad for this visual change and likely to disturb page-level navigation layouts.

## Visual Design

### Expanded sidebar

- Anchor the dock below the scrollable navigation at the sidebar's lower-left edge.
- Use the existing warm sidebar canvas and a subtle top hairline; do not add a floating card or new accent color.
- Show a compact circular avatar and the user's name in the primary row, following the reference composition.
- Keep the email, notification control, language selector, and logout action inside a right-opening popover so the 205px rail remains visually quiet.
- Preserve the current font, neutral colors, corner-radius language, and existing ANIFORCE logo without resizing or recoloring it.

### Collapsed sidebar

- Keep only the centered circular avatar at the bottom of the 52px rail.
- Clicking the avatar opens the same account popover to the right of the rail.
- The popover must not be clipped by the sidebar and must remain above the main content and footer.

### Header

- On workspace routes, remove the entire signed-in account/language action group from the top-right header, leaving the existing thin header boundary and height unchanged.
- On non-workspace routes, retain the current header account placement and behavior.

## Component Boundaries

- `AccountControls.vue`: owns avatar/name/email rendering, notification button, language switching, logout menu state, and expanded/collapsed variants.
- `AppHeader.vue`: decides whether the header instance is visible based on `route.meta.workspaceShell`.
- `SidebarNav.vue`: renders the workspace account dock after the scrollable navigation and passes the sidebar collapse state.

No page-level component should duplicate or individually position the account dock.

## Interaction and Accessibility

- The account trigger remains a semantic button with `aria-haspopup`, `aria-expanded`, and a descriptive label in collapsed mode.
- Escape and outside-click close the popover.
- Keyboard focus styles remain visible on the avatar trigger, notification control, language choices, and logout button.
- The notification control retains its current no-op behavior; this task does not add notification business logic.
- Logout and language changes continue to use the existing stores.

## Responsive Behavior

- Desktop workspace routes use the expanded or user-collapsed sidebar behavior described above.
- At existing narrow breakpoints, preserve the current rail width rules and ensure the popover stays within the viewport.
- Moving the account controls must not change content width, footer offset, or the sidebar's right-cast shadow.

## Verification

- Add source-level regression tests confirming workspace header actions are hidden and the account dock is rendered by `SidebarNav`.
- Cover expanded and collapsed variants, shared controls, and preserved non-workspace header rendering.
- Run the complete `main-app` test suite and production build.
- Inspect at least Home and one non-Home workspace route in the browser, plus a non-workspace route, checking popover placement, collapse behavior, no clipping, no horizontal overflow, and no console errors.

## Scope Boundaries

- Do not modify the ANIFORCE logo asset, size, filter, or position.
- Do not change authentication, notification, language, or logout business logic.
- Do not change navigation items, history sessions, footer layout, route metadata, or unrelated user changes.
