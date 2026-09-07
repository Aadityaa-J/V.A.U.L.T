"""
V.A.U.L.T. Fine-Tuning Runtime Router

Connects deployed fine-tuned models to the main
V.A.U.L.T. model routing system.

Flow:

User Prompt
    ↓
Task Classification
    ↓
Check Specialized Fine-Tuned Models
    ↓
Check Deployment Status
    ↓
Use Specialized Model
        OR
Fallback to Main Router
"""


from pathlib import Path
import sys
from typing import Any, Dict, Optional


# ==========================================================
# PROJECT ROOT IMPORT SUPPORT
# ==========================================================

PROJECT_ROOT = Path(
    __file__
).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )


from models.router import (
    classify_task,
    select_model,
)

from models.fine_tuning.registry import (
    ModelRegistry,
)

from models.fine_tuning.deployer import (
    FineTuningDeployer,
)


# ==========================================================
# RUNTIME ROUTER
# ==========================================================

class FineTuningRuntimeRouter:

    """
    Select between:

    1. A deployed specialized fine-tuned model
    2. The normal V.A.U.L.T. model router

    Safety principle:

    Fine-tuned models are only used when they are:

    - Registered
    - Approved
    - Deployed
    - Ready
    """

    def __init__(
        self,
        registry: Optional[
            ModelRegistry
        ] = None,

        deployer: Optional[
            FineTuningDeployer
        ] = None,
    ):

        self.registry = (

            registry

            or

            ModelRegistry()

        )

        self.deployer = (

            deployer

            or

            FineTuningDeployer()

        )

    # ======================================================
    # FIND SPECIALIZED MODEL
    # ======================================================

    def get_specialized_model(
        self,
        task_type: str,
    ) -> Optional[
        Dict[str, Any]
    ]:

        """
        Find the best approved fine-tuned model
        for the requested task type.

        The model must also be deployed and ready.
        """

        # --------------------------------------------------
        # GET BEST REGISTERED MODEL
        # --------------------------------------------------

        model = (

            self.registry.get_best_model(
                task_type
            )

        )

        if model is None:

            return None

        model_name = (

            model.get(
                "model_name"
            )

        )

        if not model_name:

            return None

        # --------------------------------------------------
        # CHECK DEPLOYMENT STATUS
        # --------------------------------------------------

        if not (

            self.deployer.is_model_ready(
                model_name
            )

        ):

            return None

        # --------------------------------------------------
        # GET DEPLOYMENT RECORD
        # --------------------------------------------------

        deployment = (

            self.deployer.get_deployment(
                model_name
            )

        )

        if deployment is None:

            return None

        return {

            "model":
                model,

            "deployment":
                deployment,

        }

    # ======================================================
    # ROUTE REQUEST
    # ======================================================

    def route(
        self,
        prompt: str,
        image_path: Optional[
            str
        ] = None,
        use_vram_manager: bool = True,
        use_performance_manager: bool = True,
    ) -> Dict[str, Any]:

        """
        Route a user request.

        Priority:

        1. Ready specialized fine-tuned model
        2. Normal V.A.U.L.T. router
        """

        # --------------------------------------------------
        # VALIDATE PROMPT
        # --------------------------------------------------

        if not isinstance(
            prompt,
            str,
        ):

            raise TypeError(
                "prompt must be a string."
            )

        # --------------------------------------------------
        # CLASSIFY TASK
        # --------------------------------------------------

        task_type = (

            classify_task(

                prompt=prompt,

                image_path=image_path,

            )

        )

        # --------------------------------------------------
        # LOOK FOR SPECIALIZED MODEL
        # --------------------------------------------------

        try:

            specialized = (

                self.get_specialized_model(
                    task_type
                )

            )

        except Exception:

            specialized = None

        # --------------------------------------------------
        # SPECIALIZED MODEL AVAILABLE
        # --------------------------------------------------

        if specialized is not None:

            model = specialized[
                "model"
            ]

            deployment = specialized[
                "deployment"
            ]

            runtime_model_name = (

                deployment.get(
                    "runtime_model_name"
                )

                or

                model.get(
                    "model_name"
                )

            )

            return {

                "task_type":
                    task_type,

                "selected_model":
                    runtime_model_name,

                "source":
                    "fine_tuned",

                "status":
                    "specialized_model_selected",

                "model":
                    model,

                "deployment":
                    deployment,

            }

        # --------------------------------------------------
        # FALLBACK TO NORMAL ROUTER
        # --------------------------------------------------

        fallback_model = (

            select_model(

                task_type=task_type,

                use_vram_manager=(
                    use_vram_manager
                ),

                use_performance_manager=(
                    use_performance_manager
                ),

            )

        )

        return {

            "task_type":
                task_type,

            "selected_model":
                fallback_model,

            "source":
                "base_router",

            "status":
                "fallback_model_selected",

            "model":
                None,

            "deployment":
                None,

        }

    # ======================================================
    # SIMPLE MODEL ROUTING
    # ======================================================

    def select_model(
        self,
        prompt: str,
        image_path: Optional[
            str
        ] = None,
        use_vram_manager: bool = True,
        use_performance_manager: bool = True,
    ) -> str:

        """
        Return only the selected model name.

        Useful for direct integration with chat.py.
        """

        result = (

            self.route(

                prompt=prompt,

                image_path=image_path,

                use_vram_manager=(
                    use_vram_manager
                ),

                use_performance_manager=(
                    use_performance_manager
                ),

            )

        )

        return result[
            "selected_model"
        ]


# ==========================================================
# CONVENIENCE FUNCTION
# ==========================================================

def route_with_fine_tuning(
    prompt: str,
    image_path: Optional[
        str
    ] = None,
    use_vram_manager: bool = True,
    use_performance_manager: bool = True,
) -> Dict[str, Any]:

    """
    Convenience function for routing through
    the fine-tuning-aware router.
    """

    router = (

        FineTuningRuntimeRouter()

    )

    return (

        router.route(

            prompt=prompt,

            image_path=image_path,

            use_vram_manager=(
                use_vram_manager
            ),

            use_performance_manager=(
                use_performance_manager
            ),

        )

    )


# ==========================================================
# TEST HELPERS
# ==========================================================

def create_test_artifact(
    model_name: str,
    task_type: str,
) -> Dict[str, Any]:

    """
    Create a test artifact.
    """

    return {

        "model_name":
            model_name,

        "artifact_id":
            f"{model_name}-artifact",

        "base_model":
            "qwen3:4b",

        "task_type":
            task_type,

        "dataset_version":
            1,

        "runtime":
            "mock",

    }


def create_test_evaluation() -> Dict[str, Any]:

    """
    Create an approved evaluation result.
    """

    return {

        "accepted":
            True,

        "candidate_score":
            0.95,

        "base_score":
            0.80,

        "improvement":
            0.15,

    }


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNING RUNTIME ROUTER TEST"
    )

    print("=" * 60)

    # ------------------------------------------------------
    # USE ISOLATED TEST STORAGE
    # ------------------------------------------------------

    registry = (

        ModelRegistry(

            storage_path=(
                "data/test_runtime_registry"
            )

        )

    )

    deployer = (

        FineTuningDeployer(

            storage_path=(
                "data/test_runtime_deployments"
            )

        )

    )

    runtime_router = (

        FineTuningRuntimeRouter(

            registry=registry,

            deployer=deployer,

        )

    )

    # ------------------------------------------------------
    # CREATE SPECIALIZED MODEL
    # ------------------------------------------------------

    artifact = (

        create_test_artifact(

            model_name=(
                "vault-engineering-runtime-v1"
            ),

            task_type=(
                "engineering"
            ),

        )

    )

    evaluation = (

        create_test_evaluation()

    )

    # ------------------------------------------------------
    # REGISTER MODEL
    # ------------------------------------------------------

    registration = (

        registry.register_model(

            artifact=artifact,

            evaluation=evaluation,

        )

    )

    print()

    print(
        "MODEL REGISTRATION"
    )

    print("-" * 60)

    print(
        registration
    )

    # ------------------------------------------------------
    # DEPLOY MODEL
    # ------------------------------------------------------

    deployment = (

        deployer.deploy(

            artifact=artifact,

            evaluation=evaluation,

        )

    )

    print()

    print(
        "MODEL DEPLOYMENT"
    )

    print("-" * 60)

    print(
        deployment
    )

    # ------------------------------------------------------
    # TEST 1
    # ENGINEERING TASK
    # ------------------------------------------------------

    prompt = (

        "Calculate the force required "
        "to accelerate a 10 kg object."
    )

    print()

    print(
        "TEST 1: ENGINEERING TASK"
    )

    print("-" * 60)

    print(
        f"Prompt: {prompt}"
    )

    result = (

        runtime_router.route(

            prompt=prompt,

            use_vram_manager=False,

            use_performance_manager=False,

        )

    )

    print()

    print(
        result
    )

    # ------------------------------------------------------
    # TEST 2
    # SIMPLE TASK
    # ------------------------------------------------------

    prompt = (

        "Hello, how are you?"
    )

    print()

    print(
        "TEST 2: SIMPLE TASK"
    )

    print("-" * 60)

    print(
        f"Prompt: {prompt}"
    )

    result = (

        runtime_router.route(

            prompt=prompt,

            use_vram_manager=False,

            use_performance_manager=False,

        )

    )

    print()

    print(
        result
    )

    # ------------------------------------------------------
    # TEST 3
    # SIMPLE MODEL NAME
    # ------------------------------------------------------

    prompt = (

        "Calculate electrical power "
        "from voltage and current."
    )

    print()

    print(
        "TEST 3: SIMPLE MODEL SELECTION"
    )

    print("-" * 60)

    selected_model = (

        runtime_router.select_model(

            prompt=prompt,

            use_vram_manager=False,

            use_performance_manager=False,

        )

    )

    print(

        f"Selected Model: "
        f"{selected_model}"

    )

    print()

    print("=" * 60)

    print(
        "RUNTIME ROUTER TEST COMPLETE"
    )

    print("=" * 60)