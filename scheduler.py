from time_utils import parse_time, add_minutes
from datetime import datetime, timedelta


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
    day_end = parse_time("21:00")

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
            return int(intent["user_priority"])
    
    if intent["inferred_priority"] is not None:
        return int(intent["inferred_priority"])
    return 999 # rest of the intents


def get_window_range(preferred_time_window):
    if preferred_time_window == "morning":
        return (parse_time("09:00"), parse_time("12:00"))
    if preferred_time_window == "afternoon":
        return (parse_time("12:00"), parse_time("17:00"))
    if preferred_time_window == "evening":
        return (parse_time("17:00"), parse_time("21:00"))
    return (parse_time("09:00"), parse_time("21:00"))  # flexible



def get_candidate_windows(preferred_window: str) -> list[tuple[datetime, datetime]]:
    windows = [get_window_range(preferred_window)]
    flexible_window = get_window_range("flexible")
    if flexible_window not in windows:
        windows.append(flexible_window)

    return windows


def subtract_interval(free_intervals, occupied_start, occupied_end):
    updated = []

    for interval in free_intervals:
        start = interval["start"]
        end = interval["end"]

        # no overlap
        if occupied_end <= start or occupied_start >= end:
            updated.append(interval)
            continue

        # left remaining part
        if occupied_start > start:
            updated.append({
                "start": start,
                "end": occupied_start
            })

        # right remaining part
        if occupied_end < end:
            updated.append({
                "start": occupied_end,
                "end": end
            })

    return updated


def parse_not_before(time_str):
    if not time_str:
        return None
    
    try:
        return parse_time(time_str)
    except Exception:
        return None


def generate_concrete_plan(planning_intents: dict, tool_results: dict) -> dict:
    if "get_calendar_events" not in tool_results:
        raise ValueError("Missing required context: get_calendar_events")
    
    if "get_todo_items" not in tool_results:
        raise ValueError("Missing required context: get_todo_items")

    calendar_events = tool_results["get_calendar_events"]["events"]
    todos = tool_results["get_todo_items"]["todos"]

    # 1. convert calendar events to busy intervals
    busy_intervals = get_busy_intervals(calendar_events)

    # 2. generate free intervals (from 9:00 AM to 9:00 PM)
    free_intervals = get_free_intervals(busy_intervals)

    # 3. sort todos by explicit_user_priority / inferred_priority / original order
    intents = planning_intents["planning_intents"]

    scheduled_candidate_intents = []
    skipped_intents = []

    for intent in intents:
        if intent.get("should_schedule", True):
            scheduled_candidate_intents.append(intent)
        else:
            skipped_intents.append({
                "todo_id": intent["todo_id"],
                "reason": intent.get("skip_reason", "Marked as not schedulable")
            })

    scheduled_candidate_intents.sort(key=get_priority)
    
    # 4. place each todo into earliest valid free slot based on preferred_time_window
    todo_map = {}
    for todo in todos:
        todo_map[todo["todo_id"]] = todo["duration_minutes"]

    plans = []
    unscheduled = []

    for intent in scheduled_candidate_intents:
        placed = False
        
        todo_id = intent["todo_id"]
        default_duration = todo_map.get(todo_id)

        if default_duration is None:
            unscheduled.append({
                "todo_id": todo_id,
                "reason": f"todo id {todo_id} not found in the tool results"
            })
            continue

        preferred_time_window = intent["preferred_time_window"]
        
        not_before = parse_not_before(intent.get("not_before"))

        override_duration = intent.get("override_duration_minutes")
        
        for window_start, window_end in get_candidate_windows(preferred_time_window):
            for free_interval in free_intervals:
                candidate_start = max(
                    free_interval["start"],
                    window_start,
                    not_before or window_start)
                
                candidate_end_limit = min(free_interval["end"], window_end)

                duration = int(override_duration) if override_duration is not None else default_duration
                candidate_end = add_minutes(candidate_start, duration)
                
                # task can fit in:
                if candidate_end <= candidate_end_limit:
                    # no need to split the task. Task is completely fit in this candidate window
                    plan = {
                        "todo_id": todo_id,
                        "start": candidate_start.strftime("%H:%M"),
                        "end": candidate_end.strftime("%H:%M"),
                        "duration_minutes": duration
                    }
                    plans.append(plan)

                    free_intervals = subtract_interval(
                        free_intervals,
                        candidate_start,
                        candidate_end
                    )

                    placed = True
                    break
            
            if placed:
                break
        
        if not placed:
            unscheduled.append({
                "todo_id": todo_id,
                "reason": "No valid free slot found"
            })

    # 5. return scheduled tasks and unscheduled tasks
    return plans, unscheduled, skipped_intents