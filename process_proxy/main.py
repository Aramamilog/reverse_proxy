import multiprocessing

from config import PROCESS_COUNT
from worker import run_worker


def main() -> None:
    processes: list[multiprocessing.Process] = []

    for worker_number in range(PROCESS_COUNT):
        process = multiprocessing.Process(
            target=run_worker,
            args=(worker_number + 1,),
            name=f"proxy-worker-{worker_number + 1}",
        )

        process.start()
        processes.append(process)

    print(
        f"Started {PROCESS_COUNT} proxy processes"
    )

    try:
        for process in processes:
            process.join()

    except KeyboardInterrupt:
        print("Stopping process proxy")

    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()

        for process in processes:
            process.join(timeout=5)

        for process in processes:
            if process.is_alive():
                process.kill()
                process.join()


if __name__ == "__main__":
    multiprocessing.set_start_method(
        "spawn",
        force=True,
    )

    main()
