"""
V.A.U.L.T. Fine-Tuned Model Selector

Responsible for discovering approved fine-tuned models
and deciding whether a specialized model should be used.

The selector does NOT replace the main router.

Instead, it provides the router with information about
available approved specialized models.

Flow:

Task Type
    ↓
Model Registry
    ↓
Approved Specialized Model Available?
    ↓
YES → Return Fine-Tuned Model
NO  → Return None
"""


from typing import Any, Dict, Optional

from models.fine_tuning.registry import (
    ModelRegistry
)


# ==========================================================
# FINE-TUNED MODEL SELECTOR
# ==========================================================

class FineTunedModelSelector:

    """
    Discover and select approved fine-tuned models.

    The selector queries the ModelRegistry and returns
    the best approved model for a task type.
    """

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
    ):

        self.registry = (

            registry

            or

            ModelRegistry()

        )

    # ======================================================
    # GET BEST MODEL
    # ======================================================

    def get_best_model(
        self,
        task_type: str,
    ) -> Optional[Dict[str, Any]]:

        """
        Return the best approved fine-tuned model
        for the requested task type.

        Returns None if no approved specialized model
        exists.
        """

        if not isinstance(
            task_type,
            str,
        ):

            raise TypeError(
                "task_type must be a string."
            )

        task_type = task_type.strip().lower()

        if not task_type:

            return None

        try:

            model = (

                self.registry.get_best_model(
                    task_type
                )

            )

            return model

        except Exception:

            # Registry problems must never stop
            # V.A.U.L.T. from operating.

            return None

    # ======================================================
    # SELECT MODEL
    # ======================================================

    def select_model(
        self,
        task_type: str,
    ) -> Dict[str, Any]:

        """
        Select an approved fine-tuned model.

        Returns information explaining whether
        a specialized model was found.
        """

        model = (

            self.get_best_model(
                task_type
            )

        )

        # --------------------------------------------------
        # NO SPECIALIZED MODEL
        # --------------------------------------------------

        if model is None:

            return {

                "available":
                    False,

                "model":
                    None,

                "model_name":
                    None,

                "task_type":
                    task_type,

                "reason":
                    (
                        "No approved fine-tuned "
                        "model is available for "
                        "this task type."
                    ),

            }

        # --------------------------------------------------
        # SPECIALIZED MODEL FOUND
        # --------------------------------------------------

        return {

            "available":
                True,

            "model":
                model,

            "model_name":
                model.get(
                    "model_name"
                ),

            "task_type":
                task_type,

            "evaluation_score":
                model.get(
                    "evaluation_score"
                ),

            "improvement":
                model.get(
                    "improvement"
                ),

            "reason":
                (
                    "Approved fine-tuned model "
                    "available for this task type."
                ),

        }

    # ======================================================
    # CHECK AVAILABILITY
    # ======================================================

    def has_specialized_model(
        self,
        task_type: str,
    ) -> bool:

        """
        Return True when an approved fine-tuned model
        exists for the task type.
        """

        result = (

            self.select_model(
                task_type
            )

        )

        return bool(

            result.get(
                "available",
                False,
            )

        )


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNED MODEL SELECTOR TEST"
    )

    print("=" * 60)

    # ------------------------------------------------------
    # CREATE TEST REGISTRY
    # ------------------------------------------------------

    registry = ModelRegistry(

        storage_path=(
            "data/test_model_selector_registry"
        )

    )

    # ------------------------------------------------------
    # REGISTER TEST MODEL
    # ------------------------------------------------------

    artifact = {

        "model_name":
            "vault-engineering-test-v1",

        "artifact_id":
            "engineering-test-001",

        "base_model":
            "qwen3:4b",

        "task_type":
            "engineering",

        "dataset_version":
            1,

        "created_at":
            "2026-09-07T08:30:00",

        "runtime":
            "mock",

    }

    evaluation = {

        "accepted":
            True,

        "candidate_score":
            0.92,

        "base_score":
            0.80,

        "improvement":
            0.12,

    }

    registration = (

        registry.register_model(

            artifact=artifact,

            evaluation=evaluation,

        )

    )

    print()

    print(
        "REGISTER TEST MODEL"
    )

    print("-" * 60)

    print(
        registration
    )

    # ------------------------------------------------------
    # CREATE SELECTOR
    # ------------------------------------------------------

    selector = (

        FineTunedModelSelector(

            registry=registry

        )

    )

    # ------------------------------------------------------
    # TEST ENGINEERING
    # ------------------------------------------------------

    print()

    print(
        "TEST 1: ENGINEERING MODEL"
    )

    print("-" * 60)

    result = (

        selector.select_model(
            "engineering"
        )

    )

    print(
        result
    )

    # ------------------------------------------------------
    # TEST CODING
    # ------------------------------------------------------

    print()

    print(
        "TEST 2: CODING MODEL"
    )

    print("-" * 60)

    result = (

        selector.select_model(
            "coding"
        )

    )

    print(
        result
    )

    # ------------------------------------------------------
    # AVAILABILITY TEST
    # ------------------------------------------------------

    print()

    print(
        "TEST 3: AVAILABILITY CHECK"
    )

    print("-" * 60)

    print(

        "Engineering:",

        selector.has_specialized_model(
            "engineering"
        )

    )

    print(

        "Coding:",

        selector.has_specialized_model(
            "coding"
        )

    )

    print()

    print("=" * 60)

    print(
        "MODEL SELECTOR TEST COMPLETE"
    )

    print("=" * 60)