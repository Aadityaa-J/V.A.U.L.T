"""
V.A.U.L.T. Ollama Model Manager

Responsible for:

- Detecting Ollama availability
- Listing installed models
- Listing running models
- Checking whether a model is installed
- Selecting available fallback models
"""

from typing import Any, Dict, List, Optional
import subprocess


class ModelManager:

    def __init__(self):

        self.configured_models = [
            "qwen3:1.7b",
            "qwen3:4b",
            "qwen3-vl:2b",
        ]

    # ==========================================================
    # OLLAMA AVAILABILITY
    # ==========================================================

    def is_ollama_available(self) -> bool:

        try:

            subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            return True

        except Exception:

            return False

    # ==========================================================
    # INSTALLED MODELS
    # ==========================================================

    def get_installed_models(
        self,
    ) -> List[str]:

        if not self.is_ollama_available():

            return []

        try:

            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )

            if result.returncode != 0:

                return []

            lines = result.stdout.splitlines()

            models = []

            # Skip header line.
            for line in lines[1:]:

                parts = line.split()

                if not parts:
                    continue

                model_name = parts[0]

                models.append(
                    model_name
                )

            return models

        except Exception:

            return []

    # ==========================================================
    # RUNNING MODELS
    # ==========================================================

    def get_running_models(
        self,
    ) -> List[str]:

        if not self.is_ollama_available():

            return []

        try:

            result = subprocess.run(
                ["ollama", "ps"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )

            if result.returncode != 0:

                return []

            lines = result.stdout.splitlines()

            models = []

            for line in lines[1:]:

                parts = line.split()

                if not parts:
                    continue

                models.append(
                    parts[0]
                )

            return models

        except Exception:

            return []

    # ==========================================================
    # MODEL INSTALLED CHECK
    # ==========================================================

    def is_model_installed(
        self,
        model_name: str,
    ) -> bool:

        if not isinstance(
            model_name,
            str,
        ):

            return False

        model_name = (
            model_name.strip()
        )

        if not model_name:

            return False

        installed_models = (
            self.get_installed_models()
        )

        return (
            model_name
            in installed_models
        )

    # ==========================================================
    # CONFIGURED MODEL STATUS
    # ==========================================================

    def get_configured_model_status(
        self,
    ) -> Dict[str, Dict[str, bool]]:

        installed_models = (
            self.get_installed_models()
        )

        running_models = (
            self.get_running_models()
        )

        result = {}

        for model in self.configured_models:

            result[model] = {

                "installed":
                    model
                    in installed_models,

                "running":
                    model
                    in running_models,

            }

        return result

    # ==========================================================
    # FIND AVAILABLE MODEL
    # ==========================================================

    def get_available_model(
        self,
        preferred_models: List[str],
    ) -> Optional[str]:

        if not preferred_models:

            return None

        installed_models = (
            self.get_installed_models()
        )

        for model in preferred_models:

            if model in installed_models:

                return model

        return None

    # ==========================================================
    # MODEL REPORT
    # ==========================================================

    def get_model_report(
        self,
    ) -> Dict[str, Any]:

        ollama_available = (
            self.is_ollama_available()
        )

        installed_models = (
            self.get_installed_models()
        )

        running_models = (
            self.get_running_models()
        )

        return {

            "ollama_available":
                ollama_available,

            "installed_models":
                installed_models,

            "running_models":
                running_models,

            "configured_models":
                self.configured_models,

            "configured_model_status":
                self.get_configured_model_status(),

        }

    # ==========================================================
    # PRINT REPORT
    # ==========================================================

    def print_report(
        self,
    ) -> None:

        report = (
            self.get_model_report()
        )

        print()

        print("=" * 60)
        print(
            "V.A.U.L.T. OLLAMA MODEL MANAGER"
        )
        print("=" * 60)

        print()

        print("OLLAMA")

        print("-" * 60)

        print(
            f"Available: "
            f"{report['ollama_available']}"
        )

        print()

        print("INSTALLED MODELS")

        print("-" * 60)

        installed_models = (
            report[
                "installed_models"
            ]
        )

        if not installed_models:

            print(
                "No Ollama models found."
            )

        else:

            for model in installed_models:

                print(
                    f"- {model}"
                )

        print()

        print("RUNNING MODELS")

        print("-" * 60)

        running_models = (
            report[
                "running_models"
            ]
        )

        if not running_models:

            print(
                "No models currently running."
            )

        else:

            for model in running_models:

                print(
                    f"- {model}"
                )

        print()

        print(
            "V.A.U.L.T. CONFIGURED MODELS"
        )

        print("-" * 60)

        status = report[
            "configured_model_status"
        ]

        for model, info in status.items():

            print()

            print(
                f"Model: {model}"
            )

            print(
                f"Installed: "
                f"{info['installed']}"
            )

            print(
                f"Running: "
                f"{info['running']}"
            )

        print()

        print("=" * 60)
        print(
            "MODEL MANAGER TEST COMPLETE"
        )
        print("=" * 60)


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    manager = ModelManager()

    manager.print_report()