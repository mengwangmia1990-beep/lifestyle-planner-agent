from prompts import system_prompt
from llm import llm
from tools import calendar_tool, todo_items_tool
import json

def get_calendar_events(date: str):
    return {
        "date": date,
        "events": [
            {"start": "12:00", "end": "13:00", "title": "Lunch"},
            {"start": "15:30", "end": "16:30", "title": "Pick up my daughter from daycare"}
        ]
    }

def get_todo_items(date: str):
    return {
        "date": date,
        "events": [
            {"task": "Study LeetCode for 1 hour", "priority": "high"},
            {"task": "Work on AI agent project for 2 hours", "priority": "high"},
            {"task": "Buy groceries", "priority": "medium"}
        ]
    }

TOOL_MAP = {
    "get_calendar_events": get_calendar_events,
    "get_todo_items": get_todo_items
}

ALL_TOOLS = calendar_tool.TOOLS + todo_items_tool.TOOLS

def run_agent(user_input: str) -> str:
    messages = []
    user_message = {
        "role": "user",
        "content": user_input
    }
    messages.append(system_prompt.system_message)
    messages.append(user_message)

    while True:
        # 让LLM决定是否要调用tool
        response = llm.call_llm(messages, ALL_TOOLS)

        if not response.tool_calls:
            return response.content

        # append assistant message
        messages.append(response)

        for tool_call in response.tool_calls:
            tool_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            tool_result = TOOL_MAP[tool_name](**args)
            print(f"tool_result: {tool_result}")

            # new role: tool --> backend 执行tool, 把结果返回LLM
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result)
            })