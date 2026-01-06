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

### Running Mock Inference (No GPU Required)

```bash
export USE_MOCK_MODEL=true
uvicorn server.app.main:app --host 0.0.0.0 --port 8000
```

Or using the Makefile:

```bash
USE_MOCK_MODEL=true make server
```

### Running Real GPU Inference

```bash
uvicorn server.app.main:app --host 0.0.0.0 --port 8000
```

The server will detect available GPUs and log warnings if multiple GPUs are present (Step-1 assumes single-GPU usage).

### Configuration

Environment variables (set in `.env` or export):

- `USE_MOCK_MODEL`: Enable mock mode (no GPU required)
- `MAX_CONCURRENT_REQUESTS`: Maximum concurrent inference requests (default: 2)
- `LOG_LEVEL`: Logging level (default: INFO)
- `PORT`: Server port (default: 8000)
- `HOST`: Server host (default: 0.0.0.0)

### API Contract

- **Version:** All requests/responses include `api_version: "v1"`
- **Strict Validation:** Unknown fields are rejected
- **Backpressure:** HTTP 429 returned when concurrency limit exceeded

### Documentation

- **Failure Modes:** See `docs/failure_modes.md` for expected behavior in error scenarios
- **Roadmap:** See `docs/roadmap.md` for Step-2 goals and non-goals
- **Step-1 Summary:** See `docs/step1_complete.md` for release notes

## CI/CD

GitHub Actions validates Step-1 end-to-end on every push and PR:
- Server boots in mock mode (no GPU required)
- Health and inference endpoints are tested
- Client SDK integration is verified
- Shared schema compatibility is checked

