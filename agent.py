from prompts import system_prompt, repair_prompt
from llm import llm
from tools import tool_registry
import json
import config
from models.validation_models import ValidationResult
import scheduler
import validators
from datetime import date
import os
from  dataclasses import asdict


def get_plan_intents(user_input):
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


def generate_plan_summary(normalized_plan, tool_results):
    lines = []
    scheduled = normalized_plan["scheduled"]
    unscheduled = normalized_plan["unscheduled"]
    skipped = normalized_plan["skipped"]

    id_to_tool_name = {}
    for todo in tool_results["get_todo_items"]["todos"]:
        todo_id = todo["todo_id"]
        name = todo["title"]
        id_to_tool_name[todo_id] = name

    if scheduled:
        lines.append("Here is your plan:")
        for task in scheduled:
            task_name = id_to_tool_name[task["todo_id"]]
            start = task["start"]
            end = task["end"]
            
            lines.append(f"{start} -- {end}: {task_name}")

    if unscheduled:
        lines.append("")
        lines.append("Unscheduled plan:")
        for task in unscheduled:
            task_name = id_to_tool_name[task["todo_id"]]
            lines.append(f"{task_name}, reason: {task.get("reason", "No reason provided.")}")

    if skipped:
        lines.append("")
        lines.append("Skipped plan:")
        for task in skipped:
            task_name = id_to_tool_name[task["todo_id"]]
            lines.append(f"{task_name}, reason: {task.get("reason", "Skipped.")}")

    return "\n".join(lines)


def normalize(scheduled, unscheduled, skipped):
    scheduled.sort(key=lambda x:x["start"])

    return {
        "scheduled": scheduled,
        "unscheduled": unscheduled,
        "skipped": skipped
    }


def ensure_required_tool_results(tool_results):
    """
    Ensure backend scheduler has all required context tool results.
    Do not rely on LLM to always call every required tool.
    """

    today = date.today().isoformat()
    REQUIRED_CONTEXT_TOOLS = {
        "get_calendar_events": {
            "date": today
        },
        "get_todo_items": {
            "date": today
        },
    }

    for tool_name, args in REQUIRED_CONTEXT_TOOLS.items():
        if tool_name not in tool_results:
            result = tool_registry.TOOL_MAP[tool_name](**args)
            tool_results[tool_name] = result
    
    return tool_results


def set_trace(user_input, planning_intents, scheduled, unscheduled, skipped, validation_result):
    runtime_trace_file = os.path.join(config.LOGS_FILE, config.TRACE_FILE_NAME)

    status = "success" if validation_result.valid else "failed"
    intents = planning_intents["planning_intents"]
    trace = {
        "query": user_input,
        "status": status,
        "planning_intents": intents,
        "scheduled": scheduled,
        "unscheduled": unscheduled,
        "skipped": skipped,
        "validation_result": asdict(validation_result)
    }
    print(type(validation_result))
    with open(runtime_trace_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(trace, ensure_ascii=False) + "\n")


def run_agent(user_input: str) -> str:
    response_content, tool_results = get_plan_intents(user_input)

    try:
        planning_intents = json.loads(response_content)
    except json.JSONDecodeError:
        return ""
    
    # Sometimes LLM does not call all required tools. We cannot only reply on LLM.
    # Therefore we ensure all required tools to be called before sending to scheduler.
    tool_results = ensure_required_tool_results(tool_results)
    
    # Generate concrete plan
    scheduled, unscheduled, skipped = scheduler.generate_concrete_plan(planning_intents, tool_results)

    # Validate plan
    validation_result = validators.validate(scheduled, unscheduled, skipped, tool_results, planning_intents)

    # Set runtime trace
    set_trace(user_input, planning_intents, scheduled, unscheduled, skipped, validation_result)

    # Normalization
    if validation_result.valid:
        normalized_plan = normalize(scheduled, unscheduled, skipped)
        summary = generate_plan_summary(normalized_plan, tool_results)

        return json.dumps({
            "status": "success",
            "summary": summary,
            "plan": normalized_plan
        })
    else:
        print(validation_result)
        return json.dumps({
            "status": "failed",
            "summary": "Failed to generate plan",
            "errors": validation_result.errors,
            "plan": {
                "scheduled": scheduled,
                "unscheduled": unscheduled,
                "skipped": skipped
            }
        })