# AI Lifestyle Planner Agent

A lightweight multi-step AI agent built with OpenAI tool calling APIs.

This project demonstrates how to build a tool-using AI agent from scratch without relying on frameworks such as LangChain or LangGraph.  

The agent can:

- Reason about user requests
- Decide when tools are needed
- Execute backend tools
- Consume tool results
- Generate final recommendations

Current tools:

- Calendar tool
- Todo list tool

## Architecture
```
User Input
    ↓
LLM Reasoning
    ↓
Tool Calling
    ↓
Backend Tool Execution
    ↓
Tool Result Injection
    ↓
LLM Continues Reasoning
    ↓
Final Response
```

## Key Features
### Multi-step Agent Loop
The agent supports iterative reasoning and tool execution:  
```python
while True:
    response = llm.call_llm(messages, ALL_TOOLS)

    if not response.tool_calls:
        return response.content

    messages.append(response)
    for tool_call in response.tool_calls:
        
        ...

        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(tool_result)
        })
```
This allows the LLM to:

1. Decide which tools are needed
2. Consume tool outputs
3. Continue reasoning
4. Optionally call more tools  
5. Generate a final response  

## Tool Registry
Backend tools are dynamically dispatched through a tool registry:  
```python
TOOL_MAP = {
    "get_calendar_events": get_calendar_events,
    "get_todo_items": get_todo_items
}
```

## Conversation State Management
The project manually maintains the full conversation state through the `messages` list:  
```
system prompt
user request
assistant tool-call decisions
tool execution results
assistant reasoning
tool execution results
...
final response
```
This mimics how modern AI agent runtimes manage reasoning context across multiple steps.

## Example Workflow
```
User:
Help me plan tomorrow.

LLM:
Calls calendar tool

Backend:
Executes tool and returns results

LLM:
Calls todo items tool

Backend:
Returns todo items results

LLM:
Generates final lifestyle plan
```

## Key Learnings
This project helped deepen understanding of:

- OpenAI tool calling APIs
- Agent orchestration loops
- Multi-step reasoning
- Tool execution routing
- Conversation state management
- Agent runtime design

## Run the project
```
python main.py
```