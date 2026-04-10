"""Flask routes for the Calendar automation service."""
from __future__ import annotations

import logging
from typing import Any

from flask import Blueprint, current_app, jsonify, request

from .calendar_service import get_calendar_service_from_token
from .event_parser import EventParsingError, parse_event_details
from .openai_client import request_event_details

LOGGER = logging.getLogger(__name__)


def _check_api_key(app_config):
    """Validate X-API-Key header if API_KEYS is configured."""
    api_keys = app_config.get("API_KEYS", [])
    if not api_keys:  # not configured, skip validation
        return None
    key = request.headers.get("X-API-Key", "")
    if key not in api_keys:
        return jsonify({"error": "Invalid or missing API key"}), 401
    return None


def _get_google_token():
    """Extract Google access token from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


def register_routes(app) -> None:
    bp = Blueprint("calendar", __name__)

    @bp.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin", "*")
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response

    @bp.route("/health", methods=["GET"])
    def health() -> Any:
        return jsonify({"status": "ok"})

    @bp.route("/create_event", methods=["POST", "OPTIONS"])
    def create_event() -> Any:
        if request.method == "OPTIONS":
            return jsonify({}), 200

        # Validate API key
        err = _check_api_key(current_app.config)
        if err:
            return err

        # Get Google token from frontend
        google_token = _get_google_token()
        if not google_token:
            return jsonify({"error": "Missing Google authorization token"}), 401

        data = request.get_json(silent=True) or {}
        user_input = data.get("text")
        if not user_input:
            return jsonify({"error": "Missing input text"}), 400

        try:
            # Step 1: Call LLM to extract event details
            event_details = request_event_details(
                api_key=current_app.config["OPENAI_API_KEY"],
                model=current_app.config["OPENAI_MODEL"],
                base_url=current_app.config["OPENAI_BASE_URL"],
                user_text=user_input,
                timezone=current_app.config["DEFAULT_TIMEZONE"],
            )
            if not event_details:
                raise ValueError("LLM API returned an empty response.")

            # Step 2: Parse JSON into Google Calendar event payloads
            event_payloads = parse_event_details(
                event_details, current_app.config["DEFAULT_TIMEZONE"]
            )

            # Step 3: Insert events using frontend-provided token
            service = get_calendar_service_from_token(google_token)
            created_events = []

            for event_payload in event_payloads:
                insert_kwargs = {"calendarId": "primary", "body": event_payload}
                if "conferenceData" in event_payload:
                    insert_kwargs["conferenceDataVersion"] = 1
                created = service.events().insert(**insert_kwargs).execute()
                created_events.append({
                    "eventId": created.get("id"),
                    "eventLink": created.get("htmlLink"),
                    "summary": event_payload.get("summary"),
                    "start": event_payload.get("start"),
                    "end": event_payload.get("end"),
                    "colorId": event_payload.get("colorId"),
                })

            return jsonify({
                "message": f"{len(created_events)} event(s) created",
                "count": len(created_events),
                "events": created_events,
                "eventLink": created_events[0].get("eventLink") if created_events else None,
                "summary": created_events[0].get("summary") if created_events else None,
            })
        except (EventParsingError, ValueError) as exc:
            LOGGER.warning("Validation failed: %s", exc)
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            LOGGER.exception("Error creating event")
            return jsonify({"error": str(exc)}), 500

    @bp.route("/parse_event", methods=["POST", "OPTIONS"])
    def parse_event() -> Any:
        """Parse text into event details without creating the event (preview mode)."""
        if request.method == "OPTIONS":
            return jsonify({}), 200

        # Validate API key
        err = _check_api_key(current_app.config)
        if err:
            return err

        # Google token is optional for parse (no calendar write needed)
        # but we still validate it if present for consistency

        data = request.get_json(silent=True) or {}
        user_input = data.get("text")
        if not user_input:
            return jsonify({"error": "Missing input text"}), 400

        try:
            event_details = request_event_details(
                api_key=current_app.config["OPENAI_API_KEY"],
                model=current_app.config["OPENAI_MODEL"],
                base_url=current_app.config["OPENAI_BASE_URL"],
                user_text=user_input,
                timezone=current_app.config["DEFAULT_TIMEZONE"],
            )
            if not event_details:
                raise ValueError("LLM API returned an empty response.")

            event_payloads = parse_event_details(
                event_details, current_app.config["DEFAULT_TIMEZONE"]
            )
            return jsonify({
                "count": len(event_payloads),
                "events": event_payloads,
                "event": event_payloads[0] if event_payloads else None,
            })
        except (EventParsingError, ValueError) as exc:
            LOGGER.warning("Validation failed: %s", exc)
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            LOGGER.exception("Error parsing event")
            return jsonify({"error": str(exc)}), 500

    app.register_blueprint(bp)
