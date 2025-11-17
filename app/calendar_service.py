"""Google Calendar helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class CredentialsError(RuntimeError):
    """Raised when stored credentials are unavailable."""


def _load_credentials(path: str) -> Dict[str, str]:
    cache_path = Path(path)
    if not cache_path.exists():
        raise CredentialsError(
            f"Credentials file '{cache_path}' not found. Run the /authorize flow first."
        )

    try:
        return json.loads(cache_path.read_text())
    except json.JSONDecodeError as exc:
        raise CredentialsError(
            f"Invalid JSON format in '{cache_path}': {exc}"  # noqa: TRY003
        ) from exc


def get_calendar_service(credentials_cache: str) -> "Resource":
    """Return an authenticated Google Calendar service resource."""
    creds_data = _load_credentials(credentials_cache)
    creds = Credentials(
        token=creds_data.get("token"),
        refresh_token=creds_data.get("refresh_token"),
        token_uri=creds_data.get("token_uri"),
        client_id=creds_data.get("client_id"),
        client_secret=creds_data.get("client_secret"),
        scopes=creds_data.get("scopes", []),
    )
    return build("calendar", "v3", credentials=creds)


def serialize_credentials(credentials: Credentials) -> Dict[str, str]:
    """Convert credentials to a JSON-serializable dictionary."""
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }
