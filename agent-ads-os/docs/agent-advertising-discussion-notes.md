# Agent Advertising Discussion Notes

Date: 2026-05-01

Context: Discussion about how advertising changes when every user has multiple agents that search, compare, negotiate, and execute tasks on their behalf. This document captures the strategic direction for a possible ANIFORCE / Agent Ads OS product.

## 1. Core Question

If humans use agents to obtain information and execute decisions, will advertising on traditional media platforms be replaced by agents "watching ads" for users?

The answer is partial replacement, not disappearance.

Advertising will split into two systems:

- Attention Ads: shown to humans, mostly in entertainment, feeds, games, video, social, and brand-building environments.
- Intent Ads: exposed to agents, mostly in high-intent decisions such as software selection, travel, insurance, B2B procurement, services, games UA, and budget allocation.

Low-intent and emotional discovery will still target humans. High-intent, comparison-heavy, and purchase-oriented decisions will increasingly route through user agents.

## 2. How Advertising Logic Changes

Traditional advertising flow:

```text
Audience tags -> Exposure -> Click -> Conversion
```

Agent-era advertising flow:

```text
User intent
-> Agent parses need
-> Advertisers submit structured offers
-> Agent compares, verifies, filters, and negotiates
-> User confirms
-> Conversion/action
```

The core scarce resource changes from attention to recommendation rights inside agent-mediated decisions.

## 3. Future Advertising System

The future system likely has four actors:

1. User-side Agent
   - Represents the user's interest.
   - Knows preferences, budget, purchase history, risk tolerance, privacy constraints, and brand preferences.

2. Advertiser-side Agent
   - Represents the business.
   - Generates offers, proofs, creatives, discounts, commitments, API actions, and campaign strategies.

3. Agent Ad Marketplace / Exchange
   - Matches user intent with advertiser offers.
   - Does not auction simple impressions.
   - Auctions qualified access to the user's decision set.

4. Trust and Verification Layer
   - Verifies claims, evidence, reviews, pricing, refunds, regulatory constraints, and post-purchase risk.

## 4. Agent-Readable Ad Object

Future ads should not only be images, videos, and copy. They should become structured commercial objects.

Example:

```json
{
  "product": "AI ad platform",
  "target_user": "game publishers with monthly ad spend above $100k",
  "price_model": "5%-10% of managed ad spend",
  "proof": ["case studies", "ROAS data", "verified Meta account data"],
  "constraints": ["Meta first", "Google requires developer token", "best fit for high-frequency creative teams"],
  "offer": "pilot campaign with limited budget",
  "creative_assets": ["video", "image", "copy"],
  "api_actions": ["book_demo", "connect_ad_account", "generate_campaign_plan", "launch_test_campaign"]
}
```

In short:

```text
Offer + Evidence + Constraint + Action API + Trust Score
```

## 5. Agent Ad Score

Initial proposed score:

```text
Agent Ad Score =
  User Fit
  x Trust Score
  x Expected Utility
  x Executability
  + Commercial Bid
  - Risk Penalty
```

The important clarification:

The score should primarily serve matching efficiency and user utility. Commercial value is a result, not the first principle. Fairness is a constraint, not the main optimization function.

Recommended system design:

### Layer 1: Eligibility and Trust Filter

Before ranking, an ad/offer must pass eligibility:

```text
Compliant?
Truthful?
Verifiable?
Relevant to user intent?
Clear price / service / constraint?
Executable action available?
```

If it fails this layer, no bid should allow it into the candidate set.

### Layer 2: Utility Ranking

Calculate:

```text
User Utility Score =
  User Fit
  x Trust Score
  x Expected Utility
  x Executability
  - Risk Penalty
```

### Layer 3: Commercial Ranking Within Quality Boundaries

Commercial bid should only influence ranking within a quality band:

```text
Final Rank Score =
  User Utility Score
  + lambda x Bid x Conversion Probability
```

Where `lambda` controls how much bid can affect ranking.

Principle:

```text
Commercial bid can break ties, but cannot buy trust.
```

If `lambda` is too high, the system becomes a traditional ad auction and user agents lose trust. If `lambda` is too low, monetization is weak.

## 6. Build on Google/Meta or Build Something Else?

Recommended answer:

Do not position this as a direct modification of Google/Meta systems. Do not start as a pure SDK company either.

The better path is:

```text
Build an independent Agent-Native Ads OS.
Use Google, Meta, TikTok, AppLovin, Xiaohongshu, official sites, CRM, and app stores as execution/data channels.
```

Google/Meta will not open their core auction and recommendation systems for third-party control. A third party can use their APIs to:

- Create campaigns.
- Create ad sets.
- Create ads.
- Upload creatives.
- Adjust budgets.
- Pull insights.
- Import conversion data.
- Pause or update underperforming campaigns.

This is important, but it is execution-layer integration, not the agent-native protocol layer.

## 7. Recommended Product Architecture

### 7.1 Advertiser Agent Ad Server

Core product.

Turns advertiser data into agent-readable ad assets:

- Product/service descriptions.
- Target users.
- Prices and business model.
- Proof and performance claims.
- Constraints.
- Creative assets.
- Action APIs.
- Compliance and trust evidence.

This should be the heart of the system.

### 7.2 Platform Execution Layer

Continue integrating traditional ad platforms:

- Meta.
- Google.
- TikTok.
- AppLovin.
- Xiaohongshu.
- CRM.
- Analytics and attribution providers.

The role of this layer:

- Push strategies into ad platforms.
- Upload creatives.
- Create campaigns.
- Pull performance data.
- Feed ROAS, CPA, CTR, creative fatigue, and LTV back into the system.

### 7.3 Agent Intent API

Expose offers to user agents.

Example user agent request:

```json
{
  "intent": "Find an AI advertising system for a game publishing team",
  "budget": "monthly ad spend >= 100000 USD",
  "priority": ["lower CAC", "creative generation", "Meta automation"],
  "risk": ["no long-term contract", "need verified case studies"]
}
```

Example response:

```json
{
  "rank": 1,
  "brand": "ANIFORCE",
  "fit_score": 0.91,
  "why": "Strong fit for high-frequency creative testing and Meta automation",
  "proof": ["Meta API verified", "creative fatigue monitoring", "budget automation"],
  "sponsored": true,
  "next_action": "book_demo"
}
```

### 7.4 SDK / MCP / Plugin Layer

SDK should be a distribution and integration layer, not the company identity.

Useful SDK/API surfaces:

- Advertiser website SDK: collect conversion data, detect products/offers, expose agent-readable offers.
- Agent SDK / MCP server: let agents query, compare, and execute advertiser offers.
- Platform connectors: connect Meta, Google, TikTok, CRM, Shopify, Appsflyer, etc.

Recommended initial priority:

```text
Advertiser SDK + Offer API + Platform Connectors
```

Do not rely on consumer agent distribution too early.

## 8. Commercial Model

### Stage 1: Advertiser-Side Tooling

Sell Agent Ads OS to advertisers before trying to run a full exchange.

Revenue:

- SaaS subscription.
- Platform connection fee.
- Creative generation usage fee.
- Managed ad automation service fee.
- Percentage of managed ad spend.

This matches ANIFORCE's current direction and can generate near-term revenue.

### Stage 2: Qualified Intent Monetization

As user-agent queries emerge, charge for qualified agent-side events:

- CPAQ: Cost Per Agent Qualified Query.
- CPAS: Cost Per Agent Shortlist.
- CPAR: Cost Per Agent Recommendation.
- CPA: Cost Per Action.
- Revenue share / transaction commission.

Best likely model:

```text
Base platform fee + qualified recommendation fee + outcome/revenue share
```

### Stage 3: Agent Ad Exchange

Once both advertiser supply and agent demand exist:

```text
User agent submits intent
-> advertiser agents return real-time offers
-> platform verifies, ranks, and prices
-> user agent recommends
-> user confirms
-> platform attributes and charges
```

Revenue:

- Transaction commission.
- Advertiser service fee.
- Trust and verification fee.
- API usage fee.
- Vertical data intelligence fee.

## 9. Will Google/Meta/TikTok Do This?

Yes, they will.

They are already moving toward AI-automated advertising:

- Google Performance Max / AI Max direction: advertisers submit assets and goals; Google automates targeting and placement.
- Meta Advantage+ direction: automation across creative, audiences, placements, and budget.

However, their natural product boundary is platform-internal optimization:

```text
Google optimizes Google traffic.
Meta optimizes Meta traffic.
TikTok optimizes TikTok traffic.
```

The third-party opportunity is:

```text
Neutral, advertiser-side, cross-platform, agent-native growth infrastructure.
```

## 10. Where ANIFORCE Can Build Moats

Do not place the moat in generic creative generation. That will be commoditized by giants and existing tools.

Better moats:

1. Vertical Industry Data
   - Game, short-drama, social, and other high-frequency performance marketing categories.
   - Creative fatigue, ROAS, LTV, platform response curves, audience behavior.

2. Cross-Platform Execution
   - Not only recommending strategy, but creating campaigns, uploading assets, changing budgets, pausing ads, and pulling insights.

3. Agent-Readable Offer Standard
   - Convert ads from media assets into structured, comparable, verifiable, executable commercial objects.

4. Trust and Evidence Graph
   - Verify claims such as "ROAS +20%" using real account data, historical campaign performance, refunds, retention, complaints, and case studies.

5. Outcome Loop
   - Optimize across:

```text
Agent shortlist
-> Agent recommendation
-> User confirmation
-> Transaction
-> Retention
-> LTV
-> Repeat purchase
```

Traditional ad platforms are weaker in cross-platform, advertiser-owned, long-term outcome data.

## 11. ANIFORCE Strategic Path

Short term:

```text
Connect Google / Meta / TikTok.
Automate campaign setup, creative generation, monitoring, and optimization.
Make money from ad automation.
```

Medium term:

```text
Build agent-readable ad assets and cross-platform performance data.
Develop trust/evidence scores and offer APIs.
```

Long term:

```text
Become the advertiser-side entry point and operating system for Agent Ad Exchange.
```

## 12. Recommended Positioning

Avoid:

```text
We are an AI ad creative platform.
```

Use:

```text
We are the advertising operating system for the agent era.
We help advertisers turn products, creatives, offers, proof, and media-buying strategies into agent-readable, verifiable, executable, and optimizable growth assets.
```

## 13. Best Wedge for ANIFORCE

The most natural starting market:

```text
Game / short-drama / high-frequency performance marketing teams
```

Why:

- Creative fatigue is severe.
- High creative volume is required.
- Multiple platforms are hard to manage.
- ROAS and CAC pressure are explicit.
- Existing team workflows are heavy and fragmented.
- Advertisers already pay significant budgets and can justify automation fees.

Path:

```text
Solve human-facing ad automation now.
Simultaneously build agent-readable assets and trust data.
Migrate into agent-native distribution as user agents become common.
```
