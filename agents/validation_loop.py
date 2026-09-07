from typing import Any, Callable, Dict

from agents.peer_reviewer import PeerReviewer
from agents.human_intervention import HumanIntervention
from models.llm import generate
from models.router import select_model


class ValidationLoop:
    """
    Fast validation system for V.A.U.L.T.

    Strategy:

    - General tasks:
        Usually returned immediately.

    - Engineering, coding and document tasks:
        Reviewed once by the AI reviewer.

    - Revision:
        Only generated when the reviewer explicitly
        requests revision.

    This avoids unnecessary LLM calls and significantly
    improves response speed.
    """

    def __init__(
        self,
        reviewer: PeerReviewer | None = None,
        human_intervention: HumanIntervention | None = None,
        max_reviews: int = 1,
        validate_general: bool = False,
    ):
        self.reviewer = (
            reviewer
            or PeerReviewer()
        )

        self.human_intervention = (
            human_intervention
            or HumanIntervention()
        )

        self.max_reviews = max_reviews

        self.validate_general = (
            validate_general
        )

        self.last_state: Dict[str, Any] = {}

    # ======================================================
    # MAIN VALIDATION LOOP
    # ======================================================

    def run(
        self,
        task: str,
        initial_result: str,
        generate_revision: Callable[
            [str, str, str],
            str
        ] | None = None,
        human_input: Dict[str, Any] | None = None,
        task_type: str = "general",
    ) -> Dict[str, Any]:
        """
        Validate an agent result.

        Returns a dictionary containing:

        - final_result
        - status
        - reviews
        - human_interventions
        """

        if not isinstance(task, str):
            raise TypeError(
                "Task must be a string."
            )

        if not isinstance(initial_result, str):
            raise TypeError(
                "Initial result must be a string."
            )

        current_result = (
            initial_result.strip()
        )

        review_history = []

        human_history = []

        # ==================================================
        # FAST PATH
        # ==================================================

        should_validate = (
            task_type != "general"
            or self.validate_general
        )

        if not should_validate:

            return self._handle_human_intervention(
                task=task,
                current_result=current_result,
                human_input=human_input,
                task_type=task_type,
                review_history=review_history,
                human_history=human_history,
                generate_revision=generate_revision,
            )

        # ==================================================
        # AI REVIEW
        # ==================================================

        for review_number in range(
            1,
            self.max_reviews + 1,
        ):

            review = self.reviewer.review(
                task=task,
                result=current_result,
            )

            review_history.append(
                {
                    "review_number": (
                        review_number
                    ),
                    "phase": "ai_review",
                    "result": current_result,
                    "review": review,
                }
            )

            verdict = (
                review.get(
                    "verdict",
                    "PASS",
                )
                .strip()
                .upper()
            )

            # ----------------------------------------------
            # PASS
            # ----------------------------------------------

            if verdict == "PASS":

                break

            # ----------------------------------------------
            # REVISE
            # ----------------------------------------------

            if verdict == "REVISE":

                if review_number >= (
                    self.max_reviews
                ):

                    break

                feedback = self._build_feedback(
                    review
                )

                current_result = (
                    self._create_revision(
                        task=task,
                        result=current_result,
                        feedback=feedback,
                        generate_revision=(
                            generate_revision
                        ),
                        task_type=task_type,
                    )
                )

                continue

            # ----------------------------------------------
            # UNKNOWN REVIEW RESULT
            # ----------------------------------------------

            break

        # ==================================================
        # HUMAN INTERVENTION
        # ==================================================

        return self._handle_human_intervention(
            task=task,
            current_result=current_result,
            human_input=human_input,
            task_type=task_type,
            review_history=review_history,
            human_history=human_history,
            generate_revision=generate_revision,
        )

    # ======================================================
    # HUMAN INTERVENTION
    # ======================================================

    def _handle_human_intervention(
        self,
        task: str,
        current_result: str,
        human_input: Dict[str, Any] | None,
        task_type: str,
        review_history: list,
        human_history: list,
        generate_revision,
    ) -> Dict[str, Any]:
        """
        Process optional human approval, feedback,
        or rejection.
        """

        # --------------------------------------------------
        # NO HUMAN INPUT
        # --------------------------------------------------

        if human_input is None:

            self.last_state = {
                "task": task,
                "task_type": task_type,
                "final_result": current_result,
                "status": "validated",
                "reviews": review_history,
                "human_interventions": (
                    human_history
                ),
            }

            return self.last_state

        # --------------------------------------------------
        # VALIDATE HUMAN INPUT
        # --------------------------------------------------

        if not isinstance(
            human_input,
            dict,
        ):

            raise TypeError(
                "Human input must be a dictionary."
            )

        human_status = (
            human_input.get(
                "status",
                "none",
            )
            .strip()
            .lower()
        )

        human_message = (
            human_input.get(
                "input",
                ""
            )
        )

        if not isinstance(
            human_message,
            str,
        ):

            human_message = str(
                human_message
            )

        human_history.append(
            {
                "status": human_status,
                "input": human_message,
                "result_before_intervention": (
                    current_result
                ),
            }
        )

        # --------------------------------------------------
        # APPROVE
        # --------------------------------------------------

        if human_status == "approve":

            self.last_state = {
                "task": task,
                "task_type": task_type,
                "final_result": current_result,
                "status": "human_approved",
                "reviews": review_history,
                "human_interventions": (
                    human_history
                ),
            }

            return self.last_state

        # --------------------------------------------------
        # FEEDBACK / REJECT
        # --------------------------------------------------

        if human_status in {
            "feedback",
            "reject",
        }:

            if not human_message.strip():

                human_message = (
                    "Please carefully review and "
                    "improve the previous answer."
                )

            revised_result = (
                self._create_revision(
                    task=task,
                    result=current_result,
                    feedback=human_message,
                    generate_revision=(
                        generate_revision
                    ),
                    task_type=task_type,
                )
            )

            # ----------------------------------------------
            # REVIEW REVISED RESULT
            # ----------------------------------------------

            review = self.reviewer.review(
                task=task,
                result=revised_result,
            )

            review_history.append(
                {
                    "review_number": (
                        len(review_history)
                        + 1
                    ),
                    "phase": (
                        "post_human_review"
                    ),
                    "result": revised_result,
                    "review": review,
                }
            )

            verdict = (
                review.get(
                    "verdict",
                    "PASS",
                )
                .strip()
                .upper()
            )

            status = (
                "human_feedback_validated"
                if verdict == "PASS"
                else "requires_further_review"
            )

            self.last_state = {
                "task": task,
                "task_type": task_type,
                "final_result": revised_result,
                "status": status,
                "reviews": review_history,
                "human_interventions": (
                    human_history
                ),
            }

            return self.last_state

        # --------------------------------------------------
        # UNKNOWN HUMAN STATUS
        # --------------------------------------------------

        self.last_state = {
            "task": task,
            "task_type": task_type,
            "final_result": current_result,
            "status": "validated",
            "reviews": review_history,
            "human_interventions": (
                human_history
            ),
        }

        return self.last_state

    # ======================================================
    # BUILD REVIEW FEEDBACK
    # ======================================================

    def _build_feedback(
        self,
        review: Dict[str, Any],
    ) -> str:
        """
        Combine reviewer feedback into one string.
        """

        reason = str(
            review.get(
                "reason",
                "",
            )
        )

        corrections = str(
            review.get(
                "corrections",
                "",
            )
        )

        feedback_parts = []

        if reason.strip():

            feedback_parts.append(
                f"Reason:\n{reason}"
            )

        if corrections.strip():

            feedback_parts.append(
                f"Corrections:\n{corrections}"
            )

        if not feedback_parts:

            return (
                "Review the answer carefully and "
                "improve any potential issues."
            )

        return "\n\n".join(
            feedback_parts
        )

    # ======================================================
    # CREATE REVISION
    # ======================================================

    def _create_revision(
        self,
        task: str,
        result: str,
        feedback: str,
        generate_revision: Callable[
            [str, str, str],
            str
        ] | None,
        task_type: str,
    ) -> str:
        """
        Generate a revised answer.
        """

        if generate_revision is not None:

            return generate_revision(
                task,
                result,
                feedback,
            )

        return self._generate_revision(
            task=task,
            result=result,
            feedback=feedback,
            task_type=task_type,
        )

    # ======================================================
    # LLM REVISION
    # ======================================================

    def _generate_revision(
        self,
        task: str,
        result: str,
        feedback: str,
        task_type: str,
    ) -> str:
        """
        Ask the appropriate model to revise
        the previous answer.
        """

        model_task_type = (
            self._get_model_task_type(
                task_type
            )
        )

        model = select_model(
            model_task_type
        )

        prompt = f"""
You are V.A.U.L.T.

Revise the previous answer using the feedback below.

Original task:
{task}

Previous answer:
{result}

Feedback:
{feedback}

Rules:

- Fix the issues identified in the feedback.
- Preserve information that is already correct.
- Do not invent information.
- Return only the improved final answer.
"""

        return generate(
            prompt=prompt,
            model=model,
            use_router=False,
        )

    # ======================================================
    # TASK TYPE → MODEL TASK TYPE
    # ======================================================

    def _get_model_task_type(
        self,
        task_type: str,
    ) -> str:
        """
        Convert agent task types into router task types.
        """

        mapping = {
            "general": "simple",
            "document": "simple",
            "coding": "complex",
            "engineering": "complex",
        }

        return mapping.get(
            task_type,
            "simple",
        )


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    validation_loop = ValidationLoop()

    result = validation_loop.run(
        task="What is 2 + 2?",
        initial_result="2 + 2 = 4",
        task_type="general",
    )

    print(
        "\nV.A.U.L.T. Validation Test\n"
    )

    print(
        result
    )