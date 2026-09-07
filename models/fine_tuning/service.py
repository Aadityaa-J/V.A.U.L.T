"""
V.A.U.L.T. Fine-Tuning Service

Central service layer for the V.A.U.L.T.
automatic fine-tuning system.

Responsibilities:

    - Receive training examples
    - Store training examples persistently
    - Check fine-tuning eligibility
    - Ask the controller whether training should run
    - Run the fine-tuning pipeline safely
    - Track service status
    - Provide runtime model information

IMPORTANT:

Fine-tuning failures must NEVER crash the main
V.A.U.L.T. assistant.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


from models.fine_tuning.controller import (
    FineTuningController,
)

from models.fine_tuning.manager import (
    FineTuningManager,
)

from models.fine_tuning.pipeline_manager import (
    FineTuningPipelineManager,
)

from models.fine_tuning.runtime_router import (
    FineTuningRuntimeRouter,
)


# ==========================================================
# FINE-TUNING SERVICE
# ==========================================================

class FineTuningService:

    """
    Central service interface for the V.A.U.L.T.
    automatic fine-tuning system.

    The service is designed to be safely called
    from the main V.A.U.L.T. runtime.

    Fine-tuning failures must never crash the
    main assistant.
    """

    def __init__(
        self,
        controller: Optional[
            FineTuningController
        ] = None,
        manager: Optional[
            FineTuningManager
        ] = None,
        pipeline_manager: Optional[
            FineTuningPipelineManager
        ] = None,
        runtime_router: Optional[
            FineTuningRuntimeRouter
        ] = None,
    ):

        # --------------------------------------------------
        # CORE COMPONENTS
        # --------------------------------------------------

        self.controller = (
            controller
            or FineTuningController()
        )

        self.manager = (
            manager
            or FineTuningManager()
        )

        self.pipeline_manager = (
            pipeline_manager
            or FineTuningPipelineManager()
        )

        self.runtime_router = (
            runtime_router
            or FineTuningRuntimeRouter()
        )

        # --------------------------------------------------
        # SERVICE STATISTICS
        # --------------------------------------------------

        self.total_examples_received = 0
        self.total_examples_stored = 0
        self.total_pipeline_checks = 0
        self.total_pipeline_runs = 0
        self.total_pipeline_successes = 0
        self.total_errors = 0

        # --------------------------------------------------
        # SERVICE STATE
        # --------------------------------------------------

        self.last_pipeline_result: Optional[
            Dict[str, Any]
        ] = None

        self.last_error: Optional[
            str
        ] = None

        self.started_at = (
            datetime.now()
            .isoformat()
        )


    # ======================================================
    # ADD TRAINING EXAMPLE
    # ======================================================

    def add_training_example(
        self,
        prompt: str,
        response: str,
        task_type: str = "general",
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:

        """
        Add a completed V.A.U.L.T. interaction
        as a persistent training example.
        """

        self.total_examples_received += 1

        # --------------------------------------------------
        # VALIDATE INPUT
        # --------------------------------------------------

        if not isinstance(
            prompt,
            str,
        ):

            return {

                "success": False,
                "stored": False,

                "reason":
                    "Prompt must be a string.",

            }

        if not isinstance(
            response,
            str,
        ):

            return {

                "success": False,
                "stored": False,

                "reason":
                    "Response must be a string.",

            }

        if not isinstance(
            task_type,
            str,
        ):

            return {

                "success": False,
                "stored": False,

                "reason":
                    "Task type must be a string.",

            }

        # --------------------------------------------------
        # NORMALIZE VALUES
        # --------------------------------------------------

        prompt = (
            prompt.strip()
        )

        response = (
            response.strip()
        )

        task_type = (
            task_type.strip()
            .lower()
        )

        if not prompt:

            return {

                "success": False,
                "stored": False,

                "reason":
                    "Prompt cannot be empty.",

            }

        if not response:

            return {

                "success": False,
                "stored": False,

                "reason":
                    "Response cannot be empty.",

            }

        if not task_type:

            task_type = "general"

        # --------------------------------------------------
        # BUILD METADATA
        # --------------------------------------------------

        example_metadata = {

            "source":
                "fine_tuning_service",

            "created_at":
                datetime.now()
                .isoformat(),

        }

        if isinstance(
            metadata,
            dict,
        ):

            example_metadata.update(
                metadata
            )

        # --------------------------------------------------
        # STORE THROUGH PIPELINE MANAGER
        # --------------------------------------------------

        try:

            storage_result = (

                self.pipeline_manager
                .add_example(

                    prompt=prompt,

                    response=response,

                    task_type=task_type,

                    metadata=(
                        example_metadata
                    ),

                )

            )

        except Exception as exc:

            self.total_errors += 1

            self.last_error = (
                str(exc)
            )

            return {

                "success": False,
                "stored": False,

                "reason":
                    str(exc),

                "task_type":
                    task_type,

            }

        # --------------------------------------------------
        # CHECK STORAGE RESULT
        # --------------------------------------------------

        stored = False

        if isinstance(
            storage_result,
            dict,
        ):

            stored = bool(

                storage_result.get(
                    "stored",

                    storage_result.get(
                        "success",
                        False,
                    ),

                )

            )

        else:

            stored = True

        if stored:

            self.total_examples_stored += 1

        return {

            "success":
                stored,

            "stored":
                stored,

            "task_type":
                task_type,

            "storage":
                storage_result,

            "total_examples_received":
                self.total_examples_received,

            "total_examples_stored":
                self.total_examples_stored,

        }


    # ======================================================
    # GET EXAMPLE COUNT
    # ======================================================

    def get_example_count(
        self,
        task_type: Optional[
            str
        ] = None,
    ) -> int:

        """
        Return the number of persistent
        training examples.
        """

        try:

            return (

                self.pipeline_manager
                .get_example_count(

                    task_type=task_type

                )

            )

        except Exception as exc:

            self.last_error = (
                str(exc)
            )

            return 0


    # ======================================================
    # GET TRAINING EXAMPLES
    # ======================================================

    def get_training_examples(
        self,
    ) -> List[Dict[str, Any]]:

        """
        Return all available training examples.

        Supports multiple PipelineManager APIs:

            1. get_training_examples()
            2. get_examples()
            3. dataset.get_examples()
            4. examples attribute

        This compatibility layer prevents test
        implementations from causing failures.
        """

        try:

            manager = (
                self.pipeline_manager
            )

            # --------------------------------------------------
            # API 1
            # MANAGER.get_training_examples()
            # --------------------------------------------------

            if hasattr(
                manager,
                "get_training_examples",
            ):

                examples = (

                    manager
                    .get_training_examples()

                )

                if isinstance(
                    examples,
                    list,
                ):

                    return examples

            # --------------------------------------------------
            # API 2
            # MANAGER.get_examples()
            # --------------------------------------------------

            if hasattr(
                manager,
                "get_examples",
            ):

                examples = (

                    manager
                    .get_examples()

                )

                if isinstance(
                    examples,
                    list,
                ):

                    return examples

            # --------------------------------------------------
            # API 3
            # MANAGER.dataset
            # --------------------------------------------------

            dataset = getattr(
                manager,
                "dataset",
                None,
            )

            if dataset is not None:

                if hasattr(
                    dataset,
                    "get_examples",
                ):

                    examples = (

                        dataset
                        .get_examples()

                    )

                    if isinstance(
                        examples,
                        list,
                    ):

                        return examples

                # Dataset may itself be a list.

                if isinstance(
                    dataset,
                    list,
                ):

                    return dataset

                # Dataset may expose examples.

                dataset_examples = getattr(
                    dataset,
                    "examples",
                    None,
                )

                if isinstance(
                    dataset_examples,
                    list,
                ):

                    return dataset_examples

            # --------------------------------------------------
            # API 4
            # MANAGER.examples
            #
            # Used by MockPipelineManager.
            # --------------------------------------------------

            examples = getattr(
                manager,
                "examples",
                None,
            )

            if isinstance(
                examples,
                list,
            ):

                return examples

        except Exception as exc:

            self.last_error = (
                str(exc)
            )

        return []


    # ======================================================
    # BUILD DATASET
    # ======================================================

    def build_dataset(
        self,
        task_type: Optional[
            str
        ] = None,
    ) -> List[Dict[str, Any]]:

        """
        Build a simple dataset representation
        from persistent training examples.
        """

        examples = (
            self.get_training_examples()
        )

        dataset = []

        for example in examples:

            if not isinstance(
                example,
                dict,
            ):

                continue

            example_task_type = (

                example.get(
                    "task_type",
                    "general",
                )

            )

            if (

                task_type is not None

                and

                example_task_type
                !=
                task_type

            ):

                continue

            # --------------------------------------------------
            # SUPPORT MULTIPLE DATASET FORMATS
            # --------------------------------------------------

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

                or

                example.get(
                    "output"
                )

            )

            if not isinstance(
                prompt,
                str,
            ):

                continue

            if not isinstance(
                response,
                str,
            ):

                continue

            dataset.append({

                "input":
                    prompt,

                "output":
                    response,

                "task_type":
                    example_task_type,

                "metadata":

                    example.get(
                        "metadata",
                        {},
                    ),

            })

        return dataset


    # ======================================================
    # PIPELINE CHECK
    # ======================================================

    def check_pipeline(
        self,
        task_type: str = "general",
        base_model: Optional[
            str
        ] = None,
        dataset_path: str = (
            "data/fine_tuning"
        ),
        evaluation_dataset: Any = (
            "data/evaluation"
        ),
        dataset_version: int = 1,
        current_time: Optional[
            datetime
        ] = None,
    ) -> Dict[str, Any]:

        """
        Check whether fine-tuning should run.

        This method safely coordinates:

            Controller
                ↓
            Manager
                ↓
            Pipeline Manager
        """

        self.total_pipeline_checks += 1

        # --------------------------------------------------
        # NORMALIZE TASK TYPE
        # --------------------------------------------------

        if not isinstance(
            task_type,
            str,
        ):

            task_type = "general"

        task_type = (

            task_type
            .strip()
            .lower()

        )

        if not task_type:

            task_type = "general"

        # --------------------------------------------------
        # EXAMPLE COUNT
        # --------------------------------------------------

        example_count = (

            self.get_example_count(

                task_type=task_type

            )

        )

        if example_count <= 0:

            return {

                "success": False,

                "pipeline_started": False,

                "reason":

                    (
                        "No training examples "
                        "are available for this "
                        "task type."
                    ),

                "example_count":
                    example_count,

                "task_type":
                    task_type,

            }

        # --------------------------------------------------
        # BUILD DATASET
        # --------------------------------------------------

        dataset = (

            self.build_dataset(

                task_type=task_type

            )

        )

        # --------------------------------------------------
        # DETERMINE BASE MODEL
        # --------------------------------------------------

        if not base_model:

            try:

                model_result = (

                    self.pipeline_manager
                    .select_base_model(

                        task_type=task_type

                    )

                )

                if isinstance(
                    model_result,
                    dict,
                ):

                    base_model = (

                        model_result.get(
                            "model"
                        )

                    )

            except Exception:

                base_model = None

        if not base_model:

            base_model = (
                "qwen3:4b"
            )

        # --------------------------------------------------
        # CONTROLLER CHECK
        # --------------------------------------------------

        try:

            controller_result = (

                self.controller.check(

                    example_count=(
                        example_count
                    ),

                    task_type=(
                        task_type
                    ),

                    base_model=(
                        base_model
                    ),

                    current_time=(
                        current_time
                    ),

                )

            )

        except Exception as exc:

            self.total_errors += 1

            self.last_error = (
                str(exc)
            )

            return {

                "success": False,

                "pipeline_started": False,

                "stage":
                    "controller",

                "reason":
                    str(exc),

                "example_count":
                    example_count,

            }

        # --------------------------------------------------
        # CONTROLLER REJECTED
        # --------------------------------------------------

        if not isinstance(
            controller_result,
            dict,
        ):

            controller_result = {}

        approved = (

            controller_result.get(

                "approved",

                controller_result.get(

                    "should_train",

                    False,

                ),

            )

        )

        if not approved:

            return {

                "success": True,

                "pipeline_started": False,

                "reason":

                    (
                        "Fine-tuning is not "
                        "currently required."
                    ),

                "example_count":
                    example_count,

                "task_type":
                    task_type,

                "controller":
                    controller_result,

            }

        # --------------------------------------------------
        # MANAGER CHECK
        # --------------------------------------------------

        try:

            manager_result = (

                self.manager.evaluate(

                    example_count=(
                        example_count
                    ),

                    task_type=(
                        task_type
                    ),

                    base_model=(
                        base_model
                    ),

                )

            )

        except Exception as exc:

            manager_result = {

                "success": False,

                "error":
                    str(exc),

                "fallback":
                    True,

            }

        # --------------------------------------------------
        # RUN PIPELINE MANAGER
        # --------------------------------------------------

        try:

            pipeline_result = (

                self.pipeline_manager
                .run_pipeline(

                    task_type=task_type,

                    dataset_path=dataset_path,

                    evaluation_dataset=(
                        evaluation_dataset
                    ),

                    current_time=current_time,

                )

            )

        except Exception as exc:

            self.total_errors += 1

            self.last_error = (
                str(exc)
            )

            return {

                "success": False,

                "pipeline_started": True,

                "pipeline_success": False,

                "stage":
                    "pipeline_manager",

                "reason":
                    str(exc),

                "controller":
                    controller_result,

                "manager":
                    manager_result,

            }

        # --------------------------------------------------
        # NORMALIZE PIPELINE RESULT
        # --------------------------------------------------

        if not isinstance(
            pipeline_result,
            dict,
        ):

            pipeline_result = {

                "success": False,

                "reason":
                    (
                        "Pipeline manager returned "
                        "an invalid result."
                    ),

            }

        # --------------------------------------------------
        # STORE RESULT
        # --------------------------------------------------

        self.last_pipeline_result = (
            pipeline_result
        )

        self.total_pipeline_runs += 1

        pipeline_success = (

            pipeline_result.get(

                "success",

                False,

            )

        )

        if pipeline_success:

            self.total_pipeline_successes += 1

        return {

            "success": True,

            "pipeline_started": True,

            "pipeline_success":
                pipeline_success,

            "example_count":
                example_count,

            "dataset_size":
                len(dataset),

            "task_type":
                task_type,

            "base_model":
                base_model,

            "controller":
                controller_result,

            "manager":
                manager_result,

            "pipeline":
                pipeline_result,

        }


    # ======================================================
    # PROCESS COMPLETED TASK
    # ======================================================

    def process_completed_task(
        self,
        prompt: str,
        response: str,
        task_type: str = "general",
        base_model: Optional[
            str
        ] = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
        auto_check: bool = True,
    ) -> Dict[str, Any]:

        """
        Safely process a completed V.A.U.L.T.
        interaction.

        Fine-tuning errors never crash the
        main V.A.U.L.T. assistant.
        """

        result = {

            "success": True,

            "stored": False,

            "pipeline_checked": False,

            "pipeline_started": False,

        }

        # --------------------------------------------------
        # STORE EXAMPLE
        # --------------------------------------------------

        try:

            storage_result = (

                self.add_training_example(

                    prompt=prompt,

                    response=response,

                    task_type=task_type,

                    metadata=metadata,

                )

            )

            result["stored"] = (

                storage_result.get(

                    "stored",

                    False,

                )

            )

            result["storage"] = (
                storage_result
            )

        except Exception as exc:

            self.total_errors += 1

            self.last_error = (
                str(exc)
            )

            result["success"] = False

            result["storage_error"] = (
                str(exc)
            )

            return result

        # --------------------------------------------------
        # STOP IF STORAGE FAILED
        # --------------------------------------------------

        if not result["stored"]:

            result["success"] = False

            return result

        # --------------------------------------------------
        # AUTO CHECK DISABLED
        # --------------------------------------------------

        if not auto_check:

            return result

        # --------------------------------------------------
        # CHECK PIPELINE
        # --------------------------------------------------

        try:

            pipeline_result = (

                self.check_pipeline(

                    task_type=task_type,

                    base_model=base_model,

                )

            )

            result["pipeline_checked"] = (
                True
            )

            result["pipeline_started"] = (

                pipeline_result.get(

                    "pipeline_started",

                    False,

                )

            )

            result["pipeline"] = (
                pipeline_result
            )

        except Exception as exc:

            self.total_errors += 1

            self.last_error = (
                str(exc)
            )

            result["pipeline_error"] = (
                str(exc)
            )

        return result


    # ======================================================
    # RUNTIME MODEL ROUTING
    # ======================================================

    def get_runtime_model(
        self,
        task_type: str,
        default_model: str,
    ) -> str:

        """
        Ask the fine-tuning runtime router
        whether a fine-tuned model should
        be used.

        Falls back safely to the default model.
        """

        try:

            routing_result = (

                self.runtime_router
                .route(

                    task_type=task_type,

                    default_model=default_model,

                )

            )

            if isinstance(
                routing_result,
                str,
            ):

                return routing_result

            if isinstance(
                routing_result,
                dict,
            ):

                model = (

                    routing_result.get(

                        "model",

                        routing_result.get(

                            "selected_model",

                            default_model,

                        ),

                    )

                )

                if isinstance(
                    model,
                    str,
                ) and model.strip():

                    return model

        except Exception as exc:

            self.last_error = (
                str(exc)
            )

        return default_model


    # ======================================================
    # GET STATUS
    # ======================================================

    def get_status(
        self,
    ) -> Dict[str, Any]:

        """
        Return the current fine-tuning
        service status.
        """

        try:

            pipeline_status = (

                self.pipeline_manager
                .get_status()

            )

        except Exception as exc:

            pipeline_status = {

                "error":
                    str(exc)

            }

        return {

            "service":
                "fine_tuning",

            "status":
                "running",

            "started_at":
                self.started_at,

            "training_examples":

                self.get_example_count(),

            "total_examples_received":

                self.total_examples_received,

            "total_examples_stored":

                self.total_examples_stored,

            "total_pipeline_checks":

                self.total_pipeline_checks,

            "total_pipeline_runs":

                self.total_pipeline_runs,

            "total_pipeline_successes":

                self.total_pipeline_successes,

            "total_errors":

                self.total_errors,

            "last_error":

                self.last_error,

            "last_pipeline_result":

                self.last_pipeline_result,

            "pipeline_manager":

                pipeline_status,

        }


# ==========================================================
# TEST COMPONENTS
# ==========================================================

class MockController:

    """
    Test controller that approves training.
    """

    def check(
        self,
        example_count,
        task_type,
        base_model,
        current_time=None,
    ):

        return {

            "success": True,

            "approved": True,

            "should_train": True,

            "reason":

                (
                    "Mock controller "
                    "approved training."
                ),

        }


class MockManager:

    """
    Test manager.
    """

    def evaluate(
        self,
        example_count,
        task_type,
        base_model,
    ):

        return {

            "success": True,

            "approved": True,

        }


class MockPipelineManager:

    """
    Test pipeline manager.

    Simulates the real pipeline manager API.
    """

    def __init__(self):

        self.examples = []


    def add_example(
        self,
        prompt,
        response,
        task_type,
        metadata=None,
    ):

        example = {

            "prompt":
                prompt,

            "response":
                response,

            "task_type":
                task_type,

            "metadata":
                metadata or {},

        }

        self.examples.append(
            example
        )

        return {

            "success": True,

            "stored": True,

        }


    def get_example_count(
        self,
        task_type=None,
    ):

        if task_type is None:

            return len(
                self.examples
            )

        return len([

            example

            for example
            in self.examples

            if example.get(
                "task_type"
            )
            ==
            task_type

        ])


    def get_examples(
        self,
    ):

        """
        Compatibility API.

        Returns all stored examples.
        """

        return list(
            self.examples
        )


    def get_training_examples(
        self,
    ):

        """
        Compatibility API.

        Returns all stored examples.
        """

        return list(
            self.examples
        )


    def select_base_model(
        self,
        task_type,
    ):

        return {

            "success": True,

            "model":
                "qwen3:4b",

        }


    def run_pipeline(
        self,
        task_type="general",
        dataset_path="data/fine_tuning",
        evaluation_dataset="data/evaluation",
        current_time=None,
    ):

        return {

            "success": True,

            "stage":
                "deployment_complete",

            "model_name":

                (
                    "vault-test-"
                    f"{task_type}-v1"
                ),

            "reason":

                (
                    "Mock fine-tuning "
                    "pipeline completed."
                ),

        }


    def get_status(
        self,
    ):

        return {

            "pipeline_running": False,

            "total_examples":
                len(self.examples),

        }


class MockRuntimeRouter:

    """
    Test runtime router.
    """

    def route(
        self,
        task_type,
        default_model,
    ):

        return {

            "model":

                (
                    "vault-test-"
                    f"{task_type}-v1"
                ),

        }


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNING SERVICE TEST"
    )

    print("=" * 60)


    # ======================================================
    # CREATE TEST SERVICE
    # ======================================================

    service = (

        FineTuningService(

            controller=(
                MockController()
            ),

            manager=(
                MockManager()
            ),

            pipeline_manager=(
                MockPipelineManager()
            ),

            runtime_router=(
                MockRuntimeRouter()
            ),

        )

    )


    # ======================================================
    # TEST 1
    # ADD TRAINING EXAMPLE
    # ======================================================

    print()

    print(
        "TEST 1: ADD TRAINING EXAMPLE"
    )

    print("-" * 60)


    result = (

        service.add_training_example(

            prompt=(
                "Calculate force for "
                "a 10 kg object."
            ),

            response=(
                "Force equals mass "
                "multiplied by acceleration."
            ),

            task_type=(
                "engineering"
            ),

        )

    )

    print(
        result
    )


    # ======================================================
    # TEST 2
    # PROCESS COMPLETED TASK
    # ======================================================

    print()

    print(
        "TEST 2: PROCESS COMPLETED TASK"
    )

    print("-" * 60)


    result = (

        service.process_completed_task(

            prompt=(
                "Write a Python function "
                "for factorial."
            ),

            response=(
                "def factorial(n): "
                "return 1 if n <= 1 "
                "else n * factorial(n - 1)"
            ),

            task_type=(
                "coding"
            ),

            base_model=(
                "qwen3:4b"
            ),

            auto_check=True,

        )

    )

    print(
        result
    )


    # ======================================================
    # TEST 3
    # RUNTIME MODEL
    # ======================================================

    print()

    print(
        "TEST 3: RUNTIME MODEL ROUTING"
    )

    print("-" * 60)


    model = (

        service.get_runtime_model(

            task_type=(
                "engineering"
            ),

            default_model=(
                "qwen3:4b"
            ),

        )

    )

    print(

        f"Selected model: {model}"

    )


    # ======================================================
    # TEST 4
    # SERVICE STATUS
    # ======================================================

    print()

    print(
        "TEST 4: SERVICE STATUS"
    )

    print("-" * 60)


    print(

        service.get_status()

    )


    print()

    print("=" * 60)

    print(
        "FINE-TUNING SERVICE TEST COMPLETE"
    )

    print("=" * 60)