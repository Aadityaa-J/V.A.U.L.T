"""
V.A.U.L.T. Fine-Tuning Model Deployer

Responsible for converting an approved training artifact
into a deployable model record.

IMPORTANT:

This module does NOT perform real Ollama model creation yet.

The current implementation provides a safe deployment
abstraction that:

- Validates trained artifacts
- Prevents rejected models from being deployed
- Tracks deployment status
- Creates persistent deployment records
- Supports future Ollama / GGUF / Transformers backends

Flow:

Approved Training Artifact
        ↓
Deployment Validation
        ↓
Deployment Backend
        ↓
Runtime Model Registration
        ↓
Deployment Record
        ↓
Ready for Router
"""


import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


# ==========================================================
# DEPLOYMENT BACKEND
# ==========================================================

class DeploymentBackend(ABC):

    """
    Abstract interface for deployment backends.

    Future implementations may include:

    - OllamaDeploymentBackend
    - GGUFDeploymentBackend
    - TransformersDeploymentBackend
    """

    @abstractmethod
    def deploy(
        self,
        artifact: Dict[str, Any],
    ) -> Dict[str, Any]:

        """
        Deploy a trained model artifact.
        """

        pass


# ==========================================================
# MOCK DEPLOYMENT BACKEND
# ==========================================================

class MockDeploymentBackend(
    DeploymentBackend
):

    """
    Development deployment backend.

    Simulates deployment without requiring:

    - Ollama
    - Docker
    - CUDA
    - GGUF conversion
    - Model files
    """

    def __init__(
        self,
        should_fail: bool = False,
    ):

        self.should_fail = should_fail

    def deploy(
        self,
        artifact: Dict[str, Any],
    ) -> Dict[str, Any]:

        # --------------------------------------------------
        # SIMULATE FAILURE
        # --------------------------------------------------

        if self.should_fail:

            return {

                "success": False,

                "runtime_model_name": None,

                "runtime": "mock",

                "error":
                    "Mock deployment failure.",

            }

        # --------------------------------------------------
        # VALIDATE MODEL NAME
        # --------------------------------------------------

        model_name = artifact.get(
            "model_name"
        )

        if not model_name:

            return {

                "success": False,

                "runtime_model_name": None,

                "runtime": "mock",

                "error":
                    (
                        "Artifact does not contain "
                        "a model_name."
                    ),

            }

        # --------------------------------------------------
        # SIMULATED DEPLOYMENT
        # --------------------------------------------------

        return {

            "success": True,

            "runtime_model_name":
                model_name,

            "runtime":
                "mock",

            "status":
                "ready",

            "deployed_at":
                datetime.now().isoformat(),

            "error":
                None,

        }


# ==========================================================
# FINE-TUNING DEPLOYER
# ==========================================================

class FineTuningDeployer:

    """
    Coordinates deployment of approved fine-tuned models.

    Deployment is intentionally separate from:

    - Training
    - Evaluation
    - Registry

    This prevents unapproved or failed models from
    becoming available to the router.
    """

    def __init__(
        self,
        backend: Optional[
            DeploymentBackend
        ] = None,

        storage_path: str = (
            "data/model_deployments"
        ),
    ):

        self.backend = (

            backend

            or

            MockDeploymentBackend()

        )

        self.storage_path = Path(
            storage_path
        )

        self.storage_path.mkdir(

            parents=True,

            exist_ok=True,

        )

        self.deployments_file = (

            self.storage_path

            / "deployments.json"

        )

        self._ensure_storage()

    # ======================================================
    # INITIALIZE STORAGE
    # ======================================================

    def _ensure_storage(
        self,
    ) -> None:

        """
        Create deployment storage if needed.
        """

        if not self.deployments_file.exists():

            self._save_deployments(

                {
                    "deployments": []
                }

            )

    # ======================================================
    # LOAD DEPLOYMENTS
    # ======================================================

    def _load_deployments(
        self,
    ) -> Dict[str, Any]:

        """
        Load deployment records safely.
        """

        try:

            with open(

                self.deployments_file,

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

                    "deployments": []

                }

            if "deployments" not in data:

                data[
                    "deployments"
                ] = []

            return data

        except (

            json.JSONDecodeError,

            OSError,

        ):

            return {

                "deployments": []

            }

    # ======================================================
    # SAVE DEPLOYMENTS
    # ======================================================

    def _save_deployments(
        self,
        data: Dict[str, Any],
    ) -> None:

        """
        Save deployment records.
        """

        with open(

            self.deployments_file,

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
    # VALIDATE ARTIFACT
    # ======================================================

    def validate_artifact(
        self,
        artifact: Dict[str, Any],
    ) -> Dict[str, Any]:

        """
        Validate whether an artifact can be deployed.
        """

        if not isinstance(
            artifact,
            dict,
        ):

            return {

                "valid": False,

                "reason":
                    (
                        "Artifact must be "
                        "a dictionary."
                    ),

            }

        required_fields = [

            "model_name",

            "artifact_id",

            "base_model",

            "task_type",

        ]

        missing_fields = []

        for field in required_fields:

            if not artifact.get(
                field
            ):

                missing_fields.append(
                    field
                )

        if missing_fields:

            return {

                "valid": False,

                "reason":
                    (
                        "Artifact is missing "
                        "required fields."
                    ),

                "missing_fields":
                    missing_fields,

            }

        return {

            "valid": True,

            "reason":
                (
                    "Artifact is valid "
                    "for deployment."
                ),

            "missing_fields": [],

        }

    # ======================================================
    # CHECK EXISTING DEPLOYMENT
    # ======================================================

    def get_deployment(
        self,
        model_name: str,
    ) -> Optional[
        Dict[str, Any]
    ]:

        """
        Find an existing deployment.
        """

        data = (

            self._load_deployments()

        )

        for deployment in data[
            "deployments"
        ]:

            if (

                deployment.get(
                    "model_name"
                )

                ==

                model_name

            ):

                return deployment

        return None

    # ======================================================
    # DEPLOY MODEL
    # ======================================================

    def deploy(
        self,
        artifact: Dict[str, Any],
        evaluation: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:

        """
        Deploy a fine-tuned model.

        If evaluation data is provided, the model
        must explicitly be approved.
        """

        # --------------------------------------------------
        # ARTIFACT VALIDATION
        # --------------------------------------------------

        validation = (

            self.validate_artifact(
                artifact
            )

        )

        if not validation.get(
            "valid",
            False,
        ):

            return {

                "success": False,

                "deployed": False,

                "reason":
                    validation.get(
                        "reason"
                    ),

                "validation":
                    validation,

            }

        # --------------------------------------------------
        # EVALUATION SAFETY CHECK
        # --------------------------------------------------

        if evaluation is not None:

            if not evaluation.get(
                "accepted",
                False,
            ):

                return {

                    "success": False,

                    "deployed": False,

                    "reason":
                        (
                            "Model was not approved "
                            "by evaluation."
                        ),

                    "validation":
                        validation,

                }

        model_name = artifact[
            "model_name"
        ]

        # --------------------------------------------------
        # DUPLICATE CHECK
        # --------------------------------------------------

        existing = (

            self.get_deployment(
                model_name
            )

        )

        if existing is not None:

            return {

                "success": True,

                "deployed": True,

                "already_deployed": True,

                "deployment":
                    existing,

                "reason":
                    (
                        "Model is already "
                        "deployed."
                    ),

            }

        # --------------------------------------------------
        # BACKEND DEPLOYMENT
        # --------------------------------------------------

        try:

            backend_result = (

                self.backend.deploy(
                    artifact
                )

            )

        except Exception as exc:

            return {

                "success": False,

                "deployed": False,

                "reason":
                    (
                        "Deployment backend "
                        f"failed: {exc}"
                    ),

            }

        # --------------------------------------------------
        # VALIDATE BACKEND RESULT
        # --------------------------------------------------

        if not isinstance(
            backend_result,
            dict,
        ):

            return {

                "success": False,

                "deployed": False,

                "reason":
                    (
                        "Deployment backend "
                        "returned an invalid result."
                    ),

            }

        if not backend_result.get(
            "success",
            False,
        ):

            return {

                "success": False,

                "deployed": False,

                "reason":
                    backend_result.get(
                        "error",

                        "Deployment failed."
                    ),

                "backend":
                    backend_result,

            }

        # --------------------------------------------------
        # CREATE DEPLOYMENT RECORD
        # --------------------------------------------------

        deployment = {

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

            "runtime_model_name":
                backend_result.get(
                    "runtime_model_name"
                ),

            "runtime":
                backend_result.get(
                    "runtime"
                ),

            "status":
                backend_result.get(
                    "status",

                    "ready",
                ),

            "deployed_at":
                backend_result.get(
                    "deployed_at",

                    datetime.now().isoformat(),
                ),

        }

        # --------------------------------------------------
        # STORE DEPLOYMENT
        # --------------------------------------------------

        data = (

            self._load_deployments()

        )

        data[
            "deployments"
        ].append(

            deployment

        )

        self._save_deployments(
            data
        )

        # --------------------------------------------------
        # SUCCESS
        # --------------------------------------------------

        return {

            "success": True,

            "deployed": True,

            "already_deployed": False,

            "deployment":
                deployment,

            "backend":
                backend_result,

        }

    # ======================================================
    # CHECK MODEL READY
    # ======================================================

    def is_model_ready(
        self,
        model_name: str,
    ) -> bool:

        """
        Return True only if the model has a
        ready deployment.
        """

        deployment = (

            self.get_deployment(
                model_name
            )

        )

        if deployment is None:

            return False

        return (

            deployment.get(
                "status"
            )

            ==

            "ready"

        )

    # ======================================================
    # LIST DEPLOYMENTS
    # ======================================================

    def list_deployments(
        self,
    ) -> list[Dict[str, Any]]:

        """
        Return all deployment records.
        """

        data = (

            self._load_deployments()

        )

        return data[
            "deployments"
        ]


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNING DEPLOYER TEST"
    )

    print("=" * 60)

    # ------------------------------------------------------
    # CREATE DEPLOYER
    # ------------------------------------------------------

    deployer = (

        FineTuningDeployer(

            storage_path=(
                "data/test_model_deployments"
            )

        )

    )

    # ------------------------------------------------------
    # TEST ARTIFACT
    # ------------------------------------------------------

    artifact = {

        "model_name":
            "vault-engineering-test-v1",

        "artifact_id":
            "test-artifact-001",

        "base_model":
            "qwen3:4b",

        "task_type":
            "engineering",

        "dataset_version":
            1,

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

    # ------------------------------------------------------
    # TEST 1
    # VALID DEPLOYMENT
    # ------------------------------------------------------

    print()

    print(
        "TEST 1: APPROVED MODEL DEPLOYMENT"
    )

    print("-" * 60)

    result = (

        deployer.deploy(

            artifact=artifact,

            evaluation=evaluation,

        )

    )

    print(
        result
    )

    # ------------------------------------------------------
    # TEST 2
    # MODEL READY
    # ------------------------------------------------------

    print()

    print(
        "TEST 2: MODEL READY CHECK"
    )

    print("-" * 60)

    print(

        deployer.is_model_ready(

            "vault-engineering-test-v1"

        )

    )

    # ------------------------------------------------------
    # TEST 3
    # DUPLICATE DEPLOYMENT
    # ------------------------------------------------------

    print()

    print(
        "TEST 3: DUPLICATE DEPLOYMENT"
    )

    print("-" * 60)

    result = (

        deployer.deploy(

            artifact=artifact,

            evaluation=evaluation,

        )

    )

    print(
        result
    )

    # ------------------------------------------------------
    # TEST 4
    # REJECTED MODEL
    # ------------------------------------------------------

    print()

    print(
        "TEST 4: REJECTED MODEL"
    )

    print("-" * 60)

    rejected_evaluation = {

        "accepted":
            False,

    }

    result = (

        deployer.deploy(

            artifact={

                "model_name":
                    "vault-rejected-model",

                "artifact_id":
                    "rejected-001",

                "base_model":
                    "qwen3:4b",

                "task_type":
                    "engineering",

            },

            evaluation=(
                rejected_evaluation
            ),

        )

    )

    print(
        result
    )

    # ------------------------------------------------------
    # LIST DEPLOYMENTS
    # ------------------------------------------------------

    print()

    print(
        "ALL DEPLOYMENTS"
    )

    print("-" * 60)

    print(

        deployer.list_deployments()

    )

    print()

    print("=" * 60)

    print(
        "DEPLOYER TEST COMPLETE"
    )

    print("=" * 60)