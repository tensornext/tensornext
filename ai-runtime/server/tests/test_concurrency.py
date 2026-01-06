import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from server.app.core.pipeline import InferencePipeline
from server.app.schemas.inference import InferenceRequest
from server.app.core.config import settings


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_pipeline_handles_concurrent_requests(self):
        pipeline = InferencePipeline()
        try:
            await pipeline.initialize()

            async def make_request(i: int) -> str:
                request = InferenceRequest(prompt=f"test {i}")
                response = await asyncio.wait_for(
                    pipeline.enqueue(request, f"req{i}"), timeout=5.0
                )
                return response.text

            tasks = [make_request(i) for i in range(10)]
            results = await asyncio.gather(*tasks)

            assert len(results) == 10
            assert all(isinstance(r, str) for r in results)
        finally:
            await pipeline.shutdown()
            await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_pipeline_backpressure(self):
        pipeline = InferencePipeline()
        try:
            await pipeline.initialize()

            # Test that queue exists and has a max size
            assert pipeline._request_queue is not None
            assert pipeline._request_queue._maxsize > 0

            # Try to enqueue a request - should work
            request = InferenceRequest(prompt="test")
            response = await asyncio.wait_for(
                pipeline.enqueue(request, "req0"), timeout=5.0
            )
            assert response.api_version == "v1"
            
            # Test that backpressure mechanism exists (queue can be full)
            # This is a basic smoke test - actual backpressure depends on load
        finally:
            await pipeline.shutdown()
            await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_pipeline_batching(self):
        pipeline = InferencePipeline()
        try:
            await pipeline.initialize()

            requests = [
                InferenceRequest(prompt=f"test {i}") for i in range(settings.batch_max_size * 2)
            ]

            async def enqueue_with_timeout(req, req_id):
                return await asyncio.wait_for(
                    pipeline.enqueue(req, req_id), timeout=5.0
                )

            tasks = [
                enqueue_with_timeout(req, f"req{i}") for i, req in enumerate(requests)
            ]
            results = await asyncio.gather(*tasks)

            assert len(results) == len(requests)
            assert all(r.api_version == "v1" for r in results)
        finally:
            await pipeline.shutdown()
            await asyncio.sleep(0.1)
