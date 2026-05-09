# GEO Diagnosis MVP Plan

This document keeps the Agent Ads OS / GEO diagnosis MVP plan separate from the
main ANIFORCE ad-agent application.

## Goal

Build a local, runnable GEO diagnosis flow for Agent Ads OS:

1. Select or create a project.
2. Enter brand, website, category, competitors, and target market.
3. Generate an AI visibility / crawler / prompt / competitor / readiness report.
4. Persist the report.
5. Produce an agent-offer.json preview.
6. Show report history and latest diagnosis summary.

## Local MVP Scope

- One-command local startup in a later phase.
- No required third-party API keys for the first demo.
- Deterministic mock generation for stable demos.
- SQLite persistence for audit reports.
- Clean boundaries for later replacement with crawling, LLM generation, prompt
  monitoring, and ad platform data.

## GEO Diagnosis Minimal Flow

1. Open project detail or GEO diagnosis demo.
2. Confirm brand, URL, category, competitors, and target market.
3. Create a diagnosis report.
4. Save it to the GEO audit repository.
5. Display score cards, prompt visibility, crawler activity, page gaps, fixes,
   and agent-offer.json.
6. List previous reports for the same project.

## Development Order

1. Keep GEO diagnosis code under `agent-ads-os/geo-diagnosis`.
2. Maintain standalone backend contracts and frontend clients in this module.
3. Only integrate into the main ANIFORCE app after the flow is stable.
4. When integrating, expose a thin adapter from ANIFORCE to this module instead
   of copying business logic into main app folders.

## Future Resources

- OpenAI or compatible LLM API.
- Website crawler: httpx / BeautifulSoup first, Playwright later if needed.
- Prompt monitoring dataset.
- Server log / bot user-agent analytics.
- SQLite locally, PostgreSQL when deployed.
- Export pipeline for Markdown / PDF reports.
