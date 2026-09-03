from agents.agent_loop import AgentLoop
from tools.base import BaseTool


class FakeCalculator(BaseTool):
    name = "calculate"
    description = "Performs a simple arithmetic calculation."

    def execute(self, arguments):
        if arguments.strip() == "25 * 4":
            return "100"

        return f"Unknown calculation: {arguments}"


class FakeGenerate:
    def __init__(self):
        self.calls = 0

    def __call__(self, prompt, model):
        self.calls += 1

        if self.calls == 1:
            return """
ACTION: tool
NAME: calculate
ARGUMENTS: 25 * 4
"""

        return """
ACTION: final
CONTENT: The calculation result is 100.
"""


def main():
    print("=" * 60)
    print("AGENT LOOP MULTI-STEP TOOL TEST")
    print("=" * 60)

    calculator = FakeCalculator()
    fake_generate = FakeGenerate()

    import agents.agent_loop as agent_loop_module

    original_generate = agent_loop_module.generate

    agent_loop_module.generate = fake_generate

    try:
        loop = AgentLoop(
            system_prompt="You are a test agent.",
            model="qwen3:1.7b",
            tools={
                "calculate": calculator
            },
            max_steps=5
        )

        result = loop.run(
            "Calculate 25 multiplied by 4."
        )

        print("\nFINAL RESULT:")
        print(result)

        print("\nLLM CALLS:", fake_generate.calls)

        assert result == "The calculation result is 100."
        assert fake_generate.calls == 2

        print("\n" + "=" * 60)
        print("MULTI-STEP TOOL TEST PASSED")
        print("=" * 60)

    finally:
        agent_loop_module.generate = original_generate


if __name__ == "__main__":
    main()