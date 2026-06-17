"""HITL 确认响应 API 端点"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user_id
from app.mcp.hitl_server import respond_to_hitl

router = APIRouter(prefix="/hitl", tags=["hitl"])
logger = logging.getLogger(__name__)


class HitlRespondRequest(BaseModel):
    """HITL 响应请求"""
    approved: bool
    feedback: Optional[str] = None


@router.post("/{hitl_id}/respond")
async def respond(
    hitl_id: str,
    request: HitlRespondRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    响应 HITL 确认请求

    前端收到 HITL 请求（TaskOutputProduced type=hitl_request）后，
    用户做出选择，通过此端点响应。Agent 会收到响应并继续执行。

    Args:
        hitl_id: HITL 请求 ID
        request: 响应内容（approved + feedback）
    """
    success = respond_to_hitl(
        hitl_id=hitl_id,
        approved=request.approved,
        feedback=request.feedback or "",
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail="HITL 请求不存在或已超时",
        )

    logger.info(
        f"HITL responded: hitl_id={hitl_id}, approved={request.approved}, user={user_id}"
    )
    return {
        "hitl_id": hitl_id,
        "approved": request.approved,
        "status": "delivered",
    }
