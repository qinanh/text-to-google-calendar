"""Configuration helpers for the application."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv


DEFAULT_SCOPES: List[str] = ["https://www.googleapis.com/auth/calendar"]
LOGGER = logging.getLogger(__name__)


def _ensure_credentials_file(path: str) -> str:
    expanded = Path(path).expanduser()
    if not expanded.exists():
        LOGGER.warning(
            "Google OAuth client secrets file '%s' is not present yet. Authorization will fail until it is uploaded.",
            expanded,
        )
    return str(expanded)


def load_config() -> Dict[str, Any]:
    """Load settings from the environment with sensible defaults."""
    load_dotenv()

    secret_key = os.getenv("FLASK_SECRET_KEY", "change-me")
    client_secrets_file = os.getenv("GOOGLE_CLIENT_SECRETS", "credentials.json")
    credentials_cache = os.getenv("GOOGLE_CREDENTIALS_CACHE", "cred.json")

    config: Dict[str, Any] = {
        "SECRET_KEY": secret_key,
        "GOOGLE_SCOPES": DEFAULT_SCOPES,
        "CLIENT_SECRETS_FILE": _ensure_credentials_file(client_secrets_file),
        "GOOGLE_CREDENTIALS_CACHE": credentials_cache,
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "OPENAI_MODEL": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        "DEFAULT_TIMEZONE": os.getenv("DEFAULT_TIMEZONE", "America/Chicago"),
        "FORCE_SSL": os.getenv("FORCE_SSL", "false").lower() == "true",
    }

    if not config["OPENAI_API_KEY"]:
        raise EnvironmentError(
            "OPENAI_API_KEY must be supplied via environment variables or .env."
        )

    return config
