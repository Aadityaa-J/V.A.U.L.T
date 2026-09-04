from typing import Dict, Any, Callable

from agents.peer_reviewer import PeerReviewer
from agents.human_intervention import HumanIntervention
from models.llm import generate
from models.router import select_model


class ValidationLoop:
    """
    Coordinates AI generation, AI peer review, revision,
    and optional human intervention.

    Validation flow:

        Primary AI
            ↓
        Peer Review
            ↓
        AI Revision (if required)
            ↓
        Peer Review
            ↓
        Validated Result
            ↓
        Optional Human Intervention
            ↓
        AI Revision (if required)
            ↓
        Peer Review
            ↓
        Final Result

    Every newly generated AI result is reviewed again.
    """

    def __init__(
        self,
        reviewer: PeerReviewer | None = None,
        human_intervention: HumanIntervention | None = None,
        max_reviews: int = 2
    ):
        self.reviewer = reviewer or PeerReviewer()

        self.human_intervention = (
            human_intervention
            or HumanIntervention()
        )

        self.max_reviews = max_reviews

        self.last_state: Dict[str, Any] = {}

    def run(
        self,
        task: str,
        initial_result: str,
        generate_revision: Callable[
            [str, str, str],
            str
        ] | None = None,
        human_input: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:

        current_result = initial_result

        review_history = []
        human_history = []

        # -------------------------------------------------
        # Phase 1:
        # AI → AI review → AI revision
        # -------------------------------------------------

        for review_number in range(
            1,
            self.max_reviews + 1
        ):

            review = self.reviewer.review(
                task=task,
                result=current_result
            )

            review_history.append({
                "review_number": review_number,
                "phase": "ai_review",
                "result": current_result,
                "review": review
            })

            verdict = review["verdict"]

            if verdict == "PASS":
                break

            if verdict == "REVISE":

                if review_number >= self.max_reviews:

                    self.last_state = {
                        "task": task,
                        "final_result": current_result,
                        "status": (
                            "review_limit_reached"
                        ),
                        "reviews": review_history,
                        "human_interventions": human_history
                    }

                    return self.last_state

                current_result = self._create_revision(
                    task=task,
                    result=current_result,
                    feedback=(
                        review["reason"]
                        + "\n"
                        + review["corrections"]
                    ),
                    generate_revision=generate_revision
                )

                continue

            self.last_state = {
                "task": task,
                "final_result": current_result,
                "status": "review_uncertain",
                "reviews": review_history,
                "human_interventions": human_history
            }

            return self.last_state

        # -------------------------------------------------
        # Phase 2:
        # Optional human intervention
        # -------------------------------------------------

        if human_input is not None:

            human_status = human_input.get(
                "status",
                "none"
            )

            human_message = human_input.get(
                "input",
                ""
            )

            human_history.append({
                "status": human_status,
                "input": human_message,
                "result_before_intervention": (
                    current_result
                )
            })

            # ---------------------------------------------
            # Human approves the validated result
            # ---------------------------------------------

            if human_status == "approve":

                self.last_state = {
                    "task": task,
                    "final_result": current_result,
                    "status": "human_approved",
                    "reviews": review_history,
                    "human_interventions": (
                        human_history
                    )
                }

                return self.last_state

            # ---------------------------------------------
            # Human provides feedback or rejects
            # ---------------------------------------------

            if human_status in {
                "feedback",
                "reject"
            }:

                current_result = self._create_revision(
                    task=task,
                    result=current_result,
                    feedback=human_message,
                    generate_revision=generate_revision
                )

                # -----------------------------------------
                # IMPORTANT:
                # The newly generated result MUST be
                # reviewed again.
                # -----------------------------------------

                review = self.reviewer.review(
                    task=task,
                    result=current_result
                )

                review_history.append({
                    "review_number": (
                        len(review_history) + 1
                    ),
                    "phase": (
                        "post_human_ai_review"
                    ),
                    "result": current_result,
                    "review": review
                })

                if review["verdict"] == "PASS":

                    self.last_state = {
                        "task": task,
                        "final_result": current_result,
                        "status": (
                            "human_feedback_validated"
                        ),
                        "reviews": review_history,
                        "human_interventions": (
                            human_history
                        )
                    }

                    return self.last_state

                self.last_state = {
                    "task": task,
                    "final_result": current_result,
                    "status": (
                        "requires_further_review"
                    ),
                    "reviews": review_history,
                    "human_interventions": (
                        human_history
                    )
                }

                return self.last_state

        # -------------------------------------------------
        # No human intervention
        # -------------------------------------------------

        self.last_state = {
            "task": task,
            "final_result": current_result,
            "status": "validated",
            "reviews": review_history,
            "human_interventions": human_history
        }

        return self.last_state

    def _create_revision(
        self,
        task: str,
        result: str,
        feedback: str,
        generate_revision: Callable[
            [str, str, str],
            str
        ] | None
    ) -> str:

        if generate_revision is not None:

            return generate_revision(
                task,
                result,
                feedback
            )

        return self._generate_revision(
            task=task,
            result=result,
            feedback=feedback
        )

    def _generate_revision(
        self,
        task: str,
        result: str,
        feedback: str
    ) -> str:

        model = select_model(
            "engineering"
        )

        prompt = f"""
You are the primary AI in V.A.U.L.T.

You must revise your previous result.

Original task:
{task}

Previous result:
{result}

Feedback:
{feedback}

Revise the result carefully.

Rules:
- Address the feedback.
- Preserve correct information.
- Do not invent missing information.
- Clearly correct identified issues.
- Produce only the revised final answer.
"""

        return generate(
            prompt=prompt,
            model=model
        )


if __name__ == "__main__":

    loop = ValidationLoop()

    result = loop.run(
        task="Test validation loop",
        initial_result=(
            "This is an initial AI result."
        )
    )

    print(result)