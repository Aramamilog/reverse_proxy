# Roadmap

## ✅ Implemented

### Networking

- TCP server built with `asyncio.start_server`
- HTTP/1.1 request parsing
- HTTP/1.1 response parsing
- Request body streaming
- Response body streaming
- Client HTTP Keep-Alive
- Upstream TCP connection pooling
- Connection reuse
- Backpressure support (`await writer.drain()`)

### Load Balancing

- Round-Robin load balancing
- Per-upstream connection pools
- Per-upstream concurrency limits
- Global client connection limit

### Configuration

- YAML configuration
- Configurable connect timeout
- Configurable read timeout
- Configurable write timeout
- Configurable total request timeout

### Performance

- Load testing with k6
- asyncio implementation
- Thread implementation
- Processes + Threads implementation
- Processes + Async implementation
- uvloop benchmark

---

## 🚧 Future Improvements

### HTTP

- Transfer-Encoding: chunked
- HTTP/2 support
- HTTPS support

### Reliability

- Health checks
- Retry policy
- Circuit breaker
- Rate limiting

### Operations

- Metrics endpoint
- Dynamic upstream discovery
- Configuration hot reload (SIGHUP)

### Architecture

- Evolve the current Async implementation into a production-grade multi-process asyncio reverse proxy.
- Improve connection lifecycle management.
- Add graceful worker restart.
- Introduce smarter upstream health monitoring.

---

## 🎯 Learning Goals

This project was created to understand how a reverse proxy works internally instead of relying on existing frameworks.

Topics covered during development:

- asyncio event loop
- TCP networking
- HTTP/1.1 protocol
- Coroutines
- Tasks
- Streaming
- Backpressure
- Connection pooling
- HTTP Keep-Alive
- Load balancing
- Timeout management
- Thread-based concurrency
- Process-based concurrency
- Async vs Threads vs Processes
- Benchmarking with k6
- Performance analysis
- Reverse proxy architecture

---

## 📈 Current Status

The project successfully demonstrates four different reverse proxy implementations:

- Async
- Threads
- Processes + Threads
- Processes + Async

The best benchmark results were achieved by the **Processes + Async** implementation.

The **Async** implementation remains the primary reference implementation because of its simplicity and serves as the foundation for future improvements toward a production-ready multi-process asyncio architecture.