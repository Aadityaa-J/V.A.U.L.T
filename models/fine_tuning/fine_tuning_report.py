"""
V.A.U.L.T. Fine-Tuning Report

Generates a consolidated report for the
V.A.U.L.T. fine-tuning system.

Responsibilities:

    - Collect fine-tuning status
    - Collect dataset information
    - Collect health information
    - Collect diagnostics
    - Generate a consolidated system report
    - Keep reporting failures isolated
"""


from datetime import datetime
from typing import Any, Dict, Optional


from models.fine_tuning.pipeline_manager import (
    FineTuningPipelineManager,
)


# ==========================================================
# FINE-TUNING REPORT
# ==========================================================

class FineTuningReport:

    """
    Generate consolidated reports for the
    V.A.U.L.T. fine-tuning system.
    """

    def __init__(
        self,
        pipeline_manager: Optional[
            FineTuningPipelineManager
        ] = None,
    ):

        self.pipeline_manager = (

            pipeline_manager

            or FineTuningPipelineManager()

        )

        self.last_report: Optional[
            Dict[str, Any]
        ] = None


    # ======================================================
    # SAFE METHOD CALL
    # ======================================================

    @staticmethod
    def _safe_call(
        obj: Any,
        method_name: str,
    ) -> Dict[str, Any]:

        """
        Safely call a method.

        Reporting should never crash the
        V.A.U.L.T. runtime.
        """

        try:

            method = getattr(
                obj,
                method_name,
            )

            result = method()

            if isinstance(
                result,
                dict,
            ):

                return result

            return {

                "success": True,

                "result":
                    result,

            }

        except Exception as exc:

            return {

                "success": False,

                "error":
                    str(exc),

            }


    # ======================================================
    # DATASET REPORT
    # ======================================================

    def get_dataset_report(
        self,
    ) -> Dict[str, Any]:

        """
        Get dataset information.
        """

        try:

            dataset = (
                self.pipeline_manager.dataset
            )

            if hasattr(
                dataset,
                "get_info",
            ):

                return dataset.get_info()

            return {

                "success": False,

                "reason":
                    (
                        "Dataset does not "
                        "provide get_info()."
                    ),

            }

        except Exception as exc:

            return {

                "success": False,

                "error":
                    str(exc),

            }


    # ======================================================
    # PIPELINE REPORT
    # ======================================================

    def get_pipeline_report(
        self,
    ) -> Dict[str, Any]:

        """
        Get pipeline manager status.
        """

        return self._safe_call(

            self.pipeline_manager,

            "get_status",

        )


    # ======================================================
    # ELIGIBILITY REPORT
    # ======================================================

    def get_eligibility_report(
        self,
        task_type: str = "general",
    ) -> Dict[str, Any]:

        """
        Check fine-tuning eligibility.
        """

        try:

            return (

                self.pipeline_manager
                .check_eligibility(

                    task_type=task_type

                )

            )

        except Exception as exc:

            return {

                "eligible": False,

                "error":
                    str(exc),

            }


    # ======================================================
    # FULL REPORT
    # ======================================================

    def generate_report(
        self,
        task_type: str = "general",
    ) -> Dict[str, Any]:

        """
        Generate a complete fine-tuning
        system report.
        """

        report = {

            "generated_at":

                datetime.now()
                .isoformat(),

            "task_type":

                task_type,

            "dataset":

                self.get_dataset_report(),

            "pipeline":

                self.get_pipeline_report(),

            "eligibility":

                self.get_eligibility_report(

                    task_type=task_type

                ),

        }

        # --------------------------------------------------
        # SUMMARY
        # --------------------------------------------------

        dataset = report.get(

            "dataset",

            {},

        )

        pipeline = report.get(

            "pipeline",

            {},

        )

        eligibility = report.get(

            "eligibility",

            {},

        )

        report[

            "summary"

        ] = {

            "total_examples":

                dataset.get(

                    "total_examples",

                    pipeline.get(

                        "total_examples",

                        0,

                    ),

                ),

            "dataset_version":

                dataset.get(

                    "dataset_version",

                    1,

                ),

            "pipeline_running":

                pipeline.get(

                    "pipeline_running",

                    False,

                ),

            "eligible":

                eligibility.get(

                    "eligible",

                    False,

                ),

        }

        self.last_report = report

        return report


    # ======================================================
    # LAST REPORT
    # ======================================================

    def get_last_report(
        self,
    ) -> Optional[Dict[str, Any]]:

        """
        Return the most recently generated report.
        """

        return self.last_report


    # ======================================================
    # SIMPLE TEXT REPORT
    # ======================================================

    def generate_text_report(
        self,
        task_type: str = "general",
    ) -> str:

        """
        Generate a human-readable report.
        """

        report = (

            self.generate_report(

                task_type=task_type

            )

        )

        summary = report.get(

            "summary",

            {},

        )

        lines = [

            "=" * 60,

            "V.A.U.L.T. FINE-TUNING REPORT",

            "=" * 60,

            "",

            f"Generated At: "
            f"{report.get('generated_at')}",

            f"Task Type: "
            f"{report.get('task_type')}",

            "",

            "SYSTEM SUMMARY",

            "-" * 60,

            f"Total Examples: "
            f"{summary.get('total_examples')}",

            f"Dataset Version: "
            f"{summary.get('dataset_version')}",

            f"Pipeline Running: "
            f"{summary.get('pipeline_running')}",

            f"Eligible For Training: "
            f"{summary.get('eligible')}",

            "",

            "=" * 60,

        ]

        return "\n".join(
            lines
        )


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNING REPORT TEST"
    )

    print("=" * 60)

    report_generator = (

        FineTuningReport()

    )

    print()

    print(
        report_generator.generate_text_report()
    )

    print()

    print(
        "FULL REPORT:"
    )

    print(

        report_generator.generate_report()

    )

    print()

    print("=" * 60)

    print(
        "FINE-TUNING REPORT TEST COMPLETE"
    )

    print("=" * 60)