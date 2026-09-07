"""
V.A.U.L.T. Smart Model Router

Selects the most appropriate local model based on:

- Task type
- Approved fine-tuned models
- System performance
- Available VRAM
"""

from typing import Optional, Dict, Any

from config.config import (
    FAST_MODEL,
    MAIN_MODEL,
    VISION_MODEL,
)

from system.vram_manager import VRAMManager
from system.performance_manager import PerformanceManager

from models.fine_tuning.model_selector import (
    FineTunedModelSelector,
)


# =========================================================
# TASK CLASSIFICATION
# =========================================================

def classify_task(
    prompt: str,
    image_path: Optional[str] = None,
) -> str:

    """Classify a request for model selection."""

    if image_path:
        return "visual"

    if not isinstance(prompt, str):
        raise TypeError(
            "Prompt must be a string."
        )

    prompt_lower = prompt.lower().strip()

    if not prompt_lower:
        return "simple"

    document_keywords = [
        "document",
        "file",
        "pdf",
        "csv",
        "json",
        "markdown",
        "summarize document",
        "read document",
        "search document",
    ]

    if any(
        keyword in prompt_lower
        for keyword in document_keywords
    ):
        return "document"

    extraction_keywords = [
        "extract",
        "extract text",
        "get the text",
        "transcribe",
        "ocr",
    ]

    if any(
        keyword in prompt_lower
        for keyword in extraction_keywords
    ):
        return "extraction"

    classification_keywords = [
        "classify",
        "classification",
        "categorize",
        "category",
        "label this",
    ]

    if any(
        keyword in prompt_lower
        for keyword in classification_keywords
    ):
        return "classification"

    coding_keywords = [
        "python",
        "code",
        "program",
        "function",
        "script",
        "debug",
        "software",
        "algorithm",
        "programming",
    ]

    if any(
        keyword in prompt_lower
        for keyword in coding_keywords
    ):
        return "coding"

    engineering_keywords = [
        "calculate",
        "calculation",
        "engineering",
        "force",
        "pressure",
        "velocity",
        "acceleration",
        "voltage",
        "current",
        "power",
        "torque",
        "stress",
        "strain",
        "density",
    ]

    if any(
        keyword in prompt_lower
        for keyword in engineering_keywords
    ):
        return "engineering"

    complex_keywords = [
        "analyze",
        "analyse",
        "compare",
        "evaluate",
        "reason",
        "explain why",
        "root cause",
        "failure analysis",
        "diagnose",
        "optimization",
        "optimize",
        "derive",
        "design",
        "architecture",
        "trade-off",
        "step by step",
    ]

    if any(
        keyword in prompt_lower
        for keyword in complex_keywords
    ):
        return "complex"

    return "simple"


# =========================================================
# BASE MODEL SELECTION
# =========================================================

def _select_preferred_model(
    task_type: str,
) -> str:

    """Select the default model for a task type."""

    if task_type in {
        "simple",
        "classification",
        "extraction",
        "document",
    }:
        return FAST_MODEL

    if task_type in {
        "complex",
        "coding",
        "engineering",
    }:
        return MAIN_MODEL

    if task_type == "visual":
        return VISION_MODEL

    return FAST_MODEL


# =========================================================
# FINE-TUNED MODEL SELECTION
# =========================================================

def _select_fine_tuned_model(
    task_type: str,
    selector: Optional[
        FineTunedModelSelector
    ] = None,
) -> Dict[str, Any]:

    """
    Check whether an approved specialized
    fine-tuned model exists.
    """

    try:

        selector = (

            selector

            or

            FineTunedModelSelector()

        )

        result = (

            selector.select_model(
                task_type
            )

        )

        return result

    except Exception as exc:

        return {

            "available":
                False,

            "model":
                None,

            "model_name":
                None,

            "task_type":
                task_type,

            "reason":
                (
                    "Fine-tuned model selection "
                    f"failed: {exc}"
                ),

        }


# =========================================================
# PERFORMANCE POLICY
# =========================================================

def _apply_performance_policy(
    task_type: str,
    preferred_model: str,
    performance_manager: PerformanceManager,
) -> str:

    """Apply system performance rules."""

    recommendation = (

        performance_manager
        .get_model_recommendation()

    )

    can_run_heavy = (

        performance_manager
        .can_run_heavy_task()

    )

    if recommendation == "small":

        if task_type == "visual":
            return VISION_MODEL

        return FAST_MODEL

    if recommendation == "medium":

        if task_type == "visual":
            return preferred_model

        if (
            task_type in {
                "complex",
                "coding",
                "engineering",
            }
            and can_run_heavy
        ):
            return MAIN_MODEL

        return FAST_MODEL

    return preferred_model


# =========================================================
# VRAM POLICY
# =========================================================

def _apply_vram_policy(
    task_type: str,
    preferred_model: str,
    vram_manager: VRAMManager,
) -> str:

    """Select a model that fits available VRAM."""

    if vram_manager.can_run_model(
        preferred_model
    ):
        return preferred_model

    if task_type == "visual":

        fallback_models = [
            VISION_MODEL,
            FAST_MODEL,
        ]

    elif task_type in {
        "complex",
        "coding",
        "engineering",
    }:

        fallback_models = [
            MAIN_MODEL,
            FAST_MODEL,
        ]

    else:

        fallback_models = [
            FAST_MODEL,
        ]

    for model in fallback_models:

        if vram_manager.can_run_model(
            model
        ):
            return model

    return FAST_MODEL


# =========================================================
# MODEL SELECTION
# =========================================================

def select_model(
    task_type: str,
    use_vram_manager: bool = True,
    use_performance_manager: bool = True,
    use_fine_tuned_models: bool = True,
    fine_tuned_selector: Optional[
        FineTunedModelSelector
    ] = None,
) -> str:

    """
    Select the best model.

    Priority:

    1. Approved fine-tuned model
    2. Default task model
    3. Performance policy
    4. VRAM policy
    """

    preferred_model = (

        _select_preferred_model(
            task_type
        )

    )

    # -----------------------------------------------------
    # FINE-TUNED MODEL
    # -----------------------------------------------------

    if use_fine_tuned_models:

        fine_tuned_result = (

            _select_fine_tuned_model(

                task_type=task_type,

                selector=(
                    fine_tuned_selector
                ),

            )

        )

        if fine_tuned_result.get(
            "available",
            False,
        ):

            model_name = (

                fine_tuned_result.get(
                    "model_name"
                )

            )

            if model_name:

                return model_name

    # -----------------------------------------------------
    # DEFAULT MODEL
    # -----------------------------------------------------

    selected_model = preferred_model

    # -----------------------------------------------------
    # PERFORMANCE POLICY
    # -----------------------------------------------------

    if use_performance_manager:

        try:

            performance_manager = (
                PerformanceManager()
            )

            selected_model = (

                _apply_performance_policy(

                    task_type=task_type,

                    preferred_model=(
                        selected_model
                    ),

                    performance_manager=(
                        performance_manager
                    ),

                )

            )

        except Exception:

            pass

    # -----------------------------------------------------
    # VRAM POLICY
    # -----------------------------------------------------

    if use_vram_manager:

        try:

            vram_manager = (
                VRAMManager()
            )

            selected_model = (

                _apply_vram_policy(

                    task_type=task_type,

                    preferred_model=(
                        selected_model
                    ),

                    vram_manager=(
                        vram_manager
                    ),

                )

            )

        except Exception:

            pass

    return selected_model


# =========================================================
# DETAILED MODEL SELECTION
# =========================================================

def get_model_selection(
    task_type: str,
    use_vram_manager: bool = True,
    use_performance_manager: bool = True,
    use_fine_tuned_models: bool = True,
    fine_tuned_selector: Optional[
        FineTunedModelSelector
    ] = None,
) -> Dict[str, Any]:

    """
    Return detailed information about model selection.
    """

    preferred_model = (

        _select_preferred_model(
            task_type
        )

    )

    fine_tuned_result = {

        "available": False,

        "model": None,

        "model_name": None,

        "reason":
            "Fine-tuned model selection disabled.",

    }

    if use_fine_tuned_models:

        fine_tuned_result = (

            _select_fine_tuned_model(

                task_type=task_type,

                selector=(
                    fine_tuned_selector
                ),

            )

        )

    selected_model = (

        select_model(

            task_type=task_type,

            use_vram_manager=(
                use_vram_manager
            ),

            use_performance_manager=(
                use_performance_manager
            ),

            use_fine_tuned_models=(
                use_fine_tuned_models
            ),

            fine_tuned_selector=(
                fine_tuned_selector
            ),

        )

    )

    # -----------------------------------------------------
    # STATUS
    # -----------------------------------------------------

    if fine_tuned_result.get(
        "available",
        False,
    ):

        status = "fine_tuned"

    elif selected_model != preferred_model:

        status = "fallback"

    else:

        status = "preferred"

    result = {

        "task_type":
            task_type,

        "preferred_model":
            preferred_model,

        "selected_model":
            selected_model,

        "status":
            status,

        "fine_tuned_available":
            fine_tuned_result.get(
                "available",
                False,
            ),

        "fine_tuned_model":
            fine_tuned_result.get(
                "model_name"
            ),

        "fine_tuning_reason":
            fine_tuned_result.get(
                "reason"
            ),

        "vram_manager_enabled":
            use_vram_manager,

        "performance_manager_enabled":
            use_performance_manager,

        "fine_tuned_models_enabled":
            use_fine_tuned_models,

    }

    # -----------------------------------------------------
    # PERFORMANCE INFORMATION
    # -----------------------------------------------------

    if use_performance_manager:

        try:

            performance_manager = (
                PerformanceManager()
            )

            result["performance"] = (

                performance_manager
                .get_performance_snapshot()

            )

        except Exception as exc:

            result["performance_error"] = (
                str(exc)
            )

    # -----------------------------------------------------
    # VRAM INFORMATION
    # -----------------------------------------------------

    if use_vram_manager:

        try:

            vram_manager = (
                VRAMManager()
            )

            result[
                "selected_model_status"
            ] = (

                vram_manager.get_model_status(
                    selected_model
                )

            )

            result["gpu"] = (

                vram_manager.get_gpu_info()

            )

        except Exception as exc:

            result["vram_error"] = (
                str(exc)
            )

    return result


# =========================================================
# ROUTER
# =========================================================

def route(
    prompt: str,
    image_path: Optional[str] = None,
    use_vram_manager: bool = True,
    use_performance_manager: bool = True,
    use_fine_tuned_models: bool = True,
    fine_tuned_selector: Optional[
        FineTunedModelSelector
    ] = None,
) -> str:

    """
    Determine which model should handle a request.
    """

    task_type = classify_task(

        prompt=prompt,

        image_path=image_path,

    )

    selection = (

        get_model_selection(

            task_type=task_type,

            use_vram_manager=(
                use_vram_manager
            ),

            use_performance_manager=(
                use_performance_manager
            ),

            use_fine_tuned_models=(
                use_fine_tuned_models
            ),

            fine_tuned_selector=(
                fine_tuned_selector
            ),

        )

    )

    model = selection[
        "selected_model"
    ]

    print()

    print(
        f"[Router] Task type: "
        f"{task_type}"
    )

    print(
        f"[Router] Preferred model: "
        f"{selection['preferred_model']}"
    )

    print(
        f"[Router] Selected model: "
        f"{model}"
    )

    print(
        f"[Router] Selection status: "
        f"{selection['status']}"
    )

    print(
        f"[Router] Fine-tuned available: "
        f"{selection['fine_tuned_available']}"
    )

    if selection.get(
        "fine_tuned_model"
    ):

        print(
            f"[Router] Fine-tuned model: "
            f"{selection['fine_tuned_model']}"
        )

    return model


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. SMART ROUTER TEST"
    )

    print("=" * 60)

    test_prompts = [

        "Hello, how are you?",

        (
            "Write a Python function "
            "that calculates factorial."
        ),

        (
            "Calculate the force required "
            "to accelerate a 10 kg object."
        ),

        (
            "Analyze the advantages and "
            "disadvantages of solar power."
        ),

    ]

    for prompt in test_prompts:

        print()

        print("-" * 60)

        print(
            f"Prompt: {prompt}"
        )

        print()

        selected_model = (

            route(
                prompt
            )

        )

        print()

        print(
            f"FINAL MODEL: "
            f"{selected_model}"
        )

    print()

    print("=" * 60)

    print(
        "ROUTER TEST COMPLETE"
    )

    print("=" * 60)