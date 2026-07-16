import asyncio

from client_handler import proxy_client
from config import APP_CONFIG
from upstream_connection_pool import upstream_connection_pool


async def main() -> None:
    await upstream_connection_pool.start()

    srv = await asyncio.start_server(
        proxy_client,
        APP_CONFIG.listen.host,
        APP_CONFIG.listen.port,
    )

    try:
        async with srv:
            await srv.serve_forever()
    finally:
        await upstream_connection_pool.close()


if __name__ == "__main__":
    asyncio.run(main())
