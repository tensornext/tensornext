import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable, Awaitable
import logging
from gateway.app.core.metrics import metrics

logger = logging.getLogger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware for request ID propagation, latency tracking, and structured logging."""
    
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Extract tenant_id if available
        tenant_id = getattr(request.state, "tenant_id", None)
        
        start_time = time.time()
        endpoint = request.url.path
        
        # Structured log for request start
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "endpoint": endpoint,
            "tenant_id": tenant_id,
        }
        logger.info(f"Request started: {log_data}")
        
        try:
            response = await call_next(request)
            elapsed = time.time() - start_time
            
            # Record metrics
            status_code = response.status_code
            metrics.record_request(endpoint, status_code, elapsed)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # Structured log for request completion
            log_data.update({
                "status_code": status_code,
                "elapsed_seconds": round(elapsed, 3),
            })
            logger.info(f"Request completed: {log_data}")
            
            return response
            
        except Exception as e:
            elapsed = time.time() - start_time
            status_code = 500
            
            # Record error metrics
            metrics.record_request(endpoint, status_code, elapsed)
            
            # Structured log for request error
            log_data.update({
                "status_code": status_code,
                "elapsed_seconds": round(elapsed, 3),
                "error": str(e),
            })
            logger.error(f"Request failed: {log_data}", exc_info=True)
            
            raise