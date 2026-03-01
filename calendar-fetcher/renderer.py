import os
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# Kindle PW3 native resolution
WIDTH = 1072
HEIGHT = 1448

FONTS_DIR = Path(__file__).parent / "fonts"

# Padding / layout constants
MARGIN = 60
DATE_TOP = 60
DIVIDER_PADDING = 40
EVENT_LINE_PADDING = 18
FOOTER_BOTTOM_MARGIN = 40


def _font(bold=False, size=40):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(str(FONTS_DIR / name), size)


def _draw_divider(draw, y):
    draw.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill=0, width=3)
    return y


def render_image(events, output_path):
    img = Image.new("L", (WIDTH, HEIGHT), color=255)
    draw = ImageDraw.Draw(img)

    now = datetime.now()

    # --- Date block ---
    day_name = now.strftime("%A")
    date_str = now.strftime("%-d %B %Y")

    font_day = _font(bold=True, size=120)
    font_date = _font(bold=False, size=72)

    y = DATE_TOP
    draw.text((MARGIN, y), day_name, font=font_day, fill=0)
    y += font_day.getbbox(day_name)[3] + 20
    draw.text((MARGIN, y), date_str, font=font_date, fill=0)
    y += font_date.getbbox(date_str)[3] + DIVIDER_PADDING

    # --- Divider ---
    _draw_divider(draw, y)
    y += DIVIDER_PADDING

    # --- Event list ---
    font_event_time = _font(bold=True, size=44)
    font_event_title = _font(bold=False, size=44)
    font_no_events = _font(bold=False, size=48)

    if not events:
        draw.text((MARGIN, y), "No upcoming events", font=font_no_events, fill=0)
    else:
        for event in events:
            if event["all_day"]:
                time_label = "All day"
            else:
                start = event["start"]
                time_label = start.strftime("%-I:%M %p").lstrip("0")

            summary = event["summary"]

            # Time label
            time_bbox = font_event_time.getbbox(time_label)
            time_w = time_bbox[2]
            draw.text((MARGIN, y), time_label, font=font_event_time, fill=0)

            # Title — indented after time
            title_x = MARGIN + time_w + 24
            available_w = WIDTH - title_x - MARGIN
            title = _truncate_text(draw, summary, font_event_title, available_w)
            draw.text((title_x, y), title, font=font_event_title, fill=0)

            row_h = max(
                font_event_time.getbbox(time_label)[3],
                font_event_title.getbbox(title)[3],
            )
            y += row_h + EVENT_LINE_PADDING

            if y > HEIGHT - 150:
                break

    # --- Footer ---
    font_footer = _font(bold=False, size=36)
    updated_str = f"Updated: {now.strftime('%H:%M')}"
    footer_bbox = font_footer.getbbox(updated_str)
    footer_y = HEIGHT - footer_bbox[3] - FOOTER_BOTTOM_MARGIN
    draw.text((MARGIN, footer_y), updated_str, font=font_footer, fill=0)

    # Atomic write
    tmp_path = output_path + ".tmp"
    img.save(tmp_path, format="PNG")
    os.replace(tmp_path, output_path)


def _truncate_text(draw, text, font, max_width):
    if font.getbbox(text)[2] <= max_width:
        return text
    ellipsis = "…"
    while text:
        candidate = text + ellipsis
        if font.getbbox(candidate)[2] <= max_width:
            return candidate
        text = text[:-1]
    return ellipsis
