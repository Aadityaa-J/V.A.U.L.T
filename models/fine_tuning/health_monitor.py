"""
V.A.U.L.T. Fine-Tuning Health Monitor

Monitors the health of the fine-tuning system.

Responsibilities:

    - Check dataset health
    - Check pipeline status
    - Check integration status
    - Detect component failures
    - Provide an overall health report
    - Keep health monitoring isolated from the
      main V.A.U.L.T. runtime

The health monitor does not start training,
modify datasets, or deploy models.
"""


from datetime import datetime
from typing import Any, Dict, List, Optional


from models.fine_tuning.dataset import (
    FineTuningDataset,
)

from models.fine_tuning.pipeline_manager import (
    FineTuningPipelineManager,
)


# ==========================================================
# FINE-TUNING HEALTH MONITOR
# ==========================================================

class FineTuningHealthMonitor:

    """
    Monitor the health of the V.A.U.L.T.
    fine-tuning system.

    The monitor checks available components and
    returns a structured health report.
    """

    def __init__(
        self,
        dataset: Optional[
            FineTuningDataset
        ] = None,
        pipeline_manager: Optional[
            FineTuningPipelineManager
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
        # STATE
        # --------------------------------------------------

        self.last_report: Optional[
            Dict[str, Any]
        ] = None

        self.health_history: List[
            Dict[str, Any]
        ] = []

    # ======================================================
    # CHECK DATASET HEALTH
    # ======================================================

    def check_dataset_health(
        self,
    ) -> Dict[str, Any]:

        """
        Check whether the training dataset is
        accessible and functioning correctly.
        """

        try:

            info = (
                self.dataset.get_info()
            )

            example_count = (
                info.get(
                    "total_examples",
                    0,
                )
            )

            dataset_version = (
                info.get(
                    "dataset_version",
                    1,
                )
            )

            return {

                "healthy": True,

                "component":
                    "dataset",

                "example_count":
                    example_count,

                "dataset_version":
                    dataset_version,

                "storage_path":

                    info.get(
                        "storage_path"
                    ),

                "message":
                    "Dataset is healthy.",

            }

        except Exception as exc:

            return {

                "healthy": False,

                "component":
                    "dataset",

                "error":
                    str(exc),

                "message":
                    "Dataset health check failed.",

            }

    # ======================================================
    # CHECK PIPELINE HEALTH
    # ======================================================

    def check_pipeline_health(
        self,
    ) -> Dict[str, Any]:

        """
        Check whether the pipeline manager is
        functioning correctly.
        """

        try:

            status = (

                self.pipeline_manager
                .get_status()

            )

            pipeline_running = (

                status.get(

                    "pipeline_running",

                    False,

                )

            )

            total_examples = (

                status.get(

                    "total_examples",

                    0,

                )

            )

            dataset_version = (

                status.get(

                    "dataset_version",

                    1,

                )

            )

            return {

                "healthy": True,

                "component":
                    "pipeline",

                "pipeline_running":
                    pipeline_running,

                "total_examples":
                    total_examples,

                "dataset_version":
                    dataset_version,

                "pipeline_runs":

                    status.get(

                        "pipeline_runs",

                        0,

                    ),

                "message":
                    "Pipeline manager is healthy.",

            }

        except Exception as exc:

            return {

                "healthy": False,

                "component":
                    "pipeline",

                "error":
                    str(exc),

                "message":
                    (
                        "Pipeline health check "
                        "failed."
                    ),

            }

    # ======================================================
    # DETERMINE OVERALL HEALTH
    # ======================================================

    @staticmethod
    def _determine_status(
        checks: List[
            Dict[str, Any]
        ],
    ) -> str:

        """
        Determine the overall system status.
        """

        if not checks:

            return "unknown"

        unhealthy_count = sum(

            1

            for check in checks

            if not check.get(
                "healthy",
                False,
            )

        )

        if unhealthy_count == 0:

            return "healthy"

        if unhealthy_count == len(
            checks
        ):

            return "critical"

        return "degraded"

    # ======================================================
    # RUN HEALTH CHECK
    # ======================================================

    def check_health(
        self,
    ) -> Dict[str, Any]:

        """
        Run a complete fine-tuning health check.
        """

        checked_at = (

            datetime.now()
            .isoformat()

        )

        # --------------------------------------------------
        # DATASET CHECK
        # --------------------------------------------------

        dataset_check = (

            self.check_dataset_health()

        )

        # --------------------------------------------------
        # PIPELINE CHECK
        # --------------------------------------------------

        pipeline_check = (

            self.check_pipeline_health()

        )

        checks = [

            dataset_check,

            pipeline_check,

        ]

        # --------------------------------------------------
        # OVERALL STATUS
        # --------------------------------------------------

        status = (

            self._determine_status(
                checks
            )

        )

        healthy_components = sum(

            1

            for check in checks

            if check.get(
                "healthy",
                False,
            )

        )

        unhealthy_components = (

            len(checks)

            -

            healthy_components

        )

        report = {

            "status":
                status,

            "healthy":

                status == "healthy",

            "checked_at":
                checked_at,

            "total_components":
                len(checks),

            "healthy_components":
                healthy_components,

            "unhealthy_components":
                unhealthy_components,

            "checks":

                {

                    "dataset":
                        dataset_check,

                    "pipeline":
                        pipeline_check,

                },

        }

        # --------------------------------------------------
        # STORE REPORT
        # --------------------------------------------------

        self.last_report = report

        self.health_history.append(
            report
        )

        return report

    # ======================================================
    # GET LAST REPORT
    # ======================================================

    def get_last_report(
        self,
    ) -> Optional[
        Dict[str, Any]
    ]:

        """
        Return the most recent health report.
        """

        return self.last_report

    # ======================================================
    # GET HEALTH HISTORY
    # ======================================================

    def get_history(
        self,
        limit: Optional[
            int
        ] = None,
    ) -> List[
        Dict[str, Any]
    ]:

        """
        Return health check history.
        """

        history = list(
            self.health_history
        )

        if limit is None:

            return history

        try:

            limit = int(
                limit
            )

        except (

            TypeError,

            ValueError,

        ):

            return history

        if limit <= 0:

            return []

        return history[
            -limit:
        ]

    # ======================================================
    # GET SUMMARY
    # ======================================================

    def get_summary(
        self,
    ) -> Dict[str, Any]:

        """
        Return a compact health summary.
        """

        report = (

            self.last_report

            or

            self.check_health()

        )

        return {

            "status":
                report.get(
                    "status"
                ),

            "healthy":
                report.get(
                    "healthy"
                ),

            "checked_at":
                report.get(
                    "checked_at"
                ),

            "healthy_components":
                report.get(
                    "healthy_components"
                ),

            "unhealthy_components":
                report.get(
                    "unhealthy_components"
                ),

        }


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNING HEALTH MONITOR TEST"
    )

    print("=" * 60)

    # ======================================================
    # CREATE MONITOR
    # ======================================================

    monitor = (

        FineTuningHealthMonitor()

    )

    # ======================================================
    # TEST 1
    # COMPLETE HEALTH CHECK
    # ======================================================

    print()

    print(
        "TEST 1: COMPLETE HEALTH CHECK"
    )

    print("-" * 60)

    result = (

        monitor.check_health()

    )

    print(
        result
    )

    # ======================================================
    # TEST 2
    # HEALTH SUMMARY
    # ======================================================

    print()

    print(
        "TEST 2: HEALTH SUMMARY"
    )

    print("-" * 60)

    print(

        monitor.get_summary()

    )

    # ======================================================
    # TEST 3
    # LAST REPORT
    # ======================================================

    print()

    print(
        "TEST 3: LAST REPORT"
    )

    print("-" * 60)

    print(

        monitor.get_last_report()

    )

    # ======================================================
    # TEST 4
    # HEALTH HISTORY
    # ======================================================

    print()

    print(
        "TEST 4: HEALTH HISTORY"
    )

    print("-" * 60)

    print(

        monitor.get_history()

    )

    print()

    print("=" * 60)

    print(
        "FINE-TUNING HEALTH MONITOR TEST COMPLETE"
    )

    print("=" * 60)