from agents.orchestrator import Orchestrator


class FakeValidationLoop:
    """
    Deterministic validation loop used only for testing
    human-in-the-loop integration.
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

        if human_input and human_input.get("status") == "feedback":
            final_result = (
                "REVISED RESULT: "
                "DRAFT RESULT updated using human feedback"
            )
            status = "human_feedback_validated"
        else:
            final_result = initial_result
            status = "validated"

        return {
            "task": task,
            "task_type": task_type,
            "final_result": final_result,
            "status": status,
            "reviews": [
                {
                    "review_number": 1,
                    "phase": "ai_review",
                    "review": {
                        "verdict": "PASS",
                        "reason": "Validation passed.",
                        "corrections": "",
                        "raw_response": ""
                    }
                }
            ],
            "human_interventions": [
                {
                    "status": human_input.get("status")
                    if human_input
                    else "none",
                    "input": human_input.get("input")
                    if human_input
                    else ""
                }
            ]
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
    print("ORCHESTRATOR + HUMAN INTERVENTION TEST")
    print("=" * 60)

    fake_validation = FakeValidationLoop()

    orchestrator = Orchestrator(
        validation_loop=fake_validation
    )

    orchestrator.classifier = FakeClassifier()
    orchestrator.agents["engineering"] = FakeAgent()

    task = "Calculate the pump efficiency."

    human_input = {
        "status": "feedback",
        "input": (
            "Use the measured efficiency value from the "
            "inspection report and explain the calculation."
        )
    }

    print("\nTask:")
    print(task)

    print("\nHuman feedback:")
    print(human_input["input"])

    result = orchestrator.run(
        task,
        human_input=human_input
    )

    print("\nFinal result:")
    print(result)

    # The orchestrator must return the result
    # produced after human feedback was supplied.
    assert result == (
        "REVISED RESULT: "
        "DRAFT RESULT updated using human feedback"
    )

    # ValidationLoop must have been called exactly once.
    assert len(fake_validation.calls) == 1

    call = fake_validation.calls[0]

    # Verify the original task and draft reached
    # the validation layer.
    assert call["task"] == task
    assert call["initial_result"] == "DRAFT RESULT"

    # Verify task-aware routing was preserved.
    assert call["task_type"] == "engineering"

    # Verify human feedback reached ValidationLoop.
    assert call["human_input"] == human_input

    print("\nValidationLoop received:")
    print("  Task:", call["task"])
    print("  Initial result:", call["initial_result"])
    print("  Task type:", call["task_type"])
    print("  Human status:", call["human_input"]["status"])
    print("  Human feedback:", call["human_input"]["input"])

    print("\n" + "=" * 60)
    print("ORCHESTRATOR + HUMAN INTERVENTION TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()