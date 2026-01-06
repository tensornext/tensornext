# TensorNext - Distributed AI Runtime PoC

A minimal but realistic proof-of-concept distributed AI runtime demonstrating client-server inference with CPU/GPU scheduling.

## Architecture

This PoC consists of:

- **Server** (Ubuntu): FastAPI service that schedules and executes inference on CPU or GPU
- **Client** (Windows/any): Simple CLI application that sends inference requests
- **Model**: Small PyTorch MLP that supports both CPU and CUDA execution

### Components

**Server (`server/`)**:
- `server.py` - FastAPI entrypoint and HTTP endpoints
- `scheduler.py` - Decides execution target (CPU vs GPU) based on availability and constraints
- `executor.py` - Runs inference on the selected device
- `telemetry.py` - Collects execution metadata (latency, device, GPU memory)
- `models/simple_model.py` - Simple PyTorch MLP model

**Client (`client/`)**:
- `client.py` - CLI application for sending inference requests

## Requirements

- Python 3.11+
- CUDA-capable GPU (for GPU execution) - Server only
- Network connectivity between client and server

## Installation

### Server (Ubuntu)

**Quick Setup (Recommended):**

1. Install Python 3.11+ and CUDA toolkit (if using GPU)

2. Install `python3-venv` (if not already installed):
```bash
sudo apt install python3.12-venv
```

3. Run the setup script:
```bash
./setup.sh
```

The script will automatically:
- Create a virtual environment
- Install all dependencies
- Install the package in editable mode (if `ai-runtime/` exists)
- Verify CUDA availability

**Manual Setup:**

1. Install Python 3.11+ and CUDA toolkit (if using GPU)

2. Install `python3-venv` (if not already installed):
```bash
sudo apt install python3.12-venv
```

3. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. (Optional) Install the package in editable mode:
```bash
cd ai-runtime
pip install -e .
cd ..
```

6. Verify CUDA availability (optional):
```bash
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### Client (Windows)

1. Install Python 3.11+

2. Create and activate a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running the Server

On the Ubuntu machine:

**Make sure the virtual environment is activated first:**
```bash
source venv/bin/activate
```

**Option 1: Run the server script directly (recommended):**
```bash
cd server
python server.py
```

**Option 2: Use uvicorn directly:**
```bash
uvicorn server.server:app --host 0.0.0.0 --port 8000
```

The server will start on `0.0.0.0:8000` (accessible from LAN).

**Note**: For localhost-only access, modify `server.py` to use `host="127.0.0.1"` or use `--host 127.0.0.1` with uvicorn.

### Running the Client

On the Windows machine (or any client):

```bash
cd client
python client.py --server http://<SERVER_IP>:8000
```

Replace `<SERVER_IP>` with the Ubuntu server's IP address (e.g., `192.168.1.100`).

### Client Options

```bash
# Basic usage (prefers GPU)
python client.py --server http://192.168.1.100:8000

# Force CPU execution
python client.py --server http://192.168.1.100:8000 --no-prefer-gpu

# Send multiple requests
python client.py --server http://192.168.1.100:8000 --count 5

# Custom batch size and input dimension
python client.py --server http://192.168.1.100:8000 --batch-size 4 --input-dim 256

# Set minimum GPU memory requirement
python client.py --server http://192.168.1.100:8000 --min-gpu-memory 500.0
```

### Testing CPU vs GPU Routing

1. **Test GPU routing** (default):
   ```bash
   python client.py --server http://<SERVER_IP>:8000 --prefer-gpu
   ```
   Expected: Device should be `cuda:0` (if GPU available and has sufficient memory)

2. **Test CPU routing**:
   ```bash
   python client.py --server http://<SERVER_IP>:8000 --no-prefer-gpu
   ```
   Expected: Device should be `cpu`

3. **Test GPU fallback** (when GPU memory is low):
   ```bash
   python client.py --server http://<SERVER_IP>:8000 --prefer-gpu --min-gpu-memory 10000.0
   ```
   Expected: Falls back to CPU if GPU doesn't have enough free memory

## API Endpoints

### `GET /health`

Health check endpoint. Returns server status and device information.

**Response**:
```json
{
  "status": "ready",
  "cuda_available": true,
  "current_device": "cuda:0",
  "gpu_memory_free_mb": 20480.5
}
```

### `POST /predict`

Main inference endpoint.

**Request**:
```json
{
  "input_data": [[0.1, 0.2, ...]],  // 2D array: batch_size x input_dim
  "prefer_gpu": true,
  "min_gpu_memory_mb": 100.0
}
```

**Response**:
```json
{
  "output": [[0.5, 0.3, ...]],  // Model output
  "device": "cuda:0",
  "latency_ms": 12.34,
  "gpu_memory_mb": 256.78
}
```

## Project Structure

```
tensornext/
├── server/
│   ├── __init__.py
│   ├── server.py          # FastAPI entrypoint
│   ├── scheduler.py       # CPU/GPU scheduling logic
│   ├── executor.py        # Inference execution
│   ├── telemetry.py       # Execution metadata collection
│   └── models/
│       ├── __init__.py
│       └── simple_model.py  # PyTorch model definition
├── client/
│   └── client.py          # CLI client application
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Design Decisions

### Separation of Concerns

- **Scheduler**: Pure scheduling logic, no execution
- **Executor**: Pure execution logic, no scheduling
- **Telemetry**: Isolated metric collection
- **Server**: Orchestration and HTTP handling

### Device Management

- Model is loaded once at startup on an initial device
- Executor can switch devices per-request if needed
- This allows for dynamic routing without reloading the model

### Extensibility

The codebase is structured to easily extend:
- Add more sophisticated scheduling policies
- Support multiple GPU devices
- Add batching support
- Implement request queuing
- Add authentication/authorization

## Limitations (Non-Goals)

This PoC intentionally does NOT include:
- Authentication/authorization
- Request persistence
- Distributed training
- Request batching (single request at a time)
- Production-grade error handling
- Load balancing across multiple servers

## Troubleshooting

### Server won't start

- Check if port 8000 is available: `netstat -tuln | grep 8000`
- Verify Python version: `python --version` (should be 3.11+)
- Check dependencies: `pip list | grep fastapi`

### GPU not detected

- Verify CUDA installation: `nvidia-smi`
- Check PyTorch CUDA support: `python -c "import torch; print(torch.cuda.is_available())"`
- Ensure CUDA-compatible PyTorch is installed

### Connection refused

- Verify server is running and accessible
- Check firewall settings on Ubuntu server
- Ensure server is bound to `0.0.0.0` (not just `127.0.0.1`)
- Verify IP address and port are correct

### GPU memory errors

- Reduce `min_gpu_memory_mb` requirement
- Use `--no-prefer-gpu` to force CPU execution
- Check GPU memory usage: `nvidia-smi`

## Next Steps

This PoC serves as a foundation for:
- Multi-GPU support and load balancing
- Request queuing and batching
- Model versioning and A/B testing
- Distributed inference across multiple servers
- Advanced scheduling policies (priority queues, cost-based routing)
- Observability and monitoring integration
