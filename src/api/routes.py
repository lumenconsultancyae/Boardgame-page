"""HTTP route dispatcher for the Boardgame Page API and static web frontend."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import urllib.parse

from src.api.dtos import ApiResponse, format_error_envelope, parse_game_filter_query
from src.application.boardgame_service import BoardgameService
from src.config.settings import read_app_version
from src.domain.errors import DomainError, NotFoundError, ValidationError

STATIC_DIR = Path(__file__).resolve().parent / "static"


class ApiRouter:
    """Thin HTTP route dispatcher delegating all business workflows to BoardgameService."""

    def __init__(self, service: BoardgameService, app_version: str | None = None) -> None:
        self._service = service
        self._version = app_version or read_app_version()

    def dispatch(
        self,
        method: str,
        raw_path: str,
        json_body: Any = None,
    ) -> ApiResponse:
        """Route an incoming HTTP request to the matching handler or static asset."""
        parsed = urllib.parse.urlsplit(raw_path or "/")
        path = parsed.path.rstrip("/") or "/"
        query = parsed.query
        verb = method.upper()

        try:
            if json_body is None:
                payload: dict[str, Any] = {}
            elif not isinstance(json_body, dict):
                raise ValidationError("Request body must be a JSON object.", details={"field": "body"})
            else:
                payload = json_body

            if verb == "GET" and path in {"/", "/index.html"}:
                return self._serve_static("index.html", "text/html; charset=utf-8")
            if verb == "GET" and path == "/styles.css":
                return self._serve_static("styles.css", "text/css; charset=utf-8")
            if verb == "GET" and path == "/app.js":
                return self._serve_static("app.js", "application/javascript; charset=utf-8")

            if verb == "GET" and path == "/api/v1/health":
                return ApiResponse(
                    status_code=200,
                    body={"status": "ok", "service": "boardgame-page", "version": self._version},
                )

            if path == "/api/v1/games":
                if verb == "GET":
                    spec, _ = parse_game_filter_query(query)
                    items = [g.to_dict() for g in self._service.list_games(spec)]
                    return ApiResponse(status_code=200, body={"items": items, "total": len(items)})
                if verb == "POST":
                    created = self._service.create_game(payload)
                    return ApiResponse(status_code=201, body=created.to_dict())

            if path.startswith("/api/v1/games/"):
                tail = path[len("/api/v1/games/") :]
                parts = [p for p in tail.split("/") if p]
                if len(parts) == 1:
                    game_id = urllib.parse.unquote(parts[0])
                    if verb == "GET":
                        return ApiResponse(status_code=200, body=self._service.get_game(game_id).to_dict())
                    if verb == "PATCH":
                        updated = self._service.update_game(game_id, payload)
                        return ApiResponse(status_code=200, body=updated.to_dict())
                    if verb == "DELETE":
                        return ApiResponse(status_code=200, body=self._service.delete_game(game_id))
                elif len(parts) == 2 and parts[1] == "rules-diagram" and verb == "GET":
                    game_id = urllib.parse.unquote(parts[0])
                    return ApiResponse(status_code=200, body=self._service.get_rules_diagram(game_id))

            if path == "/api/v1/sessions":
                if verb == "GET":
                    q_params = urllib.parse.parse_qs(query)
                    game_id_filter = q_params.get("game_id", [None])[0]
                    sessions = [s.to_dict() for s in self._service.list_sessions(game_id=game_id_filter)]
                    return ApiResponse(status_code=200, body={"items": sessions, "total": len(sessions)})
                if verb == "POST":
                    logged = self._service.log_session(payload)
                    return ApiResponse(status_code=201, body=logged.to_dict())

            if verb == "GET" and path == "/api/v1/analytics":
                return ApiResponse(status_code=200, body=self._service.get_analytics())

            if path == "/api/v1/events":
                if verb == "GET":
                    q_params = urllib.parse.parse_qs(query)
                    emirate = q_params.get("emirate", [None])[0]
                    category = q_params.get("category", [None])[0]
                    search = q_params.get("search", [None])[0]
                    events = [
                        e.to_dict()
                        for e in self._service.list_events(emirate=emirate, category=category, search=search)
                    ]
                    return ApiResponse(status_code=200, body={"items": events, "total": len(events)})
                if verb == "POST":
                    created_evt = self._service.create_event(payload)
                    return ApiResponse(status_code=201, body=created_evt.to_dict())

            if path.startswith("/api/v1/events/"):
                tail = path[len("/api/v1/events/") :]
                parts = [p for p in tail.split("/") if p]
                if len(parts) == 1:
                    event_id = urllib.parse.unquote(parts[0])
                    if verb == "GET":
                        return ApiResponse(status_code=200, body=self._service.get_event(event_id).to_dict())
                    if verb == "DELETE":
                        return ApiResponse(status_code=200, body=self._service.delete_event(event_id))
                elif len(parts) == 2 and parts[1] == "rsvp" and verb == "POST":
                    event_id = urllib.parse.unquote(parts[0])
                    return ApiResponse(status_code=200, body=self._service.rsvp_event(event_id).to_dict())

            if verb == "GET" and path.startswith("/api/v1/share/whatsapp/"):
                tail = path[len("/api/v1/share/whatsapp/") :]
                parts = [p for p in tail.split("/") if p]
                if len(parts) == 1 and parts[0] == "list":
                    spec, list_title = parse_game_filter_query(query)
                    return ApiResponse(
                        status_code=200,
                        body=self._service.share_list_whatsapp(filter_spec=spec, list_title=list_title),
                    )
                if len(parts) == 2 and parts[0] == "game":
                    game_id = urllib.parse.unquote(parts[1])
                    return ApiResponse(status_code=200, body=self._service.share_game_whatsapp(game_id))
                if len(parts) == 2 and parts[0] == "event":
                    event_id = urllib.parse.unquote(parts[1])
                    return ApiResponse(status_code=200, body=self._service.share_event_whatsapp(event_id))

            raise NotFoundError(f"Endpoint '{verb} {path}' not found.", details={"path": path, "method": verb})
        except DomainError as err:
            return format_error_envelope(err)

    @staticmethod
    def _serve_static(filename: str, content_type: str) -> ApiResponse:
        target = STATIC_DIR / filename
        if not target.is_file():
            raise NotFoundError(f"Static asset '{filename}' not found.")
        return ApiResponse(
            status_code=200,
            body=target.read_text(encoding="utf-8"),
            content_type=content_type,
        )
