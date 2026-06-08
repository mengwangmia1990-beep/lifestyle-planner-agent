from fastapi import FastAPI
from pydantic import BaseModel
import json

from agent import run_agent

class PlanRequest(BaseModel):
    user_input: str

app = FastAPI(
    title = "Lifestyle Daily Planner Agent",
    version = "0.1.0"
)

@app.post("/plan-day")
def plan_day(request: PlanRequest):
    user_input = request.user_input.strip()

    if not user_input:
        return {
            "response": {
                "status": "failed",
                "summary": "User input cannot be empty.",
                "plan": {
                    "scheduled": [],
                    "unscheduled": [],
                    "skipped": []
                }
            },
            "trace": None
        }
    
    response, trace, tool_results = run_agent(user_input)

    try:
        response_dict = json.loads(response)
    except json.JSONDecodeError:
        return {
            "response": {
                "status": "failed",
                "summary": f"Failed to decode response {response}",
                "plan": {
                    "scheduled": [],
                    "unscheduled": [],
                    "skipped": []
                }
            },
            "trace": None            
        }
    
    return {
        "response": response_dict,
        "trace": trace
    }