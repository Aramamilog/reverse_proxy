from dataclasses import dataclass


@dataclass(frozen=True)
class UpstreamConfig:
    host: str
    port: int
    pool_size: int
    concurrency_limit: int

    @property
    def key(self) -> str:
        return f"{self.host}:{self.port}"


LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 8300

PROCESS_COUNT = 4

# Это лимит внутри одного process, а не глобальный лимит.
MAX_CLIENT_CONNECTIONS_PER_PROCESS = 200

CONNECT_TIMEOUT = 1.0
READ_TIMEOUT = 15.0
WRITE_TIMEOUT = 15.0
TOTAL_TIMEOUT = 30.0

CLIENT_READ_SIZE = 16 * 1024
UPSTREAM_READ_SIZE = 16 * 1024
LISTEN_BACKLOG = 2048

# Четыре процесса × 12 соединений ≈ 48 соединений
# на каждый upstream в сумме.
UPSTREAMS = [
    UpstreamConfig(
        host="127.0.0.1",
        port=9001,
        pool_size=12,
        concurrency_limit=12,
    ),
    UpstreamConfig(
        host="127.0.0.1",
        port=9002,
        pool_size=12,
        concurrency_limit=12,
    ),
    UpstreamConfig(
        host="127.0.0.1",
        port=9003,
        pool_size=12,
        concurrency_limit=12,
    ),
    UpstreamConfig(
        host="127.0.0.1",
        port=9004,
        pool_size=12,
        concurrency_limit=12,
    ),
]
