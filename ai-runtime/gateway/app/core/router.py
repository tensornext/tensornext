import logging
from typing import Optional
from gateway.app.core.registry import NodeRegistry, NodeInfo, registry

logger = logging.getLogger(__name__)


class Router:
    def __init__(self, registry: NodeRegistry) -> None:
        self._registry = registry

    async def select_node(self) -> Optional[NodeInfo]:
        nodes = await self._registry.get_healthy_nodes()
        if not nodes:
            return None

        best_node: Optional[NodeInfo] = None
        best_capacity = -1

        for node in nodes:
            capacity = node.get_available_capacity()
            if capacity > best_capacity:
                best_capacity = capacity
                best_node = node

        return best_node


router = Router(registry)
