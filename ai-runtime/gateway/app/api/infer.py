import httpx
import logging
from fastapi import APIRouter, HTTPException, Request
from shared.schemas.inference import InferenceRequest, InferenceResponse
from gateway.app.core.router import router as node_router
from gateway.app.core.registry import registry
from gateway.app.core.config import settings
import time

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/infer", response_model=InferenceResponse)
async def infer(
    request: InferenceRequest, http_request: Request
) -> InferenceResponse:
    node = await node_router.select_node()
    if node is None:
        logger.error("No healthy nodes available")
        raise HTTPException(
            status_code=503, detail="No inference nodes available"
        )

    if not await registry.increment_node_load(node.node_id):
        logger.warning(f"Node {node.node_id} became unhealthy during selection")
        raise HTTPException(
            status_code=503, detail="No inference nodes available"
        )

    node_url = f"{node.url.rstrip('/')}/infer"
    start_time = time.time()

    try:
        timeout = httpx.Timeout(settings.request_timeout_sec)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                node_url,
                json=request.model_dump(),
                headers={
                    "X-Request-ID": http_request.headers.get(
                        "X-Request-ID", ""
                    )
                },
            )
            response.raise_for_status()
            result = InferenceResponse(**response.json())
            elapsed = time.time() - start_time
            logger.info(
                f"Request routed to {node.node_id} (elapsed={elapsed:.3f}s)"
            )
            return result
    except httpx.TimeoutException:
        logger.error(f"Request to {node.node_id} timed out")
        raise HTTPException(status_code=504, detail="Request timeout")
    except httpx.HTTPStatusError as e:
        logger.error(f"Node {node.node_id} returned error: {e.response.status_code}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Node error: {e.response.text}",
        )
    except Exception as e:
        logger.error(f"Request to {node.node_id} failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await registry.decrement_node_load(node.node_id)
