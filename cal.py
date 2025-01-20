from flask import Flask, request, jsonify, session, redirect, url_for
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import requests
import logging
import os
import json  

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # YOUR SECRET KEY

# set Google Calendar API 
SCOPES = ['https://www.googleapis.com/auth/calendar']
CLIENT_SECRETS_FILE = 'credentials.json'  # replace with your credentials file
OPENAI_API_KEY = YOUR-OPENAI-API-KEY  # your OpenAI API Key

logging.basicConfig(level=logging.INFO)


def get_calendar_service(client_id=None):
    """get Google Calendar API service"""
    credentials_file = 'cred.json'

    # load credentials from file
    try:
        with open(credentials_file, 'r') as f:
            stored_credentials = json.load(f)
    except FileNotFoundError:
        raise ValueError(f"Credentials file '{credentials_file}' not found. Please reauthorize.")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON format in '{credentials_file}'.")


    creds_data = stored_credentials
    
    try:
        # create Credentials object
        creds = Credentials(
            token=creds_data['token'],
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data['token_uri'],
            client_id=creds_data['client_id'],
            client_secret=creds_data['client_secret'],
            scopes=creds_data['scopes']
        )
        
        print(f"credentials: {str(creds)}")
        
        # initialize Google Calendar API service
        service = build('calendar', 'v3', credentials=creds)
        print("Authentication successful")
        return service
        
    except KeyError as e:
        raise ValueError(f"Missing required credential field: {str(e)}")


def parse_event_details(details):
    """parse event details from OpenAI response"""
    if not details or not isinstance(details, str):
        raise ValueError("Event details are empty or invalid.")

    lines = [line.strip() for line in details.split("\n") if line.strip()]
    event = {
        'summary': "New Event",
        'location': "No Location",
        'description': "No Description",
        'start': {'dateTime': None, 'timeZone': "America/Chicago"},
        'end': {'dateTime': None, 'timeZone': "America/Chicago"},
        'recurrence': [],
        'attendees': [],
        'reminders': {'useDefault': True}
    }

    for line in lines:
        try:
            if line.startswith("Title:"):
                event['summary'] = line.split(":", 1)[1].strip()
            elif line.startswith("Location:"):
                event['location'] = line.split(":", 1)[1].strip()
            elif line.startswith("Description:"):
                event['description'] = line.split(":", 1)[1].strip()
            elif line.startswith("Start Time:"):
                event['start']['dateTime'] = line.split(":", 1)[1].strip()
            elif line.startswith("End Time:"):
                event['end']['dateTime'] = line.split(":", 1)[1].strip()
            elif line.startswith("Recurrence:"):
                recurrence_rule = line.split(":", 1)[1].strip()
                # skip "N/A", "none" or empty strings
                if recurrence_rule and recurrence_rule.lower() not in ["n/a", "none"]:
                    # if missing "RRULE:" prefix, add it
                    if not recurrence_rule.upper().startswith("RRULE:"):
                        recurrence_rule = "RRULE:" + recurrence_rule
                    event['recurrence'] = [recurrence_rule]
            elif line.startswith("Attendees:"):
                attendees_text = line.split(":", 1)[1].strip()
                # skip "N/A", "none" or empty strings
                if attendees_text and attendees_text.lower() not in ["n/a", "none"]:
                    # split emails by comma
                    possible_emails = [email.strip() for email in attendees_text.split(",")]
                    valid_attendees = []
                    for e in possible_emails:
                        # validate email format
                        if "@" in e and "." in e:
                            valid_attendees.append({'email': e})
                    event['attendees'] = valid_attendees
            elif line.startswith("Reminders:"):
                reminders_text = line.split(":", 1)[1].strip()
                if reminders_text and reminders_text.lower() not in ["n/a", "none"]:
                    overrides = []
                    for r in reminders_text.split(","):
                        r = r.strip()
                        if ":" in r:
                            method, minutes = r.split(":", 1)
                            method = method.strip()
                            try:
                                minutes = int(minutes.strip())
                                overrides.append({'method': method, 'minutes': minutes})
                            except ValueError:
                                pass
                    if overrides:
                        event['reminders'] = {
                            'useDefault': False,
                            'overrides': overrides
                        }
        except Exception as e:
            raise ValueError(f"Error parsing line: '{line}'. Details: {e}")

    if not event['start']['dateTime']:
        raise ValueError("Start Time is missing or invalid.")
    if not event['end']['dateTime']:
        raise ValueError("End Time is missing or invalid.")

    return event


@app.route('/authorize')
def authorize():
    """Google OAuth 2.0 授权"""
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
    # set redirect URI
    redirect_uri = request.host_url.rstrip('/') + '/oauth2callback'
    flow.redirect_uri = redirect_uri
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # force user to re-consent
    )
    session['state'] = state
    return redirect(authorization_url)

def credentials_to_dict(credentials):
    """convert credentials to dictionary"""
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }


@app.route('/oauth2callback')
def oauth2callback():
    """Google OAuth 2.0 callback"""
    try:
        state = session['state']
        flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
        redirect_uri = request.host_url.rstrip('/') + '/oauth2callback'
        flow.redirect_uri = redirect_uri
        flow.fetch_token(authorization_response=request.url)
        print(flow.credentials)
        # convert credentials to dictionary
        credentials_dict = credentials_to_dict(flow.credentials)
        print(credentials_dict)
        # store credentials to file
        with open('cred.json', 'w') as f:
            json.dump(credentials_dict, f)

        # store credentials in session
        session['credentials'] = credentials_dict

        return jsonify({'message': 'Authorization successful. You can now use the service.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/create_event', methods=['POST'])
def create_event():
    """Create a Google Calendar event based on user input"""
    try:
        user_input = request.json.get('text')
        if not user_input:
            return jsonify({'error': 'Missing input text'}), 400

        # retrieve credentials from session
        logging.info("Sending data to OpenAI API")
        openai_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Please format the following text as a Google Calendar event:\n\n"
                        f"{user_input}\n\n"
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
                }
                ]
            }
        )
        openai_response.raise_for_status()
        response_json = openai_response.json()
        event_details = response_json.get('choices', [{}])[0].get('message', {}).get('content', '')
        print(event_details)
        # test if response is empty
        if not event_details:
            raise ValueError("OpenAI API returned an empty response.")

        # create Google Calendar event
        event = parse_event_details(event_details)
        print(event)
        service = get_calendar_service()
        created_event = service.events().insert(calendarId='primary', body=event).execute()

        return jsonify({'message': 'Event created', 'eventLink': created_event.get('htmlLink')})

    except Exception as e:
        logging.error(f"Error creating event: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, ssl_context=(
        'PATH/fullchain.pem',  # Change to your fullchain.pem path
        'PATH/privkey.pem'     # Change to your privkey.pem path
    ))
