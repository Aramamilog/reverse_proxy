import socket
from concurrent.futures import ThreadPoolExecutor

from client_handler import handle_client
from config import LISTEN_HOST, LISTEN_PORT, MAX_WORKERS
from upstream_connection_pool import upstream_connection_pool


def main() -> None:
    upstream_connection_pool.start()

    server_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    )

    server_socket.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1,
    )

    server_socket.bind((LISTEN_HOST, LISTEN_PORT))
    server_socket.listen()

    print(
        f"Thread proxy listening on "
        f"{LISTEN_HOST}:{LISTEN_PORT}, "
        f"workers={MAX_WORKERS}"
    )

    try:
        with ThreadPoolExecutor(
            max_workers=MAX_WORKERS,
            thread_name_prefix="proxy-worker",
        ) as executor:
            while True:
                client_socket, client_address = server_socket.accept()

                executor.submit(
                    handle_client,
                    client_socket,
                    client_address,
                )

    except KeyboardInterrupt:
        print("Stopping thread proxy")

    finally:
        server_socket.close()
        upstream_connection_pool.close()


if __name__ == "__main__":
    main()
