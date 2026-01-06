import asyncio
import logging
from typing import Optional, Generic, TypeVar, Callable, Awaitable
from dataclasses import dataclass
from server.app.schemas.inference import InferenceRequest, InferenceResponse

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class QueuedRequest:
    request: InferenceRequest
    future: asyncio.Future[InferenceResponse]
    request_id: str


class BoundedRequestQueue(Generic[T, R]):
    def __init__(
        self,
        maxsize: int,
        on_item: Optional[Callable[[T], Awaitable[R]]] = None,
    ) -> None:
        self._queue: asyncio.Queue[QueuedRequest] = asyncio.Queue(maxsize=maxsize)
        self._maxsize = maxsize
        self._on_item = on_item

    async def put(
        self, request: InferenceRequest, request_id: str
    ) -> asyncio.Future[InferenceResponse]:
        future: asyncio.Future[InferenceResponse] = asyncio.Future()
        queued = QueuedRequest(request=request, future=future, request_id=request_id)
        try:
            self._queue.put_nowait(queued)
            logger.debug(f"Request {request_id} enqueued")
        except asyncio.QueueFull:
            logger.warning(f"Request {request_id} rejected: queue full")
            future.set_exception(
                RuntimeError("Request queue full, backpressure applied")
            )
        return future

    async def get(self) -> QueuedRequest:
        return await self._queue.get()

    def get_nowait(self) -> Optional[QueuedRequest]:
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def qsize(self) -> int:
        return self._queue.qsize()

    def full(self) -> bool:
        return self._queue.full()

    def empty(self) -> bool:
        return self._queue.empty()
