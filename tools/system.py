from datetime import datetime


def get_current_datetime() -> dict:
    """
    Get the current local date and time.
    """

    now = datetime.now()

    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day": now.strftime("%A"),
        "formatted": now.strftime(
            "%A, %B %d, %Y at %I:%M %p"
        ),
    }