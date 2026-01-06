import asyncio
import logging
from typing import Optional, List
from server.app.core.batcher import Batch
from server.app.models.loader import ModelLoader
from server.app.schemas.inference import InferenceResponse

logger = logging.getLogger(__name__)


class GPUWorker:
    def __init__(self, worker_id: int, gpu_id: int, model_loader: ModelLoader) -> None:
        self._worker_id = worker_id
        self._gpu_id = gpu_id
        self._model_loader = model_loader
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._input_queue: Optional[asyncio.Queue[Batch]] = None
        self._available = True

    async def start(self) -> None:
        if self._running:
            return
        self._input_queue = asyncio.Queue()
        self._running = True
        self._task = asyncio.create_task(self._worker_loop())
        logger.info(f"GPUWorker {self._worker_id} started on GPU {self._gpu_id}")

    def get_input_queue(self) -> asyncio.Queue[Batch]:
        if self._input_queue is None:
            self._input_queue = asyncio.Queue()
        return self._input_queue  # type: ignore

    async def stop(self) -> None:
        self._running = False
        if self._task:
            await self._task
        logger.info(f"GPUWorker {self._worker_id} stopped")

    @property
    def available(self) -> bool:
        return self._available

    @property
    def worker_id(self) -> int:
        return self._worker_id

    @property
    def gpu_id(self) -> int:
        return self._gpu_id

    async def _worker_loop(self) -> None:
        while self._running:
            try:
                if self._input_queue is None:
                    await asyncio.sleep(0.1)
                    continue
                batch = await self._input_queue.get()
                self._available = False
                await self._process_batch(batch)
                self._available = True
            except Exception as e:
                logger.error(f"Worker {self._worker_id} error: {e}", exc_info=True)
                self._available = True

    async def _process_batch(self, batch: Batch) -> None:
        logger.debug(
            f"Worker {self._worker_id} processing batch: size={batch.size()}"
        )
        responses = await self._generate_batch(batch.requests)
        for queued, response in zip(batch.requests, responses):
            if not queued.future.done():
                queued.future.set_result(response)

    async def _generate_batch(
        self, requests: List
    ) -> List[InferenceResponse]:
        loop = asyncio.get_event_loop()
        responses: List[InferenceResponse] = []
        for queued in requests:
            try:
                text = await loop.run_in_executor(
                    None,
                    self._model_loader.generate,
                    queued.request.prompt,
                    queued.request.max_tokens if queued.request.max_tokens is not None else 100,
                    queued.request.temperature if queued.request.temperature is not None else 0.7,
                )
                responses.append(
                    InferenceResponse(
                        api_version="v1", text=text, request_id=queued.request_id
                    )
                )
            except Exception as e:
                logger.error(
                    f"Worker {self._worker_id} generation error: {e}", exc_info=True
                )
                if not queued.future.done():
                    queued.future.set_exception(e)
                responses.append(
                    InferenceResponse(
                        api_version="v1",
                        text=f"Error: {str(e)}",
                        request_id=queued.request_id,
                    )
                )
        return responses
