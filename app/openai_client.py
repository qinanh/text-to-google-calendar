"""Helper for calling LLM Chat Completions API (OpenAI-compatible)."""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict

import requests

LOGGER = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a calendar event extraction assistant. Extract event details from user text and return ONLY valid JSON.

Current date/time context: {current_time}

IMPORTANT: The user may describe ONE or MULTIPLE events in a single message. Always return a JSON object with an "events" array, even if there is only one event.

Return format:
{{
  "events": [
    {{
      "summary": "Event title (required)",
      "location": "Event location",
      "description": "Event description or additional details (can contain HTML)",
      "start_datetime": "YYYY-MM-DDTHH:mm:ss (required for timed events)",
      "end_datetime": "YYYY-MM-DDTHH:mm:ss (required, default 1 hour after start)",
      "all_day": false,
      "start_date": "YYYY-MM-DD (only for all-day events)",
      "end_date": "YYYY-MM-DD (only for all-day events, exclusive end date)",
      "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR"],
      "attendees": [
        {{"email": "a@example.com", "displayName": "Alice", "optional": false}},
        {{"email": "b@example.com"}}
      ],
      "reminders": [{{"method": "popup", "minutes": 10}}, {{"method": "email", "minutes": 1440}}],
      "color_id": "1-24",
      "visibility": "default|public|private|confidential",
      "transparency": "opaque|transparent",
      "status": "confirmed|tentative",
      "event_type": "default|focusTime|outOfOffice|workingLocation",
      "conference": true,
      "guests_can_modify": false,
      "guests_can_invite_others": true,
      "guests_can_see_other_guests": true,
      "source_title": "Source name",
      "source_url": "https://...",
      "timezone": "Asia/Shanghai",
      "importance": "critical|high|normal|low|trivial"
    }}
  ]
}}

Color assignment rules (MUST follow based on event importance and type):
- importance=critical → color_id "11" (Tomato/Red - urgent deadlines, emergencies)
- importance=high → color_id "6" (Tangerine/Orange - important meetings, reviews)
- importance=normal → color_id "7" (Peacock/Teal - regular meetings, default)
- importance=low → color_id "9" (Blueberry/Blue - casual catch-ups, optional)
- importance=trivial → color_id "8" (Graphite/Gray - reminders, notes)
- event_type=focusTime → color_id "5" (Banana/Yellow)
- event_type=outOfOffice → color_id "3" (Grape/Purple)
- event_type=workingLocation → color_id "2" (Sage/Green)
- Birthday/anniversary → color_id "4" (Flamingo/Pink)
- Exercise/health/gym → color_id "10" (Basil/Dark Green)
- Social/party/dinner → color_id "1" (Lavender)
- Travel/flight/trip → color_id="14" (Peacock)

Determine importance by these criteria:
- critical: words like "urgent", "deadline", "ASAP", "emergency", "due", "紧急", "截止", "最后期限"
- high: "important", "review", "interview", "presentation", "exam", "重要", "面试", "评审", "考试"
- normal: regular meetings, calls, appointments (default if not specified)
- low: "optional", "casual", "coffee chat", "可选", "随意"
- trivial: "reminder", "note", "FYI", "提醒", "备忘"

Other rules:
- If the user specifies a relative date like "tomorrow", "next Monday", calculate from current date/time.
- If no time is given for a meeting, default to 09:00.
- If no end time is given, default to 1 hour after start.
- If the text mentions "all day" or "全天", set all_day=true and use start_date/end_date.
- For recurrence, use standard RRULE format (RFC 5545). Support EXDATE for exceptions.
- Always assign importance and color_id based on the rules above.
- Return ONLY the JSON object, no markdown, no explanation, no code fences.\
"""


def request_event_details(
    *, api_key: str, model: str, user_text: str, base_url: str, timezone: str
) -> str:
    """Send user text to LLM and return the JSON event description."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(current_time=current_time),
            },
            {
                "role": "user",
                "content": user_text,
            },
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
    }

    # Dashscope (Qwen) compatible-mode: disable thinking for speed
    if "qwen" in model.lower():
        payload["enable_thinking"] = False

    api_url = f"{base_url.rstrip('/')}/chat/completions"
    LOGGER.info("Sending request to %s model %s", api_url, model)

    response = requests.post(
        api_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    response_json = response.json()
    content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")

    # Strip markdown code fences if present
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines).strip()

    # Handle Qwen thinking tags - strip <think>...</think> blocks
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

    return content
