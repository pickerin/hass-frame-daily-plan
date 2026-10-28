import io

from PIL import Image

import render


def test_week_columns():
    assert render.week_columns("monday") == (0, "MTWTFSS", {5, 6})
    assert render.week_columns("sunday") == (6, "SMTWTFS", {0, 6})


def test_render_produces_4k_jpeg():
    day = {"date": "2026-10-27", "week_start": "sunday", "todos": ["Milk"] * 12,
           "today": [{"start": "8:00 am", "end": "9:00 am", "title": "A very long event title that wraps onto two lines " * 3, "color": "blue", "past": True}],
           "tomorrow": [], "weather": {"max": 61, "min": 45, "text": "Cloudy", "hint": "Bring a jacket"}}
    data = render.render(day)
    im = Image.open(io.BytesIO(data))
    assert im.size == (3840, 2160) and im.format == "JPEG"
