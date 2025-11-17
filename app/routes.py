"""Flask routes for the Calendar automation service."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from flask import Blueprint, current_app, jsonify, redirect, request, session, url_for
from google_auth_oauthlib.flow import Flow

from .calendar_service import get_calendar_service, serialize_credentials
from .event_parser import EventParsingError, parse_event_details
from .openai_client import request_event_details

LOGGER = logging.getLogger(__name__)


def register_routes(app) -> None:
    bp = Blueprint("calendar", __name__)

    @bp.route("/health", methods=["GET"])
    def health() -> Any:
        return jsonify({"status": "ok"})

    @bp.route("/authorize")
    def authorize() -> Any:
        flow = Flow.from_client_secrets_file(
            current_app.config["CLIENT_SECRETS_FILE"],
            scopes=current_app.config["GOOGLE_SCOPES"],
        )
        redirect_uri = request.host_url.rstrip("/") + url_for("calendar.oauth2callback")
        flow.redirect_uri = redirect_uri
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        session["state"] = state
        return redirect(authorization_url)

    @bp.route("/oauth2callback")
    def oauth2callback() -> Any:
        try:
            state = session["state"]
            flow = Flow.from_client_secrets_file(
                current_app.config["CLIENT_SECRETS_FILE"],
                scopes=current_app.config["GOOGLE_SCOPES"],
                state=state,
            )
            redirect_uri = request.host_url.rstrip("/") + url_for("calendar.oauth2callback")
            flow.redirect_uri = redirect_uri
            flow.fetch_token(authorization_response=request.url)

            credentials_dict = serialize_credentials(flow.credentials)
            cache_path = Path(current_app.config["GOOGLE_CREDENTIALS_CACHE"])
            cache_path.write_text(json.dumps(credentials_dict))
            session["credentials"] = credentials_dict
            return jsonify({"message": "Authorization successful. You can now create events."})
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("OAuth callback failed")
            return jsonify({"error": str(exc)}), 500

    @bp.route("/create_event", methods=["POST"])
    def create_event() -> Any:
        data = request.get_json(silent=True) or {}
        user_input = data.get("text")
        if not user_input:
            return jsonify({"error": "Missing input text"}), 400

        try:
            event_details = request_event_details(
                api_key=current_app.config["OPENAI_API_KEY"],
                model=current_app.config["OPENAI_MODEL"],
                user_text=user_input,
            )
            if not event_details:
                raise ValueError("OpenAI API returned an empty response.")

            event_payload = parse_event_details(
                event_details, current_app.config["DEFAULT_TIMEZONE"]
            )
            service = get_calendar_service(current_app.config["GOOGLE_CREDENTIALS_CACHE"])
            created_event = (
                service.events().insert(calendarId="primary", body=event_payload).execute()
            )
            return jsonify({"message": "Event created", "eventLink": created_event.get("htmlLink")})
        except (EventParsingError, ValueError) as exc:
            LOGGER.warning("Validation failed: %s", exc)
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Error creating event")
            return jsonify({"error": str(exc)}), 500

    app.register_blueprint(bp)
