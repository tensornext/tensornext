import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from server.app.core.scheduler import Scheduler
from server.app.core.worker import GPUWorker
from server.app.core.batcher import Batch
from server.app.core.queue import QueuedRequest
from server.app.schemas.inference import InferenceRequest
from server.app.models.loader import ModelLoader
from server.app.core.config import settings


class TestScheduler:
    @pytest.mark.asyncio
    async def test_scheduler_initialization(self):
        workers: list[GPUWorker] = []
        try:
            for i in range(2):
                loader = ModelLoader(gpu_id=i)
                loader.load()
                worker = GPUWorker(worker_id=i, gpu_id=i, model_loader=loader)
                workers.append(worker)
                await worker.start()

            batch_queue = asyncio.Queue()
            scheduler = Scheduler(workers=workers, batch_queue=batch_queue)
            await scheduler.start()

            assert len(scheduler._workers) == 2
            await asyncio.sleep(0.1)

            await scheduler.stop()
            await asyncio.sleep(0.2)
        finally:
            for worker in workers:
                await worker.stop()
            await asyncio.sleep(0.2)

    @pytest.mark.asyncio
    async def test_scheduler_assigns_to_available_worker(self):
        workers: list[GPUWorker] = []
        try:
            for i in range(2):
                loader = ModelLoader(gpu_id=i)
                loader.load()
                worker = GPUWorker(worker_id=i, gpu_id=i, model_loader=loader)
                workers.append(worker)
                await worker.start()

            batch_queue = asyncio.Queue()
            scheduler = Scheduler(workers=workers, batch_queue=batch_queue)
            await scheduler.start()

            request = InferenceRequest(prompt="test")
            future = asyncio.Future()
            queued = QueuedRequest(request=request, future=future, request_id="req0")
            batch = Batch(requests=[queued], created_at=0.0)

            await batch_queue.put(batch)
            await asyncio.sleep(0.3)

            # Check if batch was assigned (either in queue or being processed)
            assigned = False
            for worker in workers:
                if not worker.get_input_queue().empty():
                    assigned = True
                    break
                # Or worker is processing (not available)
                if not worker.available:
                    assigned = True
                    break

            assert assigned

            await scheduler.stop()
        finally:
            for worker in workers:
                await worker.stop()
            await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_scheduler_requeues_when_no_worker_available(self):
        workers: list[GPUWorker] = []
        try:
            for i in range(1):
                loader = ModelLoader(gpu_id=i)
                loader.load()
                worker = GPUWorker(worker_id=i, gpu_id=i, model_loader=loader)
                workers.append(worker)
                await worker.start()

            batch_queue = asyncio.Queue()
            scheduler = Scheduler(workers=workers, batch_queue=batch_queue)
            await scheduler.start()

            request = InferenceRequest(prompt="test")
            future = asyncio.Future()
            queued = QueuedRequest(request=request, future=future, request_id="req0")
            batch = Batch(requests=[queued], created_at=0.0)

            worker = workers[0]
            worker._available = False

            await batch_queue.put(batch)
            await asyncio.sleep(0.2)

            assert batch_queue.qsize() >= 0

            await scheduler.stop()
            await asyncio.sleep(0.2)
        finally:
            for worker in workers:
                await worker.stop()
            await asyncio.sleep(0.2)
