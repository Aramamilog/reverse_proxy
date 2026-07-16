from dataclasses import dataclass
from pathlib import Path

import yaml
from asyncio import Semaphore

from timeouts import Timeouts


@dataclass(frozen=True)
class ListenConfig:
    host: str
    port: int


@dataclass(frozen=True)
class UpstreamConfig:
    host: str
    port: int
    pool_size: int
    concurrency_limit: int

    @property
    def key(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass(frozen=True)
class TimeoutsConfig:
    connect_ms: int
    read_ms: int
    write_ms: int
    total_ms: int


@dataclass(frozen=True)
class LimitsConfig:
    max_client_conns: int


@dataclass(frozen=True)
class LoggingConfig:
    level: str


@dataclass(frozen=True)
class AppConfig:
    listen: ListenConfig
    upstreams: list[UpstreamConfig]
    timeouts: TimeoutsConfig
    limits: LimitsConfig
    logging: LoggingConfig


class ConfigLoader:
    @staticmethod
    def load(path: str = "config.yaml") -> AppConfig:
        config_path = Path(path)

        with config_path.open("r") as file:
            raw = yaml.safe_load(file)

        upstreams = [
            UpstreamConfig(
                host=item["host"],
                port=int(item["port"]),
                pool_size=int(item.get("pool_size", raw["limits"].get("max_conns_per_upstream", 100))),
                concurrency_limit=int(item.get("concurrency_limit", raw["limits"].get("max_conns_per_upstream", 100))),
            )
            for item in raw["upstreams"]
        ]

        if not upstreams:
            raise ValueError("Config error: upstreams cannot be empty")

        return AppConfig(
            listen=ListenConfig(
                host=raw["listen"]["host"],
                port=int(raw["listen"]["port"]),
            ),
            upstreams=upstreams,
            timeouts=TimeoutsConfig(
                connect_ms=int(raw["timeouts"]["connect_ms"]),
                read_ms=int(raw["timeouts"]["read_ms"]),
                write_ms=int(raw["timeouts"]["write_ms"]),
                total_ms=int(raw["timeouts"]["total_ms"]),
            ),
            limits=LimitsConfig(
                max_client_conns=int(raw["limits"]["max_client_conns"]),
            ),
            logging=LoggingConfig(
                level=raw["logging"]["level"],
            ),
        )


APP_CONFIG = ConfigLoader.load()

TIMEOUTS = Timeouts(
    connect=APP_CONFIG.timeouts.connect_ms / 1000,
    read=APP_CONFIG.timeouts.read_ms / 1000,
    write=APP_CONFIG.timeouts.write_ms / 1000,
    total=APP_CONFIG.timeouts.total_ms / 1000,
)

CONNECTION_LIMIT = Semaphore(APP_CONFIG.limits.max_client_conns)
UPSTREAMS = APP_CONFIG.upstreams
