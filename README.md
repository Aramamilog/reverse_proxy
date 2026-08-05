# Async Reverse Proxy (MVP)

Educational reverse proxy server implemented with Python `asyncio`.

The purpose of this project is to study low-level networking, asynchronous programming and reverse proxy architecture by implementing everything manually instead of relying on existing web frameworks.

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
  max_conns_per_upstream: 100

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
- Apple M1 Pro
- Python 3.14
- k6
- 10-second benchmark
- HTTP Keep-Alive enabled

---

## Benchmark Summary

| Implementation | Best Configuration                                                                      | Best Test | RPS | Avg | P95 | Errors |
|---------------|-----------------------------------------------------------------------------------------|-----------|----:|----:|----:|-------:|
| Async | 4 upstreams, pool=50, concurrency=50, max_client_conns=200                              | 200 VUs | **~12.3k** | ~16.2 ms | ~31 ms | 0% |
| Threads | 250 worker threads                                                                      | 50 VUs | **~7.9k** | ~6.3 ms | ~10.7 ms | 0% |
| Processes + Threads | 4 processes × 250 threads                                                               | 200 VUs | **~7.2k** | ~13.9 ms | ~28.4 ms | 0% |
| **Processes + Async** | **4 processes, 4 upstreams, pool=12, concurrency=12, max_client_conns_per_process=200** | **200 VUs** | **~14.2k** | **~14.0 ms** | **~35 ms** | **0%** |

This experimental implementation achieved the highest throughput during local benchmarks.

It combines the scalability of asyncio with better CPU utilization through multiple worker processes.

The current Async implementation can be evolved into this architecture in future iterations.

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

---

## Alternative Implementations

To better understand Python concurrency models, several reverse proxy implementations were developed and benchmarked.

### Async

- asyncio
- Single event loop
- Non-blocking sockets

Reference implementation used throughout the project.

---

### Threads

- socket
- ThreadPoolExecutor
- queue.Queue

Implemented to compare classic thread-based concurrency with asynchronous I/O.

---

### Processes + Threads

- multiprocessing
- ThreadPoolExecutor
- SO_REUSEPORT

Implemented to evaluate the impact of combining processes with blocking thread pools.

---

### Processes + Async

- multiprocessing
- asyncio
- SO_REUSEPORT

Experimental implementation combining multiple worker processes with asynchronous event loops.

This version achieved the highest throughput during local benchmarks (~14k requests/sec), demonstrating that multi-process asyncio architecture scales better for I/O-bound workloads.

---

## Documentation

Additional project documentation:

- [ROADMAP.md](ROADMAP.md)
