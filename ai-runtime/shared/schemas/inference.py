from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class InferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    
    api_version: str = Field(default="v1", description="API version")
    prompt: str = Field(..., description="Input prompt text")
    max_tokens: Optional[int] = Field(default=100, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(default=0.7, description="Sampling temperature")


class InferenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    
    api_version: str = Field(default="v1", description="API version")
    text: str = Field(..., description="Generated text")
    request_id: str = Field(..., description="Request identifier for tracing")

