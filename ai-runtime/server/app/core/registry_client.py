import asyncio
import httpx
import logging
from typing import Optional
from server.app.core.config import settings

logger = logging.getLogger(__name__)


class RegistryClient:
    def __init__(self) -> None:
        self._gateway_url: Optional[str] = settings.gateway_url
        self._node_id: Optional[str] = settings.node_id
        self._node_url: Optional[str] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

    def set_node_url(self, url: str) -> None:
        self._node_url = url

    async def register(self) -> bool:
        if not self._gateway_url or not self._node_id or not self._node_url:
            logger.warning(
                "Skipping registration: GATEWAY_URL, NODE_ID, or node URL not set"
            )
            return False

        gateway_base = self._gateway_url.rstrip("/")
        register_url = f"{gateway_base}/register"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    register_url,
                    json={
                        "node_id": self._node_id,
                        "url": self._node_url,
                        "max_capacity": settings.node_max_capacity,
                    },
                )
                response.raise_for_status()
                logger.info(
                    f"Node {self._node_id} registered with gateway at {gateway_base}"
                )
                return True
        except Exception as e:
            logger.error(f"Registration failed: {e}", exc_info=True)
            return False

    async def start_heartbeat(self) -> None:
        if not self._gateway_url or not self._node_id:
            return

        if self._heartbeat_task is not None:
            return

        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop_heartbeat(self) -> None:
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

    async def _heartbeat_loop(self) -> None:
        gateway_base = self._gateway_url.rstrip("/")
        heartbeat_url = f"{gateway_base}/heartbeat/{self._node_id}"

        while self._running:
            try:
                await asyncio.sleep(settings.heartbeat_interval_sec)
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(heartbeat_url)
                    response.raise_for_status()
                    logger.debug(f"Heartbeat sent for node {self._node_id}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")

    async def shutdown(self) -> None:
        await self.stop_heartbeat()


registry_client = RegistryClient()
