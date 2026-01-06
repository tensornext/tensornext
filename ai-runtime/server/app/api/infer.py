from fastapi import APIRouter, HTTPException
from app.schemas.inference import InferenceRequest, InferenceResponse
from app.models.loader import ModelLoader
from app.core.logging import get_request_id
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

model_loader = ModelLoader()


@router.post("/infer", response_model=InferenceResponse)
async def infer(request: InferenceRequest) -> InferenceResponse:
    request_id = get_request_id()
    logger.info(f"Received inference request: prompt_length={len(request.prompt)}")
    
    try:
        text = model_loader.generate(
            prompt=request.prompt,
            max_tokens=request.max_tokens if request.max_tokens is not None else 100,
            temperature=request.temperature if request.temperature is not None else 0.7,
        )
        logger.info(f"Inference completed: response_length={len(text)}")
        return InferenceResponse(text=text, request_id=request_id)
    except Exception as e:
        logger.error(f"Inference failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

