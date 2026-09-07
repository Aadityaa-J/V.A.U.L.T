from typing import Any, Dict, List, Optional

from models.resource_manager import ResourceManager
from models.model_profiles import ModelProfiles


class ResourceFeasibility:
    """
    Determines whether an Ollama model can safely run
    based on current system resources.

    Uses:
    - Current available RAM
    - Current available VRAM
    - Model resource profiles
    - Configurable safety buffers
    """

    def __init__(
        self,
        resource_manager: Optional[ResourceManager] = None,
        model_profiles: Optional[ModelProfiles] = None,
        ram_safety_buffer_gb: float = 1.5,
        vram_safety_buffer_gb: float = 0.5,
    ):
        self.resource_manager = (
            resource_manager
            if resource_manager is not None
            else ResourceManager()
        )

        self.model_profiles = (
            model_profiles
            if model_profiles is not None
            else ModelProfiles()
        )

        self.ram_safety_buffer_gb = (
            ram_safety_buffer_gb
        )

        self.vram_safety_buffer_gb = (
            vram_safety_buffer_gb
        )

    # ==================================================
    # RESOURCE HELPERS
    # ==================================================

    def _get_usable_ram(
        self,
        ram_info: Dict[str, Any]
    ) -> Optional[float]:
        """
        Calculate RAM available for model usage
        after reserving a safety buffer.
        """

        available_ram = ram_info.get(
            "available_gb"
        )

        if available_ram is None:
            return None

        usable_ram = (
            available_ram
            - self.ram_safety_buffer_gb
        )

        return max(
            round(usable_ram, 2),
            0.0
        )

    def _get_usable_vram(
        self,
        gpu_info: Dict[str, Any]
    ) -> Optional[float]:
        """
        Calculate VRAM available for model usage
        after reserving a safety buffer.
        """

        if not gpu_info.get(
            "available",
            False
        ):
            return None

        available_vram = gpu_info.get(
            "available_vram_gb"
        )

        if available_vram is None:
            return None

        usable_vram = (
            available_vram
            - self.vram_safety_buffer_gb
        )

        return max(
            round(usable_vram, 2),
            0.0
        )

    # ==================================================
    # MODEL CHECK
    # ==================================================

    def check_model(
        self,
        model_name: str
    ) -> Dict[str, Any]:
        """
        Check whether a specific model can safely run
        with the current system resources.
        """

        profile = (
            self.model_profiles.get_profile(
                model_name
            )
        )

        if profile is None:

            return {
                "model": model_name,
                "known_model": False,
                "safe": False,
                "reasons": [
                    "No resource profile exists "
                    "for this model."
                ],
            }

        snapshot = (
            self.resource_manager
            .get_resource_snapshot()
        )

        ram_info = snapshot.get(
            "ram",
            {}
        )

        gpu_info = snapshot.get(
            "gpu",
            {}
        )

        required_ram = profile.get(
            "estimated_ram_gb",
            0.0
        )

        required_vram = profile.get(
            "estimated_vram_gb",
            0.0
        )

        usable_ram = self._get_usable_ram(
            ram_info
        )

        usable_vram = self._get_usable_vram(
            gpu_info
        )

        reasons = []

        ram_safe = True
        vram_safe = True

        # ----------------------------------------------
        # RAM CHECK
        # ----------------------------------------------

        if usable_ram is None:

            ram_safe = False

            reasons.append(
                "Available RAM could not be detected."
            )

        elif usable_ram < required_ram:

            ram_safe = False

            reasons.append(
                f"Insufficient usable RAM. "
                f"Requires approximately "
                f"{required_ram} GB but only "
                f"{usable_ram} GB is currently "
                f"available after the safety buffer."
            )

        # ----------------------------------------------
        # VRAM CHECK
        # ----------------------------------------------

        if required_vram > 0:

            if usable_vram is None:

                # No GPU information does not automatically
                # mean failure. The model may still run using
                # CPU/RAM, but it will not have enough confirmed
                # VRAM for the estimated GPU requirement.

                vram_safe = False

                reasons.append(
                    "Required VRAM cannot be confirmed "
                    "because no supported GPU information "
                    "is available."
                )

            elif usable_vram < required_vram:

                vram_safe = False

                reasons.append(
                    f"Insufficient usable VRAM. "
                    f"Requires approximately "
                    f"{required_vram} GB but only "
                    f"{usable_vram} GB is currently "
                    f"available after the safety buffer."
                )

        safe = (
            ram_safe
            and vram_safe
        )

        if safe:

            reasons.append(
                "Current resources meet the estimated "
                "requirements for this model."
            )

        return {
            "model": model_name,

            "known_model": True,

            "safe": safe,

            "profile": profile,

            "requirements": {

                "ram_gb": required_ram,

                "vram_gb": required_vram,

            },

            "current_resources": {

                "available_ram_gb": (
                    ram_info.get(
                        "available_gb"
                    )
                ),

                "usable_ram_gb": usable_ram,

                "available_vram_gb": (
                    gpu_info.get(
                        "available_vram_gb"
                    )
                ),

                "usable_vram_gb": usable_vram,

            },

            "safety_buffers": {

                "ram_gb": (
                    self.ram_safety_buffer_gb
                ),

                "vram_gb": (
                    self.vram_safety_buffer_gb
                ),

            },

            "ram_safe": ram_safe,

            "vram_safe": vram_safe,

            "reasons": reasons,
        }

    # ==================================================
    # CHECK MULTIPLE MODELS
    # ==================================================

    def check_models(
        self,
        model_names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Check multiple models.
        """

        results = []

        for model_name in model_names:

            result = self.check_model(
                model_name
            )

            results.append(result)

        return results

    # ==================================================
    # FIND SAFE MODELS
    # ==================================================

    def find_safe_models(
        self
    ) -> List[Dict[str, Any]]:
        """
        Find all known models that are currently
        considered safe to run.
        """

        safe_models = []

        model_names = (
            self.model_profiles.get_model_names()
        )

        for model_name in model_names:

            result = self.check_model(
                model_name
            )

            if result.get(
                "safe",
                False
            ):

                safe_models.append(
                    result
                )

        safe_models.sort(
            key=lambda item: item[
                "profile"
            ].get(
                "priority",
                0
            ),
            reverse=True
        )

        return safe_models

    # ==================================================
    # FIND SAFE MODELS BY CAPABILITY
    # ==================================================

    def find_safe_models_by_capability(
        self,
        required_capabilities: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Find models that:

        1. Support all requested capabilities.
        2. Are currently safe to run.
        """

        capable_models = (
            self.model_profiles.get_capable_models(
                required_capabilities
            )
        )

        safe_models = []

        for profile in capable_models:

            model_name = profile["name"]

            result = self.check_model(
                model_name
            )

            if result.get(
                "safe",
                False
            ):

                safe_models.append(
                    result
                )

        safe_models.sort(
            key=lambda item: item[
                "profile"
            ].get(
                "priority",
                0
            ),
            reverse=True
        )

        return safe_models

    # ==================================================
    # FIND BEST MODEL
    # ==================================================

    def find_best_model(
        self,
        required_capabilities: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Find the highest-priority model that:

        - Supports all required capabilities.
        - Is currently safe to run.

        Returns None if no suitable model is found.
        """

        safe_models = (
            self.find_safe_models_by_capability(
                required_capabilities
            )
        )

        if not safe_models:

            return None

        return safe_models[0]

    # ==================================================
    # INSTALLED MODEL FILTER
    # ==================================================

    def find_safe_installed_models(
        self
    ) -> List[Dict[str, Any]]:
        """
        Find safe models that are actually installed
        in Ollama.

        This prevents V.A.U.L.T. from recommending
        models that exist in profiles but are not
        installed on the machine.
        """

        snapshot = (
            self.resource_manager
            .get_resource_snapshot()
        )

        ollama_info = snapshot.get(
            "ollama",
            {}
        )

        installed_models = (
            ollama_info.get(
                "installed_models",
                []
            )
        )

        installed_names = {

            model.get("name")

            for model in installed_models

            if model.get("name")

        }

        safe_models = []

        for model_name in installed_names:

            result = self.check_model(
                model_name
            )

            if result.get(
                "safe",
                False
            ):

                safe_models.append(
                    result
                )

        safe_models.sort(
            key=lambda item: item[
                "profile"
            ].get(
                "priority",
                0
            ),
            reverse=True
        )

        return safe_models

    # ==================================================
    # HUMAN-READABLE MODEL REPORT
    # ==================================================

    def get_model_report(
        self,
        model_name: str
    ) -> str:
        """
        Return a readable report for one model.
        """

        result = self.check_model(
            model_name
        )

        lines = [

            "V.A.U.L.T. Model Resource Check",

            "=" * 40,

            "",

            f"Model: {model_name}",

            (
                "Known Profile: "
                f"{result.get('known_model')}"
            ),

            (
                "Safe to Run: "
                f"{result.get('safe')}"
            ),

        ]

        if not result.get(
            "known_model",
            False
        ):

            lines.extend(

                [

                    "",

                    "Reason:",

                ]
            )

            for reason in result.get(
                "reasons",
                []
            ):

                lines.append(
                    f"- {reason}"
                )

            return "\n".join(lines)

        requirements = result[
            "requirements"
        ]

        resources = result[
            "current_resources"
        ]

        buffers = result[
            "safety_buffers"
        ]

        lines.extend(

            [

                "",

                "Requirements:",

                (
                    "Estimated RAM: "
                    f"{requirements['ram_gb']} GB"
                ),

                (
                    "Estimated VRAM: "
                    f"{requirements['vram_gb']} GB"
                ),

                "",

                "Current Resources:",

                (
                    "Available RAM: "
                    f"{resources['available_ram_gb']} GB"
                ),

                (
                    "Usable RAM after buffer: "
                    f"{resources['usable_ram_gb']} GB"
                ),

                (
                    "Available VRAM: "
                    f"{resources['available_vram_gb']} GB"
                ),

                (
                    "Usable VRAM after buffer: "
                    f"{resources['usable_vram_gb']} GB"
                ),

                "",

                "Safety Buffers:",

                (
                    "RAM Buffer: "
                    f"{buffers['ram_gb']} GB"
                ),

                (
                    "VRAM Buffer: "
                    f"{buffers['vram_gb']} GB"
                ),

                "",

                "Assessment:",

                (
                    "RAM Safe: "
                    f"{result['ram_safe']}"
                ),

                (
                    "VRAM Safe: "
                    f"{result['vram_safe']}"
                ),

                "",

                "Reasons:",

            ]
        )

        for reason in result.get(
            "reasons",
            []
        ):

            lines.append(
                f"- {reason}"
            )

        return "\n".join(lines)