from agents.orchestrator import Orchestrator


class FakeClassifier:
    """
    Avoid using the real LLM classifier.
    """

    def classify(self, task: str) -> str:
        return "engineering"


class ContextCheckingAgent:
    """
    Fake agent that records the conversation history
    it receives from the orchestrator.
    """

    def __init__(self):
        self.tools = {}
        self.received_history = []

    def run(
        self,
        task: str,
        conversation_history=None
    ) -> str:

        self.received_history = (
            conversation_history or []
        )

        return f"Processed: {task}"


def main():
    print("=" * 60)
    print("ORCHESTRATOR CONVERSATION CONTEXT TEST")
    print("=" * 60)

    orchestrator = Orchestrator()

    # Replace LLM-dependent classifier.
    orchestrator.classifier = FakeClassifier()

    # Create our test agent.
    fake_agent = ContextCheckingAgent()

    orchestrator.agents["engineering"] = fake_agent

    # --------------------------------------------------
    # TEST 1: FIRST TASK
    # --------------------------------------------------

    print("\nTEST 1: FIRST TASK")

    result_1 = orchestrator.run(
        "My name is Alex."
    )

    print("RESULT:")
    print(result_1)

    # The first task should have no previous history.
    assert fake_agent.received_history == []

    print("PASSED")

    # --------------------------------------------------
    # TEST 2: SESSION AFTER FIRST TASK
    # --------------------------------------------------

    print("\nTEST 2: SESSION STORAGE")

    history = orchestrator.get_session_history()

    print("SESSION HISTORY:")
    print(history)

    assert len(history) == 2

    assert history[0]["role"] == "user"
    assert history[0]["content"] == "My name is Alex."

    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == result_1

    print("PASSED")

    # --------------------------------------------------
    # TEST 3: SECOND TASK RECEIVES HISTORY
    # --------------------------------------------------

    print("\nTEST 3: SECOND TASK")

    result_2 = orchestrator.run(
        "What is my name?"
    )

    print("RESULT:")
    print(result_2)

    received_history = fake_agent.received_history

    print("\nHISTORY RECEIVED BY AGENT:")
    print(received_history)

    # The agent should receive the conversation
    # that existed BEFORE the second task.
    assert len(received_history) == 2

    assert received_history[0]["role"] == "user"
    assert received_history[0]["content"] == "My name is Alex."

    assert received_history[1]["role"] == "assistant"
    assert received_history[1]["content"] == result_1

    print("PASSED")

    # --------------------------------------------------
    # TEST 4: SESSION AFTER SECOND TASK
    # --------------------------------------------------

    print("\nTEST 4: FINAL SESSION")

    final_history = (
        orchestrator.get_session_history()
    )

    print("FINAL HISTORY:")
    print(final_history)

    assert len(final_history) == 4

    assert final_history[2]["role"] == "user"
    assert final_history[2]["content"] == "What is my name?"

    assert final_history[3]["role"] == "assistant"
    assert final_history[3]["content"] == result_2

    print("PASSED")

    print("\n" + "=" * 60)
    print("END-TO-END CONVERSATION CONTEXT TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()