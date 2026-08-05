import asyncio
from asyncio import StreamReader, StreamWriter
from dataclasses import dataclass

from config import (
    CLIENT_READ_SIZE,
    MAX_CLIENT_CONNECTIONS_PER_PROCESS,
    READ_TIMEOUT,
    TOTAL_TIMEOUT,
    UPSTREAM_READ_SIZE,
    WRITE_TIMEOUT,
)
from upstream_connection_pool import (
    UpstreamConnection,
    UpstreamConnectionPool,
)


HEADER_SEPARATOR = b"\r\n\r\n"


@dataclass(frozen=True)
class HttpMessageHead:
    start_line: str
    headers: dict[str, str]
    raw: bytes

    @property
    def content_length(self) -> int:
        value = self.headers.get("content-length")

        if value is None:
            return 0

        return int(value)


async def read_http_head(
    reader: StreamReader,
) -> HttpMessageHead | None:
    try:
        raw = await asyncio.wait_for(
            reader.readuntil(HEADER_SEPARATOR),
            timeout=READ_TIMEOUT,
        )
    except asyncio.IncompleteReadError:
        return None

    lines = raw[:-4].split(b"\r\n")

    if not lines:
        raise ValueError("Empty HTTP message")

    start_line = lines[0].decode("iso-8859-1")
    headers: dict[str, str] = {}

    for raw_header in lines[1:]:
        header = raw_header.decode("iso-8859-1")

        if ":" not in header:
            raise ValueError(
                f"Invalid HTTP header: {header!r}"
            )

        name, value = header.split(":", 1)
        headers[name.strip().lower()] = value.strip()

    return HttpMessageHead(
        start_line=start_line,
        headers=headers,
        raw=raw,
    )


async def stream_content_length(
    reader: StreamReader,
    writer: StreamWriter,
    content_length: int,
    read_size: int,
) -> None:
    remaining = content_length

    while remaining > 0:
        chunk_size = min(remaining, read_size)

        chunk = await asyncio.wait_for(
            reader.readexactly(chunk_size),
            timeout=READ_TIMEOUT,
        )

        writer.write(chunk)

        await asyncio.wait_for(
            writer.drain(),
            timeout=WRITE_TIMEOUT,
        )

        remaining -= len(chunk)


def should_keep_alive(
    request: HttpMessageHead,
) -> bool:
    parts = request.start_line.split()

    if len(parts) != 3:
        raise ValueError(
            f"Invalid request line: {request.start_line!r}"
        )

    version = parts[2]
    connection = request.headers.get(
        "connection",
        "",
    ).lower()

    if version == "HTTP/1.0":
        return connection == "keep-alive"

    return connection != "close"


def response_allows_reuse(
    response: HttpMessageHead,
) -> bool:
    connection = response.headers.get(
        "connection",
        "",
    ).lower()

    return connection != "close"


async def process_one_request(
    client_reader: StreamReader,
    client_writer: StreamWriter,
    upstream_pool: UpstreamConnectionPool,
) -> bool:
    request = await read_http_head(client_reader)

    if request is None:
        return False

    client_keep_alive = should_keep_alive(request)

    upstream_connection: UpstreamConnection | None = None
    upstream_reusable = False

    try:
        upstream_connection = await upstream_pool.acquire()

        upstream_connection.writer.write(request.raw)

        await asyncio.wait_for(
            upstream_connection.writer.drain(),
            timeout=WRITE_TIMEOUT,
        )

        await stream_content_length(
            reader=client_reader,
            writer=upstream_connection.writer,
            content_length=request.content_length,
            read_size=CLIENT_READ_SIZE,
        )

        response = await read_http_head(
            upstream_connection.reader
        )

        if response is None:
            raise ConnectionError(
                "Upstream closed connection without response"
            )

        client_writer.write(response.raw)

        await asyncio.wait_for(
            client_writer.drain(),
            timeout=WRITE_TIMEOUT,
        )

        await stream_content_length(
            reader=upstream_connection.reader,
            writer=client_writer,
            content_length=response.content_length,
            read_size=UPSTREAM_READ_SIZE,
        )

        upstream_reusable = response_allows_reuse(
            response
        )

        return client_keep_alive

    finally:
        if upstream_connection is not None:
            await upstream_pool.release(
                upstream_connection,
                reusable=upstream_reusable,
            )


async def handle_client(
    client_reader: StreamReader,
    client_writer: StreamWriter,
    upstream_pool: UpstreamConnectionPool,
    client_limit: asyncio.Semaphore,
) -> None:
    client_address = client_writer.get_extra_info(
        "peername"
    )

    async with client_limit:
        try:
            while True:
                keep_alive = await asyncio.wait_for(
                    process_one_request(
                        client_reader=client_reader,
                        client_writer=client_writer,
                        upstream_pool=upstream_pool,
                    ),
                    timeout=TOTAL_TIMEOUT,
                )

                if not keep_alive:
                    break

        except (
            asyncio.IncompleteReadError,
            asyncio.TimeoutError,
            ConnectionError,
            OSError,
            ValueError,
        ) as exc:
            print(
                f"Client {client_address} error: {exc}"
            )

        finally:
            try:
                client_writer.close()
                await client_writer.wait_closed()
            except Exception:
                pass


def create_client_handler(
    upstream_pool: UpstreamConnectionPool,
):
    client_limit = asyncio.Semaphore(
        MAX_CLIENT_CONNECTIONS_PER_PROCESS
    )

    async def client_connected(
        reader: StreamReader,
        writer: StreamWriter,
    ) -> None:
        await handle_client(
            client_reader=reader,
            client_writer=writer,
            upstream_pool=upstream_pool,
            client_limit=client_limit,
        )

    return client_connected
