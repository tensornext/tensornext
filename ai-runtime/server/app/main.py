from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from server.app.core.config import settings
from server.app.core.logging import setup_logging, request_id_var
from server.app.api import health, infer
import logging
import uuid
from typing import Callable, Awaitable

setup_logging(settings.log_level)
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


@app.middleware("http")
async def add_request_id(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request_id_var.set(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting AI Runtime Server")
    from server.app.core.pipeline import pipeline
    await pipeline.initialize()
    
    from server.app.core.registry_client import registry_client
    node_url = f"http://{settings.host}:{settings.port}"
    registry_client.set_node_url(node_url)
    await registry_client.register()
    await registry_client.start_heartbeat()
    
    logger.info("Server startup complete")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Shutting down AI Runtime Server")
    from server.app.core.registry_client import registry_client
    await registry_client.shutdown()
    from server.app.core.pipeline import pipeline
    await pipeline.shutdown()

