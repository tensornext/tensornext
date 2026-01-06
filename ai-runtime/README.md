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

## Running the Gateway (Step-3)

The gateway is a centralized service that routes requests to multiple inference nodes.

```bash
uvicorn gateway.app.main:app --host 0.0.0.0 --port 8001
```

Or using Python module:

```bash
python -m gateway
```

## Running Inference Nodes (Step-3)

Inference nodes register with the gateway on startup and send periodic heartbeats.

**Node 1:**
```bash
export GATEWAY_URL=http://localhost:8001
export NODE_ID=node-1
export NODE_MAX_CAPACITY=100
uvicorn server.app.main:app --host 0.0.0.0 --port 8000
```

**Node 2:**
```bash
export GATEWAY_URL=http://localhost:8001
export NODE_ID=node-2
export NODE_MAX_CAPACITY=100
uvicorn server.app.main:app --host 0.0.0.0 --port 8002
```

## Running Single Node (Step-2)

For single-node operation without gateway:

```bash
uvicorn server.app.main:app --host 0.0.0.0 --port 8000
```

Or using the Makefile:

```bash
make server
```

## Running the Client

**With Gateway (Step-3):**
```bash
python -m client.cli.submit_job --url http://gateway-ip:8001 --prompt "Hello, world!"
```

**Direct to Node (Step-2):**
```bash
python -m client.cli.submit_job --url http://server-ip:8000 --prompt "Hello, world!"
```

If no URL is specified, the client defaults to `http://localhost:8000`.

## Environment Variables

Copy `.env.example` to `.env` and configure as needed.

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

**Step-3 Gateway Variables:**
- `REQUEST_TIMEOUT_SEC`: Request timeout for node calls (default: 30)
- `NODE_EVICTION_TIMEOUT_SEC`: Time before marking node unhealthy (default: 10)
- `HEARTBEAT_INTERVAL_SEC`: Heartbeat check interval (default: 5)

**Step-3 Node Variables:**
- `GATEWAY_URL`: Gateway base URL (required for multi-node mode)
- `NODE_ID`: Unique node identifier (required for multi-node mode)
- `NODE_MAX_CAPACITY`: Maximum concurrent requests for this node (default: 100)
- `HEARTBEAT_INTERVAL_SEC`: Heartbeat send interval (default: 5)

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

## Step-3 Multi-Node Inference

Step-3 enables distributed inference across multiple inference nodes using a centralized gateway.

### Features

- **Gateway Service:** Centralized request routing without GPU logic
- **Node Registration:** Automatic self-registration on startup
- **Health-Aware Routing:** Least-loaded policy with unhealthy node exclusion
- **Heartbeat Monitoring:** Periodic health checks with automatic eviction
- **Failure Handling:** Timeout detection and node eviction
- **Transparent Proxying:** Gateway forwards requests without modification

### Architecture

Step-3 adds a gateway layer:

1. **Gateway:** FastAPI service that routes requests to nodes
   - `/health`: Gateway health check
   - `/infer`: Proxy endpoint (forwards to nodes)
   - `/register`: Node registration endpoint
   - `/heartbeat/{node_id}`: Heartbeat endpoint

2. **Node Registry:** Tracks registered nodes with health status
   - Load tracking per node
   - Heartbeat monitoring
   - Automatic eviction of stale nodes

3. **Router:** Selects nodes using least-loaded policy
   - Considers available capacity
   - Skips unhealthy nodes
   - Deterministic selection

4. **Registry Client:** Node-side registration and heartbeat
   - Startup registration
   - Periodic heartbeat sending
   - Graceful shutdown

### Multi-Node Setup

1. **Start Gateway:**
   ```bash
   uvicorn gateway.app.main:app --host 0.0.0.0 --port 8001
   ```

2. **Start Node 1:**
   ```bash
   export GATEWAY_URL=http://localhost:8001
   export NODE_ID=node-1
   uvicorn server.app.main:app --host 0.0.0.0 --port 8000
   ```

3. **Start Node 2:**
   ```bash
   export GATEWAY_URL=http://localhost:8001
   export NODE_ID=node-2
   uvicorn server.app.main:app --host 0.0.0.0 --port 8002
   ```

4. **Send Requests to Gateway:**
   ```bash
   python -m client.cli.submit_job --url http://localhost:8001 --prompt "test"
   ```

### Routing Behavior

- Gateway selects the node with the highest available capacity
- Nodes report their current load and maximum capacity
- Unhealthy nodes (stale heartbeat) are excluded from routing
- Load is incremented when routing, decremented on completion

### Failure Handling

- **Node Timeout:** Gateway returns HTTP 504 after `REQUEST_TIMEOUT_SEC`
- **Node Failure:** Gateway returns HTTP 500/503 based on node response
- **No Healthy Nodes:** Gateway returns HTTP 503
- **Stale Heartbeat:** Node marked unhealthy after `NODE_EVICTION_TIMEOUT_SEC`
- **Node Eviction:** Node removed after 2x eviction timeout

### Compatibility

- **Client API:** No changes required (same `/infer` endpoint)
- **Request/Response:** Identical schemas (transparent proxying)
- **Step-2 Nodes:** Nodes retain all Step-2 batching behavior
- **Backward Compatible:** Nodes can run standalone without gateway

### Documentation

- **Failure Modes:** See `docs/failure_modes.md` for expected behavior in error scenarios
- **Roadmap:** See `docs/roadmap.md` for Step-2 goals and non-goals
- **Step-1 Summary:** See `docs/step1_complete.md` for release notes

## Project Structure

- `server/` - FastAPI inference server (nodes)
- `gateway/` - FastAPI gateway service (Step-3)
- `client/` - Client SDK and CLI
- `shared/` - Shared schemas and types

## CI/CD

GitHub Actions validates Step-1, Step-2, and Step-3 end-to-end on every push and PR:
- Server boots in mock mode (no GPU required)
- Health and inference endpoints are tested
- Client SDK integration is verified
- Shared schema compatibility is checked
- Batching and multi-GPU scheduling are tested with mock model
- Gateway routing and node registration are tested

