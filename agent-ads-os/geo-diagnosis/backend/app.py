"""Standalone FastAPI app for the GEO diagnosis module."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .schemas import GeoAuditListResponse, GeoAuditReport, GeoAuditRequest
from .service import GeoDiagnosisService
from .sqlite_repository import SqliteGeoAuditRepository

ROOT = Path(__file__).resolve().parents[1]
repo = SqliteGeoAuditRepository(ROOT / "data" / "geo-diagnosis.db")
service = GeoDiagnosisService()

app = FastAPI(
    title="Agent Ads OS GEO Diagnosis",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/frontend", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")


@app.get("/health")
async def health_check():
    return {"status": "ok", "module": "geo-diagnosis"}


@app.post("/api/geo-audits", response_model=GeoAuditReport)
async def create_geo_audit(request: GeoAuditRequest):
    try:
        report = await service.generate(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await repo.create(report.model_dump())
    return report


@app.get("/api/geo-audits", response_model=GeoAuditListResponse)
async def list_geo_audits(project_id: str):
    audits = await repo.list_by_project(project_id)
    return {"audits": [GeoAuditReport.model_validate(audit) for audit in audits]}


@app.get("/api/geo-audits/{audit_id}", response_model=GeoAuditReport)
async def get_geo_audit(audit_id: str):
    audit = await repo.get_by_id(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="GEO audit not found")
    return GeoAuditReport.model_validate(audit)
