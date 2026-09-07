"""
V.A.U.L.T. Fine-Tuning Diagnostics

Performs diagnostic checks on the V.A.U.L.T.
fine-tuning system.

Responsibilities:

    - Check dataset availability
    - Check dataset contents
    - Check pipeline manager health
    - Inspect recent pipeline results
    - Detect failed components
    - Detect configuration problems
    - Produce diagnostic reports

Diagnostics never starts training, modifies the
dataset, registers models, or deploys models.
"""


from datetime import datetime
from typing import Any, Dict, List, Optional


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
# FINE-TUNING DIAGNOSTICS
# ==========================================================

class FineTuningDiagnostics:

    """
    Perform diagnostics on the V.A.U.L.T.
    fine-tuning system.

    This component is read-only and should never
    modify training data or start a training job.
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

        self.last_report: Optional[
            Dict[str, Any]
        ] = None

        self.diagnostic_history: List[
            Dict[str, Any]
        ] = []

    # ======================================================
    # DATASET DIAGNOSTICS
    # ======================================================

    def diagnose_dataset(
        self,
    ) -> Dict[str, Any]:

        """
        Diagnose the fine-tuning dataset.
        """

        issues = []

        try:

            info = (
                self.dataset.get_info()
            )

            example_count = int(

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

            storage_path = (

                info.get(
                    "storage_path"
                )

            )

            # --------------------------------------------------
            # EMPTY DATASET
            # --------------------------------------------------

            if example_count == 0:

                issues.append(

                    "Dataset contains no "
                    "training examples."

                )

            # --------------------------------------------------
            # INVALID VERSION
            # --------------------------------------------------

            if not isinstance(
                dataset_version,
                int,
            ):

                issues.append(

                    "Dataset version is invalid."

                )

            healthy = (

                len(issues) == 0

            )

            return {

                "healthy":
                    healthy,

                "component":
                    "dataset",

                "example_count":
                    example_count,

                "dataset_version":
                    dataset_version,

                "storage_path":
                    storage_path,

                "issues":
                    issues,

            }

        except Exception as exc:

            return {

                "healthy":
                    False,

                "component":
                    "dataset",

                "issues":

                    [

                        str(exc)

                    ],

            }

    # ======================================================
    # PIPELINE DIAGNOSTICS
    # ======================================================

    def diagnose_pipeline(
        self,
    ) -> Dict[str, Any]:

        """
        Diagnose the fine-tuning pipeline manager.
        """

        issues = []

        try:

            status = (

                self.pipeline_manager
                .get_status()

            )

            running = bool(

                status.get(
                    "pipeline_running",
                    False,
                )

            )

            pipeline_runs = int(

                status.get(
                    "pipeline_runs",
                    0,
                )

            )

            last_result = (

                status.get(
                    "last_result"
                )

            )

            # --------------------------------------------------
            # LAST PIPELINE FAILURE
            # --------------------------------------------------

            if isinstance(
                last_result,
                dict,
            ):

                if not last_result.get(
                    "success",
                    False,
                ):

                    issues.append(

                        "The most recent "
                        "pipeline execution failed."

                    )

            healthy = (

                len(issues) == 0

            )

            return {

                "healthy":
                    healthy,

                "component":
                    "pipeline",

                "pipeline_running":
                    running,

                "pipeline_runs":
                    pipeline_runs,

                "last_result":
                    last_result,

                "issues":
                    issues,

            }

        except Exception as exc:

            return {

                "healthy":
                    False,

                "component":
                    "pipeline",

                "issues":

                    [

                        str(exc)

                    ],

            }

    # ======================================================
    # HEALTH MONITOR DIAGNOSTICS
    # ======================================================

    def diagnose_health_monitor(
        self,
    ) -> Dict[str, Any]:

        """
        Run the health monitor and inspect its
        result.
        """

        try:

            health = (

                self.health_monitor
                .check_health()

            )

            healthy = bool(

                health.get(
                    "healthy",
                    False,
                )

            )

            issues = []

            if not healthy:

                issues.append(

                    "Fine-tuning system health "
                    "monitor reported a problem."

                )

            return {

                "healthy":
                    healthy,

                "component":
                    "health_monitor",

                "status":

                    health.get(
                        "status",
                        "unknown",
                    ),

                "health_report":
                    health,

                "issues":
                    issues,

            }

        except Exception as exc:

            return {

                "healthy":
                    False,

                "component":
                    "health_monitor",

                "issues":

                    [

                        str(exc)

                    ],

            }

    # ======================================================
    # DETERMINE DIAGNOSTIC STATUS
    # ======================================================

    @staticmethod
    def _determine_status(
        checks: List[
            Dict[str, Any]
        ],
    ) -> str:

        """
        Determine the overall diagnostic status.
        """

        if not checks:

            return "unknown"

        failed = sum(

            1

            for check in checks

            if not check.get(
                "healthy",
                False,
            )

        )

        if failed == 0:

            return "healthy"

        if failed == len(checks):

            return "critical"

        return "warning"

    # ======================================================
    # RUN DIAGNOSTICS
    # ======================================================

    def run_diagnostics(
        self,
    ) -> Dict[str, Any]:

        """
        Run all fine-tuning diagnostic checks.
        """

        started_at = (

            datetime.now()
            .isoformat()

        )

        # --------------------------------------------------
        # DATASET
        # --------------------------------------------------

        dataset_check = (

            self.diagnose_dataset()

        )

        # --------------------------------------------------
        # PIPELINE
        # --------------------------------------------------

        pipeline_check = (

            self.diagnose_pipeline()

        )

        # --------------------------------------------------
        # HEALTH MONITOR
        # --------------------------------------------------

        health_check = (

            self.diagnose_health_monitor()

        )

        checks = [

            dataset_check,

            pipeline_check,

            health_check,

        ]

        # --------------------------------------------------
        # OVERALL STATUS
        # --------------------------------------------------

        status = (

            self._determine_status(
                checks
            )

        )

        issues = []

        for check in checks:

            check_issues = (

                check.get(
                    "issues",
                    [],
                )

            )

            if isinstance(
                check_issues,
                list,
            ):

                issues.extend(
                    check_issues
                )

        healthy_components = sum(

            1

            for check in checks

            if check.get(
                "healthy",
                False,
            )

        )

        report = {

            "status":
                status,

            "healthy":

                status == "healthy",

            "started_at":
                started_at,

            "completed_at":

                datetime.now()
                .isoformat(),

            "total_checks":
                len(checks),

            "healthy_checks":
                healthy_components,

            "failed_checks":

                len(checks)

                -

                healthy_components,

            "issue_count":
                len(issues),

            "issues":
                issues,

            "checks":

                {

                    "dataset":
                        dataset_check,

                    "pipeline":
                        pipeline_check,

                    "health_monitor":
                        health_check,

                },

        }

        # --------------------------------------------------
        # STORE REPORT
        # --------------------------------------------------

        self.last_report = report

        self.diagnostic_history.append(
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
        Return the most recent diagnostic report.
        """

        return self.last_report

    # ======================================================
    # GET HISTORY
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
        Return diagnostic history.
        """

        history = list(
            self.diagnostic_history
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
        Return a compact diagnostic summary.
        """

        report = (

            self.last_report

            or

            self.run_diagnostics()

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

            "issue_count":
                report.get(
                    "issue_count",
                    0,
                ),

            "healthy_checks":
                report.get(
                    "healthy_checks",
                    0,
                ),

            "failed_checks":
                report.get(
                    "failed_checks",
                    0,
                ),

        }


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNING DIAGNOSTICS TEST"
    )

    print("=" * 60)

    # ======================================================
    # CREATE DIAGNOSTICS
    # ======================================================

    diagnostics = (

        FineTuningDiagnostics()

    )

    # ======================================================
    # TEST 1
    # DATASET DIAGNOSTICS
    # ======================================================

    print()

    print(
        "TEST 1: DATASET DIAGNOSTICS"
    )

    print("-" * 60)

    print(

        diagnostics
        .diagnose_dataset()

    )

    # ======================================================
    # TEST 2
    # PIPELINE DIAGNOSTICS
    # ======================================================

    print()

    print(
        "TEST 2: PIPELINE DIAGNOSTICS"
    )

    print("-" * 60)

    print(

        diagnostics
        .diagnose_pipeline()

    )

    # ======================================================
    # TEST 3
    # COMPLETE DIAGNOSTICS
    # ======================================================

    print()

    print(
        "TEST 3: COMPLETE DIAGNOSTICS"
    )

    print("-" * 60)

    print(

        diagnostics
        .run_diagnostics()

    )

    # ======================================================
    # TEST 4
    # DIAGNOSTIC SUMMARY
    # ======================================================

    print()

    print(
        "TEST 4: DIAGNOSTIC SUMMARY"
    )

    print("-" * 60)

    print(

        diagnostics
        .get_summary()

    )

    # ======================================================
    # TEST 5
    # DIAGNOSTIC HISTORY
    # ======================================================

    print()

    print(
        "TEST 5: DIAGNOSTIC HISTORY"
    )

    print("-" * 60)

    print(

        diagnostics
        .get_history()

    )

    print()

    print("=" * 60)

    print(
        "FINE-TUNING DIAGNOSTICS TEST COMPLETE"
    )

    print("=" * 60)