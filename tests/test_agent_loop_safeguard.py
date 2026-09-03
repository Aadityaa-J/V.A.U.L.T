from agents.agent_loop import AgentLoop
from tools.base import BaseTool


class RepeatingTool(BaseTool):
    name = "repeating_tool"
    description = "A test tool used to detect repeated calls."

    def execute(self, arguments):
        return "Tool executed."


class FakeGenerate:
    def __init__(self):
        self.calls = 0

    def __call__(self, prompt, model):
        self.calls += 1

        return """
ACTION: tool
NAME: repeating_tool
ARGUMENTS: same_argument
"""


def main():
    print("=" * 60)
    print("AGENT LOOP REPEATED TOOL SAFEGUARD TEST")
    print("=" * 60)

    repeating_tool = RepeatingTool()
    fake_generate = FakeGenerate()

    import agents.agent_loop as agent_loop_module

    original_generate = agent_loop_module.generate

    agent_loop_module.generate = fake_generate

    try:
        loop = AgentLoop(
            system_prompt="You are a test agent.",
            model="qwen3:1.7b",
            tools={
                "repeating_tool": repeating_tool
            },
            max_steps=5
        )

        result = loop.run(
            "Keep using the same tool."
        )

        print("\nFINAL RESULT:")
        print(result)

        print("\nLLM CALLS:", fake_generate.calls)

        print("\nEXECUTION STATE:")
        print(loop.last_state)

        assert result == (
            "Agent stopped because a repeated "
            "identical tool call was detected."
        )

        assert fake_generate.calls == 2

        assert len(loop.last_state["steps"]) == 2

        assert (
            loop.last_state["steps"][1]["observation"]["type"]
            == "tool_error"
        )

        assert (
            "Repeated identical tool call"
            in loop.last_state["steps"][1]["observation"]["error"]
        )

        print("\n" + "=" * 60)
        print("REPEATED TOOL SAFEGUARD TEST PASSED")
        print("=" * 60)

    finally:
        agent_loop_module.generate = original_generate


if __name__ == "__main__":
    main()