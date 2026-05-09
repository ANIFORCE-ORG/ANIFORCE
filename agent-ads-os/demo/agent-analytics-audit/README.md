# Agent Analytics Audit Demo

Static local demo for the minimum viable Agent Analytics / AI Buyer Visibility audit product.

## Run Locally

From this directory:

```bash
python3 -m http.server 8123
```

Open:

```text
http://127.0.0.1:8123
```

## Demo Flow

1. Enter customer brand, website, category, competitors, and target market.
2. Click `生成诊断报告`.
3. Review:
   - AI Mention Rate
   - Citation Rate
   - GEO Readiness
   - Agent Hits
   - AI crawler activity
   - Prompt visibility win/loss
   - Page-level asset gaps
   - `agent-offer.json`
   - prioritized recommendations

## Current Implementation

This is a deterministic static prototype. It does not call external APIs.

Future replacements:

- Website crawler.
- CDN/server log ingestion.
- Bot registry and reverse DNS verification.
- Prompt/citation monitoring.
- Search Console / analytics integration.
- Exportable PDF report.
