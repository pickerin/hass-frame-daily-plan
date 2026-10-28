"""Pure plan assembly: turns Home Assistant service responses into the dict render() draws.

No Home Assistant imports here, so it is unit-testable as plain Python.
"""

from __future__ import annotations

import datetime
from typing import Any

HINT_RAIN = "Take an umbrella"
HINT_COLD = "Wear a warm coat"
HINT_COOL = "Bring a jacket"
HINT_HOT = "Drink plenty, wear sunscreen"

CONDITIONS = {
    "clear-night": "Clear", "cloudy": "Cloudy", "exceptional": "Exceptional", "fog": "Fog", "hail": "Hail",
    "lightning": "Thunderstorms", "lightning-rainy": "Thunderstorms", "partlycloudy": "Partly cloudy",
    "pouring": "Heavy rain", "rainy": "Rain", "snowy": "Snow", "snowy-rainy": "Sleet", "sunny": "Sunny",
    "windy": "Windy", "windy-variant": "Windy",
}


def fmt_time(dt: datetime.datetime, clock: str) -> str:
    if clock == "12":
        return dt.strftime("%I:%M %p").lstrip("0").replace("AM", "am").replace("PM", "pm")
    return dt.strftime("%H:%M")


def _parse(value: str, tz: datetime.tzinfo) -> datetime.datetime | datetime.date:
    """calendar.get_events gives ISO strings: datetimes for timed events, dates for all-day ones."""
    if len(value) == 10:
        return datetime.date.fromisoformat(value)
    return datetime.datetime.fromisoformat(value).astimezone(tz)


def events_for_day(response: dict[str, Any], calendars: list[str], day: datetime.date, tz: datetime.tzinfo,
                   now: datetime.datetime, clock: str, palette: list[str]) -> list[dict[str, Any]]:
    """Events touching `day` from a calendar.get_events response, sorted, all-day first."""
    out = []
    for i, entity_id in enumerate(calendars):
        color = palette[i % len(palette)]
        for ev in (response.get(entity_id) or {}).get("events") or []:
            title = (ev.get("summary") or "").strip()
            if not title:
                continue
            start = _parse(ev["start"], tz)
            end = _parse(ev["end"], tz) if ev.get("end") else None
            if isinstance(start, datetime.datetime):
                end_dt = end or start
                last_day = (end_dt - datetime.timedelta(microseconds=1)).date() if end and end != start else end_dt.date()
                if not start.date() <= day <= last_day:
                    continue
                if start.date() < day:  # started on an earlier day: show as all-day
                    item = {"sort": "00:00", "start": "All day", "end": None, "end_dt": end_dt}
                else:
                    item = {"sort": start.strftime("%H:%M"), "start": fmt_time(start, clock),
                            "end": fmt_time(end, clock) if end and end != start else None, "end_dt": end_dt}
            else:
                if not start <= day < (end or start + datetime.timedelta(days=1)):  # all-day, end exclusive
                    continue
                item = {"sort": "00:00", "start": "All day", "end": None, "end_dt": None}
            item.update({"title": title, "color": color,
                         "past": item["end_dt"] is not None and item["end_dt"] <= now})
            out.append(item)
    out.sort(key=lambda e: e["sort"])
    return out


def todos(response: dict[str, Any], lists: list[str]) -> list[str]:
    """Open items from a todo.get_items response, de-duplicated, in order."""
    seen, out = set(), []
    for entity_id in lists:
        for item in (response.get(entity_id) or {}).get("items") or []:
            text = (item.get("summary") or "").strip()
            if text and item.get("status", "needs_action") == "needs_action" and text not in seen:
                seen.add(text)
                out.append(text)
    return out


def weather(forecast: dict[str, Any] | None, unit: str) -> dict[str, Any] | None:
    """Today's daily forecast entry -> what the panel shows. Hints are judged in Celsius."""
    if not forecast or forecast.get("temperature") is None:
        return None
    tmax = float(forecast["temperature"])
    tmin = float(forecast.get("templow") if forecast.get("templow") is not None else tmax)
    rain = float(forecast.get("precipitation_probability") or 0)
    to_c = (lambda t: (t - 32) * 5 / 9) if unit.endswith("F") else (lambda t: t)
    cmax, cmin = to_c(tmax), to_c(tmin)
    if rain >= 50:
        hint = HINT_RAIN
    elif cmax < 12:
        hint = HINT_COLD
    elif cmax < 18 or cmin < 12:
        hint = HINT_COOL
    elif cmax >= 28:
        hint = HINT_HOT
    else:
        hint = None
    text = CONDITIONS.get(str(forecast.get("condition")), str(forecast.get("condition") or "").replace("-", " ").capitalize())
    if 30 <= rain < 50:
        text += f", {round(rain)} % rain"
    return {"max": round(tmax), "min": round(tmin), "text": text, "hint": hint}
