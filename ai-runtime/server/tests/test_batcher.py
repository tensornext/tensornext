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
        try:
            await batcher.start()

            for i in range(3):
                request = InferenceRequest(prompt=f"test {i}")
                future = asyncio.Future()
                queued = QueuedRequest(request=request, future=future, request_id=f"req{i}")
                await input_queue.put(queued)

            await asyncio.sleep(0.2)
            batch = await asyncio.wait_for(output_queue.get(), timeout=1.0)
            assert batch.size() == 3
        finally:
            await batcher.stop()
            await asyncio.sleep(0.1)

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
        try:
            await batcher.start()

            request = InferenceRequest(prompt="test")
            future = asyncio.Future()
            queued = QueuedRequest(request=request, future=future, request_id="req0")
            await input_queue.put(queued)

            await asyncio.sleep(0.15)
            batch = await asyncio.wait_for(output_queue.get(), timeout=1.0)
            assert batch.size() == 1
        finally:
            await batcher.stop()
            await asyncio.sleep(0.1)

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
        try:
            await batcher.start()

            for i in range(5):
                request = InferenceRequest(prompt=f"test {i}")
                future = asyncio.Future()
                queued = QueuedRequest(request=request, future=future, request_id=f"req{i}")
                await input_queue.put(queued)

            await asyncio.sleep(0.3)

            batches: List[Batch] = []
            for _ in range(5):
                try:
                    batch = await asyncio.wait_for(output_queue.get(), timeout=0.5)
                    batches.append(batch)
                except asyncio.TimeoutError:
                    break

            assert len(batches) >= 2
            total_requests = sum(b.size() for b in batches)
            # Allow for last batch that might be in current_batch
            assert total_requests >= 4
        finally:
            await batcher.stop()
            await asyncio.sleep(0.1)


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
