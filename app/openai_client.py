"""Helper for calling the OpenAI Chat Completions API."""
from __future__ import annotations

import logging
from typing import Any, Dict

import requests

LOGGER = logging.getLogger(__name__)


PROMPT_TEMPLATE = (
    "Please format the following text as a Google Calendar event.\n\n"
    "{text}\n\n"
    "Respond with the event details in the following format:\n"
    "Title: [Event Title]\n"
    "Start Time: [YYYY-MM-DDTHH:mm:ss]\n"
    "End Time: [YYYY-MM-DDTHH:mm:ss]\n"
    "Location: [Event Location]\n"
    "Description: [Event Description]\n"
    "Recurrence: [Recurrence Rule]\n"
    "Attendees: [Comma-separated list of emails]\n"
    "Reminders: [Reminder Method: Minutes Before, e.g., popup:10, email:1440]"
)


def request_event_details(*, api_key: str, model: str, user_text: str) -> str:
    """Send user text to OpenAI and return the formatted event description."""
    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": PROMPT_TEMPLATE.format(text=user_text),
            }
        ],
        "temperature": 0.1,
    }

    LOGGER.info("Sending request to OpenAI model %s", model)
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    response_json = response.json()
    return response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
