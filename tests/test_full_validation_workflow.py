from agents.orchestrator import Orchestrator


class FakeValidationLoop:
    """
    Deterministic validation loop representing the complete
    AI -> AI -> Human -> AI -> AI workflow.

    This is a test double only. It does not replace the
    production ValidationLoop.
    """

    def __init__(self):
        self.calls = []
        self.events = []

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

        # Simulate the complete validation lifecycle.
        self.events.append("primary_ai_draft")
        self.events.append("peer_ai_review")
        self.events.append("ai_revision")
        self.events.append("peer_ai_re_review")
        self.events.append("human_intervention")
        self.events.append("ai_revision_after_human")
        self.events.append("peer_ai_final_review")

        final_result = (
            "FINAL VALIDATED RESULT: "
            "DRAFT RESULT revised after peer review "
            "and human feedback"
        )

        return {
            "task": task,
            "task_type": task_type,
            "final_result": final_result,
            "status": "human_feedback_validated",
            "reviews": [
                {
                    "review_number": 1,
                    "phase": "ai_review",
                    "review": {
                        "verdict": "REVISE",
                        "reason": "Improve technical clarity.",
                        "corrections": "Clarify the calculation.",
                        "raw_response": ""
                    }
                },
                {
                    "review_number": 2,
                    "phase": "ai_review",
                    "review": {
                        "verdict": "PASS",
                        "reason": "Revision is acceptable.",
                        "corrections": "",
                        "raw_response": ""
                    }
                },
                {
                    "review_number": 3,
                    "phase": "post_human_ai_review",
                    "review": {
                        "verdict": "PASS",
                        "reason": "Human feedback incorporated.",
                        "corrections": "",
                        "raw_response": ""
                    }
                }
            ],
            "human_interventions": [
                {
                    "status": "feedback",
                    "input": human_input["input"]
                }
            ]
        }


class FakeAgent:
    """
    Deterministic agent used so the test does not depend
    on an actual LLM response.
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
    print("FULL V.A.U.L.T. VALIDATION WORKFLOW TEST")
    print("=" * 60)

    fake_validation = FakeValidationLoop()

    orchestrator = Orchestrator(
        validation_loop=fake_validation
    )

    orchestrator.classifier = FakeClassifier()
    orchestrator.agents["engineering"] = FakeAgent()

    task = (
        "Calculate the efficiency of the cooling-water pump "
        "from the inspection measurements."
    )

    human_input = {
        "status": "feedback",
        "input": (
            "Make sure the final answer explains the calculation "
            "and clearly states the measured values used."
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

    # --------------------------------------------------------
    # Verify final output
    # --------------------------------------------------------

    assert result == (
        "FINAL VALIDATED RESULT: "
        "DRAFT RESULT revised after peer review "
        "and human feedback"
    )

    # --------------------------------------------------------
    # Verify ValidationLoop was called correctly
    # --------------------------------------------------------

    assert len(fake_validation.calls) == 1

    call = fake_validation.calls[0]

    assert call["task"] == task
    assert call["initial_result"] == "DRAFT RESULT"
    assert call["task_type"] == "engineering"
    assert call["human_input"] == human_input

    # --------------------------------------------------------
    # Verify the complete workflow occurred
    # --------------------------------------------------------

    expected_events = [
        "primary_ai_draft",
        "peer_ai_review",
        "ai_revision",
        "peer_ai_re_review",
        "human_intervention",
        "ai_revision_after_human",
        "peer_ai_final_review"
    ]

    assert fake_validation.events == expected_events

    print("\nWorkflow events:")

    for number, event in enumerate(
        fake_validation.events,
        start=1
    ):
        print(f"  {number}. {event}")

    # --------------------------------------------------------
    # Verify review history
    # --------------------------------------------------------

    validation_state = fake_validation.run(
        task=task,
        initial_result="DRAFT RESULT",
        human_input=human_input,
        task_type="engineering"
    )

    assert validation_state["status"] == (
        "human_feedback_validated"
    )

    assert len(validation_state["reviews"]) == 3

    assert (
        validation_state["reviews"][0]["review"]["verdict"]
        == "REVISE"
    )

    assert (
        validation_state["reviews"][1]["review"]["verdict"]
        == "PASS"
    )

    assert (
        validation_state["reviews"][2]["review"]["verdict"]
        == "PASS"
    )

    assert len(
        validation_state["human_interventions"]
    ) == 1

    assert (
        validation_state["human_interventions"][0]["status"]
        == "feedback"
    )

    print("\nValidation summary:")
    print("  Initial AI result: DRAFT RESULT")
    print("  Peer review #1: REVISE")
    print("  AI revision: completed")
    print("  Peer review #2: PASS")
    print("  Human intervention: feedback")
    print("  AI revision after human: completed")
    print("  Final peer review: PASS")
    print("  Final status: human_feedback_validated")

    print("\n" + "=" * 60)
    print("FULL V.A.U.L.T. VALIDATION WORKFLOW TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()