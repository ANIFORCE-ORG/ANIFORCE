# Legacy ANIMAGUS Feature Migration Audit

Date: 2026-05-09

This document records the migration status from the original local system at `/Users/PJlai/Desktop/ANIMAGUS` into the rewritten system at `/Users/PJlai/Desktop/ANIMAGUS_remote`.

## 1. Immediate Fix Completed: Creative Materials

The old system's `creatives` panel was partially rebuilt in the new Vue/FastAPI architecture, but the running system showed a blank creative materials module because the database had no migrated creative rows and the backend image API did not read the new frontend public asset directory.

Completed changes:

- Migrated 24 legacy creative materials into the current SQLite database via `backend/scripts/seed_legacy_creatives.py`.
- Added legacy material performance fields to the backend model and response: `roi`, `spend`, `campaign_id`.
- Made the material repository normalize old SQLite enum names such as `RUNNING` and `FULL_VIDEO` into frontend-safe values such as `running` and `full_video`.
- Fixed `GET /api/v1/materials/images/list` to read both backend-uploaded images and frontend public creative images.
- Fixed `GET /api/v1/materials/{id}/image` to return Base64 images for legacy public creative assets.
- Fixed `POST /api/v1/materials` to accept the frontend JSON body instead of query parameters.
- Added `POST /api/v1/materials/upload` for real file upload into `backend/data/images`.
- Fixed creative feature cards to route to the new AI generation routes:
  - `/material/ai-generate/new`
  - `/material/ai-generate/remix`
  - `/material/ai-generate/hot`
  - `/material/ai-generate/mix`
- Fixed "添加到投放计划" to call `POST /campaigns/{campaign_id}/materials/{material_id}` and refresh materials after success.
- Updated campaign-material linking so it writes both `Campaign.material_ids` and `Material.campaign_ids`.

Verification:

- Backend syntax check passed with `venv/bin/python -m py_compile`.
- Legacy material repository query returns 24 materials for `user_test_001`.
- `GET http://127.0.0.1:8010/api/v1/materials` returns 24 materials.
- `GET http://127.0.0.1:8010/api/v1/materials/images/list` returns public creative images.
- `GET http://127.0.0.1:8010/api/v1/materials/cre_001/image?thumbnail=true` returns JPEG Base64 data.
- `npm exec vite build` passed.
- `npm run build` still fails at `vue-tsc` because of pre-existing global TypeScript baseline issues outside this migration.

Running links:

- Frontend: `http://localhost:3010/`
- Backend health: `http://127.0.0.1:8010/health`
- Creative materials page: `http://localhost:3010/material`

## 2. Page-by-Page Migration Status

| Legacy panel | New route / module | Status | Gaps |
| --- | --- | --- | --- |
| `dashboard.js` | `/dashboard`, `Dashboard.vue`, home workspace components | Partial | KPI and insight display exists, but old alert routing, creative fatigue alert action, and report insight cards are not fully mapped to backend data. |
| `projects.js` | `/projects`, `/projects/:id` | Partial | List/detail exist. Some old project-level campaign/creative aggregation depends on migrated campaign/material relationships and still needs data consistency work. |
| `campaigns.js` | `/campaign`, `/campaigns/create`, `/campaigns/:id` | Partial | New campaign flow exists and has agent-oriented budget/pacing fields. Missing or incomplete: full old wizard parity, old batch operations, and legacy campaign dataset migration. |
| `creatives.js` | `/material` | Restored / Partial | Material library, filtering, upload, add-to-campaign and AI entry routing are restored. Remaining work: real preview/player modal, project selection during upload, better campaign name display, and fatigue workflow actions. |
| `aig-new.js` | `/material/ai-generate/new` | Partial | UI exists. Needs persistence of generated assets into material library and traceable generation task history. |
| `aig-remix.js` | `/material/ai-generate/remix` | Partial | UI exists. Needs source material selection from real material API and generated variant persistence. |
| `aig-hot.js` | `/material/ai-generate/hot` | Partial | UI exists. Needs real hot creative source data, trend tags, and output persistence. |
| `aig-mix.js` | `/material/ai-generate/mix` | Partial | UI exists. Needs real segment selection, mix task execution state, and output persistence. |
| `reports.js` | Sidebar points to `/monitor`; home has `ReportsContent.vue` | Missing route / Partial component | `/monitor` is not registered in router. Need a real reports route or sidebar correction. |
| `settings.js` | No dedicated new route | Missing | Old settings panel has API key/platform/settings actions. Decide whether to rebuild as platform connection settings or move into project/account setup. |
| `chat.js` and old agents | `ChatPanel.vue`, backend chat route | Partial | Chat UI exists, but old intent actions such as list creatives, creative fatigue, create campaign, and report navigation are not fully bound to new APIs/routes. |

## 3. Known Data Model Mismatch

The legacy creative dataset references campaign IDs such as `camp_g001`, `camp_d001`, and `camp_d002`. The current SQLite database only has one campaign row at the time of this audit, so old creative-to-campaign relationships are preserved on the material side but cannot all be reflected into `campaigns.material_ids`.

Recommended approach:

- Migrate the legacy campaign dataset next, or
- Map old campaign IDs to the new campaign records if the new IDs are now canonical.

Do not silently rewrite these IDs without an explicit migration map because that would create misleading campaign-material attribution.

## 4. Development Plan

### Phase 1: Creative Module Completion

Goal: make creative materials fully usable as a daily media buying workspace.

- Add material detail / preview modal with image/video rendering, metrics, tags, related campaigns and action buttons.
- Add project selector and tag input to upload modal, then pass them to `POST /materials/upload`.
- Display associated campaign names in material cards, not only count.
- Add fatigue workflow: filter `fatigue > 5`, mark as fatigue, send to remix, replace in campaign.
- Add delete and edit metadata actions.
- Persist AI generated outputs from all four AI generation pages into `/materials`.

### Phase 2: Campaign Dataset and Link Consistency

Goal: make projects, campaigns, and creatives operate on one coherent migrated dataset.

- Migrate original campaign records or create an explicit old-to-new campaign ID map.
- Add a repair script to synchronize:
  - `materials.campaign_ids`
  - `materials.campaign_id`
  - `campaigns.material_ids`
- Update campaign detail material section to read from backend material API and show creative performance.
- Add batch material assignment from campaign detail and create campaign flow.

### Phase 3: Reports and Agent Actions

Goal: recover the old reporting value while keeping the new agent-native direction.

- Add `/monitor` route or change sidebar to the actual report route.
- Build reports page from backend campaigns, metrics, and materials:
  - spend / revenue / ROI summary
  - creative ranking
  - fatigue warnings
  - project and platform breakdown
- Bind chat quick actions to real navigation and API calls:
  - "查看疲劳素材"
  - "生成二创"
  - "把素材加入计划"
  - "查看预算异常"

### Phase 4: Settings and Platform Connections

Goal: avoid rebuilding old settings as generic admin pages; keep only what supports the agent workflow.

- Rebuild settings as "平台连接与执行权限":
  - Meta / Google / TikTok connection status
  - API credentials health check
  - execution mode: suggest / confirm / auto
  - per-platform action limits
- Move non-critical generic settings out of the MVP.

### Phase 5: TypeScript Baseline Cleanup

Goal: make `npm run build` reliable.

Current `npm exec vite build` passes, but `npm run build` fails because `vue-tsc` catches existing project-wide issues:

- Missing Node type declarations for `vite.config.ts`.
- Several unused variables under strict `noUnusedLocals`.
- Type mismatches in home dashboard numeric comparisons.
- `AIGenerateMix.vue` expects a material `format` property that is not in the API type.
- `AIGenerateNew.vue` has an image/video literal type mismatch.
- `Projects.vue` expects `product_type` as required, but API data can omit it.

These should be fixed as a separate cleanup pass instead of mixed into the creative migration.

## 5. Recommended Next Implementation Order

1. Migrate or map legacy campaigns so creative attribution is real end to end.
2. Finish material detail / preview / edit / delete actions.
3. Persist AI-generated outputs from the four AI pages into the material API.
4. Add `/monitor` reports route and fix sidebar navigation.
5. Clean TypeScript baseline until `npm run build` passes.
