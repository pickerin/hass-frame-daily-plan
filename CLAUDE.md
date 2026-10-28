# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

HACS integration `frame_daily_plan`: renders a daily plan (calendars, to-dos, weather) as a 4K JPEG and
shows it in Art Mode on a Samsung The Frame, then restores the artwork and slideshow. Adapted from
JustifyTechExpenses/frame-daily-plan (MIT); credit stays in README and THIRD_PARTY_NOTICES.

## Layout (`custom_components/frame_daily_plan/`)

- `tv.py`: sync Frame client on `samsungtvws.art.SamsungTVArt` (the version HA core ships, >=3.0.6). One
  connection per call. `show_image` / `restore` are the whole transaction and own the state dict
  (`plan_ids`, `restore_id`, `slideshow`). Only images we uploaded are ever deleted. No HA imports.
- `logic.py`: pure conversion of `calendar.get_events`, `todo.get_items`, `weather.get_forecasts` responses
  into the render dict. Wear hints judge in Celsius. No HA imports.
- `render.py`: Pillow renderer, English only, generated gradient background, Inter fonts bundled. No HA imports.
- `plan.py`: calls the HA services and the renderer (executor).
- `coordinator.py`: polls Art Mode every 2 min, holds `FrameTV`, the `Store`-persisted state and the last JPEG.
- `config_flow.py`: host, then pairing via `async_show_progress` (TV Allow prompt, 120 s). Options flow for
  calendars / todo lists / weather / clock / week start; options are read at render time, no reload needed.
- Platforms: `switch` (art_mode), `button` (show_plan, restore_artwork), `image` (plan). Services in `__init__`.

## Rules

- Never send `KEY_POWER` to a Frame to reach Art Mode: a short press toggles. Use `set_artmode`.
- Read slideshow status *before* `select_image`; selecting ends a "Display All" slideshow and the TV then reports off.
- All `samsungtvws` calls go through `hass.async_add_executor_job`.
- Tests (`tests/`) run without HA: `python -m pytest tests` in a venv with samsungtvws, pillow, pytest.
- Keep `strings.json` and `translations/en.json` identical.
