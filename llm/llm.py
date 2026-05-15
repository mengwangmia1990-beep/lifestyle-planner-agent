from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_llm(messages, tools) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    return response.choices[0].message


def call_llm_final(messages) -> str:
    final_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    return final_response.choices[0].message.content