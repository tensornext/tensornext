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

## CI/CD

GitHub Actions validates Step-1 end-to-end on every push and PR:
- Server boots in mock mode (no GPU required)
- Health and inference endpoints are tested
- Client SDK integration is verified
- Shared schema compatibility is checked

