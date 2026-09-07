"""
V.A.U.L.T. Fine-Tuning Quality Filter

Filters collected interactions before they are allowed
into the fine-tuning dataset.

Responsibilities:

    - Validate prompts and responses
    - Reject empty content
    - Reject extremely short responses
    - Detect common error responses
    - Detect placeholder responses
    - Enforce length limits
    - Calculate a basic quality score
    - Return clear acceptance or rejection reasons

IMPORTANT:

This module does not modify the dataset.

It only decides whether an interaction is suitable
for fine-tuning.
"""


from typing import Any, Dict, Optional


# ==========================================================
# FINE-TUNING QUALITY FILTER
# ==========================================================

class FineTuningQualityFilter:

    """
    Evaluate interaction quality before the interaction
    becomes a fine-tuning training example.
    """

    def __init__(
        self,
        minimum_prompt_length: int = 3,
        minimum_response_length: int = 10,
        maximum_prompt_length: int = 20000,
        maximum_response_length: int = 50000,
        minimum_quality_score: float = 0.60,
    ):

        self.minimum_prompt_length = max(
            1,
            int(minimum_prompt_length),
        )

        self.minimum_response_length = max(
            1,
            int(minimum_response_length),
        )

        self.maximum_prompt_length = max(
            self.minimum_prompt_length,
            int(maximum_prompt_length),
        )

        self.maximum_response_length = max(
            self.minimum_response_length,
            int(maximum_response_length),
        )

        self.minimum_quality_score = max(
            0.0,
            min(
                1.0,
                float(minimum_quality_score),
            ),
        )

        # --------------------------------------------------
        # COMMON ERROR INDICATORS
        # --------------------------------------------------

        self.error_patterns = [

            "traceback",

            "internal server error",

            "connection refused",

            "connection error",

            "model not found",

            "unable to generate",

            "generation failed",

            "an error occurred",

            "something went wrong",

            "exception:",

            "runtimeerror",

            "valueerror",

            "keyerror",

        ]

        # --------------------------------------------------
        # LOW-QUALITY PLACEHOLDERS
        # --------------------------------------------------

        self.placeholder_responses = [

            "i don't know",

            "i do not know",

            "unknown",

            "n/a",

            "na",

            "none",

            "null",

            "error",

            "failed",

            "no response",

            "cannot answer",

            "can't answer",

        ]


    # ======================================================
    # VALIDATE TEXT
    # ======================================================

    @staticmethod
    def _is_valid_text(
        value: Any,
    ) -> bool:

        """
        Return True when the value contains useful text.
        """

        return (

            isinstance(
                value,
                str,
            )

            and bool(
                value.strip()
            )

        )


    # ======================================================
    # NORMALIZE TEXT
    # ======================================================

    @staticmethod
    def _normalize_text(
        value: str,
    ) -> str:

        """
        Normalize text for comparison.
        """

        return (

            value
            .strip()
            .lower()

        )


    # ======================================================
    # CHECK ERROR RESPONSE
    # ======================================================

    def _contains_error_pattern(
        self,
        response: str,
    ) -> Optional[str]:

        """
        Detect common system or generation errors.
        """

        normalized_response = (
            self._normalize_text(
                response
            )
        )

        for pattern in self.error_patterns:

            if pattern in normalized_response:

                return pattern

        return None


    # ======================================================
    # CHECK PLACEHOLDER
    # ======================================================

    def _is_placeholder_response(
        self,
        response: str,
    ) -> bool:

        """
        Detect very low-quality placeholder responses.
        """

        normalized_response = (
            self._normalize_text(
                response
            )
        )

        return (

            normalized_response
            in
            self.placeholder_responses

        )


    # ======================================================
    # CALCULATE QUALITY SCORE
    # ======================================================

    def calculate_quality_score(
        self,
        prompt: str,
        response: str,
    ) -> float:

        """
        Calculate a basic quality score.

        Score range:

            0.0 → Very poor
            1.0 → Good
        """

        score = 1.0

        prompt_length = len(
            prompt.strip()
        )

        response_length = len(
            response.strip()
        )

        # --------------------------------------------------
        # SHORT PROMPT PENALTY
        # --------------------------------------------------

        if prompt_length < 10:

            score -= 0.10

        # --------------------------------------------------
        # SHORT RESPONSE PENALTY
        # --------------------------------------------------

        if response_length < 50:

            score -= 0.10

        # --------------------------------------------------
        # VERY SHORT RESPONSE PENALTY
        # --------------------------------------------------

        if response_length < 25:

            score -= 0.15

        # --------------------------------------------------
        # RESPONSE SAME AS PROMPT
        # --------------------------------------------------

        if (

            self._normalize_text(
                prompt
            )

            ==

            self._normalize_text(
                response
            )

        ):

            score -= 0.40

        # --------------------------------------------------
        # ERROR PATTERN PENALTY
        # --------------------------------------------------

        if self._contains_error_pattern(
            response
        ):

            score -= 0.50

        # --------------------------------------------------
        # PLACEHOLDER PENALTY
        # --------------------------------------------------

        if self._is_placeholder_response(
            response
        ):

            score -= 0.60

        return round(

            max(
                0.0,
                min(
                    1.0,
                    score,
                ),
            ),

            3,

        )


    # ======================================================
    # FILTER INTERACTION
    # ======================================================

    def evaluate(
        self,
        prompt: Any,
        response: Any,
        task_type: str = "general",
    ) -> Dict[str, Any]:

        """
        Evaluate an interaction.

        Returns:

            accepted
            quality_score
            reason
            task_type
        """

        # --------------------------------------------------
        # VALIDATE PROMPT TYPE
        # --------------------------------------------------

        if not self._is_valid_text(
            prompt
        ):

            return {

                "accepted": False,

                "quality_score": 0.0,

                "reason":
                    "Prompt is empty or invalid.",

                "task_type":
                    task_type,

            }

        # --------------------------------------------------
        # VALIDATE RESPONSE TYPE
        # --------------------------------------------------

        if not self._is_valid_text(
            response
        ):

            return {

                "accepted": False,

                "quality_score": 0.0,

                "reason":
                    "Response is empty or invalid.",

                "task_type":
                    task_type,

            }

        prompt = (
            prompt.strip()
        )

        response = (
            response.strip()
        )

        # --------------------------------------------------
        # PROMPT TOO SHORT
        # --------------------------------------------------

        if (

            len(prompt)

            <

            self.minimum_prompt_length

        ):

            return {

                "accepted": False,

                "quality_score": 0.0,

                "reason":
                    "Prompt is too short.",

                "task_type":
                    task_type,

            }

        # --------------------------------------------------
        # RESPONSE TOO SHORT
        # --------------------------------------------------

        if (

            len(response)

            <

            self.minimum_response_length

        ):

            return {

                "accepted": False,

                "quality_score": 0.0,

                "reason":
                    "Response is too short.",

                "task_type":
                    task_type,

            }

        # --------------------------------------------------
        # PROMPT TOO LONG
        # --------------------------------------------------

        if (

            len(prompt)

            >

            self.maximum_prompt_length

        ):

            return {

                "accepted": False,

                "quality_score": 0.0,

                "reason":
                    "Prompt exceeds maximum length.",

                "task_type":
                    task_type,

            }

        # --------------------------------------------------
        # RESPONSE TOO LONG
        # --------------------------------------------------

        if (

            len(response)

            >

            self.maximum_response_length

        ):

            return {

                "accepted": False,

                "quality_score": 0.0,

                "reason":
                    "Response exceeds maximum length.",

                "task_type":
                    task_type,

            }

        # --------------------------------------------------
        # PLACEHOLDER RESPONSE
        # --------------------------------------------------

        if self._is_placeholder_response(
            response
        ):

            return {

                "accepted": False,

                "quality_score": 0.0,

                "reason":
                    "Response is a low-quality placeholder.",

                "task_type":
                    task_type,

            }

        # --------------------------------------------------
        # ERROR RESPONSE
        # --------------------------------------------------

        error_pattern = (

            self._contains_error_pattern(
                response
            )

        )

        if error_pattern:

            return {

                "accepted": False,

                "quality_score": 0.0,

                "reason":
                    (
                        "Response contains "
                        "an error indicator: "
                        f"{error_pattern}"
                    ),

                "task_type":
                    task_type,

            }

        # --------------------------------------------------
        # IDENTICAL PROMPT AND RESPONSE
        # --------------------------------------------------

        if (

            self._normalize_text(
                prompt
            )

            ==

            self._normalize_text(
                response
            )

        ):

            return {

                "accepted": False,

                "quality_score": 0.0,

                "reason":
                    (
                        "Prompt and response "
                        "are identical."
                    ),

                "task_type":
                    task_type,

            }

        # --------------------------------------------------
        # CALCULATE SCORE
        # --------------------------------------------------

        quality_score = (

            self.calculate_quality_score(

                prompt=prompt,

                response=response,

            )

        )

        # --------------------------------------------------
        # QUALITY THRESHOLD
        # --------------------------------------------------

        if (

            quality_score

            <

            self.minimum_quality_score

        ):

            return {

                "accepted": False,

                "quality_score":
                    quality_score,

                "reason":
                    (
                        "Interaction quality "
                        "score is below the "
                        "minimum threshold."
                    ),

                "task_type":
                    task_type,

            }

        # --------------------------------------------------
        # ACCEPT
        # --------------------------------------------------

        return {

            "accepted": True,

            "quality_score":
                quality_score,

            "reason":
                "Interaction passed quality checks.",

            "task_type":
                task_type,

            "prompt_length":
                len(prompt),

            "response_length":
                len(response),

        }


    # ======================================================
    # FILTER EXAMPLE DICTIONARY
    # ======================================================

    def filter_example(
        self,
        example: Dict[str, Any],
    ) -> Dict[str, Any]:

        """
        Evaluate a training example dictionary.

        Supports both formats:

            prompt / response

        and:

            input / final_response
        """

        if not isinstance(
            example,
            dict,
        ):

            return {

                "accepted": False,

                "quality_score": 0.0,

                "reason":
                    (
                        "Training example must "
                        "be a dictionary."
                    ),

            }

        prompt = (

            example.get(
                "prompt"
            )

            or

            example.get(
                "input"
            )

            or

            example.get(
                "task"
            )

        )

        response = (

            example.get(
                "response"
            )

            or

            example.get(
                "final_response"
            )

        )

        task_type = (

            example.get(
                "task_type",
                "general",
            )

        )

        return self.evaluate(

            prompt=prompt,

            response=response,

            task_type=task_type,

        )


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNING QUALITY FILTER TEST"
    )

    print("=" * 60)

    # ======================================================
    # CREATE FILTER
    # ======================================================

    quality_filter = (

        FineTuningQualityFilter()

    )

    # ======================================================
    # TEST CASES
    # ======================================================

    test_cases = [

        {

            "name":
                "GOOD INTERACTION",

            "prompt":
                (
                    "Write a Python function "
                    "to calculate factorial."
                ),

            "response":
                (
                    "You can calculate factorial "
                    "using a recursive Python "
                    "function with base cases "
                    "for zero and one."
                ),

        },

        {

            "name":
                "EMPTY RESPONSE",

            "prompt":
                "Explain Python.",

            "response":
                "",

        },

        {

            "name":
                "PLACEHOLDER RESPONSE",

            "prompt":
                "Explain machine learning.",

            "response":
                "I don't know",

        },

        {

            "name":
                "ERROR RESPONSE",

            "prompt":
                "Write Python code.",

            "response":
                (
                    "Traceback: generation failed"
                ),

        },

        {

            "name":
                "IDENTICAL TEXT",

            "prompt":
                "Hello world",

            "response":
                "Hello world",

        },

    ]

    # ======================================================
    # RUN TESTS
    # ======================================================

    for test in test_cases:

        print()

        print(
            "-" * 60
        )

        print(
            test["name"]
        )

        print(
            "-" * 60
        )

        result = (

            quality_filter.evaluate(

                prompt=(
                    test["prompt"]
                ),

                response=(
                    test["response"]
                ),

            )

        )

        print(
            result
        )

    print()

    print("=" * 60)

    print(
        "QUALITY FILTER TEST COMPLETE"
    )

    print("=" * 60)