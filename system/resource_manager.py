"""
V.A.U.L.T. Resource Manager

Responsible for monitoring:

- CPU usage
- System RAM usage
- GPU / VRAM usage
- Hardware profile
- Ollama model status
"""

from typing import Any, Dict, Optional

import psutil

from system.hardware_manager import HardwareManager
from system.vram_manager import VRAMManager
from system.model_manager import ModelManager


class ResourceManager:

    CPU_WARNING_PERCENT = 80.0
    CPU_CRITICAL_PERCENT = 95.0

    RAM_WARNING_PERCENT = 80.0
    RAM_CRITICAL_PERCENT = 92.0

    VRAM_WARNING_PERCENT = 80.0
    VRAM_CRITICAL_PERCENT = 92.0

    def __init__(
        self,
        hardware_manager: Optional[
            HardwareManager
        ] = None,
        vram_manager: Optional[
            VRAMManager
        ] = None,
        model_manager: Optional[
            ModelManager
        ] = None,
    ):

        self.hardware_manager = (
            hardware_manager
            or HardwareManager()
        )

        self.vram_manager = (
            vram_manager
            or VRAMManager(
                hardware_manager=
                self.hardware_manager
            )
        )

        self.model_manager = (
            model_manager
            or ModelManager()
        )

    # ======================================================
    # STATUS HELPER
    # ======================================================

    def _get_resource_status(
        self,
        value: float,
        warning_threshold: float,
        critical_threshold: float,
    ) -> str:

        if value >= critical_threshold:
            return "critical"

        if value >= warning_threshold:
            return "warning"

        return "healthy"

    # ======================================================
    # CPU
    # ======================================================

    def get_cpu_status(
        self,
    ) -> Dict[str, Any]:

        cpu_percent = psutil.cpu_percent(
            interval=0.1
        )

        status = (
            self._get_resource_status(
                value=cpu_percent,
                warning_threshold=
                self.CPU_WARNING_PERCENT,
                critical_threshold=
                self.CPU_CRITICAL_PERCENT,
            )
        )

        return {

            "usage_percent":
                round(cpu_percent, 2),

            "physical_cores":
                psutil.cpu_count(
                    logical=False
                ),

            "logical_cores":
                psutil.cpu_count(
                    logical=True
                ),

            "status":
                status,

        }

    # ======================================================
    # RAM
    # ======================================================

    def get_ram_status(
        self,
    ) -> Dict[str, Any]:

        memory = (
            psutil.virtual_memory()
        )

        status = (
            self._get_resource_status(
                value=memory.percent,
                warning_threshold=
                self.RAM_WARNING_PERCENT,
                critical_threshold=
                self.RAM_CRITICAL_PERCENT,
            )
        )

        return {

            "total_gb":
                round(
                    memory.total /
                    (1024 ** 3),
                    2,
                ),

            "used_gb":
                round(
                    memory.used /
                    (1024 ** 3),
                    2,
                ),

            "available_gb":
                round(
                    memory.available /
                    (1024 ** 3),
                    2,
                ),

            "usage_percent":
                round(
                    memory.percent,
                    2,
                ),

            "status":
                status,

        }

    # ======================================================
    # VRAM
    # ======================================================

    def get_vram_status(
        self,
    ) -> Dict[str, Any]:

        if not self.vram_manager.has_gpu():

            return {

                "gpu_available":
                    False,

                "usage_percent":
                    0.0,

                "status":
                    "unavailable",

            }

        total_vram = (
            self.vram_manager
            .get_total_vram_mb()
        )

        used_vram = (
            self.vram_manager
            .get_used_vram_mb()
        )

        free_vram = (
            self.vram_manager
            .get_free_vram_mb()
        )

        usage_percent = 0.0

        if total_vram > 0:

            usage_percent = (
                used_vram /
                total_vram
            ) * 100

        status = (
            self._get_resource_status(
                value=usage_percent,
                warning_threshold=
                self.VRAM_WARNING_PERCENT,
                critical_threshold=
                self.VRAM_CRITICAL_PERCENT,
            )
        )

        return {

            "gpu_available":
                True,

            "total_gb":
                round(
                    total_vram / 1024,
                    2,
                ),

            "used_gb":
                round(
                    used_vram / 1024,
                    2,
                ),

            "free_gb":
                round(
                    free_vram / 1024,
                    2,
                ),

            "usage_percent":
                round(
                    usage_percent,
                    2,
                ),

            "status":
                status,

        }

    # ======================================================
    # HARDWARE PROFILE
    # ======================================================

    def get_hardware_profile(
        self,
    ) -> Dict[str, Any]:

        try:

            hardware_info = (
                self.hardware_manager
                .get_hardware_info()
            )

            return {

                "hardware_class":
                    hardware_info.get(
                        "hardware_class",
                        "unknown",
                    ),

                "gpu_available":
                    self.vram_manager.has_gpu(),

                "best_gpu":
                    self.vram_manager.get_gpu_info(),

            }

        except Exception:

            return {

                "hardware_class":
                    "unknown",

                "gpu_available":
                    self.vram_manager.has_gpu(),

                "best_gpu":
                    self.vram_manager.get_gpu_info(),

            }

    # ======================================================
    # OLLAMA
    # ======================================================

    def get_ollama_status(
        self,
    ) -> Dict[str, Any]:

        try:

            return (
                self.model_manager
                .get_model_report()
            )

        except Exception as exc:

            return {

                "error":
                    str(exc),

                "ollama_available":
                    False,

                "installed_models":
                    [],

                "running_models":
                    [],

            }

    # ======================================================
    # OVERALL SYSTEM LOAD
    # ======================================================

    def get_system_load(
        self,
    ) -> str:

        cpu = (
            self.get_cpu_status()
        )

        ram = (
            self.get_ram_status()
        )

        vram = (
            self.get_vram_status()
        )

        statuses = [

            cpu["status"],

            ram["status"],

        ]

        # Only include VRAM if GPU exists.

        if vram["status"] != "unavailable":

            statuses.append(
                vram["status"]
            )

        if "critical" in statuses:

            return "critical"

        if "warning" in statuses:

            return "warning"

        return "healthy"

    # ======================================================
    # COMPLETE SNAPSHOT
    # ======================================================

    def get_resource_snapshot(
        self,
    ) -> Dict[str, Any]:

        cpu_status = (
            self.get_cpu_status()
        )

        ram_status = (
            self.get_ram_status()
        )

        vram_status = (
            self.get_vram_status()
        )

        hardware_profile = (
            self.get_hardware_profile()
        )

        ollama_status = (
            self.get_ollama_status()
        )

        statuses = [

            cpu_status["status"],

            ram_status["status"],

        ]

        if (
            vram_status["status"]
            != "unavailable"
        ):

            statuses.append(
                vram_status["status"]
            )

        if "critical" in statuses:

            overall_status = "critical"

        elif "warning" in statuses:

            overall_status = "warning"

        else:

            overall_status = "healthy"

        return {

            "overall_status":
                overall_status,

            "cpu":
                cpu_status,

            "ram":
                ram_status,

            "vram":
                vram_status,

            "hardware":
                hardware_profile,

            "ollama":
                ollama_status,

        }

    # ======================================================
    # HEAVY TASK CHECK
    # ======================================================

    def can_run_heavy_task(
        self,
    ) -> bool:

        return (
            self.get_system_load()
            != "critical"
        )

    # ======================================================
    # RECOMMENDATION
    # ======================================================

    def get_recommendation(
        self,
    ) -> str:

        system_status = (
            self.get_system_load()
        )

        if system_status == "critical":

            return (
                "System resources are critically "
                "high. Use the smallest available "
                "model."
            )

        if system_status == "warning":

            return (
                "System resource usage is elevated. "
                "Prefer smaller models for faster "
                "and more stable performance."
            )

        return (
            "System resources are healthy. "
            "Configured models can be used normally."
        )

    # ======================================================
    # PRINT REPORT
    # ======================================================

    def print_report(
        self,
    ) -> None:

        snapshot = (
            self.get_resource_snapshot()
        )

        print()

        print("=" * 60)
        print(
            "V.A.U.L.T. RESOURCE MANAGER"
        )
        print("=" * 60)

        print()

        print(
            "OVERALL SYSTEM STATUS"
        )

        print("-" * 60)

        print(
            snapshot[
                "overall_status"
            ].upper()
        )

        # CPU

        cpu = snapshot["cpu"]

        print()
        print("CPU")
        print("-" * 60)

        print(
            f"Usage: "
            f"{cpu['usage_percent']}%"
        )

        print(
            f"Physical Cores: "
            f"{cpu['physical_cores']}"
        )

        print(
            f"Logical Cores: "
            f"{cpu['logical_cores']}"
        )

        print(
            f"Status: "
            f"{cpu['status']}"
        )

        # RAM

        ram = snapshot["ram"]

        print()
        print("SYSTEM RAM")
        print("-" * 60)

        print(
            f"Total RAM: "
            f"{ram['total_gb']} GB"
        )

        print(
            f"Used RAM: "
            f"{ram['used_gb']} GB"
        )

        print(
            f"Available RAM: "
            f"{ram['available_gb']} GB"
        )

        print(
            f"Usage: "
            f"{ram['usage_percent']}%"
        )

        print(
            f"Status: "
            f"{ram['status']}"
        )

        # GPU

        vram = snapshot["vram"]

        print()
        print("GPU / VRAM")
        print("-" * 60)

        if not vram["gpu_available"]:

            print(
                "No GPU available."
            )

        else:

            gpu = (
                self.vram_manager
                .get_gpu_info()
            )

            if gpu:

                print(
                    f"GPU: "
                    f"{gpu.get('name', 'Unknown')}"
                )

            print(
                f"Total VRAM: "
                f"{vram['total_gb']} GB"
            )

            print(
                f"Used VRAM: "
                f"{vram['used_gb']} GB"
            )

            print(
                f"Free VRAM: "
                f"{vram['free_gb']} GB"
            )

            print(
                f"Usage: "
                f"{vram['usage_percent']}%"
            )

            print(
                f"Status: "
                f"{vram['status']}"
            )

        # HARDWARE

        hardware = (
            snapshot["hardware"]
        )

        print()
        print("HARDWARE PROFILE")
        print("-" * 60)

        print(
            f"Hardware Class: "
            f"{hardware['hardware_class']}"
        )

        print(
            f"GPU Available: "
            f"{hardware['gpu_available']}"
        )

        # OLLAMA

        ollama = snapshot["ollama"]

        print()
        print("OLLAMA")
        print("-" * 60)

        print(
            f"Available: "
            f"{ollama.get('ollama_available')}"
        )

        print(
            f"Installed Models: "
            f"{len(ollama.get('installed_models', []))}"
        )

        print(
            f"Running Models: "
            f"{len(ollama.get('running_models', []))}"
        )

        # RECOMMENDATION

        print()
        print("RECOMMENDATION")
        print("-" * 60)

        print(
            self.get_recommendation()
        )

        print()

        print("=" * 60)
        print(
            "RESOURCE MANAGER TEST COMPLETE"
        )
        print("=" * 60)


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    manager = ResourceManager()

    manager.print_report()