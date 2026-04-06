from __future__ import annotations

import math
import os
from collections import Counter


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


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _optional_float(value: object) -> float | None:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def normalize_native_usage_metrics(native_usage: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(native_usage, dict):
        return {}

    prompt_tokens = _optional_int(native_usage.get("prompt_tokens"))
    if prompt_tokens is None:
        prompt_tokens = _optional_int(native_usage.get("input_tokens"))

    completion_tokens = _optional_int(native_usage.get("completion_tokens"))
    if completion_tokens is None:
        completion_tokens = _optional_int(native_usage.get("output_tokens"))
    if completion_tokens is None:
        completion_tokens = _optional_int(native_usage.get("generation_tokens"))
    if completion_tokens is None:
        completion_tokens = _optional_int(native_usage.get("eval_count"))

    if prompt_tokens is None:
        prompt_tokens = _optional_int(native_usage.get("prompt_eval_count"))

    total_tokens = _optional_int(native_usage.get("total_tokens"))
    if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
        total_tokens = int(prompt_tokens) + int(completion_tokens)

    cost_usd = _optional_float(native_usage.get("cost_usd"))
    usage_source = str(native_usage.get("usage_source") or "provider_native_usage").strip() or "provider_native_usage"
    cost_source = str(native_usage.get("cost_source") or ("provider_native_usage" if cost_usd is not None else "provider_native_usage_unpriced")).strip()

    normalized: dict[str, object] = {
        "usage_source": usage_source,
        "cost_source": cost_source,
    }
    if prompt_tokens is not None:
        normalized["prompt_tokens"] = int(prompt_tokens)
    if completion_tokens is not None:
        normalized["completion_tokens"] = int(completion_tokens)
    if total_tokens is not None:
        normalized["total_tokens"] = int(total_tokens)
    if cost_usd is not None:
        normalized["cost_usd"] = round(float(cost_usd), 6)
    return normalized


def get_provider_native_usage_metrics(provider: object) -> dict[str, object]:
    if hasattr(provider, "get_last_usage_metrics"):
        try:
            usage = provider.get_last_usage_metrics()  # type: ignore[attr-defined]
        except Exception:
            return {}
        return normalize_native_usage_metrics(usage if isinstance(usage, dict) else None)
    return {}


def aggregate_provider_call_native_usage(provider_calls: list[dict[str, object]] | None) -> dict[str, object]:
    prompt_tokens_total = 0
    completion_tokens_total = 0
    total_tokens_total = 0
    cost_total = 0.0
    prompt_found = False
    completion_found = False
    total_found = False
    cost_found = False
    usage_source_counter: Counter[str] = Counter()
    cost_source_counter: Counter[str] = Counter()

    for call in provider_calls or []:
        if not isinstance(call, dict):
            continue
        native_usage = normalize_native_usage_metrics(call.get("native_usage") if isinstance(call.get("native_usage"), dict) else None)
        if not native_usage:
            continue
        prompt_tokens = _optional_int(native_usage.get("prompt_tokens"))
        completion_tokens = _optional_int(native_usage.get("completion_tokens"))
        total_tokens = _optional_int(native_usage.get("total_tokens"))
        cost_usd = _optional_float(native_usage.get("cost_usd"))
        usage_source = str(native_usage.get("usage_source") or "provider_native_usage").strip()
        cost_source = str(native_usage.get("cost_source") or "provider_native_usage_unpriced").strip()

        if prompt_tokens is not None:
            prompt_found = True
            prompt_tokens_total += int(prompt_tokens)
        if completion_tokens is not None:
            completion_found = True
            completion_tokens_total += int(completion_tokens)
        if total_tokens is not None:
            total_found = True
            total_tokens_total += int(total_tokens)
        if cost_usd is not None:
            cost_found = True
            cost_total += float(cost_usd)
        if usage_source:
            usage_source_counter[usage_source] += 1
        if cost_source:
            cost_source_counter[cost_source] += 1

    if not any([prompt_found, completion_found, total_found, cost_found]):
        return {}

    result: dict[str, object] = {
        "usage_source": usage_source_counter.most_common(1)[0][0] if usage_source_counter else "provider_native_usage",
        "cost_source": cost_source_counter.most_common(1)[0][0] if cost_source_counter else "provider_native_usage_unpriced",
    }
    if prompt_found:
        result["prompt_tokens"] = prompt_tokens_total
    if completion_found:
        result["completion_tokens"] = completion_tokens_total
    if total_found:
        result["total_tokens"] = total_tokens_total
    elif prompt_found and completion_found:
        result["total_tokens"] = prompt_tokens_total + completion_tokens_total
    if cost_found:
        result["cost_usd"] = round(cost_total, 6)
    return result


def estimate_runtime_usage_metrics(
    *,
    prompt_chars: int,
    completion_chars: int,
    context_chars: int = 0,
    provider: str | None = None,
    native_usage: dict[str, object] | None = None,
    chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
) -> dict[str, object]:
    normalized_provider = str(provider or "").strip().lower()
    prompt_chars = max(int(prompt_chars or 0), 0)
    completion_chars = max(int(completion_chars or 0), 0)
    context_chars = max(int(context_chars or 0), 0)

    normalized_native_usage = normalize_native_usage_metrics(native_usage)

    estimated_prompt_tokens = estimate_token_count_from_chars(prompt_chars, chars_per_token=chars_per_token)
    estimated_completion_tokens = estimate_token_count_from_chars(completion_chars, chars_per_token=chars_per_token)
    prompt_tokens = _optional_int(normalized_native_usage.get("prompt_tokens"))
    if prompt_tokens is None:
        prompt_tokens = estimated_prompt_tokens
    completion_tokens = _optional_int(normalized_native_usage.get("completion_tokens"))
    if completion_tokens is None:
        completion_tokens = estimated_completion_tokens
    total_tokens = _optional_int(normalized_native_usage.get("total_tokens"))
    if total_tokens is None:
        total_tokens = int(prompt_tokens) + int(completion_tokens)

    pricing_prefix = _PROVIDER_PRICING_ENV_PREFIX.get(normalized_provider)
    input_cost_per_1m = _optional_float_env(f"{pricing_prefix}_INPUT_COST_PER_1M_TOKENS") if pricing_prefix else None
    output_cost_per_1m = _optional_float_env(f"{pricing_prefix}_OUTPUT_COST_PER_1M_TOKENS") if pricing_prefix else None

    estimated_cost_usd = _optional_float(normalized_native_usage.get("cost_usd"))
    if input_cost_per_1m is not None or output_cost_per_1m is not None:
        estimated_cost_usd = round(
            (prompt_tokens / 1_000_000) * float(input_cost_per_1m or 0.0)
            + (completion_tokens / 1_000_000) * float(output_cost_per_1m or 0.0),
            6,
        )

    native_cost_source = str(normalized_native_usage.get("cost_source") or "").strip()
    native_usage_source = str(normalized_native_usage.get("usage_source") or "").strip()

    if estimated_cost_usd is not None and (input_cost_per_1m is not None or output_cost_per_1m is not None):
        cost_source = "env_pricing"
    elif estimated_cost_usd is not None:
        cost_source = native_cost_source or "provider_native_usage"
    elif normalized_provider in {"ollama", "huggingface_local", "huggingface_server"}:
        cost_source = "local_runtime_not_priced"
    else:
        cost_source = "pricing_not_configured"

    return {
        "prompt_chars": prompt_chars,
        "output_chars": completion_chars,
        "context_chars": context_chars,
        "prompt_tokens": int(prompt_tokens),
        "completion_tokens": int(completion_tokens),
        "total_tokens": int(total_tokens),
        "usage_source": native_usage_source or "estimated_chars",
        "cost_source": cost_source,
        "native_usage_available": bool(normalized_native_usage),
        **({"cost_usd": estimated_cost_usd} if estimated_cost_usd is not None else {}),
    }