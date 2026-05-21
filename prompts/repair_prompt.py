
from models.validation_models import ValidationResult

def get_repair_prompt(
        plan: dict, 
        validation_result: ValidationResult, 
        todo_items: list,
        calendar_events: list
    ) -> list:
    return [{
        "role": "user",
        "content": f"""
            Your plan does not pass the validation.
            
            You are NOT allowed to preserve the current plan.
            Discard all existing task blocks.
            Create a brand-new tasks list using only expected todo items.

            Output Rules:
            - Return ONLY valid JSON.
            - Return exactly one top-level key: "tasks".
            - Do NOT include "calendar_events" or any other top-level keys.
            - Do NOT include markdown formatting.
            - Do NOT wrap the output with ```json.
            - Do NOT include explanations.

            Planning rules:
            - Calendar events are fixed busy blocks and cannot be moved.
            - Each todo_id should appear at most once unless splitting is necessary.
            - Planned todo tasks MUST NOT overlap with each other.
            - Planned todo tasks MUST NOT overlap with calendar events.
            - Only schedule todo items from the expected todo items list.
            - Include ALL expected todo items.
            - For each todo_id, the total scheduled duration across all task blocks MUST equal its expected duration_minutes exactly.
            - Do NOT over-schedule or under-schedule any todo_id.
            - You may split a todo item into multiple blocks only if the total duration still equals expected duration_minutes.
            - Return tasks sorted by start time.
        
            Current plan:
            {plan}

            Validation errors:
            {validation_result.errors}

            Fixed calendar events:
            {calendar_events}
            
            Expectated todo items
            {todo_items},

            expected_duration_by_todo
            {{
                "todo_1": 120,
                "todo_2": 120,
                "todo_3": 30
            }}
            For each todo_id, total scheduled minutes must equal this map exactly.
        """
    }]