"""
V.A.U.L.T. Fine-Tuning Lifecycle Manager

Coordinates the complete automatic fine-tuning lifecycle.

Flow:

Interaction
    ↓
Eligibility Check
    ↓
Training Dataset
    ↓
Scheduler
    ↓
Resource Check
    ↓
Training Backend
    ↓
Evaluation
    ↓
Model Registry
"""

from typing import Any, Dict


from models.fine_tuning.dataset import (
    FineTuningDataset
)

from models.fine_tuning.eligibility import (
    EligibilityChecker
)

from models.fine_tuning.scheduler import (
    FineTuningScheduler
)

from models.fine_tuning.trainer import (
    FineTuningTrainer
)

from models.fine_tuning.evaluator import (
    FineTuningEvaluator
)

from models.fine_tuning.registry import (
    ModelRegistry
)


class FineTuningManager:

    """
    Main coordinator for the automatic
    fine-tuning lifecycle.
    """

    def __init__(
        self,
        dataset=None,
        eligibility_checker=None,
        scheduler=None,
        trainer=None,
        evaluator=None,
        registry=None,
    ):

        self.dataset = (
            dataset
            or FineTuningDataset()
        )

        self.eligibility_checker = (
            eligibility_checker
            or EligibilityChecker()
        )

        self.scheduler = (
            scheduler
            or FineTuningScheduler()
        )

        self.trainer = (
            trainer
            or FineTuningTrainer()
        )

        self.evaluator = (
            evaluator
            or FineTuningEvaluator()
        )

        self.registry = (
            registry
            or ModelRegistry()
        )

    # ======================================================
    # COLLECT INTERACTION
    # ======================================================

    def collect_interaction(
        self,
        interaction: Dict[str, Any],
    ) -> Dict[str, Any]:

        """
        Check whether an interaction is suitable
        for fine-tuning.

        Eligible interactions are added to the
        training dataset.
        """

        if not isinstance(
            interaction,
            dict,
        ):

            raise TypeError(
                "interaction must be a dictionary."
            )

        # --------------------------------------------------
        # ELIGIBILITY CHECK
        # --------------------------------------------------

        eligibility = (
            self.eligibility_checker.evaluate(
                interaction
            )
        )

        # --------------------------------------------------
        # REJECTED
        # --------------------------------------------------

        if not eligibility.get(
            "eligible",
            False,
        ):

            return {

                "stored": False,

                "eligibility":
                    eligibility,

                "reason":
                    "Interaction was rejected.",

            }

        # --------------------------------------------------
        # ACCEPTED
        # --------------------------------------------------

        dataset_result = (
            self.dataset.add_example(
                interaction
            )
        )

        return {

            "stored":
                dataset_result.get(
                    "success",
                    False,
                ),

            "eligibility":
                eligibility,

            "dataset_result":
                dataset_result,

        }

    # ======================================================
    # CHECK TRAINING STATUS
    # ======================================================

    def check_training_status(
        self,
    ) -> Dict[str, Any]:

        """
        Determine whether fine-tuning should run.

        The scheduler is responsible for:

        - Overnight timing
        - Dataset size
        - Resource availability
        """

        # --------------------------------------------------
        # GET DATASET INFORMATION
        # --------------------------------------------------

        dataset_info = (
            self.dataset.get_info()
        )

        total_examples = (
            dataset_info.get(
                "total_examples",
                0,
            )
        )

        # --------------------------------------------------
        # ASK SCHEDULER
        # --------------------------------------------------

        return (
            self.scheduler.should_train(

                example_count=(
                    total_examples
                )

            )
        )

    # ======================================================
    # RUN TRAINING LIFECYCLE
    # ======================================================

    def run_training(
        self,
        base_model: str,
        task_type: str,
        evaluation_dataset: Any,
    ) -> Dict[str, Any]:

        """
        Run the complete fine-tuning lifecycle.

        This method:

        1. Checks scheduler
        2. Creates training job
        3. Runs trainer
        4. Evaluates candidate
        5. Registers approved model
        """

        # --------------------------------------------------
        # SCHEDULER CHECK
        # --------------------------------------------------

        schedule_result = (
            self.check_training_status()
        )

        if not schedule_result.get(
            "should_train",
            False,
        ):

            return {

                "success": False,

                "status":
                    "deferred",

                "reason":
                    schedule_result.get(
                        "reason",
                        "Training is not scheduled."
                    ),

                "scheduler":
                    schedule_result,

            }

        # --------------------------------------------------
        # DATASET INFORMATION
        # --------------------------------------------------

        dataset_info = (
            self.dataset.get_info()
        )

        dataset_version = (
            dataset_info.get(
                "dataset_version"
            )
        )

        dataset_path = (
            dataset_info.get(
                "storage_path"
            )
        )

        # --------------------------------------------------
        # CREATE TRAINING JOB
        # --------------------------------------------------

        job = (
            self.trainer.create_job(

                base_model=base_model,

                task_type=task_type,

                dataset_version=(
                    dataset_version
                ),

                dataset_path=(
                    dataset_path
                ),

            )
        )

        # --------------------------------------------------
        # TRAIN MODEL
        # --------------------------------------------------

        training_result = (
            self.trainer.train(
                job
            )
        )

        # --------------------------------------------------
        # TRAINING FAILED
        # --------------------------------------------------

        if not training_result.get(
            "success",
            False,
        ):

            return {

                "success": False,

                "status":
                    "training_failed",

                "training":
                    training_result,

                "job":
                    job,

            }

        # --------------------------------------------------
        # GET MODEL ARTIFACT
        # --------------------------------------------------

        artifact = (
            training_result.get(
                "artifact"
            )
        )

        # --------------------------------------------------
        # EVALUATION
        # --------------------------------------------------

        base_model_data = {

            "model_name":
                base_model,

        }

        evaluation_result = (
            self.evaluator.evaluate_candidate(

                base_model=(
                    base_model_data
                ),

                candidate_model=(
                    artifact
                ),

                evaluation_dataset=(
                    evaluation_dataset
                ),

            )
        )

        # --------------------------------------------------
        # REJECTED
        # --------------------------------------------------

        if not evaluation_result.get(
            "accepted",
            False,
        ):

            return {

                "success": False,

                "status":
                    "rejected",

                "artifact":
                    artifact,

                "evaluation":
                    evaluation_result,

            }

        # --------------------------------------------------
        # REGISTER APPROVED MODEL
        # --------------------------------------------------

        registration_result = (
            self.registry.register_model(

                artifact=artifact,

                evaluation=(
                    evaluation_result
                ),

            )
        )

        # --------------------------------------------------
        # REGISTRATION FAILED
        # --------------------------------------------------

        if not registration_result.get(
            "success",
            False,
        ):

            return {

                "success": False,

                "status":
                    "registration_failed",

                "artifact":
                    artifact,

                "evaluation":
                    evaluation_result,

                "registration":
                    registration_result,

            }

        # --------------------------------------------------
        # SUCCESS
        # --------------------------------------------------

        return {

            "success": True,

            "status":
                "approved",

            "job":
                job,

            "artifact":
                artifact,

            "evaluation":
                evaluation_result,

            "registration":
                registration_result,

        }


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNING MANAGER TEST"
    )

    print("=" * 60)

    # ------------------------------------------------------
    # CREATE MANAGER
    # ------------------------------------------------------

    manager = FineTuningManager()

    # ------------------------------------------------------
    # TEST INTERACTION
    # ------------------------------------------------------

    interaction = {

        "task":
            "Calculate pump efficiency",

        "task_type":
            "engineering",

        "input":
            (
                "Input power is 10 kW "
                "and useful power is 8 kW."
            ),

        "initial_response":
            "Pump efficiency is 80%.",

        "peer_review": {

            "verdict":
                "PASS",

            "feedback":
                "",

        },

        "human_feedback":
            "",

        "final_response":
            (
                "Pump efficiency = "
                "8 / 10 = 0.8 = 80%."
            ),

        "quality":
            "accepted",

        "source_model":
            "qwen3:4b",

    }

    # ------------------------------------------------------
    # COLLECT INTERACTION
    # ------------------------------------------------------

    print()

    print(
        "COLLECTING INTERACTION"
    )

    print("-" * 60)

    result = (
        manager.collect_interaction(
            interaction
        )
    )

    print(result)

    # ------------------------------------------------------
    # DATASET STATUS
    # ------------------------------------------------------

    print()

    print(
        "DATASET STATUS"
    )

    print("-" * 60)

    print(
        manager.dataset.get_info()
    )

    # ------------------------------------------------------
    # TRAINING STATUS
    # ------------------------------------------------------

    print()

    print(
        "TRAINING STATUS"
    )

    print("-" * 60)

    print(
        manager.check_training_status()
    )

    print()

    print("=" * 60)

    print(
        "MANAGER TEST COMPLETE"
    )

    print("=" * 60)