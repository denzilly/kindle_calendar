# Kindle Calendar Display — Project Brief

## Overview

A Raspberry Pi service that fetches Google Calendar events, renders them as a grayscale PNG, and serves the image over HTTP to a jailbroken Kindle Paperwhite (7th gen / PW3). The Kindle polls the Pi every 30 minutes and displays the image using `eips`, acting as a always-on e-ink wall calendar mounted on a refrigerator.

---

## Architecture

```
Google Calendar API
        ↓
Raspberry Pi (Docker)
  ├── calendar-fetcher  →  fetches events, renders PNG, saves to shared volume
  └── nginx             →  serves PNG over HTTP on local network
        ↓ (HTTP, every 30 min)
Kindle Paperwhite PW3 (jailbroken)
  └── shell script loop  →  wget image → eips to display
```

---

## Repository Structure

```
kindle-calendar/
├── docker-compose.yml
├── .env                        # CALENDAR_ID, PORT, etc.
├── calendar-fetcher/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # Entry point: fetch → render → save
│   ├── fetcher.py              # Google Calendar API logic
│   ├── renderer.py             # Pillow image rendering
│   └── credentials/            # Volume-mounted, gitignored
│       └── service_account.json
├── nginx/
│   └── nginx.conf
├── output/                     # Shared volume: rendered PNG lives here
└── kindle/
    └── update.sh               # Script to run on the Kindle
```

---

## Pi Side — Docker Services

### docker-compose.yml

Two services:

**`calendar-fetcher`**
- Python 3.11 container
- Runs `main.py` on a loop (sleep 1800 between runs)
- Mounts `./credentials` (read-only) and `./output` (read-write)
- Environment variables via `.env`

**`nginx`**
- Official nginx:alpine image
- Mounts `./output` as the web root (read-only)
- Exposes port 8080 (or configurable via `.env`)
- Serves `calendar.png` at `http://<pi-ip>:8080/calendar.png`

---

## Python Service

### Dependencies (`requirements.txt`)

```
google-api-python-client
google-auth
Pillow
```

### `fetcher.py` — Google Calendar API

- Authenticate using a **service account** (not OAuth) for reliability in an always-on setup. No token refresh issues.
- Share the target Google Calendar with the service account email.
- Fetch events with:
  - `timeMin`: now (UTC)
  - `timeMax`: now + 7 days
  - `singleEvents: True`, `orderBy: startTime`
  - `maxResults: 10`
- Return a list of event dicts: `{summary, start, end, all_day}`

### `renderer.py` — Image Generation

- Output size: **1072 × 1448 px** (Kindle PW3 native resolution), grayscale
- White background, black text
- Layout (top to bottom):
  - **Large date block**: Day of week (e.g. "Monday"), full date (e.g. "1 March 2025") — very large font, top section
  - **Divider line**
  - **Event list**: Each event shows time + title. All-day events show "All day". 
  - **Footer**: Small text showing "Updated: HH:MM" timestamp
- Font: Use a bundled TTF (e.g. DejaVu or Liberation Sans — include in the repo, don't rely on system fonts)
- High contrast only — no grays, no anti-aliasing tricks. E-ink renders best with pure black on white.
- If no events: show "No upcoming events" in the event area

### `main.py` — Entry Point

```python
while True:
    events = fetch_events()
    render_image(events, output_path="/output/calendar.png")
    sleep(1800)
```

Write to a temp file first, then `os.replace()` atomically so nginx never serves a half-written file.

---

## Google Calendar Setup

1. Create a Google Cloud project
2. Enable the **Google Calendar API**
3. Create a **Service Account** (no roles needed)
4. Download the JSON key → place at `credentials/service_account.json`
5. In Google Calendar, share the calendar with the service account email (view-only is sufficient)
6. Set `CALENDAR_ID` in `.env` (use the calendar's email address, or `primary` if it's the main calendar of the service account)

---

## Environment Variables (`.env`)

```env
CALENDAR_ID=your-calendar-id@gmail.com
OUTPUT_DIR=/output
REFRESH_INTERVAL=1800
NGINX_PORT=8080
```

---

## Kindle Side

The Kindle must be jailbroken first (see MobileRead forums for PW3 jailbreak guide — check firmware version before connecting to WiFi to avoid auto-update blocking the jailbreak).

### `kindle/update.sh`

```sh
#!/bin/sh

PI_IP="192.168.1.x"       # Set to your Pi's local IP
PORT="8080"
IMAGE_URL="http://${PI_IP}:${PORT}/calendar.png"
IMAGE_PATH="/tmp/calendar.png"

while true; do
    wget -q "$IMAGE_URL" -O "$IMAGE_PATH"
    if [ $? -eq 0 ]; then
        eips -g "$IMAGE_PATH"
    fi
    sleep 1800
done
```

Deploy via SSH after jailbreaking. Set up via KUAL or the jailbreak's init system to run on boot.

**Kindle power settings:** Disable automatic sleep (so the script keeps running). The screen will stay on showing the last rendered image.

---

## Development & Testing

- Test the renderer locally first — run `renderer.py` standalone to produce a PNG and visually inspect it before deploying
- Use a test PNG of the correct dimensions (1072×1448) to verify `eips` rendering on the Kindle before wiring up the full pipeline
- The Pi service can be developed and tested entirely before the Kindle arrives

---

## Notes & Constraints

- **Battery:** Expect ~1–2 weeks per charge with WiFi on and 30-minute refreshes. Plan to charge weekly.
- **Static IP:** Assign the Pi a static local IP (via router DHCP reservation) so the Kindle's hardcoded URL never breaks.
- **No HTTPS needed:** This is purely local network traffic.
- **Fonts:** Bundle TTF fonts in the repo — do not rely on system fonts inside Docker.
- **Atomic writes:** Always write PNG to a temp path then rename to avoid nginx serving a partial file.
- **Timezone:** Render times in local timezone (configurable via `TZ` env var on the Docker container).
