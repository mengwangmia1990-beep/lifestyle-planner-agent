import os
from agent import run_agent

# main responsibilities:
# 1. Handle user input and output

def main():
    print("AI: Please enter your request:")
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["exit", "quit"]:
            print("AI: Goodbye!")
            break
        
        user_input = user_input.strip().lower()
        
        if not user_input:
            print("AI: Please enter a valid request.")
            continue

        response = run_agent(user_input)
        print(f"AI: {response}")


if __name__ == "__main__":
    main()