import os
import socket
from concurrent.futures import ThreadPoolExecutor

from client_handler import handle_client
from config import (
    LISTEN_BACKLOG,
    LISTEN_HOST,
    LISTEN_PORT,
    THREADS_PER_PROCESS,
    UPSTREAMS,
)
from upstream_connection_pool import UpstreamConnectionPool


def run_worker(worker_number: int) -> None:
    process_id = os.getpid()

    upstream_pool = UpstreamConnectionPool(UPSTREAMS)
    upstream_pool.start()

    server_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    )

    server_socket.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1,
    )

    if not hasattr(socket, "SO_REUSEPORT"):
        raise RuntimeError(
            "SO_REUSEPORT is not supported "
            "by this operating system"
        )

    server_socket.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEPORT,
        1,
    )

    server_socket.bind(
        (LISTEN_HOST, LISTEN_PORT)
    )
    server_socket.listen(LISTEN_BACKLOG)

    print(
        f"Worker {worker_number} started: "
        f"pid={process_id}, "
        f"threads={THREADS_PER_PROCESS}"
    )

    try:
        with ThreadPoolExecutor(
            max_workers=THREADS_PER_PROCESS,
            thread_name_prefix=(
                f"process-{process_id}-thread"
            ),
        ) as executor:
            while True:
                client_socket, client_address = (
                    server_socket.accept()
                )

                executor.submit(
                    handle_client,
                    client_socket,
                    client_address,
                    upstream_pool,
                )

    except KeyboardInterrupt:
        pass

    finally:
        server_socket.close()
        upstream_pool.close()

        print(
            f"Worker {worker_number} stopped: "
            f"pid={process_id}"
        )
