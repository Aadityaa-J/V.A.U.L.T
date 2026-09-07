"""
V.A.U.L.T. Fine-Tuning Controller

High-level automation controller for the V.A.U.L.T.
fine-tuning system.

Architecture:

    V.A.U.L.T. Interaction
            ↓
    FineTuningController
            ↓
    FineTuningManager
            ↓
    Eligibility Check
            ↓
    FineTuningPipelineManager
            ↓
    Fine-Tuning Pipeline
            ↓
    Training / Evaluation / Registry / Deployment
            ↓
    FineTuningRuntimeRouter
            ↓
    Fine-Tuned Model Available

The controller is designed to be SAFE.

Failures inside the fine-tuning system must never
crash the main V.A.U.L.T. assistant.
"""


from datetime import datetime
from typing import Any, Dict, List, Optional


from models.fine_tuning.manager import (
    FineTuningManager,
)

from models.fine_tuning.pipeline_manager import (
    FineTuningPipelineManager,
)

from models.fine_tuning.runtime_router import (
    FineTuningRuntimeRouter,
)


# ==========================================================
# FINE-TUNING CONTROLLER
# ==========================================================

class FineTuningController:

    """
    High-level controller for V.A.U.L.T. fine-tuning.

    Responsibilities:

        - Manage fine-tuning state
        - Record system activity
        - Check fine-tuning eligibility
        - Trigger the pipeline manager
        - Monitor pipeline results
        - Query runtime routing
        - Protect the main assistant from failures
    """

    def __init__(
        self,
        manager: Optional[
            FineTuningManager
        ] = None,
        pipeline_manager: Optional[
            FineTuningPipelineManager
        ] = None,
        runtime_router: Optional[
            FineTuningRuntimeRouter
        ] = None,
        auto_training: bool = False,
    ):

        # --------------------------------------------------
        # CORE COMPONENTS
        # --------------------------------------------------

        self.manager = (
            manager
            or FineTuningManager()
        )

        self.pipeline_manager = (
            pipeline_manager
            or FineTuningPipelineManager()
        )

        self.runtime_router = (
            runtime_router
            or FineTuningRuntimeRouter()
        )

        # --------------------------------------------------
        # CONFIGURATION
        # --------------------------------------------------

        self.auto_training = bool(
            auto_training
        )

        # --------------------------------------------------
        # STATE
        # --------------------------------------------------

        self.total_interactions = 0

        self.total_checks = 0

        self.total_training_attempts = 0

        self.last_result: Optional[
            Dict[str, Any]
        ] = None

        self.last_error: Optional[
            str
        ] = None

        self.history: List[
            Dict[str, Any]
        ] = []


    # ======================================================
    # SAFE METHOD CALL
    # ======================================================

    @staticmethod
    def _safe_call(
        obj: Any,
        method_names: List[str],
        *args,
        **kwargs,
    ) -> Any:

        """
        Call the first available compatible method.

        Different V.A.U.L.T. components may evolve
        independently, so this controller supports
        multiple possible method names.
        """

        last_error = None

        for method_name in method_names:

            method = getattr(
                obj,
                method_name,
                None,
            )

            if not callable(method):

                continue

            try:

                return method(
                    *args,
                    **kwargs,
                )

            except TypeError as exc:

                last_error = exc

                try:

                    return method(
                        *args
                    )

                except TypeError as exc:

                    last_error = exc

                    continue

            except Exception:

                raise

        if last_error:

            raise last_error

        raise AttributeError(
            "No compatible method found. "
            f"Tried: {method_names}"
        )


    # ======================================================
    # NORMALIZE TASK TYPE
    # ======================================================

    @staticmethod
    def _normalize_task_type(
        task_type: Any,
    ) -> str:

        """
        Normalize task type.
        """

        if not isinstance(
            task_type,
            str,
        ):

            return "general"

        task_type = (
            task_type
            .strip()
            .lower()
        )

        if not task_type:

            return "general"

        return task_type


    # ======================================================
    # STORE HISTORY
    # ======================================================

    def _store_history(
        self,
        event: Dict[str, Any],
    ) -> None:

        """
        Store a controller event.
        """

        record = dict(
            event
        )

        record.setdefault(
            "timestamp",
            datetime.now().isoformat(),
        )

        self.history.append(
            record
        )


    # ======================================================
    # RECORD INTERACTION
    # ======================================================

    def record_interaction(
        self,
        prompt: str,
        response: str,
        task_type: str = "general",
        successful: bool = True,
    ) -> Dict[str, Any]:

        """
        Record a V.A.U.L.T. interaction.

        The interaction may later be used by the
        fine-tuning dataset system.
        """

        task_type = (
            self._normalize_task_type(
                task_type
            )
        )

        self.total_interactions += 1

        result = {

            "success": True,

            "recorded": False,

            "task_type":
                task_type,

            "auto_training":
                self.auto_training,

        }

        try:

            manager_result = (

                self._safe_call(

                    self.manager,

                    [

                        "record_interaction",

                        "add_interaction",

                        "process_interaction",

                        "add_example",

                    ],

                    prompt=prompt,

                    response=response,

                    task_type=task_type,

                    successful=successful,

                )

            )

            result[
                "manager_result"
            ] = manager_result

            result[
                "recorded"
            ] = True

        except Exception as exc:

            # ------------------------------------------------
            # SAFE FAILURE
            # ------------------------------------------------

            self.last_error = str(
                exc
            )

            result[
                "success"
            ] = False

            result[
                "reason"
            ] = str(exc)

        self._store_history({

            "event":
                "interaction",

            "task_type":
                task_type,

            "successful":
                successful,

            "result":
                result,

        })

        # --------------------------------------------------
        # AUTOMATIC TRAINING CHECK
        # --------------------------------------------------

        if self.auto_training:

            try:

                training_check = (

                    self.check_training(
                        task_type
                    )

                )

                result[
                    "training_check"
                ] = training_check

            except Exception as exc:

                result[
                    "training_check_error"
                ] = str(exc)

        return result


    # ======================================================
    # CHECK TRAINING
    # ======================================================

    def check_training(
        self,
        task_type: str = "general",
    ) -> Dict[str, Any]:

        """
        Check whether fine-tuning should run.
        """

        task_type = (
            self._normalize_task_type(
                task_type
            )
        )

        self.total_checks += 1

        result = {

            "success": True,

            "task_type":
                task_type,

            "eligible":
                False,

            "timestamp":
                datetime.now().isoformat(),

        }

        try:

            # ------------------------------------------------
            # ASK MANAGER
            # ------------------------------------------------

            manager_result = (

                self._safe_call(

                    self.manager,

                    [

                        "check_eligibility",

                        "is_eligible",

                        "should_train",

                        "check_training",

                    ],

                    task_type=task_type,

                )

            )

            result[
                "manager_result"
            ] = manager_result

            # ------------------------------------------------
            # NORMALIZE RESULT
            # ------------------------------------------------

            if isinstance(
                manager_result,
                bool,
            ):

                eligible = (
                    manager_result
                )

            elif isinstance(
                manager_result,
                dict,
            ):

                eligible = bool(

                    manager_result.get(

                        "eligible",

                        manager_result.get(

                            "should_train",

                            manager_result.get(

                                "success",

                                False,

                            ),

                        ),

                    )

                )

            else:

                eligible = False

            result[
                "eligible"
            ] = eligible

        except Exception as exc:

            result[
                "success"
            ] = False

            result[
                "reason"
            ] = str(exc)

            self.last_error = str(
                exc
            )

        self.last_result = result

        self._store_history({

            "event":
                "training_check",

            "result":
                result,

        })

        return result


    # ======================================================
    # RUN PIPELINE
    # ======================================================

    def run_pipeline(
        self,
        task_type: str = "general",
        **kwargs,
    ) -> Dict[str, Any]:

        """
        Run the fine-tuning pipeline.

        This method safely communicates with the
        FineTuningPipelineManager.
        """

        task_type = (
            self._normalize_task_type(
                task_type
            )
        )

        self.total_training_attempts += 1

        try:

            result = (

                self._safe_call(

                    self.pipeline_manager,

                    [

                        "run",

                        "run_pipeline",

                        "start_pipeline",

                        "execute",

                    ],

                    task_type=task_type,

                    **kwargs,

                )

            )

            if not isinstance(
                result,
                dict,
            ):

                result = {

                    "success":
                        bool(result),

                    "result":
                        result,

                }

            result.setdefault(

                "task_type",

                task_type,

            )

            self.last_result = (
                result
            )

            self._store_history({

                "event":
                    "pipeline",

                "task_type":
                    task_type,

                "result":
                    result,

            })

            return result

        except Exception as exc:

            self.last_error = str(
                exc
            )

            result = {

                "success": False,

                "stage":
                    "controller",

                "task_type":
                    task_type,

                "reason":
                    str(exc),

            }

            self.last_result = (
                result
            )

            return result


    # ======================================================
    # PROCESS AUTO TRAINING
    # ======================================================

    def process_auto_training(
        self,
        task_type: str = "general",
        **kwargs,
    ) -> Dict[str, Any]:

        """
        Run automatic fine-tuning logic.

        Steps:

            Check eligibility
                    ↓
            If eligible
                    ↓
            Run pipeline
                    ↓
            Return result
        """

        task_type = (
            self._normalize_task_type(
                task_type
            )
        )

        check = (

            self.check_training(
                task_type
            )

        )

        # --------------------------------------------------
        # NOT ELIGIBLE
        # --------------------------------------------------

        if not check.get(
            "eligible",
            False,
        ):

            return {

                "success": True,

                "trained": False,

                "task_type":
                    task_type,

                "reason":
                    "Fine-tuning is not yet eligible.",

                "check":
                    check,

            }

        # --------------------------------------------------
        # RUN PIPELINE
        # --------------------------------------------------

        pipeline_result = (

            self.run_pipeline(

                task_type=task_type,

                **kwargs,

            )

        )

        return {

            "success":

                pipeline_result.get(

                    "success",

                    False,

                ),

            "trained":

                pipeline_result.get(

                    "success",

                    False,

                ),

            "task_type":
                task_type,

            "check":
                check,

            "pipeline":
                pipeline_result,

        }


    # ======================================================
    # GET RUNTIME MODEL
    # ======================================================

    def get_runtime_model(
        self,
        task_type: str = "general",
        fallback_model: Optional[
            str
        ] = None,
    ) -> Dict[str, Any]:

        """
        Ask the runtime router which model should
        currently handle the task.
        """

        task_type = (
            self._normalize_task_type(
                task_type
            )
        )

        try:

            result = (

                self._safe_call(

                    self.runtime_router,

                    [

                        "route",

                        "select_model",

                        "get_model",

                        "resolve",

                    ],

                    task_type=task_type,

                    fallback_model=(
                        fallback_model
                    ),

                )

            )

            if isinstance(
                result,
                str,
            ):

                return {

                    "success": True,

                    "model":
                        result,

                    "task_type":
                        task_type,

                }

            if isinstance(
                result,
                dict,
            ):

                return result

            return {

                "success": False,

                "model":
                    fallback_model,

                "task_type":
                    task_type,

            }

        except Exception as exc:

            self.last_error = str(
                exc
            )

            return {

                "success": False,

                "model":
                    fallback_model,

                "task_type":
                    task_type,

                "reason":
                    str(exc),

            }


    # ======================================================
    # ENABLE AUTO TRAINING
    # ======================================================

    def enable_auto_training(
        self,
    ) -> None:

        """
        Enable automatic fine-tuning.
        """

        self.auto_training = True


    # ======================================================
    # DISABLE AUTO TRAINING
    # ======================================================

    def disable_auto_training(
        self,
    ) -> None:

        """
        Disable automatic fine-tuning.
        """

        self.auto_training = False


    # ======================================================
    # GET STATUS
    # ======================================================

    def get_status(
        self,
    ) -> Dict[str, Any]:

        """
        Return controller status.
        """

        return {

            "auto_training":
                self.auto_training,

            "total_interactions":
                self.total_interactions,

            "total_checks":
                self.total_checks,

            "total_training_attempts":
                self.total_training_attempts,

            "last_result":
                self.last_result,

            "last_error":
                self.last_error,

            "history_count":
                len(self.history),

        }


    # ======================================================
    # GET HISTORY
    # ======================================================

    def get_history(
        self,
        limit: Optional[
            int
        ] = None,
    ) -> List[Dict[str, Any]]:

        """
        Return controller history.
        """

        if limit is None:

            return list(
                self.history
            )

        try:

            limit = int(
                limit
            )

        except (
            TypeError,
            ValueError,
        ):

            return list(
                self.history
            )

        if limit <= 0:

            return []

        return self.history[
            -limit:
        ]


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNING CONTROLLER TEST"
    )

    print("=" * 60)

    # ------------------------------------------------------
    # CREATE CONTROLLER
    # ------------------------------------------------------

    controller = (

        FineTuningController(

            auto_training=False,

        )

    )

    # ------------------------------------------------------
    # TEST 1
    # STATUS
    # ------------------------------------------------------

    print()

    print(
        "TEST 1: CONTROLLER STATUS"
    )

    print("-" * 60)

    print(

        controller.get_status()

    )

    # ------------------------------------------------------
    # TEST 2
    # RECORD INTERACTION
    # ------------------------------------------------------

    print()

    print(
        "TEST 2: RECORD INTERACTION"
    )

    print("-" * 60)

    result = (

        controller.record_interaction(

            prompt=(

                "Calculate the force required "

                "to accelerate a 10 kg object."

            ),

            response=(

                "Force is calculated using "

                "F = m × a."

            ),

            task_type=(
                "engineering"
            ),

            successful=True,

        )

    )

    print(
        result
    )

    # ------------------------------------------------------
    # TEST 3
    # CHECK TRAINING
    # ------------------------------------------------------

    print()

    print(
        "TEST 3: CHECK TRAINING"
    )

    print("-" * 60)

    print(

        controller.check_training(

            "engineering"

        )

    )

    # ------------------------------------------------------
    # TEST 4
    # RUNTIME MODEL
    # ------------------------------------------------------

    print()

    print(
        "TEST 4: RUNTIME MODEL"
    )

    print("-" * 60)

    print(

        controller.get_runtime_model(

            task_type=(
                "engineering"
            ),

            fallback_model=(
                "qwen3:4b"
            ),

        )

    )

    # ------------------------------------------------------
    # TEST 5
    # AUTO TRAINING CHECK
    # ------------------------------------------------------

    print()

    print(
        "TEST 5: AUTO TRAINING CHECK"
    )

    print("-" * 60)

    print(

        controller.process_auto_training(

            task_type=(
                "engineering"
            )

        )

    )

    # ------------------------------------------------------
    # FINAL STATUS
    # ------------------------------------------------------

    print()

    print(
        "FINAL CONTROLLER STATUS"
    )

    print("-" * 60)

    print(

        controller.get_status()

    )

    print()

    print("=" * 60)

    print(
        "FINE-TUNING CONTROLLER TEST COMPLETE"
    )

    print("=" * 60)