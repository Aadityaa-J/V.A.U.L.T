"""
V.A.U.L.T. Hardware Manager

Detects:

- Operating system
- CPU
- System RAM
- NVIDIA GPUs
- GPU VRAM
- Basic hardware capability profile

The module is designed to work on Windows and gracefully
fall back when optional system commands are unavailable.
"""

from __future__ import annotations

import platform
import subprocess
from typing import Any, Dict, List


class HardwareManager:
    """
    Detect and report system hardware information.
    """

    def __init__(self):
        self._hardware_cache = None

    # ==========================================================
    # PUBLIC API
    # ==========================================================

    def get_hardware_info(self) -> Dict[str, Any]:
        """
        Return complete hardware information.
        """

        if self._hardware_cache is not None:
            return self._hardware_cache

        hardware = {
            "system": self.get_system_info(),
            "cpu": self.get_cpu_info(),
            "ram": self.get_ram_info(),
            "gpus": self.get_gpu_info(),
        }

        self._hardware_cache = hardware

        return hardware

    def refresh(self) -> Dict[str, Any]:
        """
        Clear cached information and detect hardware again.
        """

        self._hardware_cache = None

        return self.get_hardware_info()

    # ==========================================================
    # SYSTEM
    # ==========================================================

    def get_system_info(self) -> Dict[str, Any]:
        """
        Detect operating system information.
        """

        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "architecture": platform.architecture()[0],
            "processor": platform.processor(),
        }

    # ==========================================================
    # CPU
    # ==========================================================

    def get_cpu_info(self) -> Dict[str, Any]:
        """
        Detect CPU information.
        """

        logical_cores = None
        physical_cores = None

        try:
            import os

            logical_cores = os.cpu_count()

        except Exception:
            logical_cores = None

        # Try psutil if installed.

        try:
            import psutil

            physical_cores = psutil.cpu_count(
                logical=False
            )

            if logical_cores is None:

                logical_cores = psutil.cpu_count(
                    logical=True
                )

        except Exception:
            pass

        return {
            "name": platform.processor()
            or "Unknown CPU",

            "physical_cores": physical_cores,

            "logical_cores": logical_cores,
        }

    # ==========================================================
    # RAM
    # ==========================================================

    def get_ram_info(self) -> Dict[str, Any]:
        """
        Detect total and available system RAM.
        """

        try:
            import psutil

            memory = psutil.virtual_memory()

            return {
                "total_bytes": memory.total,

                "available_bytes": memory.available,

                "used_bytes": memory.used,

                "total_gb": round(
                    memory.total / (1024 ** 3),
                    2,
                ),

                "available_gb": round(
                    memory.available / (1024 ** 3),
                    2,
                ),

                "used_gb": round(
                    memory.used / (1024 ** 3),
                    2,
                ),

                "percent_used": memory.percent,
            }

        except Exception:

            return {
                "total_bytes": None,
                "available_bytes": None,
                "used_bytes": None,
                "total_gb": None,
                "available_gb": None,
                "used_gb": None,
                "percent_used": None,
            }

    # ==========================================================
    # GPU DETECTION
    # ==========================================================

    def get_gpu_info(self) -> List[Dict[str, Any]]:
        """
        Detect available GPUs.

        NVIDIA GPUs are detected using nvidia-smi when
        available.

        Falls back to WMIC / PowerShell detection on Windows.
        """

        nvidia_gpus = self._get_nvidia_gpus()

        if nvidia_gpus:

            return nvidia_gpus

        windows_gpus = self._get_windows_gpus()

        if windows_gpus:

            return windows_gpus

        return []

    # ==========================================================
    # NVIDIA GPU
    # ==========================================================

    def _get_nvidia_gpus(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Detect NVIDIA GPUs using nvidia-smi.
        """

        command = [

            "nvidia-smi",

            "--query-gpu="
            "name,"
            "memory.total,"
            "memory.used,"
            "memory.free",

            "--format=csv,noheader,nounits",
        ]

        try:

            result = subprocess.run(

                command,

                capture_output=True,

                text=True,

                timeout=5,

            )

            if result.returncode != 0:

                return []

        except (

            FileNotFoundError,

            subprocess.TimeoutExpired,

            OSError,

        ):

            return []

        gpus = []

        lines = (

            result.stdout

            .strip()

            .splitlines()

        )

        for index, line in enumerate(
            lines
        ):

            parts = [

                part.strip()

                for part in line.split(",")

            ]

            if len(parts) < 4:

                continue

            try:

                total_mb = float(
                    parts[1]
                )

                used_mb = float(
                    parts[2]
                )

                free_mb = float(
                    parts[3]
                )

            except ValueError:

                total_mb = None

                used_mb = None

                free_mb = None

            gpu = {

                "index": index,

                "name": parts[0],

                "vendor": "NVIDIA",

                "vram_total_mb": total_mb,

                "vram_used_mb": used_mb,

                "vram_free_mb": free_mb,

                "vram_total_gb": (
                    round(
                        total_mb / 1024,
                        2,
                    )
                    if total_mb is not None
                    else None
                ),

                "vram_used_gb": (
                    round(
                        used_mb / 1024,
                        2,
                    )
                    if used_mb is not None
                    else None
                ),

                "vram_free_gb": (
                    round(
                        free_mb / 1024,
                        2,
                    )
                    if free_mb is not None
                    else None
                ),

                "backend": "nvidia-smi",

            }

            gpus.append(
                gpu
            )

        return gpus

    # ==========================================================
    # WINDOWS FALLBACK GPU DETECTION
    # ==========================================================

    def _get_windows_gpus(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Detect GPUs on Windows using PowerShell.

        VRAM information may not always be available through
        this fallback method.
        """

        if platform.system() != "Windows":

            return []

        command = [

            "powershell",

            "-NoProfile",

            "-Command",

            (
                "Get-CimInstance "
                "Win32_VideoController | "
                "Select-Object "
                "Name,AdapterRAM | "
                "ConvertTo-Csv -NoTypeInformation"
            ),

        ]

        try:

            result = subprocess.run(

                command,

                capture_output=True,

                text=True,

                timeout=8,

            )

            if result.returncode != 0:

                return []

        except (

            FileNotFoundError,

            subprocess.TimeoutExpired,

            OSError,

        ):

            return []

        lines = [

            line.strip()

            for line in result.stdout.splitlines()

            if line.strip()

        ]

        if len(lines) <= 1:

            return []

        import csv
        from io import StringIO

        gpus = []

        try:

            reader = csv.DictReader(

                StringIO(
                    "\n".join(lines)
                )
            )

            for index, row in enumerate(
                reader
            ):

                name = row.get(
                    "Name",
                    "Unknown GPU",
                )

                adapter_ram = row.get(
                    "AdapterRAM"
                )

                try:

                    vram_bytes = int(
                        adapter_ram
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    vram_bytes = None

                vendor = self._detect_vendor(
                    name
                )

                gpus.append(

                    {

                        "index": index,

                        "name": name,

                        "vendor": vendor,

                        "vram_total_mb": (
                            round(
                                vram_bytes
                                / (1024 ** 2),
                                2,
                            )
                            if vram_bytes
                            else None
                        ),

                        "vram_used_mb": None,

                        "vram_free_mb": None,

                        "vram_total_gb": (
                            round(
                                vram_bytes
                                / (1024 ** 3),
                                2,
                            )
                            if vram_bytes
                            else None
                        ),

                        "vram_used_gb": None,

                        "vram_free_gb": None,

                        "backend": "windows",

                    }

                )

        except Exception:

            return []

        return gpus

    # ==========================================================
    # GPU VENDOR DETECTION
    # ==========================================================

    def _detect_vendor(
        self,
        name: str,
    ) -> str:

        name_lower = (
            name.lower()
        )

        if "nvidia" in name_lower:

            return "NVIDIA"

        if (
            "amd" in name_lower
            or "radeon" in name_lower
        ):

            return "AMD"

        if (
            "intel" in name_lower
        ):

            return "Intel"

        return "Unknown"

    # ==========================================================
    # HARDWARE PROFILE
    # ==========================================================

    def get_hardware_profile(
        self,
    ) -> Dict[str, Any]:
        """
        Generate a simplified hardware capability profile.
        """

        hardware = (
            self.get_hardware_info()
        )

        ram = (
            hardware.get(
                "ram",
                {},
            )
        )

        gpus = (
            hardware.get(
                "gpus",
                [],
            )
        )

        total_ram_gb = (
            ram.get(
                "total_gb"
            )
        )

        best_gpu = (
            self._get_best_gpu(
                gpus
            )
        )

        vram_gb = None

        gpu_available = False

        if best_gpu:

            gpu_available = True

            vram_gb = (
                best_gpu.get(
                    "vram_total_gb"
                )
            )

        profile = {

            "gpu_available": (
                gpu_available
            ),

            "best_gpu": (
                best_gpu
            ),

            "system_ram_gb": (
                total_ram_gb
            ),

            "gpu_vram_gb": (
                vram_gb
            ),

            "hardware_class": (
                self._classify_hardware(
                    ram_gb=total_ram_gb,
                    vram_gb=vram_gb,
                )
            ),

        }

        return profile

    # ==========================================================
    # BEST GPU
    # ==========================================================

    def _get_best_gpu(
        self,
        gpus: List[Dict[str, Any]],
    ) -> Dict[str, Any] | None:

        if not gpus:

            return None

        def gpu_score(
            gpu
        ):

            vram = gpu.get(
                "vram_total_gb"
            )

            if vram is None:

                return 0

            return vram

        return max(
            gpus,
            key=gpu_score,
        )

    # ==========================================================
    # HARDWARE CLASSIFICATION
    # ==========================================================

    def _classify_hardware(
        self,
        ram_gb,
        vram_gb,
    ) -> str:
        """
        Classify the machine into a general hardware tier.
        """

        if (
            vram_gb is not None
            and vram_gb >= 16
        ):

            return "high"

        if (
            vram_gb is not None
            and vram_gb >= 8
        ):

            return "medium"

        if (
            ram_gb is not None
            and ram_gb >= 16
        ):

            return "standard"

        return "low"

    # ==========================================================
    # READABLE REPORT
    # ==========================================================

    def get_readable_report(
        self,
    ) -> str:
        """
        Return a human-readable hardware report.
        """

        hardware = (
            self.get_hardware_info()
        )

        profile = (
            self.get_hardware_profile()
        )

        system = hardware["system"]

        cpu = hardware["cpu"]

        ram = hardware["ram"]

        gpus = hardware["gpus"]

        lines = []

        lines.append(
            "=" * 60
        )

        lines.append(
            "V.A.U.L.T. HARDWARE REPORT"
        )

        lines.append(
            "=" * 60
        )

        lines.append("")

        # SYSTEM

        lines.append(
            "SYSTEM"
        )

        lines.append(
            "-" * 60
        )

        lines.append(
            f"Operating System: "
            f"{system['system']} "
            f"{system['release']}"
        )

        lines.append(
            f"Architecture: "
            f"{system['architecture']}"
        )

        lines.append("")

        # CPU

        lines.append(
            "CPU"
        )

        lines.append(
            "-" * 60
        )

        lines.append(
            f"Processor: "
            f"{cpu['name']}"
        )

        lines.append(
            f"Physical Cores: "
            f"{cpu['physical_cores']}"
        )

        lines.append(
            f"Logical Cores: "
            f"{cpu['logical_cores']}"
        )

        lines.append("")

        # RAM

        lines.append(
            "SYSTEM RAM"
        )

        lines.append(
            "-" * 60
        )

        lines.append(
            f"Total RAM: "
            f"{ram['total_gb']} GB"
        )

        lines.append(
            f"Available RAM: "
            f"{ram['available_gb']} GB"
        )

        lines.append(
            f"Used RAM: "
            f"{ram['used_gb']} GB"
        )

        lines.append(
            f"RAM Usage: "
            f"{ram['percent_used']}%"
        )

        lines.append("")

        # GPU

        lines.append(
            "GPU"
        )

        lines.append(
            "-" * 60
        )

        if not gpus:

            lines.append(
                "No GPU information detected."
            )

        else:

            for gpu in gpus:

                lines.append(
                    f"GPU {gpu['index']}: "
                    f"{gpu['name']}"
                )

                lines.append(
                    f"Vendor: "
                    f"{gpu['vendor']}"
                )

                lines.append(
                    f"Total VRAM: "
                    f"{gpu['vram_total_gb']} GB"
                )

                lines.append(
                    f"Free VRAM: "
                    f"{gpu['vram_free_gb']} GB"
                )

                lines.append(
                    f"Detection Backend: "
                    f"{gpu['backend']}"
                )

                lines.append("")

        # PROFILE

        lines.append(
            "HARDWARE PROFILE"
        )

        lines.append(
            "-" * 60
        )

        lines.append(
            f"Hardware Class: "
            f"{profile['hardware_class']}"
        )

        lines.append(
            f"GPU Available: "
            f"{profile['gpu_available']}"
        )

        lines.append(
            f"Best GPU: "
            f"{profile['best_gpu']}"
        )

        lines.append(
            f"GPU VRAM: "
            f"{profile['gpu_vram_gb']} GB"
        )

        lines.append("")

        return "\n".join(
            lines
        )


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    manager = HardwareManager()

    print(
        manager.get_readable_report()
    )