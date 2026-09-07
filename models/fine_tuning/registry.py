"""
V.A.U.L.T. Fine-Tuning Model Registry

Responsible for:

- Registering approved models
- Storing model metadata locally
- Tracking model versions
- Discovering approved specialized models
- Preventing rejected models from becoming active

The registry is runtime-agnostic.
"""


import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ModelRegistry:

    """
    Local registry for approved fine-tuned models.
    """

    def __init__(
        self,
        storage_path: str = "data/model_registry",
    ):

        self.storage_path = Path(
            storage_path
        )

        self.storage_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.registry_file = (
            self.storage_path
            / "registry.json"
        )

        self._ensure_registry()

    # ======================================================
    # INITIALIZE REGISTRY
    # ======================================================

    def _ensure_registry(
        self,
    ) -> None:

        """
        Create registry file if it does not exist.
        """

        if not self.registry_file.exists():

            self._save_registry(
                {
                    "models": []
                }
            )

    # ======================================================
    # LOAD REGISTRY
    # ======================================================

    def _load_registry(
        self,
    ) -> Dict[str, Any]:

        try:

            with open(
                self.registry_file,
                "r",
                encoding="utf-8",
            ) as file:

                data = json.load(
                    file
                )

            if not isinstance(
                data,
                dict,
            ):

                return {
                    "models": []
                }

            if "models" not in data:

                data["models"] = []

            return data

        except (
            json.JSONDecodeError,
            OSError,
        ):

            # Fail safely.

            return {
                "models": []
            }

    # ======================================================
    # SAVE REGISTRY
    # ======================================================

    def _save_registry(
        self,
        data: Dict[str, Any],
    ) -> None:

        with open(
            self.registry_file,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False,
            )

    # ======================================================
    # REGISTER MODEL
    # ======================================================

    def register_model(
        self,
        artifact: Dict[str, Any],
        evaluation: Dict[str, Any],
    ) -> Dict[str, Any]:

        """
        Register a model ONLY if evaluation approved it.
        """

        if not isinstance(
            artifact,
            dict,
        ):

            raise TypeError(
                "artifact must be a dictionary."
            )

        if not isinstance(
            evaluation,
            dict,
        ):

            raise TypeError(
                "evaluation must be a dictionary."
            )

        # --------------------------------------------------
        # SAFETY CHECK
        # --------------------------------------------------

        if not evaluation.get(
            "accepted",
            False,
        ):

            return {

                "success": False,

                "registered": False,

                "reason":
                    (
                        "Model was not approved "
                        "by evaluation."
                    ),

            }

        model_name = artifact.get(
            "model_name"
        )

        if not model_name:

            return {

                "success": False,

                "registered": False,

                "reason":
                    (
                        "Model artifact does not "
                        "contain model_name."
                    ),

            }

        registry = (
            self._load_registry()
        )

        models = registry[
            "models"
        ]

        # --------------------------------------------------
        # DUPLICATE CHECK
        # --------------------------------------------------

        for model in models:

            if (

                model.get(
                    "model_name"
                )

                ==

                model_name

            ):

                return {

                    "success": False,

                    "registered": False,

                    "reason":
                        (
                            "Model is already "
                            "registered."
                        ),

                }

        # --------------------------------------------------
        # CREATE REGISTRY RECORD
        # --------------------------------------------------

        record = {

            "model_name":
                model_name,

            "artifact_id":
                artifact.get(
                    "artifact_id"
                ),

            "base_model":
                artifact.get(
                    "base_model"
                ),

            "task_type":
                artifact.get(
                    "task_type"
                ),

            "dataset_version":
                artifact.get(
                    "dataset_version"
                ),

            "created_at":
                artifact.get(
                    "created_at"
                ),

            "registered_at":
                datetime.now()
                .isoformat(),

            "runtime":
                artifact.get(
                    "runtime"
                ),

            "status":
                "approved",

            "evaluation_score":
                evaluation.get(
                    "candidate_score"
                ),

            "base_score":
                evaluation.get(
                    "base_score"
                ),

            "improvement":
                evaluation.get(
                    "improvement"
                ),

        }

        # --------------------------------------------------
        # STORE MODEL
        # --------------------------------------------------

        models.append(
            record
        )

        self._save_registry(
            registry
        )

        return {

            "success": True,

            "registered": True,

            "model":
                record,

        }

    # ======================================================
    # GET MODEL
    # ======================================================

    def get_model(
        self,
        model_name: str,
    ) -> Optional[
        Dict[str, Any]
    ]:

        """
        Find a registered model by name.
        """

        registry = (
            self._load_registry()
        )

        for model in registry[
            "models"
        ]:

            if (

                model.get(
                    "model_name"
                )

                ==

                model_name

            ):

                return model

        return None

    # ======================================================
    # GET MODELS FOR TASK TYPE
    # ======================================================

    def get_models_for_task(
        self,
        task_type: str,
    ) -> List[
        Dict[str, Any]
    ]:

        """
        Return approved models for a task type.
        """

        registry = (
            self._load_registry()
        )

        results = []

        for model in registry[
            "models"
        ]:

            if (

                model.get(
                    "task_type"
                )

                ==

                task_type

                and

                model.get(
                    "status"
                )

                ==

                "approved"

            ):

                results.append(
                    model
                )

        return results

    # ======================================================
    # GET BEST MODEL
    # ======================================================

    def get_best_model(
        self,
        task_type: str,
    ) -> Optional[
        Dict[str, Any]
    ]:

        """
        Return the highest-scoring approved model
        for a task type.
        """

        models = (

            self.get_models_for_task(
                task_type
            )

        )

        if not models:

            return None

        return max(

            models,

            key=lambda model:

                model.get(
                    "evaluation_score"
                )

                or 0.0,

        )

    # ======================================================
    # LIST MODELS
    # ======================================================

    def list_models(
        self,
    ) -> List[
        Dict[str, Any]
    ]:

        """
        Return all registered models.
        """

        registry = (
            self._load_registry()
        )

        return registry[
            "models"
        ]


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. MODEL REGISTRY TEST"
    )

    print("=" * 60)

    registry = ModelRegistry(
        storage_path=(
            "data/test_model_registry"
        )
    )

    # ------------------------------------------------------
    # APPROVED MODEL
    # ------------------------------------------------------

    artifact = {

        "model_name":
            "vault-engineering-v1",

        "artifact_id":
            "abc123",

        "base_model":
            "qwen3:4b",

        "task_type":
            "engineering",

        "dataset_version":
            1,

        "created_at":
            datetime.now()
            .isoformat(),

        "runtime":
            "mock",

    }

    evaluation = {

        "accepted":
            True,

        "candidate_score":
            0.91,

        "base_score":
            0.80,

        "improvement":
            0.11,

    }

    result = (

        registry.register_model(

            artifact,

            evaluation,

        )

    )

    print()

    print(
        "TEST 1: APPROVED MODEL"
    )

    print("-" * 60)

    print(result)

    # ------------------------------------------------------
    # REJECTED MODEL
    # ------------------------------------------------------

    rejected_artifact = {

        "model_name":
            "vault-engineering-bad",

        "artifact_id":
            "bad123",

        "base_model":
            "qwen3:4b",

        "task_type":
            "engineering",

        "dataset_version":
            1,

        "created_at":
            datetime.now()
            .isoformat(),

        "runtime":
            "mock",

    }

    rejected_evaluation = {

        "accepted":
            False,

        "candidate_score":
            0.70,

        "base_score":
            0.80,

        "improvement":
            -0.10,

    }

    result = (

        registry.register_model(

            rejected_artifact,

            rejected_evaluation,

        )

    )

    print()

    print(
        "TEST 2: REJECTED MODEL"
    )

    print("-" * 60)

    print(result)

    # ------------------------------------------------------
    # FIND BEST ENGINEERING MODEL
    # ------------------------------------------------------

    best_model = (

        registry.get_best_model(
            "engineering"
        )

    )

    print()

    print(
        "TEST 3: BEST ENGINEERING MODEL"
    )

    print("-" * 60)

    print(best_model)

    print()

    print("=" * 60)

    print(
        "MODEL REGISTRY TEST COMPLETE"
    )

    print("=" * 60)