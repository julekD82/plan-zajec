import os.path
import json
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

scopes = ["https://www.googleapis.com/auth/calendar"]



def add_event(summary: str, start_datetime: str, end_datetime: str, location: str = "", description: str = ""):
    # Convert string timestamps to datetime objects
    start_datetime = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
    end_datetime = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))

    # Rest of the code remains the same
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file("token.json")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            with open('credentials.json', 'r') as file:
                credentials = json.load(file)
            flow = InstalledAppFlow.from_client_config(credentials, scopes=scopes)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        event = {
            "summary": summary,
            "location": location,
            "description": description,
            "colorId": 6,
            "start": {
                "dateTime": start_datetime.isoformat(),
                "timeZone": "Europe/Warsaw"
            },
            "end": {
                "dateTime": end_datetime.isoformat(),
                "timeZone": "Europe/Warsaw"
            },
            "recurrence": [],
            "attendees": []
        }

        event = service.events().insert(calendarId="primary", body=event).execute()
        print(event.get('htmlLink'))
    except HttpError as e:
        print(e)
