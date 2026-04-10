"""Utilities to parse LLM JSON responses into Google Calendar API payloads."""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

LOGGER = logging.getLogger(__name__)

# Valid Google Calendar event color IDs (1-24 per Colors API)
VALID_COLOR_IDS = {str(i) for i in range(1, 25)}

VALID_VISIBILITY = {"default", "public", "private", "confidential"}
VALID_TRANSPARENCY = {"opaque", "transparent"}
VALID_STATUS = {"confirmed", "tentative"}
VALID_EVENT_TYPES = {"default", "focusTime", "outOfOffice", "workingLocation", "birthday"}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# Importance → colorId fallback mapping
IMPORTANCE_COLOR_MAP = {
    "critical": "11",  # Tomato
    "high": "6",       # Tangerine
    "normal": "7",     # Peacock
    "low": "9",        # Blueberry
    "trivial": "8",    # Graphite
}


class EventParsingError(ValueError):
    """Raised when an LLM response cannot be parsed into an event."""


def _parse_json(raw: str) -> Dict[str, Any]:
    """Try to parse JSON from LLM response, handling common issues."""
    raw = raw.strip()

    # Strip markdown code fences
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw = "\n".join(lines).strip()

    # Strip thinking tags
    raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()

    # Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try to find outermost JSON object
    depth = 0
    start_idx = None
    for i, ch in enumerate(raw):
        if ch == '{':
            if depth == 0:
                start_idx = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start_idx is not None:
                try:
                    return json.loads(raw[start_idx:i + 1])
                except json.JSONDecodeError:
                    start_idx = None

    raise EventParsingError(f"Could not parse JSON from LLM response: {raw[:300]}")


def parse_event_details(details: str, timezone: str) -> List[Dict[str, Any]]:
    """Parse an LLM JSON response into a list of Google Calendar event bodies."""
    if not details or not isinstance(details, str):
        raise EventParsingError("Event details are empty or invalid.")

    data = _parse_json(details)

    # Support both {"events": [...]} and single event {...}
    if "events" in data and isinstance(data["events"], list):
        raw_events = data["events"]
    else:
        raw_events = [data]

    if not raw_events:
        raise EventParsingError("No events found in LLM response.")

    results = []
    for idx, item in enumerate(raw_events):
        try:
            event = _build_event(item, timezone)
            results.append(event)
        except EventParsingError as e:
            LOGGER.warning("Skipping event #%d: %s", idx + 1, e)
            if len(raw_events) == 1:
                raise
            continue

    if not results:
        raise EventParsingError("All events failed to parse.")

    return results


def _build_event(data: Dict[str, Any], timezone: str) -> Dict[str, Any]:
    """Build a single Google Calendar event payload from parsed data."""
    event: Dict[str, Any] = {}

    # Required: summary
    summary = str(data.get("summary", "")).strip()
    if not summary:
        raise EventParsingError("Event summary/title is required.")
    event["summary"] = summary

    # Determine timezone
    tz = data.get("timezone", timezone) or timezone

    # Start and End times
    is_all_day = data.get("all_day", False)

    if is_all_day:
        start_date = data.get("start_date", "")
        end_date = data.get("end_date", "")
        if not start_date:
            raise EventParsingError("start_date is required for all-day events.")
        if not end_date:
            try:
                dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_date = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
            except ValueError:
                raise EventParsingError(f"Invalid start_date format: {start_date}")
        event["start"] = {"date": start_date}
        event["end"] = {"date": end_date}
    else:
        start_dt = data.get("start_datetime", "")
        end_dt = data.get("end_datetime", "")
        if not start_dt:
            raise EventParsingError("start_datetime is required.")
        if not end_dt:
            try:
                dt = datetime.fromisoformat(start_dt)
                end_dt = (dt + timedelta(hours=1)).isoformat()
            except ValueError:
                raise EventParsingError(f"Invalid start_datetime format: {start_dt}")
        event["start"] = {"dateTime": start_dt, "timeZone": tz}
        event["end"] = {"dateTime": end_dt, "timeZone": tz}

    # Optional: location
    location = str(data.get("location", "")).strip()
    if location and location.lower() not in {"n/a", "none", "null", ""}:
        event["location"] = location

    # Optional: description (supports HTML)
    description = str(data.get("description", "")).strip()
    if description and description.lower() not in {"n/a", "none", "null", ""}:
        event["description"] = description

    # Optional: recurrence (RRULE/EXRULE/RDATE/EXDATE)
    recurrence = data.get("recurrence", "")
    if isinstance(recurrence, list):
        rules = []
        for rule in recurrence:
            rule = str(rule).strip()
            if rule and rule.lower() not in {"n/a", "none", "null"}:
                if not any(rule.upper().startswith(prefix) for prefix in ("RRULE:", "EXRULE:", "RDATE:", "EXDATE:")):
                    rule = f"RRULE:{rule}"
                rules.append(rule)
        if rules:
            event["recurrence"] = rules
    elif isinstance(recurrence, str) and recurrence.strip() and recurrence.lower() not in {"n/a", "none", "null"}:
        rule = recurrence.strip()
        if not any(rule.upper().startswith(prefix) for prefix in ("RRULE:", "EXRULE:", "RDATE:", "EXDATE:")):
            rule = f"RRULE:{rule}"
        event["recurrence"] = [rule]

    # Optional: attendees (supports extended format)
    attendees = data.get("attendees", [])
    if attendees and isinstance(attendees, list):
        valid_attendees = []
        for att in attendees:
            if isinstance(att, str):
                email = att.strip()
                if EMAIL_RE.match(email):
                    valid_attendees.append({"email": email})
            elif isinstance(att, dict) and "email" in att:
                email = str(att["email"]).strip()
                if not EMAIL_RE.match(email):
                    LOGGER.warning("Skipping invalid attendee email: %s", email)
                    continue
                entry: Dict[str, Any] = {"email": email}
                if att.get("displayName"):
                    entry["displayName"] = att["displayName"]
                if att.get("optional") is True:
                    entry["optional"] = True
                if att.get("comment"):
                    entry["comment"] = att["comment"]
                if att.get("additionalGuests") and isinstance(att["additionalGuests"], int):
                    entry["additionalGuests"] = att["additionalGuests"]
                valid_attendees.append(entry)
        if valid_attendees:
            event["attendees"] = valid_attendees

    # Optional: reminders (max 5 overrides)
    reminders = data.get("reminders", [])
    if reminders and isinstance(reminders, list):
        overrides = []
        for r in reminders:
            if isinstance(r, dict) and "method" in r and "minutes" in r:
                method = r["method"]
                minutes = r["minutes"]
                if method in ("popup", "email") and isinstance(minutes, (int, float)):
                    overrides.append({"method": method, "minutes": int(minutes)})
        if overrides:
            event["reminders"] = {"useDefault": False, "overrides": overrides[:5]}
    else:
        event["reminders"] = {"useDefault": True}

    # Color: use explicit color_id, or derive from importance
    color_id = str(data.get("color_id", "")).strip()
    importance = str(data.get("importance", "normal")).strip().lower()
    if color_id in VALID_COLOR_IDS:
        event["colorId"] = color_id
    elif importance in IMPORTANCE_COLOR_MAP:
        event["colorId"] = IMPORTANCE_COLOR_MAP[importance]

    # Optional: visibility
    visibility = str(data.get("visibility", "")).strip().lower()
    if visibility in VALID_VISIBILITY and visibility != "default":
        event["visibility"] = visibility

    # Optional: transparency (busy/free)
    transparency = str(data.get("transparency", "")).strip().lower()
    if transparency in VALID_TRANSPARENCY:
        event["transparency"] = transparency

    # Optional: status
    status = str(data.get("status", "")).strip().lower()
    if status in VALID_STATUS:
        event["status"] = status

    # Optional: eventType
    event_type = str(data.get("event_type", "")).strip()
    if event_type in VALID_EVENT_TYPES and event_type != "default":
        event["eventType"] = event_type
        # Add type-specific properties
        if event_type == "focusTime":
            event["focusTimeProperties"] = {
                "chatStatus": "doNotDisturb",
                "autoDeclineMode": "declineAllConflictingInvitations",
                "declineMessage": "Declined because I am in focus time.",
            }
        elif event_type == "outOfOffice":
            event["outOfOfficeProperties"] = {
                "autoDeclineMode": "declineAllConflictingInvitations",
                "declineMessage": "I am out of office.",
            }

    # Optional: guest permissions
    if data.get("guests_can_modify") is True:
        event["guestsCanModify"] = True
    if data.get("guests_can_invite_others") is False:
        event["guestsCanInviteOthers"] = False
    if data.get("guests_can_see_other_guests") is False:
        event["guestsCanSeeOtherGuests"] = False

    # Optional: conference (Google Meet)
    if data.get("conference") is True:
        event["conferenceData"] = {
            "createRequest": {
                "requestId": str(uuid.uuid4()),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }

    # Optional: source
    source_url = str(data.get("source_url", "")).strip()
    source_title = str(data.get("source_title", "")).strip()
    if source_url:
        event["source"] = {"url": source_url}
        if source_title:
            event["source"]["title"] = source_title

    return event
