"""
V.A.U.L.T. Fine-Tuning Pipeline

Coordinates the complete fine-tuning lifecycle.

Pipeline:

    Training Examples
            ↓
    Fine-Tuning Scheduler
            ↓
    Training Decision
            ↓
    Fine-Tuning Trainer
            ↓
    Candidate Model
            ↓
    Fine-Tuning Evaluator
            ↓
    Model Registry
            ↓
    Fine-Tuning Deployer
            ↓
    Runtime Ready
"""


from datetime import datetime
from typing import Any, Dict, Optional


from models.fine_tuning.scheduler import (
    FineTuningScheduler,
)

from models.fine_tuning.trainer import (
    FineTuningTrainer,
)

from models.fine_tuning.evaluator import (
    FineTuningEvaluator,
)

from models.fine_tuning.registry import (
    ModelRegistry,
)

from models.fine_tuning.deployer import (
    FineTuningDeployer,
)


# ==========================================================
# FINE-TUNING PIPELINE
# ==========================================================

class FineTuningPipeline:

    """
    Coordinate the complete V.A.U.L.T.
    fine-tuning lifecycle.

    Stages:

        1. Scheduler check
        2. Create training job
        3. Train candidate model
        4. Evaluate candidate
        5. Register approved model
        6. Deploy approved model

    A failed or rejected model can never reach
    the deployment stage.
    """

    def __init__(
        self,
        scheduler: Optional[
            FineTuningScheduler
        ] = None,
        trainer: Optional[
            FineTuningTrainer
        ] = None,
        evaluator: Optional[
            FineTuningEvaluator
        ] = None,
        registry: Optional[
            ModelRegistry
        ] = None,
        deployer: Optional[
            FineTuningDeployer
        ] = None,
    ):

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

        self.deployer = (
            deployer
            or FineTuningDeployer()
        )

    # ======================================================
    # MAIN PIPELINE
    # ======================================================

    def run(
        self,
        example_count: int,
        base_model: str,
        task_type: str,
        dataset_version: Any,
        dataset_path: str,
        evaluation_dataset: Any,
        current_time: Optional[
            datetime
        ] = None,
        force: bool = False,
    ) -> Dict[str, Any]:

        """
        Run the complete fine-tuning pipeline.

        Parameters:

            example_count:
                Number of available training examples.

            base_model:
                Base model selected for fine-tuning.

            task_type:
                Training task category.

            dataset_version:
                Version identifier for the dataset.

            dataset_path:
                Location of the training dataset.

            evaluation_dataset:
                Dataset used to evaluate the candidate.

            current_time:
                Optional time override for testing.

            force:
                Explicit development override.

                When True, bypasses the overnight
                scheduling restriction.

                Dataset and resource safety checks
                remain active.
        """

        pipeline_started_at = (
            datetime.now()
            .isoformat()
        )

        # ==================================================
        # STAGE 1
        # SCHEDULER
        # ==================================================

        scheduling_result = (
            self.scheduler.should_train(
                example_count=example_count,
                current_time=current_time,
                force=force,
            )
        )

        if not scheduling_result.get(
            "should_train",
            False,
        ):

            return {

                "success": False,

                "stage":
                    "scheduler",

                "reason":
                    scheduling_result.get(
                        "reason"
                    ),

                "started_at":
                    pipeline_started_at,

                "completed_at":
                    datetime.now()
                    .isoformat(),

                "force":
                    force,

                "scheduling":
                    scheduling_result,

            }

        # ==================================================
        # STAGE 2
        # CREATE TRAINING JOB
        # ==================================================

        try:

            training_job = (
                self.trainer.create_job(
                    base_model=base_model,
                    task_type=task_type,
                    dataset_version=dataset_version,
                    dataset_path=dataset_path,
                )
            )

        except Exception as exc:

            return {

                "success": False,

                "stage":
                    "job_creation",

                "reason":
                    str(exc),

                "started_at":
                    pipeline_started_at,

                "completed_at":
                    datetime.now()
                    .isoformat(),

                "force":
                    force,

                "scheduling":
                    scheduling_result,

            }

        # ==================================================
        # VALIDATE TRAINING JOB
        # ==================================================

        if not isinstance(
            training_job,
            dict,
        ):

            return {

                "success": False,

                "stage":
                    "job_creation",

                "reason":
                    (
                        "Trainer returned an invalid "
                        "training job."
                    ),

                "started_at":
                    pipeline_started_at,

                "completed_at":
                    datetime.now()
                    .isoformat(),

                "force":
                    force,

                "scheduling":
                    scheduling_result,

                "job":
                    training_job,

            }

        # ==================================================
        # STAGE 3
        # TRAIN MODEL
        # ==================================================

        try:

            training_result = (
                self.trainer.train(
                    training_job
                )
            )

        except Exception as exc:

            return {

                "success": False,

                "stage":
                    "training",

                "reason":
                    str(exc),

                "started_at":
                    pipeline_started_at,

                "completed_at":
                    datetime.now()
                    .isoformat(),

                "force":
                    force,

                "scheduling":
                    scheduling_result,

                "job":
                    training_job,

            }

        # ==================================================
        # VALIDATE TRAINING RESULT
        # ==================================================

        if not isinstance(
            training_result,
            dict,
        ):

            return {

                "success": False,

                "stage":
                    "training",

                "reason":
                    (
                        "Trainer returned an invalid "
                        "training result."
                    ),

                "started_at":
                    pipeline_started_at,

                "completed_at":
                    datetime.now()
                    .isoformat(),

                "force":
                    force,

                "scheduling":
                    scheduling_result,

                "job":
                    training_job,

                "training":
                    training_result,

            }

        # ==================================================
        # TRAINING FAILED
        # ==================================================

        if not training_result.get(
            "success",
            False,
        ):

            return {

                "success": False,

                "stage":
                    "training",

                "reason":
                    training_result.get(
                        "error"
                    )
                    or
                    training_result.get(
                        "reason"
                    )
                    or
                    "Training failed.",

                "started_at":
                    pipeline_started_at,

                "completed_at":
                    datetime.now()
                    .isoformat(),

                "force":
                    force,

                "scheduling":
                    scheduling_result,

                "job":
                    training_job,

                "training":
                    training_result,

            }

        # ==================================================
        # GET TRAINED ARTIFACT
        # ==================================================

        artifact = (
            training_result.get(
                "artifact"
            )
        )

        if not isinstance(
            artifact,
            dict,
        ):

            return {

                "success": False,

                "stage":
                    "training",

                "reason":
                    (
                        "Training completed but "
                        "no valid model artifact "
                        "was returned."
                    ),

                "started_at":
                    pipeline_started_at,

                "completed_at":
                    datetime.now()
                    .isoformat(),

                "force":
                    force,

                "scheduling":
                    scheduling_result,

                "job":
                    training_job,

                "training":
                    training_result,

            }

        # ==================================================
        # STAGE 4
        # PREPARE BASE MODEL
        # ==================================================

        base_model_info = {

            "model_name":
                base_model,

        }

        # ==================================================
        # STAGE 5
        # EVALUATE CANDIDATE
        # ==================================================

        try:

            evaluation_result = (
                self.evaluator.evaluate_candidate(
                    base_model=base_model_info,
                    candidate_model=artifact,
                    evaluation_dataset=(
                        evaluation_dataset
                    ),
                )
            )

        except Exception as exc:

            return {

                "success": False,

                "stage":
                    "evaluation",

                "reason":
                    str(exc),

                "started_at":
                    pipeline_started_at,

                "completed_at":
                    datetime.now()
                    .isoformat(),

                "force":
                    force,

                "scheduling":
                    scheduling_result,

                "job":
                    training_job,

                "training":
                    training_result,

                "artifact":
                    artifact,

            }

        # ==================================================
        # VALIDATE EVALUATION RESULT
        # ==================================================

        if not isinstance(
            evaluation_result,
            dict,
        ):

            return {

                "success": False,

                "stage":
                    "evaluation",

                "reason":
                    (
                        "Evaluator returned an invalid "
                        "evaluation result."
                    ),

                "started_at":
                    pipeline_started_at,

                "completed_at":
                    datetime.now()
                    .isoformat(),

                "force":
                    force,

                "artifact":
                    artifact,

                "evaluation":
                    evaluation_result,

            }

        # ==================================================
        # REJECTED MODEL
        # ==================================================

        if not evaluation_result.get(
            "accepted",
            False,
        ):

            return {

                "success": False,

                "stage":
                    "evaluation",

                "reason":
                    evaluation_result.get(
                        "reason"
                    )
                    or
                    "Candidate model was rejected.",

                "started_at":
                    pipeline_started_at,

                "completed_at":
                    datetime.now()
                    .isoformat(),

                "force":
                    force,

                "scheduling":
                    scheduling_result,

                "job":
                    training_job,

                "training":
                    training_result,

                "artifact":
                    artifact,

                "evaluation":
                    evaluation_result,

            }

        # ==================================================
        # STAGE 6
        # REGISTER MODEL
        # ==================================================

        try:

            registry_result = (
                self.registry.register_model(
                    artifact=artifact,
                    evaluation=(
                        evaluation_result
                    ),
                )
            )

        except Exception as exc:

            return {

                "success": False,

                "stage":
                    "registry",

                "reason":
                    str(exc),

                "started_at":
                    pipeline_started_at,

                "completed_at":
                    datetime.now()
                    .isoformat(),

                "force":
                    force,

                "artifact":
                    artifact,

                "evaluation":
                    evaluation_result,

            }

        # ==================================================
        # VALIDATE REGISTRY RESULT
        # ==================================================

        if not isinstance(
            registry_result,
            dict,
        ):

            return {

                "success": False,

                "stage":
                    "registry",

                "reason":
                    (
                        "Model registry returned an "
                        "invalid result."
                    ),

                "started_at":
                    pipeline_started_at,

                "completed_at":
                    datetime.now()
                    .isoformat(),

                "force":
                    force,

                "artifact":
                    artifact,

                "evaluation":
                    evaluation_result,

                "registry":
                    registry_result,

            }

        # ==================================================
        # REGISTRATION FAILED
        # ==================================================

        if not registry_result.get(
            "registered",
            False,
        ):

            return {

                "success": False,

                "stage":
                    "registry",

                "reason":
                    registry_result.get(
                        "reason"
                    )
                    or
                    "Model registration failed.",

                "started_at":
                    pipeline_started_at,

                "completed_at":
                    datetime.now()
                    .isoformat(),

                "force":
                    force,

                "artifact":
                    artifact,

                "evaluation":
                    evaluation_result,

                "registry":
                    registry_result,

            }

        # ==================================================
        # STAGE 7
        # DEPLOY MODEL
        # ==================================================

        try:

            deployment_result = (
                self.deployer.deploy(
                    artifact=artifact,
                    evaluation=(
                        evaluation_result
                    ),
                )
            )

        except Exception as exc:

            return {

                "success": False,

                "stage":
                    "deployment",

                "reason":
                    str(exc),

                "started_at":
                    pipeline_started_at,

                "completed_at":
                    datetime.now()
                    .isoformat(),

                "force":
                    force,

                "artifact":
                    artifact,

                "evaluation":
                    evaluation_result,

                "registry":
                    registry_result,

            }

        # ==================================================
        # VALIDATE DEPLOYMENT RESULT
        # ==================================================

        if not isinstance(
            deployment_result,
            dict,
        ):

            return {

                "success": False,

                "stage":
                    "deployment",

                "reason":
                    (
                        "Model deployer returned an "
                        "invalid result."
                    ),

                "started_at":
                    pipeline_started_at,

                "completed_at":
                    datetime.now()
                    .isoformat(),

                "force":
                    force,

                "artifact":
                    artifact,

                "evaluation":
                    evaluation_result,

                "registry":
                    registry_result,

                "deployment":
                    deployment_result,

            }

        # ==================================================
        # DEPLOYMENT FAILED
        # ==================================================

        if not deployment_result.get(
            "deployed",
            False,
        ):

            return {

                "success": False,

                "stage":
                    "deployment",

                "reason":
                    deployment_result.get(
                        "reason"
                    )
                    or
                    "Model deployment failed.",

                "started_at":
                    pipeline_started_at,

                "completed_at":
                    datetime.now()
                    .isoformat(),

                "force":
                    force,

                "artifact":
                    artifact,

                "evaluation":
                    evaluation_result,

                "registry":
                    registry_result,

                "deployment":
                    deployment_result,

            }

        # ==================================================
        # PIPELINE SUCCESS
        # ==================================================

        return {

            "success": True,

            "stage":
                "deployment_complete",

            "reason":
                (
                    "Fine-tuning pipeline "
                    "completed successfully."
                ),

            "started_at":
                pipeline_started_at,

            "completed_at":
                datetime.now()
                .isoformat(),

            "force":
                force,

            "model_name":
                artifact.get(
                    "model_name"
                ),

            "task_type":
                task_type,

            "scheduling":
                scheduling_result,

            "job":
                training_job,

            "training":
                training_result,

            "artifact":
                artifact,

            "evaluation":
                evaluation_result,

            "registry":
                registry_result,

            "deployment":
                deployment_result,

        }


# ==========================================================
# PIPELINE TEST EVALUATION BACKEND
# ==========================================================

class PipelineTestEvaluationBackend:

    """
    Test evaluation backend.

    Gives the base model a score of 0.80 and
    the candidate model a score of 0.90.

    This allows the complete pipeline to be tested.
    """

    def evaluate(
        self,
        model: Dict[str, Any],
        evaluation_dataset: Any,
    ) -> Dict[str, Any]:

        model_name = model.get(
            "model_name",
            "",
        )

        if model_name == "qwen3:4b":

            score = 0.80

        else:

            score = 0.90

        return {

            "success": True,

            "model_name":
                model_name,

            "score":
                score,

            "evaluation_dataset":
                evaluation_dataset,

        }


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNING PIPELINE TEST"
    )

    print("=" * 60)

    # ======================================================
    # IMPORT TEST COMPONENTS
    # ======================================================

    from models.fine_tuning.scheduler import (
        MockPerformanceManager,
    )

    # ======================================================
    # CREATE SCHEDULER
    # ======================================================

    scheduler = (

        FineTuningScheduler(

            performance_manager=(

                MockPerformanceManager(
                    can_run=True
                )

            ),

            minimum_examples=10,

        )

    )

    # ======================================================
    # CREATE EVALUATOR
    # ======================================================

    evaluator = (

        FineTuningEvaluator(

            backend=(

                PipelineTestEvaluationBackend()

            )

        )

    )

    # ======================================================
    # CREATE PIPELINE
    # ======================================================

    pipeline = (

        FineTuningPipeline(

            scheduler=scheduler,

            evaluator=evaluator,

        )

    )

    # ======================================================
    # TEST 1
    # SUCCESSFUL PIPELINE
    # ======================================================

    print()

    print(
        "TEST 1: SUCCESSFUL PIPELINE"
    )

    print("-" * 60)

    result = (

        pipeline.run(

            example_count=20,

            base_model="qwen3:4b",

            task_type="engineering",

            dataset_version=1,

            dataset_path=(
                "data/fine_tuning"
            ),

            evaluation_dataset=(
                "data/evaluation"
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

    print(result)

    # ======================================================
    # TEST 2
    # NOT ENOUGH EXAMPLES
    # ======================================================

    print()

    print(
        "TEST 2: NOT ENOUGH TRAINING EXAMPLES"
    )

    print("-" * 60)

    result = (

        pipeline.run(

            example_count=5,

            base_model="qwen3:4b",

            task_type="engineering",

            dataset_version=1,

            dataset_path=(
                "data/fine_tuning"
            ),

            evaluation_dataset=(
                "data/evaluation"
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

    print(result)

    # ======================================================
    # TEST 3
    # OUTSIDE TRAINING WINDOW
    # ======================================================

    print()

    print(
        "TEST 3: DAYTIME TRAINING"
    )

    print("-" * 60)

    result = (

        pipeline.run(

            example_count=20,

            base_model="qwen3:4b",

            task_type="engineering",

            dataset_version=1,

            dataset_path=(
                "data/fine_tuning"
            ),

            evaluation_dataset=(
                "data/evaluation"
            ),

            current_time=datetime(
                2026,
                9,
                7,
                14,
                0,
            ),

        )

    )

    print(result)

    # ======================================================
    # TEST 4
    # FORCED DEVELOPMENT PIPELINE
    # ======================================================

    print()

    print(
        "TEST 4: FORCED DEVELOPMENT PIPELINE"
    )

    print("-" * 60)

    result = (

        pipeline.run(

            example_count=20,

            base_model="qwen3:4b",

            task_type="engineering",

            dataset_version=1,

            dataset_path=(
                "data/fine_tuning"
            ),

            evaluation_dataset=(
                "data/evaluation"
            ),

            current_time=datetime(
                2026,
                9,
                7,
                14,
                0,
            ),

            force=True,

        )

    )

    print(result)

    print()

    print("=" * 60)

    print(
        "FINE-TUNING PIPELINE TEST COMPLETE"
    )

    print("=" * 60)