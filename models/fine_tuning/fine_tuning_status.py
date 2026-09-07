"""
V.A.U.L.T. Fine-Tuning Status

Provides a centralized status interface for the
V.A.U.L.T. fine-tuning system.

Responsibilities:

    - Report dataset status
    - Report pipeline status
    - Report system health
    - Report training activity
    - Report recent errors
    - Provide a single status snapshot

This module does not modify the dataset, start
training, or deploy models.
"""


from datetime import datetime
from typing import Any, Dict, Optional


from models.fine_tuning.dataset import (
    FineTuningDataset,
)

from models.fine_tuning.pipeline_manager import (
    FineTuningPipelineManager,
)

from models.fine_tuning.health_monitor import (
    FineTuningHealthMonitor,
)


# ==========================================================
# FINE-TUNING STATUS
# ==========================================================

class FineTuningStatus:

    """
    Centralized status provider for the V.A.U.L.T.
    fine-tuning system.
    """

    def __init__(
        self,
        dataset: Optional[
            FineTuningDataset
        ] = None,
        pipeline_manager: Optional[
            FineTuningPipelineManager
        ] = None,
        health_monitor: Optional[
            FineTuningHealthMonitor
        ] = None,
    ):

        # --------------------------------------------------
        # DATASET
        # --------------------------------------------------

        self.dataset = (
            dataset
            or FineTuningDataset()
        )

        # --------------------------------------------------
        # PIPELINE MANAGER
        # --------------------------------------------------

        self.pipeline_manager = (
            pipeline_manager
            or FineTuningPipelineManager(
                dataset=self.dataset
            )
        )

        # --------------------------------------------------
        # HEALTH MONITOR
        # --------------------------------------------------

        self.health_monitor = (
            health_monitor
            or FineTuningHealthMonitor(
                dataset=self.dataset,
                pipeline_manager=(
                    self.pipeline_manager
                ),
            )
        )

        # --------------------------------------------------
        # STATE
        # --------------------------------------------------

        self.last_status: Optional[
            Dict[str, Any]
        ] = None

    # ======================================================
    # DATASET STATUS
    # ======================================================

    def get_dataset_status(
        self,
    ) -> Dict[str, Any]:

        """
        Return the current dataset status.
        """

        try:

            info = (
                self.dataset.get_info()
            )

            return {

                "available": True,

                "dataset_version":

                    info.get(
                        "dataset_version",
                        1,
                    ),

                "total_examples":

                    info.get(
                        "total_examples",
                        0,
                    ),

                "storage_path":

                    info.get(
                        "storage_path"
                    ),

                "created_at":

                    info.get(
                        "created_at"
                    ),

                "updated_at":

                    info.get(
                        "updated_at"
                    ),

            }

        except Exception as exc:

            return {

                "available": False,

                "error":
                    str(exc),

            }

    # ======================================================
    # PIPELINE STATUS
    # ======================================================

    def get_pipeline_status(
        self,
    ) -> Dict[str, Any]:

        """
        Return the current pipeline status.
        """

        try:

            status = (

                self.pipeline_manager
                .get_status()

            )

            return {

                "available": True,

                "pipeline_running":

                    status.get(
                        "pipeline_running",
                        False,
                    ),

                "pipeline_runs":

                    status.get(
                        "pipeline_runs",
                        0,
                    ),

                "last_result":

                    status.get(
                        "last_result"
                    ),

                "total_examples":

                    status.get(
                        "total_examples",
                        0,
                    ),

                "dataset_version":

                    status.get(
                        "dataset_version",
                        1,
                    ),

            }

        except Exception as exc:

            return {

                "available": False,

                "error":
                    str(exc),

            }

    # ======================================================
    # HEALTH STATUS
    # ======================================================

    def get_health_status(
        self,
    ) -> Dict[str, Any]:

        """
        Run and return a fine-tuning health check.
        """

        try:

            return (

                self.health_monitor
                .check_health()

            )

        except Exception as exc:

            return {

                "status":
                    "unknown",

                "healthy":
                    False,

                "error":
                    str(exc),

            }

    # ======================================================
    # LAST TRAINING STATUS
    # ======================================================

    def get_last_training_status(
        self,
    ) -> Dict[str, Any]:

        """
        Return information about the most recent
        pipeline execution.
        """

        try:

            last_result = (

                self.pipeline_manager
                .get_last_result()

            )

            if not last_result:

                return {

                    "available": False,

                    "message":
                        (
                            "No fine-tuning pipeline "
                            "has been executed yet."
                        ),

                }

            return {

                "available": True,

                "success":

                    last_result.get(
                        "success",
                        False,
                    ),

                "stage":

                    last_result.get(
                        "stage"
                    ),

                "reason":

                    last_result.get(
                        "reason"
                    ),

                "started_at":

                    last_result.get(
                        "started_at"
                    ),

                "completed_at":

                    last_result.get(
                        "completed_at"
                    ),

                "task_type":

                    last_result.get(
                        "task_type"
                    ),

            }

        except Exception as exc:

            return {

                "available": False,

                "error":
                    str(exc),

            }

    # ======================================================
    # COMPLETE STATUS
    # ======================================================

    def get_status(
        self,
        include_health: bool = True,
    ) -> Dict[str, Any]:

        """
        Return a complete fine-tuning system
        status snapshot.
        """

        generated_at = (

            datetime.now()
            .isoformat()

        )

        # --------------------------------------------------
        # DATASET
        # --------------------------------------------------

        dataset_status = (

            self.get_dataset_status()

        )

        # --------------------------------------------------
        # PIPELINE
        # --------------------------------------------------

        pipeline_status = (

            self.get_pipeline_status()

        )

        # --------------------------------------------------
        # LAST TRAINING
        # --------------------------------------------------

        training_status = (

            self.get_last_training_status()

        )

        # --------------------------------------------------
        # BUILD RESULT
        # --------------------------------------------------

        result = {

            "generated_at":
                generated_at,

            "dataset":
                dataset_status,

            "pipeline":
                pipeline_status,

            "last_training":
                training_status,

        }

        # --------------------------------------------------
        # OPTIONAL HEALTH CHECK
        # --------------------------------------------------

        if include_health:

            result[
                "health"
            ] = (

                self.get_health_status()

            )

        self.last_status = result

        return result

    # ======================================================
    # QUICK STATUS
    # ======================================================

    def get_quick_status(
        self,
    ) -> Dict[str, Any]:

        """
        Return a lightweight status summary.
        """

        try:

            dataset_info = (
                self.dataset.get_info()
            )

        except Exception:

            dataset_info = {}

        try:

            pipeline_info = (

                self.pipeline_manager
                .get_status()

            )

        except Exception:

            pipeline_info = {}

        return {

            "total_examples":

                dataset_info.get(
                    "total_examples",
                    0,
                ),

            "dataset_version":

                dataset_info.get(
                    "dataset_version",
                    1,
                ),

            "pipeline_running":

                pipeline_info.get(
                    "pipeline_running",
                    False,
                ),

            "pipeline_runs":

                pipeline_info.get(
                    "pipeline_runs",
                    0,
                ),

        }

    # ======================================================
    # GET LAST STATUS
    # ======================================================

    def get_last_status(
        self,
    ) -> Optional[
        Dict[str, Any]
    ]:

        """
        Return the last generated status snapshot.
        """

        return self.last_status


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNING STATUS TEST"
    )

    print("=" * 60)

    # ======================================================
    # CREATE STATUS PROVIDER
    # ======================================================

    status_provider = (

        FineTuningStatus()

    )

    # ======================================================
    # TEST 1
    # QUICK STATUS
    # ======================================================

    print()

    print(
        "TEST 1: QUICK STATUS"
    )

    print("-" * 60)

    print(

        status_provider
        .get_quick_status()

    )

    # ======================================================
    # TEST 2
    # DATASET STATUS
    # ======================================================

    print()

    print(
        "TEST 2: DATASET STATUS"
    )

    print("-" * 60)

    print(

        status_provider
        .get_dataset_status()

    )

    # ======================================================
    # TEST 3
    # PIPELINE STATUS
    # ======================================================

    print()

    print(
        "TEST 3: PIPELINE STATUS"
    )

    print("-" * 60)

    print(

        status_provider
        .get_pipeline_status()

    )

    # ======================================================
    # TEST 4
    # LAST TRAINING STATUS
    # ======================================================

    print()

    print(
        "TEST 4: LAST TRAINING STATUS"
    )

    print("-" * 60)

    print(

        status_provider
        .get_last_training_status()

    )

    # ======================================================
    # TEST 5
    # COMPLETE STATUS
    # ======================================================

    print()

    print(
        "TEST 5: COMPLETE STATUS"
    )

    print("-" * 60)

    print(

        status_provider
        .get_status()

    )

    print()

    print("=" * 60)

    print(
        "FINE-TUNING STATUS TEST COMPLETE"
    )

    print("=" * 60)