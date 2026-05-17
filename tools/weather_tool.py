def get_weather(location: str, date: str):
    return {
        "location": location,
        "date": date,
        "forecast": "rainy",
        "temperature": "52°F",
        "suggestion": "Prefer indoor activities or bring an umbrella."
    }

SCHEMA = {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather for given location and date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Location, e.g. seattle, wa"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format"
                    }
                },
                "required": ["date"],
                "required": ["location"],
                "additionalProperties": False
            }
        }
    }