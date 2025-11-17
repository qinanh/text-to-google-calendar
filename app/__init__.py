"""Application factory for the Google Calendar event service."""
from flask import Flask

from .config import load_config
from .routes import register_routes


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    config = load_config()
    app.config.from_mapping(config)

    register_routes(app)
    return app
