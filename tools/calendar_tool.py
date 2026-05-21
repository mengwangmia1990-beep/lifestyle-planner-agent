def get_calendar_events(date: str):
    return {
        "date": date,
        "events": [
            {
                "start": "12:00", 
                "end": "13:00", 
                "title": "Lunch"
            },
            {
                "start": "15:30", 
                "end": "16:30", 
                "title": "Pick up my daughter from daycare"
            }
        ]
    }

SCHEMA = {
        "type": "function",
        "function": {
            "name": "get_calendar_events",
            "description": "Get user's calendar events for a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format"
                    }
                },
                "required": ["date"],
                "additionalProperties": False
            }
        }
    }

