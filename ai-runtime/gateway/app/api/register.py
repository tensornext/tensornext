from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict
from gateway.app.core.registry import registry
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class RegisterRequest(BaseModel):
    node_id: str = Field(..., description="Unique node identifier")
    url: str = Field(..., description="Node base URL")
    max_capacity: int = Field(..., gt=0, description="Maximum concurrent requests")


@router.post("/register")
async def register_node(request: RegisterRequest) -> Dict[str, str]:
    try:
        await registry.register_node(
            node_id=request.node_id,
            url=request.url,
            max_capacity=request.max_capacity,
        )
        return {"status": "registered"}
    except Exception as e:
        logger.error(f"Registration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/heartbeat/{node_id}")
async def heartbeat(node_id: str) -> Dict[str, str]:
    node = await registry.update_heartbeat(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return {"status": "ok"}
