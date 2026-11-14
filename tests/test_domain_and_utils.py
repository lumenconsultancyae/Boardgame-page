"""Unit tests for domain entities, value objects, and formatting/diagram utilities."""

from __future__ import annotations

import urllib.parse
import pytest

from src.config.settings import load_settings
from src.domain.entities import (
    Game,
    GameFilterSpec,
    PlaySession,
    TurnPhase,
    UaeEvent,
    validate_emirate,
    validate_game_status,
)
from src.domain.errors import DomainError, ErrorCode, NotFoundError, ValidationError
from src.utils.formatting import (
    build_collection_analytics,
    build_rule_diagram,
    build_whatsapp_event_share,
    build_whatsapp_game_share,
    build_whatsapp_list_share,
    classify_complexity_tier,
)


def _make_sample_game(
    game_id: str = "game-catan",
    title: str = "Catan",
    status: str = "owned",
    complexity_weight: float = 2.3,
    play_count: int = 8,
) -> Game:
    return Game(
        id=game_id,
        title=title,
        subtitle="Trade, build, and settle the island of Catan",
        min_players=3,
        max_players=4,
        min_playtime_mins=60,
        max_playtime_mins=90,
        complexity_weight=complexity_weight,
        status=status,
        categories=("Strategy", "Family"),
        mechanics=("Trading", "Dice Rolling", "Network Building"),
        setup_steps=(
            "Assemble the hex terrain frame and place 19 terrain hexes.",
            "Place numbered tokens A-R on terrain hexes and robber on desert.",
            "Give each player 5 settlements, 4 cities, and 15 roads.",
        ),
        turn_phases=(
            TurnPhase(
                phase="Resource Production",
                summary="Roll 2d6 so all matching settlements and cities produce resources.",
            ),
            TurnPhase(
                phase="Domestic & Maritime Trade",
                summary="Trade resource cards with other players or 4:1/3:1/2:1 at harbors.",
            ),
            TurnPhase(
                phase="Build & Development",
                summary="Spend resources to build roads, settlements, cities, or development cards.",
            ),
        ),
        scoring_rules=(
            "1 VP per Settlement and 2 VP per City.",
            "2 VP for Longest Road (5+ segments) and Largest Army (3+ knights).",
            "First player to reach 10 Victory Points on their turn wins immediately.",
        ),
        quick_tips=(
            "Prioritize high-probability numbers (6 and 8) during initial placement.",
            "Keep hand size at 7 or fewer cards when a 7 is rolled to avoid discarding half.",
        ),
        play_count=play_count,
        rating=8.4,
        archived=False,
        created_at="2026-11-13T10:00:00Z",
    )


def test_settings_load_defaults_and_overrides() -> None:
    """Verify Settings loads clean defaults and respects explicit mapping overrides."""
    default_cfg = load_settings({})
    assert default_cfg.app_port == 8088
    assert default_cfg.seed_defaults is True
    assert default_cfg.environment == "development"

    custom_cfg = load_settings(
        {
            "BOARDGAME_APP_HOST": "127.0.0.1",
            "BOARDGAME_APP_PORT": "9090",
            "BOARDGAME_DB_PATH": "/tmp/custom.sqlite3",
            "BOARDGAME_SEED_DEFAULTS": "false",
            "BOARDGAME_ENVIRONMENT": "test",
        }
    )
    assert custom_cfg.app_host == "127.0.0.1"
    assert custom_cfg.app_port == 9090
    assert custom_cfg.db_path == "/tmp/custom.sqlite3"
    assert custom_cfg.seed_defaults is False
    assert custom_cfg.environment == "test"


@pytest.mark.parametrize(
    ("weight", "expected_tier"),
    [
        (1.2, "Light"),
        (2.0, "Light"),
        (2.4, "Medium"),
        (3.2, "Medium"),
        (3.8, "Heavy"),
    ],
)
def test_classify_complexity_tier(weight: float, expected_tier: str) -> None:
    """Verify BGG complexity weight maps to human-readable complexity tiers."""
    assert classify_complexity_tier(weight) == expected_tier


def test_domain_validation_helpers_and_errors() -> None:
    """Verify status and UAE emirate validators accept valid values and reject invalid ones."""
    assert validate_game_status("owned") == "owned"
    assert validate_game_status("wishlist") == "wishlist"
    assert validate_game_status("played") == "played"

    with pytest.raises(ValidationError) as exc_info:
        validate_game_status("borrowed")
    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR

    assert validate_emirate("Dubai") == "Dubai"
    assert validate_emirate("Abu Dhabi") == "Abu Dhabi"
    assert validate_emirate("Sharjah") == "Sharjah"

    with pytest.raises(ValidationError):
        validate_emirate("Atlantis")

    not_found = NotFoundError("Game not found", details={"id": "missing"})
    assert isinstance(not_found, DomainError)
    assert not_found.code == ErrorCode.NOT_FOUND
    assert not_found.details == {"id": "missing"}


def test_game_filter_matching_combinatorial() -> None:
    """Verify GameFilterSpec filters games by status, player count, playtime, complexity, mechanic, and search."""
    game = _make_sample_game()

    assert game.matches(GameFilterSpec()) is True
    assert game.matches(GameFilterSpec(status="owned", players=4, max_playtime=90, max_complexity=2.5)) is True
    assert game.matches(GameFilterSpec(status="wishlist")) is False
    assert game.matches(GameFilterSpec(players=2)) is False
    assert game.matches(GameFilterSpec(max_playtime=45)) is False
    assert game.matches(GameFilterSpec(max_complexity=2.0)) is False
    assert game.matches(GameFilterSpec(mechanic="Trading")) is True
    assert game.matches(GameFilterSpec(mechanic="Deck Building")) is False
    assert game.matches(GameFilterSpec(search="settle")) is True
    assert game.matches(GameFilterSpec(search="mars")) is False

    from dataclasses import replace
    archived_copy = replace(_make_sample_game(), archived=True)
    assert archived_copy.matches(GameFilterSpec(include_archived=False)) is False
    assert archived_copy.matches(GameFilterSpec(include_archived=True)) is True


def test_build_rule_diagram_and_whatsapp_shares() -> None:
    """Verify rule diagram builder generates Mermaid v11 flowchart nodes, edges, and WhatsApp links."""
    game = _make_sample_game()
    diagram = build_rule_diagram(game)

    assert diagram["game_id"] == "game-catan"
    assert diagram["complexity_tier"] == "Medium"
    assert diagram["mermaid_code"].startswith("flowchart LR")
    assert '"Setup (3 steps)"' in diagram["mermaid_code"]
    assert len(diagram["diagram_nodes"]) == 5  # 1 setup + 3 phases + 1 scoring/win
    assert len(diagram["diagram_edges"]) == 4

    wa_game = build_whatsapp_game_share(game)
    assert "Catan" in wa_game["text"]
    assert "Turn Flow" in wa_game["text"]
    assert wa_game["whatsapp_url"].startswith("https://wa.me/?text=")
    decoded = urllib.parse.unquote(wa_game["whatsapp_url"].split("text=", 1)[1])
    assert "Catan" in decoded

    wa_list = build_whatsapp_list_share([game], list_title="Friday Strategy Night")
    assert "Friday Strategy Night" in wa_list["text"]
    assert "*Catan* (3-4P" in wa_list["text"]
    assert wa_list["whatsapp_url"].startswith("https://wa.me/?text=")

    empty_list = build_whatsapp_list_share([], list_title="Empty List")
    assert "No matching games" in empty_list["text"]

    event = UaeEvent(
        id="evt-dubai-1",
        title="Dubai Strategy Saturday",
        emirate="Dubai",
        venue="Unwind Specialty Boardgame Cafe, Al Barsha",
        event_date="2026-11-21",
        start_time="18:00",
        category="Strategy Night",
        featured_games=("Catan", "Dune: Imperium"),
        organizer="UAE Tabletop Guild",
        max_players=16,
        rsvp_count=9,
        description="Weekly strategy boardgame teach and play session in Dubai.",
        whatsapp_contact="+971501234567",
        created_at="2026-11-13T10:00:00Z",
    )
    wa_event = build_whatsapp_event_share(event)
    assert "Dubai Strategy Saturday" in wa_event["text"]
    assert "Unwind Specialty Boardgame Cafe" in wa_event["text"]
    assert wa_event["whatsapp_url"].startswith("https://wa.me/?text=")


def test_build_collection_analytics_and_empty_state() -> None:
    """Verify analytics builder calculates complexity buckets, mechanic percentages, and empty fallbacks."""
    empty_stats = build_collection_analytics([], [])
    assert empty_stats["total_games"] == 0
    assert empty_stats["total_plays"] == 0
    assert empty_stats["average_complexity"] == 0.0

    g1 = _make_sample_game("g1", "Azul", "owned", complexity_weight=1.8, play_count=5)
    g2 = _make_sample_game("g2", "Catan", "owned", complexity_weight=2.3, play_count=8)
    g3 = _make_sample_game("g3", "Dune: Imperium", "wishlist", complexity_weight=3.5, play_count=2)
    sessions = [
        PlaySession(
            id="s1",
            game_id="g2",
            game_title="Catan",
            played_on="2026-11-10",
            duration_mins=75,
            location="Dubai",
            players=("Omar", "Layla", "Zayd"),
            winner="Layla",
            scores={"Omar": 8, "Layla": 10, "Zayd": 7},
            notes="Close finish on Longest Road.",
            created_at="2026-11-10T20:00:00Z",
        )
    ]
    stats = build_collection_analytics([g1, g2, g3], sessions)
    assert stats["total_games"] == 3
    assert stats["owned_games"] == 2
    assert stats["wishlist_games"] == 1
    assert stats["total_plays"] == 15
    assert stats["logged_sessions_count"] == 1
    buckets = {b["bucket"]: b["count"] for b in stats["complexity_distribution"]}
    assert buckets["Light (1.0-2.0)"] == 1
    assert buckets["Medium (2.1-3.2)"] == 1
    assert buckets["Heavy (3.3-5.0)"] == 1
    assert stats["top_played_games"][0]["title"] == "Catan"
