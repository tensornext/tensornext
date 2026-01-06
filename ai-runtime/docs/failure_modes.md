# Failure Modes

This document describes expected behavior for various failure scenarios in Step-1.

## Server Unreachable

**Scenario:** Client cannot connect to server (network issue, server down, wrong URL).

**Expected Behavior:**
- Client SDK raises `ConnectionError` with descriptive message
- CLI exits with non-zero exit code and error message
- No retry logic in Step-1

**Client Handling:**
```python
try:
    response = client.infer(prompt="test")
except ConnectionError as e:
    # Handle connection failure
```

## GPU Out of Memory (OOM)

**Scenario:** Model inference exceeds available GPU memory.

**Expected Behavior:**
- Server logs error with OOM details
- Returns HTTP 500 with error message
- Server continues running (does not crash)
- Subsequent requests may succeed if memory is freed

**Note:** Step-1 does not implement memory management or request queuing beyond basic concurrency limits.

## Model Load Failure

**Scenario:** Model fails to load during server startup (missing file, corrupted model, incompatible CUDA version).

**Expected Behavior:**
- Server logs error during startup
- Server may start but inference requests will fail
- Health check endpoint returns 200 (server is running)
- Inference endpoint returns HTTP 500

**Note:** Step-1 uses mock mode by default. Real model loading is a placeholder.

## Request Overload

**Scenario:** More concurrent requests than `MAX_CONCURRENT_REQUESTS` (default: 2).

**Expected Behavior:**
- Excess requests receive HTTP 429 (Too Many Requests)
- Response includes message: "Request limit exceeded, please try again later"
- Server logs warning for rejected requests
- No queuing - requests are rejected immediately

**Configuration:** Set `MAX_CONCURRENT_REQUESTS` environment variable to adjust limit.

## Invalid Schema

**Scenario:** Client sends request with unknown fields or invalid types.

**Expected Behavior:**
- FastAPI validation rejects request before handler execution
- Returns HTTP 422 (Unprocessable Entity)
- Response includes validation error details
- Server logs validation error

**Schema Rules:**
- Unknown fields are rejected (`extra="forbid"`)
- Type validation is strict (`strict=True`)
- Required fields must be present

## Request Timeout

**Scenario:** Inference takes longer than client timeout.

**Expected Behavior:**
- Client SDK raises `TimeoutError`
- Server continues processing (no cancellation)
- Client can retry with longer timeout

**Configuration:** Client timeout is configurable in `AIRuntimeClient` constructor (default: 30 seconds).

## Multiple GPUs Detected

**Scenario:** Server detects more than one GPU when not in mock mode.

**Expected Behavior:**
- Server logs warning during model loader initialization
- Server continues running normally
- Only first GPU is used (Step-1 assumption)
- No error returned to client

**Note:** Multi-GPU support will be added in Step-2.

