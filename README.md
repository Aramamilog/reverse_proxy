# Async Reverse Proxy (MVP)

Educational reverse proxy server implemented with `asyncio`.

The goal of the project is educational: to learn asyncio, TCP networking, streaming, connection pooling, load balancing, and reverse proxy architecture.

## Features

* TCP server based on `asyncio.start_server`
* HTTP request parsing
* HTTP response parsing
* Request body streaming
* Response body streaming
* Backpressure support via `await writer.drain()`
* Multiple upstream servers
* Round-Robin load balancing
* Client HTTP keep-alive support
* Upstream TCP connection pool
* Configurable timeouts:

  * connect timeout
  * read timeout
  * write timeout
  * total request timeout
* Connection limits via `asyncio.Semaphore`
* Load testing with k6

---

## Architecture

```text
Client
   │
   ▼
Reverse Proxy (:8000)
   │
   ├── Upstream Pool (:9001)
   └── Upstream Pool (:9002)
```

---

## Run Upstreams

Start two upstream instances:

```bash
PORT=9001 python tests/echo_app.py
```

```bash
PORT=9002 python tests/echo_app.py
```

---

## Run Reverse Proxy

From the project root:

```bash
python proxy/main.py
```

Proxy listens on:

```text
127.0.0.1:8000
```

---

## Test Upstreams Directly

### Basic Endpoint

```bash
curl http://127.0.0.1:9001/
curl http://127.0.0.1:9002/
```

### Echo Endpoint

```bash
curl -X POST http://127.0.0.1:9001/echo -d "hello world"
curl -X POST http://127.0.0.1:9002/echo -d "hello world"
```

### Slow Endpoint

```bash
time curl "http://127.0.0.1:9001/slow?delay=3"
time curl "http://127.0.0.1:9002/slow?delay=3"
```

### Streaming Endpoint

```bash
curl http://127.0.0.1:9001/stream
curl http://127.0.0.1:9002/stream
```

### Large Response Endpoint

```bash
curl "http://127.0.0.1:9001/big?size_mb=50" -o /dev/null
curl "http://127.0.0.1:9002/big?size_mb=50" -o /dev/null
```

---

## Test Through Reverse Proxy

Replace upstream ports (`9001`, `9002`) with proxy port (`8000`).

Examples:

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

## Verify Keep-Alive

```bash
curl -v http://127.0.0.1:8000/ http://127.0.0.1:8000/
```

Expected output:

```text
Re-using existing connection with host 127.0.0.1
```

---

## Load Testing

Example k6 scenario:

```javascript
import http from "k6/http";
import { check } from "k6";

export const options = {
  vus: 25,
  duration: "10s",
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

Run:

```bash
k6 run tests/test.js
```

---

## Load Test Results

Environment: local machine (MacBook M1 Pro)

The best observed configuration for this local benchmark was `CONNECTION_LIMIT = 100`.
Higher values such as `1000` did not improve RPS and increased p95 latency.

| VUs |     RPS | Avg latency |     P95 | Errors |
| --: | ------: | ----------: | ------: | -----: |
|  25 | ~11 648 |      ~2.1ms |  ~2.9ms |     0% |
|  50 | ~12 387 |      ~4.0ms |  ~5.3ms |     0% |
| 100 | ~12 346 |      ~8.0ms | ~10.7ms |     0% |


---

## Implemented Optimizations

* Client HTTP keep-alive
* Upstream TCP connection pool
* Connection reuse
* Round-robin load balancing
* Timeout management
* Backpressure handling
* Request/response streaming

---

## Current Limitations

The following features are intentionally not implemented in the MVP:

* HTTP chunked transfer encoding
* Health checks
* Retry policy
* Circuit breaker
* Rate limiting
* HTTPS support
* Metrics endpoint
* Dynamic upstream discovery
* HTTP/2 support

---

## Learning Goals Covered

* asyncio event loop
* Coroutines and tasks
* TCP servers and clients
* Backpressure
* Streaming request/response bodies
* Timeouts
* Connection pooling
* Load balancing
* Keep-alive
* Load testing with k6

---

## Additional Experiments

### uvloop

The proxy was benchmarked using both:

* standard asyncio event loop
* uvloop

Results on the test environment (MacBook M1 Pro) showed no performance improvement from uvloop.

| VUs | asyncio RPS | uvloop RPS |
|------|------------|------------|
| 25 | ~11.6k | ~10.6k |
| 50 | ~12.4k | ~11.6k |
| 100 | ~12.3k | ~12.0k |

Based on these measurements, the final implementation keeps the default asyncio event loop.