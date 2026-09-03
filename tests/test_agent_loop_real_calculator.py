from agents.agent_loop import AgentLoop
from tools.adapters import CalculateTool


def fake_generate(prompt: str, model: str) -> str:
    """
    First call: choose the calculator.
    Second call: use the calculator observation
    and return the final answer.
    """

    fake_generate.calls += 1

    if fake_generate.calls == 1:
        return """
ACTION: tool
NAME: calculate
ARGUMENTS: 125 * 8
"""

    return """
ACTION: final
CONTENT: The result of 125 * 8 is 1000.
"""


fake_generate.calls = 0


def main():
    print("=" * 60)
    print("REAL AGENT LOOP + CALCULATOR TEST")
    print("=" * 60)

    # Import the module itself so we can temporarily
    # replace its generate function.
    import agents.agent_loop as agent_loop_module

    original_generate = agent_loop_module.generate

    try:
        agent_loop_module.generate = fake_generate

        loop = AgentLoop(
            system_prompt=(
                "You are a helpful engineering agent."
            ),
            model="test-model",
            tools={
                "calculate": CalculateTool(),
            },
            max_steps=5,
        )

        result = loop.run(
            "What is 125 multiplied by 8?"
        )

        print("\nFINAL RESULT:")
        print(result)

        print("\nLLM CALLS:")
        print(fake_generate.calls)

        print("\nLAST STATE:")
        print(loop.last_state)

        assert result == (
            "The result of 125 * 8 is 1000."
        )

        assert fake_generate.calls == 2

        observations = loop.last_state["observations"]

        assert len(observations) == 1

        observation = observations[0]

        assert observation["type"] == "tool_result"
        assert observation["tool"] == "calculate"
        assert observation["result"] == 1000

        print("\n" + "=" * 60)
        print(
            "REAL AGENT LOOP + CALCULATOR TEST PASSED"
        )
        print("=" * 60)

    finally:
        agent_loop_module.generate = original_generate


if __name__ == "__main__":
    main()