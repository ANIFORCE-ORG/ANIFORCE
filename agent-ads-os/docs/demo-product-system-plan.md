# Demo and Product System Plan

Date: 2026-05-01

Purpose: Plan how to validate and develop the ANIFORCE Agent-Native RTC Ad OS demo in phases.

## 1. Product Goal

Build a demo that proves ANIFORCE is not only an AI creative generation tool. It is a workflow system that:

```text
Generates human-facing ads
-> Plans and executes campaigns
-> Monitors performance
-> Optimizes budget and creatives
-> Emits Agent/GEO assets
-> Measures AI/search/agent visibility
```

The demo should make the future thesis visible through current measurable steps.

## 2. Demo Narrative

User story:

```text
A game or short-drama advertiser wants to launch a new campaign.
They enter product info, budget, region, and target CPA/ROAS.
ANIFORCE generates human ad creatives, builds a cross-platform media plan, launches or simulates launch, monitors performance, and simultaneously creates Agent/GEO assets for AI search and future user agents.
```

Main demo promise:

```text
One campaign creates two growth assets:
1. Attention assets for people.
2. Intent assets for agents.
```

## 3. Demo Phases

### Phase 0: Strategy Prototype

Timeline: 1 week

Goal:

Make the concept sellable before full engineering.

Deliverables:

- Updated BP deck.
- Clickable Figma or HTML screens.
- One sample Agent/GEO Asset Pack.
- One before/after visibility report mock.

Validation:

- Can advertisers understand "human ads + agent-readable assets" in less than 5 minutes?
- Do they see GEO/Agent visibility as incremental value, not sci-fi?
- Are they willing to run a pilot?

### Phase 1: Workflow Demo

Timeline: 2-3 weeks

Goal:

Show the full workflow with mock data.

Modules:

- Project setup.
- AI campaign chat / brief intake.
- Creative generation.
- Campaign plan generation.
- Monitoring dashboard.
- Optimization suggestions.
- Agent/GEO Asset Pack output.

Key screens:

- Home / project dashboard.
- AI campaign planner.
- Creative generation page.
- Campaign plan page.
- Monitor dashboard.
- Agent/GEO asset page.
- Visibility report page.

Validation:

- Does the end-to-end flow feel like an AI operator?
- Can a sales call use it without backend dependencies?
- Which step creates the strongest "aha" moment?

### Phase 2: Semi-Real Integration Demo

Timeline: 4-6 weeks

Goal:

Connect selected real APIs where available, keep risky parts in controlled mode.

Real integrations:

- Meta account connection.
- Campaign/account insights pull.
- Creative upload test where safe.
- Campaign creation in paused/draft mode.
- Website/landing page scan.
- Sitemap/robots/schema audit.

Mock or controlled:

- Google full execution until Developer Token is ready.
- TikTok until credentials are approved.
- Live spending.
- Actual automated budget changes.

Validation:

- Can the system pull real ad data?
- Can it generate a credible optimization recommendation from real metrics?
- Can it publish or preview Agent/GEO assets?

### Phase 3: Pilot System

Timeline: 8-12 weeks

Goal:

Run with one real advertiser.

Scope:

- One vertical: game, short drama, or AI marketing SaaS.
- One platform first: Meta.
- One campaign or one product.
- One Agent/GEO asset pack.

Metrics:

- Creative production time.
- Number of variants generated.
- CTR / CPA / ROAS vs baseline.
- Creative fatigue rate.
- Budget optimization actions.
- Crawlability and indexability.
- Prompt mention / citation rate.
- AI/search referral traffic.
- Assisted conversion.

Validation:

- Did advertiser save time or cost?
- Did performance improve enough to justify fee?
- Did Agent/GEO assets produce measurable visibility proxies?

### Phase 4: Repeatable Product

Timeline: 3-6 months

Goal:

Turn pilot workflows into a scalable product.

Add:

- Multi-account support.
- Platform connector abstraction.
- Real-time metrics ingestion.
- Rules engine.
- Offer & Evidence Graph.
- Prompt visibility runner.
- Role/permission system.
- Billing model.

## 4. Product Modules

### 4.1 Project and Advertiser Profile

Stores:

- Advertiser.
- Product/app.
- Region.
- Industry.
- Target audience.
- Budget.
- Target CPA / ROAS.
- Brand constraints.
- Competitors.
- Proof assets.

Why:

This profile powers both human creative generation and Agent/GEO assets.

### 4.2 AI Campaign Planner

Input:

- User prompt.
- Product description.
- Platform selection.
- Budget.
- Goal.
- Region/language.

Output:

- Campaign objective.
- Audience/persona.
- Creative directions.
- Media split.
- Launch plan.
- Expected metrics.

Demo behavior:

- Chat interface plus right-side execution panel.
- Show "thinking" steps: market analysis, creative strategy, media plan, risk checks.

### 4.3 Creative Engine

Features:

- Generate hooks.
- Generate image/video concepts.
- Generate ad copy.
- Generate variant matrix.
- Tag assets by persona, hook, style, CTA, platform, language.
- Estimate CTR / fatigue risk.

Future:

- VLM-based analysis of uploaded winning creatives.
- Segment creative into A/B/C modules for short video.

### 4.4 Campaign Execution Engine

Features:

- Build campaign/adset/ad structure.
- Allocate budget.
- Attach creatives.
- Create draft/paused campaigns through platform APIs.
- Pull insights.
- Update status and budget.

Initial platform priority:

1. Meta.
2. Google.
3. TikTok.
4. AppLovin / Xiaohongshu later.

Safety:

- Default to draft/paused creation.
- Require explicit user confirmation before spend.
- Keep audit logs for every action.

### 4.5 Monitoring and Optimization

Metrics:

- Spend.
- Impressions.
- CTR.
- CPC.
- CPA.
- ROAS.
- Conversion.
- Creative fatigue.
- Budget pacing.

Rules:

- Pause low-ROI creative.
- Shift budget to high-ROI creative.
- Generate replacement creative when fatigue rises.
- Alert if CPA exceeds target.
- Alert if spend pacing deviates.

Output:

- Recommendations.
- Explainable reasoning.
- One-click execution.

### 4.6 Agent/GEO Asset Compiler

Input:

- Campaign brief.
- Product info.
- Creative hooks.
- Offers.
- Claims.
- Proof.
- Target persona.
- Competitors.

Output:

- Landing page.
- FAQ page.
- Comparison page.
- Proof page.
- Offer summary.
- JSON-LD.
- `agent-offer.json`.
- Sitemap entry.
- Tracking URLs.

Position:

This is the bridge between today's paid media automation and future Agent Ads OS.

### 4.7 Agent Visibility Monitor

Features:

- Generate prompt set by persona and intent.
- Run prompt tests manually or via approved APIs/tools.
- Track mention, citation, correctness, and competitor outcomes.
- Monitor crawler hits if hosted pages are controlled.
- Import Search Console / analytics later.

Metrics:

- Agent Visibility Score.
- Citation Share.
- Correct Fact Rate.
- Offer Extraction Rate.
- Competitor Win/Loss.
- AI/Search Referral Traffic.

### 4.8 Offer & Evidence Graph

Entities:

```text
Advertiser
Product
Campaign
Persona
Intent
Claim
Proof
Offer
Constraint
Action
LandingPage
ContentAsset
CrawlerEvent
PromptTest
VisibilitySnapshot
ConversionEvent
```

Rule:

Every claim should link to evidence.

This becomes the future moat because it makes advertising verifiable for agents.

## 5. Technical Architecture

Recommended architecture:

```text
Frontend
Vue app / existing ANIMAGUS UI

Backend
FastAPI services

Data
SQLite for demo, PostgreSQL for production
Object storage for creative assets
Analytics tables for metrics and visibility snapshots

Integrations
Meta Marketing API
Google Ads API
TikTok API
Search Console / analytics later
Crawler and prompt test tools
```

Service modules:

```text
project_service
campaign_planner_service
creative_service
platform_execution_service
monitor_service
geo_asset_service
visibility_monitor_service
offer_graph_service
```

## 6. Data Model Additions

Add or plan these entities:

```text
advertisers
products
creative_assets
campaigns
campaign_metrics
geo_asset_packs
agent_offers
claims
proof_items
visibility_prompts
visibility_runs
visibility_results
crawler_events
optimization_actions
```

Minimum MVP tables:

```text
geo_asset_packs
agent_offers
visibility_prompts
visibility_results
proof_items
```

## 7. First Engineering Sprint

Sprint length: 1-2 weeks

Build:

1. New navigation item: Agent/GEO Assets.
2. Campaign detail tab: Generate Agent-Ready Assets.
3. Mock Agent/GEO asset generation:
   - Landing page preview.
   - FAQ.
   - Comparison.
   - Proof.
   - `agent-offer.json`.
4. GEO readiness checklist.
5. Prompt visibility mock report.
6. Save generated assets to backend.

Definition of done:

- From a campaign, user can click "Generate Agent-Ready Assets".
- System creates a structured offer JSON and page previews.
- Dashboard shows Agent Visibility baseline.
- Sales demo can explain why this matters in under 3 minutes.

## 8. Second Engineering Sprint

Sprint length: 2-3 weeks

Build:

1. Real static publishing for asset pages.
2. Sitemap generation.
3. Basic robots/crawler recommendations.
4. Prompt test set generator.
5. Manual prompt result entry or semi-automated test runner.
6. Claim/proof linking.

Definition of done:

- Demo can publish a campaign asset pack to a local or hosted URL.
- Prompt tests can be recorded and compared over time.
- Each major claim can link to proof.

## 9. Pilot Readiness Checklist

Need before real pilot:

- Clear consent for account connection.
- Draft/paused campaign safety.
- Budget action confirmation.
- Landing page publishing approval.
- Claim/proof review.
- Privacy and data handling statement.
- Baseline metrics collection.
- Weekly report template.

## 10. What Not to Build First

Do not start with:

- Full agent ad exchange.
- Consumer agent SDK.
- Fully automated spend control without human confirmation.
- Over-generalized GEO platform.
- Unsupported claims about guaranteed ChatGPT/Gemini ranking.

Start with:

```text
Agent/GEO Asset Pack attached to paid campaign automation.
```

This is the narrowest bridge from current product to the future thesis.
