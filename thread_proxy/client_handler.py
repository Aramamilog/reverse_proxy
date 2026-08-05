import socket
from dataclasses import dataclass
from typing import BinaryIO

from config import READ_SIZE, SOCKET_TIMEOUT
from upstream_connection_pool import (
    UpstreamConnection,
    upstream_connection_pool,
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


def read_http_head(reader: BinaryIO) -> HttpMessageHead | None:
    raw_lines: list[bytes] = []

    start_line_raw = reader.readline()

    if start_line_raw == b"":
        return None

    if not start_line_raw.endswith(b"\r\n"):
        raise ValueError("Invalid HTTP start line")

    raw_lines.append(start_line_raw)

    while True:
        line = reader.readline()

        if line == b"":
            raise ConnectionError(
                "Connection closed while reading HTTP headers"
            )

        raw_lines.append(line)

        if line == b"\r\n":
            break

    start_line = start_line_raw.decode("iso-8859-1").rstrip("\r\n")
    headers: dict[str, str] = {}

    for raw_header in raw_lines[1:-1]:
        header = raw_header.decode("iso-8859-1").rstrip("\r\n")

        if ":" not in header:
            raise ValueError(f"Invalid HTTP header: {header!r}")

        name, value = header.split(":", 1)
        headers[name.strip().lower()] = value.strip()

    return HttpMessageHead(
        start_line=start_line,
        headers=headers,
        raw=b"".join(raw_lines),
    )


def stream_content_length(
    reader: BinaryIO,
    destination: socket.socket,
    content_length: int,
) -> None:
    remaining = content_length

    while remaining > 0:
        chunk = reader.read(min(remaining, READ_SIZE))

        if not chunk:
            raise ConnectionError(
                "Connection closed before body was fully read"
            )

        destination.sendall(chunk)
        remaining -= len(chunk)


def should_keep_alive(message: HttpMessageHead) -> bool:
    try:
        version = message.start_line.split()[2]
    except IndexError as exc:
        raise ValueError(
            f"Invalid HTTP request line: {message.start_line!r}"
        ) from exc

    connection = message.headers.get("connection", "").lower()

    if version == "HTTP/1.0":
        return connection == "keep-alive"

    return connection != "close"


def response_allows_reuse(response: HttpMessageHead) -> bool:
    connection = response.headers.get("connection", "").lower()
    return connection != "close"


def process_one_request(
    client_reader: BinaryIO,
    client_socket: socket.socket,
) -> bool:
    request = read_http_head(client_reader)

    if request is None:
        return False

    client_keep_alive = should_keep_alive(request)

    upstream_connection: UpstreamConnection | None = None
    upstream_reusable = False

    try:
        upstream_connection = upstream_connection_pool.acquire()

        upstream_connection.socket.sendall(request.raw)

        stream_content_length(
            reader=client_reader,
            destination=upstream_connection.socket,
            content_length=request.content_length,
        )

        response = read_http_head(upstream_connection.reader)

        if response is None:
            raise ConnectionError(
                "Upstream closed connection without response"
            )

        client_socket.sendall(response.raw)

        stream_content_length(
            reader=upstream_connection.reader,
            destination=client_socket,
            content_length=response.content_length,
        )

        upstream_reusable = response_allows_reuse(response)

        return client_keep_alive

    finally:
        if upstream_connection is not None:
            upstream_connection_pool.release(
                upstream_connection,
                reusable=upstream_reusable,
            )


def handle_client(
    client_socket: socket.socket,
    client_address: tuple[str, int],
) -> None:
    client_socket.settimeout(SOCKET_TIMEOUT)
    client_reader = client_socket.makefile("rb")

    try:
        while True:
            keep_alive = process_one_request(
                client_reader=client_reader,
                client_socket=client_socket,
            )

            if not keep_alive:
                break

    except (
        ConnectionError,
        TimeoutError,
        socket.timeout,
        ValueError,
        OSError,
    ) as exc:
        print(f"Client {client_address} error: {exc}")

    finally:
        try:
            client_reader.close()
        except Exception:
            pass

        try:
            client_socket.close()
        except Exception:
            pass
