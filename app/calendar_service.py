"""Google Calendar helpers."""
from __future__ import annotations

import logging
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

LOGGER = logging.getLogger(__name__)


def get_calendar_service_from_token(access_token: str) -> Any:
    """Build Google Calendar service from a frontend-provided access token."""
    creds = Credentials(token=access_token)
    return build("calendar", "v3", credentials=creds)
