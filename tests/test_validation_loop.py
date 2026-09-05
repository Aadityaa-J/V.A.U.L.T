from agents.validation_loop import ValidationLoop


class FakeReviewer:

    def __init__(self):
        self.calls = 0

    def review(
        self,
        task,
        result
    ):
        self.calls += 1

        if self.calls == 1:
            return {
                "verdict": "REVISE",
                "reason": "The result needs correction.",
                "corrections": "Fix the stated value.",
                "raw_response": ""
            }

        return {
            "verdict": "PASS",
            "reason": "The revised result is acceptable.",
            "corrections": "",
            "raw_response": ""
        }


def test_revision_loop_revises_and_passes():

    reviewer = FakeReviewer()

    loop = ValidationLoop(
        reviewer=reviewer,
        max_reviews=2
    )

    revisions = []

    def fake_revision(
        task,
        result,
        feedback
    ):
        revisions.append({
            "task": task,
            "result": result,
            "feedback": feedback
        })

        return "Revised result"

    state = loop.run(
        task="Calculate something",
        initial_result="Initial result",
        generate_revision=fake_revision
    )

    assert state["status"] == "validated"

    assert state["final_result"] == (
        "Revised result"
    )

    assert len(state["reviews"]) == 2

    assert len(revisions) == 1

    assert (
        "Fix the stated value."
        in revisions[0]["feedback"]
    )


def test_revision_loop_stops_at_limit():

    class AlwaysReviseReviewer:

        def review(
            self,
            task,
            result
        ):
            return {
                "verdict": "REVISE",
                "reason": "Needs another revision.",
                "corrections": "Change something.",
                "raw_response": ""
            }

    loop = ValidationLoop(
        reviewer=AlwaysReviseReviewer(),
        max_reviews=2
    )

    state = loop.run(
        task="Test",
        initial_result="Initial",
        generate_revision=lambda task, result, feedback: (
            "Revised"
        )
    )

    assert state["status"] == (
        "review_limit_reached"
    )

    assert len(state["reviews"]) == 2


def test_pass_requires_no_revision():

    class PassReviewer:

        def review(
            self,
            task,
            result
        ):
            return {
                "verdict": "PASS",
                "reason": "Looks correct.",
                "corrections": "",
                "raw_response": ""
            }

    loop = ValidationLoop(
        reviewer=PassReviewer()
    )

    state = loop.run(
        task="Test",
        initial_result="Correct result"
    )

    assert state["status"] == "validated"

    assert state["final_result"] == (
        "Correct result"
    )

    assert len(state["reviews"]) == 1


def test_human_approval():

    class PassReviewer:

        def review(
            self,
            task,
            result
        ):
            return {
                "verdict": "PASS",
                "reason": "Looks correct.",
                "corrections": "",
                "raw_response": ""
            }

    loop = ValidationLoop(
        reviewer=PassReviewer()
    )

    state = loop.run(
        task="Engineering task",
        initial_result="Correct result",
        human_input={
            "status": "approve",
            "input": "Approved by engineer."
        }
    )

    assert state["status"] == (
        "human_approved"
    )

    assert state["final_result"] == (
        "Correct result"
    )

    assert len(
        state["human_interventions"]
    ) == 1


def test_human_feedback_triggers_revision_and_rereview():

    class TrackingReviewer:

        def __init__(self):
            self.calls = []

        def review(
            self,
            task,
            result
        ):
            self.calls.append(result)

            return {
                "verdict": "PASS",
                "reason": "Looks correct.",
                "corrections": "",
                "raw_response": ""
            }

    reviewer = TrackingReviewer()

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

        return "Human-corrected result"

    state = loop.run(
        task="Engineering task",
        initial_result="Initial result",
        generate_revision=fake_revision,
        human_input={
            "status": "feedback",
            "input": (
                "Recheck the pressure measurement."
            )
        }
    )

    assert state["status"] == (
        "human_feedback_validated"
    )

    assert state["final_result"] == (
        "Human-corrected result"
    )

    assert len(revisions) == 1

    assert (
        revisions[0]
        == "Recheck the pressure measurement."
    )

    assert reviewer.calls[0] == (
        "Initial result"
    )

    assert reviewer.calls[1] == (
        "Human-corrected result"
    )

    assert len(reviewer.calls) == 2

    assert len(
        state["reviews"]
    ) == 2


def test_human_rejection_triggers_revision_and_rereview():

    class TrackingReviewer:

        def __init__(self):
            self.calls = []

        def review(
            self,
            task,
            result
        ):
            self.calls.append(result)

            return {
                "verdict": "PASS",
                "reason": "Looks correct.",
                "corrections": "",
                "raw_response": ""
            }

    reviewer = TrackingReviewer()

    loop = ValidationLoop(
        reviewer=reviewer
    )

    state = loop.run(
        task="Test",
        initial_result="Initial",
        generate_revision=(
            lambda task, result, feedback:
            "Revised after rejection"
        ),
        human_input={
            "status": "reject",
            "input": (
                "The operating condition "
                "is incorrect."
            )
        }
    )

    assert state["status"] == (
        "human_feedback_validated"
    )

    assert state["final_result"] == (
        "Revised after rejection"
    )

    assert reviewer.calls == [
        "Initial",
        "Revised after rejection"
    ]


def test_no_human_intervention():

    class PassReviewer:

        def review(
            self,
            task,
            result
        ):
            return {
                "verdict": "PASS",
                "reason": "Looks correct.",
                "corrections": "",
                "raw_response": ""
            }

    loop = ValidationLoop(
        reviewer=PassReviewer()
    )

    state = loop.run(
        task="Test",
        initial_result="Initial"
    )

    assert state["status"] == "validated"

    assert (
        state["human_interventions"]
        == []
    )


def test_task_type_is_preserved_in_validation_state():

    class PassReviewer:

        def review(
            self,
            task,
            result
        ):
            return {
                "verdict": "PASS",
                "reason": "Looks correct.",
                "corrections": "",
                "raw_response": ""
            }

    loop = ValidationLoop(
        reviewer=PassReviewer()
    )

    state = loop.run(
        task="Write Python code",
        initial_result="Code result",
        task_type="coding"
    )

    assert state["task_type"] == "coding"


if __name__ == "__main__":

    test_revision_loop_revises_and_passes()
    test_revision_loop_stops_at_limit()
    test_pass_requires_no_revision()
    test_human_approval()
    test_human_feedback_triggers_revision_and_rereview()
    test_human_rejection_triggers_revision_and_rereview()
    test_no_human_intervention()
    test_task_type_is_preserved_in_validation_state()

    print(
        "All validation loop tests passed."
    )