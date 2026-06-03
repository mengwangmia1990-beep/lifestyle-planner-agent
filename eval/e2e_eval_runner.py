# End-to-End Evaluation Runner
# User input --> Final Concrete Plan

import os
import sys

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
sys.path.append(PROJECT_ROOT)

import config
from agent import run_agent
import json


def get_todo_ids(tasks):
    ids = []
    for task in tasks:
        if task["todo_id"]:
            ids.append(task["todo_id"])
    return ids


def compare_status(expected_plan, trace):
    # validate execution status
    expected_status = expected_plan["status"]
    actual_status = trace["status"]
    status_equal = expected_status == actual_status
    return status_equal


def compare_scheduled(expected_plan, trace):
    # validate scheduled tasks
    expected_scheduled = expected_plan["scheduled_todo_ids"]
    actual_scheduled = []
    for task in trace.get("scheduled", []):
        actual_scheduled.append(task.get("todo_id"))
    scheduled_equal = set(expected_scheduled) == set(actual_scheduled)
    return scheduled_equal


def compare_unscheduled(expected_plan, trace):
    # validate unscheduled tasks
    expected_unscheduled = expected_plan["unscheduled_todo_ids"]
    actual_unscheduled = []
    for task in trace.get("unscheduled", []):
        actual_unscheduled.append(task.get("todo_id"))
    unscheduled_equal = set(expected_unscheduled) == set(actual_unscheduled)
    return unscheduled_equal


def compare_skipped(expected_plan, trace):
    # validate skipped tasks
    expected_skipped = expected_plan["skipped_todo_ids"]
    actual_skipped = []
    for task in trace.get("skipped", []):
        actual_skipped.append(task.get("todo_id"))
    skipped_equal = set(expected_skipped) == set(actual_skipped)
    return skipped_equal


def compare_respect_busy_calendar(plan_assertions, trace):
    # validate respect busy calendar
    expected_respect_busy_calendar = plan_assertions["respect_busy_calendar"]
    actual_respect_busy_calendar = trace["validation_result"]["checks"]["respect_busy_calendar"]
    respect_busy_calendar_equal = expected_respect_busy_calendar == actual_respect_busy_calendar
    return respect_busy_calendar_equal


def compare_duration(plan_assertions, trace, default_duration_map):
    task_assertions = plan_assertions.get("task_assertions", {})
    
    # compare duration
    override_duration_equal = None
    duration_hallucination = False
    override_duration_missing = False

    actual_scheduled_duration_map = {}
    expected_todo_ids = set()

    for task in trace.get("scheduled", []):
        actual_scheduled_duration_map[task.get("todo_id")] = task.get("duration_minutes")

    for todo_id, assertions in task_assertions.items():
        expected_duration = assertions.get("expected_duration_minutes")
        actual_duration = actual_scheduled_duration_map.get(todo_id)

        # golden expects an override duration
        if expected_duration is not None:
            expected_todo_ids.add(todo_id)

            if todo_id not in actual_scheduled_duration_map:
                override_duration_missing = True
                override_duration_equal = False
            else:
                if override_duration_equal is None:
                    override_duration_equal = True

                if actual_duration != expected_duration:
                    override_duration_equal = False

    for todo_id, actual_duration in actual_scheduled_duration_map.items():
        if todo_id in expected_todo_ids:
            continue
        
        default_duration = default_duration_map.get(todo_id)

        if todo_id in default_duration_map and default_duration is not None and actual_duration != default_duration:
            duration_hallucination = True

    passed = not override_duration_missing and not duration_hallucination
    if override_duration_equal is not None:
        passed = passed and override_duration_equal

    duration_result = {
        "passed": passed,
        "override_duration_equal": override_duration_equal,
        "override_duration_missing": override_duration_missing,
        "duration_hallucination": duration_hallucination
    }

    return duration_result


def compare_not_before(plan_assertions, trace):
    # validate not_before
    task_assertions = plan_assertions.get("task_assertions", {})
    not_before_equal = None
    actual_scheduled_not_before_map = {}
    
    for intent in trace.get("planning_intents", []):
        if intent.get("not_before") is not None:
            actual_scheduled_not_before_map[intent["todo_id"]] = intent.get("not_before")
        
    for todo_id, assertions in task_assertions.items():
        expected_not_before = assertions.get("not_before")

        if expected_not_before is None:
            continue
        
        actual_not_before = actual_scheduled_not_before_map.get(todo_id)

        if not_before_equal is None:
            not_before_equal = True
        
        if actual_not_before != expected_not_before:
            not_before_equal = False
    return not_before_equal


def compare(gold_data, trace, default_duration_map):
    case_name = gold_data["name"]
    category = gold_data["category"]
    user_input = gold_data["user_input"]

    expected_plan = gold_data.get("expected_plan", {})
    plan_assertions = gold_data.get("plan_assertions", {})

    status_equal = compare_status(expected_plan, trace)
    scheduled_equal = compare_scheduled(expected_plan, trace)
    unscheduled_equal = compare_unscheduled(expected_plan, trace)
    skipped_equal = compare_skipped(expected_plan, trace)
    respect_busy_calendar_equal = compare_respect_busy_calendar(plan_assertions, trace)
    duration_result = compare_duration(plan_assertions, trace, default_duration_map)
    not_before_equal = compare_not_before(plan_assertions, trace)

    passed = status_equal and scheduled_equal and unscheduled_equal and skipped_equal and respect_busy_calendar_equal
    if duration_result is not None:
        passed = passed and duration_result["passed"]
    if not_before_equal is not None:
        passed = passed and not_before_equal

    result = {
        "case_name": case_name,
        "category": category,
        "passed": passed,
        "query": user_input,
        "checks": {
            "status_equal": status_equal,
            "scheduled_equal": scheduled_equal,
            "unscheduled_equal": unscheduled_equal,
            "skipped_equal": skipped_equal,
            "respect_busy_calendar_equal": respect_busy_calendar_equal,
            "override_duration_equal": duration_result["override_duration_equal"],
            "override_duration_missing": duration_result["override_duration_missing"],
            "duration_hallucination": duration_result["duration_hallucination"],
            "not_before_equal": not_before_equal
        }
    }

    with open(config.EVAL_COMPARE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")

    return result


def build_default_duration_map(tool_results):
    default_duration_map = {}

    todo_items = tool_results.get("get_todo_items").get("todos", [])

    for todo in todo_items:
        todo_id = todo.get("todo_id")
        duration = todo.get("duration_minutes")

        if todo_id and duration is not None:
            default_duration_map[todo_id] = duration

    return default_duration_map


def main():
    with open(config.EVAL_DATA_FILE) as f: # per-case evaluation
        for line in f:
            gold_data = json.loads(line)
            user_input = gold_data["user_input"]
            print(user_input)

            # run agent and collect runtime trace log
            response, trace, tool_results = run_agent(user_input)

            default_duration_map = build_default_duration_map(tool_results)

            # compare with golden data
            eval_result = compare(gold_data, trace, default_duration_map)

            # TODO: generate eval summary report
            # TODO: intent grounding check


if __name__ == "__main__":
    main()