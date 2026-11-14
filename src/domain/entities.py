"""Domain entities, value objects, and validation rules for boardgames, sessions, and UAE events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.domain.errors import ValidationError

VALID_GAME_STATUSES: frozenset[str] = frozenset({"owned", "wishlist", "played"})
VALID_UAE_EMIRATES: tuple[str, ...] = (
    "Dubai",
    "Abu Dhabi",
    "Sharjah",
    "Ajman",
    "Ras Al Khaimah",
    "Fujairah",
    "Umm Al Quwain",
)


def validate_game_status(status: str) -> str:
    """Validate and normalize a board game collection status."""
    cleaned = (status or "").strip().lower()
    if cleaned not in VALID_GAME_STATUSES:
        raise ValidationError(
            f"Invalid game status '{status}'. Must be one of: {', '.join(sorted(VALID_GAME_STATUSES))}.",
            details={"field": "status", "allowed": sorted(VALID_GAME_STATUSES)},
        )
    return cleaned


def validate_emirate(emirate: str) -> str:
    """Validate a UAE emirate name."""
    cleaned = (emirate or "").strip()
    for candidate in VALID_UAE_EMIRATES:
        if candidate.lower() == cleaned.lower():
            return candidate
    raise ValidationError(
        f"Invalid UAE emirate '{emirate}'. Must be one of: {', '.join(VALID_UAE_EMIRATES)}.",
        details={"field": "emirate", "allowed": list(VALID_UAE_EMIRATES)},
    )


@dataclass(frozen=True)
class TurnPhase:
    """Single step or phase in a game's turn-order flow."""

    phase: str
    summary: str

    def to_dict(self) -> dict[str, str]:
        return {"phase": self.phase, "summary": self.summary}


@dataclass(frozen=True)
class GameFilterSpec:
    """Filter specification for querying and curating shareable boardgame lists."""

    status: str | None = None
    players: int | None = None
    max_playtime: int | None = None
    max_complexity: float | None = None
    mechanic: str | None = None
    search: str | None = None
    include_archived: bool = False


@dataclass(frozen=True)
class Game:
    """Board game entity with rule summary, setup steps, turn phases, and collection metadata."""

    id: str
    title: str
    subtitle: str
    min_players: int
    max_players: int
    min_playtime_mins: int
    max_playtime_mins: int
    complexity_weight: float
    status: str
    categories: tuple[str, ...]
    mechanics: tuple[str, ...]
    setup_steps: tuple[str, ...]
    turn_phases: tuple[TurnPhase, ...]
    scoring_rules: tuple[str, ...]
    quick_tips: tuple[str, ...]
    play_count: int = 0
    rating: float = 8.0
    archived: bool = False
    created_at: str = ""

    def matches(self, spec: GameFilterSpec) -> bool:
        """Return True if this game satisfies all criteria in GameFilterSpec."""
        if not spec.include_archived and self.archived:
            return False
        if spec.status and self.status != spec.status.strip().lower():
            return False
        if spec.players is not None and not (self.min_players <= spec.players <= self.max_players):
            return False
        if spec.max_playtime is not None and self.max_playtime_mins > spec.max_playtime:
            return False
        if spec.max_complexity is not None and self.complexity_weight > spec.max_complexity:
            return False
        if spec.mechanic:
            needle = spec.mechanic.strip().lower()
            if not any(needle in m.lower() for m in self.mechanics):
                return False
        if spec.search:
            q = spec.search.strip().lower()
            haystack = " ".join(
                [self.title, self.subtitle, *self.categories, *self.mechanics]
            ).lower()
            if q not in haystack:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        """Serialize Game entity to a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "subtitle": self.subtitle,
            "min_players": self.min_players,
            "max_players": self.max_players,
            "min_playtime_mins": self.min_playtime_mins,
            "max_playtime_mins": self.max_playtime_mins,
            "complexity_weight": round(self.complexity_weight, 2),
            "status": self.status,
            "categories": list(self.categories),
            "mechanics": list(self.mechanics),
            "setup_steps": list(self.setup_steps),
            "turn_phases": [tp.to_dict() for tp in self.turn_phases],
            "scoring_rules": list(self.scoring_rules),
            "quick_tips": list(self.quick_tips),
            "play_count": self.play_count,
            "rating": round(self.rating, 1),
            "archived": self.archived,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class PlaySession:
    """Recorded boardgame play session with players, scores, winner, and notes."""

    id: str
    game_id: str
    game_title: str
    played_on: str
    duration_mins: int
    location: str
    players: tuple[str, ...]
    winner: str
    scores: dict[str, int] = field(default_factory=dict)
    notes: str = ""
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "game_id": self.game_id,
            "game_title": self.game_title,
            "played_on": self.played_on,
            "duration_mins": self.duration_mins,
            "location": self.location,
            "players": list(self.players),
            "winner": self.winner,
            "scores": dict(self.scores),
            "notes": self.notes,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class UaeEvent:
    """UAE boardgame community event, café meetup, tournament, or convention."""

    id: str
    title: str
    emirate: str
    venue: str
    event_date: str
    start_time: str
    category: str
    featured_games: tuple[str, ...]
    organizer: str
    max_players: int
    rsvp_count: int
    description: str
    whatsapp_contact: str
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "emirate": self.emirate,
            "venue": self.venue,
            "event_date": self.event_date,
            "start_time": self.start_time,
            "category": self.category,
            "featured_games": list(self.featured_games),
            "organizer": self.organizer,
            "max_players": self.max_players,
            "rsvp_count": self.rsvp_count,
            "spots_remaining": max(0, self.max_players - self.rsvp_count),
            "description": self.description,
            "whatsapp_contact": self.whatsapp_contact,
            "created_at": self.created_at,
        }
