# AI Lifestyle Planner Agent

A lightweight AI agent system that combines LLM reasoning with deterministic backend scheduling, validation, normalization, observabilitiy and evaluation pipeline.

This project explores how to build reliable AI agents from scratch using OpenAI tool-calling APIs, without relying on orchestration frameworks such as LangChain or LangGraph.

Unlike many purely LLM-driven agent systems, this project gradually evolves toward a hybrid architecture:

LLMs handle semantic reasoning and user intent understanding
Backend systems handle deterministic scheduling and hard constraints

The project focuses heavily on:

- multi-step agent orchestration
- tool calling
- deterministic backend scheduling
- validation pipelines
- hybrid AI system design
- architecture evolution
- observation
- evaluation

## Example User Query
User: *Help me plan tomorrow. I want to go grocery shopping first and plan rest of the things after picking up kid.*

The system:  
1. retrieve calendar events
2. retrieve todo items
3. extract planning intents
4. generate deterministic schedule
5. validate on hard constraints
6. return normalized plan


## Key Features
### Multi-step Single Agent Loop
The agent supports iterative reasoning and tool execution within a fixed max loop count, and a fallback return message when reaching max limit.

```text
User Input
    ↓
LLM Reasoning
    ↓
Backend Tool Execution
    ↓
Tool Result Injection
    ↓
LLM Continues Reasoning
    ↓
Planning Intent Extraction
    ↓
Backend Deterministic Scheduling
    ↓
Backend Validation
    ↓
Final Structured Plan
```

The system maintains full conversation state through `messages` list:  
```text
system prompt
user request
assistant tool-call decisions
tool execution results
assistant reasoning
tool execution results
...
final response
```

### Tool Registry
Backend tools are dynamically dispatched through a tool registry:  
```python
TOOL_MAP = {
    "get_calendar_events": get_calendar_events,
    "get_todo_items": get_todo_items,
    "get_weather: get_weather
}
```

### Deterministic Scheduler
The backend scheduler converts high level planning intents into concrete schedules.

Current scheduling features:  
- earliest free slot allocation
- calendar-aware scheduling
- skipped task handling
- preferred time windows
- priority task handling
- `not_before` constraint
- duration overrides
- unscheduled task handling

Example Scheduling Logic:  
```text
planning intents
    ↓
calendar busy intervals
    ↓
free interval generation
    ↓
priority sorting
    ↓
deterministic slot allocation
    • preferred time window
    • not_before
    • duration fitting
    ↓
structured final plan
```

### Deterministic Validation  
A deterministic validation layer verifies that generated schedules satisfy hard constraints.  

Current validations include:  
- valid time intervals
- overlap detection
- calendar conflict detection
- duration correctness
- `not_before`constraint validation
- todo items coverage validation

### Normalization
A normalization layer translates the validated raw plan into a structured plan. Without normalization, the raw plan can be:  
- unsorted
- without task title

Normalization layer sorts the intervals by chronological order, generates the structured planning summary, status, and structured plan.  

### Observability
The agent generates strucutred runtime traces for every execution.  

Each trace record:  
- user input
- execution status
- planning intents
- scheduled tasks
- unscheduled tasks
- skipped tasks
- validation results

These traces facilate debugging, failure anlaysis, and evaluation pipeline.

### Evaluation (on-going)
The project includes an end-to-end evaluation pipeline based on golden test cases.  

Components:
- `gold_data.jsonl`
- `e2e_eval_runner.py`
- runtime trace collection
- Expect vs Actual comparison
- Failure categorization

Observed failure categories:  
- Constraint Hallucination
- Coverage Missing
- Duration Hallucination
- Unsupported Feature Leakage



## Architecture Evolution: LLM-heavy Planning vs Hybrid Systems

### Iteration 1: LLM-heavy Planning

LLM generates:
- todo_id
- start
- end

Problems:
- unstable repair loop
- poor converges

---
### Iteration 2: Hybrid Architecture

The current hybrid architecture moves deterministic logic into the backend. And removed the LLM based repair loop.  

LLM responsibilities:
- understand user intent
- prioritize tasks
- reason about user preferences
- generate high-level planning intent

Backend responsibilities:
- deterministic duration calculation
- interval allocation
- overlap prevention
- conflict resolution
- final schedule generation

This transition reflects a common industrial pattern in modern AI agent systems:

> LLM + deterministic backend systems


## Core Engineering Challenges
### 1. LLMs Are Weak at Deterministic Scheduling
Initial iterations allowed the LLM to generate fully concrete schedules directly.  

This led to common failures:  
- invalid time calculation
- incorrect task duration calculation
- overlap reintroduction
- unstable repair behavior

Example issues:  
- fixing one introduces another
- repeated over or less scheduling
- local repairs breaks global consistency

Key engineering insight:
> LLMs are strong at semantic reasoning, but weak at deterministic constraint satisfaction.

---
### 2. Repair Loop Do Not Converge
Ealier iterations experimented with LLM repair loops:
```text
invalid plan
    ↓
validation errors
    ↓
LLM repair
    ↓
re-validation
    ...
```
However, repair loops failed to converge. At the same time, repair loops are costy, unreliable and introducing bigger latency.  

This motivates the transition towards backend deterministic scheduling by reducing LLM's responsibility.

---

### 3. LLM Output Contract Violations
The system also exposed common agent reliability problems:  
- invalid JSON output
- inconsistent schemas and type
- missing todo coverage

These issues motivated:

- stronger prompting
- validation pipelines
- normalization layers
- stricter backend contracts

### 4. Latency Issue
latency issue is hard to ignored in current project MVP. Single query takes more than a few seconds to provide a final result. The main issue is about sequentially calling all the availble tools. In this iteration, `get_calender_events` and `get_todo_items` can be called in parallel since they are not dependent on each other. Next iteration will call these tools in parallel to reduce the overall latency.


## Future improvement:
- parallel tool calling
- FastAPI service wrapper



## Run the project
```
python main.py

example user query:
help me plan tomorrow's schedule
```