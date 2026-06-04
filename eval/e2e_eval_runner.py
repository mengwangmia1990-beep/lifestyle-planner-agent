# End-to-End Evaluation Runner
# User input --> Final Concrete Plan

import os
import sys
from collections import Counter

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
    task_assertions = plan_assertions.get("task_assertions", {})

    not_before_value_mismatch = None
    not_before_missing = False
    not_before_hallucination = False

    expected_not_before_map = {}
    actual_not_before_map = {}

    for todo_id, assertions in task_assertions.items():
        expected_not_before_map[todo_id] = assertions.get("not_before")

    for intent in trace.get("planning_intents", []):
        todo_id = intent.get("todo_id")
        actual_not_before = intent.get("not_before")

        if todo_id and actual_not_before is not None:
            actual_not_before_map[todo_id] = actual_not_before

    for todo_id, expected_not_before in expected_not_before_map.items():
        if expected_not_before is not None:
            if todo_id not in actual_not_before_map:
                not_before_missing = True
            else:
                if not_before_value_mismatch is None:
                    not_before_value_mismatch = False

                if actual_not_before_map[todo_id] != expected_not_before:
                    not_before_value_mismatch = True

    for todo_id in actual_not_before_map:
        if todo_id not in expected_not_before_map:
            not_before_hallucination = True

    passed = (
        not not_before_missing
        and not not_before_hallucination
    )

    if not_before_value_mismatch is not None:
        passed = passed and not not_before_value_mismatch

    return {
        "passed": passed,
        "not_before_value_mismatch": not_before_value_mismatch,
        "not_before_missing": not_before_missing,
        "not_before_hallucination": not_before_hallucination,
    }


def compare_intent_coverage(trace, default_duration_map):
    # default_duration_map has all the todo_ids
    expected_todo_ids = set(default_duration_map.keys())
    
    actual_todo_ids = {
        intent.get("todo_id") 
        for intent in trace.get("planning_intents", [])
        if intent.get("todo_id")
    }

    missing_todo_ids = expected_todo_ids - actual_todo_ids

    return {
        "passed": len(missing_todo_ids) == 0,
        "intent_coverage_missing": len(missing_todo_ids) > 0,
        "intent_missing_todo_ids": list(missing_todo_ids)
    }


def compare_dependency_order(plan_assertions, trace):
    expected_dependency_order = plan_assertions.get("respect_dependency_order", [])

    actual_scheduled = trace.get("scheduled", [])
    start_time_map = {}

    for task in actual_scheduled:
        todo_id = task.get("todo_id")
        start = task.get("start")

        if todo_id and start:
            start_time_map[todo_id] = start

    dependency_order_incorrect = False
    violated_dependencies = []

    for before_todo_id, after_todo_id in expected_dependency_order:
        before_start_time = start_time_map.get(before_todo_id)
        after_start_time = start_time_map.get(after_todo_id)

        if before_start_time is None or after_start_time is None:
            continue

        if before_start_time >= after_start_time:
            dependency_order_incorrect = True
            violated_dependencies.append({
                "before": before_todo_id,
                "after": after_todo_id,
                "before_start_time": before_start_time,
                "after_start_time": after_start_time
            })
    
    return {
        "passed": not dependency_order_incorrect,
        "dependency_order_incorrect": dependency_order_incorrect,
        "violated_dependencies": violated_dependencies
    }


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
    not_before_result = compare_not_before(plan_assertions, trace)
    intent_coverage_result = compare_intent_coverage(trace, default_duration_map)
    dependency_result = compare_dependency_order(plan_assertions, trace)

    passed = status_equal and scheduled_equal and unscheduled_equal and skipped_equal and respect_busy_calendar_equal
    if duration_result is not None:
        passed = passed and duration_result["passed"]
    if not_before_result is not None:
        passed = passed and not_before_result["passed"]
    if intent_coverage_result is not None:
        passed = passed and intent_coverage_result["passed"]
    if dependency_result is not None:
        passed = passed and dependency_result["passed"]

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
            "not_before_value_mismatch": not_before_result["not_before_value_mismatch"],
            "not_before_missing": not_before_result["not_before_missing"],
            "not_before_hallucination": not_before_result["not_before_hallucination"],
            "intent_coverage_missing": intent_coverage_result["intent_coverage_missing"],
            "intent_missing_todo_ids": intent_coverage_result["intent_missing_todo_ids"],
            "dependency_order_incorrect": dependency_result["dependency_order_incorrect"],
            "violated_dependencies": dependency_result["violated_dependencies"],
        }
    }

    return result


def build_default_duration_map(tool_results):
    default_duration_map = {}

    todo_items = tool_results.get("get_todo_items", {}).get("todos", [])

    for todo in todo_items:
        todo_id = todo.get("todo_id")
        duration = todo.get("duration_minutes")

        if todo_id and duration is not None:
            default_duration_map[todo_id] = duration

    return default_duration_map


def tag_failure_category(gold_data, compare_result):
    failures = []
    if compare_result is None:
        return None
    
    # unsupported case
    if gold_data.get("known_limitation") == True:
        failures.append("UNSUPPORTED_CASE")
    else:
        checks = compare_result.get("checks")
        if checks is not None:
            # duration failures
            if checks.get("override_duration_equal") == False:
                failures.append("DURATION_VALUE_MISMATCH")
            if checks.get("override_duration_missing") == True:
                failures.append("MISSING_EXPECTED_OVERRIDE_DURATION")
            if checks.get("duration_hallucination") == True:
                failures.append("DURATION_HALLUCINATION")

            # not_before failures
            if checks.get("not_before_value_mismatch") == True:
                failures.append("NOT_BEFORE_VALUE_MISMATCH")
            if checks.get("not_before_missing") == True:
                failures.append("NOT_BEFORE_MISSING")
            if checks.get("not_before_hallucination") == True:
                failures.append("NOT_BEFORE_HALLUCINATION")

            # calendar conflict failure
            if checks.get("respect_busy_calendar_equal") == False:
                failures.append("CONFLICT_WITH_CALENDAR")

            # schedueling failures
            if checks.get("scheduled_equal") == False:
                failures.append("SCHEDULED_TASK_SET_MISMATCH")
            if checks.get("unscheduled_equal") == False:
                failures.append("UNSCHEDULED_TASK_SET_MISMATCH")
            if checks.get("skipped_equal") == False:
                failures.append("SKIPPED_TASK_SET_MISMATCH")

            # intent coverage missing failure
            if checks.get("intent_coverage_missing") == True:
                failures.append("INTENT_COVERAGE_MISSING")

            # scheduled tasks dependency order incorrect
            if checks.get("dependency_order_incorrect") == True:
                failures.append("DEPENDENCY_ORDER_INCORRECT")

            # execution status failure
            if checks.get("status_equal") == False:
                failures.append("STATUS_MISMATCH")
        
    compare_result["failure_categories"] = failures

    return compare_result


def write_to_file(path, content):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(content, ensure_ascii=False) + "\n")


def generate_summary_report():
    total_cases = 0
    passed = 0
    failed = 0
    unsupported = 0

    counter = Counter()

    results = []
    with open(config.EVAL_COMPARE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            results.append(json.loads(line))

    for result in results:
        total_cases += 1

        if result["passed"]:
            passed += 1

        if not result["passed"]:
            failed += 1

        for failure in result.get("failure_categories", []):
            counter[failure] += 1
            if failure == "UNSUPPORTED_CASE":
                unsupported += 1

    supported = total_cases - unsupported
    actual_failed = failed - unsupported
    
    if supported == 0:
        pass_rate = 0
    else:
        pass_rate = round(passed / supported * 100, 2)

    summary_report = {
        "total": total_cases,
        "passed": passed,
        "failed": actual_failed,
        "supported_case": supported,
        "unsupported_case": unsupported,
        "supported_pass_rate": pass_rate,
    }

    for failure, count in counter.most_common():
        summary_report[failure] = count

    write_to_file(config.EVAL_E2E_SUMMARY_FILE, summary_report)


def reset_eval_output():
    with open(config.EVAL_COMPARE_FILE, "w"):
        pass

    with open(config.EVAL_E2E_SUMMARY_FILE, "w"):
        pass


def main():
    reset_eval_output()

    with open(config.EVAL_DATA_FILE) as f: # per-case evaluation
        for line in f:
            gold_data = json.loads(line)
            user_input = gold_data["user_input"]
            print(user_input)

            # run agent and collect runtime trace log
            response, trace, tool_results = run_agent(user_input)

            default_duration_map = build_default_duration_map(tool_results)

            # compare with golden data
            compare_result = compare(gold_data, trace, default_duration_map)

            # tag failure
            tagged_result = tag_failure_category(gold_data, compare_result)

            # write to file
            write_to_file(config.EVAL_COMPARE_FILE, tagged_result)

            # TODO: intent grounding check

    generate_summary_report()

if __name__ == "__main__":
    main()