"""
V.A.U.L.T. Fine-Tuning Eligibility Manager

Responsible for deciding whether an interaction
is suitable for the fine-tuning dataset.

Possible decisions:

- ACCEPTED
- CANDIDATE
- REJECTED

This module does not perform training.

It only evaluates the quality and usefulness
of interaction data.

The checker supports both interaction formats:

Canonical format:

{
    "task": "...",
    "task_type": "...",
    "input": "...",
    "final_response": "..."
}

Pipeline format:

{
    "prompt": "...",
    "response": "...",
    "task_type": "...",
    "metadata": {...}
}
"""

from typing import Any, Dict


class EligibilityChecker:

    """
    Determine whether an interaction should be
    included in the fine-tuning pipeline.
    """

    ACCEPTED = "accepted"
    CANDIDATE = "candidate"
    REJECTED = "rejected"

    # ======================================================
    # NORMALIZE INTERACTION
    # ======================================================

    def _normalize_interaction(
        self,
        interaction: Dict[str, Any],
    ) -> Dict[str, Any]:

        """
        Normalize supported interaction formats
        into the canonical eligibility format.

        Supported formats:

        1. Canonical:

            task
            task_type
            input
            final_response

        2. Pipeline:

            prompt
            response
            task_type
            metadata
        """

        if not isinstance(
            interaction,
            dict,
        ):

            return {}

        normalized = dict(
            interaction
        )

        # --------------------------------------------------
        # PROMPT -> INPUT
        # --------------------------------------------------

        if not normalized.get(
            "input"
        ):

            prompt = normalized.get(
                "prompt"
            )

            if isinstance(
                prompt,
                str,
            ):

                normalized[
                    "input"
                ] = prompt

        # --------------------------------------------------
        # RESPONSE -> FINAL_RESPONSE
        # --------------------------------------------------

        if not normalized.get(
            "final_response"
        ):

            response = normalized.get(
                "response"
            )

            if isinstance(
                response,
                str,
            ):

                normalized[
                    "final_response"
                ] = response

        # --------------------------------------------------
        # CREATE TASK IF MISSING
        # --------------------------------------------------

        if not normalized.get(
            "task"
        ):

            task_type = normalized.get(
                "task_type",
                "general",
            )

            if not isinstance(
                task_type,
                str,
            ):

                task_type = "general"

            normalized[
                "task"
            ] = (
                task_type.strip()
                or "general"
            )

        # --------------------------------------------------
        # DEFAULT TASK TYPE
        # --------------------------------------------------

        if not normalized.get(
            "task_type"
        ):

            normalized[
                "task_type"
            ] = "general"

        # --------------------------------------------------
        # READ METADATA
        # --------------------------------------------------

        metadata = normalized.get(
            "metadata",
            {},
        )

        if not isinstance(
            metadata,
            dict,
        ):

            metadata = {}

        # --------------------------------------------------
        # PEER REVIEW FROM METADATA
        # --------------------------------------------------

        if not isinstance(
            normalized.get(
                "peer_review"
            ),
            dict,
        ):

            peer_review = metadata.get(
                "peer_review"
            )

            if isinstance(
                peer_review,
                dict,
            ):

                normalized[
                    "peer_review"
                ] = peer_review

        # --------------------------------------------------
        # HUMAN FEEDBACK FROM METADATA
        # --------------------------------------------------

        if not normalized.get(
            "human_feedback"
        ):

            human_feedback = metadata.get(
                "human_feedback"
            )

            if isinstance(
                human_feedback,
                str,
            ):

                normalized[
                    "human_feedback"
                ] = human_feedback

        # --------------------------------------------------
        # SUCCESSFUL PIPELINE EXAMPLES
        # --------------------------------------------------

        # Examples that passed the quality filter
        # and entered the training pipeline are
        # considered candidates by default.

        if (
            not normalized.get(
                "peer_review"
            )
            and
            not normalized.get(
                "human_feedback"
            )
        ):

            source = metadata.get(
                "source"
            )

            quality_score = metadata.get(
                "quality_score"
            )

            if source == "vault_runtime":

                normalized[
                    "_pipeline_candidate"
                ] = True

            elif isinstance(
                quality_score,
                (
                    int,
                    float,
                ),
            ) and quality_score >= 0.8:

                normalized[
                    "_pipeline_candidate"
                ] = True

        return normalized


    # ======================================================
    # MAIN ELIGIBILITY CHECK
    # ======================================================

    def evaluate(
        self,
        interaction: Dict[str, Any],
    ) -> Dict[str, Any]:

        """
        Evaluate an interaction.

        Returns:

        {
            "eligible": bool,
            "quality": accepted/candidate/rejected,
            "reason": str
        }
        """

        # --------------------------------------------------
        # BASIC VALIDATION
        # --------------------------------------------------

        if not isinstance(
            interaction,
            dict,
        ):

            return self._reject(
                "Interaction must be a dictionary."
            )

        # --------------------------------------------------
        # NORMALIZE FORMAT
        # --------------------------------------------------

        interaction = (
            self._normalize_interaction(
                interaction
            )
        )

        # --------------------------------------------------
        # REQUIRED FIELDS
        # --------------------------------------------------

        required_fields = [

            "task",

            "task_type",

            "input",

            "final_response",

        ]

        for field in required_fields:

            value = interaction.get(
                field
            )

            if not isinstance(
                value,
                str,
            ):

                return self._reject(
                    f"Missing required field: {field}"
                )

            if not value.strip():

                return self._reject(
                    f"Empty required field: {field}"
                )

        # --------------------------------------------------
        # NORMALIZE VALUES
        # --------------------------------------------------

        final_response = (

            interaction[
                "final_response"
            ]

            .strip()

        )

        # --------------------------------------------------
        # REJECT VERY SHORT RESPONSES
        # --------------------------------------------------

        if len(
            final_response
        ) < 10:

            return self._reject(
                "Final response is too short."
            )

        # --------------------------------------------------
        # CHECK PEER REVIEW
        # --------------------------------------------------

        peer_review = (

            interaction.get(
                "peer_review",
                {},
            )

        )

        if not isinstance(
            peer_review,
            dict,
        ):

            peer_review = {}

        verdict = (

            peer_review.get(
                "verdict",
                "",
            )

            if isinstance(
                peer_review.get(
                    "verdict",
                    "",
                ),
                str,
            )

            else ""

        )

        verdict = (

            verdict

            .strip()

            .upper()

        )

        # --------------------------------------------------
        # HUMAN FEEDBACK
        # --------------------------------------------------

        human_feedback = (

            interaction.get(
                "human_feedback",
                "",
            )

        )

        if not isinstance(
            human_feedback,
            str,
        ):

            human_feedback = ""

        human_feedback = (

            human_feedback.strip()

        )

        # --------------------------------------------------
        # ACCEPTED
        # --------------------------------------------------

        if verdict == "PASS":

            return {

                "eligible":
                    True,

                "quality":
                    self.ACCEPTED,

                "reason":
                    (
                        "Peer review passed the "
                        "final response."
                    ),

            }

        # --------------------------------------------------
        # REJECT FAILED REVIEW
        # --------------------------------------------------

        if verdict in {

            "FAIL",

            "REJECT",

            "REVISE",

        }:

            # --------------------------------------------------
            # HUMAN FEEDBACK OVERRIDES REJECTION
            # --------------------------------------------------

            if human_feedback:

                return {

                    "eligible":
                        True,

                    "quality":
                        self.CANDIDATE,

                    "reason":
                        (
                            "Human feedback is "
                            "available for this "
                            "interaction."
                        ),

                }

            return self._reject(

                "Final response was not accepted "
                "by peer review."

            )

        # --------------------------------------------------
        # HUMAN FEEDBACK CANDIDATE
        # --------------------------------------------------

        if human_feedback:

            return {

                "eligible":
                    True,

                "quality":
                    self.CANDIDATE,

                "reason":
                    (
                        "Human feedback is available "
                        "for this interaction."
                    ),

            }

        # --------------------------------------------------
        # PIPELINE GENERATED CANDIDATE
        # --------------------------------------------------

        if interaction.get(
            "_pipeline_candidate",
            False,
        ):

            return {

                "eligible":
                    True,

                "quality":
                    self.CANDIDATE,

                "reason":
                    (
                        "Interaction passed the "
                        "V.A.U.L.T. quality pipeline "
                        "and is eligible as a "
                        "training candidate."
                    ),

            }

        # --------------------------------------------------
        # DEFAULT
        # --------------------------------------------------

        return self._reject(

            "Interaction does not contain "
            "sufficient validation evidence."

        )


    # ======================================================
    # REJECT HELPER
    # ======================================================

    def _reject(
        self,
        reason: str,
    ) -> Dict[str, Any]:

        """
        Create a rejected eligibility result.
        """

        return {

            "eligible":
                False,

            "quality":
                self.REJECTED,

            "reason":
                reason,

        }


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    checker = EligibilityChecker()

    interactions = [

        # ==================================================
        # ACCEPTED EXAMPLE
        # ==================================================

        {

            "task":
                "Calculate pump efficiency",

            "task_type":
                "engineering",

            "input":
                (
                    "Input power is 10 kW and "
                    "useful power is 8 kW."
                ),

            "final_response":
                (
                    "Pump efficiency is "
                    "80 percent."
                ),

            "peer_review": {

                "verdict":
                    "PASS"

            },

            "human_feedback":
                "",

        },

        # ==================================================
        # CANDIDATE EXAMPLE
        # ==================================================

        {

            "task":
                "Analyze pump vibration",

            "task_type":
                "engineering",

            "input":
                (
                    "Pump vibration measurement "
                    "is 5 mm/s."
                ),

            "final_response":
                (
                    "Additional operating conditions "
                    "are required before determining "
                    "whether the pump is operating "
                    "normally."
                ),

            "peer_review": {

                "verdict":
                    "REVISE"

            },

            "human_feedback":
                (
                    "Focus on the measured vibration "
                    "and explain missing information."
                ),

        },

        # ==================================================
        # PIPELINE FORMAT EXAMPLE
        # ==================================================

        {

            "prompt":
                (
                    "Write a Python function "
                    "that calculates factorial."
                ),

            "response":
                (
                    "Use a function with a base case "
                    "for zero and one, then multiply "
                    "the number by the factorial of "
                    "the previous number."
                ),

            "task_type":
                "coding",

            "metadata": {

                "source":
                    "vault_runtime",

                "quality_score":
                    1.0,

            },

        },

        # ==================================================
        # REJECTED EXAMPLE
        # ==================================================

        {

            "task":
                "Hello",

            "task_type":
                "general",

            "input":
                "Hello",

            "final_response":
                "Hi!",

            "peer_review": {

                "verdict":
                    ""

            },

            "human_feedback":
                "",

        },

    ]

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. ELIGIBILITY TEST"
    )

    print("=" * 60)

    for index, interaction in enumerate(

        interactions,

        start=1,

    ):

        result = checker.evaluate(
            interaction
        )

        print()

        print(
            f"INTERACTION {index}"
        )

        print("-" * 60)

        print(
            result
        )

    print()

    print("=" * 60)

    print(
        "ELIGIBILITY TEST COMPLETE"
    )

    print("=" * 60)