import asyncio
import logging
from typing import List, Optional
from server.app.core.config import settings
from server.app.core.queue import BoundedRequestQueue
from server.app.core.batcher import DynamicBatcher
from server.app.core.worker import GPUWorker
from server.app.core.scheduler import Scheduler
from server.app.models.loader import ModelLoader
from server.app.schemas.inference import InferenceRequest, InferenceResponse

logger = logging.getLogger(__name__)


class InferencePipeline:
    def __init__(self) -> None:
        self._request_queue: Optional[BoundedRequestQueue] = None
        self._batch_queue: Optional[asyncio.Queue] = None
        self._batcher: Optional[DynamicBatcher] = None
        self._workers: List[GPUWorker] = []
        self._scheduler: Optional[Scheduler] = None
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return

        gpu_count = self._get_gpu_count()
        logger.info(f"Initializing pipeline with {gpu_count} GPUs")

        self._request_queue = BoundedRequestQueue(
            maxsize=settings.max_in_flight_requests
        )
        self._batch_queue = asyncio.Queue()

        self._batcher = DynamicBatcher(
            max_batch_size=settings.batch_max_size,
            max_batch_latency_ms=settings.batch_max_latency_ms,
            input_queue=self._request_queue._queue,
            output_queue=self._batch_queue,
        )

        self._workers = []
        for i in range(gpu_count):
            loader = ModelLoader(gpu_id=i)
            loader.load()
            worker = GPUWorker(worker_id=i, gpu_id=i, model_loader=loader)
            self._workers.append(worker)

        self._scheduler = Scheduler(
            workers=self._workers,
            batch_queue=self._batch_queue,
        )

        await self._batcher.start()
        for worker in self._workers:
            await worker.start()
        await self._scheduler.start()

        self._initialized = True
        logger.info("Inference pipeline initialized")

    async def shutdown(self) -> None:
        if not self._initialized:
            return
        logger.info("Shutting down inference pipeline")
        if self._batcher:
            await self._batcher.stop()
        for worker in self._workers:
            await worker.stop()
        if self._scheduler:
            await self._scheduler.stop()
        self._initialized = False

    async def enqueue(
        self, request: InferenceRequest, request_id: str
    ) -> InferenceResponse:
        if not self._initialized:
            await self.initialize()
        if self._request_queue is None:
            raise RuntimeError("Request queue not initialized")
        future = await self._request_queue.put(request, request_id)
        return await future

    def _get_gpu_count(self) -> int:
        if settings.use_mock_model:
            return 2
        gpu_count = ModelLoader.get_gpu_count()
        if gpu_count == 0:
            return 1
        return gpu_count


pipeline = InferencePipeline()
