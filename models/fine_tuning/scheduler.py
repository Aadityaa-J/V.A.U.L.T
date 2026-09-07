"""
V.A.U.L.T. Fine-Tuning Scheduler

Responsible for deciding whether an automatic
fine-tuning job should start.

The scheduler checks:

- Overnight time window
- Number of available training examples
- Resource availability
- Heavy task support

This module does NOT perform training.

It only decides whether training is currently
appropriate.
"""

from datetime import datetime
from typing import Any, Dict, Optional


# ==========================================================
# OPTIONAL SYSTEM IMPORTS
# ==========================================================

try:

    from system.performance_manager import (
        PerformanceManager,
    )

except Exception:

    PerformanceManager = None


try:

    from system.resource_manager import (
        ResourceManager,
    )

except Exception:

    ResourceManager = None


# ==========================================================
# FINE-TUNING SCHEDULER
# ==========================================================

class FineTuningScheduler:

    """
    Decide whether fine-tuning should run.

    The scheduler automatically attempts to use
    V.A.U.L.T.'s existing PerformanceManager.

    If PerformanceManager cannot be initialized,
    ResourceManager is used as a fallback.

    Training is normally restricted to the
    configured overnight window.

    The force parameter can be used for explicit
    development and pipeline testing.
    """

    def __init__(
        self,
        resource_manager=None,
        performance_manager=None,
        minimum_examples: int = 10,
        overnight_start_hour: int = 0,
        overnight_end_hour: int = 6,
    ):

        # --------------------------------------------------
        # RESOURCE MANAGER
        # --------------------------------------------------

        self.resource_manager = (
            resource_manager
        )

        # --------------------------------------------------
        # PERFORMANCE MANAGER
        # --------------------------------------------------

        self.performance_manager = (
            performance_manager
        )

        # --------------------------------------------------
        # AUTOMATIC PERFORMANCE MANAGER
        # --------------------------------------------------

        if (
            self.performance_manager is None
            and PerformanceManager is not None
        ):

            try:

                self.performance_manager = (
                    PerformanceManager()
                )

            except Exception:

                self.performance_manager = None

        # --------------------------------------------------
        # AUTOMATIC RESOURCE MANAGER
        # --------------------------------------------------

        if (
            self.resource_manager is None
            and self.performance_manager is None
            and ResourceManager is not None
        ):

            try:

                self.resource_manager = (
                    ResourceManager()
                )

            except Exception:

                self.resource_manager = None

        # --------------------------------------------------
        # CONFIGURATION
        # --------------------------------------------------

        self.minimum_examples = (
            minimum_examples
        )

        self.overnight_start_hour = (
            overnight_start_hour
        )

        self.overnight_end_hour = (
            overnight_end_hour
        )

    # ======================================================
    # OVERNIGHT CHECK
    # ======================================================

    def is_overnight(
        self,
        current_time: Optional[
            datetime
        ] = None,
    ) -> bool:

        """
        Determine whether the current time is
        inside the configured overnight window.
        """

        if current_time is None:

            current_time = datetime.now()

        hour = current_time.hour

        start = (
            self.overnight_start_hour
        )

        end = (
            self.overnight_end_hour
        )

        # --------------------------------------------------
        # ALL-DAY WINDOW
        # --------------------------------------------------

        if start == end:

            return True

        # --------------------------------------------------
        # WINDOW DOES NOT CROSS MIDNIGHT
        # --------------------------------------------------

        if start < end:

            return (

                start <= hour < end

            )

        # --------------------------------------------------
        # WINDOW CROSSES MIDNIGHT
        # --------------------------------------------------

        return (

            hour >= start

            or

            hour < end

        )

    # ======================================================
    # DATASET CHECK
    # ======================================================

    def has_enough_examples(
        self,
        example_count: int,
    ) -> bool:

        """
        Check whether enough examples exist
        to justify fine-tuning.
        """

        if not isinstance(
            example_count,
            int,
        ):

            return False

        if example_count < 0:

            return False

        return (

            example_count
            >=
            self.minimum_examples

        )

    # ======================================================
    # RESOURCE STATUS
    # ======================================================

    def get_resource_status(
        self,
    ) -> Dict[str, Any]:

        """
        Return information about the resource
        system currently available to the scheduler.
        """

        # --------------------------------------------------
        # PERFORMANCE MANAGER
        # --------------------------------------------------

        if self.performance_manager is not None:

            try:

                system_status = None

                if hasattr(
                    self.performance_manager,
                    "get_system_status",
                ):

                    system_status = (

                        self.performance_manager
                        .get_system_status()

                    )

                can_run = (

                    self.performance_manager
                    .can_run_heavy_task()

                )

                return {

                    "available": True,

                    "manager":
                        "performance_manager",

                    "system_status":
                        system_status,

                    "can_run_heavy_task":
                        bool(can_run),

                }

            except Exception as exc:

                return {

                    "available": False,

                    "manager":
                        "performance_manager",

                    "error":
                        str(exc),

                    "can_run_heavy_task":
                        False,

                }

        # --------------------------------------------------
        # RESOURCE MANAGER
        # --------------------------------------------------

        if self.resource_manager is not None:

            try:

                system_status = (

                    self.resource_manager
                    .get_system_load()

                )

                if hasattr(
                    self.resource_manager,
                    "can_run_heavy_task",
                ):

                    can_run = (

                        self.resource_manager
                        .can_run_heavy_task()

                    )

                else:

                    can_run = (

                        system_status
                        !=
                        "critical"

                    )

                return {

                    "available": True,

                    "manager":
                        "resource_manager",

                    "system_status":
                        system_status,

                    "can_run_heavy_task":
                        bool(can_run),

                }

            except Exception as exc:

                return {

                    "available": False,

                    "manager":
                        "resource_manager",

                    "error":
                        str(exc),

                    "can_run_heavy_task":
                        False,

                }

        # --------------------------------------------------
        # NO RESOURCE SYSTEM
        # --------------------------------------------------

        return {

            "available": False,

            "manager": None,

            "system_status": None,

            "can_run_heavy_task": False,

        }

    # ======================================================
    # RESOURCE CHECK
    # ======================================================

    def resources_available(
        self,
    ) -> bool:

        """
        Check whether the existing V.A.U.L.T.
        performance/resource management system
        considers training safe.
        """

        resource_status = (

            self.get_resource_status()

        )

        return bool(

            resource_status.get(
                "can_run_heavy_task",
                False,
            )

        )

    # ======================================================
    # MAIN SCHEDULING DECISION
    # ======================================================

    def should_train(
        self,
        example_count: int,
        current_time: Optional[
            datetime
        ] = None,
        force: bool = False,
    ) -> Dict[str, Any]:

        """
        Determine whether fine-tuning should start.

        Parameters:

            example_count:
                Number of available examples.

            current_time:
                Optional time override used for
                deterministic testing.

            force:
                Explicit development override.

                When True, the overnight time
                restriction is bypassed.

                Dataset and resource safety checks
                are still enforced.

        Returns:

        {
            "should_train": bool,
            "reason": str,
            "example_count": int,
            "minimum_examples": int,
            "force": bool,
            "resource_status": dict
        }
        """

        # --------------------------------------------------
        # CHECK DATASET
        # --------------------------------------------------

        if not self.has_enough_examples(
            example_count
        ):

            return {

                "should_train": False,

                "reason":
                    (
                        "Not enough training "
                        "examples."
                    ),

                "example_count":
                    example_count,

                "minimum_examples":
                    self.minimum_examples,

                "force":
                    force,

            }

        # --------------------------------------------------
        # CHECK TIME WINDOW
        # --------------------------------------------------

        if not force:

            if not self.is_overnight(
                current_time
            ):

                return {

                    "should_train": False,

                    "reason":
                        (
                            "Outside overnight "
                            "training window."
                        ),

                    "example_count":
                        example_count,

                    "minimum_examples":
                        self.minimum_examples,

                    "force":
                        False,

                }

        # --------------------------------------------------
        # CHECK RESOURCES
        # --------------------------------------------------

        resource_status = (

            self.get_resource_status()

        )

        if not resource_status.get(
            "can_run_heavy_task",
            False,
        ):

            return {

                "should_train": False,

                "reason":
                    (
                        "Insufficient system "
                        "resources for training."
                    ),

                "example_count":
                    example_count,

                "minimum_examples":
                    self.minimum_examples,

                "force":
                    force,

                "resource_status":
                    resource_status,

            }

        # --------------------------------------------------
        # APPROVED
        # --------------------------------------------------

        if force:

            reason = (

                "Training approved using explicit "
                "development override. Dataset and "
                "resource safety checks passed."

            )

        else:

            reason = (

                "Overnight window active, enough "
                "training examples available, and "
                "resources are sufficient."

            )

        return {

            "should_train": True,

            "reason":
                reason,

            "example_count":
                example_count,

            "minimum_examples":
                self.minimum_examples,

            "force":
                force,

            "resource_status":
                resource_status,

        }

    # ======================================================
    # STATUS
    # ======================================================

    def get_status(
        self,
    ) -> Dict[str, Any]:

        """
        Return scheduler configuration and
        resource availability information.
        """

        return {

            "minimum_examples":
                self.minimum_examples,

            "overnight_start_hour":
                self.overnight_start_hour,

            "overnight_end_hour":
                self.overnight_end_hour,

            "resource_status":
                self.get_resource_status(),

        }


# ==========================================================
# MOCK PERFORMANCE MANAGER
# ==========================================================

class MockPerformanceManager:

    """
    Used only for development testing.

    This allows scheduler testing without
    depending on actual hardware resources.
    """

    def __init__(
        self,
        can_run: bool = True,
        system_status: str = "healthy",
    ):

        self.can_run = can_run

        self.system_status = (
            system_status
        )

    def can_run_heavy_task(
        self,
    ) -> bool:

        return self.can_run

    def get_system_status(
        self,
    ) -> str:

        return self.system_status


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNING SCHEDULER TEST"
    )

    print("=" * 60)

    # ------------------------------------------------------
    # TEST 1
    # NOT ENOUGH DATA
    # ------------------------------------------------------

    scheduler = FineTuningScheduler(

        performance_manager=(

            MockPerformanceManager(
                can_run=True
            )

        ),

        minimum_examples=10,

    )

    result = scheduler.should_train(

        example_count=5,

        current_time=datetime(
            2026,
            9,
            7,
            2,
            0,
        ),

    )

    print()

    print(
        "TEST 1: INSUFFICIENT DATA"
    )

    print("-" * 60)

    print(result)

    # ------------------------------------------------------
    # TEST 2
    # ENOUGH DATA + OVERNIGHT + RESOURCES
    # ------------------------------------------------------

    result = scheduler.should_train(

        example_count=20,

        current_time=datetime(
            2026,
            9,
            7,
            2,
            0,
        ),

    )

    print()

    print(
        "TEST 2: TRAINING APPROVED"
    )

    print("-" * 60)

    print(result)

    # ------------------------------------------------------
    # TEST 3
    # DAYTIME
    # ------------------------------------------------------

    result = scheduler.should_train(

        example_count=20,

        current_time=datetime(
            2026,
            9,
            7,
            14,
            0,
        ),

    )

    print()

    print(
        "TEST 3: DAYTIME"
    )

    print("-" * 60)

    print(result)

    # ------------------------------------------------------
    # TEST 4
    # FORCE DAYTIME TEST
    # ------------------------------------------------------

    result = scheduler.should_train(

        example_count=20,

        current_time=datetime(
            2026,
            9,
            7,
            14,
            0,
        ),

        force=True,

    )

    print()

    print(
        "TEST 4: FORCED DEVELOPMENT RUN"
    )

    print("-" * 60)

    print(result)

    # ------------------------------------------------------
    # TEST 5
    # INSUFFICIENT RESOURCES
    # ------------------------------------------------------

    low_resource_scheduler = (

        FineTuningScheduler(

            performance_manager=(

                MockPerformanceManager(
                    can_run=False,
                    system_status="critical",
                )

            ),

            minimum_examples=10,

        )

    )

    result = (

        low_resource_scheduler
        .should_train(

            example_count=20,

            current_time=datetime(
                2026,
                9,
                7,
                2,
                0,
            ),

        )

    )

    print()

    print(
        "TEST 5: INSUFFICIENT RESOURCES"
    )

    print("-" * 60)

    print(result)

    # ------------------------------------------------------
    # TEST 6
    # REAL VAULT SYSTEM
    # ------------------------------------------------------

    print()

    print(
        "TEST 6: REAL V.A.U.L.T. RESOURCE CHECK"
    )

    print("-" * 60)

    real_scheduler = (

        FineTuningScheduler(
            minimum_examples=10
        )

    )

    print(

        real_scheduler.get_status()

    )

    print()

    print("=" * 60)

    print(
        "SCHEDULER TEST COMPLETE"
    )

    print("=" * 60)