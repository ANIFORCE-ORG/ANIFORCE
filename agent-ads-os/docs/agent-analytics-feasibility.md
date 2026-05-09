# Agent Analytics Feasibility

Date: 2026-05-06

Purpose: Analyze the feasibility, workload, cost, and technical barriers for building a Profound Agent Analytics-like feature that monitors what AI agents crawl and retrieve.

## 1. Key Distinction

There are two different products people may mean by "monitor what AI agents are searching and crawling."

### Observable: AI Agents Visiting Your Own Site

This is feasible.

You can monitor:

- Which AI crawlers/agents request your pages.
- Which pages they access.
- Frequency and trend.
- User-agent and organization classification.
- Crawl status: indexed/crawled/blocked.
- Referrals from AI search/chat products.
- Whether pages later appear in AI answers via prompt/citation testing.

This is what products like Profound Agent Analytics primarily do: infrastructure-level monitoring from CDN/server logs instead of JavaScript analytics.

### Not Directly Observable: What AI Agents Search Across the Whole Web

This is not directly observable unless you own the agent, browser, search product, or proxy layer.

You cannot know all questions users asked ChatGPT, Gemini, Claude, or Perplexity. You can only infer demand through:

- Your own server/CDN logs.
- AI referral traffic.
- Prompt monitoring.
- Citation tracking.
- Search Console / Bing Webmaster / IndexNow signals.
- Third-party panels or partnerships.

Therefore, the product should be positioned as:

```text
Agent traffic and AI visibility analytics for your owned digital presence.
```

Not:

```text
We know everything AI agents search on the internet.
```

## 2. What Profound-Like Agent Analytics Usually Includes

Based on public product materials, the category includes:

- Server/CDN log-based AI crawler tracking.
- AI bot classification.
- Page-level crawler activity.
- Technical crawlability/indexability analysis.
- Real-time monitoring.
- Attribution from AI-driven search to human visits.
- Content performance tracking.
- Citation/answer monitoring.
- Integrations with Vercel, Cloudflare, CloudFront, Fastly, Netlify, Akamai, or custom logs.

The key technical premise:

```text
Traditional web analytics rely on browser JavaScript and cookies.
AI bots rarely execute JavaScript.
Therefore agent analytics must read CDN/server-side request logs.
```

## 3. MVP Scope

Recommended MVP:

```text
AI Agent Traffic Monitor for Owned Sites
```

Minimum features:

1. Log ingestion.
2. AI crawler detection.
3. Daily dashboard.
4. Page-level crawl report.
5. Agent organization breakdown.
6. Blocked/indexable page check.
7. Basic AI referral tracking.
8. Exportable weekly report.

Do not start with full citation attribution or global AI search intelligence.

## 4. Data Sources

### Server/CDN Logs

Best first integrations:

1. Vercel logs.
2. Cloudflare Logpush / Worker.
3. AWS CloudFront logs.
4. Netlify / Fastly later.
5. Custom Nginx logs for manual upload.

Minimum log fields:

```text
timestamp
host
path
method
status_code
user_agent
ip
referer
country
bytes
cache_status
request_id
```

### Bot Registry

Need a registry of known agents:

```text
OpenAI: GPTBot, OAI-SearchBot, ChatGPT-User, OAI-AdsBot
Anthropic: ClaudeBot, Claude-User
Perplexity: PerplexityBot
Google: Googlebot, Google-Extended, Gemini-related crawlers where identifiable
Microsoft: Bingbot, Copilot/Bing-related traffic
Meta, Apple, Mistral, Common Crawl, and others
```

Important:

User-agent alone is not enough because it can be spoofed. Production-grade detection should include reverse DNS/IP verification where available.

### Referrals

Track referrers from:

```text
chatgpt.com
perplexity.ai
copilot.microsoft.com
gemini.google.com
google.com AI/Search surfaces when identifiable
claude.ai where applicable
```

Referral tracking is noisy but useful for business reporting.

### Prompt/Citation Tests

To connect crawls to "AI answers", run synthetic prompts:

```text
Best X software for Y
X alternatives
X vs Y
How to solve Z
Which vendor should I choose for W
```

Record:

- Mentioned or not.
- Cited or not.
- Source URL.
- Rank/order.
- Correct facts.
- Competitors.

## 5. Product Levels

### Level 1: Basic Log Analytics

What it answers:

```text
Which AI bots visited my site yesterday?
Which pages did they read?
Which pages are never crawled?
Is traffic rising or falling?
```

Difficulty: low to medium.

### Level 2: Verified Bot Classification

Adds:

- Bot registry.
- Reverse DNS / IP verification.
- Bot family classification.
- Spoofing detection.
- Crawl type inference.

Difficulty: medium.

### Level 3: AI Visibility and Citation Connection

Adds:

- Prompt tests.
- Citation tracking.
- Mention/citation/correctness scores.
- Competitor visibility.

Difficulty: medium to high.

### Level 4: Business Attribution

Adds:

- AI referral sessions.
- Conversion tracking.
- Assisted conversion.
- CRM/source matching.
- Campaign-to-Agent/GEO asset attribution.

Difficulty: high.

### Level 5: Optimization and Automation

Adds:

- Content gap detection.
- Recommended fixes.
- Auto-generation of Agent/GEO assets.
- Alerts when agents stop crawling important pages.
- Submit/update signals to index systems where supported.

Difficulty: high.

## 6. Workload Estimate

### Prototype: 1-2 Weeks

Team:

- 1 full-stack engineer.
- 1 product/marketing person for bot taxonomy and report design.

Build:

- Manual log upload or one integration.
- AI bot user-agent matching.
- Daily summary table.
- Top crawled pages.
- Agent breakdown.
- CSV export.

This is enough for an internal demo.

### MVP Beta: 4-6 Weeks

Team:

- 1 backend engineer.
- 1 frontend engineer.
- 0.5 data engineer.
- 0.5 product/PM.

Build:

- Cloudflare or Vercel integration.
- Log ingestion pipeline.
- Bot registry.
- Dashboard.
- Page-level reports.
- Basic alerts.
- AI referral tracking.
- Simple readiness scoring.

This is enough for 3-5 design partners.

### Commercial v1: 8-12 Weeks

Team:

- 2 backend/data engineers.
- 1 frontend engineer.
- 1 product/PM.
- 1 GTM/solutions person.

Build:

- Multiple integrations.
- Verified bot classification.
- Tenant/account management.
- Historical trends.
- Weekly reports.
- Prompt/citation monitoring.
- Exportable customer reports.
- Basic billing gates.

This is enough to sell as ARR add-on.

### Profound-Like Enterprise Platform: 6-12 Months

Team:

- 4-8 engineers across backend/data/frontend/integrations.
- 1-2 product/GTM.
- Security/compliance support.

Build:

- Many CDN/server integrations.
- High-volume log processing.
- Bot verification and taxonomy.
- Prompt/citation intelligence.
- Attribution.
- Role-based access.
- SSO.
- SOC2-style security posture.
- Enterprise reporting and alerts.

## 7. Cost Estimate

Costs depend mainly on log volume and prompt/citation tests.

### Small Site

Traffic:

```text
< 1M requests/month
```

Infra:

```text
USD 50-300/month
```

Includes:

- Basic ingestion.
- Database.
- Dashboard.
- Light storage.

### Medium Site

Traffic:

```text
10M-50M requests/month
```

Infra:

```text
USD 300-2,000/month
```

Depends on:

- Raw log retention.
- Aggregation frequency.
- Query engine.
- Number of customers.

### Large Site

Traffic:

```text
100M+ requests/month
```

Infra:

```text
USD 2,000-10,000+/month
```

Needs:

- Streaming ingestion.
- Object storage.
- Columnar analytics database.
- Partitioning and retention controls.

### Prompt Monitoring Costs

If using LLM APIs or paid search/answer monitoring:

```text
100 prompts x 5 engines x weekly = manageable
1,000+ prompts x 10 engines x daily = significant
```

Early product should cap prompts by plan.

## 8. Technical Barriers

### Low Barrier

- Parse logs.
- Match user-agent strings.
- Show dashboards.
- Count visits by page and bot.

### Medium Barrier

- Multi-CDN integrations.
- Normalized log schema.
- Bot registry maintenance.
- Reverse DNS/IP verification.
- Data retention and performance.
- Tenant isolation.

### High Barrier

- Accurate classification of agent intent: citation vs indexing vs training.
- Connecting a specific crawl to a specific AI answer.
- Measuring true AI referral attribution.
- Handling spoofed user agents.
- Enterprise security/compliance.
- Scaling to large customer log volumes.
- Keeping taxonomy current as AI companies change crawlers.

## 9. Suggested Architecture

### Ingestion

```text
CDN/server logs
-> collector
-> queue or batch processor
-> normalization
-> bot classification
-> storage
```

### Storage

MVP:

```text
PostgreSQL or SQLite for small demo
Object storage for raw logs
```

Commercial:

```text
ClickHouse / BigQuery / DuckDB + object storage
```

### Services

```text
log_ingestion_service
bot_registry_service
agent_traffic_service
page_analytics_service
referral_attribution_service
visibility_prompt_service
report_service
alert_service
```

### Dashboard

Core views:

- Overview.
- Agents.
- Pages.
- Trends.
- Referrals.
- Readiness.
- Alerts.
- Reports.

## 10. Recommended MVP for ANIFORCE

Since ANIFORCE is already moving toward Agent/GEO Asset Packs, the best first version should be:

```text
Agent Analytics for Agent/GEO Asset Packs
```

Instead of monitoring an entire large website, start with pages ANIFORCE generates:

- Landing page.
- FAQ page.
- Comparison page.
- Proof page.
- `agent-offer.json`.

This reduces integration complexity and makes validation easier.

MVP flow:

```text
Generate Agent/GEO Asset Pack
-> Publish pages under ANIFORCE-controlled domain/subdomain
-> Capture server logs
-> Detect AI crawlers
-> Show which asset pages agents read
-> Run prompt tests
-> Report mention/citation/correctness
```

This is much easier than integrating every customer's infrastructure on day one.

## 11. Monetization

Agent Analytics can be monetized as part of the Agent/GEO module.

### Add-On Pricing

```text
Agent/GEO Asset Pack + Agent Analytics
USD 3k-8k/month for growth customers
USD 10k-30k/month for scale customers
```

Plan limits:

- Number of monitored pages.
- Number of prompts.
- Number of engines/models.
- Log retention.
- Report frequency.
- Number of integrations.

### Standalone Audit

Lead-gen product:

```text
AI Agent Traffic Audit
```

Pricing:

```text
Free / low-cost audit
or USD 1k-5k one-time for a deeper report
```

### Enterprise

```text
Custom monthly fee
+ integration setup
+ log volume pricing
+ prompt volume pricing
+ managed optimization service
```

## 12. Recommendation

Build in this order:

1. Monitor ANIFORCE-generated Agent/GEO pages first.
2. Add Cloudflare/Vercel integration for customers second.
3. Add prompt/citation monitoring third.
4. Add conversion/CRM attribution fourth.
5. Add enterprise controls after design partners.

This keeps the first version small while still proving the strategic point:

```text
Agent/GEO assets are not theoretical. We can see AI agents reading them, track visibility, and optimize them over time.
```

## 13. Sources Checked

- Profound Agent Analytics feature page: https://www.tryprofound.com/features/agent-analytics
- Profound docs overview: https://docs.tryprofound.com/agent-analytics/overview
- Profound help overview: https://help.tryprofound.com/articles/2449520166-agent-analytics
- Profound Vercel integration blog: https://www.tryprofound.com/blog/agent-analytics-vercel
- OpenAI crawler docs: https://platform.openai.com/docs/bots
- Promptwatch agent analytics page: https://promptwatch.com/agent-analytics
- Unusual Agent Analytics: https://analytics.unusual.ai/
- Known Agents: https://knownagents.com/
