from prompts import system_prompt, repair_prompt
from llm import llm
from tools import tool_registry
import json
import config
from models.validation_models import ValidationResult
import scheduler
import validators


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


def normalize(plan):
    # TODO: add normalization logic
    return plan


def run_agent(user_input: str) -> str:
    response_content, tool_results = get_plan_intents(user_input)

    try:
        planning_intents = json.loads(response_content)
    except json.JSONDecodeError:
        return ""
    
    scheduled, unscheduled, skipped = scheduler.generate_concrete_plan(planning_intents, tool_results)

    validation_result = validators.validate(scheduled, unscheduled, skipped, tool_results)
    print(validation_result)

    return json.dumps({
        "scheduled": scheduled,
        "unscheduled": unscheduled,
        "skipped": skipped
    }, indent=2)