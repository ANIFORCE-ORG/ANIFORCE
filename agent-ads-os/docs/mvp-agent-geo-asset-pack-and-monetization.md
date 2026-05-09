# MVP: Agent/GEO Asset Pack and Monetization

Date: 2026-05-01

Purpose: Expand the minimum viable feature direction for ANIFORCE Agent Ads OS. This document defines what the demo should do, how to validate it, and how it can become ARR and future agent-ad monetization.

## 1. MVP Definition

The MVP should be:

```text
Agent/GEO Asset Pack
```

It is not a standalone "GEO tool" at first. It is an add-on module attached to the existing campaign creation workflow.

Core promise:

```text
When ANIFORCE generates a paid campaign for humans, it also generates an agent-readable asset pack:
landing page, FAQ, comparison page, proof page, structured offer JSON, schema, tracking, and AI visibility report.
```

Why this is the right MVP:

- It connects directly to the current ad automation system.
- It gives advertisers near-term value: better landing pages, clearer offers, content reuse, AI-search visibility monitoring.
- It creates the data foundation for future Agent Ads OS.
- It can be charged as an ARR add-on before the true agent ad exchange exists.

## 2. Demo Goal

The demo needs to make one idea obvious:

```text
One campaign now creates two growth assets:
1. Human-facing ads for attention and conversion.
2. Agent-readable assets for AI search, chatbot answers, and future user-agent decisions.
```

Do not demo "future agents will definitely recommend you." Demo measurable intermediate steps:

- Can the offer be understood by an LLM?
- Can claims be extracted correctly?
- Can proof be linked to claims?
- Can AI-search-style prompts mention or cite the brand?
- Can the campaign asset pack be monitored over time?

## 3. Demo Storyline

Recommended vertical:

```text
Game or short-drama advertiser launching a campaign in the US market.
```

Demo flow:

```text
1. User inputs campaign brief.
2. ANIFORCE generates human-facing ad creatives.
3. ANIFORCE generates a platform campaign plan.
4. User clicks "Generate Agent-Ready Assets".
5. System creates Agent/GEO Asset Pack.
6. System runs readiness checks and prompt tests.
7. Dashboard shows before/after visibility and conversion-readiness report.
```

The key "aha" moment:

```text
The same ad strategy that creates videos and Meta/TikTok campaigns also creates a structured offer that Chatbot/AI Search can understand.
```

## 4. Demo Screens

### Screen 1: Campaign Brief

Fields:

- Product/app name.
- Category.
- Target region.
- Target audience.
- Budget.
- Target CPA/ROAS.
- Main offer.
- Competitors.
- Existing landing page.
- Proof/case materials.

Demo copy:

```text
Launch a US campaign for a short-drama app targeting female users 25-44 with a target CPA below $18.
```

### Screen 2: Human Creative Plan

Show:

- 3-5 creative directions.
- Hook examples.
- Persona match.
- Suggested platforms.
- Expected CTR / CPA estimate.
- Generated image/video placeholders.

Purpose:

Keep continuity with the existing ANIFORCE BP: this is still a paid media automation product.

### Screen 3: Campaign Plan

Show:

- Meta/TikTok/Google split.
- Budget allocation.
- Ad group structure.
- Creative-to-persona mapping.
- Launch checklist.
- Optimization rules.

MVP can use mock data, but the UI should look like it can execute through APIs.

### Screen 4: Generate Agent-Ready Assets

Button:

```text
Generate Agent/GEO Asset Pack
```

Progress steps:

```text
Extracting offer
Mapping claims to proof
Generating FAQ
Generating comparison page
Generating structured offer JSON
Checking crawlability
Creating prompt test set
```

### Screen 5: Asset Pack Preview

Tabs:

- Landing page.
- FAQ.
- Comparison.
- Proof page.
- `agent-offer.json`.
- JSON-LD/schema.
- Sitemap entry.

The most important preview is `agent-offer.json`.

Example:

```json
{
  "brand": "DramaWave",
  "category": "short drama app",
  "offer": "Unlimited short drama episodes with personalized recommendations",
  "target_persona": "US female users aged 25-44 interested in romance and suspense stories",
  "proof": [
    {
      "claim": "High completion rate on romance episodes",
      "evidence_url": "https://example.com/proof/dramawave-romance-retention"
    }
  ],
  "constraints": {
    "region": ["US"],
    "platforms": ["iOS", "Android"],
    "pricing": "Freemium with in-app purchases"
  },
  "actions": [
    {
      "type": "install_app",
      "url": "https://example.com/install"
    }
  ]
}
```

### Screen 6: GEO Readiness Score

Score dimensions:

```text
Crawlability
Offer clarity
Structured data consistency
Proof coverage
FAQ completeness
Comparison readiness
Action executability
Tracking readiness
```

Output:

```text
GEO Readiness: 78/100
Agent Offer Score: 84/100
Proof Coverage: 62/100
Recommended fixes: add pricing clarity, add independent proof, expand competitor comparison.
```

### Screen 7: Prompt Visibility Report

Show 20-50 test prompts:

- "Best short drama apps for romance stories in the US"
- "Which app should I use for quick romance episodes?"
- "Compare DramaWave vs ReelShort alternatives"
- "What short drama app has good suspense and romance content?"

For each prompt:

- Mentioned or not.
- Cited source.
- Position among competitors.
- Facts extracted correctly or incorrectly.
- Recommended content/offer fix.

Demo can begin with simulated results, then evolve to semi-real prompt testing.

### Screen 8: Business Impact Summary

Show:

```text
Human campaign assets:
12 creatives, 3 personas, 2 platform plans.

Agent/GEO assets:
1 landing page, 1 FAQ, 1 comparison page, 1 proof page, 1 structured offer API, 30 prompts monitored.

Expected impact:
Better landing-page clarity
More AI-search discoverability
Reusable proof and offer assets
Foundation for future agent recommendation
```

## 5. System Modules

### Module 1: Brief-to-Offer Extractor

Input:

- Campaign brief.
- Product profile.
- Existing landing page.
- Creative hooks.
- Proof files.

Output:

- Offer.
- Target persona.
- Claims.
- Constraints.
- Actions.
- Competitors.

### Module 2: Claim-Proof Mapper

Goal:

Every claim should be linked to proof.

Data structure:

```text
Claim
- text
- type: performance / pricing / feature / audience / compliance
- proof_status: missing / weak / verified
- proof_item_ids
- risk_level
```

### Module 3: Asset Generator

Generates:

- Landing page copy.
- FAQ.
- Comparison page.
- Proof page.
- Structured offer JSON.
- JSON-LD.
- Sitemap entry.

### Module 4: GEO Readiness Checker

Checks:

- Is content visible in HTML?
- Is page indexable?
- Are canonical URLs correct?
- Is structured data valid?
- Is sitemap present?
- Are key facts consistent across page and JSON?
- Is the offer unambiguous?

### Module 5: Prompt Set Generator

Generates prompts across five intent types:

```text
Category discovery
Problem/solution
Competitor comparison
Budget/pricing fit
Action intent
```

### Module 6: Visibility Monitor

Tracks:

- Mention rate.
- Citation rate.
- Correct fact rate.
- Competitor win/loss.
- Offer extraction rate.
- AI/search referral traffic.

Initial implementation can support manual or semi-automated prompt result entry. Full automation can come later.

## 6. Data Model for MVP

Minimum tables or collections:

```text
geo_asset_packs
agent_offers
claims
proof_items
geo_pages
visibility_prompts
visibility_runs
visibility_results
geo_readiness_checks
```

Suggested fields:

```text
geo_asset_packs
- id
- campaign_id
- advertiser_id
- status
- landing_page_url
- offer_json_url
- readiness_score
- offer_score
- created_at
- updated_at

agent_offers
- id
- asset_pack_id
- brand
- category
- offer
- target_persona
- constraints_json
- actions_json
- proof_json

claims
- id
- asset_pack_id
- text
- claim_type
- proof_status
- risk_level

proof_items
- id
- advertiser_id
- title
- url
- proof_type
- verification_status

visibility_prompts
- id
- asset_pack_id
- prompt
- intent_type
- region
- language

visibility_results
- id
- prompt_id
- model_or_engine
- mentioned
- cited
- rank
- facts_correct
- competitors_json
- raw_response
- created_at
```

## 7. Scoring

### GEO Readiness Score

```text
GEO Readiness =
  20% crawlability
  15% HTML text availability
  15% structured data consistency
  15% offer clarity
  15% proof coverage
  10% action executability
  10% tracking readiness
```

### Agent Offer Score

```text
Agent Offer Score =
  persona fit
  x evidence strength
  x constraint transparency
  x action executability
  - ambiguity/risk penalty
```

### Visibility Score

```text
Visibility Score =
  30% mention rate
  25% citation rate
  20% correct fact rate
  15% competitor win rate
  10% action path availability
```

The score should be explainable. Advertisers need to see exactly what to fix.

## 8. Build Plan

### Sprint 1: Mock Demo

Timeline: 1-2 weeks

Build:

- "Generate Agent/GEO Asset Pack" button.
- Asset pack preview.
- Static `agent-offer.json` generator.
- GEO readiness score mock.
- Prompt visibility report mock.

Goal:

Make sales narrative and investor demo work.

### Sprint 2: Saved Asset Packs

Timeline: 2-3 weeks

Build:

- Backend models for asset packs, offers, claims, proof, prompts.
- Save generated assets.
- Connect asset pack to campaign.
- Export JSON and markdown/HTML previews.

Goal:

Make the feature persistent and reviewable.

### Sprint 3: Static Publishing and Checks

Timeline: 3-4 weeks

Build:

- Publish pages to local or hosted static route.
- Generate sitemap entry.
- Basic schema validation.
- Basic crawlability checker.
- Prompt set generator.

Goal:

Move from mock output to technical validation.

### Sprint 4: Semi-Real Visibility Testing

Timeline: 4-6 weeks

Build:

- Prompt run workflow.
- Manual or API-assisted result capture.
- Mention/citation/correctness scoring.
- Compare asset pack before/after.
- Weekly report export.

Goal:

Prove measurable GEO/agent visibility proxies.

### Sprint 5: Pilot

Timeline: 8-12 weeks

Build:

- One real advertiser.
- One real campaign.
- Real asset pack.
- Baseline vs optimized report.
- Connect paid media performance with agent/GEO visibility.

Goal:

Validate willingness to pay and ARR packaging.

## 9. Commercialization Strategy

The MVP should be sold in three layers.

### Layer 1: ARR Add-On to Paid Media Automation

This is the first commercial path.

Package name:

```text
Agent/GEO Asset Pack
```

What customer buys:

- For every campaign, ANIFORCE generates agent-readable assets.
- Monthly monitoring of AI-search visibility.
- Recommendations to improve answer inclusion, citations, and offer clarity.

Why it fits ARR:

- Recurring monitoring.
- Recurring prompt tracking.
- Recurring content refresh.
- Recurring campaign asset generation.
- Clear monthly reporting.

Pricing structure:

```text
Base platform subscription
+ Agent/GEO module
+ prompt/model tracking usage
+ asset pack generation usage
+ optional managed service
```

### Layer 2: Managed Service / Hybrid Fee

For game and short-drama teams, pure self-serve may be too early.

Recommended package:

```text
Monthly platform fee
+ managed campaign/GEO operation fee
+ optional percentage of managed ad spend or uplift
```

This matches how performance advertisers already buy services.

### Layer 3: Future Agent Recommendation Fee

This comes later, after agent-side demand exists.

Potential pricing:

- CPAQ: cost per qualified agent query.
- CPAS: cost per agent shortlist.
- CPAR: cost per agent recommendation.
- CPA: cost per user action.
- Revenue share / transaction commission.

Do not sell this first. Use it as the long-term upside in BP.

## 10. Suggested Pricing

Pricing should be anchored above generic creative tools and below full managed agency retainers.

### Pilot Package

For first 3-5 design partners.

```text
Setup fee: RMB 30k-100k or USD 5k-15k
Monthly fee: RMB 10k-30k or USD 2k-5k
Term: 2-3 months
Includes: 1-3 campaigns, 1 asset pack per campaign, 30-100 prompts monitored, monthly report.
```

Goal:

Validate willingness to pay and customer language.

### Growth ARR Package

For small but serious advertisers.

```text
USD 3k-8k / month
Includes:
- 3-5 campaigns / month
- 3-5 Agent/GEO asset packs
- 100-300 prompts
- 3-5 AI/search engines or models
- weekly visibility report
- basic platform integrations
```

### Scale ARR Package

For high-frequency teams.

```text
USD 10k-30k / month
Includes:
- 10-30 campaigns / month
- multi-brand / multi-region
- 500-2000 prompts
- API access
- proof/evidence graph
- custom dashboard
- dedicated success support
```

### Enterprise / Managed Growth

For large game/short-drama publishers.

```text
Custom monthly retainer
+ 1%-3% of managed ad spend for automation
or 5%-10% AI Agent service fee if ANIFORCE operates the full growth workflow.
```

Use carefully. If performance responsibility is high, include minimum platform fee plus upside rather than relying only on revenue share.

## 11. ARR Model Examples

### Conservative Year-1 ARR

```text
10 pilot customers x USD 3k MRR = USD 30k MRR
ARR = USD 360k
```

### Strong Early PMF

```text
20 customers x USD 6k MRR = USD 120k MRR
ARR = USD 1.44M
```

### Vertical Scale

```text
50 customers x USD 10k MRR = USD 500k MRR
ARR = USD 6M
```

### Enterprise Upside

```text
10 enterprise customers x USD 25k MRR = USD 250k MRR
ARR = USD 3M
plus managed service / ad spend fee
```

Important:

ARR should come from recurring platform + monitoring + asset generation. Performance fees should be treated as expansion revenue, not the only core revenue.

## 12. How This Compares to Existing Markets

Market signals:

- AI creative tools charge subscription plus credits and brand/user limits.
- AI search visibility tools often charge based on prompts, models, projects, tracking frequency, and reporting.
- Free AI visibility graders are used as lead-generation tools.

ANIFORCE should combine these:

```text
Creative generation subscription
+ campaign automation fee
+ agent/GEO visibility monitoring
+ asset pack generation usage
+ managed performance upside
```

This is stronger than a pure GEO tool because it ties AI visibility to paid media and conversion data.

## 13. Sales Narrative

Do not lead with:

```text
We help you rank in ChatGPT.
```

Lead with:

```text
Your paid campaigns already create the best hooks, offers, proof, and personas.
We turn those into durable Agent/GEO assets so AI search and future user agents can understand, verify, compare, and act on your product.
```

Then show:

```text
Before:
- Ads disappear when budget stops.
- Landing page is not structured.
- Claims are not linked to proof.
- AI answers may ignore or misrepresent the brand.

After:
- Every campaign leaves reusable assets.
- Offer is machine-readable.
- Proof is structured.
- AI visibility can be monitored and improved.
```

## 14. KPI Framework

### Product KPIs

- Asset packs generated.
- Average readiness score.
- Proof coverage.
- Prompt sets monitored.
- Correct fact rate.
- Citation/share-of-answer rate.

### Customer KPIs

- Creative production time saved.
- Landing page conversion lift.
- AI/search referral traffic.
- Assisted conversion.
- Cost per asset pack.
- Campaign performance lift.

### Business KPIs

- Pilot conversion rate.
- Average MRR.
- Gross retention.
- Net revenue retention.
- Expansion from base automation to Agent/GEO module.
- Prompt/asset usage expansion.

## 15. What to Build First in Existing Demo

The first product slice:

```text
Campaign Detail -> Agent/GEO Asset Pack tab
```

Inside the tab:

1. Generate Agent-Ready Assets.
2. Preview pages and JSON.
3. Show GEO Readiness Score.
4. Show Prompt Visibility Baseline.
5. Export report.

Minimum backend:

1. Save asset pack.
2. Save agent offer JSON.
3. Save prompt list.
4. Save mock or manual visibility results.

This is enough to support sales demos, investor demos, and early pilot conversations.

## 16. Key Risk and Messaging Guardrails

Avoid unsupported claims:

- Guaranteed ChatGPT ranking.
- Guaranteed Gemini/GPT inclusion.
- Guaranteed AI answer citation.
- Full replacement of Google/Meta ads.

Use defensible claims:

- Make offers easier for AI systems to parse.
- Improve crawlability and structured content.
- Monitor AI-search visibility and competitor presence.
- Link claims to proof.
- Turn paid campaigns into reusable agent-readable assets.

## 17. Recommended Next Step

Engineering:

```text
Build the Campaign Detail -> Agent/GEO Asset Pack tab.
```

Sales:

```text
Offer 3 design partners a paid pilot:
RMB 30k-100k setup + RMB 10k-30k/month for 2-3 months.
```

Investor narrative:

```text
This begins as an ARR add-on for high-frequency paid media teams and compounds into the advertiser-side infrastructure for agent-native advertising.
```
