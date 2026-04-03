from __future__ import annotations

import math
import os


DEFAULT_CHARS_PER_TOKEN = 4.0

_PROVIDER_PRICING_ENV_PREFIX = {
    "openai": "OPENAI",
    "huggingface_inference": "HUGGINGFACE_INFERENCE",
}


def _optional_float_env(name: str) -> float | None:
    raw_value = str(os.getenv(name, "")).strip()
    if not raw_value:
        return None
    try:
        return float(raw_value)
    except ValueError:
        return None


def count_message_chars(messages: list[dict[str, object]] | None) -> int:
    total = 0
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        total += len(str(message.get("content") or ""))
    return total


def estimate_token_count_from_chars(chars: int, *, chars_per_token: float = DEFAULT_CHARS_PER_TOKEN) -> int:
    normalized_chars = max(int(chars or 0), 0)
    if normalized_chars <= 0:
        return 0
    ratio = max(float(chars_per_token or DEFAULT_CHARS_PER_TOKEN), 1.0)
    return max(1, int(math.ceil(normalized_chars / ratio)))


def estimate_runtime_usage_metrics(
    *,
    prompt_chars: int,
    completion_chars: int,
    context_chars: int = 0,
    provider: str | None = None,
    chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
) -> dict[str, object]:
    normalized_provider = str(provider or "").strip().lower()
    prompt_chars = max(int(prompt_chars or 0), 0)
    completion_chars = max(int(completion_chars or 0), 0)
    context_chars = max(int(context_chars or 0), 0)

    prompt_tokens = estimate_token_count_from_chars(prompt_chars, chars_per_token=chars_per_token)
    completion_tokens = estimate_token_count_from_chars(completion_chars, chars_per_token=chars_per_token)
    total_tokens = prompt_tokens + completion_tokens

    pricing_prefix = _PROVIDER_PRICING_ENV_PREFIX.get(normalized_provider)
    input_cost_per_1m = _optional_float_env(f"{pricing_prefix}_INPUT_COST_PER_1M_TOKENS") if pricing_prefix else None
    output_cost_per_1m = _optional_float_env(f"{pricing_prefix}_OUTPUT_COST_PER_1M_TOKENS") if pricing_prefix else None

    estimated_cost_usd: float | None = None
    if input_cost_per_1m is not None or output_cost_per_1m is not None:
        estimated_cost_usd = round(
            (prompt_tokens / 1_000_000) * float(input_cost_per_1m or 0.0)
            + (completion_tokens / 1_000_000) * float(output_cost_per_1m or 0.0),
            6,
        )

    if estimated_cost_usd is not None:
        cost_source = "env_pricing"
    elif normalized_provider in {"ollama", "huggingface_local", "huggingface_server"}:
        cost_source = "local_runtime_not_priced"
    else:
        cost_source = "pricing_not_configured"

    return {
        "prompt_chars": prompt_chars,
        "output_chars": completion_chars,
        "context_chars": context_chars,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "usage_source": "estimated_chars",
        "cost_source": cost_source,
        **({"cost_usd": estimated_cost_usd} if estimated_cost_usd is not None else {}),
    }