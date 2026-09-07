from typing import Any, Dict, List, Optional

from models.model_profiles import ModelProfiles
from models.resource_feasibility import ResourceFeasibility
from models.resource_manager import ResourceManager


class SmartModelSelector:
    """
    Select the best installed model for a task.

    Selection strategy:

    1. Find installed models.
    2. Find models with the required capabilities.
    3. Prefer models currently considered safe.
    4. If no safe model exists, select the least demanding
       compatible model as a fallback.
    """

    def __init__(
        self,
        model_profiles: Optional[ModelProfiles] = None,
        resource_manager: Optional[ResourceManager] = None,
        feasibility: Optional[ResourceFeasibility] = None,
    ):
        self.model_profiles = (
            model_profiles
            if model_profiles is not None
            else ModelProfiles()
        )

        self.resource_manager = (
            resource_manager
            if resource_manager is not None
            else ResourceManager()
        )

        self.feasibility = (
            feasibility
            if feasibility is not None
            else ResourceFeasibility(
                resource_manager=self.resource_manager,
                model_profiles=self.model_profiles,
            )
        )

    # ==================================================
    # INSTALLED MODELS
    # ==================================================

    def get_installed_model_names(self) -> List[str]:
        """
        Return names of models currently installed in Ollama.
        """

        snapshot = (
            self.resource_manager.get_resource_snapshot()
        )

        ollama_info = snapshot.get(
            "ollama",
            {}
        )

        installed_models = ollama_info.get(
            "installed_models",
            []
        )

        model_names = []

        for model in installed_models:

            if isinstance(model, dict):

                name = model.get("name")

            else:

                name = str(model)

            if name:

                model_names.append(name)

        return model_names

    # ==================================================
    # CAPABILITY MATCHING
    # ==================================================

    def get_capable_installed_models(
        self,
        required_capabilities: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Return installed models that support all required
        capabilities.
        """

        installed_names = set(
            self.get_installed_model_names()
        )

        capable_models = (
            self.model_profiles.get_capable_models(
                required_capabilities
            )
        )

        results = []

        for profile in capable_models:

            model_name = profile.get("name")

            if model_name in installed_names:

                results.append(profile)

        return results

    # ==================================================
    # SAFE MODELS
    # ==================================================

    def get_safe_models(
        self,
        required_capabilities: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Return compatible models that currently pass the
        resource feasibility check.
        """

        capable_models = (
            self.get_capable_installed_models(
                required_capabilities
            )
        )

        safe_models = []

        for profile in capable_models:

            model_name = profile.get("name")

            feasibility_result = (
                self.feasibility.check_model(
                    model_name
                )
            )

            if feasibility_result.get(
                "safe",
                False
            ):

                safe_models.append(
                    feasibility_result
                )

        # Prefer higher priority models when safe.
        safe_models.sort(
            key=lambda result: (
                result.get(
                    "profile",
                    {}
                ).get(
                    "priority",
                    0
                )
            ),
            reverse=True,
        )

        return safe_models

    # ==================================================
    # FALLBACK MODELS
    # ==================================================

    def get_fallback_models(
        self,
        required_capabilities: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Return compatible installed models ordered from
        least resource-intensive to most resource-intensive.

        These models may not currently pass the strict
        feasibility check.
        """

        capable_models = (
            self.get_capable_installed_models(
                required_capabilities
            )
        )

        fallback_models = capable_models.copy()

        # Prefer the smallest model first when resources
        # are constrained.
        fallback_models.sort(
            key=lambda profile: (
                profile.get(
                    "estimated_ram_gb",
                    9999
                ),
                profile.get(
                    "estimated_vram_gb",
                    9999
                ),
                -profile.get(
                    "priority",
                    0
                ),
            )
        )

        return fallback_models

    # ==================================================
    # MAIN SELECTION
    # ==================================================

    def select_model(
        self,
        required_capabilities: List[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Select the best model.

        Priority:

        1. Highest-priority safe compatible model.
        2. Least demanding compatible fallback model.
        3. None if no compatible installed model exists.
        """

        safe_models = self.get_safe_models(
            required_capabilities
        )

        # ----------------------------------------------
        # SAFE MODEL FOUND
        # ----------------------------------------------

        if safe_models:

            selected = safe_models[0]

            return {
                "model": selected.get("model"),
                "status": "safe",
                "profile": selected.get(
                    "profile",
                    {}
                ),
                "feasibility": selected,
            }

        # ----------------------------------------------
        # FALLBACK MODEL
        # ----------------------------------------------

        fallback_models = self.get_fallback_models(
            required_capabilities
        )

        if fallback_models:

            profile = fallback_models[0]

            return {
                "model": profile.get("name"),
                "status": "fallback",
                "profile": profile,
                "feasibility": None,
            }

        # ----------------------------------------------
        # NOTHING AVAILABLE
        # ----------------------------------------------

        return None

    # ==================================================
    # SIMPLE MODEL NAME API
    # ==================================================

    def select_model_name(
        self,
        required_capabilities: List[str],
        fallback: Optional[str] = None,
    ) -> Optional[str]:
        """
        Return only the selected model name.
        """

        result = self.select_model(
            required_capabilities
        )

        if result is None:

            return fallback

        return result.get("model")

    # ==================================================
    # TASK TYPE → CAPABILITIES
    # ==================================================

    def get_capabilities_for_task(
        self,
        task_type: str,
    ) -> List[str]:
        """
        Convert V.A.U.L.T. task types into required
        model capabilities.
        """

        mapping = {

            "general": [
                "general",
                "conversation",
            ],

            "simple": [
                "general",
                "conversation",
            ],

            "classification": [
                "general",
                "conversation",
            ],

            "coding": [
                "coding",
            ],

            "complex": [
                "complex_reasoning",
            ],

            "engineering": [
                "engineering",
            ],

            "vision": [
                "vision",
            ],

            "document_visual": [
                "document_visual_analysis",
            ],

            "embedding": [
                "embedding",
            ],
        }

        return mapping.get(
            task_type,
            [
                "general",
                "conversation",
            ],
        )

    # ==================================================
    # SELECT FOR TASK TYPE
    # ==================================================

    def select_for_task(
        self,
        task_type: str,
        fallback: Optional[str] = None,
    ) -> Optional[str]:
        """
        Select the best model for a V.A.U.L.T. task.
        """

        capabilities = (
            self.get_capabilities_for_task(
                task_type
            )
        )

        return self.select_model_name(
            required_capabilities=capabilities,
            fallback=fallback,
        )

    # ==================================================
    # DETAILED REPORT
    # ==================================================

    def get_selection_report(
        self,
        required_capabilities: List[str],
    ) -> Dict[str, Any]:
        """
        Return detailed information about model selection.
        """

        installed_models = (
            self.get_installed_model_names()
        )

        capable_models = (
            self.get_capable_installed_models(
                required_capabilities
            )
        )

        safe_models = self.get_safe_models(
            required_capabilities
        )

        fallback_models = (
            self.get_fallback_models(
                required_capabilities
            )
        )

        selected = self.select_model(
            required_capabilities
        )

        return {

            "required_capabilities": (
                required_capabilities
            ),

            "installed_models": (
                installed_models
            ),

            "capable_models": [
                profile.get("name")
                for profile in capable_models
            ],

            "safe_models": [
                result.get("model")
                for result in safe_models
            ],

            "fallback_models": [
                profile.get("name")
                for profile in fallback_models
            ],

            "selected_model": (
                selected.get("model")
                if selected
                else None
            ),

            "selection_status": (
                selected.get("status")
                if selected
                else "unavailable"
            ),
        }

    # ==================================================
    # HUMAN-READABLE REPORT
    # ==================================================

    def get_readable_report(
        self,
        required_capabilities: List[str],
    ) -> str:
        """
        Return a human-readable model selection report.
        """

        report = self.get_selection_report(
            required_capabilities
        )

        lines = [

            "V.A.U.L.T. Smart Model Selection",

            "=" * 40,

            "",

            "Required Capabilities: "
            + ", ".join(
                report[
                    "required_capabilities"
                ]
            ),

            "",

            "Installed Models:",
        ]

        installed_models = report[
            "installed_models"
        ]

        if installed_models:

            for model in installed_models:

                lines.append(
                    f"- {model}"
                )

        else:

            lines.append(
                "- None detected"
            )

        # ----------------------------------------------

        lines.extend([

            "",

            "Capable Installed Models:",

        ])

        capable_models = report[
            "capable_models"
        ]

        if capable_models:

            for model in capable_models:

                lines.append(
                    f"- {model}"
                )

        else:

            lines.append(
                "- None"
            )

        # ----------------------------------------------

        lines.extend([

            "",

            "Safe Models:",

        ])

        safe_models = report[
            "safe_models"
        ]

        if safe_models:

            for model in safe_models:

                lines.append(
                    f"- {model}"
                )

        else:

            lines.append(
                "- None currently safe"
            )

        # ----------------------------------------------

        lines.extend([

            "",

            "Fallback Models:",

        ])

        fallback_models = report[
            "fallback_models"
        ]

        if fallback_models:

            for model in fallback_models:

                lines.append(
                    f"- {model}"
                )

        else:

            lines.append(
                "- None"
            )

        # ----------------------------------------------

        lines.extend([

            "",

            "Selected Model:",

        ])

        selected_model = report[
            "selected_model"
        ]

        selection_status = report[
            "selection_status"
        ]

        if selected_model:

            lines.append(
                selected_model
            )

            lines.append(
                f"Selection Status: "
                f"{selection_status}"
            )

        else:

            lines.append(
                "No suitable model available."
            )

        return "\n".join(lines)