from prompts import system_prompt
from llm import llm
from tools import tool_registry
import json
import config
from datetime import datetime


def parse_time(time_str: str):
    time = datetime.strptime(time_str, "%H:%M")
    return time


def validate_interval(task: dict) -> bool:
    try:
        start_time = parse_time(task["start"])
        end_time = parse_time(task["end"])
        return start_time < end_time
    except Exception as e:
        print("Error", e)
        return False


def validate_overlap(tasks):
    intervals = []
    try:
        for task in tasks:
            start_time = parse_time(task["start"])
            end_time = parse_time(task["end"])
            intervals.append([start_time, end_time])
        
        # sort intervals by start_time
        intervals.sort(key=lambda x:x[0])

        for i in range(len(intervals)-1):
            if intervals[i][1] > intervals[i+1][0]:
                return False # has overlap --> validation didn't pass

        return True # no overlap --> pass validation
    except Exception as e:
        print("Error", e)
        return False


def validate(plan):
    if not plan or "tasks" not in plan or not plan["tasks"]:
        return False
    
    tasks = plan["tasks"]
    for task in tasks:
        if not validate_interval(task):
            return False
    
    if not validate_overlap(tasks):
        return False
    
    return True


def run_agent(user_input: str) -> str:
    messages = []
    user_message = {
        "role": "user",
        "content": user_input
    }
    messages.append(system_prompt.system_message)
    messages.append(user_message)

    loop_count = 0

    while loop_count < config.MAX_LOOP_COUNT:
        loop_count += 1

        response = llm.call_llm(messages, tool_registry.TOOLS)

        # stop tool calling
        if not response.tool_calls:
            try:
                plan = json.loads(response.content)
            except json.JSONDecodeError:
                return ""
            
            if validate(plan):
                return response.content
            else:
                return ""

        # assistant role message: e.g. LLM decides to call which tool, and let backend know
        messages.append(response)

        for tool_call in response.tool_calls:
            tool_name = tool_call.function.name
            if tool_name not in tool_registry.TOOL_MAP:
                return f"Unknown tool name: {tool_name}"
            
            args = json.loads(tool_call.function.arguments)

            tool_result = tool_registry.TOOL_MAP[tool_name](**args)
            print(f"tool_result: {tool_result}")

            # new role: tool --> backend 执行tool, 把结果返回LLM
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result)
            })
    
    # fallback return when reaches max loop
    return "Sorry, I couldn't complete the request within the allowed number of steps."