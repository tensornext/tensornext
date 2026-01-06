from typing import Optional
from pydantic import BaseModel, Field


class InferenceRequest(BaseModel):
    prompt: str = Field(..., description="Input prompt text")
    max_tokens: Optional[int] = Field(default=100, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(default=0.7, description="Sampling temperature")


class InferenceResponse(BaseModel):
    text: str = Field(..., description="Generated text")
    request_id: str = Field(..., description="Request identifier for tracing")

