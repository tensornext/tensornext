import httpx
import logging
import json
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from shared.schemas.inference import InferenceRequest, InferenceResponse
from gateway.app.core.router import router as node_router
from gateway.app.core.registry import registry
from gateway.app.core.config import settings
from gateway.app.core.circuit_breaker import circuit_breaker
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)
router = APIRouter()


async def _execute_inference(
    node,
    request: InferenceRequest,
    http_request: Request,
    stream: bool = False,
) -> Tuple[httpx.Response, float]:
    """Execute inference request with retry logic and circuit breaker."""
    node_url = f"{node.url.rstrip('/')}/infer"
    start_time = time.time()
    timeout_ms = settings.gateway_timeout_ms / 1000.0
    timeout = httpx.Timeout(timeout_ms)
    
    last_error: Optional[Exception] = None
    
    for attempt in range(settings.max_retries + 1):
        # Check circuit breaker
        if not circuit_breaker.is_available(node.node_id):
            logger.warning(f"Circuit breaker open for node {node.node_id}, skipping")
            if attempt < settings.max_retries:
                # Try to select a different node
                node = await node_router.select_node()
                if node is None or not circuit_breaker.is_available(node.node_id):
                    break
                node_url = f"{node.url.rstrip('/')}/infer"
                continue
            else:
                break
        
        try:
            headers = {
                "X-Request-ID": getattr(http_request.state, "request_id", ""),
            }
            if stream:
                headers["Accept"] = "text/event-stream"
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    node_url,
                    json=request.model_dump(),
                    headers=headers,
                )
                response.raise_for_status()
                
                # Record success
                circuit_breaker.record_success(node.node_id)
                elapsed = time.time() - start_time
                return response, elapsed
                
        except httpx.TimeoutException as e:
            last_error = e
            circuit_breaker.record_failure(node.node_id)
            logger.warning(
                f"Request to {node.node_id} timed out (attempt {attempt + 1})"
            )
            if attempt < settings.max_retries:
                # Try different node on retry
                node = await node_router.select_node()
                if node is None:
                    break
                node_url = f"{node.url.rstrip('/')}/infer"
                continue
                
        except httpx.HTTPStatusError as e:
            last_error = e
            if e.response.status_code >= 500:
                circuit_breaker.record_failure(node.node_id)
            logger.warning(
                f"Node {node.node_id} returned error: {e.response.status_code} "
                f"(attempt {attempt + 1})"
            )
            if attempt < settings.max_retries and e.response.status_code >= 500:
                # Retry on server errors
                node = await node_router.select_node()
                if node is None:
                    break
                node_url = f"{node.url.rstrip('/')}/infer"
                continue
            else:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Node error: {e.response.text}",
                )
                
        except Exception as e:
            last_error = e
            circuit_breaker.record_failure(node.node_id)
            logger.error(
                f"Request to {node.node_id} failed: {e} (attempt {attempt + 1})",
                exc_info=True,
            )
            if attempt < settings.max_retries:
                node = await node_router.select_node()
                if node is None:
                    break
                node_url = f"{node.url.rstrip('/')}/infer"
                continue
    
    # All retries exhausted
    elapsed = time.time() - start_time
    if isinstance(last_error, httpx.TimeoutException):
        raise HTTPException(status_code=504, detail="Request timeout")
    raise HTTPException(status_code=503, detail="No healthy nodes available")


@router.post("/infer", response_model=InferenceResponse)
async def infer(
    request: InferenceRequest,
    http_request: Request,
    stream: bool = Query(default=False, description="Enable streaming response"),
) -> InferenceResponse:
    """Non-streaming inference endpoint (default)."""
    # If streaming is requested but not enabled, fall back to non-streaming
    if stream and settings.enable_streaming:
        raise HTTPException(
            status_code=400,
            detail="Use /infer/stream endpoint for streaming responses",
        )
    
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

    try:
        response, elapsed = await _execute_inference(node, request, http_request, stream=False)
        result = InferenceResponse(**response.json())
        logger.info(
            f"Request routed to {node.node_id} (elapsed={elapsed:.3f}s)"
        )
        return result
    finally:
        await registry.decrement_node_load(node.node_id)


@router.post("/infer/stream")
async def infer_stream(
    request: InferenceRequest,
    http_request: Request,
) -> StreamingResponse:
    """Streaming inference endpoint using Server-Sent Events."""
    if not settings.enable_streaming:
        raise HTTPException(
            status_code=503,
            detail="Streaming is not enabled",
        )
    
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

    async def generate_stream():
        try:
            response, elapsed = await _execute_inference(
                node, request, http_request, stream=True
            )
            
            # Check if response is actually streaming
            content_type = response.headers.get("content-type", "")
            if "text/event-stream" in content_type or "text/plain" in content_type:
                # Proxy SSE stream
                async for chunk in response.aiter_bytes():
                    yield chunk
            else:
                # Fallback: convert non-streaming response to SSE
                try:
                    data = response.json()
                    result = InferenceResponse(**data)
                    # Emit as SSE
                    sse_data = json.dumps(result.model_dump())
                    yield f"data: {sse_data}\n\n".encode()
                except:
                    # If JSON parsing fails, stream raw text
                    async for chunk in response.aiter_bytes():
                        yield chunk
                yield f"data: [DONE]\n\n".encode()
                
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            error_data = json.dumps({"error": str(e)})
            yield f"data: {error_data}\n\n".encode()
        finally:
            await registry.decrement_node_load(node.node_id)

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
