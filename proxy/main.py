import asyncio

from client_handler import proxy_client


async def main(host: str, port: int):
    srv = await asyncio.start_server(
        proxy_client, host, port
    )

    async with srv:
        await srv.serve_forever()


if __name__ == '__main__':
    asyncio.run(main('127.0.0.1', 8000))
