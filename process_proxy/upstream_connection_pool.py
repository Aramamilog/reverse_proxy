import socket
import threading
from dataclasses import dataclass
from queue import Queue
from typing import BinaryIO

from config import SOCKET_TIMEOUT, UPSTREAMS, UpstreamConfig


@dataclass
class UpstreamConnection:
    upstream: UpstreamConfig
    socket: socket.socket
    reader: BinaryIO


class UpstreamConnectionPool:
    def __init__(self, upstreams: list[UpstreamConfig]) -> None:
        if not upstreams:
            raise ValueError("Upstream list cannot be empty")

        self._upstreams = upstreams

        self._queues: dict[str, Queue[UpstreamConnection]] = {
            upstream.key: Queue(maxsize=upstream.pool_size)
            for upstream in upstreams
        }

        self._round_robin_index = 0
        self._round_robin_lock = threading.Lock()

    def start(self) -> None:
        for upstream in self._upstreams:
            queue = self._queues[upstream.key]

            for _ in range(upstream.pool_size):
                queue.put(self._create_connection(upstream))

    def acquire(self) -> UpstreamConnection:
        upstream = self._get_next_upstream()
        return self._queues[upstream.key].get()

    def release(
        self,
        connection: UpstreamConnection,
        *,
        reusable: bool,
    ) -> None:
        queue = self._queues[connection.upstream.key]

        if reusable and self._is_connection_alive(connection):
            queue.put(connection)
            return

        self._close_connection(connection)

        replacement = self._create_connection(connection.upstream)
        queue.put(replacement)

    def close(self) -> None:
        for queue in self._queues.values():
            while not queue.empty():
                connection = queue.get_nowait()
                self._close_connection(connection)

    def _get_next_upstream(self) -> UpstreamConfig:
        with self._round_robin_lock:
            upstream = self._upstreams[self._round_robin_index]

            self._round_robin_index += 1

            if self._round_robin_index >= len(self._upstreams):
                self._round_robin_index = 0

            return upstream

    @staticmethod
    def _create_connection(
        upstream: UpstreamConfig,
    ) -> UpstreamConnection:
        upstream_socket = socket.create_connection(
            (upstream.host, upstream.port),
            timeout=SOCKET_TIMEOUT,
        )
        upstream_socket.settimeout(SOCKET_TIMEOUT)

        return UpstreamConnection(
            upstream=upstream,
            socket=upstream_socket,
            reader=upstream_socket.makefile("rb"),
        )

    @staticmethod
    def _is_connection_alive(
        connection: UpstreamConnection,
    ) -> bool:
        return (
            connection.socket.fileno() != -1
            and not connection.socket._closed
        )

    @staticmethod
    def _close_connection(
        connection: UpstreamConnection,
    ) -> None:
        try:
            connection.reader.close()
        except Exception:
            pass

        try:
            connection.socket.close()
        except Exception:
            pass
