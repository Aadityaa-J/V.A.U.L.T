"""
V.A.U.L.T. Fine-Tuning Pipeline Manager

Coordinates:

    Persistent Dataset Storage
        ↓
    Eligibility Checking
        ↓
    Base Model Selection
        ↓
    Fine-Tuning Pipeline
        ↓
    Model Deployment

This manager acts as the bridge between the
V.A.U.L.T. fine-tuning dataset and the complete
fine-tuning pipeline.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from models.fine_tuning.dataset import (
    FineTuningDataset,
)

from models.fine_tuning.eligibility import (
    EligibilityChecker,
)

from models.fine_tuning.pipeline import (
    FineTuningPipeline,
)


# ==========================================================
# FINE-TUNING PIPELINE MANAGER
# ==========================================================

class FineTuningPipelineManager:

    """
    Manage V.A.U.L.T. fine-tuning datasets and pipelines.

    Responsibilities:

        - Store training examples persistently
        - Load existing training examples
        - Prevent duplicate examples
        - Check example eligibility
        - Select a base model
        - Run the fine-tuning pipeline
        - Store pipeline history
    """

    def __init__(
        self,
        pipeline: Optional[
            FineTuningPipeline
        ] = None,
        eligibility_checker: Optional[
            EligibilityChecker
        ] = None,
        dataset: Optional[
            FineTuningDataset
        ] = None,
    ):

        # --------------------------------------------------
        # CORE COMPONENTS
        # --------------------------------------------------

        self.pipeline = (
            pipeline
            or FineTuningPipeline()
        )

        self.eligibility_checker = (
            eligibility_checker
            or EligibilityChecker()
        )

        # --------------------------------------------------
        # PERSISTENT DATASET STORAGE
        # --------------------------------------------------

        self.dataset = (
            dataset
            or FineTuningDataset()
        )

        # --------------------------------------------------
        # PIPELINE STATE
        # --------------------------------------------------

        self.is_running = False

        self.pipeline_runs = 0

        self.last_result: Optional[
            Dict[str, Any]
        ] = None

        self.pipeline_history: List[
            Dict[str, Any]
        ] = []

        # --------------------------------------------------
        # DATASET VERSION
        # --------------------------------------------------

        dataset_info = (
            self.dataset.get_info()
        )

        self.dataset_version = (
            dataset_info.get(
                "dataset_version",
                1,
            )
        )

        # --------------------------------------------------
        # DEFAULT MODEL
        # --------------------------------------------------

        self.default_base_model = (
            "qwen3:4b"
        )

    # ======================================================
    # INTERNAL DATASET HELPERS
    # ======================================================

    def _get_all_examples(
        self,
    ) -> List[Dict[str, Any]]:

        """
        Return all examples from the
        persistent dataset.
        """

        try:

            examples = (
                self.dataset.get_examples()
            )

            if isinstance(
                examples,
                list,
            ):

                return examples

            return []

        except Exception:

            return []

    # ======================================================
    # ADD TRAINING EXAMPLE
    # ======================================================

    def add_training_example(
        self,
        interaction: Dict[str, Any],
    ) -> Dict[str, Any]:

        """
        Add a training interaction to the
        persistent FineTuningDataset.

        Duplicate interactions are rejected.
        """

        # --------------------------------------------------
        # VALIDATE INPUT
        # --------------------------------------------------

        if not isinstance(
            interaction,
            dict,
        ):

            return {

                "success":
                    False,

                "reason":
                    (
                        "Training interaction "
                        "must be a dictionary."
                    ),

            }

        # --------------------------------------------------
        # CREATE ID
        # --------------------------------------------------

        example_id = (
            self._create_example_id(
                interaction
            )
        )

        # --------------------------------------------------
        # DUPLICATE CHECK
        # --------------------------------------------------

        existing_examples = (
            self._get_all_examples()
        )

        for example in existing_examples:

            existing_id = (
                example.get("id")
            )

            if existing_id == example_id:

                return {

                    "success":
                        False,

                    "reason":
                        (
                            "Duplicate training "
                            "example."
                        ),

                    "id":
                        example_id,

                }

            # ----------------------------------------------
            # FALLBACK DUPLICATE CHECK
            # ----------------------------------------------

            try:

                comparison_example = dict(
                    example
                )

                comparison_example.pop(
                    "id",
                    None,
                )

                comparison_example.pop(
                    "created_at",
                    None,
                )

                existing_hash = (
                    self._create_example_id(
                        comparison_example
                    )
                )

                if existing_hash == example_id:

                    return {

                        "success":
                            False,

                        "reason":
                            (
                                "Duplicate training "
                                "example."
                            ),

                        "id":
                            example_id,

                    }

            except Exception:

                continue

        # --------------------------------------------------
        # PREPARE STORED EXAMPLE
        # --------------------------------------------------

        stored_example = dict(
            interaction
        )

        stored_example["id"] = (
            example_id
        )

        stored_example.setdefault(

            "created_at",

            datetime.now()
            .isoformat(),

        )

        # --------------------------------------------------
        # STORE EXAMPLE
        # --------------------------------------------------

        try:

            storage_result = (
                self.dataset.add_example(
                    stored_example
                )
            )

        except Exception as exc:

            return {

                "success":
                    False,

                "stored":
                    False,

                "id":
                    example_id,

                "reason":
                    (
                        "Unable to store training "
                        f"example: {exc}"
                    ),

            }

        # --------------------------------------------------
        # HANDLE DATASET RESULT
        # --------------------------------------------------

        if isinstance(
            storage_result,
            dict,
        ):

            if not storage_result.get(
                "success",
                True,
            ):

                return {

                    "success":
                        False,

                    "stored":
                        False,

                    "id":
                        example_id,

                    "reason":

                        storage_result.get(

                            "reason",

                            (
                                "Dataset rejected "
                                "the training example."
                            ),

                        ),

                    "dataset_result":
                        storage_result,

                }

        # --------------------------------------------------
        # REFRESH DATASET VERSION
        # --------------------------------------------------

        try:

            dataset_info = (
                self.dataset.get_info()
            )

            self.dataset_version = (

                dataset_info.get(

                    "dataset_version",

                    self.dataset_version,

                )

            )

        except Exception:

            pass

        # --------------------------------------------------
        # SUCCESS
        # --------------------------------------------------

        return {

            "success":
                True,

            "stored":
                True,

            "id":
                example_id,

            "example_count":

                self.get_example_count(),

            "dataset_result":
                storage_result,

        }

    # ======================================================
    # CREATE EXAMPLE ID
    # ======================================================

    def _create_example_id(
        self,
        interaction: Dict[str, Any],
    ) -> str:

        """
        Create a deterministic ID for
        duplicate detection.
        """

        import hashlib
        import json

        clean_interaction = dict(
            interaction
        )

        clean_interaction.pop(
            "id",
            None,
        )

        clean_interaction.pop(
            "created_at",
            None,
        )

        serialized = json.dumps(

            clean_interaction,

            sort_keys=True,

            default=str,

        )

        return hashlib.sha256(

            serialized.encode(
                "utf-8"
            )

        ).hexdigest()

    # ======================================================
    # GET EXAMPLE COUNT
    # ======================================================

    def get_example_count(
        self,
        task_type: Optional[
            str
        ] = None,
    ) -> int:

        examples = (
            self._get_all_examples()
        )

        if task_type is None:

            return len(
                examples
            )

        return sum(

            1

            for example in examples

            if example.get(
                "task_type"
            ) == task_type

        )

    # ======================================================
    # GET TRAINING EXAMPLES
    # ======================================================

    def get_training_examples(
        self,
        task_type: Optional[
            str
        ] = None,
    ) -> List[Dict[str, Any]]:

        examples = (
            self._get_all_examples()
        )

        if task_type is None:

            return list(
                examples
            )

        return [

            example

            for example in examples

            if example.get(
                "task_type"
            ) == task_type

        ]

    # ======================================================
    # CLEAR TRAINING EXAMPLES
    # ======================================================

    def clear_training_examples(
        self,
    ) -> None:

        raise NotImplementedError(

            "Persistent dataset clearing is "
            "not implemented by "
            "FineTuningPipelineManager. "

            "Use FineTuningDataset directly "
            "to manage stored data."

        )

    # ======================================================
    # CHECK ELIGIBILITY
    # ======================================================

    def check_eligibility(
        self,
        task_type: str = "general",
    ) -> Dict[str, Any]:

        examples = (

            self.get_training_examples(

                task_type=task_type

            )

        )

        results = []

        eligible_examples = 0

        for interaction in examples:

            result = (

                self.eligibility_checker.evaluate(

                    interaction

                )

            )

            results.append(
                result
            )

            if result.get(

                "eligible",

                False,

            ):

                eligible_examples += 1

        # --------------------------------------------------
        # NO EXAMPLES
        # --------------------------------------------------

        if not examples:

            return {

                "eligible":
                    False,

                "reason":
                    (
                        "No training examples "
                        "available for this "
                        "task type."
                    ),

                "example_count":
                    0,

                "eligible_examples":
                    0,

                "task_type":
                    task_type,

                "results":
                    results,

            }

        # --------------------------------------------------
        # NO ELIGIBLE EXAMPLES
        # --------------------------------------------------

        if eligible_examples <= 0:

            return {

                "eligible":
                    False,

                "reason":
                    (
                        "No eligible training "
                        "examples found."
                    ),

                "example_count":
                    len(
                        examples
                    ),

                "eligible_examples":
                    eligible_examples,

                "task_type":
                    task_type,

                "results":
                    results,

            }

        # --------------------------------------------------
        # DATASET ELIGIBLE
        # --------------------------------------------------

        return {

            "eligible":
                True,

            "reason":
                (
                    "Eligible training examples "
                    "found."
                ),

            "example_count":
                len(
                    examples
                ),

            "eligible_examples":
                eligible_examples,

            "task_type":
                task_type,

            "results":
                results,

        }

    # ======================================================
    # SELECT BASE MODEL
    # ======================================================

    def select_base_model(
        self,
        task_type: str = "general",
    ) -> Dict[str, Any]:

        model = (
            self.default_base_model
        )

        return {

            "success":
                True,

            "model":
                model,

            "task_type":
                task_type,

            "reason":
                (
                    "Default base model "
                    "selected."
                ),

        }

    # ======================================================
    # GET DATASET VERSION
    # ======================================================

    def get_dataset_version(
        self,
    ) -> int:

        try:

            dataset_info = (
                self.dataset.get_info()
            )

            self.dataset_version = (

                dataset_info.get(

                    "dataset_version",

                    self.dataset_version,

                )

            )

        except Exception:

            pass

        return self.dataset_version

    # ======================================================
    # GET STATUS
    # ======================================================

    def get_status(
        self,
    ) -> Dict[str, Any]:

        return {

            "pipeline_running":
                self.is_running,

            "total_examples":
                self.get_example_count(),

            "dataset_version":
                self.get_dataset_version(),

            "pipeline_runs":
                self.pipeline_runs,

            "last_result":
                self.last_result,

        }

    # ======================================================
    # RUN PIPELINE
    # ======================================================

    def run_pipeline(
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

        # NEW: DEVELOPMENT OVERRIDE
        force: bool = False,

    ) -> Dict[str, Any]:

        """
        Run the complete fine-tuning pipeline.

        force=True:
            Explicit development override.

            The underlying pipeline and scheduler
            still perform their safety logic.
        """

        # --------------------------------------------------
        # ALREADY RUNNING
        # --------------------------------------------------

        if self.is_running:

            return {

                "success":
                    False,

                "stage":
                    "pipeline_manager",

                "reason":
                    (
                        "Fine-tuning pipeline "
                        "is already running."
                    ),

                "force":
                    force,

            }

        # --------------------------------------------------
        # START PIPELINE
        # --------------------------------------------------

        self.is_running = True

        started_at = (

            datetime.now()

            .isoformat()

        )

        try:

            # ==============================================
            # EXAMPLE COUNT
            # ==============================================

            example_count = (

                self.get_example_count(

                    task_type=task_type

                )

            )

            # ==============================================
            # ELIGIBILITY CHECK
            # ==============================================

            eligibility_result = (

                self.check_eligibility(

                    task_type=task_type

                )

            )

            if not eligibility_result.get(

                "eligible",

                False,

            ):

                result = {

                    "success":
                        False,

                    "stage":
                        "eligibility",

                    "reason":

                        eligibility_result.get(

                            "reason",

                            (
                                "Dataset is not "
                                "eligible for "
                                "fine-tuning."
                            ),

                        ),

                    "started_at":
                        started_at,

                    "completed_at":

                        datetime.now()
                        .isoformat(),

                    "eligibility":
                        eligibility_result,

                    "example_count":
                        example_count,

                    "task_type":
                        task_type,

                    "force":
                        force,

                }

                self._store_result(
                    result
                )

                return result

            # ==============================================
            # MODEL SELECTION
            # ==============================================

            model_selection = (

                self.select_base_model(

                    task_type=task_type

                )

            )

            if not model_selection.get(

                "success",

                False,

            ):

                result = {

                    "success":
                        False,

                    "stage":
                        "model_selection",

                    "reason":

                        model_selection.get(

                            "reason",

                            (
                                "Unable to select "
                                "a base model."
                            ),

                        ),

                    "started_at":
                        started_at,

                    "completed_at":

                        datetime.now()
                        .isoformat(),

                    "eligibility":
                        eligibility_result,

                    "model_selection":
                        model_selection,

                    "task_type":
                        task_type,

                    "force":
                        force,

                }

                self._store_result(
                    result
                )

                return result

            # ==============================================
            # BASE MODEL
            # ==============================================

            base_model = (

                model_selection.get(
                    "model"
                )

            )

            # ==============================================
            # DATASET VERSION
            # ==============================================

            dataset_version = (

                self.get_dataset_version()

            )

            # ==============================================
            # RUN FINE-TUNING PIPELINE
            # ==============================================

            pipeline_result = (

                self.pipeline.run(

                    example_count=
                        example_count,

                    base_model=
                        base_model,

                    task_type=
                        task_type,

                    dataset_version=
                        dataset_version,

                    dataset_path=
                        dataset_path,

                    evaluation_dataset=
                        evaluation_dataset,

                    current_time=
                        current_time,

                    # IMPORTANT:
                    # Pass force into the main pipeline.
                    force=
                        force,

                )

            )

            # ==============================================
            # FINAL RESULT
            # ==============================================

            result = {

                "success":

                    pipeline_result.get(

                        "success",

                        False,

                    ),

                "stage":

                    pipeline_result.get(
                        "stage"
                    ),

                "reason":

                    pipeline_result.get(
                        "reason"
                    ),

                "started_at":
                    started_at,

                "completed_at":

                    datetime.now()
                    .isoformat(),

                "task_type":
                    task_type,

                "example_count":
                    example_count,

                "dataset_version":
                    dataset_version,

                "base_model":
                    base_model,

                "force":
                    force,

                "eligibility":
                    eligibility_result,

                "model_selection":
                    model_selection,

                "pipeline":
                    pipeline_result,

            }

            # ==============================================
            # SUCCESS COUNTER
            # ==============================================

            if result.get(

                "success",

                False,

            ):

                self.pipeline_runs += 1

            # ==============================================
            # STORE RESULT
            # ==============================================

            self._store_result(
                result
            )

            return result

        except Exception as exc:

            result = {

                "success":
                    False,

                "stage":
                    "pipeline_manager",

                "reason":
                    str(exc),

                "started_at":
                    started_at,

                "completed_at":

                    datetime.now()
                    .isoformat(),

                "task_type":
                    task_type,

                "force":
                    force,

            }

            self._store_result(
                result
            )

            return result

        finally:

            self.is_running = False

    # ======================================================
    # COMPATIBILITY RUN METHOD
    # ======================================================

    def run(
        self,
        **kwargs,
    ) -> Dict[str, Any]:

        """
        Compatibility method for other
        V.A.U.L.T. components.
        """

        # ==================================================
        # TASK TYPE
        # ==================================================

        task_type = (

            kwargs.get(

                "task_type",

                "general",

            )

        )

        # ==================================================
        # DATASET PATH
        # ==================================================

        dataset_path = (

            kwargs.get(

                "dataset_path",

                "data/fine_tuning",

            )

        )

        # ==================================================
        # EVALUATION DATASET
        # ==================================================

        evaluation_dataset = (

            kwargs.get(

                "evaluation_dataset",

                "data/evaluation",

            )

        )

        # ==================================================
        # CURRENT TIME
        # ==================================================

        current_time = (

            kwargs.get(

                "current_time",

                None,

            )

        )

        # ==================================================
        # FORCE
        # ==================================================

        force = (

            kwargs.get(

                "force",

                False,

            )

        )

        # ==================================================
        # OPTIONAL EXTERNAL PARAMETERS
        # ==================================================

        requested_example_count = (

            kwargs.get(

                "example_count",

                None,

            )

        )

        requested_base_model = (

            kwargs.get(

                "base_model",

                None,

            )

        )

        requested_dataset_version = (

            kwargs.get(

                "dataset_version",

                None,

            )

        )

        # ==================================================
        # RUN PIPELINE
        # ==================================================

        result = (

            self.run_pipeline(

                task_type=
                    task_type,

                dataset_path=
                    dataset_path,

                evaluation_dataset=
                    evaluation_dataset,

                current_time=
                    current_time,

                force=
                    force,

            )

        )

        # ==================================================
        # ADD COMPATIBILITY INFORMATION
        # ==================================================

        if isinstance(

            result,

            dict,

        ):

            result.setdefault(

                "requested_parameters",

                {

                    "example_count":
                        requested_example_count,

                    "base_model":
                        requested_base_model,

                    "dataset_version":
                        requested_dataset_version,

                    "task_type":
                        task_type,

                    "force":
                        force,

                },

            )

        return result

    # ======================================================
    # STORE RESULT
    # ======================================================

    def _store_result(
        self,
        result: Dict[str, Any],
    ) -> None:

        self.last_result = (
            result
        )

        self.pipeline_history.append(
            result
        )

    # ======================================================
    # GET LAST RESULT
    # ======================================================

    def get_last_result(
        self,
    ) -> Optional[Dict[str, Any]]:

        return self.last_result

    # ======================================================
    # GET HISTORY
    # ======================================================

    def get_history(
        self,
    ) -> List[Dict[str, Any]]:

        return list(
            self.pipeline_history
        )


# ==========================================================
# TEST DATA HELPER
# ==========================================================

def create_test_interaction(
    number: int,
    task_type: str = "engineering",
) -> Dict[str, Any]:

    """
    Create a valid test interaction.
    """

    return {

        "task":

            (
                f"Engineering task "
                f"{number}"
            ),

        "task_type":
            task_type,

        "input":

            (
                f"Calculate engineering "
                f"value {number}."
            ),

        "final_response":

            (
                f"This is a valid engineering "
                f"response for training example "
                f"{number}."
            ),

        "peer_review": {

            "verdict":
                "PASS"

        },

        "human_feedback":
            "",

    }


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. PIPELINE MANAGER TEST"
    )

    print("=" * 60)

    # ======================================================
    # CREATE MANAGER
    # ======================================================

    manager = (

        FineTuningPipelineManager()

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
        manager.get_status()
    )

    # ======================================================
    # TEST 2
    # CURRENT DATASET
    # ======================================================

    print()

    print(
        "TEST 2: PERSISTENT DATASET"
    )

    print("-" * 60)

    print(

        "Total examples:",

        manager.get_example_count(),

    )

    print(

        "Engineering examples:",

        manager.get_example_count(

            task_type="engineering"

        ),

    )

    print(

        "General examples:",

        manager.get_example_count(

            task_type="general"

        ),

    )

    # ======================================================
    # TEST 3
    # ELIGIBILITY CHECK
    # ======================================================

    print()

    print(
        "TEST 3: ELIGIBILITY CHECK"
    )

    print("-" * 60)

    for task_type in [

        "engineering",

        "general",

    ]:

        eligibility = (

            manager.check_eligibility(

                task_type=task_type

            )

        )

        print()

        print(

            f"{task_type.upper()} "

            "ELIGIBILITY:"

        )

        print(
            eligibility
        )

    # ======================================================
    # TEST 4
    # MODEL SELECTION
    # ======================================================

    print()

    print(
        "TEST 4: MODEL SELECTION"
    )

    print("-" * 60)

    selection = (

        manager.select_base_model(

            task_type="engineering"

        )

    )

    print(
        selection
    )

    # ======================================================
    # TEST 5
    # FORCED PIPELINE RUN
    # ======================================================

    print()

    print(
        "TEST 5: FORCED PIPELINE RUN"
    )

    print("-" * 60)

    result = (

        manager.run_pipeline(

            task_type="engineering",

            force=True,

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
        manager.get_status()
    )

    print()

    print("=" * 60)

    print(
        "PIPELINE MANAGER TEST COMPLETE"
    )

    print("=" * 60)