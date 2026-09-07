"""
V.A.U.L.T. Fine-Tuning Training Orchestrator

Coordinates the training stage between the prepared
fine-tuning dataset and the training backend.

Responsibilities:

    - Validate the training dataset
    - Validate training configuration
    - Create training jobs
    - Execute the trainer
    - Track training state
    - Prevent duplicate training runs
    - Return the candidate model artifact
    - Keep training failures isolated

Pipeline:

    Dataset
        ↓
    Validation
        ↓
    Training Configuration
        ↓
    Training Job
        ↓
    Fine-Tuning Trainer
        ↓
    Candidate Model Artifact
"""


from datetime import datetime
from typing import Any, Dict, List, Optional


from models.fine_tuning.trainer import (
    FineTuningTrainer,
)


# ==========================================================
# TRAINING ORCHESTRATOR
# ==========================================================

class FineTuningTrainingOrchestrator:

    """
    Coordinates fine-tuning training operations.

    This class provides a controlled layer between
    prepared training data and FineTuningTrainer.

    The orchestrator does not perform model training
    itself. It delegates training to FineTuningTrainer.
    """

    def __init__(
        self,
        trainer: Optional[
            FineTuningTrainer
        ] = None,
    ):

        # --------------------------------------------------
        # TRAINER
        # --------------------------------------------------

        self.trainer = (
            trainer
            or FineTuningTrainer()
        )

        # --------------------------------------------------
        # STATE
        # --------------------------------------------------

        self.is_training = False

        self.total_training_runs = 0

        self.successful_training_runs = 0

        self.failed_training_runs = 0

        self.last_result: Optional[
            Dict[str, Any]
        ] = None

        self.last_error: Optional[
            str
        ] = None

        self.training_history: List[
            Dict[str, Any]
        ] = []


    # ======================================================
    # VALIDATE DATASET
    # ======================================================

    def validate_dataset(
        self,
        dataset: Any,
    ) -> Dict[str, Any]:

        """
        Validate the training dataset.

        The orchestrator accepts either:

            - A list of training examples
            - A dictionary containing examples

        Empty datasets are rejected.
        """

        # --------------------------------------------------
        # LIST DATASET
        # --------------------------------------------------

        if isinstance(
            dataset,
            list,
        ):

            if not dataset:

                return {

                    "valid": False,

                    "reason":
                        "Training dataset is empty.",

                    "example_count": 0,

                }

            return {

                "valid": True,

                "example_count":
                    len(dataset),

            }

        # --------------------------------------------------
        # DICTIONARY DATASET
        # --------------------------------------------------

        if isinstance(
            dataset,
            dict,
        ):

            examples = (

                dataset.get(
                    "examples"
                )

                or dataset.get(
                    "records"
                )

                or dataset.get(
                    "data"
                )

            )

            if isinstance(
                examples,
                list,
            ):

                if not examples:

                    return {

                        "valid": False,

                        "reason":
                            "Training dataset is empty.",

                        "example_count": 0,

                    }

                return {

                    "valid": True,

                    "example_count":
                        len(examples),

                }

            return {

                "valid": False,

                "reason":
                    (
                        "Dataset dictionary does "
                        "not contain examples."
                    ),

                "example_count": 0,

            }

        # --------------------------------------------------
        # INVALID DATASET
        # --------------------------------------------------

        return {

            "valid": False,

            "reason":
                (
                    "Training dataset must be "
                    "a list or dictionary."
                ),

            "example_count": 0,

        }


    # ======================================================
    # VALIDATE CONFIGURATION
    # ======================================================

    def validate_configuration(
        self,
        base_model: Any,
        task_type: Any,
        dataset_path: Any,
    ) -> Dict[str, Any]:

        """
        Validate training configuration.
        """

        # --------------------------------------------------
        # BASE MODEL
        # --------------------------------------------------

        if not isinstance(
            base_model,
            str,
        ):

            return {

                "valid": False,

                "reason":
                    "Base model must be a string.",

            }

        if not base_model.strip():

            return {

                "valid": False,

                "reason":
                    "Base model cannot be empty.",

            }

        # --------------------------------------------------
        # TASK TYPE
        # --------------------------------------------------

        if not isinstance(
            task_type,
            str,
        ):

            return {

                "valid": False,

                "reason":
                    "Task type must be a string.",

            }

        if not task_type.strip():

            return {

                "valid": False,

                "reason":
                    "Task type cannot be empty.",

            }

        # --------------------------------------------------
        # DATASET PATH
        # --------------------------------------------------

        if not isinstance(
            dataset_path,
            str,
        ):

            return {

                "valid": False,

                "reason":
                    "Dataset path must be a string.",

            }

        if not dataset_path.strip():

            return {

                "valid": False,

                "reason":
                    "Dataset path cannot be empty.",

            }

        # --------------------------------------------------
        # SUCCESS
        # --------------------------------------------------

        return {

            "valid": True,

        }


    # ======================================================
    # CREATE TRAINING JOB
    # ======================================================

    def create_training_job(
        self,
        base_model: str,
        task_type: str,
        dataset_version: Any,
        dataset_path: str,
    ) -> Dict[str, Any]:

        """
        Create a training job through the trainer.
        """

        try:

            job = (

                self.trainer
                .create_job(

                    base_model=(
                        base_model
                    ),

                    task_type=(
                        task_type
                    ),

                    dataset_version=(
                        dataset_version
                    ),

                    dataset_path=(
                        dataset_path
                    ),

                )

            )

            return {

                "success": True,

                "job":
                    job,

            }

        except Exception as exc:

            self.last_error = str(
                exc
            )

            return {

                "success": False,

                "reason":
                    str(exc),

            }


    # ======================================================
    # RUN TRAINING
    # ======================================================

    def run_training(
        self,
        dataset: Any,
        base_model: str,
        task_type: str,
        dataset_version: Any,
        dataset_path: str,
    ) -> Dict[str, Any]:

        """
        Run a complete training operation.

        Flow:

            Dataset Validation
                    ↓
            Configuration Validation
                    ↓
            Create Training Job
                    ↓
            Run Trainer
                    ↓
            Return Candidate Artifact
        """

        # --------------------------------------------------
        # PREVENT DUPLICATE RUNS
        # --------------------------------------------------

        if self.is_training:

            return {

                "success": False,

                "stage":
                    "training_orchestrator",

                "reason":
                    (
                        "Training is already "
                        "running."
                    ),

            }

        self.is_training = True

        self.total_training_runs += 1

        started_at = (
            datetime.now()
            .isoformat()
        )

        try:

            # ==============================================
            # DATASET VALIDATION
            # ==============================================

            dataset_validation = (

                self.validate_dataset(
                    dataset
                )

            )

            if not dataset_validation.get(
                "valid",
                False,
            ):

                result = {

                    "success": False,

                    "stage":
                        "dataset_validation",

                    "reason":

                        dataset_validation.get(
                            "reason"
                        ),

                    "started_at":
                        started_at,

                    "completed_at":

                        datetime.now()
                        .isoformat(),

                    "dataset_validation":
                        dataset_validation,

                }

                self._store_result(
                    result
                )

                return result

            # ==============================================
            # CONFIGURATION VALIDATION
            # ==============================================

            configuration_validation = (

                self.validate_configuration(

                    base_model=(
                        base_model
                    ),

                    task_type=(
                        task_type
                    ),

                    dataset_path=(
                        dataset_path
                    ),

                )

            )

            if not configuration_validation.get(
                "valid",
                False,
            ):

                result = {

                    "success": False,

                    "stage":
                        "configuration_validation",

                    "reason":

                        configuration_validation.get(
                            "reason"
                        ),

                    "started_at":
                        started_at,

                    "completed_at":

                        datetime.now()
                        .isoformat(),

                    "dataset_validation":
                        dataset_validation,

                    "configuration_validation":

                        configuration_validation,

                }

                self._store_result(
                    result
                )

                return result

            # ==============================================
            # CREATE TRAINING JOB
            # ==============================================

            job_result = (

                self.create_training_job(

                    base_model=(
                        base_model
                    ),

                    task_type=(
                        task_type
                    ),

                    dataset_version=(
                        dataset_version
                    ),

                    dataset_path=(
                        dataset_path
                    ),

                )

            )

            if not job_result.get(
                "success",
                False,
            ):

                result = {

                    "success": False,

                    "stage":
                        "job_creation",

                    "reason":

                        job_result.get(
                            "reason"
                        ),

                    "started_at":
                        started_at,

                    "completed_at":

                        datetime.now()
                        .isoformat(),

                    "dataset_validation":
                        dataset_validation,

                    "job_creation":
                        job_result,

                }

                self._store_result(
                    result
                )

                return result

            # ==============================================
            # GET JOB
            # ==============================================

            training_job = (

                job_result.get(
                    "job"
                )

            )

            # ==============================================
            # RUN TRAINER
            # ==============================================

            try:

                training_result = (

                    self.trainer
                    .train(

                        training_job

                    )

                )

            except Exception as exc:

                training_result = {

                    "success": False,

                    "error":
                        str(exc),

                }

            # ==============================================
            # TRAINING FAILED
            # ==============================================

            if not training_result.get(
                "success",
                False,
            ):

                result = {

                    "success": False,

                    "stage":
                        "training",

                    "reason":

                        training_result.get(

                            "error",

                            training_result.get(
                                "reason"
                            ),

                        ),

                    "started_at":
                        started_at,

                    "completed_at":

                        datetime.now()
                        .isoformat(),

                    "dataset_validation":
                        dataset_validation,

                    "job":
                        training_job,

                    "training":
                        training_result,

                }

                self._store_result(
                    result
                )

                return result

            # ==============================================
            # GET ARTIFACT
            # ==============================================

            artifact = (

                training_result.get(
                    "artifact"
                )

            )

            if not isinstance(
                artifact,
                dict,
            ):

                result = {

                    "success": False,

                    "stage":
                        "artifact_validation",

                    "reason":
                        (
                            "Training completed but "
                            "no valid artifact was "
                            "returned."
                        ),

                    "started_at":
                        started_at,

                    "completed_at":

                        datetime.now()
                        .isoformat(),

                    "dataset_validation":
                        dataset_validation,

                    "job":
                        training_job,

                    "training":
                        training_result,

                }

                self._store_result(
                    result
                )

                return result

            # ==============================================
            # SUCCESS
            # ==============================================

            result = {

                "success": True,

                "stage":
                    "training_complete",

                "reason":
                    (
                        "Training completed "
                        "successfully."
                    ),

                "started_at":
                    started_at,

                "completed_at":

                    datetime.now()
                    .isoformat(),

                "example_count":

                    dataset_validation.get(
                        "example_count"
                    ),

                "base_model":
                    base_model,

                "task_type":
                    task_type,

                "dataset_version":
                    dataset_version,

                "dataset_path":
                    dataset_path,

                "job":
                    training_job,

                "training":
                    training_result,

                "artifact":
                    artifact,

            }

            self._store_result(
                result
            )

            return result

        except Exception as exc:

            self.last_error = str(
                exc
            )

            result = {

                "success": False,

                "stage":
                    "training_orchestrator",

                "reason":
                    str(exc),

                "started_at":
                    started_at,

                "completed_at":

                    datetime.now()
                    .isoformat(),

            }

            self._store_result(
                result
            )

            return result

        finally:

            self.is_training = False


    # ======================================================
    # STORE RESULT
    # ======================================================

    def _store_result(
        self,
        result: Dict[str, Any],
    ) -> None:

        """
        Store training results and update statistics.
        """

        self.last_result = result

        self.training_history.append(
            result
        )

        if result.get(
            "success",
            False,
        ):

            self.successful_training_runs += 1

        else:

            self.failed_training_runs += 1


    # ======================================================
    # GET LAST RESULT
    # ======================================================

    def get_last_result(
        self,
    ) -> Optional[Dict[str, Any]]:

        """
        Return the most recent training result.
        """

        return self.last_result


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
        Return training history.
        """

        history = list(
            self.training_history
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
    # GET STATUS
    # ======================================================

    def get_status(
        self,
    ) -> Dict[str, Any]:

        """
        Return orchestrator status.
        """

        return {

            "is_training":
                self.is_training,

            "total_training_runs":
                self.total_training_runs,

            "successful_training_runs":
                self.successful_training_runs,

            "failed_training_runs":
                self.failed_training_runs,

            "last_result":
                self.last_result,

            "last_error":
                self.last_error,

            "history_count":

                len(
                    self.training_history
                ),

        }


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. TRAINING ORCHESTRATOR TEST"
    )

    print("=" * 60)

    # ======================================================
    # CREATE ORCHESTRATOR
    # ======================================================

    orchestrator = (

        FineTuningTrainingOrchestrator()

    )

    # ======================================================
    # TEST DATASET
    # ======================================================

    test_dataset = [

        {

            "task":
                "Python programming",

            "task_type":
                "coding",

            "input":
                "Write a factorial function.",

            "final_response":
                (
                    "Use recursion with base "
                    "cases for zero and one."
                ),

            "quality":
                "accepted",

        },

        {

            "task":
                "Python programming",

            "task_type":
                "coding",

            "input":
                "Explain a Python list.",

            "final_response":
                (
                    "A Python list is an "
                    "ordered mutable collection."
                ),

            "quality":
                "accepted",

        },

    ]

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
        orchestrator.get_status()
    )

    # ======================================================
    # TEST 2
    # DATASET VALIDATION
    # ======================================================

    print()

    print(
        "TEST 2: DATASET VALIDATION"
    )

    print("-" * 60)

    print(

        orchestrator.validate_dataset(
            test_dataset
        )

    )

    # ======================================================
    # TEST 3
    # CONFIGURATION VALIDATION
    # ======================================================

    print()

    print(
        "TEST 3: CONFIGURATION VALIDATION"
    )

    print("-" * 60)

    print(

        orchestrator.validate_configuration(

            base_model=(
                "qwen3:4b"
            ),

            task_type=(
                "coding"
            ),

            dataset_path=(
                "data/fine_tuning"
            ),

        )

    )

    # ======================================================
    # TEST 4
    # RUN TRAINING
    # ======================================================

    print()

    print(
        "TEST 4: RUN TRAINING"
    )

    print("-" * 60)

    result = (

        orchestrator.run_training(

            dataset=(
                test_dataset
            ),

            base_model=(
                "qwen3:4b"
            ),

            task_type=(
                "coding"
            ),

            dataset_version=(
                1
            ),

            dataset_path=(
                "data/fine_tuning"
            ),

        )

    )

    print(
        result
    )

    # ======================================================
    # TEST 5
    # EMPTY DATASET
    # ======================================================

    print()

    print(
        "TEST 5: EMPTY DATASET"
    )

    print("-" * 60)

    result = (

        orchestrator.run_training(

            dataset=[],

            base_model=(
                "qwen3:4b"
            ),

            task_type=(
                "coding"
            ),

            dataset_version=(
                1
            ),

            dataset_path=(
                "data/fine_tuning"
            ),

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
        orchestrator.get_status()
    )

    print()

    print("=" * 60)

    print(
        "TRAINING ORCHESTRATOR TEST COMPLETE"
    )

    print("=" * 60)