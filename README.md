# Async Reverse Proxy (MVP)

Educational reverse proxy server implemented with **Python asyncio**.

The goal of this project is to understand how modern reverse proxies work by implementing core networking concepts from scratch: TCP servers, HTTP parsing, connection pooling, keep-alive, streaming, load balancing, timeout management, and benchmarking.

---

# Features

- TCP server built with `asyncio.start_server`
- HTTP/1.1 request parsing
- HTTP/1.1 response parsing
- Client HTTP Keep-Alive
- Upstream TCP connection pooling
- Connection reuse
- Request body streaming
- Response body streaming
- Backpressure support (`await writer.drain()`)
- Round-Robin load balancing
- YAML configuration
- Configurable timeouts
  - Connect
  - Read
  - Write
  - Total request
- Global client connection limit
- Per-upstream connection pools
- Per-upstream concurrency limits
- Load testing with k6
- Optional uvloop benchmark

---

# Architecture

```text
                      Client
                         │
                         ▼
             +-----------------------+
             |   Async Reverse Proxy |
             +-----------------------+
                    │
      ┌─────────────┼─────────────┐
      ▼             ▼             ▼             ▼
+------------+ +------------+ +------------+ +------------+
| Upstream 1 | | Upstream 2 | | Upstream 3 | | Upstream 4 |
|   :9001    | |   :9002    | |   :9003    | |   :9004    |
+------------+ +------------+ +------------+ +------------+

Each upstream owns:
• TCP connection pool
• Concurrency semaphore
```

---

# Configuration

Example `config.yaml`

```yaml
listen:
  host: "127.0.0.1"
  port: 8000

upstreams:
  - host: "127.0.0.1"
    port: 9001
    pool_size: 50
    concurrency_limit: 50

  - host: "127.0.0.1"
    port: 9002
    pool_size: 50
    concurrency_limit: 50

  - host: "127.0.0.1"
    port: 9003
    pool_size: 50
    concurrency_limit: 50

  - host: "127.0.0.1"
    port: 9004
    pool_size: 50
    concurrency_limit: 50

timeouts:
  connect_ms: 1000
  read_ms: 15000
  write_ms: 15000
  total_ms: 30000

limits:
  max_client_conns: 200

logging:
  level: info
```

---

# Run Upstreams

Start four upstream servers.

```bash
PORT=9001 python tests/echo_app.py
PORT=9002 python tests/echo_app.py
PORT=9003 python tests/echo_app.py
PORT=9004 python tests/echo_app.py
```

---

# Run Reverse Proxy

```bash
python proxy/main.py
```

Proxy listens on

```text
127.0.0.1:8000
```

---

# Test Upstreams

### Basic endpoint

```bash
curl http://127.0.0.1:9001/
curl http://127.0.0.1:9002/
curl http://127.0.0.1:9003/
curl http://127.0.0.1:9004/
```

### Echo endpoint

```bash
curl -X POST http://127.0.0.1:9001/echo -d "hello world"
```

### Slow endpoint

```bash
time curl "http://127.0.0.1:9001/slow?delay=3"
```

### Streaming endpoint

```bash
curl http://127.0.0.1:9001/stream
```

### Large response

```bash
curl "http://127.0.0.1:9001/big?size_mb=50" -o /dev/null
```

---

# Test Reverse Proxy

Replace upstream port with **8000**.

```bash
curl http://127.0.0.1:8000/
```

```bash
curl -X POST http://127.0.0.1:8000/echo -d "hello world"
```

```bash
time curl "http://127.0.0.1:8000/slow?delay=3"
```

```bash
curl http://127.0.0.1:8000/stream
```

---

# Verify Client Keep-Alive

```bash
curl -v http://127.0.0.1:8000/ http://127.0.0.1:8000/
```

Expected output

```text
Re-using existing connection with host
```

---

# Load Testing

Example `tests/test.js`

```javascript
import http from "k6/http";
import { check } from "k6";

export const options = {
    gracefulStop: "0s",
    noConnectionReuse: false,
    noVUConnectionReuse: false,
};

export default function () {
    const res = http.get("http://127.0.0.1:8000/", {
        headers: {
            Connection: "keep-alive",
        },
    });

    check(res, {
        "status is 200": (r) => r.status === 200,
    });
}
```

Run benchmark

```bash
k6 run --vus 200 --duration 10s tests/test.js
```

---

# Benchmark Results

Environment

- MacBook Pro M1 Pro
- Python 3.14
- asyncio
- k6

Best stable configuration

- 4 upstream servers
- pool size = 50
- concurrency limit = 50
- max client connections = 200

| VUs | RPS | Avg | P95 | Errors |
|----:|----:|----:|----:|-------:|
| 25 | ~10.6k | ~2.3 ms | ~4.4 ms | 0% |
| 50 | ~11.6k | ~4.3 ms | ~8.1 ms | 0% |
| 100 | ~12.0k | ~8.3 ms | ~16.1 ms | 0% |
| **200** | **~12.3k** | **~16.2 ms** | **~31 ms** | **0%** |

Increasing the number of virtual users beyond **200** did not improve throughput and resulted in higher latency with occasional request failures.

---

# Implemented Optimizations

- HTTP Keep-Alive
- TCP connection pooling
- Connection reuse
- Round-Robin load balancing
- Per-upstream concurrency limits
- Timeout management
- Request/response streaming
- Backpressure handling
- YAML configuration

---

# Current Limitations

The following features are intentionally left for future iterations.

- Transfer-Encoding: chunked
- HTTP/2
- HTTPS
- Health checks
- Retry policy
- Circuit breaker
- Rate limiting
- Metrics endpoint
- Dynamic upstream discovery
- Configuration hot reload (SIGHUP)

---

# Learning Goals Covered

- asyncio event loop
- TCP networking
- HTTP protocol
- Coroutines
- Tasks
- Streaming
- Backpressure
- Connection pooling
- Keep-Alive
- Load balancing
- Timeout handling
- Benchmarking with k6

---

# Additional Experiments

## uvloop

The proxy was benchmarked using both the default asyncio event loop and **uvloop**.

No measurable throughput improvement was observed on the test environment.

| VUs | asyncio | uvloop |
|----:|---------:|--------:|
| 25 | ~10.6k RPS | ~10.6k RPS |
| 50 | ~11.6k RPS | ~11.6k RPS |
| 100 | ~12.0k RPS | ~12.0k RPS |

The final implementation keeps the default asyncio event loop.