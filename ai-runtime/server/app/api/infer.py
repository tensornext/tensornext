from fastapi import APIRouter, HTTPException
from server.app.schemas.inference import InferenceRequest, InferenceResponse
from server.app.core.logging import get_request_id
from server.app.core.pipeline import pipeline
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/infer", response_model=InferenceResponse)
async def infer(request: InferenceRequest) -> InferenceResponse:
    request_id = get_request_id()
    logger.info(f"Received inference request: prompt_length={len(request.prompt)}")
    
    try:
        response = await pipeline.enqueue(request, request_id)
        logger.info(f"Inference completed: response_length={len(response.text)}")
        return response
    except RuntimeError as e:
        if "queue full" in str(e).lower() or "backpressure" in str(e).lower():
            logger.warning(f"Request {request_id} rejected: queue full")
            raise HTTPException(status_code=429, detail="Request limit exceeded, please try again later")
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")
    except Exception as e:
        logger.error(f"Inference failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

