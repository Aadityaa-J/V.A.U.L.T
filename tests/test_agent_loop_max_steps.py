from agents.agent_loop import AgentLoop
from tools.base import BaseTool


class EndlessTool(BaseTool):
    name = "endless_tool"
    description = "A test tool that always returns a result."

    def execute(self, arguments):
        return f"Tool executed with: {arguments}"


class FakeGenerate:
    def __init__(self):
        self.calls = 0

    def __call__(self, prompt, model):
        self.calls += 1

        return f"""
ACTION: tool
NAME: endless_tool
ARGUMENTS: continue_{self.calls}
"""


def main():
    print("=" * 60)
    print("AGENT LOOP MAX-STEP TEST")
    print("=" * 60)

    endless_tool = EndlessTool()
    fake_generate = FakeGenerate()

    import agents.agent_loop as agent_loop_module

    original_generate = agent_loop_module.generate

    agent_loop_module.generate = fake_generate

    try:
        max_steps = 3

        loop = AgentLoop(
            system_prompt="You are a test agent.",
            model="qwen3:1.7b",
            tools={
                "endless_tool": endless_tool
            },
            max_steps=max_steps
        )

        result = loop.run(
            "Keep using the tool."
        )

        print("\nFINAL RESULT:")
        print(result)

        print("\nLLM CALLS:", fake_generate.calls)

        print("\nEXECUTION STATE:")
        print(loop.last_state)

        assert fake_generate.calls == max_steps

        assert result == (
            "Agent stopped because the maximum "
            "number of steps was reached."
        )

        assert len(loop.last_state["steps"]) == max_steps

        print("\n" + "=" * 60)
        print("MAX-STEP TEST PASSED")
        print("=" * 60)

    finally:
        agent_loop_module.generate = original_generate


if __name__ == "__main__":
    main()