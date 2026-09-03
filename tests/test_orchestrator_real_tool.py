from agents.orchestrator import Orchestrator


def fake_generate(prompt: str, model: str) -> str:
    """
    Simulate an LLM choosing a calculator tool first,
    then returning a final answer after receiving
    the tool observation.
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
CONTENT: The calculation result is 1000.
"""


fake_generate.calls = 0


def main():
    print("=" * 60)
    print("FULL ORCHESTRATOR + REAL TOOL TEST")
    print("=" * 60)

    # Patch the generate function used by AgentLoop.
    import agents.agent_loop as agent_loop_module

    original_generate = agent_loop_module.generate

    # Patch task classification so the test always
    # routes to the Engineering Agent.
    import agents.task_classifier as classifier_module

    original_classify = classifier_module.TaskClassifier.classify

    try:
        agent_loop_module.generate = fake_generate

        def fake_classify(self, task):
            return "engineering"

        classifier_module.TaskClassifier.classify = (
            fake_classify
        )

        orchestrator = Orchestrator()

        result = orchestrator.run(
            "What is 125 multiplied by 8?"
        )

        print("\nFINAL RESULT:")
        print(result)

        print("\nLLM CALLS:")
        print(fake_generate.calls)

        assert result == (
            "The calculation result is 1000."
        )

        assert fake_generate.calls == 2

        engineering_tools = (
            orchestrator._get_agent_tools(
                "engineering"
            )
        )

        assert "calculate" in engineering_tools

        print("\nENGINEERING TOOLS:")
        print(list(engineering_tools.keys()))

        print("\n" + "=" * 60)
        print(
            "FULL ORCHESTRATOR + REAL TOOL TEST PASSED"
        )
        print("=" * 60)

    finally:
        agent_loop_module.generate = original_generate

        classifier_module.TaskClassifier.classify = (
            original_classify
        )


if __name__ == "__main__":
    main()