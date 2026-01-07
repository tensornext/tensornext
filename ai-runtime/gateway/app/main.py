from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from gateway.app.core.config import settings
from gateway.app.core.registry import registry
from gateway.app.core.observability import ObservabilityMiddleware
from gateway.app.core.auth import TenantAuthMiddleware
from gateway.app.core.rate_limit import RateLimitMiddleware
from gateway.app.api import health, infer, register, metrics
import logging
import sys

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)

# CORS middleware (outermost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Step-4 middleware (order matters: observability -> auth -> rate_limit)
app.add_middleware(ObservabilityMiddleware)
app.add_middleware(
    TenantAuthMiddleware,
    api_key_map=settings.get_api_key_map(),
)
app.add_middleware(
    RateLimitMiddleware,
    limit_per_minute=settings.tenant_rate_limit,
)

app.include_router(health.router)
app.include_router(infer.router)
app.include_router(register.router)
app.include_router(metrics.router)


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting AI Runtime Gateway")
    logger.info(f"Streaming enabled: {settings.enable_streaming}")
    logger.info(f"Rate limit: {settings.tenant_rate_limit} req/min")
    logger.info(f"Gateway timeout: {settings.gateway_timeout_ms}ms")
    logger.info(f"Max retries: {settings.max_retries}")
    await registry.start()
    logger.info("Gateway startup complete")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Shutting down AI Runtime Gateway")
    await registry.stop()
