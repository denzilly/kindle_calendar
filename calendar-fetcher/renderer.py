import os
from datetime import datetime, date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1072
HEIGHT = 1448

FONTS_DIR = Path(__file__).parent / "fonts"

# Grayscale palette (0=black, 255=white)
BG = 255
BLACK = 0
GRAY = 155          # day names row, outside-current-week numbers, footer
GRID_LINE = 190
TODAY_FILL = 0
TODAY_TEXT = 255
ALLDAY_FILL = 70    # dark bar for all-day events
ALLDAY_TEXT = 255
DOT_FILL = 0

NUM_WEEKS = 3
MAX_ALLDAY_TRACKS = 3


def _font(bold=False, size=40):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(str(FONTS_DIR / name), size)


def _w(font, text):
    bb = font.getbbox(text)
    return bb[2] - bb[0]


def _h(font, text="Ag"):
    bb = font.getbbox(text)
    return bb[3] - bb[1]


def _truncate(font, text, max_w):
    if _w(font, text) <= max_w:
        return text
    while text:
        candidate = text + "…"
        if _w(font, candidate) <= max_w:
            return candidate
        text = text[:-1]
    return "…"


def render_image(events, weather, output_path):
    today = date.today()
    now = datetime.now()

    # 3-week rolling grid starting on the Sunday of the current week
    dow = (today.weekday() + 1) % 7  # Sun=0, Mon=1, …, Sat=6
    grid_start = today - timedelta(days=dow)
    grid_dates = [grid_start + timedelta(days=i) for i in range(NUM_WEEKS * 7)]

    img = Image.new("L", (WIDTH, HEIGHT), color=BG)
    draw = ImageDraw.Draw(img)

    # ------------------------------------------------------------------ #
    # Header                                                               #
    # ------------------------------------------------------------------ #
    f_weekday = _font(bold=True, size=78)
    f_date = _font(bold=False, size=52)
    f_weather = _font(bold=False, size=42)

    y = 22
    # "Monday"
    weekday_str = today.strftime("%A")
    draw.text((WIDTH // 2 - _w(f_weekday, weekday_str) // 2, y), weekday_str,
              font=f_weekday, fill=BLACK)
    y += _h(f_weekday) + 10

    # "2 March 2026"
    date_str = today.strftime("%-d %B %Y")
    draw.text((WIDTH // 2 - _w(f_date, date_str) // 2, y), date_str,
              font=f_date, fill=BLACK)
    y += _h(f_date) + 12

    # Weather line
    if weather:
        weather_str = f"{weather['temp_c']}°C  ·  {weather['precip_pct']}% rain"
    else:
        weather_str = ""
    if weather_str:
        draw.text((WIDTH // 2 - _w(f_weather, weather_str) // 2, y), weather_str,
                  font=f_weather, fill=GRAY)
        y += _h(f_weather) + 18
    else:
        y += 6

    # Thin divider
    draw.line([(40, y), (WIDTH - 40, y)], fill=GRID_LINE, width=1)
    y += 16

    # ------------------------------------------------------------------ #
    # Day names row                                                        #
    # ------------------------------------------------------------------ #
    f_dayname = _font(bold=True, size=22)
    day_names = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
    col_x = [c * WIDTH // 7 for c in range(7)] + [WIDTH]
    dn_y = y
    for c, name in enumerate(day_names):
        x0, x1 = col_x[c], col_x[c + 1]
        draw.text((x0 + (x1 - x0 - _w(f_dayname, name)) // 2, dn_y + 8),
                  name, font=f_dayname, fill=GRAY)
    dayname_h = _h(f_dayname) + 20
    y += dayname_h

    # ------------------------------------------------------------------ #
    # Grid                                                                 #
    # ------------------------------------------------------------------ #
    grid_top = y
    draw.line([(0, grid_top), (WIDTH, grid_top)], fill=GRID_LINE, width=1)

    cell_h = (HEIGHT - grid_top - 30) // NUM_WEEKS

    f_daynum = _font(bold=True, size=26)
    f_allday = _font(bold=True, size=17)
    f_timed = _font(bold=False, size=17)
    f_footer = _font(bold=False, size=20)

    DAYNUM_H = _h(f_daynum) + 8
    ALLDAY_BAR_H = _h(f_allday) + 6
    TIMED_LINE_H = _h(f_timed) + 4

    # Helper: all-day spanning bars for a given week row
    def allday_bars_for_row(row):
        wk_start = grid_dates[row * 7]
        wk_end = grid_dates[row * 7 + 6]
        bars = []
        for ev in events:
            if not ev["all_day"]:
                continue
            s = ev["start"].date() if isinstance(ev["start"], datetime) else ev["start"]
            e = ev["end"].date() if isinstance(ev["end"], datetime) else ev["end"]
            if s > wk_end or e <= wk_start:
                continue
            bars.append({
                "ev": ev,
                "cs": max(0, (s - wk_start).days),        # col start (inclusive)
                "ce": min(7, (e - wk_start).days),         # col end   (exclusive)
            })
        # Greedy track assignment
        bars.sort(key=lambda b: (b["cs"], -(b["ce"] - b["cs"])))
        tracks = []
        for bar in bars:
            for t, tend in enumerate(tracks):
                if bar["cs"] >= tend:
                    bar["track"] = t
                    tracks[t] = bar["ce"]
                    break
            else:
                bar["track"] = len(tracks)
                tracks.append(bar["ce"])
        return bars

    for row in range(NUM_WEEKS):
        ry = grid_top + row * cell_h

        if row > 0:
            draw.line([(0, ry), (WIDTH, ry)], fill=GRID_LINE, width=1)

        bars = allday_bars_for_row(row)
        visible_tracks = min(MAX_ALLDAY_TRACKS,
                             max((b["track"] + 1 for b in bars), default=0))
        timed_top = ry + DAYNUM_H + visible_tracks * (ALLDAY_BAR_H + 2) + 3

        # Day numbers & vertical separators
        for col in range(7):
            if col > 0:
                draw.line([(col_x[col], ry), (col_x[col], ry + cell_h)],
                          fill=GRID_LINE, width=1)
            d = grid_dates[row * 7 + col]
            txt = str(d.day)
            tx, ty = col_x[col] + 7, ry + 5
            if d == today:
                tw, th = _w(f_daynum, txt), _h(f_daynum, txt)
                r = max(tw, th) // 2 + 5
                cx, cy = tx + tw // 2, ty + th // 2
                draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=TODAY_FILL)
                draw.text((tx, ty), txt, font=f_daynum, fill=TODAY_TEXT)
            else:
                draw.text((tx, ty), txt, font=f_daynum, fill=BLACK)

        # All-day spanning bars
        for bar in bars:
            if bar["track"] >= MAX_ALLDAY_TRACKS:
                continue
            bx0 = col_x[bar["cs"]] + 2
            bx1 = col_x[bar["ce"]] - 2
            by0 = ry + DAYNUM_H + bar["track"] * (ALLDAY_BAR_H + 2)
            by1 = by0 + ALLDAY_BAR_H
            draw.rectangle([(bx0, by0), (bx1, by1)], fill=ALLDAY_FILL)
            title = _truncate(f_allday, bar["ev"]["summary"], bx1 - bx0 - 6)
            draw.text((bx0 + 3, by0 + 2), title, font=f_allday, fill=ALLDAY_TEXT)

        # Timed events per cell
        for col in range(7):
            d = grid_dates[row * 7 + col]
            x0, x1 = col_x[col], col_x[col + 1]
            cell_w = x1 - x0
            day_events = [e for e in events
                          if not e["all_day"] and e["start"].date() == d]
            ey = timed_top
            for ev in day_events:
                if ey + TIMED_LINE_H > ry + cell_h - 4:
                    break
                dot_r = 3
                dot_cy = ey + TIMED_LINE_H // 2
                draw.ellipse(
                    [(x0 + 8 - dot_r, dot_cy - dot_r),
                     (x0 + 8 + dot_r, dot_cy + dot_r)],
                    fill=DOT_FILL,
                )
                t_str = ev["start"].strftime("%-I:%M%p").lower().lstrip("0")
                line = _truncate(f_timed, f"{t_str} {ev['summary']}", cell_w - 18)
                draw.text((x0 + 16, ey), line, font=f_timed, fill=BLACK)
                ey += TIMED_LINE_H

    # ------------------------------------------------------------------ #
    # Footer                                                               #
    # ------------------------------------------------------------------ #
    updated = f"Updated: {now.strftime('%H:%M')}"
    draw.text((WIDTH - _w(f_footer, updated) - 10, HEIGHT - 26),
              updated, font=f_footer, fill=GRAY)

    # Atomic write
    tmp = output_path + ".tmp"
    img.save(tmp, format="PNG")
    os.replace(tmp, output_path)
