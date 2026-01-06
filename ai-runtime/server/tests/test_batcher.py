import pytest
import asyncio
import sys
import os
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from server.app.core.batcher import DynamicBatcher, Batch
from server.app.core.queue import QueuedRequest
from server.app.schemas.inference import InferenceRequest


class TestDynamicBatcher:
    def test_batcher_initialization(self):
        input_queue = asyncio.Queue()
        output_queue = asyncio.Queue()
        batcher = DynamicBatcher(
            max_batch_size=4,
            max_batch_latency_ms=100,
            input_queue=input_queue,
            output_queue=output_queue,
        )
        assert batcher._max_batch_size == 4
        assert batcher._max_batch_latency_ms == 100

    @pytest.mark.asyncio
    async def test_batcher_flushes_on_max_size(self):
        input_queue = asyncio.Queue()
        output_queue = asyncio.Queue()
        batcher = DynamicBatcher(
            max_batch_size=3,
            max_batch_latency_ms=1000,
            input_queue=input_queue,
            output_queue=output_queue,
        )
        await batcher.start()

        for i in range(3):
            request = InferenceRequest(prompt=f"test {i}")
            future = asyncio.Future()
            queued = QueuedRequest(request=request, future=future, request_id=f"req{i}")
            await input_queue.put(queued)

        await asyncio.sleep(0.1)
        batch = await output_queue.get()
        assert batch.size() == 3

        await batcher.stop()

    @pytest.mark.asyncio
    async def test_batcher_flushes_on_timeout(self):
        input_queue = asyncio.Queue()
        output_queue = asyncio.Queue()
        batcher = DynamicBatcher(
            max_batch_size=10,
            max_batch_latency_ms=50,
            input_queue=input_queue,
            output_queue=output_queue,
        )
        await batcher.start()

        request = InferenceRequest(prompt="test")
        future = asyncio.Future()
        queued = QueuedRequest(request=request, future=future, request_id="req0")
        await input_queue.put(queued)

        await asyncio.sleep(0.1)
        batch = await output_queue.get()
        assert batch.size() == 1

        await batcher.stop()

    @pytest.mark.asyncio
    async def test_batcher_handles_multiple_batches(self):
        input_queue = asyncio.Queue()
        output_queue = asyncio.Queue()
        batcher = DynamicBatcher(
            max_batch_size=2,
            max_batch_latency_ms=1000,
            input_queue=input_queue,
            output_queue=output_queue,
        )
        await batcher.start()

        for i in range(5):
            request = InferenceRequest(prompt=f"test {i}")
            future = asyncio.Future()
            queued = QueuedRequest(request=request, future=future, request_id=f"req{i}")
            await input_queue.put(queued)

        await asyncio.sleep(0.1)

        batches: List[Batch] = []
        while not output_queue.empty():
            batches.append(await output_queue.get())

        assert len(batches) >= 2
        total_requests = sum(b.size() for b in batches)
        assert total_requests == 5

        await batcher.stop()


class TestBatch:
    def test_batch_size(self):
        requests: List[QueuedRequest] = []
        for i in range(3):
            request = InferenceRequest(prompt=f"test {i}")
            future = asyncio.Future()
            queued = QueuedRequest(request=request, future=future, request_id=f"req{i}")
            requests.append(queued)

        batch = Batch(requests=requests, created_at=0.0)
        assert batch.size() == 3
