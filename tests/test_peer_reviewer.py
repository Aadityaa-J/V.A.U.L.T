from agents.peer_reviewer import PeerReviewer


def test_peer_reviewer_parses_pass():

    reviewer = PeerReviewer()

    response = """
VERDICT: PASS
REASON: The result is consistent with
the information provided.
"""

    result = reviewer._parse_review(
        response
    )

    assert result["verdict"] == "PASS"
    assert (
        "consistent"
        in result["reason"]
    )


def test_peer_reviewer_parses_revise():

    reviewer = PeerReviewer()

    response = """
VERDICT: REVISE
REASON: The calculation uses an incorrect unit.
CORRECTIONS: Recalculate using kPa.
"""

    result = reviewer._parse_review(
        response
    )

    assert result["verdict"] == "REVISE"

    assert (
        "incorrect unit"
        in result["reason"]
    )

    assert (
        "kPa"
        in result["corrections"]
    )


def test_peer_reviewer_handles_unknown():

    reviewer = PeerReviewer()

    response = """
Something unexpected happened.
"""

    result = reviewer._parse_review(
        response
    )

    assert result["verdict"] == "UNKNOWN"


if __name__ == "__main__":

    test_peer_reviewer_parses_pass()
    test_peer_reviewer_parses_revise()
    test_peer_reviewer_handles_unknown()

    print(
        "All peer reviewer tests passed."
    )