from agents.agent_loop import AgentLoop
from tools.base import BaseTool


class FirstTool(BaseTool):
    name = "first_tool"
    description = "Returns the first piece of information."

    def execute(self, arguments):
        return "First tool result: 50"


class SecondTool(BaseTool):
    name = "second_tool"
    description = "Uses the first result to produce another result."

    def execute(self, arguments):
        if arguments.strip() == "50 * 2":
            return "Second tool result: 100"

        return f"Unexpected arguments: {arguments}"


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
NAME: first_tool
ARGUMENTS: get value
"""

        if self.calls == 2:
            return """
ACTION: tool
NAME: second_tool
ARGUMENTS: 50 * 2
"""

        return """
ACTION: final
CONTENT: The final result is 100.
"""


def main():
    print("=" * 60)
    print("AGENT LOOP MULTI-TOOL TEST")
    print("=" * 60)

    first_tool = FirstTool()
    second_tool = SecondTool()
    fake_generate = FakeGenerate()

    import agents.agent_loop as agent_loop_module

    original_generate = agent_loop_module.generate

    agent_loop_module.generate = fake_generate

    try:
        loop = AgentLoop(
            system_prompt="You are a test agent.",
            model="qwen3:1.7b",
            tools={
                "first_tool": first_tool,
                "second_tool": second_tool,
            },
            max_steps=5
        )

        result = loop.run(
            "Use both tools to solve the task."
        )

        print("\nFINAL RESULT:")
        print(result)

        print("\nLLM CALLS:", fake_generate.calls)

        print("\nOBSERVATIONS:")
        for observation in loop.tools.values():
            print("-", observation.name)

        print("\nSECOND PROMPT:")
        print(fake_generate.prompts[1])

        print("\nTHIRD PROMPT:")
        print(fake_generate.prompts[2])

        assert result == "The final result is 100."

        assert fake_generate.calls == 3

        assert "First tool result: 50" in fake_generate.prompts[1]

        assert "First tool result: 50" in fake_generate.prompts[2]

        assert "Second tool result: 100" in fake_generate.prompts[2]

        print("\n" + "=" * 60)
        print("MULTI-TOOL TEST PASSED")
        print("=" * 60)

    finally:
        agent_loop_module.generate = original_generate


if __name__ == "__main__":
    main()