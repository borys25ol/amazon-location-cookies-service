"""
Module for utility functions.
"""


def form_error_message(errors: list[dict]) -> list[str]:
    """
    Make valid pydantic `ValidationError` messages list.
    """
    messages = []
    for error in errors:
        field, message = error["loc"][-1], error["msg"]
        messages.append(f"`{field}` {message}")
    return messages
