import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from server.app.core.queue import BoundedRequestQueue, QueuedRequest
from server.app.schemas.inference import InferenceRequest, InferenceResponse


class TestBoundedRequestQueue:
    def test_queue_initialization(self):
        queue = BoundedRequestQueue(maxsize=10)
        assert queue._maxsize == 10
        assert queue.empty()

    @pytest.mark.asyncio
    async def test_queue_put_get(self):
        queue = BoundedRequestQueue(maxsize=10)
        request = InferenceRequest(prompt="test")
        future = await queue.put(request, "req0")
        assert not queue.empty()
        assert queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_queue_backpressure(self):
        queue = BoundedRequestQueue(maxsize=2)
        request1 = InferenceRequest(prompt="test1")
        request2 = InferenceRequest(prompt="test2")
        request3 = InferenceRequest(prompt="test3")

        future1 = await queue.put(request1, "req1")
        future2 = await queue.put(request2, "req2")

        assert queue.full()

        future3 = await queue.put(request3, "req3")

        with pytest.raises(Exception):
            await future3

    @pytest.mark.asyncio
    async def test_queue_get(self):
        queue = BoundedRequestQueue(maxsize=10)
        request = InferenceRequest(prompt="test")
        future = await queue.put(request, "req0")

        queued = await queue.get()
        assert queued.request.prompt == "test"
        assert queued.request_id == "req0"
