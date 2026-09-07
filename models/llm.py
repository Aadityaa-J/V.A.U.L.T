from typing import Any, Dict, List, Optional

import ollama

from config.config import (
    FAST_MODEL,
    MAIN_MODEL,
)

from models.router import route
from system.model_manager import ModelManager


# =========================================================
# TYPES
# =========================================================

Message = Dict[str, str]
Options = Dict[str, Any]


# =========================================================
# MESSAGE VALIDATION
# =========================================================

def _validate_messages(
    messages: List[Message],
) -> List[Message]:

    if not isinstance(messages, list):
        raise TypeError(
            "Messages must be a list."
        )

    valid_roles = {
        "system",
        "user",
        "assistant",
    }

    cleaned_messages: List[Message] = []

    for message in messages:

        if not isinstance(message, dict):
            raise TypeError(
                "Each message must be a dictionary."
            )

        role = message.get("role")
        content = message.get("content")

        if role not in valid_roles:
            raise ValueError(
                f"Invalid message role: {role}"
            )

        if not isinstance(content, str):
            raise TypeError(
                "Message content must be a string."
            )

        content = content.strip()

        if not content:
            continue

        cleaned_messages.append(
            {
                "role": role,
                "content": content,
            }
        )

    if not cleaned_messages:
        raise ValueError(
            "At least one valid message is required."
        )

    return cleaned_messages


# =========================================================
# GET LAST USER MESSAGE
# =========================================================

def _get_last_user_message(
    messages: List[Message],
) -> str:

    for message in reversed(messages):

        if message["role"] == "user":
            return message["content"]

    raise ValueError(
        "Conversation must contain at least "
        "one user message."
    )


# =========================================================
# MODEL VALIDATION
# =========================================================

def _validate_model(
    model: str,
) -> str:

    if not isinstance(model, str):
        raise TypeError(
            "Model must be a string."
        )

    model = model.strip()

    if not model:
        raise ValueError(
            "Model cannot be empty."
        )

    return model


# =========================================================
# OPTIONS VALIDATION
# =========================================================

def _validate_options(
    options: Optional[Options],
) -> Optional[Options]:

    if options is None:
        return None

    if not isinstance(options, dict):
        raise TypeError(
            "Options must be a dictionary."
        )

    return options


# =========================================================
# CHECK MODEL INSTALLATION
# =========================================================

def _is_model_available(
    model: str,
) -> bool:
    """
    Check whether an Ollama model is installed.

    If the ModelManager itself fails, return True so
    V.A.U.L.T. can still attempt generation.
    """

    try:

        manager = ModelManager()

        return manager.is_model_installed(
            model
        )

    except Exception:

        return True


# =========================================================
# SELECT MODEL
# =========================================================

def _select_model(
    routing_prompt: str,
    model: Optional[str],
    use_router: bool,
) -> str:
    """
    Select a model.

    Priority:

        1. Explicit model
        2. Smart router
        3. MAIN_MODEL
        4. FAST_MODEL fallback
    """

    # -------------------------------------------------
    # EXPLICIT MODEL
    # -------------------------------------------------

    if model is not None:

        selected_model = _validate_model(
            model
        )

        return selected_model

    # -------------------------------------------------
    # SMART ROUTING
    # -------------------------------------------------

    if use_router:

        selected_model = route(
            routing_prompt
        )

        selected_model = _validate_model(
            selected_model
        )

        if _is_model_available(
            selected_model
        ):
            return selected_model

    # -------------------------------------------------
    # MAIN MODEL FALLBACK
    # -------------------------------------------------

    if _is_model_available(
        MAIN_MODEL
    ):
        return _validate_model(
            MAIN_MODEL
        )

    # -------------------------------------------------
    # FAST MODEL FALLBACK
    # -------------------------------------------------

    if _is_model_available(
        FAST_MODEL
    ):
        return _validate_model(
            FAST_MODEL
        )

    # -------------------------------------------------
    # LAST RESORT
    # -------------------------------------------------

    return _validate_model(
        MAIN_MODEL
    )


# =========================================================
# BUILD FALLBACK MODELS
# =========================================================

def _get_fallback_models(
    selected_model: str,
) -> List[str]:
    """
    Build a safe fallback list.

    The originally selected model is always tried first.
    """

    models = [
        selected_model,
    ]

    for fallback_model in (
        MAIN_MODEL,
        FAST_MODEL,
    ):

        if fallback_model not in models:

            models.append(
                fallback_model
            )

    return models


# =========================================================
# RESPONSE EXTRACTION
# =========================================================

def _extract_response_content(
    response: Any,
) -> str:

    try:

        message = response["message"]

        content = message["content"]

    except (
        KeyError,
        TypeError,
    ) as exc:

        raise RuntimeError(
            "Ollama returned an unexpected "
            "response format."
        ) from exc

    if not isinstance(content, str):

        raise RuntimeError(
            "Model response content is not "
            "a string."
        )

    return content.strip()


# =========================================================
# OLLAMA GENERATION WITH FALLBACK
# =========================================================

def _generate_with_fallback(
    models: List[str],
    messages: List[Message],
    options: Optional[Options],
) -> str:
    """
    Try models in order until one successfully responds.
    """

    errors = []

    for selected_model in models:

        # Skip models known to be unavailable.

        if not _is_model_available(
            selected_model
        ):

            errors.append(
                f"{selected_model}: "
                "model not installed"
            )

            continue

        try:

            request: Dict[str, Any] = {
                "model": selected_model,
                "messages": messages,
            }

            if options is not None:

                request["options"] = options

            response = ollama.chat(
                **request
            )

            return _extract_response_content(
                response
            )

        except Exception as exc:

            errors.append(
                f"{selected_model}: {exc}"
            )

    error_message = "\n".join(
        errors
    )

    raise RuntimeError(
        "All configured models failed.\n\n"
        f"{error_message}"
    )


# =========================================================
# CORE GENERATION
# =========================================================

def generate(
    prompt: Optional[str] = None,
    model: Optional[str] = None,
    use_router: bool = True,
    messages: Optional[List[Message]] = None,
    options: Optional[Options] = None,
) -> str:
    """
    Generate text using a local Ollama model.

    Supports:

        - Single prompts
        - Conversations
        - Smart routing
        - Explicit models
        - Model fallback
        - Ollama options
    """

    # -------------------------------------------------
    # BUILD CONVERSATION
    # -------------------------------------------------

    if messages is not None:

        if prompt is not None:

            raise ValueError(
                "Provide either prompt or messages, "
                "not both."
            )

        ollama_messages = _validate_messages(
            messages
        )

        routing_prompt = (
            _get_last_user_message(
                ollama_messages
            )
        )

    else:

        if not isinstance(prompt, str):

            raise TypeError(
                "Prompt must be a string."
            )

        routing_prompt = prompt.strip()

        if not routing_prompt:

            raise ValueError(
                "Prompt cannot be empty."
            )

        ollama_messages = [
            {
                "role": "user",
                "content": routing_prompt,
            }
        ]

    # -------------------------------------------------
    # VALIDATE OPTIONS
    # -------------------------------------------------

    options = _validate_options(
        options
    )

    # -------------------------------------------------
    # SELECT MODEL
    # -------------------------------------------------

    selected_model = _select_model(
        routing_prompt=routing_prompt,
        model=model,
        use_router=use_router,
    )

    # -------------------------------------------------
    # FALLBACK LIST
    # -------------------------------------------------

    fallback_models = (
        _get_fallback_models(
            selected_model
        )
    )

    # -------------------------------------------------
    # GENERATE
    # -------------------------------------------------

    return _generate_with_fallback(
        models=fallback_models,
        messages=ollama_messages,
        options=options,
    )


# =========================================================
# CHAT GENERATION
# =========================================================

def chat_generate(
    messages: List[Message],
    model: Optional[str] = None,
    use_router: bool = True,
    options: Optional[Options] = None,
) -> str:

    return generate(
        messages=messages,
        model=model,
        use_router=use_router,
        options=options,
    )


# =========================================================
# FAST MODEL GENERATION
# =========================================================

def simple_generate(
    prompt: str,
    options: Optional[Options] = None,
) -> str:

    return generate(
        prompt=prompt,
        model=FAST_MODEL,
        use_router=False,
        options=options,
    )


# =========================================================
# MAIN MODEL GENERATION
# =========================================================

def complex_generate(
    prompt: str,
    options: Optional[Options] = None,
) -> str:

    return generate(
        prompt=prompt,
        model=MAIN_MODEL,
        use_router=False,
        options=options,
    )


# =========================================================
# SMART GENERATION
# =========================================================

def smart_generate(
    prompt: str,
    options: Optional[Options] = None,
) -> str:

    return generate(
        prompt=prompt,
        model=None,
        use_router=True,
        options=options,
    )


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)
    print(
        "V.A.U.L.T. LLM GENERATION TEST"
    )
    print("=" * 60)

    test_prompts = [

        "Hello! Respond with one short sentence.",

        "What is 25 multiplied by 48?",

    ]

    for prompt in test_prompts:

        print()

        print("-" * 60)

        print(
            f"PROMPT: {prompt}"
        )

        print()

        try:

            response = smart_generate(
                prompt
            )

            print(
                "RESPONSE:"
            )

            print(
                response
            )

        except Exception as exc:

            print(
                "ERROR:"
            )

            print(
                exc
            )

    print()

    print("=" * 60)
    print(
        "LLM TEST COMPLETE"
    )
    print("=" * 60)