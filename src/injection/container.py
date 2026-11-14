"""Composition root wiring persistence ports and application services."""

from __future__ import annotations

from dataclasses import dataclass

from src.application.boardgame_service import BoardgameService
from src.config.settings import Settings, load_settings
from src.domain.ports import BoardgameRepositoryPort
from src.infrastructure.repositories import SqliteBoardgameRepository


@dataclass(frozen=True)
class ServiceContainer:
    """Wired application dependencies."""

    settings: Settings
    repository: BoardgameRepositoryPort
    boardgame_service: BoardgameService


def build_container(settings: Settings | None = None) -> ServiceContainer:
    """Wire domain ports to concrete infrastructure adapters and return ServiceContainer."""
    cfg = settings or load_settings()
    repo = SqliteBoardgameRepository(db_path=cfg.db_path, seed_defaults=cfg.seed_defaults)
    service = BoardgameService(repository=repo)
    return ServiceContainer(settings=cfg, repository=repo, boardgame_service=service)
