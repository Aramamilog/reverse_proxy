from logger import logger

import asyncio
from asyncio.streams import StreamReader, StreamWriter

from config import CONNECTION_LIMIT, TIMEOUTS
from upstream_connection_pool import upstream_connection_pool
from utils.http import http_response_parser, http_request_parser


CLIENT_READ_SIZE = 1024
UPSTREAM_READ_SIZE = 1024

CLIENT_CONNECTIONS = 0
TOTAL_REQUESTS = 0


def _should_keep_client_connection_alive(request_model) -> bool:
    connection = request_model.headers.get("connection", "").lower()

    if request_model.version == "HTTP/1.0":
        return connection == "keep-alive"

    return connection != "close"


def _rewrite_response_connection_header(raw_response: bytes, keep_alive: bool) -> bytes:
    headers_part, separator, body_part = raw_response.partition(
        http_response_parser.SEPARATOR
    )

    lines = headers_part.split(b"\r\n")

    filtered_lines = [
        line
        for line in lines
        if not line.lower().startswith(b"connection:")
    ]

    if keep_alive:
        filtered_lines.append(b"Connection: keep-alive")
    else:
        filtered_lines.append(b"Connection: close")

    return b"\r\n".join(filtered_lines) + separator + body_part


async def stream_bytes(
        reader: StreamReader,
        writer: StreamWriter,
        content_length: int,
        read_size: int,
) -> None:
    # TODO: will be better -> while true: remaining_size -> chunk
    if content_length:
        if content_length <= read_size:
            body = await TIMEOUTS.read_timeout(reader.readexactly(content_length))

            writer.write(body)
            await TIMEOUTS.write_timeout(writer.drain())
        else:
            read_iteration = content_length // read_size
            read_tail = content_length - read_size * read_iteration

            for _ in range(read_iteration):
                body = await TIMEOUTS.read_timeout(reader.readexactly(read_size))

                writer.write(body)
                await TIMEOUTS.write_timeout(writer.drain())

            if read_tail:
                body = await TIMEOUTS.read_timeout(reader.readexactly(read_tail))

                writer.write(body)
                await TIMEOUTS.write_timeout(writer.drain())


async def _process_one_request(
    client_reader: StreamReader,
    client_writer: StreamWriter,
) -> bool:
    upstream_connection = None
    upstream_writer: StreamWriter | None = None
    upstream_address = None
    upstream_reusable = False

    try:
        client_raw_request = await TIMEOUTS.read_timeout(
            client_reader.readuntil(separator=http_request_parser.SEPARATOR)
        )
        request_model = await http_request_parser.parse_http_request(client_raw_request)
        global TOTAL_REQUESTS
        TOTAL_REQUESTS += 1

        if TOTAL_REQUESTS % 1000 == 0:
            print(f"TOTAL_REQUESTS={TOTAL_REQUESTS}")
        keep_alive = _should_keep_client_connection_alive(request_model)

        upstream_connection = await upstream_connection_pool.acquire()
        upstream_reader = upstream_connection.reader
        upstream_writer = upstream_connection.writer
        upstream_address = upstream_writer.get_extra_info("peername")

        upstream_writer.write(client_raw_request)
        await TIMEOUTS.write_timeout(upstream_writer.drain())

        request_body_task = asyncio.create_task(
            stream_bytes(
                reader=client_reader,
                writer=upstream_writer,
                content_length=http_request_parser.get_content_length(request_model.headers),
                read_size=CLIENT_READ_SIZE,
            )
        )

        upstream_raw_response = await TIMEOUTS.read_timeout(
            upstream_reader.readuntil(separator=http_response_parser.SEPARATOR)
        )
        response_model = await http_response_parser.parse_http_response(upstream_raw_response)

        upstream_raw_response = _rewrite_response_connection_header(
            raw_response=upstream_raw_response,
            keep_alive=keep_alive,
        )
        client_writer.write(upstream_raw_response)
        await TIMEOUTS.write_timeout(client_writer.drain())

        response_body_task = asyncio.create_task(
            stream_bytes(
                reader=upstream_reader,
                writer=client_writer,
                content_length=http_response_parser.get_content_length(response_model.headers),
                read_size=UPSTREAM_READ_SIZE,
            )
        )

        await asyncio.gather(request_body_task, response_body_task)
        upstream_reusable = True
        return keep_alive

    finally:
        if upstream_connection:
            await upstream_connection_pool.release(
                upstream_connection,
                reusable=upstream_reusable,
            )


async def proxy_client(
    client_reader: StreamReader,
    client_writer: StreamWriter,
) -> None:
    client_address = client_writer.get_extra_info("peername")
    global CLIENT_CONNECTIONS
    CLIENT_CONNECTIONS += 1

    print(f"CLIENT_CONNECTIONS={CLIENT_CONNECTIONS}")

    async with CONNECTION_LIMIT:
        try:
            while True:
                try:
                    keep_alive = await TIMEOUTS.total_timeout(
                        _process_one_request(
                            client_reader=client_reader,
                            client_writer=client_writer,
                        )
                    )

                    if not keep_alive:
                        break

                except asyncio.IncompleteReadError:
                    break

                except asyncio.TimeoutError:
                    logger.error(f">> Proxy timeout: {client_address}")
                    break

                except Exception as e:
                    logger.error(f">> Proxy error: {client_address}: {e}")
                    break

        finally:
            try:
                client_writer.close()
                await client_writer.wait_closed()
            except Exception as e:
                logger.error(f">> Client closing error {client_address}: {e}")
