# Async Reverse Proxy (MVP)

Educational reverse proxy server implemented with `asyncio`.

## Features

* TCP server based on `asyncio.start_server`
* HTTP request parsing
* HTTP response parsing
* Request body streaming
* Response body streaming
* Backpressure support via `await writer.drain()`
* Multiple upstream servers
* Round-Robin load balancing
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
   ├── Upstream 1 (:9001)
   └── Upstream 2 (:9002)
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

---

### Echo Endpoint

```bash
curl -X POST http://127.0.0.1:9001/echo -d "hello world"
curl -X POST http://127.0.0.1:9002/echo -d "hello world"
```

---

### Slow Endpoint

```bash
time curl "http://127.0.0.1:9001/slow?delay=3"
time curl "http://127.0.0.1:9002/slow?delay=3"
```

---

### Streaming Endpoint

```bash
curl http://127.0.0.1:9001/stream
curl http://127.0.0.1:9002/stream
```

---

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

## Load Testing

Example k6 scenario:

```javascript
import http from "k6/http";

export default function () {
    http.get("http://127.0.0.1:8000/");
}
```

Run:

```bash
k6 run --vus 10 --duration 10s test.js
```

---

## Load Test Results

Environment: local machine

### 10 Virtual Users

* RPS ≈ 1069 req/s
* Average latency ≈ 9 ms
* P95 ≈ 10 ms
* Errors = 0%

### 100 Virtual Users

* RPS ≈ 1061 req/s
* Average latency ≈ 94 ms
* P95 ≈ 105 ms
* Errors = 0%

### 200 Virtual Users

* RPS ≈ 1064 req/s
* Average latency ≈ 186 ms
* P95 ≈ 201 ms
* Errors = 0%

---

## Current Limitations

The following features are intentionally not implemented in the MVP:

* HTTP chunked transfer encoding
* HTTP keep-alive connection reuse
* Upstream connection pooling
* Health checks
* Retry policy
* Circuit breaker
* Rate limiting
* HTTPS support
* Metrics endpoint

These features are planned as future improvements.
