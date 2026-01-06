# AI Runtime PoC

Distributed AI runtime system with Windows client and Linux GPU server.

## Prerequisites

- Python 3.11+
- Ubuntu server with NVIDIA GPU (for server)
- Windows client (no GPU required)

## Installation

```bash
pip install -e .
```

## Running the Server

```bash
uvicorn server.app.main:app --host 0.0.0.0 --port 8000
```

Or using the Makefile:

```bash
make server
```

## Running the Client

```bash
python -m client.cli.submit_job --prompt "Hello, world!"
```

Or with custom server URL:

```bash
python -m client.cli.submit_job --url http://server-ip:8000 --prompt "Your prompt here"
```

## Environment Variables

Copy `.env.example` to `.env` and configure as needed.

## Project Structure

- `server/` - FastAPI server application
- `client/` - Client SDK and CLI
- `shared/` - Shared schemas and types

## Step-1 Completion

Step-1 provides a hardened foundation with API contract locking, safety mechanisms, and comprehensive documentation.

## Step-2 Scaling

Step-2 introduces request batching, multi-GPU execution (single node), and GPU-aware scheduling to increase throughput and concurrency.

### Features

- **Request Batching:** Dynamic batching with configurable batch size and latency thresholds
- **Multi-GPU Support:** Automatic detection and utilization of all available GPUs (single node)
- **GPU-Aware Scheduling:** Intelligent batch assignment to available GPU workers
- **Backpressure:** HTTP 429 returned when request queue is full
- **Mock-GPU Mode:** CI-friendly mode with 2 mock GPUs (no hardware required)

### Running Mock Inference (No GPU Required)

```bash
export USE_MOCK_MODEL=true
uvicorn server.app.main:app --host 0.0.0.0 --port 8000
```

Or using the Makefile:

```bash
USE_MOCK_MODEL=true make server
```

In mock mode, the server simulates 2 GPUs for testing batching and scheduling behavior.

### Running Real GPU Inference

```bash
uvicorn server.app.main:app --host 0.0.0.0 --port 8000
```

The server automatically detects all available GPUs and creates one worker per GPU. Each GPU runs its own model instance.

### Configuration

Environment variables (set in `.env` or export):

**Step-1 Variables:**
- `USE_MOCK_MODEL`: Enable mock mode (no GPU required)
- `MAX_CONCURRENT_REQUESTS`: Legacy setting (Step-2 uses MAX_IN_FLIGHT_REQUESTS)
- `LOG_LEVEL`: Logging level (default: INFO)
- `PORT`: Server port (default: 8000)
- `HOST`: Server host (default: 0.0.0.0)

**Step-2 Variables:**
- `BATCH_MAX_SIZE`: Maximum requests per batch (default: 8)
- `BATCH_MAX_LATENCY_MS`: Maximum time to wait before flushing a partial batch (default: 50)
- `MAX_IN_FLIGHT_REQUESTS`: Maximum requests in the queue before backpressure (default: 100)

### Architecture

Step-2 implements a pipeline architecture:

1. **Request Queue:** Bounded async queue that enqueues incoming API requests
2. **Dynamic Batcher:** Collects requests into batches based on size and latency thresholds
3. **Scheduler:** Assigns batches to available GPU workers (no oversubscription)
4. **GPU Workers:** One worker per GPU, each with its own model instance
5. **Backpressure:** Queue full condition propagates to API as HTTP 429

### API Contract

- **Version:** All requests/responses include `api_version: "v1"`
- **Strict Validation:** Unknown fields are rejected
- **Backpressure:** HTTP 429 returned when request queue is full
- **Compatibility:** Step-2 maintains full backward compatibility with Step-1 client API

### Documentation

- **Failure Modes:** See `docs/failure_modes.md` for expected behavior in error scenarios
- **Roadmap:** See `docs/roadmap.md` for Step-2 goals and non-goals
- **Step-1 Summary:** See `docs/step1_complete.md` for release notes

## CI/CD

GitHub Actions validates Step-1 and Step-2 end-to-end on every push and PR:
- Server boots in mock mode (no GPU required)
- Health and inference endpoints are tested
- Client SDK integration is verified
- Shared schema compatibility is checked
- Batching and multi-GPU scheduling are tested with mock model

