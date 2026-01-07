from fastapi import APIRouter
from gateway.app.core.metrics import metrics

router = APIRouter()


@router.get("/metrics")
async def get_metrics() -> dict:
    """Prometheus-ready metrics endpoint."""
    return metrics.get_metrics()