from agents.agent_loop import AgentLoop
from tools.base import BaseTool


class FirstTool(BaseTool):
    name = "get_value"
    description = "Returns a known test value."

    def execute(self, arguments):
        return "VALUE_FROM_FIRST_TOOL"


class SecondTool(BaseTool):
    name = "use_value"
    description = "Uses the value obtained from the previous step."

    def execute(self, arguments):
        if "VALUE_FROM_FIRST_TOOL" in arguments:
            return "SECOND_TOOL_CONFIRMED_STATE"
        
        return "SECOND_TOOL_DID_NOT_RECEIVE_STATE"


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
NAME: get_value
ARGUMENTS: retrieve value
"""

        if self.calls == 2:
            return """
ACTION: tool
NAME: use_value
ARGUMENTS: VALUE_FROM_FIRST_TOOL
"""

        return """
ACTION: final
CONTENT: State propagation confirmed successfully.
"""


def main():
    print("=" * 60)
    print("AGENT LOOP STATE PROPAGATION TEST")
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
                "get_value": first_tool,
                "use_value": second_tool,
            },
            max_steps=5
        )

        result = loop.run(
            "Retrieve a value and then use it."
        )

        print("\nFINAL RESULT:")
        print(result)

        print("\nLLM CALLS:", fake_generate.calls)

        print("\nSECOND PROMPT:")
        print(fake_generate.prompts[1])

        print("\nTHIRD PROMPT:")
        print(fake_generate.prompts[2])

        assert fake_generate.calls == 3

        assert (
            "VALUE_FROM_FIRST_TOOL"
            in fake_generate.prompts[1]
        )

        assert (
            "VALUE_FROM_FIRST_TOOL"
            in fake_generate.prompts[2]
        )

        assert (
            "SECOND_TOOL_CONFIRMED_STATE"
            in fake_generate.prompts[2]
        )

        assert result == (
            "State propagation confirmed successfully."
        )

        print("\n" + "=" * 60)
        print("STATE PROPAGATION TEST PASSED")
        print("=" * 60)

    finally:
        agent_loop_module.generate = original_generate


if __name__ == "__main__":
    main()