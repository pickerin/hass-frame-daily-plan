import datetime
import zoneinfo

import logic

TZ = zoneinfo.ZoneInfo("America/Detroit")
NOW = datetime.datetime(2026, 10, 27, 9, 0, tzinfo=TZ)
TODAY = NOW.date()
RESP = {
    "calendar.family": {"events": [
        {"start": "2026-10-27", "end": "2026-10-28", "summary": "Field trip"},
        {"start": "2026-10-27T08:00:00-04:00", "end": "2026-10-27T08:30:00-04:00", "summary": "Breakfast"},
        {"start": "2026-10-27T15:30:00-04:00", "end": "2026-10-27T16:30:00-04:00", "summary": "Swim"},
        {"start": "2026-10-26T20:00:00-04:00", "end": "2026-10-27T00:00:00-04:00", "summary": "Ends at midnight"},
        {"start": "2026-10-28T09:00:00-04:00", "end": "2026-10-28T10:00:00-04:00", "summary": "Dentist"},
        {"start": "2026-10-26", "end": "2026-10-29", "summary": "Trip"},
    ]},
    "calendar.work": {"events": [{"start": "2026-10-27T12:00:00-04:00", "end": "2026-10-27T13:00:00-04:00", "summary": "Lunch"}]},
}
CALS = ["calendar.family", "calendar.work"]


def test_fmt_time():
    t = datetime.datetime(2026, 1, 1, 14, 5)
    assert logic.fmt_time(t, "12") == "2:05 pm"
    assert logic.fmt_time(datetime.datetime(2026, 1, 1, 0, 30), "12") == "12:30 am"
    assert logic.fmt_time(t, "24") == "14:05"


def test_events_today_sorted_and_colored():
    ev = logic.events_for_day(RESP, CALS, TODAY, TZ, NOW, "12", ["green", "blue"])
    assert [e["title"] for e in ev] == ["Field trip", "Trip", "Breakfast", "Lunch", "Swim"]
    assert ev[2]["start"] == "8:00 am" and ev[2]["end"] == "8:30 am" and ev[2]["past"] is True
    assert ev[4]["past"] is False
    assert ev[3]["color"] == "blue" and ev[0]["color"] == "green"


def test_events_tomorrow():
    ev = logic.events_for_day(RESP, CALS, TODAY + datetime.timedelta(days=1), TZ, NOW, "24", ["green"])
    assert [e["title"] for e in ev] == ["Trip", "Dentist"]
    assert ev[1]["start"] == "09:00"


def test_todos():
    resp = {"todo.house": {"items": [{"summary": "Milk", "status": "needs_action"}, {"summary": "Done", "status": "completed"},
                                     {"summary": "Milk", "status": "needs_action"}]}}
    assert logic.todos(resp, ["todo.house", "todo.missing"]) == ["Milk"]


def test_weather_fahrenheit_hints_in_celsius():
    wx = logic.weather({"condition": "cloudy", "temperature": 50.0, "templow": 32.0, "precipitation_probability": 35}, "°F")
    assert (wx["max"], wx["min"]) == (50, 32)
    assert wx["hint"] == logic.HINT_COLD and wx["text"] == "Cloudy, 35 % rain"
    assert logic.weather({"condition": "sunny", "temperature": 22, "templow": 14}, "°C")["hint"] is None
    assert logic.weather(None, "°C") is None
