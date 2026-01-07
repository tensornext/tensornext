import time
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable, Awaitable
import logging
from collections import defaultdict
from gateway.app.core.config import settings
from gateway.app.core.metrics import metrics

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-tenant rate limiting middleware."""
    
    def __init__(self, app, limit_per_minute: int) -> None:
        super().__init__(app)
        self._limit = limit_per_minute
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._window_sec = 60.0
    
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Skip rate limiting for health and register endpoints
        if request.url.path in ("/health", "/register", "/metrics"):
            return await call_next(request)
        
        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            # Auth middleware should have set this, but handle gracefully
            return await call_next(request)
        
        now = time.time()
        tenant_requests = self._requests[tenant_id]
        
        # Remove requests outside the time window
        cutoff = now - self._window_sec
        tenant_requests[:] = [ts for ts in tenant_requests if ts > cutoff]
        
        # Check if limit exceeded
        if len(tenant_requests) >= self._limit:
            metrics.record_rate_limit()
            logger.warning(f"Rate limit exceeded for tenant {tenant_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {self._limit} requests per minute"
            )
        
        # Record this request
        tenant_requests.append(now)
        
        response = await call_next(request)
        return response