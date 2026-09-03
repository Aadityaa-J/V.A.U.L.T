from agents.orchestrator import Orchestrator


class FakeClassifier:
    """
    Avoid using the real LLM classifier.
    """

    def classify(self, task: str) -> str:
        return "engineering"


class FakeAgent:
    """
    Simple agent for testing session integration.
    """

    def __init__(self):
        self.tools = {}

    def run(self, task: str) -> str:
        return f"Processed task: {task}"


def main():
    print("=" * 60)
    print("ORCHESTRATOR SESSION INTEGRATION TEST")
    print("=" * 60)

    orchestrator = Orchestrator()

    # Replace LLM-dependent components.
    orchestrator.classifier = FakeClassifier()

    orchestrator.agents["engineering"] = FakeAgent()

    # --------------------------------------------------
    # TEST 1: INITIAL SESSION
    # --------------------------------------------------

    print("\nTEST 1: INITIAL SESSION")

    history = orchestrator.get_session_history()

    print(history)

    assert history == []

    print("PASSED")

    # --------------------------------------------------
    # TEST 2: FIRST TASK
    # --------------------------------------------------

    print("\nTEST 2: FIRST TASK")

    result = orchestrator.run(
        "Calculate something"
    )

    print("RESULT:")
    print(result)

    history = orchestrator.get_session_history()

    print("\nHISTORY:")
    print(history)

    assert len(history) == 2

    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Calculate something"

    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == result

    print("PASSED")

    # --------------------------------------------------
    # TEST 3: SECOND TASK
    # --------------------------------------------------

    print("\nTEST 3: SECOND TASK")

    result = orchestrator.run(
        "Perform another calculation"
    )

    print("RESULT:")
    print(result)

    history = orchestrator.get_session_history()

    print("\nHISTORY:")
    print(history)

    assert len(history) == 4

    assert history[2]["role"] == "user"
    assert history[3]["role"] == "assistant"

    print("PASSED")

    # --------------------------------------------------
    # TEST 4: CLEAR SESSION
    # --------------------------------------------------

    print("\nTEST 4: CLEAR SESSION")

    orchestrator.clear_session()

    history = orchestrator.get_session_history()

    print(history)

    assert history == []

    print("PASSED")

    print("\n" + "=" * 60)
    print("ORCHESTRATOR SESSION INTEGRATION PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()