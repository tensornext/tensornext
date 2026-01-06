from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from gateway.app.core.config import settings
from gateway.app.core.registry import registry
from gateway.app.api import health, infer, register
import logging
import sys
import uuid
from typing import Callable, Awaitable

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(infer.router)
app.include_router(register.router)


@app.middleware("http")
async def add_request_id(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting AI Runtime Gateway")
    await registry.start()
    logger.info("Gateway startup complete")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Shutting down AI Runtime Gateway")
    await registry.stop()
