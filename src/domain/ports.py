"""Domain repository port definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities import Game, PlaySession, UaeEvent


class BoardgameRepositoryPort(ABC):
    """Abstract persistence port for board games, play sessions, and UAE events."""

    @abstractmethod
    def list_games(self) -> list[Game]:
        """Return all persisted board games ordered by title."""

    @abstractmethod
    def get_game(self, game_id: str) -> Game | None:
        """Return a single board game by ID or None if not found."""

    @abstractmethod
    def save_game(self, game: Game) -> Game:
        """Insert or update a board game record."""

    @abstractmethod
    def delete_game(self, game_id: str) -> bool:
        """Delete a board game by ID and return True if removed."""

    @abstractmethod
    def list_sessions(self, game_id: str | None = None) -> list[PlaySession]:
        """Return logged play sessions ordered by played_on descending."""

    @abstractmethod
    def save_session(self, session: PlaySession) -> PlaySession:
        """Persist a new play session and increment the associated game's play count."""

    @abstractmethod
    def list_events(self, emirate: str | None = None) -> list[UaeEvent]:
        """Return UAE boardgame events ordered by event_date ascending."""

    @abstractmethod
    def get_event(self, event_id: str) -> UaeEvent | None:
        """Return a single UAE boardgame event by ID or None."""

    @abstractmethod
    def save_event(self, event: UaeEvent) -> UaeEvent:
        """Insert or update a UAE boardgame event."""

    @abstractmethod
    def increment_event_rsvp(self, event_id: str) -> UaeEvent | None:
        """Atomically increment rsvp_count if below max_players, returning updated event or None."""

    @abstractmethod
    def delete_event(self, event_id: str) -> bool:
        """Delete a UAE boardgame event by ID and return True if removed."""
