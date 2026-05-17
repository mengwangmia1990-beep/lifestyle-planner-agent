from prompts import system_prompt
from llm import llm
from tools import tool_registry
import json

def run_agent(user_input: str) -> str:
    messages = []
    user_message = {
        "role": "user",
        "content": user_input
    }
    messages.append(system_prompt.system_message)
    messages.append(user_message)

    while True:
        # 让LLM决定是否要调用tool
        response = llm.call_llm(messages, tool_registry.TOOLS)

        if not response.tool_calls:
            return response.content

        # append assistant message
        messages.append(response)

        for tool_call in response.tool_calls:
            tool_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            tool_result = tool_registry.TOOL_MAP[tool_name](**args)
            print(f"tool_result: {tool_result}")

            # new role: tool --> backend 执行tool, 把结果返回LLM
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result)
            })