from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable, Awaitable, Optional
import logging
from gateway.app.core.config import settings

logger = logging.getLogger(__name__)


class TenantAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for API key validation and tenant isolation."""
    
    def __init__(self, app, api_key_map: dict[str, str]) -> None:
        super().__init__(app)
        self._api_key_map = api_key_map
        self._tenant_requests: dict[str, int] = {}
    
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Skip auth for health and register endpoints
        if request.url.path in ("/health", "/register", "/metrics"):
            return await call_next(request)
        
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            logger.warning("Request missing X-API-Key header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing X-API-Key header"
            )
        
        tenant_id = self._api_key_map.get(api_key)
        if not tenant_id:
            logger.warning(f"Invalid API key: {api_key[:8]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        # Attach tenant_id to request state
        request.state.tenant_id = tenant_id
        request.state.api_key = api_key
        
        # Track per-tenant requests
        self._tenant_requests[tenant_id] = self._tenant_requests.get(tenant_id, 0) + 1
        
        response = await call_next(request)
        return response
    
    def get_tenant_stats(self) -> dict[str, int]:
        """Get per-tenant request counts."""
        return dict(self._tenant_requests)