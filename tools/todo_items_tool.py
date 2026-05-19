def get_todo_items(date: str):
    return {
        "date": date,
        "todos": [
            {
                "todo_id": "todo_1",
                "title": "Study LeetCode", 
                "duration_minutes": 120
            },
            {
                "todo_id": "todo_2",
                "title": "Work on AI agent project", 
                "duration_minutes": 120
            },
            {
                "todo_id": "todo_3",
                "title": "Buy groceries", 
                "duration_minutes": 30
            }
        ]
    }

SCHEMA = {
        "type": "function",
        "function": {
            "name": "get_todo_items",
            "description": "Get user's todo items for a given date. Each item has priority from low, medium to high.",
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