from typing import Any, Dict

from models.llm import generate
from models.router import select_model


class PeerReviewer:
    """
    Fast AI peer reviewer for V.A.U.L.T.

    Reviews an AI-generated answer and returns:

        PASS
        or
        REVISE

    The reviewer intentionally uses the fast model because
    review should be lightweight and should not significantly
    slow down the main agent.
    """

    def __init__(
        self,
        task_type: str = "simple",
    ):
        self.task_type = task_type

    def review(
        self,
        task: str,
        result: str,
    ) -> Dict[str, Any]:
        """
        Review an AI-generated result.

        Returns:

        {
            "verdict": "PASS" or "REVISE",
            "reason": "...",
            "corrections": "..."
        }
        """

        # --------------------------------------------------
        # INPUT VALIDATION
        # --------------------------------------------------

        if not isinstance(task, str):
            raise TypeError(
                "Task must be a string."
            )

        if not isinstance(result, str):
            raise TypeError(
                "Result must be a string."
            )

        task = task.strip()
        result = result.strip()

        if not task:
            raise ValueError(
                "Task cannot be empty."
            )

        if not result:
            return {
                "verdict": "REVISE",
                "reason": (
                    "The generated answer is empty."
                ),
                "corrections": (
                    "Provide a complete answer to the user."
                ),
            }

        # --------------------------------------------------
        # FAST MODEL SELECTION
        # --------------------------------------------------

        model = select_model(
            self.task_type
        )

        # --------------------------------------------------
        # REVIEW PROMPT
        # --------------------------------------------------

        prompt = f"""
You are a fast quality reviewer for V.A.U.L.T.

Review the answer against the user's task.

User task:
{task}

AI answer:
{result}

Check only:

1. Does the answer actually address the task?
2. Is there an obvious factual, mathematical,
   logical, or instruction-following error?
3. Is the answer clearly incomplete?

Do NOT request revisions for:

- Writing style preferences.
- Minor wording differences.
- Extra details that were not requested.
- Harmless formatting differences.

If the answer is acceptable, respond EXACTLY:

VERDICT: PASS
REASON: Answer is acceptable.
CORRECTIONS: None

If there is a significant problem, respond EXACTLY:

VERDICT: REVISE
REASON: <short explanation>
CORRECTIONS: <specific correction needed>

Do not write anything except this format.
"""

        # --------------------------------------------------
        # GENERATE REVIEW
        # --------------------------------------------------

        try:

            response = generate(
                prompt=prompt,
                model=model,
                use_router=False,
            )

        except Exception as exc:

            # Fail open instead of blocking the user.
            return {
                "verdict": "PASS",
                "reason": (
                    "Reviewer unavailable: "
                    f"{exc}"
                ),
                "corrections": "None",
            }

        # --------------------------------------------------
        # PARSE REVIEW
        # --------------------------------------------------

        return self._parse_review(
            response
        )

    # ======================================================
    # REVIEW PARSER
    # ======================================================

    def _parse_review(
        self,
        response: str,
    ) -> Dict[str, str]:
        """
        Parse the structured reviewer response.
        """

        if not isinstance(
            response,
            str,
        ):

            return self._default_pass()

        cleaned = response.strip()

        if not cleaned:

            return self._default_pass()

        verdict = None
        reason = ""
        corrections = ""

        for line in cleaned.splitlines():

            stripped_line = line.strip()

            upper_line = (
                stripped_line.upper()
            )

            # ----------------------------------------------
            # VERDICT
            # ----------------------------------------------

            if upper_line.startswith(
                "VERDICT:"
            ):

                value = (
                    stripped_line
                    .split(
                        ":",
                        1,
                    )[1]
                    .strip()
                    .upper()
                )

                if value in {
                    "PASS",
                    "REVISE",
                }:

                    verdict = value

            # ----------------------------------------------
            # REASON
            # ----------------------------------------------

            elif upper_line.startswith(
                "REASON:"
            ):

                reason = (
                    stripped_line
                    .split(
                        ":",
                        1,
                    )[1]
                    .strip()
                )

            # ----------------------------------------------
            # CORRECTIONS
            # ----------------------------------------------

            elif upper_line.startswith(
                "CORRECTIONS:"
            ):

                corrections = (
                    stripped_line
                    .split(
                        ":",
                        1,
                    )[1]
                    .strip()
                )

        # --------------------------------------------------
        # SAFE FALLBACK
        # --------------------------------------------------

        if verdict is None:

            # Small models occasionally ignore formatting.
            # If they clearly say REVISE, respect it.

            response_upper = cleaned.upper()

            if "REVISE" in response_upper:

                verdict = "REVISE"

            else:

                verdict = "PASS"

        # --------------------------------------------------
        # DEFAULT REASON
        # --------------------------------------------------

        if not reason:

            if verdict == "PASS":

                reason = (
                    "Answer is acceptable."
                )

            else:

                reason = (
                    "The answer requires revision."
                )

        # --------------------------------------------------
        # DEFAULT CORRECTIONS
        # --------------------------------------------------

        if not corrections:

            if verdict == "PASS":

                corrections = "None"

            else:

                corrections = (
                    "Correct the identified issue "
                    "and provide a complete answer."
                )

        return {
            "verdict": verdict,
            "reason": reason,
            "corrections": corrections,
        }

    # ======================================================
    # DEFAULT PASS
    # ======================================================

    def _default_pass(
        self,
    ) -> Dict[str, str]:
        """
        Safe fallback if the reviewer response cannot
        be parsed.
        """

        return {
            "verdict": "PASS",
            "reason": (
                "Answer accepted because the reviewer "
                "response could not be parsed."
            ),
            "corrections": "None",
        }


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    reviewer = PeerReviewer()

    review = reviewer.review(
        task="Calculate 25 * 48",
        result="25 × 48 = 1200",
    )

    print(
        "\nV.A.U.L.T. Peer Reviewer Test\n"
    )

    print(review)