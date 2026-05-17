def get_todo_items(date: str):
    return {
        "date": date,
        "events": [
            {"task": "Study LeetCode for 2 hour", "priority": "high"},
            {"task": "Work on AI agent project for 2 hours", "priority": "high"},
            {"task": "Buy groceries", "priority": "medium"}
        ]
    }

SCHEMA = {
        "type": "function",
        "function": {
            "name": "get_todo_items",
            "description": "Get user's to do items for a given date. Each item has priority from low, medium to high.",
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