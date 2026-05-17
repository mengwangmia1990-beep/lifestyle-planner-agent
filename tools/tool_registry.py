from tools.calendar_tool import SCHEMA as CALENDAR_SCHEMA, get_calendar_events
from tools.todo_items_tool import SCHEMA as TODO_ITEMS_SCHEMA, get_todo_items
from tools.weather_tool import SCHEMA as WEATHER_SCHEMA, get_weather

TOOLS = [CALENDAR_SCHEMA, TODO_ITEMS_SCHEMA, WEATHER_SCHEMA]

TOOL_MAP = {
    "get_calendar_events": get_calendar_events,
    "get_todo_items": get_todo_items,
    "get_weather": get_weather
}