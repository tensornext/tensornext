"""
FastAPI server for distributed AI inference.

This is the main entrypoint for the inference server. It handles HTTP requests,
coordinates scheduling and execution, and returns results with telemetry.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import torch
import uvicorn

from server.scheduler import Scheduler
from server.executor import Executor
from server.telemetry import TelemetryCollector
from server.models.simple_model import create_model


# Request/Response models
class InferenceRequest(BaseModel):
    """Request model for inference endpoint."""
    input_data: List[List[float]]  # 2D array: batch_size x input_dim
    prefer_gpu: bool = True
    min_gpu_memory_mb: float = 100.0


class InferenceResponse(BaseModel):
    """Response model for inference endpoint."""
    output: List[List[float]]  # Model output
    device: str  # Device used for execution
    latency_ms: float  # End-to-end latency
    gpu_memory_mb: Optional[float] = None  # GPU memory used (if applicable)


# Initialize FastAPI app
app = FastAPI(
    title="Distributed AI Runtime PoC",
    description="Minimal proof-of-concept for distributed AI inference",
    version="0.1.0"
)

# Global components (initialized at startup)
scheduler: Optional[Scheduler] = None
executor: Optional[Executor] = None


@app.on_event("startup")
async def startup_event():
    """
    Initialize server components at startup.
    
    This loads the model and initializes the scheduler and executor.
    The model is loaded once and reused for all requests.
    """
    global scheduler, executor
    
    print("Initializing server components...")
    
    # Initialize scheduler
    scheduler = Scheduler(default_gpu_device="cuda:0")
    
    # Determine initial device (will be updated per request)
    initial_device = scheduler.schedule(prefer_gpu=True)
    print(f"Initial device: {initial_device}")
    
    # Load model on initial device
    model = create_model(device=initial_device)
    executor = Executor(model, device=initial_device)
    
    print(f"Server ready. CUDA available: {scheduler.is_gpu_available()}")
    if scheduler.is_gpu_available():
        free_mem = scheduler.get_gpu_memory_free_mb("cuda:0")
        if free_mem is not None:
            print(f"GPU memory free: {free_mem:.2f} MB")
        else:
            print("GPU memory free: Unable to retrieve")


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Server status and device information
    """
    if scheduler is None or executor is None:
        return {"status": "not_ready"}
    
    info = {
        "status": "ready",
        "cuda_available": scheduler.is_gpu_available(),
        "current_device": executor.get_device()
    }
    
    if scheduler.is_gpu_available():
        free_mem = scheduler.get_gpu_memory_free_mb("cuda:0")
        if free_mem is not None:
            info["gpu_memory_free_mb"] = free_mem
    
    return info


@app.post("/predict", response_model=InferenceResponse, response_model_exclude_none=True)
async def predict(request: InferenceRequest):
    """
    Main inference endpoint.
    
    This endpoint:
    1. Receives inference request with input data and constraints
    2. Schedules execution target (CPU/GPU)
    3. Executes inference
    4. Collects telemetry
    5. Returns results with metadata
    
    Args:
        request: Inference request with input data and preferences
    
    Returns:
        Inference response with output and execution metadata
    """
    if scheduler is None or executor is None:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    # Initialize telemetry
    telemetry = TelemetryCollector()
    telemetry.start()
    
    try:
        # Convert input to tensor
        input_tensor = torch.tensor(request.input_data, dtype=torch.float32)
        
        # Make scheduling decision
        target_device = scheduler.schedule(
            prefer_gpu=request.prefer_gpu,
            min_gpu_memory_mb=request.min_gpu_memory_mb
        )
        
        telemetry.set_device(target_device)
        
        # Execute inference on the target device atomically
        # Pass device explicitly to avoid race conditions with concurrent requests
        output_tensor = executor.execute(input_tensor, device=target_device)
        
        # Move output back to CPU for serialization
        output_cpu = output_tensor.cpu()
        
        # Stop telemetry
        telemetry.stop()
        
        # Prepare response
        telemetry_dict = telemetry.to_dict()
        
        response = InferenceResponse(
            output=output_cpu.tolist(),
            device=telemetry_dict["device"],
            latency_ms=telemetry_dict["latency_ms"],
            gpu_memory_mb=telemetry_dict.get("gpu_memory_mb")
        )
        
        return response
        
    except Exception as e:
        telemetry.stop()
        raise HTTPException(status_code=500, detail=f"Execution error: {str(e)}")


if __name__ == "__main__":
    # Run the server
    # Default: localhost:8000
    # For LAN access, use host="0.0.0.0"
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )

