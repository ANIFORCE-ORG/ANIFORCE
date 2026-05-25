# ANIFORCE Frontend Collaboration Progress - 2026-05-25

## Branch

- Repository: `ANIFORCE-ORG/ANIFORCE`
- Working branch: `feature/frontend-marketing-home-upgrade`
- Mainline reference: `upstream/master` at `1a01129`
- Verification: `frontend/packages/main-app` passed `npm run build`
- Local preview used today: `http://localhost:3017/`

## Mainline Diff Summary

This branch keeps the mainline frontend structure and adds the current website, first-use workflow, campaign setup, Agent session, and report landing improvements.

### Website and Entry

- Updated the marketing homepage with bilingual CN/EN copy, language switching, refined first-screen feature tags, and a more system-like dashboard preview.
- Updated login behavior for local testing:
  - Demo credentials: `test@animagus.com` / `test123`
  - Demo fallback token includes expiry so the frontend does not immediately log out.
- Logged-in account area in the website header now routes into the product workspace.

### First-use Workflow

- Reworked `/home` into the first advertising workflow setup page.
- Keeps the product workspace three-column layout:
  - Left: `SidebarNav`
  - Middle: onboarding setup flow
  - Right: fixed `ChatPanel`
- Setup steps:
  1. Business project
  2. Platform authorization
  3. Platform account binding
  4. Pre-launch asset checks
  5. Creative readiness
  6. First campaign draft
- Added frontend demo fallback when project/platform/account APIs are unavailable, so the main frontend flow remains testable.

### Campaign Creation Flow

- Reworked `/campaigns/create` into a fixed three-column business flow with right-side Agent always visible.
- Added platform account selection and validation before campaign draft creation.
- If project list is empty, `SelectGroupModal` offers a Demo project path so the user can continue testing.
- If platform-account API is unavailable, the page creates a Demo account for frontend flow testing.
- Step navigation now scrolls the middle content panel to the top after `next` or `previous`; it no longer scrolls the browser window incorrectly.
- Material selection no longer blocks draft creation. If the material library is empty, `SelectMaterialModal` links to the creative module.
- Creative module supports a return path back to campaign creation when opened from the campaign flow.

### Agent Session Logic

- Added `useWorkspaceSessions` as the shared business Agent session source.
- Business pages now use one global Agent session list instead of separate cached sessions per primary nav entry.
- Updated pages:
  - `/home`
  - `/dashboard`
  - `/projects`
  - `/projects/:id`
  - `/campaign`
  - `/campaigns/:id`
  - `/campaigns/create`
  - `/material`
  - `/monitor`
- Settings pages remain an exception and do not use business workflow history sessions.

### Data Reports

- Replaced the empty `/monitor` entry with a practical report landing page:
  - Core metrics
  - Platform performance table
  - AI strategy insights
  - Creative performance ranking
- Uses static/demo data until backend report APIs are ready.

### UI Consistency

- Tightened operational UI density across the main workflow:
  - Smaller headings inside panels
  - `rounded-md` cards/buttons
  - Buttons marked `whitespace-nowrap` where text wrapping was causing layout issues
  - Dashboard alert actions use icon-style controls
- Preserved the three-column product workspace pattern for business pages.

## Important Local Files

- Website: `frontend/packages/main-app/src/pages/MarketingHome.vue`
- First-use setup: `frontend/packages/main-app/src/pages/Home.vue`
- Campaign create: `frontend/packages/main-app/src/pages/campaigns/CreateCampaign.vue`
- Campaign material picker: `frontend/packages/main-app/src/components/campaigns/SelectMaterialModal.vue`
- Project picker: `frontend/packages/main-app/src/components/campaigns/SelectGroupModal.vue`
- Reports: `frontend/packages/main-app/src/pages/Monitor.vue`
- Creative module: `frontend/packages/main-app/src/pages/creatives/Material.vue`
- Shared Agent sessions: `frontend/packages/main-app/src/composables/useWorkspaceSessions.ts`
- Platform account frontend API: `frontend/packages/main-app/src/api/platformAccounts.ts`

## How To Continue Next Time

1. Pull and switch to the branch:

   ```bash
   git fetch aniforce-org
   git switch feature/frontend-marketing-home-upgrade
   git pull --rebase aniforce-org feature/frontend-marketing-home-upgrade
   ```

2. Start frontend locally:

   ```bash
   cd frontend/packages/main-app
   npm run dev -- --host 0.0.0.0 --port 3016
   ```

   If `3016` is occupied, Vite will choose the next available port.

3. First pages to verify:

   - Website: `/`
   - Login: `/login`
   - First-use setup: `/home`
   - Campaign list: `/campaign`
   - Campaign creation: `/campaigns/create`
   - Creative module: `/material`
   - Reports: `/monitor`

4. Continue product development in this order:

   - Make the first-use setup flow use real backend project, platform authorization, and account binding.
   - Replace campaign creation Demo fallback with real draft creation using platform-account metadata.
   - Implement real material upload/create APIs and refresh the material picker after returning from creative creation.
   - Replace `/monitor` static report data with backend report metrics.
   - Continue UI consistency pass for deeper second/third-level pages as backend data contracts stabilize.

## API And Backend Collaboration Requirements

The frontend currently keeps demo fallbacks where backend APIs are missing or unstable. These should be replaced by real APIs for production.

### Platform Authorization And Accounts

Required endpoints:

- `GET /platform-auth/connections`
  - Return all platform connections.
  - Existing frontend type: `PlatformConnectionResponse[]`.
- `POST /platform-auth/meta/config`
- `GET /platform-auth/meta/config`
- `GET /platform-auth/meta/authorize_url/:connectionId`
- `POST /platform-auth/google/config`
- `GET /platform-auth/google/config`
- `GET /platform-auth/google/authorize_url/:connectionId`
- `DELETE /platform-auth/connections/:connectionId`

Additional account endpoints required by the frontend:

- `GET /platform-accounts?platform=meta&status=active`
  - Return either `PlatformAccount[]` or `{ accounts: PlatformAccount[] }`.
  - Required fields:
    - `id`
    - `platform`
    - `account_id`
    - `account_name`
    - `business_name`
    - `auth_status`
    - `account_status`
    - `currency`
    - `timezone`
    - `last_sync_at`
- `POST /platform-accounts/sync`
  - Body: `{ platform: string }`
  - Sync authorized ad accounts from the platform.
- `POST /projects/:projectId/platform-accounts`
  - Body: `{ platform_account_id: string }`
  - Bind a platform account to a business project.

Recommended additions:

- `GET /projects/:projectId/platform-accounts`
- `DELETE /projects/:projectId/platform-accounts/:platformAccountId`
- Asset readiness endpoint for publishing checks:
  - `GET /platform-accounts/:platformAccountId/assets`
  - Should include Page, IG account, Pixel/Dataset, App, payment/currency/timezone readiness.

### Campaign Draft Creation

Current frontend call:

- `POST /campaigns`
  - Existing body:
    - `project_id`
    - `name`
    - `platform`
    - `budget`
    - `status`
    - `material_ids`

Required additions for real platform-aware draft creation:

- Accept `platform_account_id`.
- Accept objective, budget type, bid strategy, target CPA/ROAS, start/end date, regions, age range, gender, interests.
- Persist draft status separately from publish status.
- Return created campaign with:
  - `id`
  - `project_id`
  - `platform`
  - `platform_account_id`
  - `status`
  - `config`
  - `material_ids`
  - `created_at`
  - `updated_at`

Publishing can remain a later endpoint, but the draft must be stable first.

### Materials

Current frontend APIs:

- `GET /materials`
- `GET /materials/:id`
- `GET /materials/:id/image?thumbnail=true`
- `POST /materials`
- `POST /materials/:materialId/projects/:projectId`
- `DELETE /materials/:materialId/projects/:projectId`
- `DELETE /materials/:id`

Required for the current UX:

- Real upload endpoint for image/video files.
- Real create/generate endpoint for AI material creation.
- Refreshable material list after upload/create.
- Material response should include:
  - `id`
  - `name`
  - `type`
  - `status`
  - `url`
  - `thumbnail_url`
  - `project_ids`
  - `campaign_ids`
  - `tags`
  - `duration`
  - `file_size`
  - `ctr_estimate`
  - `created_at`

### Reports And Metrics

`/monitor` currently uses frontend static/demo data.

Required report endpoints:

- `GET /reports/overview?range=7d&platform=all`
- `GET /reports/platforms?range=7d`
- `GET /reports/creatives?range=7d&sort=roas`
- `GET /reports/insights?range=7d`

Metrics should include spend, impressions, clicks, CTR, installs/conversions, CPI/CPA, ROAS, budget pacing, fatigue signals, and anomaly alerts.

### Agent Sessions

Frontend currently has one global business Agent session list in local storage and passes only `sessionId` into `ChatPanel`.

Backend alignment needed:

- `GET /agent/sessions`
- `POST /agent/sessions`
- `GET /agent/sessions/:sessionId`
- `POST /agent/sessions/:sessionId/messages`
- Optional: rename/delete sessions.

The product rule is: Agent history is tied to the right-side Agent, not to first-level nav entries.

## Known Frontend Demo Fallbacks To Remove Later

- Demo project fallback in first-use setup and project picker.
- Demo platform account fallback when `/platform-accounts` is unavailable.
- Static report data in `/monitor`.
- Demo login fallback for local testing.

These are intentional for frontend validation only and should be removed or gated before production release.
