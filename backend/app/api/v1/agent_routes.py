"""Compatibility aggregator for Agent HTTP transport routers."""

from fastapi import APIRouter

from app.agent.api.approvals import router as approvals_router
from app.agent.api.events import router as events_router
from app.agent.api.runs import router as runs_router
from app.agent.api.sessions import router as sessions_router

router = APIRouter(prefix="/agent", tags=["agent"])
router.include_router(sessions_router)
router.include_router(runs_router)
router.include_router(approvals_router)
router.include_router(events_router)
