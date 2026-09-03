from agents.agent_loop import AgentLoop
from tools.base import BaseTool


class FailingTool(BaseTool):
    name = "failing_tool"
    description = "A test tool that intentionally fails."

    def execute(self, arguments):
        raise RuntimeError("Simulated tool failure")


class FakeGenerate:
    def __init__(self):
        self.calls = 0
        self.prompts = []

    def __call__(self, prompt, model):
        self.calls += 1
        self.prompts.append(prompt)

        if self.calls == 1:
            return """
ACTION: tool
NAME: failing_tool
ARGUMENTS: test
"""

        return """
ACTION: final
CONTENT: The tool failed, but the agent recovered successfully.
"""


def main():
    print("=" * 60)
    print("AGENT LOOP TOOL ERROR RECOVERY TEST")
    print("=" * 60)

    failing_tool = FailingTool()
    fake_generate = FakeGenerate()

    import agents.agent_loop as agent_loop_module

    original_generate = agent_loop_module.generate

    agent_loop_module.generate = fake_generate

    try:
        loop = AgentLoop(
            system_prompt="You are a test agent.",
            model="qwen3:1.7b",
            tools={
                "failing_tool": failing_tool
            },
            max_steps=5
        )

        result = loop.run(
            "Use the failing tool and recover from any error."
        )

        print("\nFINAL RESULT:")
        print(result)

        print("\nLLM CALLS:", fake_generate.calls)

        print("\nSECOND PROMPT:")
        print(fake_generate.prompts[1])

        assert result == (
            "The tool failed, but the agent recovered successfully."
        )

        assert fake_generate.calls == 2

        assert "tool_error" in fake_generate.prompts[1]
        assert "failing_tool" in fake_generate.prompts[1]
        assert "Simulated tool failure" in fake_generate.prompts[1]

        print("\n" + "=" * 60)
        print("ERROR RECOVERY TEST PASSED")
        print("=" * 60)

    finally:
        agent_loop_module.generate = original_generate


if __name__ == "__main__":
    main()