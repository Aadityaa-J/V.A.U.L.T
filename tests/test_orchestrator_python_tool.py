from agents.orchestrator import Orchestrator


def fake_generate(prompt: str, model: str) -> str:
    """
    First call executes Python code.
    Second call returns a final answer.
    """

    fake_generate.calls += 1

    if fake_generate.calls == 1:
        return """
ACTION: tool
NAME: run_python
ARGUMENTS: print(25 * 4)
"""

    return """
ACTION: final
CONTENT: The Python code executed successfully and produced 100.
"""


fake_generate.calls = 0


def main():
    print("=" * 60)
    print("FULL ORCHESTRATOR + PYTHON TOOL TEST")
    print("=" * 60)

    import agents.agent_loop as agent_loop_module
    import agents.task_classifier as classifier_module

    original_generate = agent_loop_module.generate
    original_classify = (
        classifier_module.TaskClassifier.classify
    )

    try:
        # Replace the LLM with deterministic responses.
        agent_loop_module.generate = fake_generate

        # Force this test through the Coding Agent.
        def fake_classify(self, task):
            return "coding"

        classifier_module.TaskClassifier.classify = (
            fake_classify
        )

        orchestrator = Orchestrator()

        result = orchestrator.run(
            "Use Python to calculate 25 multiplied by 4."
        )

        print("\nFINAL RESULT:")
        print(result)

        print("\nLLM CALLS:")
        print(fake_generate.calls)

        assert result == (
            "The Python code executed successfully "
            "and produced 100."
        )

        assert fake_generate.calls == 2

        coding_tools = orchestrator._get_agent_tools(
            "coding"
        )

        print("\nCODING AGENT TOOLS:")
        print(list(coding_tools.keys()))

        assert "run_python" in coding_tools

        print("\n" + "=" * 60)
        print(
            "FULL ORCHESTRATOR + PYTHON TOOL TEST PASSED"
        )
        print("=" * 60)

    finally:
        # Always restore the real functions.
        agent_loop_module.generate = original_generate

        classifier_module.TaskClassifier.classify = (
            original_classify
        )


if __name__ == "__main__":
    main()