# AI Lifestyle Planner Agent

A lightweight multi-step AI agent built with OpenAI tool calling APIs.

This project demonstrates how to build a tool-using AI agent from scratch without relying on frameworks such as LangChain or LangGraph.  

The agent can:

- Reason about user requests
- Decide when tools are needed
- Execute backend tools
- Consume tool results
- Generate final recommendations
- Backend validate final plan

Current tools:

- Calendar tool
- Todo list tool
- weather tool

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
    ↓
Backend Deterministic Validation
```

## Key Features
### Multi-step Agent Loop
The agent supports iterative reasoning and tool execution within a fixed max loop count, and a fallback return message when reaching max limit.
```python
while loop_count < MAX_LOOP_COUNT:
    loop_count += 1

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
return "Sorry, I couldn't complete the request within the allowed number of steps."
```
This allows the LLM to:

1. Decide which tools are needed
2. Consume tool outputs
3. Continue reasoning
4. Optionally call more tools  
5. Generate a final response  
6. Avoid endless tool calling

## Tool Registry
Backend tools are dynamically dispatched through a tool registry:  
```python
TOOL_MAP = {
    "get_calendar_events": get_calendar_events,
    "get_todo_items": get_todo_items,
    "get_weather: get_weather
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

Backend:
Validates fiinal plan via repair loop
```

## Backend Deterministic Validation  
Current system validates four important metris:
- each task start and end time interval should be valid  
- each time interval should not overlap with another
- total duration time for each task should match user's todo item list
- planned todo tasks must not conflict with fixed calendar events

### Validation Result
![alt text](image.png)
From above validation result, it is obvious to see that LLM result (especially on the hard constraints) is normally not reliable. 
> **LLM is NOT source of truth**

With the validation process, we can avoid providing user with an invalid plan. However, this is a bad user experience. This brings us the next iteration plan: 
> We need to send the validation result back to LLM for revision, and validate again until a valid plan is generated.
---

### Repair Loop
1. If validation fails:
   - send validation errors back to the LLM
   - ask the LLM to repair the plan
2. Re-validate the repaired plan
3. Repeat until:
   - the plan passes validation
   - or maximum repair attempts are reached

#### Limitation

Although repair loops improve reliability, **they do not always converge.**

Common failure patterns include:  
1. fixing one validation error introduces another  
2. local edits breaks global schedule consistency
3. repeated over-scheduling tasks
4. unstable duration calculations

Below repair log indicates that system reaches the max retry limit, but still not able to converge a valid plan.
```json
[{
    'loop': 1, 
    'invalid_plan': {
        'tasks': [
            {'todo_id': 'todo_1', 'title': 'Study LeetCode', 'start': '09:00', 'end': '11:00'}, 
            {'todo_id': 'todo_2', 'title': 'Work on AI agent project', 'start': '11:00', 'end': '12:00'}, 
            {'todo_id': 'todo_3', 'title': 'Buy groceries', 'start': '13:00', 'end': '13:30'}, 
            {'todo_id': 'todo_2', 'title': 'Work on AI agent project', 'start': '13:30', 'end': '15:30'}, 
            {'todo_id': 'todo_2', 'title': 'Work on AI agent project', 'start': '16:30', 'end': '18:30'}]}, 
    'errors': ['task todo_2 duration 300.0 does not match with expected duration 120'], 
    'repaired_plan': {
        'tasks': [
            {'todo_id': 'todo_1', 'title': 'Study LeetCode', 'start': '09:00', 'end': '11:00'}, 
            {'todo_id': 'todo_2', 'title': 'Work on AI agent project', 'start': '11:00', 'end': '12:00'}, 
            {'todo_id': 'todo_3', 'title': 'Buy groceries', 'start': '13:00', 'end': '13:30'}, 
            {'todo_id': 'todo_2', 'title': 'Work on AI agent project', 'start': '13:30', 'end': '15:30'}]}}, 
{
    'loop': 2, 
    'invalid_plan': {
        'tasks': [
            {'todo_id': 'todo_1', 'title': 'Study LeetCode', 'start': '09:00', 'end': '11:00'}, 
            {'todo_id': 'todo_2', 'title': 'Work on AI agent project', 'start': '11:00', 'end': '12:00'}, 
            {'todo_id': 'todo_3', 'title': 'Buy groceries', 'start': '13:00', 'end': '13:30'}, 
            {'todo_id': 'todo_2', 'title': 'Work on AI agent project', 'start': '13:30', 'end': '15:30'}]}, 
    'errors': ['task todo_2 duration 180.0 does not match with expected duration 120'], 
    'repaired_plan': {
        'tasks': [
            {'todo_id': 'todo_1', 'title': 'Study LeetCode', 'start': '09:00', 'end': '11:00'}, 
            {'todo_id': 'todo_2', 'title': 'Work on AI agent project', 'start': '11:00', 'end': '12:00'}, 
            {'todo_id': 'todo_3', 'title': 'Buy groceries', 'start': '13:00', 'end': '13:30'}, 
            {'todo_id': 'todo_2', 'title': 'Work on AI agent project', 'start': '13:30', 'end': '15:30'}]}}, 
{
    'loop': 3, 
    'invalid_plan': {
        'tasks': [
            {'todo_id': 'todo_1', 'title': 'Study LeetCode', 'start': '09:00', 'end': '11:00'}, 
            {'todo_id': 'todo_2', 'title': 'Work on AI agent project', 'start': '11:00', 'end': '12:00'}, 
            {'todo_id': 'todo_3', 'title': 'Buy groceries', 'start': '13:00', 'end': '13:30'}, 
            {'todo_id': 'todo_2', 'title': 'Work on AI agent project', 'start': '13:30', 'end': '15:30'}]}, 
    'errors': ['task todo_2 duration 180.0 does not match with expected duration 120'], 
    'repaired_plan': {
        'tasks': [
            {'todo_id': 'todo_1', 'title': 'Study LeetCode', 'start': '09:00', 'end': '11:00'}, 
            {'todo_id': 'todo_2', 'title': 'Work on AI agent project', 'start': '11:00', 'end': '12:00'}, 
            {'todo_id': 'todo_3', 'title': 'Buy groceries', 'start': '13:00', 'end': '13:30'}, 
            {'todo_id': 'todo_2', 'title': 'Work on AI agent project', 'start': '13:30', 'end': '15:30'}]}}]
AI: I cannot generate a valid plan. Please try again.
```

This demonstrates a common limitation of LLM-compute-heavy agent systems:
> **Local repair does not guarantee global correctness**  

Thus brings us to think about the possible architecture evolution: LLM-compute-heavy vs hybrid system.


## Architecture Evolution: LLM-heavy Planning vs Hybrid Systems (Iteration 2)

Initially, the system allowed the LLM to generate fully concrete schedules including:
- start times
- end times
- duration allocation
- conflict avoidance

However, during repair-loop iterations, several important reliability issues emerged:

- non-converging repair loops
- local fixes breaking global constraints
- inaccurate duration calculations
- overlap reintroduction
- unstable time arithmetic

This revealed an important engineering insight:

> LLMs are strong at semantic reasoning,
> but weak at deterministic constraint satisfaction.

As a result, the next iteration of the project will gradually migrate deterministic scheduling logic into the backend.

Planned hybrid architecture:

LLM responsibilities:
- understand user intent
- prioritize tasks
- reason about user preferences
- generate high-level planning intent

Backend responsibilities:
- deterministic duration calculation
- interval allocation
- overlap prevention
- calendar conflict resolution
- final schedule generation

This transition reflects a common industrial pattern in modern AI agent systems:
> LLM + deterministic backend systems


## Common technical issues
### 1. LLM Does Not Always Return Valid Raw JSON
Even with explicit prompt constraints, the LLM may still wrap the JSON output inside markdown code blocks such as:

```text
```json
{
    ...
}
```

This causes `json.loads()` to fail.  

To improve robustness, we strengthened the prompt instructions to explicitly require:

- raw JSON only
- no markdown formatting
- no extra explanations

Future improvement:
- add a backend JSON extraction layer before parsing.

---

### 2. Valid Plan Does Not Always Mean Human-Readable Plan
Even if the generated plan passes validation, the output may still be difficult to read or poorly organized.

For example:
- tasks may not be sorted chronologically
- task ordering may look unnatural to humans
- formatting may be inconsistent

These issues are considered **presentation problems** rather than validation failures.

Future improvement:
- introduce a normalization layer to:
  - sort tasks by start time
  - standardize task schema
  - improve readability of final output



## Run the project
```
python main.py

example user query:
help me plan tomorrow's schedule
```