import os
from datetime import datetime, timezone, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def fetch_events():
    credentials_path = os.environ.get(
        "GOOGLE_CREDENTIALS_PATH", "/credentials/service_account.json"
    )
    calendar_id = os.environ["CALENDAR_ID"]

    creds = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=SCOPES
    )
    service = build("calendar", "v3", credentials=creds)

    now = datetime.now(timezone.utc)
    time_max = now + timedelta(days=7)

    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=now.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = []
    for item in result.get("items", []):
        start = item["start"]
        end = item["end"]

        if "date" in start:
            all_day = True
            start_dt = datetime.fromisoformat(start["date"])
            end_dt = datetime.fromisoformat(end["date"])
        else:
            all_day = False
            start_dt = datetime.fromisoformat(start["dateTime"])
            end_dt = datetime.fromisoformat(end["dateTime"])

        events.append(
            {
                "summary": item.get("summary", "(No title)"),
                "start": start_dt,
                "end": end_dt,
                "all_day": all_day,
            }
        )

    return events
