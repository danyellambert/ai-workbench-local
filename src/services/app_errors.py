from __future__ import annotations


def describe_exception(error: BaseException) -> str:
    detail = str(error).strip()
    return detail or error.__class__.__name__


def build_ui_error_message(prefix: str, error: BaseException) -> str:
    return f"{prefix}. Detalhes: {describe_exception(error)}"