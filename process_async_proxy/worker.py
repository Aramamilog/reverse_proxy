import asyncio
import os

from client_handler import create_client_handler
from config import (
    LISTEN_BACKLOG,
    LISTEN_HOST,
    LISTEN_PORT,
)
from upstream_connection_pool import (
    create_upstream_connection_pool,
)


async def worker_main(
    worker_number: int,
) -> None:
    process_id = os.getpid()

    upstream_pool = create_upstream_connection_pool()
    await upstream_pool.start()

    client_handler = create_client_handler(
        upstream_pool
    )

    server = await asyncio.start_server(
        client_handler,
        host=LISTEN_HOST,
        port=LISTEN_PORT,
        backlog=LISTEN_BACKLOG,
        reuse_port=True,
    )

    print(
        f"Async worker {worker_number} started: "
        f"pid={process_id}, "
        f"listen={LISTEN_HOST}:{LISTEN_PORT}"
    )

    try:
        async with server:
            await server.serve_forever()

    finally:
        server.close()
        await server.wait_closed()
        await upstream_pool.close()

        print(
            f"Async worker {worker_number} stopped: "
            f"pid={process_id}"
        )


def run_worker(
    worker_number: int,
) -> None:
    asyncio.run(
        worker_main(worker_number)
    )
