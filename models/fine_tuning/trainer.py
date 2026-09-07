"""
V.A.U.L.T. Fine-Tuning Trainer

Provides a runtime-agnostic training backend system.

This module does NOT assume:

- Ollama
- CUDA
- NVIDIA GPUs
- Transformers
- PEFT

During development, MockTrainer simulates training.

Real training backends can later be added.
"""

from abc import ABC, abstractmethod

from datetime import datetime

from typing import Any, Dict, Optional

import hashlib


# ==========================================================
# BASE TRAINING BACKEND
# ==========================================================

class FineTuningBackend(ABC):

    """
    Abstract interface for all fine-tuning backends.
    """

    @abstractmethod
    def train(
        self,
        job: Dict[str, Any],
    ) -> Dict[str, Any]:

        """
        Execute a fine-tuning job.
        """

        pass


# ==========================================================
# MOCK TRAINER
# ==========================================================

class MockTrainer(FineTuningBackend):

    """
    Development trainer.

    Simulates successful fine-tuning without requiring:

    - GPU
    - VRAM
    - CUDA
    - Large model training
    """

    def __init__(
        self,
        should_fail: bool = False,
    ):

        self.should_fail = should_fail

    def train(
        self,
        job: Dict[str, Any],
    ) -> Dict[str, Any]:

        # --------------------------------------------------
        # SIMULATE FAILURE
        # --------------------------------------------------

        if self.should_fail:

            return {

                "success": False,

                "error":
                    (
                        "Mock training failure."
                    ),

                "artifact": None,

            }

        # --------------------------------------------------
        # CREATE MODEL IDENTIFIER
        # --------------------------------------------------

        base_model = job.get(
            "base_model",
            "unknown-model",
        )

        task_type = job.get(
            "task_type",
            "general",
        )

        dataset_version = job.get(
            "dataset_version",
            "unknown",
        )

        timestamp = (
            datetime.now()
            .isoformat()
        )

        unique_source = (

            f"{base_model}|"
            f"{task_type}|"
            f"{dataset_version}|"
            f"{timestamp}"

        )

        model_hash = (

            hashlib.sha256(
                unique_source.encode(
                    "utf-8"
                )
            )
            .hexdigest()[:12]

        )

        model_name = (

            f"vault-"
            f"{task_type}-"
            f"{model_hash}"

        )

        # --------------------------------------------------
        # CREATE ARTIFACT
        # --------------------------------------------------

        artifact = {

            "model_name":
                model_name,

            "artifact_id":
                model_hash,

            "base_model":
                base_model,

            "task_type":
                task_type,

            "dataset_version":
                dataset_version,

            "created_at":
                timestamp,

            "runtime":
                "mock",

            "status":
                "trained",

        }

        return {

            "success": True,

            "artifact":
                artifact,

            "error":
                None,

        }


# ==========================================================
# TRAINING MANAGER
# ==========================================================

class FineTuningTrainer:

    """
    Coordinates fine-tuning jobs.

    The trainer itself does not know how
    fine-tuning is performed.

    It delegates execution to a pluggable backend.
    """

    def __init__(
        self,
        backend: Optional[
            FineTuningBackend
        ] = None,
    ):

        self.backend = (

            backend
            or MockTrainer()

        )

    # ======================================================
    # CREATE TRAINING JOB
    # ======================================================

    def create_job(
        self,
        base_model: str,
        task_type: str,
        dataset_version: Any,
        dataset_path: str,
    ) -> Dict[str, Any]:

        """
        Create a backend-independent
        training job description.
        """

        if not base_model:

            raise ValueError(
                "base_model cannot be empty."
            )

        if not task_type:

            raise ValueError(
                "task_type cannot be empty."
            )

        return {

            "job_id":
                self._generate_job_id(
                    base_model,
                    task_type,
                    dataset_version,
                ),

            "base_model":
                base_model,

            "task_type":
                task_type,

            "dataset_version":
                dataset_version,

            "dataset_path":
                dataset_path,

            "created_at":
                datetime.now()
                .isoformat(),

            "status":
                "pending",

        }

    # ======================================================
    # RUN TRAINING JOB
    # ======================================================

    def train(
        self,
        job: Dict[str, Any],
    ) -> Dict[str, Any]:

        """
        Run a training job safely.
        """

        if not isinstance(
            job,
            dict,
        ):

            raise TypeError(
                "Training job must be a dictionary."
            )

        try:

            result = (
                self.backend.train(
                    job
                )
            )

        except Exception as exc:

            return {

                "success": False,

                "error":
                    str(exc),

                "artifact":
                    None,

            }

        # --------------------------------------------------
        # NORMALIZE RESULT
        # --------------------------------------------------

        if not isinstance(
            result,
            dict,
        ):

            return {

                "success": False,

                "error":
                    (
                        "Training backend returned "
                        "an invalid result."
                    ),

                "artifact":
                    None,

            }

        return result

    # ======================================================
    # JOB ID
    # ======================================================

    def _generate_job_id(
        self,
        base_model: str,
        task_type: str,
        dataset_version: Any,
    ) -> str:

        """
        Generate a unique training job ID.
        """

        source = (

            f"{base_model}|"
            f"{task_type}|"
            f"{dataset_version}|"
            f"{datetime.now().isoformat()}"

        )

        return (

            hashlib.sha256(

                source.encode(
                    "utf-8"
                )

            )
            .hexdigest()[:16]

        )


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNING TRAINER TEST"
    )

    print("=" * 60)

    # ------------------------------------------------------
    # SUCCESSFUL TRAINING
    # ------------------------------------------------------

    trainer = FineTuningTrainer()

    job = trainer.create_job(

        base_model="qwen3:4b",

        task_type="engineering",

        dataset_version=1,

        dataset_path=(
            "data/fine_tuning"
        ),

    )

    print()

    print(
        "TRAINING JOB"
    )

    print("-" * 60)

    print(job)

    result = trainer.train(
        job
    )

    print()

    print(
        "TRAINING RESULT"
    )

    print("-" * 60)

    print(result)

    # ------------------------------------------------------
    # FAILED TRAINING
    # ------------------------------------------------------

    failing_trainer = (

        FineTuningTrainer(

            backend=MockTrainer(
                should_fail=True
            )

        )

    )

    failed_result = (

        failing_trainer.train(
            job
        )

    )

    print()

    print(
        "FAILED TRAINING TEST"
    )

    print("-" * 60)

    print(failed_result)

    print()

    print("=" * 60)

    print(
        "TRAINER TEST COMPLETE"
    )

    print("=" * 60)