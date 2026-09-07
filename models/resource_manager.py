import os
import platform
import subprocess
from typing import Any, Dict, List, Optional


class ResourceManager:
    """
    Hardware-Adaptive Resource Manager for V.A.U.L.T.

    Responsibilities:
    - Detect CPU information
    - Detect RAM information
    - Detect GPU information
    - Detect Ollama availability
    - Detect installed Ollama models
    - Detect currently loaded Ollama models
    - Provide a complete system resource snapshot

    The system must fail gracefully when optional
    dependencies or hardware tools are unavailable.
    """

    def __init__(self):
        pass

    # ==================================================
    # CPU DETECTION
    # ==================================================

    def get_cpu_info(self) -> Dict[str, Any]:
        """
        Detect CPU information.
        """

        cpu_name = platform.processor()

        physical_cores = None
        logical_cores = os.cpu_count()
        utilization_percent = None

        try:
            import psutil

            physical_cores = psutil.cpu_count(
                logical=False
            )

            logical_cores = psutil.cpu_count(
                logical=True
            )

            utilization_percent = psutil.cpu_percent(
                interval=0.1
            )

        except ImportError:
            pass

        except Exception:
            pass

        return {
            "name": cpu_name or None,
            "physical_cores": physical_cores,
            "logical_cores": logical_cores,
            "utilization_percent": utilization_percent,
        }

    # ==================================================
    # RAM DETECTION
    # ==================================================

    def get_ram_info(self) -> Dict[str, Any]:
        """
        Detect system RAM information.
        """

        empty_result = {
            "total_gb": None,
            "available_gb": None,
            "used_gb": None,
            "utilization_percent": None,
        }

        try:
            import psutil

            memory = psutil.virtual_memory()

            return {
                "total_gb": round(
                    memory.total / (1024 ** 3),
                    2
                ),

                "available_gb": round(
                    memory.available / (1024 ** 3),
                    2
                ),

                "used_gb": round(
                    memory.used / (1024 ** 3),
                    2
                ),

                "utilization_percent": memory.percent,
            }

        except ImportError:
            return empty_result

        except Exception:
            return empty_result

    # ==================================================
    # NVIDIA GPU DETECTION
    # ==================================================

    def _detect_nvidia_gpu(
        self
    ) -> Optional[Dict[str, Any]]:
        """
        Detect NVIDIA GPU using nvidia-smi.
        """

        try:

            command = [
                "nvidia-smi",
                "--query-gpu="
                "name,memory.total,memory.free,"
                "utilization.gpu",

                "--format=csv,noheader,nounits"
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return None

            output = result.stdout.strip()

            if not output:
                return None

            first_gpu = output.splitlines()[0]

            parts = [
                part.strip()
                for part in first_gpu.split(",")
            ]

            if len(parts) < 4:
                return None

            return {
                "available": True,
                "vendor": "NVIDIA",
                "name": parts[0],

                "total_vram_gb": round(
                    float(parts[1]) / 1024,
                    2
                ),

                "available_vram_gb": round(
                    float(parts[2]) / 1024,
                    2
                ),

                "utilization_percent": float(
                    parts[3]
                ),
            }

        except (
            FileNotFoundError,
            subprocess.TimeoutExpired,
            ValueError,
            OSError,
        ):

            return None

    # ==================================================
    # AMD GPU DETECTION
    # ==================================================

    def _detect_amd_gpu(
        self
    ) -> Optional[Dict[str, Any]]:
        """
        Attempt AMD GPU detection using ROCm tools.

        Detection may not be available on Windows.
        """

        try:

            command = [
                "rocm-smi",
                "--showproductname",
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return None

            output = result.stdout.strip()

            if not output:
                return None

            return {
                "available": True,
                "vendor": "AMD",
                "name": "AMD GPU",

                "total_vram_gb": None,
                "available_vram_gb": None,
                "utilization_percent": None,
            }

        except (
            FileNotFoundError,
            subprocess.TimeoutExpired,
            OSError,
        ):

            return None

    # ==================================================
    # GENERAL GPU DETECTION
    # ==================================================

    def get_gpu_info(self) -> Dict[str, Any]:
        """
        Detect supported GPU information.
        """

        nvidia_gpu = self._detect_nvidia_gpu()

        if nvidia_gpu:
            return nvidia_gpu

        amd_gpu = self._detect_amd_gpu()

        if amd_gpu:
            return amd_gpu

        return {
            "available": False,
            "vendor": None,
            "name": None,
            "total_vram_gb": None,
            "available_vram_gb": None,
            "utilization_percent": None,
        }

    # ==================================================
    # OLLAMA AVAILABILITY
    # ==================================================

    def is_ollama_available(
        self
    ) -> bool:
        """
        Check whether the Ollama CLI is installed
        and accessible.
        """

        try:

            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            return result.returncode == 0

        except (
            FileNotFoundError,
            subprocess.TimeoutExpired,
            OSError,
        ):

            return False

    # ==================================================
    # INSTALLED OLLAMA MODELS
    # ==================================================

    def get_installed_models(
        self
    ) -> List[Dict[str, Any]]:
        """
        Get models installed in Ollama.

        Uses:

            ollama list
        """

        if not self.is_ollama_available():

            return []

        try:

            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:

                return []

            lines = (
                result.stdout
                .strip()
                .splitlines()
            )

            if len(lines) <= 1:

                return []

            models = []

            # Skip header row.
            for line in lines[1:]:

                parts = line.split()

                if len(parts) < 3:
                    continue

                name = parts[0]
                model_id = parts[1]
                size = parts[2]

                modified = (
                    " ".join(parts[3:])
                    if len(parts) > 3
                    else None
                )

                models.append(
                    {
                        "name": name,
                        "id": model_id,
                        "size": size,
                        "modified": modified,
                    }
                )

            return models

        except (
            subprocess.TimeoutExpired,
            OSError,
        ):

            return []

    # ==================================================
    # CURRENTLY LOADED OLLAMA MODELS
    # ==================================================

    def get_loaded_models(
        self
    ) -> List[Dict[str, Any]]:
        """
        Detect models currently loaded in Ollama.

        Uses:

            ollama ps
        """

        if not self.is_ollama_available():

            return []

        try:

            result = subprocess.run(
                ["ollama", "ps"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:

                return []

            lines = (
                result.stdout
                .strip()
                .splitlines()
            )

            if len(lines) <= 1:

                return []

            models = []

            # Skip header row.
            for line in lines[1:]:

                parts = line.split()

                if len(parts) < 4:
                    continue

                models.append(
                    {
                        "name": parts[0],
                        "id": parts[1],
                        "size": parts[2],
                        "processor": parts[3],
                        "context": (
                            parts[4]
                            if len(parts) > 4
                            else None
                        ),
                        "until": (
                            " ".join(parts[5:])
                            if len(parts) > 5
                            else None
                        ),
                    }
                )

            return models

        except (
            subprocess.TimeoutExpired,
            OSError,
        ):

            return []

    # ==================================================
    # OLLAMA INFORMATION
    # ==================================================

    def get_ollama_info(
        self
    ) -> Dict[str, Any]:
        """
        Return complete Ollama runtime information.
        """

        available = (
            self.is_ollama_available()
        )

        if not available:

            return {
                "available": False,
                "installed_models": [],
                "loaded_models": [],
            }

        return {
            "available": True,

            "installed_models": (
                self.get_installed_models()
            ),

            "loaded_models": (
                self.get_loaded_models()
            ),
        }

    # ==================================================
    # COMPLETE RESOURCE SNAPSHOT
    # ==================================================

    def get_resource_snapshot(
        self
    ) -> Dict[str, Any]:
        """
        Return a complete system resource snapshot.
        """

        return {
            "cpu": self.get_cpu_info(),

            "ram": self.get_ram_info(),

            "gpu": self.get_gpu_info(),

            "ollama": self.get_ollama_info(),
        }

    # ==================================================
    # HUMAN-READABLE SUMMARY
    # ==================================================

    def get_summary(self) -> str:
        """
        Return a human-readable resource summary.
        """

        snapshot = (
            self.get_resource_snapshot()
        )

        cpu = snapshot["cpu"]
        ram = snapshot["ram"]
        gpu = snapshot["gpu"]
        ollama = snapshot["ollama"]

        lines = [

            "V.A.U.L.T. Resource Snapshot",

            "=" * 40,

            "",

            "CPU:",

            f"Name: {cpu['name']}",

            (
                "Physical Cores: "
                f"{cpu['physical_cores']}"
            ),

            (
                "Logical Cores: "
                f"{cpu['logical_cores']}"
            ),

            (
                "Utilization: "
                f"{cpu['utilization_percent']}%"
            ),

            "",

            "RAM:",

            (
                f"Total: "
                f"{ram['total_gb']} GB"
            ),

            (
                f"Available: "
                f"{ram['available_gb']} GB"
            ),

            (
                f"Used: "
                f"{ram['used_gb']} GB"
            ),

            (
                "Utilization: "
                f"{ram['utilization_percent']}%"
            ),

            "",

            "GPU:",
        ]

        if gpu["available"]:

            lines.extend(

                [

                    (
                        f"Vendor: "
                        f"{gpu['vendor']}"
                    ),

                    (
                        f"Name: "
                        f"{gpu['name']}"
                    ),

                    (
                        "Total VRAM: "
                        f"{gpu['total_vram_gb']} GB"
                    ),

                    (
                        "Available VRAM: "
                        f"{gpu['available_vram_gb']} GB"
                    ),

                    (
                        "Utilization: "
                        f"{gpu['utilization_percent']}%"
                    ),

                ]
            )

        else:

            lines.append(
                "No supported GPU "
                "information available."
            )

        # ==============================================
        # OLLAMA
        # ==============================================

        lines.extend(

            [

                "",

                "Ollama:",

            ]
        )

        if not ollama["available"]:

            lines.append(
                "Ollama is not available."
            )

        else:

            lines.append(
                "Status: Available"
            )

            installed_models = (
                ollama["installed_models"]
            )

            lines.append(
                f"Installed Models: "
                f"{len(installed_models)}"
            )

            if installed_models:

                for model in installed_models:

                    lines.append(

                        (
                            f"  - {model['name']} "
                            f"({model['size']})"
                        )
                    )

            loaded_models = (
                ollama["loaded_models"]
            )

            lines.append("")

            lines.append(
                f"Loaded Models: "
                f"{len(loaded_models)}"
            )

            if loaded_models:

                for model in loaded_models:

                    lines.append(

                        (
                            f"  - {model['name']} "
                            f"({model['processor']})"
                        )
                    )

            else:

                lines.append(
                    "  None currently loaded."
                )

        return "\n".join(lines)