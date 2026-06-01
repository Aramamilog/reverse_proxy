from logger import logger

import asyncio
from asyncio.streams import StreamReader, StreamWriter

from config import CONNECTION_LIMIT, TIMEOUTS
from upstream_pool import upstream_pool
from utils.http import http_response_parser, http_request_parser


CLIENT_READ_SIZE = 1024
UPSTREAM_READ_SIZE = 1024

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


async def _process_request(
    client_reader: StreamReader,
    client_writer: StreamWriter,
) -> None:
    upstream_writer: StreamWriter | None = None
    upstream_address = None

    client_address = client_writer.get_extra_info('peername')
    logger.info(f'>> Start client serving: {client_address=}')

    try:
        #-#-# Proxy read from client and write to upstream #-#-#
        client_raw_request = await TIMEOUTS.read_timeout(client_reader.readuntil(separator=http_request_parser.SEPARATOR))
        request_model = await http_request_parser.parse_http_request(client_raw_request)
        client_raw_request_log = f'method={request_model.method} path={request_model.path}, version={request_model.version}, headers={request_model.headers}'
        logger.info(f'>> Proxy read client_raw_request: {client_raw_request_log}')

        upstream = upstream_pool.get_next_upstream()
        logger.info(f'>> Selected upstream: {upstream.host}:{upstream.port}')
        upstream_reader, upstream_writer = await TIMEOUTS.connect_timeout(asyncio.open_connection(upstream.host, upstream.port))
        upstream_address = upstream_writer.get_extra_info('peername')
        logger.info(f'>> Start upstream serving: {upstream_address=}')

        upstream_writer.write(client_raw_request)
        await TIMEOUTS.write_timeout(upstream_writer.drain())

        logger.info(f'>> Proxy sent to upstream: {client_raw_request=}')

        request_body_task = asyncio.create_task(
            stream_bytes(
                reader=client_reader,
                writer=upstream_writer,
                content_length=http_request_parser.get_content_length(request_model.headers),
                read_size=CLIENT_READ_SIZE,
            )
        )

        # -#-# Proxy read from upstream and write to client #-#-#
        upstream_raw_response = await TIMEOUTS.read_timeout(upstream_reader.readuntil(separator=http_response_parser.SEPARATOR))
        response_model = await http_response_parser.parse_http_response(upstream_raw_response)
        upstream_raw_response_log = f'status_code={response_model.status_code} reason_phrase={response_model.reason_phrase}, version={response_model.version}, headers={response_model.headers}'
        logger.info(f'>> Proxy read upstream_raw_response: {upstream_raw_response_log}')

        client_writer.write(upstream_raw_response)
        await TIMEOUTS.write_timeout(client_writer.drain())

        logger.info(f'>> Proxy sent to client: {upstream_raw_response=}')

        response_body_task = asyncio.create_task(
            stream_bytes(
                reader=upstream_reader,
                writer=client_writer,
                content_length=http_response_parser.get_content_length(response_model.headers),
                read_size=UPSTREAM_READ_SIZE,
            )
        )

        await asyncio.gather(
            request_body_task,
            response_body_task,
        )

    except asyncio.TimeoutError:
        logger.error(f'>> Proxy timeout')

    except Exception as e:
        logger.error(f'>> Proxy error: {e}')

    finally:
        try:
            if upstream_writer:
                upstream_writer.close()
                await upstream_writer.wait_closed()
                logger.info(f'>> Stop upstream serving {upstream_address}')
        except Exception as e:
            logger.error(f'>> Upstream closing error {e}')

        try:
            client_writer.close()
            await client_writer.wait_closed()
            logger.info(f'>> Stop client serving {client_address}')
        except Exception as e:
            logger.error(f'>> Client closing error {e}')


async def proxy_client(
    client_reader: StreamReader,
    client_writer: StreamWriter,
) -> None:
    async with CONNECTION_LIMIT:
        await TIMEOUTS.total_timeout(_process_request(client_reader=client_reader, client_writer=client_writer))
