"""FastAPI router template for GEO diagnosis integration."""
from fastapi import APIRouter, HTTPException

from .repository import GeoAuditRepository, MemoryGeoAuditRepository
from .schemas import GeoAuditListResponse, GeoAuditReport, GeoAuditRequest
from .service import GeoDiagnosisService

router = APIRouter(prefix="/geo-audits", tags=["geo-audits"])
repo: GeoAuditRepository = MemoryGeoAuditRepository()
service = GeoDiagnosisService()


@router.post("", response_model=GeoAuditReport)
async def create_geo_audit(request: GeoAuditRequest):
    report = service.generate(request)
    await repo.create(report.model_dump())
    return report


@router.get("", response_model=GeoAuditListResponse)
async def list_geo_audits(project_id: str):
    audits = await repo.list_by_project(project_id)
    return {"audits": [GeoAuditReport.model_validate(audit) for audit in audits]}


@router.get("/{audit_id}", response_model=GeoAuditReport)
async def get_geo_audit(audit_id: str):
    audit = await repo.get_by_id(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="GEO audit not found")
    return GeoAuditReport.model_validate(audit)
