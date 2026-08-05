from dataclasses import dataclass


@dataclass(frozen=True)
class UpstreamConfig:
    host: str
    port: int
    pool_size: int = 50

    @property
    def key(self) -> str:
        return f"{self.host}:{self.port}"


LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 8100

MAX_WORKERS = 200
SOCKET_TIMEOUT = 30.0
READ_SIZE = 16 * 1024

UPSTREAMS = [
    UpstreamConfig(host="127.0.0.1", port=9001),
    UpstreamConfig(host="127.0.0.1", port=9002),
    UpstreamConfig(host="127.0.0.1", port=9003),
    UpstreamConfig(host="127.0.0.1", port=9004),
]
