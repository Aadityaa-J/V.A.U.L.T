"""
V.A.U.L.T. Fine-Tuning Pipeline Integration Test

Tests the complete fine-tuning lifecycle:

Interaction
    ↓
Eligibility Check
    ↓
Dataset Storage
    ↓
Scheduler
    ↓
Training
    ↓
Evaluation
    ↓
Model Registry
"""

from datetime import datetime

from models.fine_tuning.manager import FineTuningManager
from models.fine_tuning.scheduler import (
    FineTuningScheduler,
    MockPerformanceManager,
)
from models.fine_tuning.trainer import (
    FineTuningTrainer,
    MockTrainer,
)
from models.fine_tuning.evaluator import (
    FineTuningEvaluator,
    MockEvaluationBackend,
)
from models.fine_tuning.registry import ModelRegistry
from models.fine_tuning.dataset import FineTuningDataset
from models.fine_tuning.eligibility import EligibilityChecker


# ==========================================================
# TEST CONFIGURATION
# ==========================================================

TEST_DATASET_PATH = "data/test_fine_tuning_pipeline"

TEST_REGISTRY_PATH = (
    "data/test_fine_tuning_pipeline_registry"
)


# ==========================================================
# CREATE PIPELINE
# ==========================================================

def create_test_manager():

    """
    Create a FineTuningManager configured for
    integration testing.
    """

    # ------------------------------------------------------
    # DATASET
    # ------------------------------------------------------

    dataset = FineTuningDataset(
        storage_path=TEST_DATASET_PATH
    )

    # ------------------------------------------------------
    # ELIGIBILITY
    # ------------------------------------------------------

    eligibility_checker = (
        EligibilityChecker()
    )

    # ------------------------------------------------------
    # SCHEDULER
    # ------------------------------------------------------
    #
    # minimum_examples = 1 allows testing
    # without collecting many examples.
    # ------------------------------------------------------

    scheduler = FineTuningScheduler(

        performance_manager=(

            MockPerformanceManager(
                can_run=True
            )

        ),

        minimum_examples=1,

    )

    # ------------------------------------------------------
    # TRAINER
    # ------------------------------------------------------

    trainer = FineTuningTrainer(

        backend=MockTrainer()

    )

    # ------------------------------------------------------
    # EVALUATOR
    # ------------------------------------------------------

    backend = MockEvaluationBackend(

        scores={

            "qwen3:4b":
                0.80,

        }

    )

    evaluator = FineTuningEvaluator(

        backend=backend

    )

    # ------------------------------------------------------
    # REGISTRY
    # ------------------------------------------------------

    registry = ModelRegistry(

        storage_path=(
            TEST_REGISTRY_PATH
        )

    )

    # ------------------------------------------------------
    # MANAGER
    # ------------------------------------------------------

    manager = FineTuningManager(

        dataset=dataset,

        eligibility_checker=(
            eligibility_checker
        ),

        scheduler=scheduler,

        trainer=trainer,

        evaluator=evaluator,

        registry=registry,

    )

    return manager


# ==========================================================
# ADD TEST INTERACTIONS
# ==========================================================

def add_test_interactions(
    manager,
):

    """
    Add multiple high-quality interactions
    to the fine-tuning dataset.
    """

    interactions = [

        {

            "task":
                "Calculate pump efficiency",

            "task_type":
                "engineering",

            "input":
                (
                    "Input power is 10 kW "
                    "and useful output power "
                    "is 8 kW."
                ),

            "initial_response":
                (
                    "Pump efficiency is 80%."
                ),

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
                    "Efficiency = output power "
                    "/ input power = 8 / 10 "
                    "= 0.8 = 80%."
                ),

            "quality":
                "accepted",

            "source_model":
                "qwen3:4b",

        },

        {

            "task":
                "Calculate electrical power",

            "task_type":
                "engineering",

            "input":
                (
                    "Voltage is 12 V and "
                    "current is 5 A."
                ),

            "initial_response":
                (
                    "Power is 60 watts."
                ),

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
                    "Electrical power is "
                    "P = V × I = 12 × 5 "
                    "= 60 W."
                ),

            "quality":
                "accepted",

            "source_model":
                "qwen3:4b",

        },

    ]

    results = []

    for interaction in interactions:

        result = (

            manager.collect_interaction(
                interaction
            )

        )

        results.append(
            result
        )

    return results


# ==========================================================
# TEST PIPELINE
# ==========================================================

def run_pipeline_test():

    """
    Run the complete V.A.U.L.T.
    fine-tuning integration test.
    """

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNING PIPELINE TEST"
    )

    print("=" * 60)

    # ------------------------------------------------------
    # CREATE MANAGER
    # ------------------------------------------------------

    print()

    print(
        "INITIALIZING PIPELINE"
    )

    print("-" * 60)

    manager = create_test_manager()

    print(
        "Pipeline initialized."
    )

    # ------------------------------------------------------
    # ADD INTERACTIONS
    # ------------------------------------------------------

    print()

    print(
        "ADDING TRAINING INTERACTIONS"
    )

    print("-" * 60)

    results = (

        add_test_interactions(
            manager
        )

    )

    for index, result in enumerate(
        results,
        start=1,
    ):

        print()

        print(
            f"Interaction {index}:"
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

    dataset_info = (

        manager.dataset.get_info()

    )

    print(
        dataset_info
    )

    # ------------------------------------------------------
    # SCHEDULER TEST
    # ------------------------------------------------------

    print()

    print(
        "SCHEDULER TEST"
    )

    print("-" * 60)

    total_examples = (

        dataset_info.get(
            "total_examples",
            0,
        )

    )

    # Use an overnight test time.

    schedule_result = (

        manager.scheduler.should_train(

            example_count=(
                total_examples
            ),

            current_time=datetime(
                2026,
                9,
                7,
                2,
                0,
            ),

        )

    )

    print(
        schedule_result
    )

    # ------------------------------------------------------
    # CHECK SCHEDULER
    # ------------------------------------------------------

    if not schedule_result.get(
        "should_train",
        False,
    ):

        print()

        print(
            "PIPELINE STOPPED"
        )

        print(
            "Scheduler did not approve training."
        )

        return

    # ------------------------------------------------------
    # CREATE TRAINING JOB
    # ------------------------------------------------------

    print()

    print(
        "CREATING TRAINING JOB"
    )

    print("-" * 60)

    job = (

        manager.trainer.create_job(

            base_model=(
                "qwen3:4b"
            ),

            task_type=(
                "engineering"
            ),

            dataset_version=(

                dataset_info.get(
                    "dataset_version"
                )

            ),

            dataset_path=(

                dataset_info.get(
                    "storage_path"
                )

            ),

        )

    )

    print(
        job
    )

    # ------------------------------------------------------
    # RUN TRAINING
    # ------------------------------------------------------

    print()

    print(
        "RUNNING TRAINING"
    )

    print("-" * 60)

    training_result = (

        manager.trainer.train(
            job
        )

    )

    print(
        training_result
    )

    # ------------------------------------------------------
    # CHECK TRAINING RESULT
    # ------------------------------------------------------

    if not training_result.get(
        "success",
        False,
    ):

        print()

        print(
            "PIPELINE FAILED"
        )

        print(
            "Training failed."
        )

        return

    artifact = (

        training_result.get(
            "artifact"
        )

    )

    # ------------------------------------------------------
    # CONFIGURE CANDIDATE SCORE
    # ------------------------------------------------------

    print()

    print(
        "CONFIGURING EVALUATION"
    )

    print("-" * 60)

    candidate_model_name = (

        artifact.get(
            "model_name"
        )

    )

    # The mock backend needs a score
    # for the dynamically generated model.

    evaluator_backend = (

        manager.evaluator.backend
    )

    evaluator_backend.scores[
        candidate_model_name
    ] = 0.90

    print(
        f"Base Model Score: "
        f"0.80"
    )

    print(
        f"Candidate Model Score: "
        f"0.90"
    )

    # ------------------------------------------------------
    # EVALUATE MODEL
    # ------------------------------------------------------

    print()

    print(
        "EVALUATING MODEL"
    )

    print("-" * 60)

    evaluation_result = (

        manager.evaluator.evaluate_candidate(

            base_model={

                "model_name":
                    "qwen3:4b",

            },

            candidate_model=(
                artifact
            ),

            evaluation_dataset=(

                "data/test_evaluation"

            ),

        )

    )

    print(
        evaluation_result
    )

    # ------------------------------------------------------
    # CHECK EVALUATION
    # ------------------------------------------------------

    if not evaluation_result.get(
        "accepted",
        False,
    ):

        print()

        print(
            "PIPELINE STOPPED"
        )

        print(
            "Candidate model was rejected."
        )

        return

    # ------------------------------------------------------
    # REGISTER MODEL
    # ------------------------------------------------------

    print()

    print(
        "REGISTERING APPROVED MODEL"
    )

    print("-" * 60)

    registration_result = (

        manager.registry.register_model(

            artifact=artifact,

            evaluation=(
                evaluation_result
            ),

        )

    )

    print(
        registration_result
    )

    # ------------------------------------------------------
    # FINAL RESULT
    # ------------------------------------------------------

    print()

    print("=" * 60)

    print(
        "PIPELINE RESULT"
    )

    print("=" * 60)

    if registration_result.get(
        "success",
        False,
    ):

        print()

        print(
            "SUCCESS!"
        )

        print()

        print(
            "Fine-tuning lifecycle completed:"
        )

        print()

        print(
            "Interaction"
        )

        print(
            "    ↓"
        )

        print(
            "Eligibility Check"
        )

        print(
            "    ↓"
        )

        print(
            "Dataset Storage"
        )

        print(
            "    ↓"
        )

        print(
            "Scheduler"
        )

        print(
            "    ↓"
        )

        print(
            "Training"
        )

        print(
            "    ↓"
        )

        print(
            "Evaluation"
        )

        print(
            "    ↓"
        )

        print(
            "Model Registry"
        )

        print()

        print(
            f"Approved Model: "
            f"{artifact.get('model_name')}"
        )

    else:

        print()

        print(
            "PIPELINE FAILED"
        )

        print(
            registration_result
        )

    print()

    print("=" * 60)

    print(
        "FINE-TUNING PIPELINE TEST COMPLETE"
    )

    print("=" * 60)


# ==========================================================
# RUN TEST
# ==========================================================

if __name__ == "__main__":

    run_pipeline_test()