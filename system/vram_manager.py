"""
VRAM Manager for V.A.U.L.T.

Responsible for:

- Detecting available GPU VRAM
- Reading GPU information from HardwareManager
- Estimating model VRAM requirements
- Determining whether a model can run safely
"""

from typing import Any, Dict, Optional

from system.hardware_manager import HardwareManager


class VRAMManager:
    """
    Manage GPU VRAM availability for V.A.U.L.T.
    """

    # ==========================================================
    # MODEL VRAM ESTIMATES
    # ==========================================================

    MODEL_VRAM_REQUIREMENTS = {
        "qwen3:1.7b": 2200,
        "qwen3:4b": 4200,
        "qwen3-vl:2b": 3500,
    }

    # Keep this amount of VRAM free for safety.
    SAFETY_BUFFER_MB = 512

    def __init__(
        self,
        hardware_manager: Optional[HardwareManager] = None,
    ):
        self.hardware_manager = (
            hardware_manager
            or HardwareManager()
        )

    # ==========================================================
    # GPU INFORMATION
    # ==========================================================

    def get_gpu_info(
        self,
    ) -> Optional[Dict[str, Any]]:
        """
        Return information about the best available GPU.

        HardwareManager uses get_hardware_info().
        """

        try:

            hardware_info = (
                self.hardware_manager
                .get_hardware_info()
            )

            # --------------------------------------------------
            # FIRST POSSIBILITY:
            # HardwareManager returns "best_gpu"
            # --------------------------------------------------

            gpu = hardware_info.get(
                "best_gpu"
            )

            if gpu:

                return gpu

            # --------------------------------------------------
            # SECOND POSSIBILITY:
            # HardwareManager returns "gpus"
            # --------------------------------------------------

            gpus = hardware_info.get(
                "gpus",
                []
            )

            if gpus:

                return max(
                    gpus,
                    key=lambda gpu: float(
                        gpu.get(
                            "vram_total_mb",
                            gpu.get(
                                "vram_total",
                                0
                            )
                        )
                        or 0
                    )
                )

            # --------------------------------------------------
            # NO GPU FOUND
            # --------------------------------------------------

            return None

        except Exception as exc:

            # Do not crash V.A.U.L.T.
            return None

    # ==========================================================
    # GPU AVAILABILITY
    # ==========================================================

    def has_gpu(self) -> bool:

        gpu = self.get_gpu_info()

        return gpu is not None

    # ==========================================================
    # INTERNAL GPU VALUE READER
    # ==========================================================

    def _get_gpu_value(
        self,
        keys: list[str],
        default: float = 0.0,
    ) -> float:
        """
        Read a numeric VRAM value from multiple
        possible HardwareManager key formats.
        """

        gpu = self.get_gpu_info()

        if not gpu:
            return default

        for key in keys:

            value = gpu.get(key)

            if value is not None:

                try:

                    return float(value)

                except (
                    TypeError,
                    ValueError,
                ):

                    continue

        return default

    # ==========================================================
    # VRAM VALUES
    # ==========================================================

    def get_total_vram_mb(
        self,
    ) -> float:

        return self._get_gpu_value(

            [
                "vram_total_mb",
                "total_vram_mb",
                "memory_total_mb",
            ]

        )

    def get_used_vram_mb(
        self,
    ) -> float:

        return self._get_gpu_value(

            [
                "vram_used_mb",
                "used_vram_mb",
                "memory_used_mb",
            ]

        )

    def get_free_vram_mb(
        self,
    ) -> float:

        gpu = self.get_gpu_info()

        if not gpu:

            return 0.0

        # Try explicit free VRAM first.

        for key in [

            "vram_free_mb",
            "free_vram_mb",
            "memory_free_mb",

        ]:

            value = gpu.get(key)

            if value is not None:

                try:

                    return float(value)

                except (
                    TypeError,
                    ValueError,
                ):

                    pass

        # Otherwise calculate:
        #
        # Total - Used

        total = self.get_total_vram_mb()

        used = self.get_used_vram_mb()

        free = total - used

        return max(
            free,
            0.0,
        )

    # ==========================================================
    # VRAM IN GB
    # ==========================================================

    def get_total_vram_gb(
        self,
    ) -> float:

        return round(
            self.get_total_vram_mb() / 1024,
            2,
        )

    def get_used_vram_gb(
        self,
    ) -> float:

        return round(
            self.get_used_vram_mb() / 1024,
            2,
        )

    def get_free_vram_gb(
        self,
    ) -> float:

        return round(
            self.get_free_vram_mb() / 1024,
            2,
        )

    # ==========================================================
    # MODEL REQUIREMENTS
    # ==========================================================

    def get_model_requirement_mb(
        self,
        model_name: str,
    ) -> float:

        if not isinstance(
            model_name,
            str,
        ):

            raise TypeError(
                "Model name must be a string."
            )

        model_name = model_name.strip()

        if not model_name:

            raise ValueError(
                "Model name cannot be empty."
            )

        # Exact configured model.

        if model_name in (
            self.MODEL_VRAM_REQUIREMENTS
        ):

            return float(

                self.MODEL_VRAM_REQUIREMENTS[
                    model_name
                ]

            )

        model_lower = model_name.lower()

        # Vision models.

        if (
            "vision" in model_lower
            or "-vl" in model_lower
            or "vl:" in model_lower
        ):

            return 4000.0

        # Small models.

        if (
            "1b" in model_lower
            or "2b" in model_lower
        ):

            return 2500.0

        # Medium models.

        if (
            "3b" in model_lower
            or "4b" in model_lower
        ):

            return 4500.0

        # Larger models.

        if (
            "7b" in model_lower
            or "8b" in model_lower
        ):

            return 7000.0

        # Conservative default.

        return 4096.0

    # ==========================================================
    # REQUIRED VRAM
    # ==========================================================

    def get_required_vram_mb(
        self,
        model_name: str,
        include_safety_buffer: bool = True,
    ) -> float:

        requirement = (
            self.get_model_requirement_mb(
                model_name
            )
        )

        if include_safety_buffer:

            requirement += (
                self.SAFETY_BUFFER_MB
            )

        return requirement

    # ==========================================================
    # MODEL COMPATIBILITY
    # ==========================================================

    def can_run_model(
        self,
        model_name: str,
    ) -> bool:
        """
        Check whether the model fits into currently
        available VRAM.
        """

        if not self.has_gpu():

            return False

        free_vram = (
            self.get_free_vram_mb()
        )

        required_vram = (
            self.get_required_vram_mb(
                model_name
            )
        )

        return (
            free_vram >= required_vram
        )

    # ==========================================================
    # MODEL STATUS
    # ==========================================================

    def get_model_status(
        self,
        model_name: str,
    ) -> Dict[str, Any]:

        required_vram = (
            self.get_required_vram_mb(
                model_name
            )
        )

        free_vram = (
            self.get_free_vram_mb()
        )

        total_vram = (
            self.get_total_vram_mb()
        )

        used_vram = (
            self.get_used_vram_mb()
        )

        can_run = (
            self.can_run_model(
                model_name
            )
        )

        remaining_vram = (
            free_vram - required_vram
        )

        return {

            "model":
                model_name,

            "gpu_available":
                self.has_gpu(),

            "total_vram_mb":
                round(
                    total_vram,
                    2,
                ),

            "used_vram_mb":
                round(
                    used_vram,
                    2,
                ),

            "free_vram_mb":
                round(
                    free_vram,
                    2,
                ),

            "required_vram_mb":
                round(
                    required_vram,
                    2,
                ),

            "safety_buffer_mb":
                self.SAFETY_BUFFER_MB,

            "remaining_vram_mb":
                round(
                    remaining_vram,
                    2,
                ),

            "can_run":
                can_run,

        }

    # ==========================================================
    # COMPLETE VRAM REPORT
    # ==========================================================

    def get_vram_report(
        self,
    ) -> Dict[str, Any]:

        gpu = self.get_gpu_info()

        return {

            "gpu_available":
                self.has_gpu(),

            "gpu":
                gpu,

            "total_vram_mb":
                round(
                    self.get_total_vram_mb(),
                    2,
                ),

            "used_vram_mb":
                round(
                    self.get_used_vram_mb(),
                    2,
                ),

            "free_vram_mb":
                round(
                    self.get_free_vram_mb(),
                    2,
                ),

            "total_vram_gb":
                self.get_total_vram_gb(),

            "used_vram_gb":
                self.get_used_vram_gb(),

            "free_vram_gb":
                self.get_free_vram_gb(),

            "safety_buffer_mb":
                self.SAFETY_BUFFER_MB,

        }

    # ==========================================================
    # MODEL COMPARISON
    # ==========================================================

    def compare_models(
        self,
        models: list[str],
    ) -> Dict[str, Dict[str, Any]]:

        results = {}

        for model in models:

            results[model] = (
                self.get_model_status(
                    model
                )
            )

        return results


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    manager = VRAMManager()

    print()

    print("=" * 60)
    print("V.A.U.L.T. VRAM MANAGER")
    print("=" * 60)

    report = (
        manager.get_vram_report()
    )

    print()

    print("GPU AVAILABLE:")
    print(
        report["gpu_available"]
    )

    print()

    if report["gpu"]:

        print("GPU:")
        print(
            report["gpu"]
        )

        print()

    print("TOTAL VRAM:")
    print(
        f"{report['total_vram_gb']} GB"
    )

    print()

    print("USED VRAM:")
    print(
        f"{report['used_vram_gb']} GB"
    )

    print()

    print("FREE VRAM:")
    print(
        f"{report['free_vram_gb']} GB"
    )

    print()

    print("-" * 60)
    print("MODEL COMPATIBILITY")
    print("-" * 60)

    test_models = [

        "qwen3:1.7b",

        "qwen3:4b",

        "qwen3-vl:2b",

    ]

    for model in test_models:

        status = (
            manager.get_model_status(
                model
            )
        )

        print()

        print(
            f"MODEL: {model}"
        )

        print(
            "Required VRAM: "
            f"{status['required_vram_mb']} MB"
        )

        print(
            "Free VRAM: "
            f"{status['free_vram_mb']} MB"
        )

        print(
            "Remaining VRAM: "
            f"{status['remaining_vram_mb']} MB"
        )

        print(
            "Can Run: "
            f"{status['can_run']}"
        )

    print()

    print("=" * 60)
    print("VRAM MANAGER TEST COMPLETE")
    print("=" * 60)