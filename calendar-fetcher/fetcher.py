import os
from datetime import datetime, date, timezone, timedelta

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

    # 3-week rolling grid: Sunday of current week → Saturday 3 weeks later
    today = date.today()
    dow = (today.weekday() + 1) % 7  # Sun=0, Mon=1, …, Sat=6
    grid_start = today - timedelta(days=dow)
    grid_end = grid_start + timedelta(days=20)  # 3 full weeks, ends on a Saturday

    time_min = datetime(
        grid_start.year, grid_start.month, grid_start.day, tzinfo=timezone.utc
    )
    time_max = datetime(
        grid_end.year, grid_end.month, grid_end.day, 23, 59, 59, tzinfo=timezone.utc
    )

    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=50,
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
