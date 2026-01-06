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
        await pipeline.initialize()

        async def make_request(i: int) -> str:
            request = InferenceRequest(prompt=f"test {i}")
            response = await pipeline.enqueue(request, f"req{i}")
            return response.text

        tasks = [make_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(isinstance(r, str) for r in results)

        await pipeline.shutdown()

    @pytest.mark.asyncio
    async def test_pipeline_backpressure(self):
        pipeline = InferencePipeline()
        await pipeline.initialize()

        async def make_request(i: int):
            request = InferenceRequest(prompt=f"test {i}")
            try:
                response = await asyncio.wait_for(
                    pipeline.enqueue(request, f"req{i}"), timeout=0.1
                )
                return response
            except asyncio.TimeoutError:
                return None
            except Exception as e:
                if "queue full" in str(e).lower() or "backpressure" in str(e).lower():
                    return "backpressure"
                raise

        tasks = [make_request(i) for i in range(settings.max_in_flight_requests + 10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        backpressure_count = sum(1 for r in results if r == "backpressure" or r is None)
        assert backpressure_count > 0

        await pipeline.shutdown()

    @pytest.mark.asyncio
    async def test_pipeline_batching(self):
        pipeline = InferencePipeline()
        await pipeline.initialize()

        requests = [
            InferenceRequest(prompt=f"test {i}") for i in range(settings.batch_max_size * 2)
        ]

        tasks = [
            pipeline.enqueue(req, f"req{i}") for i, req in enumerate(requests)
        ]
        results = await asyncio.gather(*tasks)

        assert len(results) == len(requests)
        assert all(r.api_version == "v1" for r in results)

        await pipeline.shutdown()
