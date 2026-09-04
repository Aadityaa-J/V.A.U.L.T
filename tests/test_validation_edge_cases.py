from agents.validation_loop import ValidationLoop


class PassReviewer:
    def __init__(self):
        self.calls = []

    def review(self, task, result):
        self.calls.append(result)

        return {
            "verdict": "PASS",
            "reason": "Result is acceptable.",
            "corrections": "",
            "raw_response": ""
        }


class ReviseAfterHumanReviewer:
    def __init__(self):
        self.calls = []

    def review(self, task, result):
        self.calls.append(result)

        if len(self.calls) == 1:
            return {
                "verdict": "PASS",
                "reason": "Initial result is acceptable.",
                "corrections": "",
                "raw_response": ""
            }

        return {
            "verdict": "REVISE",
            "reason": "The result still contains an issue.",
            "corrections": "Correct the remaining issue.",
            "raw_response": ""
        }


def test_empty_human_input_does_not_change_result():

    reviewer = PassReviewer()

    loop = ValidationLoop(
        reviewer=reviewer
    )

    revisions = []

    def fake_revision(
        task,
        result,
        feedback
    ):
        revisions.append(feedback)
        return "Unexpected revision"

    state = loop.run(
        task="Test task",
        initial_result="Original result",
        generate_revision=fake_revision,
        human_input={
            "status": "none",
            "input": ""
        }
    )

    assert state["status"] == "validated"

    assert state["final_result"] == (
        "Original result"
    )

    assert revisions == []

    assert reviewer.calls == [
        "Original result"
    ]


def test_human_approval_does_not_trigger_revision():

    reviewer = PassReviewer()

    loop = ValidationLoop(
        reviewer=reviewer
    )

    revisions = []

    def fake_revision(
        task,
        result,
        feedback
    ):
        revisions.append(feedback)
        return "Should not happen"

    state = loop.run(
        task="Test task",
        initial_result="Validated result",
        generate_revision=fake_revision,
        human_input={
            "status": "approve",
            "input": "Approved."
        }
    )

    assert state["status"] == (
        "human_approved"
    )

    assert state["final_result"] == (
        "Validated result"
    )

    assert revisions == []

    assert reviewer.calls == [
        "Validated result"
    ]


def test_human_feedback_is_re_reviewed():

    reviewer = PassReviewer()

    loop = ValidationLoop(
        reviewer=reviewer
    )

    def fake_revision(
        task,
        result,
        feedback
    ):
        return "Revised result"

    state = loop.run(
        task="Engineering task",
        initial_result="Initial result",
        generate_revision=fake_revision,
        human_input={
            "status": "feedback",
            "input": "Use the corrected measurement."
        }
    )

    assert state["status"] == (
        "human_feedback_validated"
    )

    assert state["final_result"] == (
        "Revised result"
    )

    assert reviewer.calls == [
        "Initial result",
        "Revised result"
    ]


def test_failed_post_human_review_is_not_marked_validated():

    reviewer = ReviseAfterHumanReviewer()

    loop = ValidationLoop(
        reviewer=reviewer
    )

    def fake_revision(
        task,
        result,
        feedback
    ):
        return "Human revised result"

    state = loop.run(
        task="Engineering task",
        initial_result="Initial result",
        generate_revision=fake_revision,
        human_input={
            "status": "feedback",
            "input": "Recheck the calculation."
        }
    )

    assert state["status"] == (
        "requires_further_review"
    )

    assert state["final_result"] == (
        "Human revised result"
    )

    assert reviewer.calls == [
        "Initial result",
        "Human revised result"
    ]


if __name__ == "__main__":

    test_empty_human_input_does_not_change_result()
    test_human_approval_does_not_trigger_revision()
    test_human_feedback_is_re_reviewed()
    test_failed_post_human_review_is_not_marked_validated()

    print(
        "All validation edge-case tests passed."
    )