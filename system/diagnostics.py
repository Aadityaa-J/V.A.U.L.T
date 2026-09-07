"""
V.A.U.L.T. System Diagnostics

Checks whether the main components of V.A.U.L.T.
are installed and functioning correctly.
"""

import sys
import platform
import importlib


def print_header(title: str) -> None:
    """Print a formatted section header."""

    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def check_python() -> bool:
    """Check Python version."""

    print_header("PYTHON")

    version = sys.version_info

    print(
        f"Python Version: "
        f"{version.major}."
        f"{version.minor}."
        f"{version.micro}"
    )

    print(
        f"Platform: "
        f"{platform.system()} "
        f"{platform.release()}"
    )

    if version.major >= 3:

        print("Status: OK")

        return True

    print("Status: FAILED")

    return False


def check_module(
    module_name: str
) -> bool:
    """
    Check whether a Python module can be imported.
    """

    try:

        importlib.import_module(
            module_name
        )

        print(
            f"[OK] {module_name}"
        )

        return True

    except Exception as exc:

        print(
            f"[FAILED] {module_name}"
        )

        print(
            f"Reason: {exc}"
        )

        return False


def check_core_modules() -> bool:
    """
    Check V.A.U.L.T. core modules.
    """

    print_header(
        "CORE MODULES"
    )

    modules = [

        "config.config",

        "models.router",
        "models.llm",

        "agents.orchestrator",
        "agents.task_classifier",
        "agents.validation_loop",
        "agents.agent_loop",

        "tools.registry",
        "tools.adapters",
        "tools.calculations",

    ]

    results = []

    for module in modules:

        result = check_module(
            module
        )

        results.append(
            result
        )

    return all(
        results
    )


def check_ollama() -> bool:
    """
    Check whether the Ollama Python package
    can be imported.
    """

    print_header(
        "OLLAMA"
    )

    try:

        import ollama

        print(
            "[OK] Ollama Python package"
        )

        return True

    except Exception as exc:

        print(
            "[FAILED] Ollama Python package"
        )

        print(
            f"Reason: {exc}"
        )

        return False


def check_configuration() -> bool:
    """
    Check configured V.A.U.L.T. models.
    """

    print_header(
        "MODEL CONFIGURATION"
    )

    try:

        from config.config import (
            FAST_MODEL,
            MAIN_MODEL,
            VISION_MODEL,
        )

        print(
            f"FAST_MODEL: "
            f"{FAST_MODEL}"
        )

        print(
            f"MAIN_MODEL: "
            f"{MAIN_MODEL}"
        )

        print(
            f"VISION_MODEL: "
            f"{VISION_MODEL}"
        )

        print(
            "Status: OK"
        )

        return True

    except Exception as exc:

        print(
            "Status: FAILED"
        )

        print(
            f"Reason: {exc}"
        )

        return False


def run_diagnostics() -> dict:
    """
    Run all V.A.U.L.T. diagnostics.
    """

    print()

    print("=" * 60)
    print(
        "V.A.U.L.T. SYSTEM DIAGNOSTICS"
    )
    print("=" * 60)

    results = {}

    results[
        "python"
    ] = check_python()

    results[
        "core_modules"
    ] = check_core_modules()

    results[
        "ollama"
    ] = check_ollama()

    results[
        "configuration"
    ] = check_configuration()

    print_header(
        "FINAL RESULT"
    )

    passed = sum(
        results.values()
    )

    total = len(
        results
    )

    print(
        f"Checks Passed: "
        f"{passed}/{total}"
    )

    if all(
        results.values()
    ):

        print()

        print(
            "V.A.U.L.T. SYSTEM STATUS: HEALTHY"
        )

        status = "healthy"

    else:

        print()

        print(
            "V.A.U.L.T. SYSTEM STATUS: ISSUES DETECTED"
        )

        status = "issues_detected"

    return {

        "status": status,

        "checks": results,

        "passed": passed,

        "total": total,

    }


if __name__ == "__main__":

    run_diagnostics()