# Roadmap

## Step-1 (Current)

**Status:** Complete

**Scope:**
- Basic FastAPI server with health and inference endpoints
- Client SDK and CLI
- Shared schema definitions
- Mock model support for testing
- Single-GPU assumption
- Basic concurrency limiting (backpressure)
- API versioning (v1)
- Strict schema validation

**Limitations:**
- No batching
- No multi-GPU support
- No streaming responses
- No authentication
- No request queuing (immediate rejection on overload)
- No memory management

## Step-2 (Planned)

**Goals:**
- **Batching:** Batch multiple inference requests for improved GPU utilization
- **Multi-GPU:** Distribute inference across multiple GPUs
- **Concurrency:** Enhanced concurrency control with queuing
- **Performance:** Optimize throughput and latency

**Non-Goals:**
- Authentication/authorization (planned for Step-3)
- Streaming responses (planned for Step-3)
- Model versioning (planned for Step-3)
- Distributed inference across servers (planned for Step-4)

**Breaking Changes:**
- None expected - Step-2 will maintain Step-1 API compatibility
- New optional fields may be added to requests/responses
- Backward compatibility guaranteed for v1 API

**Implementation Areas:**
1. Batch scheduler for grouping requests
2. Multi-GPU model sharding/parallelism
3. Request queue with priority support
4. Enhanced telemetry and monitoring
5. Performance benchmarking and optimization

## Step-3 (Future)

**Planned Features:**
- Authentication and authorization
- Streaming responses (Server-Sent Events)
- Model versioning and A/B testing
- Enhanced error handling and retry logic

## Step-4 (Future)

**Planned Features:**
- Distributed inference across multiple servers
- Load balancing and service discovery
- Advanced scheduling algorithms
- Resource pooling and auto-scaling

