from dataclasses import dataclass


@dataclass
class HttpRequest:
    method: str
    path: str
    version: str
    headers: dict[str, str]


@dataclass
class HttpResponse:
    status_code: int
    reason_phrase: str
    version: str
    headers: dict[str, str]
