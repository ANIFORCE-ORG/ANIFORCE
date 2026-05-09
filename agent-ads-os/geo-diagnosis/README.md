# GEO Diagnosis Module

This folder contains the Agent Ads OS GEO diagnosis flow as an isolated module.
It is intentionally separate from the main ANIFORCE ad-agent application to avoid
mixing exploratory Agent Ads OS work with the existing campaign/material code.

## Structure

```text
geo-diagnosis/
├── README.md
├── backend/
│   ├── api.py
│   ├── models.py
│   ├── repository.py
│   ├── schemas.py
│   └── service.py
├── database/
│   └── 001_create_geo_audits.sql
└── frontend/
    ├── AgentAnalyticsAudit.vue
    ├── ProjectGeoPanel.vue
    ├── client.ts
    └── types.ts
```

## Integration Rule

The main ANIFORCE app should consume this module through a thin adapter only
after the GEO diagnosis flow is stable. Until then, keep backend schemas,
repository logic, report generation, and frontend components here.

## First Runnable Flow

1. Create a GEO audit request.
2. Generate deterministic report data.
3. Persist report to SQLite.
4. Query reports by `project_id`.
5. Render latest report and history in the frontend panel.

## Run Locally

```bash
cd agent-ads-os/geo-diagnosis
bash run_geo_demo.sh
```

Open:

```text
http://127.0.0.1:8020/frontend/index.html
```

The standalone demo writes SQLite data to:

```text
agent-ads-os/geo-diagnosis/data/geo-diagnosis.db
```
