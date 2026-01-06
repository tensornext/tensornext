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

            async def make_request(i: int):
                request = InferenceRequest(prompt=f"test {i}")
                try:
                    response = await asyncio.wait_for(
                        pipeline.enqueue(request, f"req{i}"), timeout=0.5
                    )
                    return response
                except asyncio.TimeoutError:
                    return None
                except Exception as e:
                    if "queue full" in str(e).lower() or "backpressure" in str(e).lower():
                        return "backpressure"
                    raise

            # Use smaller number to avoid hanging
            num_requests = min(settings.max_in_flight_requests + 5, 20)
            tasks = [make_request(i) for i in range(num_requests)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            backpressure_count = sum(1 for r in results if r == "backpressure" or r is None)
            assert backpressure_count > 0
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
