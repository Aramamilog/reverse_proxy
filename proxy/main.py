import asyncio
# import uvloop


from client_handler_v2 import proxy_client
from upstream_connection_pool import upstream_connection_pool


async def main(host: str, port: int):
    await upstream_connection_pool.start()

    srv = await asyncio.start_server(
        proxy_client,
        host,
        port,
    )

    try:
        async with srv:
            await srv.serve_forever()
    finally:
        await upstream_connection_pool.close()


if __name__ == '__main__':
    asyncio.run(main('127.0.0.1', 8000))
    # uvloop.run(main('127.0.0.1', 8000))
