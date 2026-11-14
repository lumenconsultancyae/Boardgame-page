"""Application entrypoint, HTTP server lifecycle, and in-process test client."""

from __future__ import annotations

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any

from src.api.dtos import ApiResponse
from src.api.routes import ApiRouter
from src.config.settings import Settings, load_settings
from src.injection.container import ServiceContainer, build_container


class BoardgameApplication:
    """Application wrapper holding the composition container and HTTP router."""

    def __init__(self, container: ServiceContainer) -> None:
        self.container = container
        self.router = ApiRouter(
            service=container.boardgame_service,
            app_version=container.settings.app_version,
        )

    def handle_request(
        self,
        method: str,
        path: str,
        json_body: Any = None,
    ) -> ApiResponse:
        return self.router.dispatch(method=method, raw_path=path, json_body=json_body)


@dataclass(frozen=True)
class TestResponse:
    """In-process HTTP response wrapper used by unit and integration tests."""

    __test__ = False

    status_code: int
    content_type: str
    raw_body: Any

    def json(self) -> Any:
        if isinstance(self.raw_body, (dict, list)):
            return self.raw_body
        return json.loads(str(self.raw_body))

    @property
    def text(self) -> str:
        if isinstance(self.raw_body, str):
            return self.raw_body
        return json.dumps(self.raw_body)


class AppTestClient:
    """Zero-network in-process test client for BoardgameApplication."""

    def __init__(self, app: BoardgameApplication) -> None:
        self._app = app

    def request(
        self,
        method: str,
        path: str,
        json_body: Any = None,
    ) -> TestResponse:
        resp = self._app.handle_request(method=method, path=path, json_body=json_body)
        return TestResponse(
            status_code=resp.status_code,
            content_type=resp.content_type,
            raw_body=resp.body,
        )

    def get(self, path: str) -> TestResponse:
        return self.request("GET", path)

    def post(self, path: str, json_body: Any = None) -> TestResponse:
        return self.request("POST", path, json_body=json_body)

    def patch(self, path: str, json_body: Any = None) -> TestResponse:
        return self.request("PATCH", path, json_body=json_body)

    def delete(self, path: str) -> TestResponse:
        return self.request("DELETE", path)


def create_app(settings: Settings | None = None) -> BoardgameApplication:
    """Construct and wire the BoardgameApplication instance."""
    container = build_container(settings=settings)
    return BoardgameApplication(container=container)


def run_server(settings: Settings | None = None) -> None:  # pragma: no cover
    """Start the multithreaded HTTP server for local or container execution."""
    cfg = settings or load_settings()
    app = create_app(cfg)

    class _Handler(BaseHTTPRequestHandler):
        def _dispatch(self, verb: str) -> None:
            payload: Any = None
            content_len = int(self.headers.get("Content-Length", "0") or "0")
            if content_len > 0:
                raw_bytes = self.rfile.read(content_len)
                try:
                    payload = json.loads(raw_bytes.decode("utf-8"))
                except json.JSONDecodeError:
                    self._send(
                        ApiResponse(
                            status_code=400,
                            body={
                                "error": {
                                    "code": "VALIDATION_ERROR",
                                    "message": "Invalid JSON request body.",
                                    "details": {},
                                }
                            },
                        )
                    )
                    return
                if not isinstance(payload, dict):
                    self._send(
                        ApiResponse(
                            status_code=400,
                            body={
                                "error": {
                                    "code": "VALIDATION_ERROR",
                                    "message": "Request body must be a JSON object.",
                                    "details": {"field": "body"},
                                }
                            },
                        )
                    )
                    return
            resp = app.handle_request(verb, self.path, json_body=payload)
            self._send(resp)

        def _send(self, resp: ApiResponse) -> None:
            if isinstance(resp.body, str):
                encoded = resp.body.encode("utf-8")
            else:
                encoded = json.dumps(resp.body).encode("utf-8")
            self.send_response(resp.status_code)
            self.send_header("Content-Type", resp.content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self) -> None:  # noqa: N802
            self._dispatch("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._dispatch("POST")

        def do_PATCH(self) -> None:  # noqa: N802
            self._dispatch("PATCH")

        def do_DELETE(self) -> None:  # noqa: N802
            self._dispatch("DELETE")

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

    server = ThreadingHTTPServer((cfg.app_host, cfg.app_port), _Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":  # pragma: no cover
    run_server()
