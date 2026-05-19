from prompts import system_prompt
from llm import llm
from tools import tool_registry
import json
import config
from datetime import datetime
from models.validation_models import ValidationResult

def parse_time(time_str: str):
    time = datetime.strptime(time_str, "%H:%M")
    return time


def validate_interval(task: dict) -> ValidationResult:
    try:
        start_time = parse_time(task["start"])
        end_time = parse_time(task["end"])

        if start_time >= end_time:
            return ValidationResult(
                valid=False,
                errors=["invalid interval"]
            )
        
        return ValidationResult(
            valid=True,
            errors=[]
        )

    except Exception as e:
        print("Error", e)
        return ValidationResult(
            valid=False,
            errors=[f"failed to validate interval. Error {e}"]
        )


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
                # has overlap --> validation didn't pass
                return ValidationResult(
                    valid=False,
                    errors=[f"detected overlap in task interval. start {start_time}, end {end_time}"]
                )
            
        # no overlap --> pass validation
        return ValidationResult(
            valid=True,
            errors=[]
        )
    except Exception as e:
        print("Error", e)
        return ValidationResult(
            valid=False,
            errors=[f"failed to validate interval overlap. Error {e}"]
        )


def validate_duration(tasks, tool_results):
    # aggregate by todo_id, construct a dict for actual tasks
    actual_todo_duration = {}
    for task in tasks:
        todo_id = task.get("todo_id")
        if not todo_id:
            continue

        todo_id = task["todo_id"]
        start_time = parse_time(task["start"])
        end_time = parse_time(task["end"])
        duration = (end_time - start_time).total_seconds() / 60

        if todo_id not in actual_todo_duration:
            actual_todo_duration[todo_id] = 0
        actual_todo_duration[todo_id] += duration

    # aggregate by todo_id, construct a dict for expected todo items
    expected_todo_duration = {}
    tool_name = "get_todo_items"
    
    for todo in tool_results[tool_name]["todos"]:
        id = todo["todo_id"]
        expected_todo_duration[id] = todo["duration_minutes"]

    # compares two important metrics:
    # 1. all todo items are included in the task plan
    # 2. each todo duration in the task plan meets user's request
    for todo_id, expected_duration in expected_todo_duration.items():
        actual_duration = actual_todo_duration.get(todo_id, 0)
        if actual_duration != expected_duration:
            return ValidationResult(
                valid=False,
                errors=[f"task {todo_id} duration {actual_duration} does not match with expected duration {expected_duration}"]
            )

    return ValidationResult(
        valid=True,
        errors=[]
    )

def validate(plan, tool_results):
    if not plan or "tasks" not in plan or not plan["tasks"]:
        return ValidationResult(
            valid=False,
            errors=["plan invalid"]
        )
    
    tasks = plan["tasks"]
    for task in tasks:
        interval_result = validate_interval(task)
        if not interval_result.valid:
            return interval_result
    
    overlap_result = validate_overlap(tasks)
    if not overlap_result.valid:
        return overlap_result
    
    duration_result = validate_duration(tasks, tool_results)
    if not duration_result.valid:
        return duration_result
    
    return ValidationResult(
        valid=True,
        errors=[]
    )


def run_agent(user_input: str) -> str:
    messages = []
    user_message = {
        "role": "user",
        "content": user_input
    }
    messages.append(system_prompt.system_message)
    messages.append(user_message)

    loop_count = 0
    tool_results = {} # dict: {tool_name:tool_result}

    while loop_count < config.MAX_LOOP_COUNT:
        loop_count += 1

        response = llm.call_llm(messages, tool_registry.TOOLS)

        # stop tool calling
        if not response.tool_calls:
            try:
                plan = json.loads(response.content)
            except json.JSONDecodeError:
                return ""
            
            validation_result = validate(plan, tool_results)
            if validation_result.valid:
                return response.content
            else:
                return validation_result

        # assistant role message: e.g. LLM decides to call which tool, and let backend know
        messages.append(response)

        for tool_call in response.tool_calls:
            tool_name = tool_call.function.name
            if tool_name not in tool_registry.TOOL_MAP:
                return f"Unknown tool name: {tool_name}"
            
            args = json.loads(tool_call.function.arguments)

            tool_result = tool_registry.TOOL_MAP[tool_name](**args)
            
            # save tool_result for backend validation
            tool_results[tool_name] = tool_result

            # new role: tool --> backend 执行tool, 把结果返回LLM
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result)
            })
    
    # fallback return when reaches max loop
    return "Sorry, I couldn't complete the request within the allowed number of steps."