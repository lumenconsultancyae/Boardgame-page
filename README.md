# Boardgame Page (`Boardgame-page`)

A full-stack web application to track board games and play sessions, share curated game collections, generate visual rule summaries and interactive setup/turn-order diagrams for friends, format one-click WhatsApp messages (`wa.me`), and track boardgame community events across the UAE.

## Core Capabilities

1. **Game Collection & Play Session Tracker**
   - Catalog owned, wishlist, and played board games with player count bounds, playtime, BGG-style complexity weight (`1.0–5.0`), categories, mechanics, and personal rating.
   - Log play sessions with date, duration, location/café, player roster, winner, scores, and session notes (automatically incrementing play counts).

2. **Visual Rule Summaries & Interactive Turn-Order Diagrams**
   - Generate readable rule cheat-sheets, table setup checklists, turn-by-turn phase breakdowns, scoring triggers, and interactive SVG + Mermaid v11 flowcharts so friends can learn or refresh rules in minutes before game night.

3. **Shareable Game Lists & Collection Analytics Graphs**
   - Filter and curate lists of games by collection status, player count, maximum complexity weight, or mechanic/title search.
   - Interactive collection graphs visualizing complexity weight distribution (Light / Medium / Heavy), player-count coverage (`1P` to `5P+`), core game mechanics frequency, and most-played game leaderboards.

4. **WhatsApp Sharing Integration**
   - One-click generation of WhatsApp-formatted summaries and `https://wa.me/?text=...` deep links for:
     - Game rule summaries & turn-flow cheat-sheets
     - Filtered game night candidate lists
     - UAE boardgame meetup and tournament invites

5. **UAE Boardgame Events Tracker**
   - Discover, host, RSVP, and share boardgame meetups, café strategy nights, and tournaments across all 7 UAE Emirates (Dubai, Abu Dhabi, Sharjah, Ajman, Ras Al Khaimah, Fujairah, and Umm Al Quwain).

## Layered Service Architecture

```text
src/
├── config/           # Leaf Settings dataclass (BOARDGAME_APP_HOST, BOARDGAME_APP_PORT, BOARDGAME_DB_PATH)
├── domain/           # Pure entities (Game, PlaySession, UaeEvent, TurnPhase), errors, and BoardgameRepositoryPort
├── utils/            # Stateless Mermaid v11 / SVG flowchart builders, analytics calculators, and WhatsApp formatters
├── infrastructure/   # SqliteBoardgameRepository and idempotent schema migrations + default catalog seed
├── application/      # BoardgameService use-case orchestration
├── injection/        # ServiceContainer composition root wiring ports to concrete adapters
└── api/              # HTTP JSON API router, DTO envelopes, static web UI, and in-process AppTestClient
```

## Quick Start & Testing

```bash
# Run unit & API integration tests with branch coverage
pytest tests/ --cov=src --cov-branch

# Start the web application server (defaults to http://0.0.0.0:8088)
python3 -m src.api.app
```

## Companion Repository

- **Documentation, PRD/SDD, Docker Compose & BDD E2E Suite**: [`lumenconsultancyae/boardgame_page_docs`](https://github.com/lumenconsultancyae/boardgame_page_docs)
