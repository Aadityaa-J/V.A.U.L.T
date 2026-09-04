from agents.human_intervention import HumanIntervention


def test_no_human_input():

    intervention = HumanIntervention()

    result = intervention.provide_input("")

    assert result["status"] == "none"
    assert result["input"] == ""


def test_human_feedback():

    intervention = HumanIntervention()

    result = intervention.provide_input(
        "Recheck the pressure measurement."
    )

    assert result["status"] == "feedback"

    assert result["input"] == (
        "Recheck the pressure measurement."
    )


def test_human_approval():

    intervention = HumanIntervention()

    result = intervention.approve(
        "Reviewed by engineer."
    )

    assert result["status"] == "approve"

    assert result["input"] == (
        "Reviewed by engineer."
    )


def test_human_rejection():

    intervention = HumanIntervention()

    result = intervention.reject(
        "The operating condition is incorrect."
    )

    assert result["status"] == "reject"

    assert result["input"] == (
        "The operating condition is incorrect."
    )


def test_clear_intervention():

    intervention = HumanIntervention()

    intervention.provide_input(
        "Additional context."
    )

    result = intervention.clear()

    assert result["status"] == "none"
    assert result["input"] == ""


def test_last_input():

    intervention = HumanIntervention()

    intervention.provide_input(
        "Check the units."
    )

    result = intervention.get_last_input()

    assert result["status"] == "feedback"
    assert result["input"] == "Check the units."


if __name__ == "__main__":

    test_no_human_input()
    test_human_feedback()
    test_human_approval()
    test_human_rejection()
    test_clear_intervention()
    test_last_input()

    print(
        "All human intervention tests passed."
    )