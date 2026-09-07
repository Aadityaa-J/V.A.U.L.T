from agents.agent_loop import AgentLoop
from tools.registry import ToolRegistry
from tools.adapters import CalculateTool


def main():

    print()
    print("=" * 60)
    print("V.A.U.L.T. AGENT LOOP TEST")
    print("=" * 60)

    registry = ToolRegistry()

    registry.register(
        CalculateTool()
    )

    tools = {
        "calculate": registry.get(
            "calculate"
        )
    }

    agent = AgentLoop(
        system_prompt="""
You are a helpful AI assistant.

If the user asks for a mathematical calculation,
use the calculate tool.

For normal questions, answer naturally.
""",
        model="qwen3:1.7b",
        tools=tools,
        max_steps=5,
    )

    print()
    print("TEST 1: CALCULATION")
    print("-" * 60)

    task = "Calculate 25 * 48"

    print("USER:", task)
    print()

    result = agent.run(task)

    print("V.A.U.L.T.:")
    print(result)

    print()
    print("TEST 2: NORMAL QUESTION")
    print("-" * 60)

    task = "What is artificial intelligence?"

    print("USER:", task)
    print()

    result = agent.run(task)

    print("V.A.U.L.T.:")
    print(result)

    print()
    print("=" * 60)
    print("AGENT LOOP TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()