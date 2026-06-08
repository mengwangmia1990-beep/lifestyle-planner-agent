# AI Lifestyle Planner Agent

AI lifestyle planner agent that combines LLM reasoning with deterministic backend scheduling, validation, runtime tracing, evaluation, and FastAPI-based service exposure.

This project explores how to build reliable AI agents from scratch using OpenAI tool-calling APIs, without relying on orchestration frameworks such as LangChain or LangGraph.

This project follows a hybrid architecture:
- LLMs handle semantic reasoning and user intent extraction
- Backend systems handle deterministic scheduling and hard constraints


## Example Workflow

User:  
*Help me plan tomorrow. I want to go grocery shopping first and plan the rest of my tasks after picking up my kid.*

System:
1. Retrieve calendar events and todo items
2. Extract planning intents using LLM
3. Generate a deterministic schedule
4. Validate hard constraints
5. Produce a normalized plan and runtime trace

## System Architecture
The system uses a hybrid agent architecture. The LLM is responsible for semantic reasoning and intent extraction, while deterministic backend handles scheduling, validation, normalization, tracing, and evaluation.  

```text
Client / CLI / FastAPI Request
        ↓
run_agent()
        ↓
LLM Tool-Calling Loop
        ↓
Planning Intent JSON
        ↓
Intent Cleanup
        ↓
Context Completion
        ↓
Deterministic Scheduler
        ↓
Validation Layer
        ↓
Normalization
        ↓
Runtime Trace + Final Plan
```

## Key Features
### Multi-step Single Agent Loop
The agent follows a multi-step tool-calling loop to gather context and generate planning intents.

```text
User Query
    ↓
LLM Tool Calling
    ↓
Tool Results
    ↓
Planning Intent Generation
```

### Deterministic Scheduler
The backend scheduler converts high level planning intents into concrete schedules while enforcing deterministic constraints.

#### Current capabilities:
- calendar-aware scheduling
- priority-based task placement
- preferred time windows
- `not_before` constraint
- duration overrides
- skipped and unscheduled task handling

#### Example Scheduling Logic:  
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
    ↓
structured final plan
```

### Deterministic Validation  
A deterministic validation layer verifies that generated schedules satisfy hard constraints before returning results. 

#### Current validations include:  
- valid time intervals
- overlap detection
- calendar conflict detection
- duration correctness
- `not_before`constraint validation
- todo coverage validation

The validator acts as a guardrail between schedule generation and final output.

### Normalization
A normalization layer converts the validated raw plan into a structured and user-friendly plan.  

This layer generates a consistent response format, planning summary, and chronologically ordered schedule.

### Runtime Trace
The agent generates structured runtime traces for every execution.  

Each trace captures:  
- user query
- execution status
- planning intents
- scheduled tasks
- unscheduled tasks
- skipped tasks
- validation results

Runtime traces serve as the foundation for debugging, validation, and offline evaluation.

### Evaluation Pipeline
The project includes an end-to-end evaluation pipeline built on golden test cases.  

Components:
- golden dataset `gold_data.jsonl`
- runtime trace collection
- expected vs actual comparison
- failure categorization
- summary report generation

The evaluation framework validates both agent behavior and scheduler correctness, enabling systematic failure analysis and iterative improvement.

## Key Engineering Insights
### not_before Constraint Hallucination

Evaluation revealed that the dominant failure mode was `not_before` hallucination.

The planner frequently inferred temporal constraints that were never explicitly requested by users. In many cases, relative ordering instructions such as "first", "then", or "after that" were incorrectly converted into absolute time constraints.

This exposed a **planner-scheduler boundary violation**, where the planner implicitly performed scheduling decisions instead of purely extracting user intent.  

### Mitigation
Prompt-based mitigation alone was insufficient to reliably prevent `not_before` hallucination.

For MVP scope, a deterministic query-level cleanup layer was introduced before scheduling. If a user query contains no explicit temporal anchor, all generated `not_before` constraints are removed before scheduling.

This conservative approach significantly reduced hallucinated constraints without introducing an additional LLM-based judge.

### Result
On the current evaluation dataset, the mitigation reduced `not_before` hallucination from 6 cases to 1 case and improved supported pass rate from 63.64% to 86.36%.

---

### LLM Reliability Requires Backend Guardrails
During development, several reliability issues surfaced:  
- structured output constraints were not always respected
- required context was not always retrieved
- repair loops did not consistently converge

Instead of relying solely on prompt engineering, deterministic backend guardrails were introduced, including:
- context completion
- validation
- normalization
- query-level constraint cleanup

This shifted critical correctness guarantees from the LLM to backend systems, resulting in a more reliable and debuggable architecture.


## Architecture Evolution: LLM-heavy Planning vs Hybrid Systems
### Iteration 1: LLM-heavy Planning

LLM generates:
- task todo_id
- task start time
- task end time

Problems:
- repair loops did not consistently converge
- scheduling constraints were difficult to enforce reliably

---
### Iteration 2: Hybrid Architecture

The hybrid architecture moves deterministic planning logic into backend systems and removes the LLM from direct schedule generation. 

LLM responsibilities:
- understand user intent
- prioritize tasks
- reason about user preferences
- generate high-level planning intent

Backend responsibilities:
- intent cleanup
- context completion
- deterministic scheduling
- interval allocation
- overlap prevention
- constraint validation
- final schedule generation

This transition reflects a common industrial pattern in production AI systems:

> LLMs handle reasoning. Backend systems enforce correctness.


## FastAPI Service
This project exposes the Lifestyle Planner Agent as a local FastAPI service for programmatic access and integration.

The API exposes a single planning endpoint that returns both the final plan and runtime trace.

#### Run Locally
```bash
pip install -r requirements.txt
python -m uvicorn app:app --reload
```

#### Swagger UI:
```text
http://127.0.0.1:8000/docs
```

#### Service Flow
```text
Client Request
    ↓
FastAPI Endpoint
    ↓
run_agent()
    ↓
LLM Planning Intent Extraction
    ↓
Intent Cleanup
    ↓
Context Completion
    ↓
Deterministic Scheduler
    ↓
Validation Layer
    ↓
Normalization
    ↓
Runtime Trace + JSON Response
```

#### Notes:
The FastAPI layer is intentionally thin. Core planning logic remains inside run_agent(), while the API layer handles request parsing, response formatting, and exposing the agent as a local backend service.

## Future improvements:
- parallel tool calling to reduce overall latency
- Task-level grounding validation for temporal constraints
- Support for task splitting across multiple free intervals
- Additional scheduling constraints such as `not_after`
- Cloud deployment beyond local FastAPI service