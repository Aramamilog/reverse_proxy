from .models import HttpRequest, HttpResponse


class BaseHttpParser:

    SEPARATOR = b"\r\n\r\n"
    CONTENT_LENGTH_KEY = "content-length"

    @staticmethod
    def _split_lines(headers: bytes) -> list[bytes]:
        lines = headers.split(b"\r\n")
        cleared_lines = [line for line in lines if line != b""]
        return cleared_lines

    @staticmethod
    def _get_headers(lines: list[bytes]) -> dict[str, str]:
        headers = {}
        for line in lines:
            k, v = line.decode().split(": ", 1)
            headers[k.lower()] = v

        return headers

    def get_content_length(self, headers: dict[str, str]) -> int:
        return int(headers.get(self.CONTENT_LENGTH_KEY, 0))


class HttpRequestParser(BaseHttpParser):

    @staticmethod
    def _get_method_path_version(request_line: bytes) -> tuple[str, str, str]:
        # TODO: some edge cases like in _get_version_statu_scode_reason_phrase?
        method, path, version = request_line.decode().split()
        return method, path, version

    async def parse_http_request(self, raw_request: bytes) -> HttpRequest:
        lines = self._split_lines(raw_request)
        method, path, version = self._get_method_path_version(lines[0])
        headers = self._get_headers(lines[1:])

        return HttpRequest(
            method=method,
            path=path,
            version=version,
            headers=headers,
        )

http_request_parser = HttpRequestParser()


class HttpResponseParser(BaseHttpParser):

    @staticmethod
    def _get_version_statu_scode_reason_phrase(request_line: bytes) -> tuple[str, int, str]:
        # TODO: what if "404 Not found" or some other bad request?
        version, status_code, reason_phrase = request_line.decode().split()
        return version, int(status_code), reason_phrase

    async def parse_http_response(self, raw_response: bytes) -> HttpResponse:
        lines = self._split_lines(raw_response)
        version, status_code, reason_phrase = self._get_version_statu_scode_reason_phrase(lines[0])
        headers = self._get_headers(lines[1:])

        return HttpResponse(
            status_code=status_code,
            reason_phrase=reason_phrase,
            version=version,
            headers=headers,
        )

http_response_parser = HttpResponseParser()
