# Google Calendar Event Creator

A modernized Flask service that converts free-form text into structured Google Calendar events by combining the OpenAI Chat Completions API with the Google Calendar API. The service is production ready for Google Cloud Run deployments and still works for local development.

## Key Features

- **Modular architecture** – isolated modules for OpenAI requests, event parsing, and Google Calendar interactions.
- **Environment-driven configuration** – secrets are injected via environment variables or a local `.env` file to keep credentials out of the source tree.
- **Cloud Run ready** – includes a lean `Dockerfile`, gunicorn entrypoint, and health endpoint for managed deployments.
- **Chrome extension integration** – the existing extension can keep posting payloads to `/create_event` with no additional work.

## Requirements

- Python 3.11+
- Google Cloud project with the Calendar API enabled
- OpenAI API key with access to the Chat Completions API

## Environment Setup

1. Copy `.env.example` to `.env` and fill in the values:
   ```bash
   cp .env.example .env
   ```
2. Update the following variables:
   - `FLASK_SECRET_KEY` – any random string.
   - `OPENAI_API_KEY` – your OpenAI key.
   - `OPENAI_MODEL` – defaults to `gpt-3.5-turbo`, but any compatible chat model works.
   - `GOOGLE_CLIENT_SECRETS` – path to the OAuth client JSON downloaded from Google Cloud Console.
   - `GOOGLE_CREDENTIALS_CACHE` – file that will store refreshed credentials after completing the OAuth flow (defaults to `cred.json`).
   - `DEFAULT_TIMEZONE` – IANA timezone used when parsing events.

3. Install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

## Local Development

1. Start the Flask server:
   ```bash
   python main.py
   ```
   The service listens on `http://127.0.0.1:8080`.

2. Run the OAuth flow once to cache Google credentials:
   - Visit `http://127.0.0.1:8080/authorize`.
   - Complete the Google consent screen. `cred.json` will be created automatically (path configurable via `GOOGLE_CREDENTIALS_CACHE`).

3. Create calendar events:
   ```bash
   curl -X POST http://127.0.0.1:8080/create_event \
     -H "Content-Type: application/json" \
     -d '{"text": "Meeting with the product team tomorrow at 2pm for one hour"}'
   ```

## Deploying to Google Cloud Run

1. Enable the required APIs:
   ```bash
   gcloud services enable run.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com
   ```

2. Build and submit the container:
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/text-to-google-calendar
   ```

3. Deploy to Cloud Run:
   ```bash
   gcloud run deploy text-to-google-calendar \
     --image gcr.io/PROJECT_ID/text-to-google-calendar \
     --platform managed \
     --region REGION \
     --allow-unauthenticated \
     --set-env-vars OPENAI_API_KEY=your-key,FLASK_SECRET_KEY=prod-secret,GOOGLE_CLIENT_SECRETS=/secrets/credentials.json,GOOGLE_CREDENTIALS_CACHE=/secrets/cred.json
   ```

   Use Secret Manager and Cloud Run volumes for the Google credentials JSON files if preferred.

4. After deployment, visit `<SERVICE_URL>/authorize` once to complete OAuth and populate the credentials cache.

## Chrome Extension Integration

The `chrome-extension/` directory contains the original background script. Update the `url` variable inside `background.js` to the new Cloud Run service URL and load it via **Load unpacked** in Chrome. Selecting any text and choosing **Send to Calendar** will call the `/create_event` endpoint.

## File Overview

- `app/` – Flask blueprints, configuration utilities, and API helpers.
- `main.py` – entrypoint used both locally and by gunicorn inside Cloud Run.
- `.env.example` – template for required environment variables.
- `Dockerfile` – container definition optimized for Cloud Run.
- `chrome-extension/` – optional Chrome extension that pushes selected text to the API.

## Health Check

Cloud Run can use `/health` for readiness probes. It returns:
```json
{"status": "ok"}
```

## License

MIT License – see `LICENSE` for details.
