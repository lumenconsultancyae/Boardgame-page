"""API request/response data transfer objects and query parsers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import urllib.parse

from src.domain.entities import GameFilterSpec
from src.domain.errors import DomainError, ErrorCode, ValidationError


@dataclass(frozen=True)
class ApiResponse:
    """Transport-agnostic HTTP response representation."""

    status_code: int
    body: Any
    content_type: str = "application/json; charset=utf-8"


def format_error_envelope(err: DomainError) -> ApiResponse:
    """Translate a DomainError into a standardized JSON API error response."""
    status_map = {
        ErrorCode.VALIDATION_ERROR: 400,
        ErrorCode.NOT_FOUND: 404,
        ErrorCode.CONFLICT: 409,
        ErrorCode.INTERNAL_ERROR: 500,
    }
    return ApiResponse(
        status_code=status_map.get(err.code, 400),
        body={
            "error": {
                "code": err.code.value,
                "message": err.message,
                "details": err.details,
            }
        },
    )


def parse_game_filter_query(query_string: str) -> tuple[GameFilterSpec, str]:
    """Parse URL query parameters into a GameFilterSpec and optional list title."""
    params = urllib.parse.parse_qs(query_string or "", keep_blank_values=False)

    def _first(key: str) -> str | None:
        vals = params.get(key)
        return vals[0].strip() if vals and vals[0].strip() else None

    raw_players = _first("players")
    players: int | None = None
    if raw_players is not None:
        try:
            players = int(raw_players)
        except ValueError as exc:
            raise ValidationError("Query parameter 'players' must be an integer.", details={"field": "players"}) from exc

    raw_playtime = _first("max_playtime")
    max_playtime: int | None = None
    if raw_playtime is not None:
        try:
            max_playtime = int(raw_playtime)
        except ValueError as exc:
            raise ValidationError(
                "Query parameter 'max_playtime' must be an integer.",
                details={"field": "max_playtime"},
            ) from exc

    raw_complexity = _first("max_complexity")
    max_complexity: float | None = None
    if raw_complexity is not None:
        try:
            max_complexity = float(raw_complexity)
        except ValueError as exc:
            raise ValidationError(
                "Query parameter 'max_complexity' must be a number.",
                details={"field": "max_complexity"},
            ) from exc

    raw_archived = (_first("include_archived") or "false").lower()
    include_archived = raw_archived in {"1", "true", "yes"}
    list_title = _first("title") or "My Boardgame List"

    spec = GameFilterSpec(
        status=_first("status"),
        players=players,
        max_playtime=max_playtime,
        max_complexity=max_complexity,
        mechanic=_first("mechanic"),
        search=_first("search"),
        include_archived=include_archived,
    )
    return spec, list_title
