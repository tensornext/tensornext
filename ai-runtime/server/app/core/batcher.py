import asyncio
import logging
from typing import List, Optional
from dataclasses import dataclass
from server.app.core.queue import QueuedRequest
from server.app.schemas.inference import InferenceRequest

logger = logging.getLogger(__name__)


@dataclass
class Batch:
    requests: List[QueuedRequest]
    created_at: float

    def size(self) -> int:
        return len(self.requests)


class DynamicBatcher:
    def __init__(
        self,
        max_batch_size: int,
        max_batch_latency_ms: int,
        input_queue: asyncio.Queue[QueuedRequest],
        output_queue: asyncio.Queue[Batch],
    ) -> None:
        self._max_batch_size = max_batch_size
        self._max_batch_latency_ms = max_batch_latency_ms
        self._input_queue = input_queue
        self._output_queue = output_queue
        self._current_batch: Optional[Batch] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._batch_loop())
        logger.info(
            f"DynamicBatcher started: max_size={self._max_batch_size}, "
            f"max_latency_ms={self._max_batch_latency_ms}"
        )

    async def stop(self) -> None:
        self._running = False
        if self._current_batch and self._current_batch.size() > 0:
            await self._flush_batch()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("DynamicBatcher stopped")

    async def _batch_loop(self) -> None:
        while self._running:
            try:
                if self._current_batch is None:
                    try:
                        queued = await asyncio.wait_for(
                            self._input_queue.get(), timeout=0.1
                        )
                        self._current_batch = Batch(
                            requests=[queued], created_at=asyncio.get_event_loop().time()
                        )
                    except asyncio.TimeoutError:
                        continue
                else:
                    try:
                        queued = await asyncio.wait_for(
                            self._input_queue.get(),
                            timeout=self._max_batch_latency_ms / 1000.0,
                        )
                        self._current_batch.requests.append(queued)
                    except asyncio.TimeoutError:
                        await self._flush_batch()
                        continue

                if self._current_batch.size() >= self._max_batch_size:
                    await self._flush_batch()
            except Exception as e:
                logger.error(f"Batcher error: {e}", exc_info=True)
                if self._current_batch and self._current_batch.size() > 0:
                    await self._flush_batch()

    async def _flush_batch(self) -> None:
        if self._current_batch is None or self._current_batch.size() == 0:
            return
        batch = self._current_batch
        self._current_batch = None
        await self._output_queue.put(batch)
        logger.debug(f"Batch flushed: size={batch.size()}")
