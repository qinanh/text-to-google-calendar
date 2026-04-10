"""Configuration helpers for the application."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from dotenv import load_dotenv


DEFAULT_SCOPES: List[str] = ["https://www.googleapis.com/auth/calendar"]
LOGGER = logging.getLogger(__name__)


def load_config() -> Dict[str, Any]:
    """Load settings from the environment with sensible defaults."""
    load_dotenv()

    config: Dict[str, Any] = {
        "SECRET_KEY": os.getenv("FLASK_SECRET_KEY", "change-me"),
        "GOOGLE_SCOPES": DEFAULT_SCOPES,
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"),
        "OPENAI_MODEL": os.getenv("OPENAI_MODEL", "qwen3.5-flash"),
        "DEFAULT_TIMEZONE": os.getenv("DEFAULT_TIMEZONE", "Asia/Shanghai"),
        "FORCE_SSL": os.getenv("FORCE_SSL", "false").lower() == "true",
        "API_KEYS": [k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()],
    }

    if not config["OPENAI_API_KEY"]:
        raise EnvironmentError(
            "OPENAI_API_KEY must be supplied via environment variables or .env."
        )

    return config
