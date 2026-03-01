import os
import time
import logging

from fetcher import fetch_events
from renderer import render_image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/output")
REFRESH_INTERVAL = int(os.environ.get("REFRESH_INTERVAL", 1800))


def run_once():
    output_path = os.path.join(OUTPUT_DIR, "calendar.png")
    log.info("Fetching events…")
    events = fetch_events()
    log.info("Fetched %d event(s). Rendering…", len(events))
    render_image(events, output_path)
    log.info("Saved to %s", output_path)


if __name__ == "__main__":
    while True:
        try:
            run_once()
        except Exception:
            log.exception("Error during update — will retry next cycle")
        log.info("Sleeping %ds…", REFRESH_INTERVAL)
        time.sleep(REFRESH_INTERVAL)
