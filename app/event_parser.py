"""Utilities to parse OpenAI responses into Google Calendar payloads."""
from __future__ import annotations

from typing import Dict


DEFAULT_EVENT_TEMPLATE: Dict[str, object] = {
    "summary": "New Event",
    "location": "No Location",
    "description": "No Description",
    "start": {"dateTime": None, "timeZone": "America/Chicago"},
    "end": {"dateTime": None, "timeZone": "America/Chicago"},
    "recurrence": [],
    "attendees": [],
    "reminders": {"useDefault": True},
}


class EventParsingError(ValueError):
    """Raised when an OpenAI response cannot be parsed into an event."""


def parse_event_details(details: str, timezone: str) -> Dict[str, object]:
    """Parse an OpenAI response into a Google Calendar event body."""
    if not details or not isinstance(details, str):
        raise EventParsingError("Event details are empty or invalid.")

    lines = [line.strip() for line in details.split("\n") if line.strip()]
    event = DEFAULT_EVENT_TEMPLATE.copy()
    event["start"] = {"dateTime": None, "timeZone": timezone}
    event["end"] = {"dateTime": None, "timeZone": timezone}

    for line in lines:
        key, _, value = line.partition(":")
        if not _:
            continue
        key = key.lower()
        value = value.strip()

        if key == "title":
            event["summary"] = value or event["summary"]
        elif key == "location":
            event["location"] = value or event["location"]
        elif key == "description":
            event["description"] = value or event["description"]
        elif key == "start time":
            event["start"]["dateTime"] = value
        elif key == "end time":
            event["end"]["dateTime"] = value
        elif key == "recurrence" and value.lower() not in {"", "n/a", "none"}:
            recurrence_rule = value
            if not recurrence_rule.upper().startswith("RRULE:"):
                recurrence_rule = f"RRULE:{recurrence_rule}"
            event["recurrence"] = [recurrence_rule]
        elif key == "attendees" and value.lower() not in {"", "n/a", "none"}:
            event["attendees"] = [
                {"email": email.strip()}
                for email in value.split(",")
                if "@" in email and "." in email
            ]
        elif key == "reminders" and value.lower() not in {"", "n/a", "none"}:
            overrides = []
            for reminder in value.split(","):
                method, _, minutes = reminder.partition(":")
                if _ and minutes.strip().isdigit():
                    overrides.append({"method": method.strip(), "minutes": int(minutes.strip())})
            if overrides:
                event["reminders"] = {"useDefault": False, "overrides": overrides}

    if not event["start"]["dateTime"] or not event["end"]["dateTime"]:
        raise EventParsingError("Start and end times are required.")

    return event
