from dataclasses import dataclass
from timeouts import Timeouts

from asyncio import Semaphore


@dataclass(frozen=True)
class UpstreamConfig:
    host: str
    port: int


UPSTREAMS = [
    UpstreamConfig(
        host="127.0.0.1",
        port=9001,
    ),
    UpstreamConfig(
        host="127.0.0.1",
        port=9002,
    ),
]


TIMEOUTS = Timeouts(
    connect=1,
    read=15,
    write=15,
    total=30,
)


CONNECTION_LIMIT = Semaphore(1)
