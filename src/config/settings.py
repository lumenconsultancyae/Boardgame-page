"""Typed application configuration loaded from environment variables."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping

VERSION_FILE = Path(__file__).resolve().parents[2] / "VERSION"


def read_app_version() -> str:
    """Read the canonical application version from the repository VERSION file."""
    if VERSION_FILE.is_file():
        raw = VERSION_FILE.read_text(encoding="utf-8").strip()
        if raw:
            return raw
    return "1.0.0"


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings for the Boardgame Page service."""

    app_host: str = "0.0.0.0"
    app_port: int = 8088
    db_path: str = "data/boardgames.sqlite3"
    seed_defaults: bool = True
    environment: str = "development"
    app_version: str = read_app_version()


def load_settings(env_map: Mapping[str, str] | None = None) -> Settings:
    """Construct Settings from an explicit mapping or process environment."""
    source: Mapping[str, str] = os.environ if env_map is None else env_map
    raw_port = source.get("BOARDGAME_APP_PORT", "8088").strip()
    raw_seed = source.get("BOARDGAME_SEED_DEFAULTS", "true").strip().lower()
    return Settings(
        app_host=source.get("BOARDGAME_APP_HOST", "0.0.0.0").strip() or "0.0.0.0",
        app_port=int(raw_port) if raw_port.isdigit() else 8088,
        db_path=source.get("BOARDGAME_DB_PATH", "data/boardgames.sqlite3").strip() or "data/boardgames.sqlite3",
        seed_defaults=raw_seed not in {"0", "false", "no", "off"},
        environment=source.get("BOARDGAME_ENVIRONMENT", "development").strip() or "development",
        app_version=read_app_version(),
    )
