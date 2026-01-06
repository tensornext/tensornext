import asyncio
import logging
from typing import List, Optional
from server.app.core.batcher import Batch
from server.app.core.worker import GPUWorker

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(
        self,
        workers: List[GPUWorker],
        batch_queue: asyncio.Queue[Batch],
    ) -> None:
        self._workers = workers
        self._batch_queue = batch_queue
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._schedule_loop())
        logger.info(f"Scheduler started with {len(self._workers)} workers")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            await self._task
        logger.info("Scheduler stopped")

    async def _schedule_loop(self) -> None:
        while self._running:
            try:
                try:
                    batch = await asyncio.wait_for(
                        self._batch_queue.get(), timeout=0.1
                    )
                except asyncio.TimeoutError:
                    continue
                worker = await self._find_available_worker()
                if worker is None:
                    logger.warning("No available worker, requeuing batch")
                    await asyncio.sleep(0.01)
                    await self._batch_queue.put(batch)
                    continue
                await worker.get_input_queue().put(batch)
                logger.debug(f"Batch scheduled to worker {worker.worker_id}")
            except Exception as e:
                logger.error(f"Scheduler error: {e}", exc_info=True)

    async def _find_available_worker(self) -> Optional[GPUWorker]:
        for worker in self._workers:
            if worker.available:
                return worker
        return None
