from agents.agent_loop import AgentLoop


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
NAME: nonexistent_tool
ARGUMENTS: test
"""

        return """
ACTION: final
CONTENT: The unavailable tool was handled successfully.
"""


def main():
    print("=" * 60)
    print("AGENT LOOP UNKNOWN TOOL TEST")
    print("=" * 60)

    fake_generate = FakeGenerate()

    import agents.agent_loop as agent_loop_module

    original_generate = agent_loop_module.generate

    agent_loop_module.generate = fake_generate

    try:
        loop = AgentLoop(
            system_prompt="You are a test agent.",
            model="qwen3:1.7b",
            tools={},
            max_steps=5
        )

        result = loop.run(
            "Try to use an unavailable tool and recover."
        )

        print("\nFINAL RESULT:")
        print(result)

        print("\nLLM CALLS:", fake_generate.calls)

        print("\nSECOND PROMPT:")
        print(fake_generate.prompts[1])

        assert fake_generate.calls == 2

        assert result == (
            "The unavailable tool was handled successfully."
        )

        assert "tool_error" in fake_generate.prompts[1]
        assert "nonexistent_tool" in fake_generate.prompts[1]
        assert "Tool is not available." in fake_generate.prompts[1]

        print("\n" + "=" * 60)
        print("UNKNOWN TOOL TEST PASSED")
        print("=" * 60)

    finally:
        agent_loop_module.generate = original_generate


if __name__ == "__main__":
    main()