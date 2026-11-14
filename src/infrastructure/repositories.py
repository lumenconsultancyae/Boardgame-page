"""SQLite repository implementation of BoardgameRepositoryPort."""

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator

from src.domain.entities import Game, PlaySession, TurnPhase, UaeEvent
from src.domain.ports import BoardgameRepositoryPort
from src.infrastructure.migrations.schema import apply_migrations_and_seed


class SqliteBoardgameRepository(BoardgameRepositoryPort):
    """SQLite-backed persistence adapter for board games, play sessions, and UAE events."""

    def __init__(self, db_path: str, seed_defaults: bool = True) -> None:
        self._db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            apply_migrations_and_seed(conn, seed_defaults=seed_defaults)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _row_to_game(row: sqlite3.Row) -> Game:
        raw_phases: list[dict[str, Any]] = json.loads(row["turn_phases_json"])
        return Game(
            id=str(row["id"]),
            title=str(row["title"]),
            subtitle=str(row["subtitle"]),
            min_players=int(row["min_players"]),
            max_players=int(row["max_players"]),
            min_playtime_mins=int(row["min_playtime_mins"]),
            max_playtime_mins=int(row["max_playtime_mins"]),
            complexity_weight=float(row["complexity_weight"]),
            status=str(row["status"]),
            categories=tuple(json.loads(row["categories_json"])),
            mechanics=tuple(json.loads(row["mechanics_json"])),
            setup_steps=tuple(json.loads(row["setup_steps_json"])),
            turn_phases=tuple(
                TurnPhase(phase=str(p.get("phase", "")), summary=str(p.get("summary", "")))
                for p in raw_phases
            ),
            scoring_rules=tuple(json.loads(row["scoring_rules_json"])),
            quick_tips=tuple(json.loads(row["quick_tips_json"])),
            play_count=int(row["play_count"]),
            rating=float(row["rating"]),
            archived=bool(row["archived"]),
            created_at=str(row["created_at"]),
        )

    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> PlaySession:
        raw_scores: dict[str, Any] = json.loads(row["scores_json"])
        return PlaySession(
            id=str(row["id"]),
            game_id=str(row["game_id"]),
            game_title=str(row["game_title"]),
            played_on=str(row["played_on"]),
            duration_mins=int(row["duration_mins"]),
            location=str(row["location"]),
            players=tuple(json.loads(row["players_json"])),
            winner=str(row["winner"]),
            scores={str(k): int(v) for k, v in raw_scores.items()},
            notes=str(row["notes"]),
            created_at=str(row["created_at"]),
        )

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> UaeEvent:
        return UaeEvent(
            id=str(row["id"]),
            title=str(row["title"]),
            emirate=str(row["emirate"]),
            venue=str(row["venue"]),
            event_date=str(row["event_date"]),
            start_time=str(row["start_time"]),
            category=str(row["category"]),
            featured_games=tuple(json.loads(row["featured_games_json"])),
            organizer=str(row["organizer"]),
            max_players=int(row["max_players"]),
            rsvp_count=int(row["rsvp_count"]),
            description=str(row["description"]),
            whatsapp_contact=str(row["whatsapp_contact"]),
            created_at=str(row["created_at"]),
        )

    def list_games(self) -> list[Game]:
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM games ORDER BY title ASC").fetchall()
        return [self._row_to_game(r) for r in rows]

    def get_game(self, game_id: str) -> Game | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
        return self._row_to_game(row) if row is not None else None

    def save_game(self, game: Game) -> Game:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO games (
                    id, title, subtitle, min_players, max_players,
                    min_playtime_mins, max_playtime_mins, complexity_weight, status,
                    categories_json, mechanics_json, setup_steps_json, turn_phases_json,
                    scoring_rules_json, quick_tips_json, play_count, rating, archived, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    subtitle = excluded.subtitle,
                    min_players = excluded.min_players,
                    max_players = excluded.max_players,
                    min_playtime_mins = excluded.min_playtime_mins,
                    max_playtime_mins = excluded.max_playtime_mins,
                    complexity_weight = excluded.complexity_weight,
                    status = excluded.status,
                    categories_json = excluded.categories_json,
                    mechanics_json = excluded.mechanics_json,
                    setup_steps_json = excluded.setup_steps_json,
                    turn_phases_json = excluded.turn_phases_json,
                    scoring_rules_json = excluded.scoring_rules_json,
                    quick_tips_json = excluded.quick_tips_json,
                    play_count = excluded.play_count,
                    rating = excluded.rating,
                    archived = excluded.archived
                """,
                (
                    game.id,
                    game.title,
                    game.subtitle,
                    game.min_players,
                    game.max_players,
                    game.min_playtime_mins,
                    game.max_playtime_mins,
                    game.complexity_weight,
                    game.status,
                    json.dumps(list(game.categories)),
                    json.dumps(list(game.mechanics)),
                    json.dumps(list(game.setup_steps)),
                    json.dumps([tp.to_dict() for tp in game.turn_phases]),
                    json.dumps(list(game.scoring_rules)),
                    json.dumps(list(game.quick_tips)),
                    game.play_count,
                    game.rating,
                    1 if game.archived else 0,
                    game.created_at,
                ),
            )
        return game

    def delete_game(self, game_id: str) -> bool:
        with self._connection() as conn:
            conn.execute("DELETE FROM play_sessions WHERE game_id = ?", (game_id,))
            cur = conn.execute("DELETE FROM games WHERE id = ?", (game_id,))
            return cur.rowcount > 0

    def list_sessions(self, game_id: str | None = None) -> list[PlaySession]:
        with self._connection() as conn:
            if game_id:
                rows = conn.execute(
                    "SELECT * FROM play_sessions WHERE game_id = ? ORDER BY played_on DESC, created_at DESC",
                    (game_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM play_sessions ORDER BY played_on DESC, created_at DESC"
                ).fetchall()
        return [self._row_to_session(r) for r in rows]

    def save_session(self, session: PlaySession) -> PlaySession:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO play_sessions (
                    id, game_id, game_title, played_on, duration_mins,
                    location, players_json, winner, scores_json, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.game_id,
                    session.game_title,
                    session.played_on,
                    session.duration_mins,
                    session.location,
                    json.dumps(list(session.players)),
                    session.winner,
                    json.dumps(session.scores),
                    session.notes,
                    session.created_at,
                ),
            )
            conn.execute(
                "UPDATE games SET play_count = play_count + 1 WHERE id = ?",
                (session.game_id,),
            )
        return session

    def list_events(self, emirate: str | None = None) -> list[UaeEvent]:
        with self._connection() as conn:
            if emirate:
                rows = conn.execute(
                    "SELECT * FROM uae_events WHERE LOWER(emirate) = LOWER(?) ORDER BY event_date ASC, start_time ASC",
                    (emirate.strip(),),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM uae_events ORDER BY event_date ASC, start_time ASC"
                ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def get_event(self, event_id: str) -> UaeEvent | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM uae_events WHERE id = ?", (event_id,)).fetchone()
        return self._row_to_event(row) if row is not None else None

    def save_event(self, event: UaeEvent) -> UaeEvent:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO uae_events (
                    id, title, emirate, venue, event_date, start_time, category,
                    featured_games_json, organizer, max_players, rsvp_count,
                    description, whatsapp_contact, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    emirate = excluded.emirate,
                    venue = excluded.venue,
                    event_date = excluded.event_date,
                    start_time = excluded.start_time,
                    category = excluded.category,
                    featured_games_json = excluded.featured_games_json,
                    organizer = excluded.organizer,
                    max_players = excluded.max_players,
                    rsvp_count = excluded.rsvp_count,
                    description = excluded.description,
                    whatsapp_contact = excluded.whatsapp_contact
                """,
                (
                    event.id,
                    event.title,
                    event.emirate,
                    event.venue,
                    event.event_date,
                    event.start_time,
                    event.category,
                    json.dumps(list(event.featured_games)),
                    event.organizer,
                    event.max_players,
                    event.rsvp_count,
                    event.description,
                    event.whatsapp_contact,
                    event.created_at,
                ),
            )
        return event

    def increment_event_rsvp(self, event_id: str) -> UaeEvent | None:
        with self._connection() as conn:
            cur = conn.execute(
                "UPDATE uae_events SET rsvp_count = rsvp_count + 1 WHERE id = ? AND rsvp_count < max_players",
                (event_id,),
            )
            if cur.rowcount == 0:
                return None
            row = conn.execute("SELECT * FROM uae_events WHERE id = ?", (event_id,)).fetchone()
        return self._row_to_event(row) if row is not None else None

    def delete_event(self, event_id: str) -> bool:
        with self._connection() as conn:
            cur = conn.execute("DELETE FROM uae_events WHERE id = ?", (event_id,))
            return cur.rowcount > 0
