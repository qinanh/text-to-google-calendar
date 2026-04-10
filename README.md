# Text to Google Calendar

> Turn any text into a Google Calendar event with AI. A Chrome extension + lightweight backend that lets you select text on any webpage and instantly create a perfectly formatted calendar event.

🌐 **Website:** https://qinanh.github.io/text-to-gcal-site/

## Features

- 🖱️ **Right-click any text** to create or preview a calendar event
- 🤖 **AI-powered parsing** of titles, dates, times, locations, attendees, recurrence, and more
- 📅 **Multi-event support** — extract several events from one block of text
- 🔐 **Multi-user by design** — each user signs in with their own Google account; the backend never stores credentials
- 🎨 **Rich event support** — colors, reminders, Google Meet links, recurrence rules, and visibility settings
- ⚡ **Self-hostable backend** — bring your own LLM provider (OpenAI, Qwen, or any OpenAI-compatible API)

## Architecture

```
┌──────────────────┐  Bearer token  ┌──────────────┐  AI parse   ┌────────────┐
│ Chrome Extension │ ─────────────► │ Flask Backend│ ──────────► │  LLM API   │
│                  │                │              │             └────────────┘
│ • OAuth login    │                │ • Parse JSON │
│ • Stores token   │                │ • Build event│  Insert event
│ • Sends text     │ ◄───────────── │ • Forward to │ ──────────► Google Calendar
└──────────────────┘   event link   │   Calendar   │             (with user's
                                    └──────────────┘              own token)
```

- The extension handles **all** Google OAuth in the user's browser via `chrome.identity.launchWebAuthFlow`.
- Each request to the backend carries the user's Google access token in the `Authorization` header.
- The backend never stores user credentials — it just forwards events to Google Calendar using whatever token is presented.
- Optional `X-API-Key` header gates backend access for self-hosted deployments.

## Project Structure

```
.
├── app/                    # Flask backend
│   ├── __init__.py         # App factory
│   ├── config.py           # Env-driven config
│   ├── routes.py           # /create_event, /parse_event, /health
│   ├── calendar_service.py # Google Calendar wrapper
│   ├── event_parser.py     # LLM JSON → Calendar payload
│   └── openai_client.py    # LLM API call
├── chrome-extension/src/   # Chrome extension (Manifest V3)
│   ├── manifest.json
│   ├── background.js       # OAuth + API calls
│   ├── popup.html / .js    # Settings UI + manual entry
│   ├── content.js / .css   # In-page toast notifications
│   └── images/             # Icons
├── web/                    # Landing page (deployed via GitHub Pages)
├── main.py                 # WSGI entrypoint
├── Dockerfile
└── requirements.txt
```

## Quick Start (Self-Hosted)

### 1. Backend

```bash
git clone https://github.com/qinanh/text-to-google-calendar.git
cd text-to-google-calendar

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set OPENAI_API_KEY (or your OpenAI-compatible provider key)

python main.py
# Backend now listening on http://localhost:8080
```

### 2. Google OAuth Client (one-time setup)

1. Open the [Google Cloud Console](https://console.cloud.google.com/) and create a project
2. Enable the **Google Calendar API**
3. Configure the **OAuth consent screen** (External, with Calendar scope)
4. Create an **OAuth 2.0 Client ID** of type **Web application**
5. Add an authorized redirect URI: `https://<your-extension-id>.chromiumapp.org/`
   - You'll get the extension ID after loading the extension below — add it then
6. Copy the **Client ID** (`xxxx.apps.googleusercontent.com`)
7. Paste it into `chrome-extension/src/background.js` at `GOOGLE_CLIENT_ID`

### 3. Chrome Extension

1. Open `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked** and select `chrome-extension/src/`
4. Copy the extension ID shown on the card
5. Go back to step 2.5 above and add `https://<that-id>.chromiumapp.org/` as a redirect URI in Google Cloud
6. Click the extension icon → **Login with Google**
7. Select text on any webpage → right-click → **Create Calendar Event**

## Configuration

### Backend (`.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | API key for your LLM provider | _required_ |
| `OPENAI_BASE_URL` | OpenAI-compatible API base URL | OpenAI |
| `OPENAI_MODEL` | Model name | `gpt-3.5-turbo` |
| `DEFAULT_TIMEZONE` | IANA timezone for parsed events | `America/Chicago` |
| `API_KEYS` | Comma-separated list of accepted API keys (empty = open) | _empty_ |
| `FLASK_SECRET_KEY` | Flask session secret | `change-me` |

### Extension (Settings popup)

- **Server URL** — backend address (default `http://localhost:8081`)
- **Default Timezone** — IANA timezone

## API

### `POST /create_event`

```http
POST /create_event
Authorization: Bearer <google-oauth-access-token>
X-API-Key: <optional-backend-api-key>
Content-Type: application/json

{ "text": "Lunch with Alice next Friday at noon at The Cheesecake Factory" }
```

Response:
```json
{
  "count": 1,
  "events": [{
    "eventId": "abc123",
    "eventLink": "https://calendar.google.com/calendar/event?...",
    "summary": "Lunch with Alice",
    "start": {"dateTime": "2026-04-17T12:00:00", "timeZone": "America/Chicago"},
    "end": {"dateTime": "2026-04-17T13:00:00", "timeZone": "America/Chicago"}
  }]
}
```

### `POST /parse_event`

Same body as `/create_event` but returns the parsed event(s) without writing to Calendar (preview mode).

### `GET /health`

Returns `{"status": "ok"}`.

## Deployment

### Docker

```bash
docker build -t text-to-gcal .
docker run -p 8080:8080 --env-file .env text-to-gcal
```

### Google Cloud Run

```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/text-to-gcal
gcloud run deploy text-to-gcal \
  --image gcr.io/PROJECT_ID/text-to-gcal \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=...,API_KEYS=...
```

Then point the extension's **Server URL** at the Cloud Run URL.

## Privacy

- The extension stores your Google OAuth token only in your browser's local storage.
- The backend does not persist user data; selected text is sent to the LLM for parsing and immediately discarded.
- See the [Privacy Policy](https://qinanh.github.io/text-to-gcal-site/privacy.html) for details.

## License

MIT — see [LICENSE](LICENSE).
