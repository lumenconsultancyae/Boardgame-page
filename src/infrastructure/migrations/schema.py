"""Idempotent SQLite schema migration and initial seed catalog."""

from __future__ import annotations

import json
import sqlite3

from src.domain.entities import Game, PlaySession, TurnPhase, UaeEvent

SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS games (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        subtitle TEXT NOT NULL,
        min_players INTEGER NOT NULL,
        max_players INTEGER NOT NULL,
        min_playtime_mins INTEGER NOT NULL,
        max_playtime_mins INTEGER NOT NULL,
        complexity_weight REAL NOT NULL,
        status TEXT NOT NULL,
        categories_json TEXT NOT NULL,
        mechanics_json TEXT NOT NULL,
        setup_steps_json TEXT NOT NULL,
        turn_phases_json TEXT NOT NULL,
        scoring_rules_json TEXT NOT NULL,
        quick_tips_json TEXT NOT NULL,
        play_count INTEGER NOT NULL DEFAULT 0,
        rating REAL NOT NULL DEFAULT 8.0,
        archived INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS play_sessions (
        id TEXT PRIMARY KEY,
        game_id TEXT NOT NULL,
        game_title TEXT NOT NULL,
        played_on TEXT NOT NULL,
        duration_mins INTEGER NOT NULL,
        location TEXT NOT NULL,
        players_json TEXT NOT NULL,
        winner TEXT NOT NULL,
        scores_json TEXT NOT NULL,
        notes TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS uae_events (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        emirate TEXT NOT NULL,
        venue TEXT NOT NULL,
        event_date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        category TEXT NOT NULL,
        featured_games_json TEXT NOT NULL,
        organizer TEXT NOT NULL,
        max_players INTEGER NOT NULL,
        rsvp_count INTEGER NOT NULL,
        description TEXT NOT NULL,
        whatsapp_contact TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
)


def default_seed_games() -> tuple[Game, ...]:
    """Return the default curated collection of board games with complete rule diagrams."""
    return (
        Game(
            id="game-catan",
            title="Catan",
            subtitle="Trade resources, build road networks, and settle the island of Catan",
            min_players=3,
            max_players=4,
            min_playtime_mins=60,
            max_playtime_mins=90,
            complexity_weight=2.3,
            status="owned",
            categories=("Strategy", "Negotiation", "Family"),
            mechanics=("Trading", "Dice Rolling", "Network Building", "Modular Board"),
            setup_steps=(
                "Assemble the sea frame and arrange the 19 terrain hexes inside.",
                "Place circular number tokens alphabetically on terrain hexes and the Robber on the Desert.",
                "Each player places 2 settlements and 2 roads in snake turn order and takes starting resources from their 2nd settlement.",
            ),
            turn_phases=(
                TurnPhase(
                    phase="Resource Production",
                    summary="Roll 2 dice; every player with a settlement (1 card) or city (2 cards) adjacent to that number collects resources.",
                ),
                TurnPhase(
                    phase="Domestic & Maritime Trade",
                    summary="Negotiate card trades with other players or trade 4:1 with the supply (3:1 or 2:1 at harbors).",
                ),
                TurnPhase(
                    phase="Build & Buy Cards",
                    summary="Spend resources to build Roads, Settlements, Cities, or draw Development Cards.",
                ),
            ),
            scoring_rules=(
                "1 Victory Point per Settlement and 2 Victory Points per City.",
                "2 Victory Points each for Longest Continuous Road (5+ roads) and Largest Army (3+ played Knights).",
                "First player to reach 10+ Victory Points on their active turn claims immediate victory.",
            ),
            quick_tips=(
                "High-dot numbers (6 and 8) roll most frequently; diversify across Brick/Wood or Ore/Wheat.",
                "Keep 7 or fewer resource cards in hand at the end of your turn so rolling a 7 does not force a half-hand discard.",
            ),
            play_count=12,
            rating=8.5,
            archived=False,
            created_at="2026-11-01T10:00:00Z",
        ),
        Game(
            id="game-wingspan",
            title="Wingspan",
            subtitle="Engine-building bird sanctuary strategy across forest, grassland, and wetland habitats",
            min_players=1,
            max_players=5,
            min_playtime_mins=40,
            max_playtime_mins=70,
            complexity_weight=2.4,
            status="owned",
            categories=("Engine Building", "Nature", "Card Game"),
            mechanics=("Engine Building", "Hand Management", "Open Drafting", "Dice Rolling"),
            setup_steps=(
                "Shuffle bird deck, reveal 3 face-up birds in the tray, and roll 5 food dice into the birdfeeder.",
                "Place 4 random round-end goal tiles on the goal board.",
                "Deal each player 5 bird cards, 5 food tokens (keep 5 total between birds + food), and 2 bonus cards (keep 1).",
            ),
            turn_phases=(
                TurnPhase(
                    phase="Choose 1 of 4 Habitat Actions",
                    summary="Place an action cube on the leftmost empty slot of Play a Bird, Gain Food, Lay Eggs, or Draw Bird Cards.",
                ),
                TurnPhase(
                    phase="Activate Brown Powers Right-to-Left",
                    summary="Move your action cube right-to-left along the chosen habitat row, triggering every 'When Activated' brown bird power.",
                ),
                TurnPhase(
                    phase="Round Cleanup & Goal Scoring",
                    summary="Once all action cubes are placed, score the active Round Goal, refresh face-up bird tray, and start next round (8/7/6/5 turns).",
                ),
            ),
            scoring_rules=(
                "Sum printed Feather VP on all played birds across your 3 habitats.",
                "Add points from completed Bonus Cards and End-of-Round Goal positions.",
                "Add 1 VP each for Every Egg on birds, Cached Food tokens, and Tucked Bird cards.",
            ),
            quick_tips=(
                "Build your Forest (food) and Wetland (card draw) rows early so Rounds 3-4 can focus on high-point birds and egg laying.",
                "Pink 'Once Between Turns' powers trigger on opponents' actions—remind the table when yours is active.",
            ),
            play_count=9,
            rating=9.1,
            archived=False,
            created_at="2026-11-02T10:00:00Z",
        ),
        Game(
            id="game-azul",
            title="Azul",
            subtitle="Abstract tile-drafting mosaic artistry for the Royal Palace of Evora",
            min_players=2,
            max_players=4,
            min_playtime_mins=30,
            max_playtime_mins=45,
            complexity_weight=1.8,
            status="owned",
            categories=("Abstract Strategy", "Puzzle", "Family"),
            mechanics=("Tile Placement", "Open Drafting", "Pattern Building", "Set Collection"),
            setup_steps=(
                "Give each player a player board with score marker at 0 and place 5/7/9 Factory displays in the center (for 2/3/4 players).",
                "Fill the cloth bag with 100 resin tiles (20 of each color) and draw 4 tiles onto each Factory disc.",
                "Place the Starting Player token in the center of the table.",
            ),
            turn_phases=(
                TurnPhase(
                    phase="Factory Offer Drafting",
                    summary="Pick all tiles of one color from either a Factory disc (pushing leftovers to the center) or the center pool, and place them on one pattern row.",
                ),
                TurnPhase(
                    phase="Wall-Tiling & Immediate Scoring",
                    summary="Move 1 tile from each completed pattern row onto the matching color space of your 5x5 Wall and score connected orthogonal chains immediately.",
                ),
                TurnPhase(
                    phase="Floor Line Penalty & Refill",
                    summary="Subtract Floor Line penalty points, return excess tiles to the box lid, and refill Factory discs if no player has completed a horizontal Wall row.",
                ),
            ),
            scoring_rules=(
                "Immediate points during Wall-tiling: 1 VP for an isolated tile, or count all horizontally + vertically linked tiles.",
                "Endgame bonuses: +2 VP per complete horizontal row, +7 VP per complete vertical column, +10 VP per complete 5-of-a-color set.",
                "Game ends at the end of the round in which any player completes at least 1 horizontal row of 5 tiles.",
            ),
            quick_tips=(
                "Count how many tiles your opponent needs for their 4- and 5-space rows before leaving a large pile in the center.",
                "Prioritize completing vertical columns (+7 VP) and central Wall adjacency for compounding chain scores.",
            ),
            play_count=15,
            rating=8.7,
            archived=False,
            created_at="2026-11-03T10:00:00Z",
        ),
        Game(
            id="game-dune-imperium",
            title="Dune: Imperium",
            subtitle="Deck-building and worker-placement struggle for Spice and control of Arrakis",
            min_players=1,
            max_players=4,
            min_playtime_mins=60,
            max_playtime_mins=120,
            complexity_weight=3.1,
            status="owned",
            categories=("Sci-Fi", "Strategy", "Political"),
            mechanics=("Deck Building", "Worker Placement", "Area Majority", "Hand Management"),
            setup_steps=(
                "Place the Arrakis board, reveal 5 Imperium Row cards, and stack Conflict I/II/III decks.",
                "Each player selects a Great House Leader, takes their identical 10-card starter deck, 2 Agents, 3 troops in garrison, and 1 Water.",
                "Draw a 5-card opening hand at the start of Round 1.",
            ),
            turn_phases=(
                TurnPhase(
                    phase="Round Start",
                    summary="Flip the top Conflict Card for the round and every player draws 5 cards from their personal deck.",
                ),
                TurnPhase(
                    phase="AgentTurns (Alternate 1 Card + 1 Agent)",
                    summary="Play a card for its Agent icon to send an Agent to an open board space, paying cost and resolving both space and card Agent box.",
                ),
                TurnPhase(
                    phase="Reveal Turn & Persuasion Buying",
                    summary="When passing, reveal remaining hand cards to gain Persuasion (buy Imperium cards) and Swords (combat strength).",
                ),
                TurnPhase(
                    phase="Combat Resolution & Makers Phase",
                    summary="Resolve the Conflict by comparing total Combat strength (2 VP per troop + 1 per Sword + Intrigue), then add bonus Spice to unvisited Maker spaces.",
                ),
            ),
            scoring_rules=(
                "Gain 1 VP at level 2 Influence on each of the 4 Faction tracks, plus +1 movable VP token when holding the Faction Alliance (level 4).",
                "Win Victory Points, Spice, and Intrigue rewards from each round's Conflict card.",
                "Endgame triggers at round end if any player reaches 10+ VP (or after Round 10); highest VP wins (Spice breaks ties).",
            ),
            quick_tips=(
                "Unlocking your 3rd Agent (Swordmaster for 8 Solari) or High Council (+2 Persuasion per round) early supercharges your tempo.",
                "Never commit all troops to a minor Conflict if a 2-VP Conflict III is coming next round.",
            ),
            play_count=7,
            rating=9.4,
            archived=False,
            created_at="2026-11-04T10:00:00Z",
        ),
        Game(
            id="game-ticket-to-ride",
            title="Ticket to Ride: Europe",
            subtitle="Cross-continent railway route claiming with tunnels, ferries, and train stations",
            min_players=2,
            max_players=5,
            min_playtime_mins=45,
            max_playtime_mins=75,
            complexity_weight=1.9,
            status="played",
            categories=("Family", "Trains", "Route Building"),
            mechanics=("Network Building", "Set Collection", "Hand Management", "Push Your Luck"),
            setup_steps=(
                "Deal each player 45 colored train cars, 3 Train Stations, 4 Train Car cards, and 1 Long Route + 3 normal Destination Tickets (keep at least 2).",
                "Reveal 5 face-up Train Car cards beside the draw deck.",
            ),
            turn_phases=(
                TurnPhase(
                    phase="Perform Exactly 1 of 4 Actions",
                    summary="Either Draw 2 Train Car cards (1 if taking a face-up Locomotive), Claim a Route, Draw 3 Destination Tickets (keep 1+), or Build a Train Station.",
                ),
                TurnPhase(
                    phase="Route & Tunnel Resolution",
                    summary="When claiming a Tunnel route, flip 3 top deck cards; pay 1 extra matching card per matching color/Locomotive flipped.",
                ),
                TurnPhase(
                    phase="Final Turn Trigger",
                    summary="When any player's plastic train supply drops to 2 or fewer cars at turn end, every player takes 1 final turn.",
                ),
            ),
            scoring_rules=(
                "Score route length points immediately (1/2/4/7/10/15/21 VP for length 1/2/3/4/6/8).",
                "Add completed Destination Ticket values and subtract incomplete Ticket values at game end.",
                "+4 VP per unused Train Station and +10 VP for the European Express longest continuous path.",
            ),
            quick_tips=(
                "Save your 3 Train Stations for single-track bottlenecks around Zürich, Wien, or Athina.",
            ),
            play_count=6,
            rating=8.1,
            archived=False,
            created_at="2026-11-05T10:00:00Z",
        ),
        Game(
            id="game-terraforming-mars",
            title="Terraforming Mars",
            subtitle="Corporate engine-building to raise temperature, oxygen, and oceans across the Red Planet",
            min_players=1,
            max_players=5,
            min_playtime_mins=90,
            max_playtime_mins=120,
            complexity_weight=3.3,
            status="wishlist",
            categories=("Sci-Fi", "Economic", "Territory Building"),
            mechanics=("Engine Building", "Tile Placement", "Card Drafting", "Hand Management"),
            setup_steps=(
                "Set Temperature at -30C, Oxygen at 0%, and 9 Ocean tiles in the supply.",
                "Deal each player 2 Corporations and 10 Project cards; each player chooses 1 Corporation and pays 3 M€ per kept Project card.",
            ),
            turn_phases=(
                TurnPhase(
                    phase="Player Order & Research Phase",
                    summary="Pass First Player marker clockwise; draft or draw 4 Project cards and buy any number into hand for 3 M€ each.",
                ),
                TurnPhase(
                    phase="Action Phase (1 or 2 Actions per Turn)",
                    summary="Play Project cards, use Standard Projects, claim a Milestone (max 3 total), fund an Award (max 3 total), use Blue card actions, or convert 8 Plants/Heat.",
                ),
                TurnPhase(
                    phase="Production Phase",
                    summary="Convert all remaining Energy into Heat, then collect M€ (Terraform Rating + M€ production) and all 5 resource productions.",
                ),
            ),
            scoring_rules=(
                "Base score equals your final Terraform Rating (starts at 20).",
                "Add 5 VP per claimed Milestone, 5/2 VP for 1st/2nd in funded Awards, plus Greenery (1 VP) and City (1 VP per adjacent Greenery) board tiles.",
                "Add printed VP on played Project cards once all 3 global parameters (14% Oxygen, +8C Temp, 9 Oceans) reach maximum.",
            ),
            quick_tips=(
                "Keep track of Milestone thresholds—claiming Gardener or Mayor for 8 M€ yields 5 VP (the most efficient M€-to-VP ratio in the game).",
            ),
            play_count=3,
            rating=9.0,
            archived=False,
            created_at="2026-11-06T10:00:00Z",
        ),
    )


def default_seed_sessions() -> tuple[PlaySession, ...]:
    """Return initial logged boardgame play sessions."""
    return (
        PlaySession(
            id="session-dubai-dune-01",
            game_id="game-dune-imperium",
            game_title="Dune: Imperium",
            played_on="2026-11-11",
            duration_mins=105,
            location="Unwind Specialty Boardgame Cafe, Al Barsha, Dubai",
            players=("Khalid", "Mariam", "Rami", "Zayd"),
            winner="Mariam",
            scores={"Mariam": 11, "Khalid": 9, "Rami": 8, "Zayd": 8},
            notes="Mariam secured Fremen + Bene Gesserit alliances and won the final Conflict III.",
            created_at="2026-11-11T21:30:00Z",
        ),
        PlaySession(
            id="session-abudhabi-wingspan-02",
            game_id="game-wingspan",
            game_title="Wingspan",
            played_on="2026-11-09",
            duration_mins=60,
            location="Yas Creative Gaming Lounge, Abu Dhabi",
            players=("Khalid", "Noura", "Omar"),
            winner="Khalid",
            scores={"Khalid": 94, "Noura": 88, "Omar": 81},
            notes="Wetland tucking engine scored 26 tucked bird cards by Round 4.",
            created_at="2026-11-09T19:45:00Z",
        ),
        PlaySession(
            id="session-dubai-azul-03",
            game_id="game-azul",
            game_title="Azul",
            played_on="2026-11-07",
            duration_mins=35,
            location="The Six Board Game Cafe, Downtown Dubai",
            players=("Khalid", "Layla", "Sami"),
            winner="Layla",
            scores={"Layla": 78, "Khalid": 71, "Sami": 64},
            notes="Completed two full vertical columns and 5-of-a-kind blue tiles.",
            created_at="2026-11-07T18:15:00Z",
        ),
        PlaySession(
            id="session-sharjah-catan-04",
            game_id="game-catan",
            game_title="Catan",
            played_on="2026-11-03",
            duration_mins=75,
            location="House of Wisdom Community Lounge, Sharjah",
            players=("Khalid", "Omar", "Tariq", "Zayd"),
            winner="Tariq",
            scores={"Tariq": 10, "Khalid": 9, "Omar": 8, "Zayd": 7},
            notes="Shared the Catan visual rule flowchart on WhatsApp before the game—setup took under 5 minutes!",
            created_at="2026-11-03T20:00:00Z",
        ),
    )


def default_seed_events() -> tuple[UaeEvent, ...]:
    """Return initial UAE boardgame community meetups and tournaments."""
    return (
        UaeEvent(
            id="event-dubai-strategy-night",
            title="Dubai Strategy & Rule-Teach Saturday",
            emirate="Dubai",
            venue="Unwind Specialty Boardgame Cafe, Al Barsha",
            event_date="2026-11-21",
            start_time="18:00",
            category="Rule Teach & Play",
            featured_games=("Dune: Imperium", "Wingspan", "Catan"),
            organizer="Dubai Boardgame Circle",
            max_players=20,
            rsvp_count=14,
            description="Weekly guided game night with printed & WhatsApp interactive rule diagrams for newcomers and veterans.",
            whatsapp_contact="+971501112233",
            created_at="2026-11-10T09:00:00Z",
        ),
        UaeEvent(
            id="event-abudhabi-euro-meetup",
            title="Abu Dhabi Eurogame & Engine Builders Meetup",
            emirate="Abu Dhabi",
            venue="Yas Creative Hub Community Hall, Yas Island",
            event_date="2026-11-24",
            start_time="19:00",
            category="Meetup",
            featured_games=("Terraforming Mars", "Wingspan", "Azul"),
            organizer="Capital Tabletop Abu Dhabi",
            max_players=16,
            rsvp_count=11,
            description="Mid-week strategy boardgame sessions on Yas Island. Beginners welcome—rule summaries shared before kickoff.",
            whatsapp_contact="+971502223344",
            created_at="2026-11-10T10:00:00Z",
        ),
        UaeEvent(
            id="event-sharjah-family-classic",
            title="Sharjah Boardgame Social & Azul Championship",
            emirate="Sharjah",
            venue="House of Wisdom Community Lounge, Al Juraina",
            event_date="2026-11-27",
            start_time="17:00",
            category="Tournament",
            featured_games=("Azul", "Ticket to Ride: Europe", "Catan"),
            organizer="Sharjah Tabletop Collective",
            max_players=24,
            rsvp_count=18,
            description="Swiss-round Azul tournament alongside open family and gateway strategy tables.",
            whatsapp_contact="+971503334455",
            created_at="2026-11-10T11:00:00Z",
        ),
        UaeEvent(
            id="event-dubai-downtown-social",
            title="Downtown Dubai Friday Night Boardgames",
            emirate="Dubai",
            venue="The Six Board Game Cafe, Burj Vista",
            event_date="2026-11-29",
            start_time="19:30",
            category="Strategy Night",
            featured_games=("Catan", "Dune: Imperium", "Ticket to Ride: Europe"),
            organizer="UAE Tabletop Guild",
            max_players=18,
            rsvp_count=12,
            description="Casual and medium-weight boardgame tables with view of Downtown Dubai.",
            whatsapp_contact="+971504445566",
            created_at="2026-11-10T12:00:00Z",
        ),
    )


def apply_migrations_and_seed(conn: sqlite3.Connection, seed_defaults: bool = True) -> None:
    """Create database tables if absent and populate default seed records when empty."""
    cur = conn.cursor()
    for stmt in SCHEMA_STATEMENTS:
        cur.execute(stmt)

    if seed_defaults:
        game_cnt = cur.execute("SELECT COUNT(*) FROM games").fetchone()[0]
        if game_cnt == 0:
            for g in default_seed_games():
                cur.execute(
                    """
                    INSERT INTO games (
                        id, title, subtitle, min_players, max_players,
                        min_playtime_mins, max_playtime_mins, complexity_weight, status,
                        categories_json, mechanics_json, setup_steps_json, turn_phases_json,
                        scoring_rules_json, quick_tips_json, play_count, rating, archived, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        g.id,
                        g.title,
                        g.subtitle,
                        g.min_players,
                        g.max_players,
                        g.min_playtime_mins,
                        g.max_playtime_mins,
                        g.complexity_weight,
                        g.status,
                        json.dumps(list(g.categories)),
                        json.dumps(list(g.mechanics)),
                        json.dumps(list(g.setup_steps)),
                        json.dumps([tp.to_dict() for tp in g.turn_phases]),
                        json.dumps(list(g.scoring_rules)),
                        json.dumps(list(g.quick_tips)),
                        g.play_count,
                        g.rating,
                        1 if g.archived else 0,
                        g.created_at,
                    ),
                )
        session_cnt = cur.execute("SELECT COUNT(*) FROM play_sessions").fetchone()[0]
        if session_cnt == 0:
            for s in default_seed_sessions():
                cur.execute(
                    """
                    INSERT INTO play_sessions (
                        id, game_id, game_title, played_on, duration_mins,
                        location, players_json, winner, scores_json, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        s.id,
                        s.game_id,
                        s.game_title,
                        s.played_on,
                        s.duration_mins,
                        s.location,
                        json.dumps(list(s.players)),
                        s.winner,
                        json.dumps(s.scores),
                        s.notes,
                        s.created_at,
                    ),
                )
        event_cnt = cur.execute("SELECT COUNT(*) FROM uae_events").fetchone()[0]
        if event_cnt == 0:
            for e in default_seed_events():
                cur.execute(
                    """
                    INSERT INTO uae_events (
                        id, title, emirate, venue, event_date, start_time, category,
                        featured_games_json, organizer, max_players, rsvp_count,
                        description, whatsapp_contact, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        e.id,
                        e.title,
                        e.emirate,
                        e.venue,
                        e.event_date,
                        e.start_time,
                        e.category,
                        json.dumps(list(e.featured_games)),
                        e.organizer,
                        e.max_players,
                        e.rsvp_count,
                        e.description,
                        e.whatsapp_contact,
                        e.created_at,
                    ),
                )
    conn.commit()
