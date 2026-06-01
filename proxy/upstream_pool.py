from dataclasses import dataclass
from config import UPSTREAMS


@dataclass(frozen=True)
class Upstream:
    host: str
    port: int


class UpstreamPool:
    def __init__(
        self,
        upstreams: list[Upstream],
    ):
        if not upstreams:
            raise ValueError(
                "Upstream pool cannot be empty"
            )

        self._upstreams = upstreams
        self._round_robin = self._round_robin_generator()

    def _round_robin_generator(self):
        index = 0

        while True:
            yield self._upstreams[index]

            index += 1

            if index >= len(self._upstreams):
                index = 0

    def get_next_upstream(self) -> Upstream:
        return next(self._round_robin)


upstream_pool = UpstreamPool(
    upstreams=[
        Upstream(
            host=item.host,
            port=item.port,
        )
        for item in UPSTREAMS
    ]
)
