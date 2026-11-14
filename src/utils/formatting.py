"""Stateless helpers for rule diagrams, collection analytics, and WhatsApp message formatting."""

from __future__ import annotations

from collections import Counter
from typing import Any
import urllib.parse

from src.domain.entities import Game, PlaySession, UaeEvent


def classify_complexity_tier(weight: float) -> str:
    """Map BGG-style 1.0-5.0 complexity weight to a readable tier."""
    if weight <= 2.0:
        return "Light"
    if weight <= 3.2:
        return "Medium"
    return "Heavy"


def _quote_mermaid_label(text: str) -> str:
    """Escape double quotes inside a Mermaid v11 node label."""
    safe = (text or "").replace('"', "'").strip()
    return f'"{safe}"'


def build_whatsapp_game_share(game: Game) -> dict[str, str]:
    """Generate a WhatsApp-formatted rule cheat-sheet and wa.me deep link for a game."""
    tier = classify_complexity_tier(game.complexity_weight)
    players_label = (
        f"{game.min_players}P"
        if game.min_players == game.max_players
        else f"{game.min_players}-{game.max_players}P"
    )
    playtime_label = (
        f"{game.min_playtime_mins}m"
        if game.min_playtime_mins == game.max_playtime_mins
        else f"{game.min_playtime_mins}-{game.max_playtime_mins}m"
    )
    lines: list[str] = [
        f"*{game.title}* — Quick Rule Summary",
        f"Players: {players_label} | Time: {playtime_label} | Complexity: {game.complexity_weight:.1f}/5 ({tier})",
        f"Mechanics: {', '.join(game.mechanics)}",
        "",
        "*Setup Checklist:*",
    ]
    for idx, step in enumerate(game.setup_steps, start=1):
        lines.append(f"{idx}. {step}")

    lines.append("")
    lines.append("*Turn Flow:*")
    for idx, tp in enumerate(game.turn_phases, start=1):
        lines.append(f"• *Phase {idx} ({tp.phase})*: {tp.summary}")

    lines.append("")
    lines.append("*Scoring & Win Condition:*")
    for rule in game.scoring_rules:
        lines.append(f"• {rule}")

    if game.quick_tips:
        lines.append("")
        lines.append(f"*Pro Tip:* {game.quick_tips[0]}")

    text = "\n".join(lines)
    encoded = urllib.parse.quote(text, safe="")
    return {
        "game_id": game.id,
        "title": game.title,
        "text": text,
        "whatsapp_url": f"https://wa.me/?text={encoded}",
    }


def build_whatsapp_list_share(games: list[Game], list_title: str = "My Boardgame List") -> dict[str, str]:
    """Generate a WhatsApp-formatted curated game list message and wa.me deep link."""
    header = (list_title or "My Boardgame List").strip()
    lines: list[str] = [f"*{header}* ({len(games)} games)"]
    if not games:
        lines.append("No matching games found for the selected filters.")
    else:
        lines.append("")
        for idx, g in enumerate(games, start=1):
            tier = classify_complexity_tier(g.complexity_weight)
            p_lbl = f"{g.min_players}P" if g.min_players == g.max_players else f"{g.min_players}-{g.max_players}P"
            t_lbl = (
                f"{g.max_playtime_mins}m"
                if g.min_playtime_mins == g.max_playtime_mins
                else f"{g.min_playtime_mins}-{g.max_playtime_mins}m"
            )
            lines.append(
                f"{idx}. *{g.title}* ({p_lbl}, {t_lbl}, {tier} {g.complexity_weight:.1f}/5) — {', '.join(g.mechanics[:2])}"
            )
        lines.append("")
        lines.append("Reply with your top pick for game night!")

    text = "\n".join(lines)
    encoded = urllib.parse.quote(text, safe="")
    return {
        "title": header,
        "count": str(len(games)),
        "text": text,
        "whatsapp_url": f"https://wa.me/?text={encoded}",
    }


def build_whatsapp_event_share(event: UaeEvent) -> dict[str, str]:
    """Generate a WhatsApp-formatted UAE boardgame event invite and wa.me deep link."""
    spots = max(0, event.max_players - event.rsvp_count)
    lines: list[str] = [
        f"*UAE Boardgame Meetup: {event.title}*",
        f"Emirate: {event.emirate} | Venue: {event.venue}",
        f"Date & Time: {event.event_date} at {event.start_time} GST ({event.category})",
        f"Featured Games: {', '.join(event.featured_games)}",
        f"Seats: {event.rsvp_count}/{event.max_players} confirmed ({spots} spots open)",
        "",
        event.description,
    ]
    text = "\n".join(lines)
    encoded = urllib.parse.quote(text, safe="")
    return {
        "event_id": event.id,
        "title": event.title,
        "text": text,
        "whatsapp_url": f"https://wa.me/?text={encoded}",
    }


def build_rule_diagram(game: Game) -> dict[str, Any]:
    """Build structured interactive flowchart nodes, edges, and Mermaid v11 diagram for a game."""
    tier = classify_complexity_tier(game.complexity_weight)
    players_label = (
        f"{game.min_players} Players"
        if game.min_players == game.max_players
        else f"{game.min_players}–{game.max_players} Players"
    )
    playtime_label = (
        f"{game.min_playtime_mins} mins"
        if game.min_playtime_mins == game.max_playtime_mins
        else f"{game.min_playtime_mins}–{game.max_playtime_mins} mins"
    )

    nodes: list[dict[str, Any]] = [
        {
            "id": "node_setup",
            "step_number": 0,
            "kind": "setup",
            "label": f"Setup ({len(game.setup_steps)} steps)",
            "subtitle": "Table & Player Prep",
            "detail": " • ".join(game.setup_steps),
        }
    ]
    edges: list[dict[str, str]] = []
    mermaid_lines: list[str] = [
        "flowchart LR",
        f"    node_setup[{_quote_mermaid_label(f'Setup ({len(game.setup_steps)} steps)')}]",
    ]

    prev_id = "node_setup"
    for idx, tp in enumerate(game.turn_phases, start=1):
        node_id = f"node_phase_{idx}"
        nodes.append(
            {
                "id": node_id,
                "step_number": idx,
                "kind": "phase",
                "label": f"Phase {idx}: {tp.phase}",
                "subtitle": f"Turn Step {idx}",
                "detail": tp.summary,
            }
        )
        edge_label = "Start Game" if idx == 1 else "Next Phase"
        edges.append({"from_id": prev_id, "to_id": node_id, "label": edge_label})
        mermaid_lines.append(f"    {node_id}[{_quote_mermaid_label(f'Phase {idx}: {tp.phase}')}]")
        mermaid_lines.append(f"    {prev_id} -->|{_quote_mermaid_label(edge_label)}| {node_id}")
        prev_id = node_id

    win_id = "node_scoring"
    win_summary = game.scoring_rules[-1] if game.scoring_rules else "Highest score wins."
    nodes.append(
        {
            "id": win_id,
            "step_number": len(game.turn_phases) + 1,
            "kind": "scoring",
            "label": "Scoring & Victory",
            "subtitle": "Endgame Trigger",
            "detail": " • ".join(game.scoring_rules) if game.scoring_rules else win_summary,
        }
    )
    edges.append({"from_id": prev_id, "to_id": win_id, "label": "Endgame Check"})
    mermaid_lines.append(f"    {win_id}[{_quote_mermaid_label('Scoring & Victory')}]")
    mermaid_lines.append(f"    {prev_id} -->|{_quote_mermaid_label('Endgame Check')}| {win_id}")

    return {
        "game_id": game.id,
        "title": game.title,
        "subtitle": game.subtitle,
        "complexity_weight": round(game.complexity_weight, 2),
        "complexity_tier": tier,
        "player_range_label": players_label,
        "playtime_label": playtime_label,
        "setup_steps": list(game.setup_steps),
        "turn_phases": [tp.to_dict() for tp in game.turn_phases],
        "scoring_rules": list(game.scoring_rules),
        "quick_tips": list(game.quick_tips),
        "mermaid_code": "\n".join(mermaid_lines),
        "diagram_nodes": nodes,
        "diagram_edges": edges,
        "whatsapp_share": build_whatsapp_game_share(game),
    }


def build_collection_analytics(games: list[Game], sessions: list[PlaySession]) -> dict[str, Any]:
    """Compute collection analytics distributions, mechanic frequency, and top-played rankings."""
    active_games = [g for g in games if not g.archived]
    total = len(active_games)
    if total == 0:
        return {
            "total_games": 0,
            "owned_games": 0,
            "wishlist_games": 0,
            "played_status_games": 0,
            "total_plays": 0,
            "logged_sessions_count": len(sessions),
            "average_complexity": 0.0,
            "average_rating": 0.0,
            "complexity_distribution": [
                {"bucket": "Light (1.0-2.0)", "count": 0, "percentage": 0.0},
                {"bucket": "Medium (2.1-3.2)", "count": 0, "percentage": 0.0},
                {"bucket": "Heavy (3.3-5.0)", "count": 0, "percentage": 0.0},
            ],
            "mechanics_breakdown": [],
            "category_breakdown": [],
            "player_count_coverage": [],
            "top_played_games": [],
        }

    owned = sum(1 for g in active_games if g.status == "owned")
    wishlist = sum(1 for g in active_games if g.status == "wishlist")
    played_status = sum(1 for g in active_games if g.status == "played")
    total_plays = sum(g.play_count for g in active_games)
    avg_complexity = round(sum(g.complexity_weight for g in active_games) / total, 2)
    avg_rating = round(sum(g.rating for g in active_games) / total, 1)

    light_cnt = sum(1 for g in active_games if g.complexity_weight <= 2.0)
    med_cnt = sum(1 for g in active_games if 2.0 < g.complexity_weight <= 3.2)
    heavy_cnt = sum(1 for g in active_games if g.complexity_weight > 3.2)
    complexity_distribution = [
        {"bucket": "Light (1.0-2.0)", "count": light_cnt, "percentage": round(light_cnt * 100.0 / total, 1)},
        {"bucket": "Medium (2.1-3.2)", "count": med_cnt, "percentage": round(med_cnt * 100.0 / total, 1)},
        {"bucket": "Heavy (3.3-5.0)", "count": heavy_cnt, "percentage": round(heavy_cnt * 100.0 / total, 1)},
    ]

    mech_counter: Counter[str] = Counter()
    cat_counter: Counter[str] = Counter()
    for g in active_games:
        mech_counter.update(g.mechanics)
        cat_counter.update(g.categories)

    mechanics_breakdown = [
        {"mechanic": name, "count": cnt, "percentage": round(cnt * 100.0 / total, 1)}
        for name, cnt in mech_counter.most_common(8)
    ]
    category_breakdown = [
        {"category": name, "count": cnt, "percentage": round(cnt * 100.0 / total, 1)}
        for name, cnt in cat_counter.most_common(6)
    ]

    player_counts = [
        ("1P Solo", sum(1 for g in active_games if g.min_players <= 1 <= g.max_players)),
        ("2P", sum(1 for g in active_games if g.min_players <= 2 <= g.max_players)),
        ("3P", sum(1 for g in active_games if g.min_players <= 3 <= g.max_players)),
        ("4P", sum(1 for g in active_games if g.min_players <= 4 <= g.max_players)),
        ("5P+", sum(1 for g in active_games if g.max_players >= 5)),
    ]
    player_count_coverage = [
        {"players": label, "count": cnt, "percentage": round(cnt * 100.0 / total, 1)}
        for label, cnt in player_counts
    ]

    top_played = sorted(active_games, key=lambda g: (-g.play_count, -g.rating, g.title))[:6]
    top_played_games = [
        {
            "game_id": g.id,
            "title": g.title,
            "play_count": g.play_count,
            "rating": round(g.rating, 1),
            "complexity_weight": round(g.complexity_weight, 2),
        }
        for g in top_played
    ]

    return {
        "total_games": total,
        "owned_games": owned,
        "wishlist_games": wishlist,
        "played_status_games": played_status,
        "total_plays": total_plays,
        "logged_sessions_count": len(sessions),
        "average_complexity": avg_complexity,
        "average_rating": avg_rating,
        "complexity_distribution": complexity_distribution,
        "mechanics_breakdown": mechanics_breakdown,
        "category_breakdown": category_breakdown,
        "player_count_coverage": player_count_coverage,
        "top_played_games": top_played_games,
    }
