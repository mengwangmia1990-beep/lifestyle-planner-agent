from prompts import system_prompt, repair_prompt
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
        todo_id = task.get("todo_id")
        if not todo_id:
            return ValidationResult(
            valid=False,
            errors=["Cannot extract todo_id of given task."]
        )

        errors = []

        if start_time >= end_time:
            errors.append(f"invalid interval for task {todo_id} start: {start_time} end: {end_time}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )

    except Exception as e:
        print("Error", e)
        return ValidationResult(
            valid=False,
            errors=[f"failed to validate interval. Error {e}"]
        )


def validate_overlap(tasks):
    intervals = []
    errors = []

    try:
        for task in tasks:
            todo_id = task.get("todo_id")
            if not todo_id:
                errors.append("Failed to extract todo_id.")
                continue
    
            start_time = parse_time(task["start"])
            end_time = parse_time(task["end"])

            intervals.append({
                "todo_id": todo_id,
                "title": task.get("title", ""),
                "start": start_time,
                "end": end_time,
            })
        
        # sort intervals by start_time
        intervals.sort(key=lambda x:x["start"])

        for i in range(len(intervals)-1):
            cur = intervals[i]
            nxt = intervals[i + 1]

            if cur["end"] > nxt["start"]:
                # has overlap --> validation didn't pass
                errors.append(
                    f"detected overlap between task {cur['todo_id']} "
                    f"({cur['start'].strftime('%H:%M')}-{cur['end'].strftime('%H:%M')}) "
                    f"and task {nxt['todo_id']} "
                    f"({nxt['start'].strftime('%H:%M')}-{nxt['end'].strftime('%H:%M')})"
                )
            
        # no overlap --> pass validation
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
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
    errors = []
    for todo_id, expected_duration in expected_todo_duration.items():
        actual_duration = actual_todo_duration.get(todo_id, 0)
        if actual_duration != expected_duration:
            duration_error = f"task {todo_id} duration {actual_duration} does not match with expected duration {expected_duration}"
            errors.append(duration_error)

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors
    )

def validate_calendar_conflict(tasks, tool_results):
    errors = []
    events = tool_results.get("get_calendar_events", {}).get("events", [])

    try:
        for task in tasks:
            task_start = parse_time(task["start"])
            task_end = parse_time(task["end"])
            task_id = task.get("todo_id", "unknown")
            task_title = task.get("title", "")

            for event in events:
                event_start = parse_time(event["start"])
                event_end = parse_time(event["end"])
                event_title = event.get("title", "")

                if task_start < event_end and task_end > event_start:
                    # task has conflict with calendar event
                    errors.append(
                        f"task {task_id} ({task_title}) "
                        f"{task['start']}-{task['end']} conflicts with calendar event "
                        f"{event_title} {event['start']}-{event['end']}"
                    )
        return ValidationResult(
            valid=len(errors)==0,
            errors=errors
        )
    except Exception as e:
        return ValidationResult(
            valid=False,
            errors=[f"failed to validate calendar conflicts. Error {e}"]
        )


def validate(plan, tool_results):
    errors = []
    
    if not plan or "tasks" not in plan or not plan["tasks"]:
        return ValidationResult(
            valid=False,
            errors=["plan invalid"]
        )

    tasks = plan["tasks"]
    for task in tasks:
        interval_result = validate_interval(task)
        if not interval_result.valid:
            errors.extend(interval_result.errors)
    
    overlap_result = validate_overlap(tasks)
    if not overlap_result.valid:
        errors.extend(overlap_result.errors)

    calendar_conflict_result = validate_calendar_conflict(tasks, tool_results)
    if not calendar_conflict_result.valid:
        errors.extend(calendar_conflict_result.errors)
    
    duration_result = validate_duration(tasks, tool_results)
    if not duration_result.valid:
        errors.extend(duration_result.errors)

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors
    )


def get_candidate_plan(user_input):
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
            return response.content, tool_results

        # assistant role message: e.g. LLM decides to call which tool, and let backend know
        messages.append(response)

        for tool_call in response.tool_calls:
            tool_name = tool_call.function.name
            if tool_name not in tool_registry.TOOL_MAP:
                return f"Unknown tool name: {tool_name}", tool_results
            
            args = json.loads(tool_call.function.arguments)

            tool_result = tool_registry.TOOL_MAP[tool_name](**args)
            
            # save tool_result for backend validation
            tool_results[tool_name] = tool_result

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result)
            })
    
    # fallback return when reaches max loop
    return "Sorry, I couldn't complete the request within the allowed number of steps.", tool_results


def repair_plan(plan, tool_results):
    repair_loop = 0
    repair_logs = []

    while repair_loop < config.MAX_REPAIR_LOOP_COUNT:
        repair_loop += 1

        validation_result = validate(plan, tool_results)

        if validation_result.valid:
            repair_logs.append({
                "loop": repair_loop,
                "invalid_plan": None,
                "errors": "repair succeed",
                "repaired_plan": plan
            })

            return plan, repair_logs
        
        else:

            repair_message = repair_prompt.get_repair_prompt(
                                            plan, 
                                            validation_result, 
                                            tool_results["get_todo_items"]["todos"],
                                            tool_results["get_calendar_events"]["events"])
            
            repaired_response = llm.call_llm_no_tool(repair_message)
            invalid_plan = plan

            try:
                repaired_plan = json.loads(repaired_response)

                repair_logs.append({
                    "loop": repair_loop,
                    "invalid_plan": invalid_plan,
                    "errors": validation_result.errors,
                    "repaired_plan": repaired_plan
                })

            except json.JSONDecodeError:
                print("Failed to generate valid JSON from repaired response. Repair Failed.")
                return None, repair_logs

            plan = repaired_plan
            
    return None, repair_logs


def normalize(plan):
    # TODO: add normalization logic
    return plan


def get_busy_intervals(events: list[dict]) -> list[dict]:
    intervals = []
    events.sort(key=lambda x:x["start"])

    for event in events:
        intervals.append({
            "start": parse_time(event["start"]),
            "end": parse_time(event["end"])
        })
    return intervals


def get_free_intervals(busy_intervals: list[dict]) -> list[dict]:
    # let's hardcode full day for now
    day_start = parse_time("09:00")
    day_end = parse_time("19:00")

    free_intervals = []
    cur_start = day_start

    for busy_interval in busy_intervals:
        busy_start = busy_interval["start"]
        busy_end = busy_interval["end"]

        if busy_start > cur_start:
            free_intervals.append({
                "start": cur_start,
                "end": busy_start
            })

        cur_start = max(cur_start, busy_end)
    
    if cur_start < day_end:
        free_intervals.append({
            "start": cur_start,
            "end": day_end
        })

    return free_intervals


def get_priority(intent: dict) -> int:
    if intent["user_priority"] is not None:
            return intent["user_priority"]
    if intent["inferred_priority"] is not None:
        return intent["inferred_priority"]
    return 999 # rest of the intents
    

def generate_concrete_plan(planning_intents: dict, tool_results: dict) -> dict:
    calendar_events = tool_results["get_calendar_events"]["events"]
    todos = tool_results["get_todo_items"]["todos"]

    # 1. build todo_id -> todo

    # 2. convert calendar events to busy intervals
    busy_intervals = get_busy_intervals(calendar_events)

    # 3. generate free intervals (from 9:00 AM to 6:00 PM)
    free_intervals = get_free_intervals(busy_intervals)

    # 4. sort todos by explicit_user_priority / inferred_priority / original order
    intents = planning_intents["planning_intents"]
    intents.sort(key=get_priority)


    
    # 5. place each todo into earliest valid free slot based on preferred_time_window
    # 6. return scheduled tasks + unscheduled tasks

    return {}


def run_agent(user_input: str) -> str:
    response_content, tool_results = get_candidate_plan(user_input)

    try:
        planning_intents = json.loads(response_content)
    except json.JSONDecodeError:
        return ""
    
    concrete_plan = generate_concrete_plan(planning_intents, tool_results)

    # repaired_plan, logs = repair_plan(plan, tool_results)
    # if not repaired_plan:
    #     print(logs)
    #     return "I cannot generate a valid plan. Please try again." # TODO: need to figure out the proper address here

    # return normalize(repaired_plan)
    return ""