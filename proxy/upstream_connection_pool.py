import asyncio
from dataclasses import dataclass
from asyncio.streams import StreamReader, StreamWriter

from config import UPSTREAMS, TIMEOUTS


@dataclass(frozen=True)
class Upstream:
    host: str
    port: int

    @property
    def key(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass
class UpstreamConnection:
    upstream: Upstream
    reader: StreamReader
    writer: StreamWriter


class UpstreamConnectionPool:
    def __init__(self, connections_per_upstream: int):
        self._connections_per_upstream = connections_per_upstream
        self._queues: dict[str, asyncio.Queue[UpstreamConnection]] = {}
        self._round_robin = self._round_robin_generator()
        self._upstreams = [
            Upstream(host=item.host, port=item.port)
            for item in UPSTREAMS
        ]

        if not self._upstreams:
            raise ValueError("Upstreams cannot be empty")

    async def start(self) -> None:
        for upstream in self._upstreams:
            queue = asyncio.Queue()
            self._queues[upstream.key] = queue

            for _ in range(self._connections_per_upstream):
                connection = await self._create_connection(upstream)
                await queue.put(connection)

    async def close(self) -> None:
        for queue in self._queues.values():
            while not queue.empty():
                connection = await queue.get()
                connection.writer.close()
                await connection.writer.wait_closed()

    async def acquire(self) -> UpstreamConnection:
        upstream = next(self._round_robin)
        queue = self._queues[upstream.key]
        return await queue.get()

    async def release(
        self,
        connection: UpstreamConnection,
        reusable: bool = True,
    ) -> None:
        queue = self._queues[connection.upstream.key]

        if reusable and not connection.writer.is_closing():
            await queue.put(connection)
            return

        try:
            connection.writer.close()
            await connection.writer.wait_closed()
        except Exception:
            pass

        new_connection = await self._create_connection(connection.upstream)
        await queue.put(new_connection)

    async def _create_connection(self, upstream: Upstream) -> UpstreamConnection:
        reader, writer = await TIMEOUTS.connect_timeout(
            asyncio.open_connection(upstream.host, upstream.port)
        )

        return UpstreamConnection(
            upstream=upstream,
            reader=reader,
            writer=writer,
        )

    def _round_robin_generator(self):
        index = 0

        while True:
            yield self._upstreams[index]

            index += 1

            if index >= len(self._upstreams):
                index = 0


upstream_connection_pool = UpstreamConnectionPool(
    connections_per_upstream=100,
)