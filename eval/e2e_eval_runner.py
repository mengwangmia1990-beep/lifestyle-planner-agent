# End-to-End Evaluation Runner
# User input --> Final Concrete Plan

import os
import sys

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
sys.path.append(PROJECT_ROOT)

import config
from agent import run_agent
import json


def get_todo_ids(tasks):
    ids = []
    for task in tasks:
        if task["todo_id"]:
            ids.append(task["todo_id"])
    return ids


def main():
    with open(config.EVAL_DATA_FILE) as f: # per-case evaluation
        for line in f:
            data = json.loads(line)
            user_input = data["user_input"]
            print(user_input)

            # run agent and collect runtime trace log
            response = run_agent(user_input)
            try:
                structured_response = json.loads(response)
            except json.JSONDecodeError:
                print("Failed to load response into json")
                continue
            
            # TODO: compare with golden data
            # TODO: generate eval summary report
            # TODO: intent grounding check


if __name__ == "__main__":
    main()