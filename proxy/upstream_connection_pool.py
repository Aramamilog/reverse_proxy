import asyncio
from dataclasses import dataclass
from asyncio.streams import StreamReader, StreamWriter

from config import TIMEOUTS, UPSTREAMS, UpstreamConfig


@dataclass
class UpstreamConnection:
    upstream: UpstreamConfig
    reader: StreamReader
    writer: StreamWriter


class UpstreamConnectionPool:
    def __init__(self, upstreams: list[UpstreamConfig]):
        if not upstreams:
            raise ValueError("Upstreams cannot be empty")

        self._upstreams = upstreams
        self._queues: dict[str, asyncio.Queue[UpstreamConnection]] = {}
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._round_robin = self._round_robin_generator()

    async def start(self) -> None:
        for upstream in self._upstreams:
            queue = asyncio.Queue(maxsize=upstream.pool_size)
            self._queues[upstream.key] = queue
            self._semaphores[upstream.key] = asyncio.Semaphore(
                upstream.concurrency_limit
            )

            for _ in range(upstream.pool_size):
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

        semaphore = self._semaphores[upstream.key]
        await semaphore.acquire()

        try:
            queue = self._queues[upstream.key]
            return await queue.get()
        except Exception:
            semaphore.release()
            raise

    async def release(
        self,
        connection: UpstreamConnection,
        reusable: bool = True,
    ) -> None:
        upstream = connection.upstream
        queue = self._queues[upstream.key]
        semaphore = self._semaphores[upstream.key]

        try:
            if reusable and not connection.writer.is_closing():
                await queue.put(connection)
                return

            try:
                connection.writer.close()
                await connection.writer.wait_closed()
            except Exception:
                pass

            new_connection = await self._create_connection(upstream)
            await queue.put(new_connection)

        finally:
            semaphore.release()

    async def _create_connection(
        self,
        upstream: UpstreamConfig,
    ) -> UpstreamConnection:
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
    upstreams=UPSTREAMS,
)
