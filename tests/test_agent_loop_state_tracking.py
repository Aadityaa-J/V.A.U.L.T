from agents.agent_loop import AgentLoop
from tools.base import BaseTool


class FakeTool(BaseTool):
    name = "test_tool"
    description = "Returns a test result."

    def execute(self, arguments):
        return "TEST_RESULT"


class FakeGenerate:
    def __init__(self):
        self.calls = 0

    def __call__(self, prompt, model):
        self.calls += 1

        if self.calls == 1:
            return """
ACTION: tool
NAME: test_tool
ARGUMENTS: test
"""

        return """
ACTION: final
CONTENT: State tracking works.
"""


def main():
    print("=" * 60)
    print("AGENT LOOP STATE TRACKING TEST")
    print("=" * 60)

    fake_tool = FakeTool()
    fake_generate = FakeGenerate()

    import agents.agent_loop as agent_loop_module

    original_generate = agent_loop_module.generate

    agent_loop_module.generate = fake_generate

    try:
        loop = AgentLoop(
            system_prompt="You are a test agent.",
            model="qwen3:1.7b",
            tools={
                "test_tool": fake_tool
            },
            max_steps=5
        )

        result = loop.run(
            "Run the test tool."
        )

        print("\nFINAL RESULT:")
        print(result)

        print("\nEXECUTION STATE:")
        print(loop.last_state)

        assert result == "State tracking works."

        assert len(loop.last_state["steps"]) == 2

        assert loop.last_state["steps"][0]["step"] == 1

        assert (
            loop.last_state["steps"][0]["action"]["type"]
            == "tool"
        )

        assert (
            loop.last_state["steps"][0]["observation"]["type"]
            == "tool_result"
        )

        assert loop.last_state["steps"][1]["step"] == 2

        assert (
            loop.last_state["steps"][1]["action"]["type"]
            == "final"
        )

        assert loop.last_state["steps"][1]["observation"] is None

        print("\n" + "=" * 60)
        print("STATE TRACKING TEST PASSED")
        print("=" * 60)

    finally:
        agent_loop_module.generate = original_generate


if __name__ == "__main__":
    main()