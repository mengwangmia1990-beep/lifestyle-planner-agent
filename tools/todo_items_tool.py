
TOOLS = [
    {
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
]