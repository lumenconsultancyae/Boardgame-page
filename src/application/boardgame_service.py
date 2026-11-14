"""Application service orchestrating boardgame tracking, rule diagrams, analytics, WhatsApp sharing, and UAE events."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import re
from typing import Any
import uuid

from src.domain.entities import (
    Game,
    GameFilterSpec,
    PlaySession,
    TurnPhase,
    UaeEvent,
    validate_emirate,
    validate_game_status,
)
from src.domain.errors import NotFoundError, ValidationError
from src.domain.ports import BoardgameRepositoryPort
from src.utils.formatting import (
    build_collection_analytics,
    build_rule_diagram,
    build_whatsapp_event_share,
    build_whatsapp_game_share,
    build_whatsapp_list_share,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slugify(value: str, prefix: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")[:28] or "item"
    short_uuid = uuid.uuid4().hex[:6]
    return f"{prefix}-{slug}-{short_uuid}"


def _require_dict_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Request payload must be a JSON object.", details={"field": "body"})
    return payload


def _parse_str(
    payload: dict[str, Any],
    field: str,
    *,
    default: str | None = None,
    required: bool = False,
    allow_empty: bool = False,
) -> str:
    if field not in payload:
        if required and default is None:
            raise ValidationError(f"Field '{field}' is required.", details={"field": field})
        return default or ""
    raw = payload[field]
    if raw is None:
        if required or default is None:
            raise ValidationError(f"Field '{field}' cannot be null.", details={"field": field})
        return default
    if not isinstance(raw, str):
        raise ValidationError(f"Field '{field}' must be a string.", details={"field": field})
    cleaned = raw.strip()
    if not cleaned and not allow_empty:
        if required or default is None:
            raise ValidationError(f"Field '{field}' cannot be empty.", details={"field": field})
        return default
    return cleaned


def _parse_int(payload: dict[str, Any], field: str, default: int) -> int:
    if field not in payload:
        return default
    raw = payload[field]
    if raw is None or isinstance(raw, bool):
        raise ValidationError(f"Field '{field}' must be an integer.", details={"field": field})
    try:
        return int(raw)
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"Field '{field}' must be an integer.", details={"field": field}) from exc


def _parse_float(payload: dict[str, Any], field: str, default: float) -> float:
    if field not in payload:
        return default
    raw = payload[field]
    if raw is None or isinstance(raw, bool):
        raise ValidationError(f"Field '{field}' must be a number.", details={"field": field})
    try:
        return float(raw)
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"Field '{field}' must be a number.", details={"field": field}) from exc


def _parse_bool(payload: dict[str, Any], field: str, default: bool) -> bool:
    if field not in payload:
        return default
    raw = payload[field]
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        norm = raw.strip().lower()
        if norm in {"true", "1", "yes"}:
            return True
        if norm in {"false", "0", "no"}:
            return False
    raise ValidationError(f"Field '{field}' must be a boolean.", details={"field": field})


def _parse_str_tuple(
    payload: dict[str, Any],
    field: str,
    default: tuple[str, ...],
    *,
    delimiters: str = r"[;,\n]+",
) -> tuple[str, ...]:
    if field not in payload or payload[field] is None:
        return default
    raw = payload[field]
    if isinstance(raw, str):
        items = tuple(part.strip() for part in re.split(delimiters, raw) if part.strip())
        return items or default
    if isinstance(raw, (list, tuple)):
        cleaned: list[str] = []
        for item in raw:
            if not isinstance(item, str):
                raise ValidationError(
                    f"All entries in '{field}' must be strings.",
                    details={"field": field},
                )
            if item.strip():
                cleaned.append(item.strip())
        return tuple(cleaned) or default
    raise ValidationError(f"Field '{field}' must be a list of strings or delimited string.", details={"field": field})


class BoardgameService:
    """Primary application service for boardgame catalog, play sessions, rule diagrams, and UAE events."""

    def __init__(self, repository: BoardgameRepositoryPort) -> None:
        self._repo = repository

    def list_games(self, filter_spec: GameFilterSpec | None = None) -> list[Game]:
        """Return board games matching the optional filter specification."""
        spec = filter_spec or GameFilterSpec()
        if spec.status:
            validate_game_status(spec.status)
        all_games = self._repo.list_games()
        return [g for g in all_games if g.matches(spec)]

    def get_game(self, game_id: str) -> Game:
        """Return a board game by ID or raise NotFoundError."""
        game = self._repo.get_game(game_id)
        if game is None:
            raise NotFoundError(f"Board game '{game_id}' was not found.", details={"game_id": game_id})
        return game

    def create_game(self, payload: dict[str, Any]) -> Game:
        """Validate and persist a new board game in the collection."""
        data = _require_dict_payload(payload)
        title = _parse_str(data, "title", required=True)
        subtitle = _parse_str(data, "subtitle", default="Board game rule summary & play tracker")
        min_players = _parse_int(data, "min_players", 2)
        max_players = _parse_int(data, "max_players", 4)
        if min_players < 1 or max_players < min_players:
            raise ValidationError(
                "Invalid player range: min_players must be >= 1 and <= max_players.",
                details={"field": "min_players"},
            )

        max_playtime = _parse_int(data, "max_playtime_mins", 60)
        min_playtime = _parse_int(data, "min_playtime_mins", min(30, max(5, max_playtime)))
        if min_playtime < 5 or max_playtime < min_playtime:
            raise ValidationError(
                "Invalid playtime range: min_playtime_mins must be >= 5 and <= max_playtime_mins.",
                details={"field": "min_playtime_mins"},
            )

        complexity = _parse_float(data, "complexity_weight", 2.0)
        if not (1.0 <= complexity <= 5.0):
            raise ValidationError(
                "Complexity weight must be between 1.0 and 5.0.",
                details={"field": "complexity_weight"},
            )

        status = validate_game_status(_parse_str(data, "status", default="owned"))
        rating = _parse_float(data, "rating", 8.0)
        if not (1.0 <= rating <= 10.0):
            raise ValidationError("Rating must be between 1.0 and 10.0.", details={"field": "rating"})

        categories = _parse_str_tuple(data, "categories", ("Strategy",))
        mechanics = _parse_str_tuple(data, "mechanics", ("Hand Management",))
        setup_steps = _parse_str_tuple(
            data,
            "setup_steps",
            (f"Place the {title} main board and components in reach of all players.",),
            delimiters=r"[;\n]+",
        )

        raw_phases = data.get("turn_phases") or [
            {"phase": "Main Action", "summary": "Execute your primary turn action."},
            {"phase": "End of Turn", "summary": "Refresh hand/resources and pass turn clockwise."},
        ]
        if not isinstance(raw_phases, (list, tuple)):
            raise ValidationError("Field 'turn_phases' must be a list of phase objects.", details={"field": "turn_phases"})
        turn_phases = tuple(
            TurnPhase(
                phase=str(tp.get("phase") or f"Phase {i}").strip(),
                summary=str(tp.get("summary") or "Resolve phase actions.").strip(),
            )
            for i, tp in enumerate(raw_phases, start=1)
            if isinstance(tp, dict)
        )

        scoring_rules = _parse_str_tuple(
            data,
            "scoring_rules",
            ("Highest Victory Points total at game end wins.",),
            delimiters=r"[;\n]+",
        )
        quick_tips = _parse_str_tuple(
            data,
            "quick_tips",
            ("Review setup and scoring triggers before Turn 1.",),
            delimiters=r"[;\n]+",
        )

        game = Game(
            id=_slugify(title, "game"),
            title=title,
            subtitle=subtitle,
            min_players=min_players,
            max_players=max_players,
            min_playtime_mins=min_playtime,
            max_playtime_mins=max_playtime,
            complexity_weight=complexity,
            status=status,
            categories=categories,
            mechanics=mechanics,
            setup_steps=setup_steps,
            turn_phases=turn_phases,
            scoring_rules=scoring_rules,
            quick_tips=quick_tips,
            play_count=_parse_int(data, "play_count", 0),
            rating=rating,
            archived=_parse_bool(data, "archived", False),
            created_at=_utc_now_iso(),
        )
        return self._repo.save_game(game)

    def update_game(self, game_id: str, payload: dict[str, Any]) -> Game:
        """Update mutable fields on an existing board game (status, rating, title, archived, etc.)."""
        data = _require_dict_payload(payload)
        existing = self.get_game(game_id)
        status = (
            validate_game_status(_parse_str(data, "status", required=True))
            if "status" in data
            else existing.status
        )
        rating = _parse_float(data, "rating", existing.rating)
        if not (1.0 <= rating <= 10.0):
            raise ValidationError("Rating must be between 1.0 and 10.0.", details={"field": "rating"})

        complexity = _parse_float(data, "complexity_weight", existing.complexity_weight)
        if not (1.0 <= complexity <= 5.0):
            raise ValidationError(
                "Complexity weight must be between 1.0 and 5.0.",
                details={"field": "complexity_weight"},
            )

        title = _parse_str(data, "title", required=True) if "title" in data else existing.title
        subtitle = _parse_str(data, "subtitle", required=True) if "subtitle" in data else existing.subtitle
        archived = _parse_bool(data, "archived", existing.archived)
        updated = replace(
            existing,
            title=title,
            subtitle=subtitle,
            status=status,
            rating=rating,
            complexity_weight=complexity,
            archived=archived,
        )
        return self._repo.save_game(updated)

    def delete_game(self, game_id: str) -> dict[str, str]:
        """Delete a board game by ID or raise NotFoundError."""
        self.get_game(game_id)
        self._repo.delete_game(game_id)
        return {"deleted_id": game_id, "status": "deleted"}

    def get_rules_diagram(self, game_id: str) -> dict[str, Any]:
        """Generate the visual rule summary and interactive flowchart diagram for a game."""
        game = self.get_game(game_id)
        return build_rule_diagram(game)

    def list_sessions(self, game_id: str | None = None) -> list[PlaySession]:
        """List logged play sessions, optionally filtered by game_id."""
        return self._repo.list_sessions(game_id=game_id)

    def log_session(self, payload: dict[str, Any]) -> PlaySession:
        """Record a new play session and increment the parent game's play_count."""
        data = _require_dict_payload(payload)
        game_id = _parse_str(data, "game_id", required=True)
        game = self.get_game(game_id)

        played_on = _parse_str(data, "played_on", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        duration_mins = _parse_int(data, "duration_mins", game.max_playtime_mins)
        if duration_mins < 5:
            raise ValidationError("duration_mins must be at least 5 minutes.", details={"field": "duration_mins"})

        players = _parse_str_tuple(data, "players", ())
        if not players:
            raise ValidationError("At least one player name is required.", details={"field": "players"})

        winner = _parse_str(data, "winner", default=players[0])
        raw_scores = data.get("scores") or {}
        if not isinstance(raw_scores, dict):
            raise ValidationError("Field 'scores' must be an object mapping player names to integer scores.", details={"field": "scores"})
        scores: dict[str, int] = {}
        for k, v in raw_scores.items():
            if isinstance(v, bool) or v is None:
                raise ValidationError("Score values must be integers.", details={"field": "scores"})
            if str(k).strip():
                try:
                    scores[str(k).strip()] = int(v)
                except (ValueError, TypeError) as exc:
                    raise ValidationError("Score values must be integers.", details={"field": "scores"}) from exc

        session = PlaySession(
            id=_slugify(game.title, "session"),
            game_id=game.id,
            game_title=game.title,
            played_on=played_on,
            duration_mins=duration_mins,
            location=_parse_str(data, "location", default="Dubai Game Night"),
            players=players,
            winner=winner,
            scores=scores,
            notes=_parse_str(data, "notes", default="", allow_empty=True),
            created_at=_utc_now_iso(),
        )
        return self._repo.save_session(session)

    def get_analytics(self) -> dict[str, Any]:
        """Compute collection analytics graphs and summary metrics."""
        games = self._repo.list_games()
        sessions = self._repo.list_sessions()
        return build_collection_analytics(games, sessions)

    def list_events(self, emirate: str | None = None, category: str | None = None, search: str | None = None) -> list[UaeEvent]:
        """List UAE boardgame events filtered by emirate, category, or search term."""
        normalized_emirate = validate_emirate(emirate) if emirate and emirate.strip() else None
        events = self._repo.list_events(emirate=normalized_emirate)
        if category and category.strip():
            cat_q = category.strip().lower()
            events = [e for e in events if e.category.lower() == cat_q]
        if search and search.strip():
            sq = search.strip().lower()
            events = [
                e
                for e in events
                if sq in " ".join([e.title, e.venue, e.emirate, e.description, *e.featured_games]).lower()
            ]
        return events

    def get_event(self, event_id: str) -> UaeEvent:
        """Return a single UAE boardgame event or raise NotFoundError."""
        event = self._repo.get_event(event_id)
        if event is None:
            raise NotFoundError(f"UAE Event '{event_id}' was not found.", details={"event_id": event_id})
        return event

    def create_event(self, payload: dict[str, Any]) -> UaeEvent:
        """Validate and create a new UAE boardgame event."""
        data = _require_dict_payload(payload)
        title = _parse_str(data, "title", required=True)
        emirate = validate_emirate(_parse_str(data, "emirate", default="Dubai"))
        venue = _parse_str(data, "venue", required=True)
        event_date = _parse_str(data, "event_date", default="2026-12-01")
        start_time = _parse_str(data, "start_time", default="18:30")
        category = _parse_str(data, "category", default="Meetup")
        featured = _parse_str_tuple(data, "featured_games", ("Catan",))

        max_players = _parse_int(data, "max_players", 16)
        rsvp_count = _parse_int(data, "rsvp_count", 1)
        if max_players < 2 or rsvp_count < 0 or rsvp_count > max_players:
            raise ValidationError(
                "Invalid event capacity: max_players must be >= 2 and rsvp_count <= max_players.",
                details={"field": "max_players"},
            )

        event = UaeEvent(
            id=_slugify(title, "event"),
            title=title,
            emirate=emirate,
            venue=venue,
            event_date=event_date,
            start_time=start_time,
            category=category,
            featured_games=featured,
            organizer=_parse_str(data, "organizer", default="UAE Tabletop Community"),
            max_players=max_players,
            rsvp_count=rsvp_count,
            description=_parse_str(data, "description", default="Community boardgame session."),
            whatsapp_contact=_parse_str(data, "whatsapp_contact", default="+971500000000"),
            created_at=_utc_now_iso(),
        )
        return self._repo.save_event(event)

    def rsvp_event(self, event_id: str) -> UaeEvent:
        """Atomically increment RSVP count for a UAE boardgame event if seats remain."""
        event = self.get_event(event_id)
        updated = self._repo.increment_event_rsvp(event_id)
        if updated is None:
            raise ValidationError(
                f"Event '{event.title}' has reached maximum capacity ({event.max_players} players).",
                details={"event_id": event_id, "max_players": event.max_players},
            )
        return updated

    def delete_event(self, event_id: str) -> dict[str, str]:
        """Delete a UAE boardgame event by ID."""
        self.get_event(event_id)
        self._repo.delete_event(event_id)
        return {"deleted_id": event_id, "status": "deleted"}

    def share_game_whatsapp(self, game_id: str) -> dict[str, str]:
        """Generate WhatsApp rule summary share message and wa.me deep link for a game."""
        game = self.get_game(game_id)
        return build_whatsapp_game_share(game)

    def share_list_whatsapp(
        self,
        filter_spec: GameFilterSpec | None = None,
        list_title: str = "My Boardgame List",
    ) -> dict[str, str]:
        """Generate WhatsApp curated game list share message and wa.me deep link."""
        games = self.list_games(filter_spec)
        return build_whatsapp_list_share(games, list_title=list_title)

    def share_event_whatsapp(self, event_id: str) -> dict[str, str]:
        """Generate WhatsApp UAE boardgame event invite and wa.me deep link."""
        event = self.get_event(event_id)
        return build_whatsapp_event_share(event)
