from agents.orchestrator import Orchestrator


class FakeValidationLoop:
    """
    Deterministic validation loop used only for testing
    orchestrator integration.
    """

    def __init__(self):
        self.calls = []

    def run(
        self,
        task,
        initial_result,
        human_input=None,
        task_type="engineering"
    ):
        self.calls.append({
            "task": task,
            "initial_result": initial_result,
            "human_input": human_input,
            "task_type": task_type
        })

        return {
            "task": task,
            "task_type": task_type,
            "final_result": (
                "VALIDATED RESULT: "
                + initial_result
            ),
            "status": "validated",
            "reviews": [
                {
                    "review_number": 1,
                    "phase": "ai_review",
                    "review": {
                        "verdict": "PASS",
                        "reason": "Test validation passed.",
                        "corrections": "",
                        "raw_response": ""
                    }
                }
            ],
            "human_interventions": []
        }


class FakeAgent:
    """
    Deterministic fake agent so this test does not
    depend on an actual LLM response.
    """

    def __init__(self):
        self.tools = {}

    def run(self, task, conversation_history=None):
        return "DRAFT RESULT"


class FakeClassifier:
    def classify(self, task):
        return "engineering"


def main():
    print("=" * 60)
    print("ORCHESTRATOR + VALIDATION LOOP INTEGRATION TEST")
    print("=" * 60)

    fake_validation = FakeValidationLoop()

    orchestrator = Orchestrator(
        validation_loop=fake_validation
    )

    # Replace only the components needed for deterministic testing.
    orchestrator.classifier = FakeClassifier()
    orchestrator.agents["engineering"] = FakeAgent()

    task = "Calculate the pump efficiency."

    print("\nTask:")
    print(task)

    result = orchestrator.run(task)

    print("\nFinal result:")
    print(result)

    # Verify that the orchestrator returned the
    # validated result rather than the raw draft.
    assert result == "VALIDATED RESULT: DRAFT RESULT"

    # Verify that ValidationLoop was actually called.
    assert len(fake_validation.calls) == 1

    call = fake_validation.calls[0]

    assert call["task"] == task
    assert call["initial_result"] == "DRAFT RESULT"
    assert call["task_type"] == "engineering"
    assert call["human_input"] is None

    print("\nValidationLoop received:")
    print("  Task:", call["task"])
    print("  Initial result:", call["initial_result"])
    print("  Task type:", call["task_type"])

    print("\n" + "=" * 60)
    print("ORCHESTRATOR + VALIDATION LOOP TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()