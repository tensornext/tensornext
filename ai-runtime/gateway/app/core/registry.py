import asyncio
import logging
import time
from typing import Dict, Optional
from dataclasses import dataclass, field
from gateway.app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class NodeInfo:
    node_id: str
    url: str
    max_capacity: int
    current_load: int = 0
    last_heartbeat: float = field(default_factory=time.time)
    healthy: bool = True

    def update_heartbeat(self) -> None:
        self.last_heartbeat = time.time()
        self.healthy = True

    def is_stale(self, timeout_sec: float) -> bool:
        return (time.time() - self.last_heartbeat) > timeout_sec

    def get_available_capacity(self) -> int:
        return max(0, self.max_capacity - self.current_load)

    def increment_load(self) -> None:
        self.current_load += 1

    def decrement_load(self) -> None:
        self.current_load = max(0, self.current_load - 1)


class NodeRegistry:
    def __init__(self) -> None:
        self._nodes: Dict[str, NodeInfo] = {}
        self._lock = asyncio.Lock()
        self._eviction_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._eviction_task is None:
            self._eviction_task = asyncio.create_task(self._eviction_loop())

    async def stop(self) -> None:
        if self._eviction_task:
            self._eviction_task.cancel()
            try:
                await self._eviction_task
            except asyncio.CancelledError:
                pass
            self._eviction_task = None

    async def register_node(
        self, node_id: str, url: str, max_capacity: int
    ) -> None:
        async with self._lock:
            node = NodeInfo(
                node_id=node_id, url=url, max_capacity=max_capacity
            )
            node.update_heartbeat()
            self._nodes[node_id] = node
            logger.info(
                f"Node registered: {node_id} at {url} (capacity={max_capacity})"
            )

    async def update_heartbeat(self, node_id: str) -> Optional[NodeInfo]:
        async with self._lock:
            node = self._nodes.get(node_id)
            if node:
                node.update_heartbeat()
                return node
            return None

    async def get_healthy_nodes(self) -> list[NodeInfo]:
        async with self._lock:
            return [
                node
                for node in self._nodes.values()
                if node.healthy and not node.is_stale(
                    settings.node_eviction_timeout_sec
                )
            ]

    async def get_node(self, node_id: str) -> Optional[NodeInfo]:
        async with self._lock:
            return self._nodes.get(node_id)

    async def increment_node_load(self, node_id: str) -> bool:
        async with self._lock:
            node = self._nodes.get(node_id)
            if node and node.healthy:
                node.increment_load()
                return True
            return False

    async def decrement_node_load(self, node_id: str) -> None:
        async with self._lock:
            node = self._nodes.get(node_id)
            if node:
                node.decrement_load()

    async def _eviction_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(settings.heartbeat_interval_sec)
                await self._evict_stale_nodes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in eviction loop: {e}", exc_info=True)

    async def _evict_stale_nodes(self) -> None:
        async with self._lock:
            now = time.time()
            timeout = settings.node_eviction_timeout_sec
            to_remove = []
            for node_id, node in self._nodes.items():
                if node.is_stale(timeout):
                    node.healthy = False
                    logger.warning(
                        f"Node {node_id} marked unhealthy (stale heartbeat)"
                    )
                    if (now - node.last_heartbeat) > (timeout * 2):
                        to_remove.append(node_id)
            for node_id in to_remove:
                del self._nodes[node_id]
                logger.info(f"Node {node_id} evicted (no heartbeat)")

    async def get_stats(self) -> Dict:
        async with self._lock:
            healthy = sum(1 for n in self._nodes.values() if n.healthy)
            total = len(self._nodes)
            return {
                "total_nodes": total,
                "healthy_nodes": healthy,
                "nodes": [
                    {
                        "node_id": n.node_id,
                        "url": n.url,
                        "load": n.current_load,
                        "capacity": n.max_capacity,
                        "healthy": n.healthy,
                    }
                    for n in self._nodes.values()
                ],
            }


registry = NodeRegistry()
