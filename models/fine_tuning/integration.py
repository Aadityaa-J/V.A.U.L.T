"""
V.A.U.L.T. Fine-Tuning Integration

Connects the fine-tuning system to the main
V.A.U.L.T. runtime.

Responsibilities:

    - Collect successful interactions
    - Validate interactions with the quality filter
    - Reject low-quality training data
    - Convert interactions into training examples
    - Store examples in the fine-tuning dataset
    - Check fine-tuning eligibility
    - Trigger the pipeline when appropriate
    - Prevent training from running too frequently
    - Keep fine-tuning failures isolated from V.A.U.L.T.

IMPORTANT:

Fine-tuning must NEVER crash the main assistant.

If the fine-tuning system fails, V.A.U.L.T.
continues operating normally.
"""


from datetime import datetime
from typing import Any, Dict, List, Optional


from models.fine_tuning.pipeline_manager import (
    FineTuningPipelineManager,
)

from models.fine_tuning.quality_filter import (
    FineTuningQualityFilter,
)


# ==========================================================
# FINE-TUNING INTEGRATION
# ==========================================================

class FineTuningIntegration:

    """
    Connect the V.A.U.L.T. runtime with the
    fine-tuning pipeline.

    Typical flow:

        User Request
              ↓
        V.A.U.L.T. Generates Response
              ↓
        Interaction Evaluated
              ↓
        Quality Filter
              ↓
        Training Example Stored
              ↓
        Eligibility Checked
              ↓
        Pipeline Triggered When Ready
    """

    def __init__(
        self,
        pipeline_manager: Optional[
            FineTuningPipelineManager
        ] = None,
        quality_filter: Optional[
            FineTuningQualityFilter
        ] = None,
        auto_train: bool = False,
        minimum_examples_before_check: int = 5,
    ):

        # --------------------------------------------------
        # PIPELINE MANAGER
        # --------------------------------------------------

        self.pipeline_manager = (
            pipeline_manager
            or FineTuningPipelineManager()
        )

        # --------------------------------------------------
        # QUALITY FILTER
        # --------------------------------------------------

        self.quality_filter = (
            quality_filter
            or FineTuningQualityFilter()
        )

        # --------------------------------------------------
        # CONFIGURATION
        # --------------------------------------------------

        self.auto_train = bool(
            auto_train
        )

        self.minimum_examples_before_check = max(
            1,
            int(
                minimum_examples_before_check
            ),
        )

        # --------------------------------------------------
        # STATE
        # --------------------------------------------------

        self.total_interactions = 0

        self.total_examples_added = 0

        self.total_quality_rejections = 0

        self.last_training_check_count = 0

        self.last_training_result: Optional[
            Dict[str, Any]
        ] = None

        self.last_error: Optional[
            str
        ] = None

        self.integration_history: List[
            Dict[str, Any]
        ] = []


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
            task_type.strip()
            .lower()
        )

        if not task_type:

            return "general"

        return task_type


    # ======================================================
    # RECORD INTERACTION
    # ======================================================

    def record_interaction(
        self,
        prompt: str,
        response: str,
        task_type: str = "general",
        successful: bool = True,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:

        """
        Record a V.A.U.L.T. interaction.

        Flow:

            Interaction
                ↓
            Basic Validation
                ↓
            Success Check
                ↓
            Quality Filter
                ↓
            Dataset
                ↓
            Optional Training Check
        """

        self.total_interactions += 1

        task_type = (
            self._normalize_task_type(
                task_type
            )
        )

        # --------------------------------------------------
        # VALIDATE PROMPT
        # --------------------------------------------------

        if not self._is_valid_text(
            prompt
        ):

            result = {

                "success":
                    False,

                "stored":
                    False,

                "reason":
                    "Prompt is empty or invalid.",

                "task_type":
                    task_type,

            }

            self._store_history(
                result
            )

            return result

        # --------------------------------------------------
        # VALIDATE RESPONSE
        # --------------------------------------------------

        if not self._is_valid_text(
            response
        ):

            result = {

                "success":
                    False,

                "stored":
                    False,

                "reason":
                    "Response is empty or invalid.",

                "task_type":
                    task_type,

            }

            self._store_history(
                result
            )

            return result

        # --------------------------------------------------
        # SKIP UNSUCCESSFUL INTERACTIONS
        # --------------------------------------------------

        if not successful:

            result = {

                "success":
                    True,

                "stored":
                    False,

                "reason":
                    (
                        "Interaction was marked "
                        "as unsuccessful and was "
                        "not added to training data."
                    ),

                "task_type":
                    task_type,

            }

            self._store_history(
                result
            )

            return result

        # --------------------------------------------------
        # QUALITY FILTER
        # --------------------------------------------------

        try:

            quality_result = (

                self.quality_filter.evaluate(

                    prompt=(
                        prompt
                    ),

                    response=(
                        response
                    ),

                    task_type=(
                        task_type
                    ),

                )

            )

        except Exception as exc:

            self.last_error = str(
                exc
            )

            result = {

                "success":
                    False,

                "stored":
                    False,

                "reason":
                    (
                        "Quality filter failed: "
                        f"{exc}"
                    ),

                "task_type":
                    task_type,

            }

            self._store_history(
                result
            )

            return result

        # --------------------------------------------------
        # REJECT LOW-QUALITY INTERACTION
        # --------------------------------------------------

        if not quality_result.get(
            "accepted",
            False,
        ):

            self.total_quality_rejections += 1

            result = {

                "success":
                    True,

                "stored":
                    False,

                "quality_accepted":
                    False,

                "reason":

                    quality_result.get(

                        "reason",

                        (
                            "Interaction was rejected "
                            "by the quality filter."
                        ),

                    ),

                "quality":
                    quality_result,

                "task_type":
                    task_type,

                "total_quality_rejections":

                    self.total_quality_rejections,

            }

            self._store_history(
                result
            )

            return result

        # --------------------------------------------------
        # BUILD METADATA
        # --------------------------------------------------

        example_metadata = {

            "source":
                "vault_runtime",

            "recorded_at":
                datetime.now().isoformat(),

            "quality_score":

                quality_result.get(
                    "quality_score"
                ),

        }

        if isinstance(
            metadata,
            dict,
        ):

            example_metadata.update(
                metadata
            )

        # --------------------------------------------------
        # BUILD TRAINING INTERACTION
        #
        # IMPORTANT:
        #
        # EligibilityChecker requires:
        #
        #     task
        #
        # PipelineManager also uses:
        #
        #     task_type
        #
        # Therefore BOTH fields are stored.
        # --------------------------------------------------

        interaction = {

            "prompt":
                prompt.strip(),

            "response":
                response.strip(),

            "task":
                task_type,

            "task_type":
                task_type,

            "metadata":
                example_metadata,

            "quality":
                quality_result,

            "created_at":
                datetime.now().isoformat(),

        }

        # --------------------------------------------------
        # ADD TRAINING EXAMPLE
        # --------------------------------------------------

        try:

            add_result = (

                self.pipeline_manager
                .add_training_example(

                    interaction

                )

            )

        except Exception as exc:

            self.last_error = str(
                exc
            )

            result = {

                "success":
                    False,

                "stored":
                    False,

                "reason":
                    str(exc),

                "quality":
                    quality_result,

                "task_type":
                    task_type,

            }

            self._store_history(
                result
            )

            return result

        # --------------------------------------------------
        # CHECK DATASET RESULT
        # --------------------------------------------------

        dataset_success = True

        if isinstance(
            add_result,
            dict,
        ):

            dataset_success = add_result.get(
                "success",
                True,
            )

        if not dataset_success:

            result = {

                "success":
                    False,

                "stored":
                    False,

                "reason":

                    add_result.get(

                        "reason",

                        (
                            "Dataset rejected "
                            "the training example."
                        ),

                    ),

                "quality":
                    quality_result,

                "dataset_result":
                    add_result,

                "task_type":
                    task_type,

            }

            self._store_history(
                result
            )

            return result

        # --------------------------------------------------
        # EXAMPLE SUCCESSFULLY ADDED
        # --------------------------------------------------

        self.total_examples_added += 1

        result = {

            "success":
                True,

            "stored":
                True,

            "quality_accepted":
                True,

            "quality":
                quality_result,

            "task_type":
                task_type,

            "dataset_result":
                add_result,

            "total_examples_added":
                self.total_examples_added,

        }

        # --------------------------------------------------
        # AUTO-TRAIN CHECK
        # --------------------------------------------------

        if self.auto_train:

            training_result = (

                self._maybe_run_pipeline(

                    task_type=(
                        task_type
                    )

                )

            )

            result[
                "training_check"
            ] = training_result

        self._store_history(
            result
        )

        return result


    # ======================================================
    # SHOULD CHECK TRAINING
    # ======================================================

    def _should_check_training(
        self,
        example_count: int,
    ) -> bool:

        """
        Prevent unnecessary repeated training checks.
        """

        if (

            example_count
            <
            self.minimum_examples_before_check

        ):

            return False

        if (

            example_count
            ==
            self.last_training_check_count

        ):

            return False

        return True


    # ======================================================
    # MAYBE RUN PIPELINE
    # ======================================================

    def _maybe_run_pipeline(
        self,
        task_type: str,
    ) -> Dict[str, Any]:

        """
        Check whether fine-tuning should run.

        Pipeline errors are captured so the main
        V.A.U.L.T. assistant never crashes.
        """

        try:

            example_count = (

                self.pipeline_manager
                .get_example_count(

                    task_type=(
                        task_type
                    )

                )

            )

        except Exception as exc:

            self.last_error = str(
                exc
            )

            return {

                "checked":
                    False,

                "started":
                    False,

                "reason":
                    str(exc),

            }

        # --------------------------------------------------
        # CHECK FREQUENCY
        # --------------------------------------------------

        if not self._should_check_training(
            example_count
        ):

            return {

                "checked":
                    False,

                "started":
                    False,

                "reason":
                    (
                        "Training check is not "
                        "required yet."
                    ),

                "example_count":
                    example_count,

            }

        self.last_training_check_count = (
            example_count
        )

        # --------------------------------------------------
        # ELIGIBILITY
        # --------------------------------------------------

        try:

            eligibility = (

                self.pipeline_manager
                .check_eligibility(

                    task_type=(
                        task_type
                    )

                )

            )

        except Exception as exc:

            self.last_error = str(
                exc
            )

            return {

                "checked":
                    True,

                "started":
                    False,

                "reason":
                    str(exc),

                "example_count":
                    example_count,

            }

        # --------------------------------------------------
        # NOT ELIGIBLE
        # --------------------------------------------------

        if not eligibility.get(
            "eligible",
            False,
        ):

            return {

                "checked":
                    True,

                "started":
                    False,

                "eligible":
                    False,

                "reason":

                    eligibility.get(

                        "reason",

                        (
                            "Dataset is not yet "
                            "eligible for "
                            "fine-tuning."
                        ),

                    ),

                "example_count":
                    example_count,

                "eligibility":
                    eligibility,

            }

        # --------------------------------------------------
        # RUN PIPELINE
        # --------------------------------------------------

        try:

            pipeline_result = (

                self.pipeline_manager
                .run_pipeline(

                    task_type=(
                        task_type
                    )

                )

            )

            self.last_training_result = (
                pipeline_result
            )

            return {

                "checked":
                    True,

                "started":
                    True,

                "eligible":
                    True,

                "example_count":
                    example_count,

                "eligibility":
                    eligibility,

                "pipeline":
                    pipeline_result,

            }

        except Exception as exc:

            self.last_error = str(
                exc
            )

            return {

                "checked":
                    True,

                "started":
                    False,

                "eligible":
                    True,

                "success":
                    False,

                "reason":
                    str(exc),

                "example_count":
                    example_count,

                "eligibility":
                    eligibility,

            }


    # ======================================================
    # MANUAL PIPELINE RUN
    # ======================================================

    def run_training(
        self,
        task_type: str = "general",
        dataset_path: str = (
            "data/fine_tuning"
        ),
        evaluation_dataset: Any = (
            "data/evaluation"
        ),
        current_time: Optional[
            datetime
        ] = None,
    ) -> Dict[str, Any]:

        """
        Manually run the fine-tuning pipeline.
        """

        task_type = (

            self._normalize_task_type(
                task_type
            )

        )

        try:

            result = (

                self.pipeline_manager
                .run_pipeline(

                    task_type=(
                        task_type
                    ),

                    dataset_path=(
                        dataset_path
                    ),

                    evaluation_dataset=(
                        evaluation_dataset
                    ),

                    current_time=(
                        current_time
                    ),

                )

            )

            self.last_training_result = (
                result
            )

            return result

        except Exception as exc:

            self.last_error = str(
                exc
            )

            return {

                "success":
                    False,

                "stage":
                    "integration",

                "reason":
                    str(exc),

                "task_type":
                    task_type,

            }


    # ======================================================
    # ENABLE AUTO TRAINING
    # ======================================================

    def enable_auto_training(
        self,
    ) -> None:

        """
        Enable automatic fine-tuning checks.
        """

        self.auto_train = True


    # ======================================================
    # DISABLE AUTO TRAINING
    # ======================================================

    def disable_auto_training(
        self,
    ) -> None:

        """
        Disable automatic fine-tuning checks.
        """

        self.auto_train = False


    # ======================================================
    # GET STATUS
    # ======================================================

    def get_status(
        self,
    ) -> Dict[str, Any]:

        """
        Return the fine-tuning integration status.
        """

        try:

            pipeline_status = (

                self.pipeline_manager
                .get_status()

            )

        except Exception as exc:

            pipeline_status = {

                "error":
                    str(exc),

            }

        return {

            "auto_train":
                self.auto_train,

            "total_interactions":
                self.total_interactions,

            "total_examples_added":
                self.total_examples_added,

            "total_quality_rejections":
                self.total_quality_rejections,

            "minimum_examples_before_check":

                self.minimum_examples_before_check,

            "last_training_check_count":

                self.last_training_check_count,

            "last_training_result":

                self.last_training_result,

            "last_error":
                self.last_error,

            "history_count":

                len(
                    self.integration_history
                ),

            "pipeline_manager":
                pipeline_status,

        }


    # ======================================================
    # GET HISTORY
    # ======================================================

    def get_history(
        self,
        limit: Optional[
            int
        ] = None,
    ) -> List[Dict[str, Any]]:

        """
        Return integration history.
        """

        history = list(
            self.integration_history
        )

        if limit is None:

            return history

        try:

            limit = int(
                limit
            )

        except (

            TypeError,
            ValueError,

        ):

            return history

        if limit <= 0:

            return []

        return history[
            -limit:
        ]


    # ======================================================
    # STORE HISTORY
    # ======================================================

    def _store_history(
        self,
        result: Dict[str, Any],
    ) -> None:

        """
        Store an integration event.
        """

        event = dict(
            result
        )

        event[
            "recorded_at"
        ] = (

            datetime.now()
            .isoformat()

        )

        self.integration_history.append(
            event
        )


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNING INTEGRATION TEST"
    )

    print("=" * 60)

    # ======================================================
    # CREATE INTEGRATION
    # ======================================================

    integration = (

        FineTuningIntegration(

            auto_train=False,

            minimum_examples_before_check=5,

        )

    )

    # ======================================================
    # TEST 1
    # INITIAL STATUS
    # ======================================================

    print()

    print(
        "TEST 1: INITIAL STATUS"
    )

    print("-" * 60)

    print(
        integration.get_status()
    )

    # ======================================================
    # TEST 2
    # GOOD INTERACTION
    # ======================================================

    print()

    print(
        "TEST 2: GOOD INTERACTION"
    )

    print("-" * 60)

    result = (

        integration.record_interaction(

            prompt=(
                "Write a Python function "
                "that calculates factorial."
            ),

            response=(
                "You can create a recursive "
                "factorial function with base "
                "cases for zero and one."
            ),

            task_type=(
                "coding"
            ),

        )

    )

    print(
        result
    )

    # ======================================================
    # TEST 3
    # PLACEHOLDER RESPONSE
    # ======================================================

    print()

    print(
        "TEST 3: LOW QUALITY RESPONSE"
    )

    print("-" * 60)

    result = (

        integration.record_interaction(

            prompt=(
                "Explain machine learning."
            ),

            response=(
                "I don't know"
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
    # TEST 4
    # ERROR RESPONSE
    # ======================================================

    print()

    print(
        "TEST 4: ERROR RESPONSE"
    )

    print("-" * 60)

    result = (

        integration.record_interaction(

            prompt=(
                "Write a Python program."
            ),

            response=(
                "Traceback: generation failed"
            ),

            task_type=(
                "coding"
            ),

        )

    )

    print(
        result
    )

    # ======================================================
    # TEST 5
    # UNSUCCESSFUL INTERACTION
    # ======================================================

    print()

    print(
        "TEST 5: UNSUCCESSFUL INTERACTION"
    )

    print("-" * 60)

    result = (

        integration.record_interaction(

            prompt=(
                "Bad answer example"
            ),

            response=(
                "This answer is incorrect."
            ),

            task_type=(
                "general"
            ),

            successful=False,

        )

    )

    print(
        result
    )

    # ======================================================
    # TEST 6
    # FINAL STATUS
    # ======================================================

    print()

    print(
        "TEST 6: FINAL STATUS"
    )

    print("-" * 60)

    print(
        integration.get_status()
    )

    # ======================================================
    # TEST 7
    # HISTORY
    # ======================================================

    print()

    print(
        "TEST 7: INTEGRATION HISTORY"
    )

    print("-" * 60)

    print(
        integration.get_history()
    )

    print()

    print("=" * 60)

    print(
        "FINE-TUNING INTEGRATION TEST COMPLETE"
    )

    print("=" * 60)