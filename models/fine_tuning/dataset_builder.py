"""
V.A.U.L.T. Fine-Tuning Dataset Builder

Converts V.A.U.L.T. runtime interactions into
valid fine-tuning dataset records.

Pipeline:

    User Prompt
        ↓
    V.A.U.L.T. Response
        ↓
    Dataset Builder
        ↓
    Valid Training Record
        ↓
    FineTuningDataset

The generated records follow the format required
by FineTuningDataset:

    - task
    - task_type
    - input
    - final_response
    - quality
"""


from datetime import datetime
from typing import Any, Dict, Optional


# ==========================================================
# DATASET BUILDER
# ==========================================================

class FineTuningDatasetBuilder:

    """
    Convert V.A.U.L.T. interactions into valid
    fine-tuning training examples.

    This class is responsible for making runtime
    prompt/response interactions compatible with
    FineTuningDataset.
    """

    def __init__(
        self,
        default_quality: str = "accepted",
    ):

        self.default_quality = (
            self._normalize_quality(
                default_quality
            )
        )

        self.total_examples_built = 0

        self.total_rejected = 0


    # ======================================================
    # BUILD EXAMPLE
    # ======================================================

    def build_example(
        self,
        prompt: str,
        response: str,
        task_type: str = "general",
        metadata: Optional[
            Dict[str, Any]
        ] = None,
        quality: Optional[str] = None,
        source_model: Optional[str] = None,
    ) -> Dict[str, Any]:

        """
        Build a valid fine-tuning training example.

        Returns:

            {
                "success": True,
                "example": {...}
            }

        Or:

            {
                "success": False,
                "reason": "..."
            }
        """

        # --------------------------------------------------
        # VALIDATE PROMPT
        # --------------------------------------------------

        if not self._is_valid_text(
            prompt
        ):

            self.total_rejected += 1

            return {

                "success": False,

                "reason":
                    "Prompt is empty or invalid.",

            }

        # --------------------------------------------------
        # VALIDATE RESPONSE
        # --------------------------------------------------

        if not self._is_valid_text(
            response
        ):

            self.total_rejected += 1

            return {

                "success": False,

                "reason":
                    "Response is empty or invalid.",

            }

        # --------------------------------------------------
        # NORMALIZE TASK TYPE
        # --------------------------------------------------

        normalized_task_type = (
            self._normalize_task_type(
                task_type
            )
        )

        # --------------------------------------------------
        # NORMALIZE QUALITY
        # --------------------------------------------------

        if quality is None:

            normalized_quality = (
                self.default_quality
            )

        else:

            normalized_quality = (
                self._normalize_quality(
                    quality
                )
            )

        # --------------------------------------------------
        # BUILD TRAINING EXAMPLE
        # --------------------------------------------------

        example = {

            # Required by FineTuningDataset

            "task":

                self._create_task(
                    prompt
                ),

            "task_type":

                normalized_task_type,

            "input":

                prompt.strip(),

            "final_response":

                response.strip(),

            "quality":

                normalized_quality,

            # Optional metadata

            "initial_response":

                response.strip(),

            "peer_review":

                {

                    "verdict":

                        (
                            "PASS"

                            if normalized_quality
                            == "accepted"

                            else "PENDING"
                        ),

                    "feedback":

                        "",

                },

            "human_feedback":

                "",

            "source_model":

                source_model
                or "vault_runtime",

            "timestamp":

                datetime.now()
                .isoformat(),

        }

        # --------------------------------------------------
        # ADD METADATA
        # --------------------------------------------------

        if isinstance(
            metadata,
            dict,
        ):

            example[
                "metadata"
            ] = dict(
                metadata
            )

        else:

            example[
                "metadata"
            ] = {}

        # --------------------------------------------------
        # SUCCESS
        # --------------------------------------------------

        self.total_examples_built += 1

        return {

            "success": True,

            "example":

                example,

        }


    # ======================================================
    # CREATE TASK
    # ======================================================

    @staticmethod
    def _create_task(
        prompt: str,
    ) -> str:

        """
        Create a task description.

        The current implementation uses the prompt
        itself as the task description.
        """

        prompt = (
            prompt.strip()
        )

        # Keep the task useful but avoid extremely
        # large duplicated fields.

        max_length = 200

        if len(
            prompt
        ) > max_length:

            return (

                prompt[
                    :max_length
                ]

                + "..."

            )

        return prompt


    # ======================================================
    # VALIDATE TEXT
    # ======================================================

    @staticmethod
    def _is_valid_text(
        value: Any,
    ) -> bool:

        """
        Check whether a value contains useful text.
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
    # NORMALIZE TASK TYPE
    # ======================================================

    @staticmethod
    def _normalize_task_type(
        task_type: Any,
    ) -> str:

        """
        Normalize the task type.
        """

        if not isinstance(
            task_type,
            str,
        ):

            return "general"

        task_type = (

            task_type
            .strip()
            .lower()

        )

        if not task_type:

            return "general"

        return task_type


    # ======================================================
    # NORMALIZE QUALITY
    # ======================================================

    @staticmethod
    def _normalize_quality(
        quality: Any,
    ) -> str:

        """
        Normalize training example quality.
        """

        if not isinstance(
            quality,
            str,
        ):

            return "accepted"

        quality = (

            quality
            .strip()
            .lower()

        )

        if not quality:

            return "accepted"

        return quality


    # ======================================================
    # BUILD AND STORE
    # ======================================================

    def build_and_store(
        self,
        dataset: Any,
        prompt: str,
        response: str,
        task_type: str = "general",
        metadata: Optional[
            Dict[str, Any]
        ] = None,
        quality: Optional[str] = None,
        source_model: Optional[str] = None,
    ) -> Dict[str, Any]:

        """
        Build a training example and immediately
        store it in a FineTuningDataset.
        """

        # --------------------------------------------------
        # BUILD EXAMPLE
        # --------------------------------------------------

        build_result = (

            self.build_example(

                prompt=prompt,

                response=response,

                task_type=task_type,

                metadata=metadata,

                quality=quality,

                source_model=source_model,

            )

        )

        if not build_result.get(
            "success",
            False,
        ):

            return build_result

        example = (

            build_result.get(
                "example"
            )

        )

        # --------------------------------------------------
        # VALIDATE DATASET
        # --------------------------------------------------

        if dataset is None:

            return {

                "success": False,

                "reason":

                    (
                        "Dataset instance "
                        "was not provided."
                    ),

                "example":

                    example,

            }

        # --------------------------------------------------
        # STORE EXAMPLE
        # --------------------------------------------------

        try:

            if hasattr(
                dataset,
                "add_example",
            ):

                storage_result = (

                    dataset.add_example(
                        example
                    )

                )

            elif hasattr(
                dataset,
                "add",
            ):

                storage_result = (

                    dataset.add(
                        example
                    )

                )

            else:

                return {

                    "success": False,

                    "reason":

                        (
                            "Dataset does not "
                            "contain a supported "
                            "add method."
                        ),

                    "example":

                        example,

                }

        except Exception as exc:

            return {

                "success": False,

                "reason":

                    str(
                        exc
                    ),

                "example":

                    example,

            }

        # --------------------------------------------------
        # FINAL RESULT
        # --------------------------------------------------

        return {

            "success":

                bool(

                    storage_result.get(

                        "success",

                        True,

                    )

                    if isinstance(
                        storage_result,
                        dict,
                    )

                    else True

                ),

            "example":

                example,

            "storage":

                storage_result,

        }


    # ======================================================
    # BUILD STATUS
    # ======================================================

    def get_status(
        self,
    ) -> Dict[str, Any]:

        """
        Return Dataset Builder status.
        """

        return {

            "total_examples_built":

                self.total_examples_built,

            "total_rejected":

                self.total_rejected,

            "default_quality":

                self.default_quality,

        }


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. DATASET BUILDER TEST"
    )

    print("=" * 60)


    # ======================================================
    # CREATE BUILDER
    # ======================================================

    builder = (

        FineTuningDatasetBuilder()

    )


    # ======================================================
    # TEST 1
    # BUILD EXAMPLE
    # ======================================================

    print()

    print(
        "TEST 1: BUILD TRAINING EXAMPLE"
    )

    print("-" * 60)


    result = (

        builder.build_example(

            prompt=(

                "Write a Python function "
                "to calculate factorial."

            ),

            response=(

                "def factorial(n):\n"
                "    if n <= 1:\n"
                "        return 1\n"
                "    return n * factorial(n - 1)"

            ),

            task_type=(

                "coding"

            ),

            source_model=(

                "qwen3:4b"

            ),

        )

    )


    print(
        result
    )


    # ======================================================
    # TEST 2
    # INVALID PROMPT
    # ======================================================

    print()

    print(
        "TEST 2: INVALID PROMPT"
    )

    print("-" * 60)


    result = (

        builder.build_example(

            prompt="",

            response=(

                "This should fail."

            ),

            task_type=(

                "general"

            ),

        )

    )


    print(
        result
    )


    # ======================================================
    # TEST 3
    # BUILDER STATUS
    # ======================================================

    print()

    print(
        "TEST 3: BUILDER STATUS"
    )

    print("-" * 60)


    print(

        builder.get_status()

    )


    print()

    print("=" * 60)

    print(
        "DATASET BUILDER TEST COMPLETE"
    )

    print("=" * 60)