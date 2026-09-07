from typing import Any, Dict, List, Optional


class ModelProfiles:
    """
    Stores capability and resource profiles for known
    Ollama models used by V.A.U.L.T.

    These values are conservative estimates used for
    resource-planning decisions. They are not exact
    measurements of Ollama runtime memory usage.
    """

    def __init__(self):
        self.profiles = self._build_profiles()

    # ==================================================
    # MODEL PROFILES
    # ==================================================

    def _build_profiles(self) -> Dict[str, Dict[str, Any]]:
        """
        Define known model profiles.
        """

        return {

            # ==========================================
            # QWEN 3 - 1.7B
            # ==========================================

            "qwen3:1.7b": {
                "name": "qwen3:1.7b",

                "type": "language",

                "capabilities": [
                    "general",
                    "conversation",
                    "simple_reasoning",
                    "basic_coding",
                ],

                "supports_vision": False,

                # Conservative resource estimates.
                "estimated_ram_gb": 3.0,

                "estimated_vram_gb": 2.0,

                "priority": 1,

                "description": (
                    "Lightweight general-purpose language "
                    "model suitable for normal conversation "
                    "and simpler tasks."
                ),
            },

            # ==========================================
            # QWEN 3 - 4B
            # ==========================================

            "qwen3:4b": {
                "name": "qwen3:4b",

                "type": "language",

                "capabilities": [
                    "general",
                    "conversation",
                    "reasoning",
                    "complex_reasoning",
                    "coding",
                    "engineering",
                ],

                "supports_vision": False,

                # Conservative resource estimates.
                "estimated_ram_gb": 5.0,

                "estimated_vram_gb": 4.0,

                "priority": 2,

                "description": (
                    "More capable language model intended "
                    "for reasoning, coding, engineering, "
                    "and more complex tasks."
                ),
            },

            # ==========================================
            # QWEN 3 VL - 2B
            # ==========================================

            "qwen3-vl:2b": {
                "name": "qwen3-vl:2b",

                "type": "vision_language",

                "capabilities": [
                    "general",
                    "conversation",
                    "vision",
                    "image_analysis",
                    "document_visual_analysis",
                ],

                "supports_vision": True,

                # Conservative resource estimates.
                "estimated_ram_gb": 4.0,

                "estimated_vram_gb": 3.0,

                "priority": 2,

                "description": (
                    "Vision-language model capable of "
                    "analyzing images and visual content."
                ),
            },

            # ==========================================
            # NOMIC EMBEDDING MODEL
            # ==========================================

            "nomic-embed-text:latest": {
                "name": "nomic-embed-text:latest",

                "type": "embedding",

                "capabilities": [
                    "embedding",
                    "semantic_search",
                    "retrieval",
                ],

                "supports_vision": False,

                "estimated_ram_gb": 1.0,

                "estimated_vram_gb": 0.5,

                "priority": 0,

                "description": (
                    "Embedding model used for semantic "
                    "search, retrieval, and vector-based "
                    "memory systems."
                ),
            },
        }

    # ==================================================
    # GET PROFILE
    # ==================================================

    def get_profile(
        self,
        model_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve the profile for a specific model.

        Returns None if the model is unknown.
        """

        return self.profiles.get(
            model_name
        )

    # ==================================================
    # CHECK MODEL EXISTS
    # ==================================================

    def has_profile(
        self,
        model_name: str
    ) -> bool:
        """
        Check whether a profile exists.
        """

        return model_name in self.profiles

    # ==================================================
    # GET ALL PROFILES
    # ==================================================

    def get_all_profiles(
        self
    ) -> Dict[str, Dict[str, Any]]:
        """
        Return all known model profiles.
        """

        return self.profiles.copy()

    # ==================================================
    # GET MODEL NAMES
    # ==================================================

    def get_model_names(
        self
    ) -> List[str]:
        """
        Return all known model names.
        """

        return list(
            self.profiles.keys()
        )

    # ==================================================
    # FIND MODELS BY CAPABILITY
    # ==================================================

    def find_models_by_capability(
        self,
        capability: str
    ) -> List[Dict[str, Any]]:
        """
        Find all models supporting a capability.

        Results are sorted by priority from highest
        to lowest.
        """

        matches = []

        for profile in self.profiles.values():

            capabilities = profile.get(
                "capabilities",
                []
            )

            if capability in capabilities:

                matches.append(
                    profile.copy()
                )

        matches.sort(
            key=lambda profile: profile.get(
                "priority",
                0
            ),
            reverse=True
        )

        return matches

    # ==================================================
    # GET CAPABILITY MODELS
    # ==================================================

    def get_capable_models(
        self,
        required_capabilities: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Return models that support ALL required
        capabilities.

        Results are sorted by priority from highest
        to lowest.
        """

        if not required_capabilities:

            return []

        matches = []

        for profile in self.profiles.values():

            capabilities = set(
                profile.get(
                    "capabilities",
                    []
                )
            )

            required = set(
                required_capabilities
            )

            if required.issubset(
                capabilities
            ):

                matches.append(
                    profile.copy()
                )

        matches.sort(
            key=lambda profile: profile.get(
                "priority",
                0
            ),
            reverse=True
        )

        return matches

    # ==================================================
    # VISION MODELS
    # ==================================================

    def get_vision_models(
        self
    ) -> List[Dict[str, Any]]:
        """
        Return models capable of vision tasks.
        """

        matches = []

        for profile in self.profiles.values():

            if profile.get(
                "supports_vision",
                False
            ):

                matches.append(
                    profile.copy()
                )

        matches.sort(
            key=lambda profile: profile.get(
                "priority",
                0
            ),
            reverse=True
        )

        return matches

    # ==================================================
    # HUMAN-READABLE SUMMARY
    # ==================================================

    def get_summary(
        self
    ) -> str:
        """
        Return a readable summary of all profiles.
        """

        lines = [

            "V.A.U.L.T. Model Profiles",

            "=" * 40,

        ]

        for profile in self.profiles.values():

            lines.extend(

                [

                    "",

                    (
                        f"Model: "
                        f"{profile['name']}"
                    ),

                    (
                        f"Type: "
                        f"{profile['type']}"
                    ),

                    (
                        "Capabilities: "
                        f"{', '.join(profile['capabilities'])}"
                    ),

                    (
                        "Supports Vision: "
                        f"{profile['supports_vision']}"
                    ),

                    (
                        "Estimated RAM: "
                        f"{profile['estimated_ram_gb']} GB"
                    ),

                    (
                        "Estimated VRAM: "
                        f"{profile['estimated_vram_gb']} GB"
                    ),

                    (
                        f"Priority: "
                        f"{profile['priority']}"
                    ),

                    (
                        "Description: "
                        f"{profile['description']}"
                    ),

                ]
            )

        return "\n".join(lines)