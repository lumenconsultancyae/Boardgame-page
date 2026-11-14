"""Integration and service tests for BoardgameService, SQLite repository, and HTTP API routes."""

from __future__ import annotations

import inspect
from pathlib import Path
import re
from unittest.mock import create_autospec
import pytest

from src.api.app import AppTestClient, TestResponse, create_app
from src.application.boardgame_service import BoardgameService
from src.config.settings import Settings, read_app_version
from src.domain.ports import BoardgameRepositoryPort
from src.infrastructure.repositories import SqliteBoardgameRepository


@pytest.fixture()
def isolated_client(tmp_path: Path) -> AppTestClient:
    """Create an isolated in-process test client backed by a temporary SQLite database."""
    db_file = tmp_path / "test_boardgames.sqlite3"
    live_db = Path("data/boardgames.sqlite3").resolve()
    assert db_file.resolve() != live_db, "Tests must never touch live database path"
    settings = Settings(
        app_host="127.0.0.1",
        app_port=0,
        db_path=str(db_file),
        seed_defaults=True,
        environment="test",
    )
    app = create_app(settings)
    return AppTestClient(app)


def test_repository_implements_domain_port_signature() -> None:
    """Verify SqliteBoardgameRepository satisfies every method signature on BoardgameRepositoryPort."""
    mock_port = create_autospec(BoardgameRepositoryPort, instance=True)
    mock_port.list_games.return_value = []
    mock_port.list_sessions.return_value = []
    service = BoardgameService(repository=mock_port)
    assert service.list_games() == []
    assert service.list_sessions() == []
    mock_port.list_games.assert_called_once()
    mock_port.list_sessions.assert_called_once()

    for name, member in inspect.getmembers(BoardgameRepositoryPort, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        assert hasattr(SqliteBoardgameRepository, name), f"Missing port method {name}"
        port_sig = inspect.signature(member)
        impl_sig = inspect.signature(getattr(SqliteBoardgameRepository, name))
        assert list(port_sig.parameters.keys()) == list(impl_sig.parameters.keys())


def test_health_and_seeded_catalog_endpoints(isolated_client: AppTestClient) -> None:
    """Verify health endpoint and default seeded board games, sessions, and UAE events."""
    health = isolated_client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["version"] == read_app_version()
    assert isinstance(health.text, str)
    raw_json_resp = TestResponse(status_code=200, content_type="application/json", raw_body='{"ok": true}')
    assert raw_json_resp.json() == {"ok": True}

    games_resp = isolated_client.get("/api/v1/games")
    assert games_resp.status_code == 200
    games = games_resp.json()["items"]
    assert len(games) >= 6
    titles = {g["title"] for g in games}
    assert {"Catan", "Wingspan", "Azul", "Dune: Imperium"} <= titles

    # Filter by player count and complexity
    filtered = isolated_client.get("/api/v1/games?players=2&max_complexity=2.5")
    assert filtered.status_code == 200
    for item in filtered.json()["items"]:
        assert item["min_players"] <= 2 <= item["max_players"]
        assert item["complexity_weight"] <= 2.5


def test_game_crud_and_archive_lifecycle(isolated_client: AppTestClient) -> None:
    """Verify creating, inspecting, updating, archiving, and deleting a board game."""
    payload = {
        "title": "7 Wonders Duel",
        "subtitle": "Head-to-head card drafting civilization builder",
        "min_players": 2,
        "max_players": 2,
        "min_playtime_mins": 30,
        "max_playtime_mins": 45,
        "complexity_weight": 2.2,
        "status": "owned",
        "categories": ["Card Game", "Civilization"],
        "mechanics": ["Card Drafting", "Set Collection"],
        "setup_steps": [
            "Arrange Age I card pyramid face-up and face-down per diagram.",
            "Place military conflict pawn on neutral center space.",
        ],
        "turn_phases": [
            {"phase": "Draft Accessible Card", "summary": "Pick an uncovered card from the pyramid."},
            {"phase": "Construct, Discard for Coins, or Build Wonder", "summary": "Use the card in 1 of 3 ways."},
        ],
        "scoring_rules": [
            "Instant victory via Military Supremacy or Scientific Supremacy.",
            "Otherwise sum Civilian, Wonder, Science, Commercial, Guild, and Treasury VP at end of Age III.",
        ],
        "quick_tips": ["Watch opponent science symbols closely."],
        "rating": 8.9,
    }
    created = isolated_client.post("/api/v1/games", json_body=payload)
    assert created.status_code == 201
    game_id = created.json()["id"]

    fetched = isolated_client.get(f"/api/v1/games/{game_id}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "7 Wonders Duel"

    # Patch status, rating, and archive state
    patched = isolated_client.patch(
        f"/api/v1/games/{game_id}",
        json_body={"status": "played", "rating": 9.2, "archived": True},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "played"
    assert patched.json()["rating"] == 9.2
    assert patched.json()["archived"] is True

    # Archived game is hidden by default and visible with include_archived=true
    active_ids = {g["id"] for g in isolated_client.get("/api/v1/games").json()["items"]}
    assert game_id not in active_ids
    all_ids = {g["id"] for g in isolated_client.get("/api/v1/games?include_archived=true").json()["items"]}
    assert game_id in all_ids

    deleted = isolated_client.delete(f"/api/v1/games/{game_id}")
    assert deleted.status_code == 200
    assert isolated_client.get(f"/api/v1/games/{game_id}").status_code == 404


def test_rules_diagram_and_whatsapp_sharing_endpoints(isolated_client: AppTestClient) -> None:
    """Verify visual rule diagram generation and WhatsApp sharing endpoints for games, lists, and events."""
    games = isolated_client.get("/api/v1/games").json()["items"]
    first_id = games[0]["id"]

    diagram_resp = isolated_client.get(f"/api/v1/games/{first_id}/rules-diagram")
    assert diagram_resp.status_code == 200
    diag = diagram_resp.json()
    assert diag["game_id"] == first_id
    assert diag["mermaid_code"].startswith("flowchart LR")
    assert len(diag["diagram_nodes"]) >= 3

    wa_game = isolated_client.get(f"/api/v1/share/whatsapp/game/{first_id}")
    assert wa_game.status_code == 200
    assert wa_game.json()["whatsapp_url"].startswith("https://wa.me/?text=")

    wa_list = isolated_client.get("/api/v1/share/whatsapp/list?status=owned&title=Weekend+Picks")
    assert wa_list.status_code == 200
    assert "Weekend Picks" in wa_list.json()["text"]

    events = isolated_client.get("/api/v1/events").json()["items"]
    wa_event = isolated_client.get(f"/api/v1/share/whatsapp/event/{events[0]['id']}")
    assert wa_event.status_code == 200
    assert wa_event.json()["whatsapp_url"].startswith("https://wa.me/?text=")


def test_play_session_logging_updates_game_play_count_and_analytics(isolated_client: AppTestClient) -> None:
    """Verify logging a play session increments the game's play_count and updates analytics graphs."""
    games = isolated_client.get("/api/v1/games").json()["items"]
    target = games[0]
    initial_plays = target["play_count"]

    session_resp = isolated_client.post(
        "/api/v1/sessions",
        json_body={
            "game_id": target["id"],
            "played_on": "2026-11-13",
            "duration_mins": 65,
            "location": "Unwind Specialty Boardgame Cafe, Dubai",
            "players": ["Tariq", "Noor", "Sami"],
            "winner": "Noor",
            "scores": {"Tariq": 42, "Noor": 51, "Sami": 39},
            "notes": "Taught rules using the interactive turn flowchart!",
        },
    )
    assert session_resp.status_code == 201

    updated_game = isolated_client.get(f"/api/v1/games/{target['id']}").json()
    assert updated_game["play_count"] == initial_plays + 1

    sessions_list = isolated_client.get(f"/api/v1/sessions?game_id={target['id']}").json()["items"]
    assert any(s["winner"] == "Noor" for s in sessions_list)

    analytics = isolated_client.get("/api/v1/analytics")
    assert analytics.status_code == 200
    stats = analytics.json()
    assert stats["total_games"] >= 6
    assert len(stats["complexity_distribution"]) == 3
    assert len(stats["mechanics_breakdown"]) >= 3


def test_uae_events_filtering_creation_and_rsvp_limits(isolated_client: AppTestClient) -> None:
    """Verify UAE boardgame events can be filtered by emirate, created, RSVP'd up to capacity, and deleted."""
    dubai_events = isolated_client.get("/api/v1/events?emirate=Dubai").json()["items"]
    assert len(dubai_events) >= 1
    assert all(e["emirate"] == "Dubai" for e in dubai_events)

    created_evt = isolated_client.post(
        "/api/v1/events",
        json_body={
            "title": "Sharjah Heavy Euro Showdown",
            "emirate": "Sharjah",
            "venue": "House of Wisdom Community Lounge",
            "event_date": "2026-11-28",
            "start_time": "17:30",
            "category": "Tournament",
            "featured_games": ["Terraforming Mars", "Brass: Birmingham"],
            "organizer": "Sharjah Boardgame Society",
            "max_players": 2,
            "rsvp_count": 1,
            "description": "Competitive Eurogame session with rule refreshers.",
            "whatsapp_contact": "+971509876543",
        },
    )
    assert created_evt.status_code == 201
    evt_id = created_evt.json()["id"]

    # First RSVP reaches max capacity (2/2)
    rsvp1 = isolated_client.post(f"/api/v1/events/{evt_id}/rsvp")
    assert rsvp1.status_code == 200
    assert rsvp1.json()["rsvp_count"] == 2

    # Second RSVP when full returns 400 validation error
    rsvp_full = isolated_client.post(f"/api/v1/events/{evt_id}/rsvp")
    assert rsvp_full.status_code == 400
    assert rsvp_full.json()["error"]["code"] == "VALIDATION_ERROR"

    del_resp = isolated_client.delete(f"/api/v1/events/{evt_id}")
    assert del_resp.status_code == 200


def test_api_validation_and_error_envelopes(isolated_client: AppTestClient) -> None:
    """Verify structured error envelopes for invalid payloads, missing resources, and static assets."""
    bad_game = isolated_client.post("/api/v1/games", json_body={"title": ""})
    assert bad_game.status_code == 400
    assert bad_game.json()["error"]["code"] == "VALIDATION_ERROR"

    missing_game = isolated_client.get("/api/v1/games/non-existent-id")
    assert missing_game.status_code == 404
    assert missing_game.json()["error"]["code"] == "NOT_FOUND"

    bad_session = isolated_client.post(
        "/api/v1/sessions",
        json_body={"game_id": "non-existent-id", "played_on": "2026-11-13", "players": ["Ali"], "winner": "Ali"},
    )
    assert bad_session.status_code == 404

    index_html = isolated_client.get("/")
    assert index_html.status_code == 200
    assert "Boardgame" in index_html.text
    assert 'aria-describedby="game-title-error"' in index_html.text
    assert 'data-testid="filter-playtime"' in index_html.text
    assert 'data-testid="session-scores-input"' in index_html.text

    styles_css = isolated_client.get("/styles.css")
    assert styles_css.status_code == 200
    assert "color-mix(in oklab" in styles_css.text
    assert "prefers-reduced-motion: reduce" in styles_css.text

    app_js = isolated_client.get("/app.js")
    assert app_js.status_code == 200
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", app_js.text)

    # Additional combinatorial validation and edge-case branches
    assert isolated_client.get("/api/v1/games?players=abc").status_code == 400
    assert isolated_client.get("/api/v1/games?max_playtime=abc").status_code == 400
    assert isolated_client.get("/api/v1/games?max_playtime=60").status_code == 200
    assert isolated_client.get("/api/v1/games?max_complexity=abc").status_code == 400
    assert isolated_client.get("/api/v1/unknown-route").status_code == 404

    # Non-dict JSON bodies and strict primitive validation
    assert isolated_client.post("/api/v1/games", json_body=["not-a-dict"]).status_code == 400
    assert isolated_client.post("/api/v1/games", json_body={"title": True}).status_code == 400
    assert isolated_client.post("/api/v1/games", json_body={"title": "X", "min_players": True}).status_code == 400
    assert isolated_client.post("/api/v1/games", json_body={"title": "X", "min_players": None}).status_code == 400
    assert isolated_client.post("/api/v1/games", json_body={"title": "X", "min_players": "bad"}).status_code == 400
    assert isolated_client.post("/api/v1/games", json_body={"title": "X", "complexity_weight": True}).status_code == 400
    assert isolated_client.post("/api/v1/games", json_body={"title": "X", "complexity_weight": "bad"}).status_code == 400
    assert isolated_client.post("/api/v1/games", json_body={"title": "X", "archived": "invalid-bool"}).status_code == 400
    assert isolated_client.post("/api/v1/games", json_body={"title": "X", "mechanics": [123]}).status_code == 400
    assert isolated_client.post("/api/v1/games", json_body={"title": "X", "mechanics": 123}).status_code == 400
    assert isolated_client.post("/api/v1/games", json_body={"title": "X", "turn_phases": "bad"}).status_code == 400

    # Short filler game (< 30m) and string-delimited mechanics/setup_steps
    short_game = isolated_client.post(
        "/api/v1/games",
        json_body={
            "title": "Love Letter",
            "max_playtime_mins": 20,
            "mechanics": "Hand Management, Deduction",
            "setup_steps": "Shuffle 16 cards; Burn 1 card face-down",
            "archived": "false",
        },
    )
    assert short_game.status_code == 201
    short_data = short_game.json()
    assert short_data["min_playtime_mins"] == 20
    assert short_data["max_playtime_mins"] == 20
    assert short_data["mechanics"] == ["Hand Management", "Deduction"]
    assert short_data["setup_steps"] == ["Shuffle 16 cards", "Burn 1 card face-down"]
    assert short_data["archived"] is False

    # Log session on short_game and verify cascading delete removes child sessions
    logged_s = isolated_client.post(
        "/api/v1/sessions",
        json_body={"game_id": short_data["id"], "players": ["Layla", "Zayd"], "winner": "Layla"},
    )
    assert logged_s.status_code == 201
    assert len(isolated_client.get(f"/api/v1/sessions?game_id={short_data['id']}").json()["items"]) == 1
    assert isolated_client.delete(f"/api/v1/games/{short_data['id']}").status_code == 200
    assert len(isolated_client.get(f"/api/v1/sessions?game_id={short_data['id']}").json()["items"]) == 0

    assert isolated_client.post("/api/v1/games", json_body={"title": "X", "min_players": 0}).status_code == 400
    assert isolated_client.post("/api/v1/games", json_body={"title": "X", "min_playtime_mins": 1}).status_code == 400
    assert isolated_client.post("/api/v1/games", json_body={"title": "X", "complexity_weight": 6.0}).status_code == 400
    assert isolated_client.post("/api/v1/games", json_body={"title": "X", "rating": 11.0}).status_code == 400

    g_id = isolated_client.get("/api/v1/games").json()["items"][0]["id"]
    assert isolated_client.patch(f"/api/v1/games/{g_id}", json_body={"rating": 0.5}).status_code == 400
    assert isolated_client.patch(f"/api/v1/games/{g_id}", json_body={"complexity_weight": 9.0}).status_code == 400
    assert isolated_client.patch(f"/api/v1/games/{g_id}", json_body={"title": "  "}).status_code == 400
    assert isolated_client.patch(f"/api/v1/games/{g_id}", json_body={"title": None}).status_code == 400
    assert isolated_client.patch(f"/api/v1/games/{g_id}", json_body={"subtitle": None}).status_code == 400
    assert isolated_client.patch(f"/api/v1/games/{g_id}", json_body={"archived": "false"}).json()["archived"] is False
    assert isolated_client.patch(f"/api/v1/games/{g_id}", json_body={"archived": "true"}).json()["archived"] is True
    assert isolated_client.patch(f"/api/v1/games/{g_id}", json_body={"archived": False}).json()["archived"] is False

    assert isolated_client.post("/api/v1/sessions", json_body={"game_id": ""}).status_code == 400
    assert (
        isolated_client.post("/api/v1/sessions", json_body={"game_id": g_id, "duration_mins": 2, "players": ["A"]}).status_code
        == 400
    )
    assert (
        isolated_client.post("/api/v1/sessions", json_body={"game_id": g_id, "players": "Ali, Omar"}).status_code
        == 201
    )
    assert (
        isolated_client.post(
            "/api/v1/sessions",
            json_body={"game_id": g_id, "players": ["Ali"], "scores": "not-a-dict"},
        ).status_code
        == 400
    )
    assert (
        isolated_client.post(
            "/api/v1/sessions",
            json_body={"game_id": g_id, "players": ["Ali"], "scores": {"Ali": True}},
        ).status_code
        == 400
    )
    assert (
        isolated_client.post(
            "/api/v1/sessions",
            json_body={"game_id": g_id, "players": ["Ali"], "scores": {"Ali": "bad"}},
        ).status_code
        == 400
    )
    assert isolated_client.post("/api/v1/sessions", json_body={"game_id": g_id, "players": []}).status_code == 400
    assert isolated_client.get("/api/v1/sessions").status_code == 200

    assert isolated_client.get("/api/v1/events?category=Tournament&search=Azul").status_code == 200
    evt_id = isolated_client.get("/api/v1/events").json()["items"][0]["id"]
    assert isolated_client.get(f"/api/v1/events/{evt_id}").status_code == 200
    assert isolated_client.get("/api/v1/events/missing-evt").status_code == 404
    assert isolated_client.post("/api/v1/events", json_body={"title": ""}).status_code == 400
    assert isolated_client.post("/api/v1/events", json_body={"title": "T", "venue": ""}).status_code == 400
    assert (
        isolated_client.post(
            "/api/v1/events",
            json_body={"title": "T", "venue": "V", "featured_games": "Catan, Azul", "max_players": 1},
        ).status_code
        == 400
    )
