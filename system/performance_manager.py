"""
V.A.U.L.T. Performance Manager

Responsible for:

- Monitoring system performance
- Evaluating resource pressure
- Recommending model sizes
- Determining whether heavy tasks should run
- Providing performance recommendations
"""

from typing import Any, Dict, Optional

from system.resource_manager import ResourceManager
from system.vram_manager import VRAMManager


class PerformanceManager:

    # ======================================================
    # PERFORMANCE LEVELS
    # ======================================================

    PERFORMANCE_LEVELS = {
        "healthy": "high",
        "warning": "medium",
        "critical": "low",
    }

    def __init__(
        self,
        resource_manager: Optional[
            ResourceManager
        ] = None,
        vram_manager: Optional[
            VRAMManager
        ] = None,
    ):

        self.resource_manager = (
            resource_manager
            or ResourceManager()
        )

        self.vram_manager = (
            vram_manager
            or VRAMManager()
        )

    # ======================================================
    # SYSTEM STATUS
    # ======================================================

    def get_system_status(self) -> str:

        return (
            self.resource_manager
            .get_system_load()
        )

    # ======================================================
    # PERFORMANCE LEVEL
    # ======================================================

    def get_performance_level(self) -> str:

        system_status = (
            self.get_system_status()
        )

        return (
            self.PERFORMANCE_LEVELS.get(
                system_status,
                "low",
            )
        )

    # ======================================================
    # MODEL RECOMMENDATION
    # ======================================================

    def get_model_recommendation(
        self,
    ) -> str:

        system_status = (
            self.get_system_status()
        )

        # --------------------------------------------------
        # CRITICAL
        # --------------------------------------------------

        if system_status == "critical":

            return "small"

        # --------------------------------------------------
        # WARNING
        # --------------------------------------------------

        if system_status == "warning":

            return "medium"

        # --------------------------------------------------
        # HEALTHY
        # --------------------------------------------------

        return "large"

    # ======================================================
    # HEAVY TASK CHECK
    # ======================================================

    def can_run_heavy_task(
        self,
    ) -> bool:

        system_status = (
            self.get_system_status()
        )

        if system_status == "critical":

            return False

        # Check available GPU VRAM if GPU exists.

        if self.vram_manager.has_gpu():

            free_vram = (
                self.vram_manager
                .get_free_vram_mb()
            )

            # Require at least 1 GB free VRAM
            # for heavy tasks.

            if free_vram < 1024:

                return False

        return True

    # ======================================================
    # PERFORMANCE SNAPSHOT
    # ======================================================

    def get_performance_snapshot(
        self,
    ) -> Dict[str, Any]:

        resource_snapshot = (
            self.resource_manager
            .get_resource_snapshot()
        )

        system_status = (
            resource_snapshot.get(
                "overall_status",
                "unknown",
            )
        )

        return {

            "system_status":
                system_status,

            "performance_level":
                self.get_performance_level(),

            "model_recommendation":
                self.get_model_recommendation(),

            "can_run_heavy_task":
                self.can_run_heavy_task(),

            "cpu":
                resource_snapshot.get(
                    "cpu",
                    {},
                ),

            "ram":
                resource_snapshot.get(
                    "ram",
                    {},
                ),

            "vram":
                resource_snapshot.get(
                    "vram",
                    {},
                ),

        }

    # ======================================================
    # PERFORMANCE RECOMMENDATION
    # ======================================================

    def get_recommendation(
        self,
    ) -> str:

        snapshot = (
            self.get_performance_snapshot()
        )

        system_status = (
            snapshot[
                "system_status"
            ]
        )

        if system_status == "critical":

            return (
                "System resources are critical. "
                "Use the smallest model and avoid "
                "heavy tasks."
            )

        if system_status == "warning":

            return (
                "System resources are elevated. "
                "Prefer smaller or medium models "
                "for better stability."
            )

        return (
            "System performance is healthy. "
            "All configured models can be used "
            "normally."
        )

    # ======================================================
    # PRINT REPORT
    # ======================================================

    def print_report(
        self,
    ) -> None:

        snapshot = (
            self.get_performance_snapshot()
        )

        print()

        print("=" * 60)
        print(
            "V.A.U.L.T. PERFORMANCE MANAGER"
        )
        print("=" * 60)

        print()

        print(
            "SYSTEM STATUS"
        )

        print("-" * 60)

        print(
            snapshot[
                "system_status"
            ].upper()
        )

        print()

        print(
            "PERFORMANCE LEVEL"
        )

        print("-" * 60)

        print(
            snapshot[
                "performance_level"
            ].upper()
        )

        print()

        print(
            "MODEL RECOMMENDATION"
        )

        print("-" * 60)

        print(
            snapshot[
                "model_recommendation"
            ].upper()
        )

        print()

        print(
            "HEAVY TASK SUPPORT"
        )

        print("-" * 60)

        print(
            snapshot[
                "can_run_heavy_task"
            ]
        )

        print()

        print(
            "RECOMMENDATION"
        )

        print("-" * 60)

        print(
            self.get_recommendation()
        )

        print()

        print("=" * 60)
        print(
            "PERFORMANCE MANAGER TEST COMPLETE"
        )
        print("=" * 60)


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    manager = PerformanceManager()

    manager.print_report()