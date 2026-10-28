"""Render the daily plan as a 3840x2160 JPEG for the Frame's Art Mode.

Layout and drawing code adapted from JustifyTechExpenses/frame-daily-plan (MIT).
A calm generated dusk gradient, three panels: date + month + to-dos, today, weather + tomorrow.
No clock: the image is static for hours. Fonts are Inter (OFL, bundled in fonts/).
"""

from __future__ import annotations

import calendar
import datetime
import io
import os
from typing import Any

from PIL import Image, ImageDraw, ImageFont

W, H = 3840, 2160
M = 180
CREAM = (255, 249, 238)
SOFT = (214, 210, 200)
DIM = (165, 162, 155)
ORANGE = (242, 150, 60)
COLORS = {"green": (120, 200, 170), "orange": ORANGE, "blue": (120, 160, 220), "red": (232, 112, 112),
          "grey": (170, 170, 170)}
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
INITIALS = "MTWTFSS"

_fonts: dict[tuple[int, str], ImageFont.FreeTypeFont] = {}


def font(size: float, weight: str = "Regular") -> ImageFont.FreeTypeFont:
    key = (round(size * 0.94), weight)  # Inter runs a little wider than the face the layout was drawn with
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(os.path.join(FONTS, f"Inter-{key[1]}.ttf"), key[0])
    return _fonts[key]


def wrap(d: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, max_w: float, max_lines: int = 2) -> list[str]:
    lines, line = [], ""
    for word in text.split(" "):
        if not word:
            continue
        trial = (line + " " + word).strip()
        if d.textlength(trial, font=f) <= max_w or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines[:max_lines]


def background() -> Image.Image:
    small = Image.new("RGB", (64, 36))
    corners = [(58, 74, 98), (92, 84, 110), (34, 52, 66), (70, 58, 72)]  # tl, tr, bl, br
    px = small.load()
    for y in range(36):
        v = y / 35
        for x in range(64):
            u = x / 63
            px[x, y] = tuple(round((corners[0][k] * (1 - u) + corners[1][k] * u) * (1 - v)
                                   + (corners[2][k] * (1 - u) + corners[3][k] * u) * v) for k in range(3))
    bg = small.resize((W, H), Image.BICUBIC)
    return Image.blend(bg, Image.new("RGB", (W, H), (12, 16, 22)), 0.25)


def panel(layer: Image.Image, box: tuple[int, int, int, int], title: str | None = None) -> None:
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(box, radius=48, fill=(14, 18, 26, 150))
    if title:
        d.text((box[0] + 70, box[1] + 50), title, font=font(86, "SemiBold"), fill=CREAM)


def events(d: ImageDraw.ImageDraw, items: list[dict[str, Any]], x: int, y: int, w: int, bottom: int,
           scale: float = 1.0) -> None:
    if not items:
        d.text((x, y), "No events", font=font(70, "Medium"), fill=DIM)
        return
    s = lambda v: round(v * scale)  # noqa: E731
    tf = font(s(74), "SemiBold")
    for ev in items:
        lines = wrap(d, ev["title"], tf, w - 60)
        need = s(80) + len(lines) * s(92) + s(50)
        if y + need > bottom:
            d.text((x, y), "… and more", font=font(64, "Medium"), fill=DIM)
            return
        past = ev.get("past")
        color = COLORS["grey"] if past else COLORS.get(ev.get("color", "green"), COLORS["green"])
        d.rounded_rectangle([x, y + 8, x + 14, y + need - s(50)], radius=7, fill=color)
        times = ev["start"] + (f" – {ev['end']}" if ev.get("end") else "")
        d.text((x + 50, y), times + ("  ·  done" if past else ""), font=font(s(62), "Medium"),
               fill=DIM if past else SOFT)
        for i, line in enumerate(lines):
            d.text((x + 50, y + s(80) + i * s(92)), line, font=tf, fill=DIM if past else CREAM)
        y += need


def week_columns(week_start: str) -> tuple[int, str, set[int]]:
    """calendar firstweekday, column initials and weekend column indexes for the month grid."""
    if week_start == "sunday":
        return 6, INITIALS[-1] + INITIALS[:-1], {0, 6}
    return 0, INITIALS, {5, 6}


def month(d: ImageDraw.ImageDraw, date: datetime.date, x: int, y: int, w: int, week_start: str) -> None:
    d.text((x, y), MONTHS[date.month - 1], font=font(72, "SemiBold"), fill=CREAM)
    cw = w / 7
    y += 110
    first, initials, weekend = week_columns(week_start)
    for i, wd in enumerate(initials):
        d.text((x + cw * i + cw / 2, y), wd, font=font(52, "Medium"), fill=DIM, anchor="mt")
    y += 80
    for week in calendar.Calendar(firstweekday=first).monthdayscalendar(date.year, date.month):
        for i, day in enumerate(week):
            if not day:
                continue
            cx, cy = x + cw * i + cw / 2, y + 34
            if day == date.day:
                d.ellipse([cx - 46, cy - 46, cx + 46, cy + 46], fill=ORANGE)
            d.text((cx, cy), str(day), font=font(58, "SemiBold" if day == date.day else "Medium"),
                   fill=CREAM if day == date.day or i not in weekend else SOFT, anchor="mm")
        y += 86


def render(day: dict[str, Any]) -> bytes:
    """day: {date, today, tomorrow, todos, weather, week_start} -> JPEG bytes."""
    date = datetime.date.fromisoformat(day["date"])
    bg = background().convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    c1, c2, c3 = (M, 1230), (1310, 2490), (2570, W - M)
    top, bottom = 560, H - M
    panel(layer, (c1[0], top, c1[1], 1300))
    panel(layer, (c1[0], 1350, c1[1], bottom), "To do")
    panel(layer, (c2[0], M, c2[1], bottom), "Today")
    panel(layer, (c3[0], M, c3[1], 820))
    panel(layer, (c3[0], 870, c3[1], bottom), "Tomorrow")
    im = Image.alpha_composite(bg, layer)
    d = ImageDraw.Draw(im)

    d.text((c1[0] + 10, M - 20), WEEKDAYS[date.weekday()], font=font(190, "Bold"), fill=CREAM)
    d.text((c1[0] + 14, M + 220), f"{MONTHS[date.month - 1]} {date.day}", font=font(96, "Medium"), fill=SOFT)
    month(d, date, c1[0] + 70, top + 50, c1[1] - c1[0] - 140, day.get("week_start") or "monday")

    y = 1505
    todos = list(day.get("todos") or [])
    if not todos:
        d.text((c1[0] + 70, y), "Nothing to do", font=font(70, "Medium"), fill=DIM)
    fits = (bottom - 40 - y) // 125
    if len(todos) > fits:
        todos = todos[:fits - 1] + [f"… and {len(todos) - fits + 1} more"]
    size, max_w = 80, c1[1] - (c1[0] + 195) - 50
    while size > 52 and any(d.textlength(t, font=font(size, "Medium")) > max_w for t in todos):
        size -= 2
    for todo in todos:
        d.rounded_rectangle([c1[0] + 70, y + 10, c1[0] + 155, y + 95], radius=18, outline=ORANGE, width=9)
        d.text((c1[0] + 195, y + (80 - size) // 2), todo, font=font(size, "Medium"), fill=CREAM)
        y += 125

    events(d, day.get("today") or [], c2[0] + 70, M + 200, c2[1] - c2[0] - 140, bottom - 40)

    wx = day.get("weather")
    if wx:
        d.text((c3[0] + 70, M + 70), f"{wx['max']}°", font=font(150, "SemiBold"), fill=CREAM)
        d.text((c3[0] + 70, M + 250), f"down to {wx['min']}° tonight", font=font(58, "Medium"), fill=SOFT)
        d.text((c3[0] + 70, M + 380), wx["text"], font=font(66, "Medium"), fill=CREAM)
        if wx.get("hint"):
            d.text((c3[0] + 70, M + 480), wx["hint"], font=font(66, "SemiBold"), fill=ORANGE)

    events(d, day.get("tomorrow") or [], c3[0] + 70, 1070, c3[1] - c3[0] - 140, bottom - 40, scale=0.82)

    out = io.BytesIO()
    im.convert("RGB").save(out, "JPEG", quality=90)
    return out.getvalue()
