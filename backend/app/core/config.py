"""Minimal, database-free settings for the H-03 backend foundation."""

from dataclasses import dataclass
from os import environ


@dataclass(frozen=True)
class Settings:
    app_name: str = "Hesabyar API"
    environment: str = "development"


def get_settings() -> Settings:
    """Read non-secret configuration from process environment on app startup."""
    return Settings(
        app_name=environ.get("HESABYAR_APP_NAME", "Hesabyar API"),
        environment=environ.get("HESABYAR_APP_ENV", "development"),
    )
