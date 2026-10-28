"""Constants for the Frame Daily Plan integration."""

DOMAIN = "frame_daily_plan"

CONF_TOKEN = "token"
CONF_CALENDARS = "calendars"
CONF_TODO_LISTS = "todo_lists"
CONF_WEATHER = "weather_entity"
CONF_CLOCK = "clock"
CONF_WEEK_START = "week_start"

DEFAULT_CLOCK = "24"
DEFAULT_WEEK_START = "monday"

CLIENT_NAME = "Frame Daily Plan"  # shown in the TV's "allow this device?" prompt
PAIR_TIMEOUT = 120  # seconds the TV gives you to press Allow
TV_TIMEOUT = 30
UPDATE_INTERVAL_SECONDS = 120

SERVICE_SHOW_PLAN = "show_plan"
SERVICE_RESTORE_ARTWORK = "restore_artwork"

STORAGE_VERSION = 1

# One colour per configured calendar, in order.
PALETTE = ["green", "blue", "orange", "red", "grey"]
