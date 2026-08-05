import asyncio
from dataclasses import dataclass
from asyncio import StreamReader, StreamWriter

from config import CONNECT_TIMEOUT, UPSTREAMS, UpstreamConfig


@dataclass
class UpstreamConnection:
    upstream: UpstreamConfig
    reader: StreamReader
    writer: StreamWriter


class UpstreamConnectionPool:
    def __init__(
        self,
        upstreams: list[UpstreamConfig],
    ) -> None:
        if not upstreams:
            raise ValueError("Upstream list cannot be empty")

        self._upstreams = upstreams

        self._queues: dict[
            str,
            asyncio.Queue[UpstreamConnection],
        ] = {}

        self._semaphores: dict[
            str,
            asyncio.Semaphore,
        ] = {}

        self._round_robin_index = 0
        self._round_robin_lock = asyncio.Lock()

    async def start(self) -> None:
        for upstream in self._upstreams:
            queue: asyncio.Queue[UpstreamConnection] = (
                asyncio.Queue(maxsize=upstream.pool_size)
            )

            self._queues[upstream.key] = queue
            self._semaphores[upstream.key] = asyncio.Semaphore(
                upstream.concurrency_limit
            )

            for _ in range(upstream.pool_size):
                connection = await self._create_connection(
                    upstream
                )
                await queue.put(connection)

    async def acquire(self) -> UpstreamConnection:
        upstream = await self._get_next_upstream()
        semaphore = self._semaphores[upstream.key]

        await semaphore.acquire()

        try:
            queue = self._queues[upstream.key]
            return await queue.get()

        except BaseException:
            semaphore.release()
            raise

    async def release(
        self,
        connection: UpstreamConnection,
        *,
        reusable: bool,
    ) -> None:
        upstream = connection.upstream
        queue = self._queues[upstream.key]
        semaphore = self._semaphores[upstream.key]

        try:
            if reusable and not connection.writer.is_closing():
                await queue.put(connection)
                return

            await self._close_connection(connection)

            replacement = await self._create_connection(
                upstream
            )
            await queue.put(replacement)

        finally:
            semaphore.release()

    async def close(self) -> None:
        for queue in self._queues.values():
            while not queue.empty():
                connection = queue.get_nowait()
                await self._close_connection(connection)

    async def _get_next_upstream(
        self,
    ) -> UpstreamConfig:
        async with self._round_robin_lock:
            upstream = self._upstreams[
                self._round_robin_index
            ]

            self._round_robin_index += 1

            if self._round_robin_index >= len(
                self._upstreams
            ):
                self._round_robin_index = 0

            return upstream

    @staticmethod
    async def _create_connection(
        upstream: UpstreamConfig,
    ) -> UpstreamConnection:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                upstream.host,
                upstream.port,
            ),
            timeout=CONNECT_TIMEOUT,
        )

        return UpstreamConnection(
            upstream=upstream,
            reader=reader,
            writer=writer,
        )

    @staticmethod
    async def _close_connection(
        connection: UpstreamConnection,
    ) -> None:
        try:
            connection.writer.close()
            await connection.writer.wait_closed()
        except Exception:
            pass


def create_upstream_connection_pool(
) -> UpstreamConnectionPool:
    return UpstreamConnectionPool(
        upstreams=UPSTREAMS,
    )
