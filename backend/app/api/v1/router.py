from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.user import router as user_router
from app.api.v1.chat import router as chat_router
from app.api.v1.agent.routes import router as agent_router
from app.api.v1.projects import router as projects_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.materials import router as materials_router
from app.api.v1.platform_auth import router as platform_auth_router
from app.api.v1.organization import router as organization_router
from app.api.v1.contact_info import router as contact_info_router
from app.api.v1.mcp import router as mcp_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(chat_router)
api_router.include_router(agent_router)
api_router.include_router(projects_router)
api_router.include_router(campaigns_router)
api_router.include_router(materials_router)
api_router.include_router(platform_auth_router)
api_router.include_router(organization_router)
api_router.include_router(contact_info_router)
api_router.include_router(mcp_router)  # MCP 工具端点
