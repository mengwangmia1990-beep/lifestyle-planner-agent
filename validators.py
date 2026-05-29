from models.validation_models import ValidationResult
from time_utils import parse_time


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


def validate_duration(tasks, planning_intents, tool_results):
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

    for intent in planning_intents["planning_intents"]:
        override_duration_minutes = intent.get("override_duration_minutes")
        if override_duration_minutes is not None:
            expected_todo_duration[intent["todo_id"]] = int(override_duration_minutes)

    errors = []
    for todo_id, duration in actual_todo_duration.items():
        expected_duration = expected_todo_duration.get(todo_id, 0)

        if duration != expected_duration:
            duration_error = f"task {todo_id} duration {duration} does not match with expected duration {expected_duration}"
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

            for event in events:
                event_start = parse_time(event["start"])
                event_end = parse_time(event["end"])
                event_title = event.get("title", "")

                if task_start < event_end and task_end > event_start:
                    # task has conflict with calendar event
                    errors.append(
                        f"task {task_id} "
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


def validate_coverage(scheduled, unscheduled, skipped, tool_results):
    expected_todo_ids = {
        todo["todo_id"]
        for todo in tool_results["get_todo_items"]["todos"]
    }

    scheduled_todo_ids = {
        task["todo_id"]
        for task in scheduled
    }

    unscheduled_todo_ids = {
        task["todo_id"]
        for task in unscheduled
    }

    skipped_todo_ids = {
        task["todo_id"]
        for task in skipped
    }

    errors = []

    missing = expected_todo_ids - scheduled_todo_ids - unscheduled_todo_ids - skipped_todo_ids
    duplicated = (scheduled_todo_ids & unscheduled_todo_ids) | \
                (scheduled_todo_ids & skipped_todo_ids) | \
                (unscheduled_todo_ids & skipped_todo_ids)
    unknown = (scheduled_todo_ids | unscheduled_todo_ids | skipped_todo_ids) - expected_todo_ids

    if missing:
        errors.append(f"missing todo ids: {missing}")
    if duplicated:
        errors.append(f"duplicate todo ids: {duplicated}. Tasks cannot be scheduled, unscheduled or skipped at the same time.")
    if unknown:
        errors.append(f"unknown todo ids: {unknown}")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors
    )


def validate_not_before(scheduled, planning_intents):
    errors = []

    not_before_intents = {}

    for intent in planning_intents["planning_intents"]:
        if intent.get("not_before") is not None:
            not_before_intents[intent["todo_id"]] = intent
    
    for task in scheduled:
        todo_id = task["todo_id"]
        if todo_id in not_before_intents:
            try:
                task_start = parse_time(task["start"])
                not_before_time = parse_time(not_before_intents[todo_id].get("not_before"))
                if task_start  < not_before_time:
                    errors.append(
                        f"task {todo_id} starts at {task_start}, "
                        f"which is before not_before constraint {not_before_time}" 
                    )
            except Exception as e:
                errors.append(f"Failed to validate not_before for task {todo_id}. Error {e}")

    return ValidationResult(
        valid=len(errors)==0,
        errors=errors
    )


def validate(scheduled, unscheduled, skipped, tool_results, planning_intents):
    errors = []

    for task in scheduled:
        interval_result = validate_interval(task)
        if not interval_result.valid:
            errors.extend(interval_result.errors)
    
    overlap_result = validate_overlap(scheduled)
    if not overlap_result.valid:
        errors.extend(overlap_result.errors)

    calendar_conflict_result = validate_calendar_conflict(scheduled, tool_results)
    if not calendar_conflict_result.valid:
        errors.extend(calendar_conflict_result.errors)
    
    duration_result = validate_duration(scheduled, planning_intents, tool_results)
    if not duration_result.valid:
        errors.extend(duration_result.errors)

    coverage_result = validate_coverage(scheduled, unscheduled, skipped, tool_results)
    if not coverage_result.valid:
        errors.extend(coverage_result.errors)

    not_before_result = validate_not_before(scheduled, planning_intents)
    if not not_before_result.valid:
        errors.extend(not_before_result.errors)

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors
    )