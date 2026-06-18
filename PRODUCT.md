# ANIMAGUS Product Context

## What we're building
AI-driven game marketing platform for global campaigns. Users create projects, generate ad materials, launch multi-channel campaigns, and track performance.

## Register
**product** — dashboard / tool interface. Design serves the product.

## Core surfaces
- **Home** — AI chat interface for campaign planning + quick tool access
- **Projects** — project list + detail views
- **Campaign** — ad campaign management + creation flow
- **Materials** — AI-generated creative assets (video, images, copy)
- **Agent Chat** — conversational AI assistant for campaign planning (newly migrated)

## User context
Marketing teams & solo advertisers managing game launches. Desktop-first (campaign setup needs space), mobile for monitoring.

## Tech stack
- Vue 3.4 + TypeScript
- Tailwind CSS 3.4
- Pinia state management
- FastAPI backend + Claude Agent SDK (in migration)

## Design constraints
- Brand primary: `#137fec` (blue)
- Dark mode support required (`darkMode: 'class'`)
- Existing components use Material Symbols icons
- Agent chat components use custom styles (not Tailwind-first)

## Current state
- Main app shell: working, Tailwind-based
- Agent chat UI: just migrated from another branch, uses scoped CSS
- Backend: migrating from OpenAI SDK to Claude SDK + AG-UI protocol

## Known issues
- Agent chat components don't match main app design language
- Inconsistent spacing/typography between main app (Tailwind) and agent components (custom CSS)
- Color system fragmentation (Tailwind tokens vs CSS variables in agent components)
