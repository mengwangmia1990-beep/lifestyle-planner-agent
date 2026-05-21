
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
            
            Please repair the plan according to the validation errors.



            Rules:
            - You MUST return the repaired plan only in valid JSON format.
            - Do NOT include markdown formatting.
            - Do NOT wrap the output with ```json.
            - Do NOT include explanations.
            - Calendar events are FIXED and CANNOT be moved.
            - The repaired plan MUST NOT overlap with the calendar events.
            - The repaired plan MUST include ALL expected todo items.
            - Only move planned todo tasks. Do not modify calendar events.
            - If validation error says missing calendar event, fix it by adding the missing calendar event back exactly.
            - Do NOT remove other calendar events.
        
            Current plan:
            {plan}

            Validation errors:
            {validation_result.errors}

            Fixed calendar events:
            {calendar_events}
            
            Expectated todo items
            {todo_items}
        """
    }]