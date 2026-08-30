from models.llm import FAST_MODEL, MAIN_MODEL


def select_model(task_type: str) -> str:
    if task_type in {"simple", "classification", "extraction"}:
        return FAST_MODEL

    return MAIN_MODEL