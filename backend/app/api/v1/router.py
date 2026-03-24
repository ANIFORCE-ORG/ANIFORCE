from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.projects import router as projects_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.materials import router as materials_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(projects_router)
api_router.include_router(campaigns_router)
api_router.include_router(materials_router)
