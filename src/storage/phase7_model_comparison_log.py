from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from ..services.model_comparison import (
    infer_model_comparison_quantization_family,
    infer_model_comparison_runtime_bucket,
)


def _safe_average(values: list[float]) -> float:
    return round(sum(values) / max(len(values), 1), 3) if values else 0.0


def _build_dimension_leaderboard(
    metrics_by_dimension: dict[str, dict[str, list[float] | int]],
    *,
    dimension_name: str,
) -> list[dict[str, object]]:
    leaderboard: list[dict[str, object]] = []
    for dimension_value, metrics in metrics_by_dimension.items():
        success_count = int(metrics.get("success_count") or 0)
        total_count = int(metrics.get("total_count") or 0)
        latencies = [float(value) for value in metrics.get("latencies") or []]
        adherence_scores = [float(value) for value in metrics.get("adherence_scores") or []]
        output_chars = [float(value) for value in metrics.get("output_chars") or []]
        groundedness_scores = [float(value) for value in metrics.get("groundedness_scores") or []]
        schema_scores = [float(value) for value in metrics.get("schema_scores") or []]
        use_case_fit_scores = [float(value) for value in metrics.get("use_case_fit_scores") or []]
        leaderboard.append(
            {
                dimension_name: dimension_value,
                "total_candidates": total_count,
                "success_rate": round(success_count / max(total_count, 1), 3),
                "avg_latency_s": _safe_average(latencies),
                "avg_format_adherence": _safe_average(adherence_scores),
                "avg_output_chars": _safe_average(output_chars),
                "avg_groundedness_score": _safe_average(groundedness_scores),
                "avg_schema_adherence": _safe_average(schema_scores),
                "avg_use_case_fit_score": _safe_average(use_case_fit_scores),
            }
        )
    leaderboard.sort(
        key=lambda item: (
            -float(item.get("success_rate") or 0.0),
            -float(item.get("avg_format_adherence") or 0.0),
            float(item.get("avg_latency_s") or 10**9),
        )
    )
    return leaderboard


def _leaderboard_top_entry(leaderboard: list[dict[str, object]]) -> dict[str, object] | None:
    return leaderboard[0] if leaderboard else None


def _accumulate_entry_dimension_metric(
    metrics_by_dimension: dict[str, dict[str, float | int]],
    *,
    dimension_value: str,
    aggregate: dict[str, object] | None,
) -> None:
    if not dimension_value or not isinstance(aggregate, dict):
        return

    total_candidates = int(aggregate.get("total_candidates") or 0)
    if total_candidates <= 0:
        return

    metrics_by_dimension.setdefault(
        dimension_value,
        {
            "total_runs": 0,
            "total_candidates": 0,
            "success_weighted_sum": 0.0,
            "latency_weighted_sum": 0.0,
            "adherence_weighted_sum": 0.0,
            "output_chars_weighted_sum": 0.0,
            "groundedness_weighted_sum": 0.0,
            "schema_weighted_sum": 0.0,
            "use_case_fit_weighted_sum": 0.0,
        },
    )
    bucket = metrics_by_dimension[dimension_value]
    bucket["total_runs"] = int(bucket.get("total_runs") or 0) + 1
    bucket["total_candidates"] = int(bucket.get("total_candidates") or 0) + total_candidates
    bucket["success_weighted_sum"] = float(bucket.get("success_weighted_sum") or 0.0) + float(aggregate.get("success_rate") or 0.0) * total_candidates
    bucket["latency_weighted_sum"] = float(bucket.get("latency_weighted_sum") or 0.0) + float(aggregate.get("avg_latency_s") or 0.0) * total_candidates
    bucket["adherence_weighted_sum"] = float(bucket.get("adherence_weighted_sum") or 0.0) + float(aggregate.get("avg_format_adherence") or 0.0) * total_candidates
    bucket["output_chars_weighted_sum"] = float(bucket.get("output_chars_weighted_sum") or 0.0) + float(aggregate.get("avg_output_chars") or 0.0) * total_candidates
    bucket["groundedness_weighted_sum"] = float(bucket.get("groundedness_weighted_sum") or 0.0) + float(aggregate.get("avg_groundedness_score") or 0.0) * total_candidates
    bucket["schema_weighted_sum"] = float(bucket.get("schema_weighted_sum") or 0.0) + float(aggregate.get("avg_schema_adherence") or 0.0) * total_candidates
    bucket["use_case_fit_weighted_sum"] = float(bucket.get("use_case_fit_weighted_sum") or 0.0) + float(aggregate.get("avg_use_case_fit_score") or 0.0) * total_candidates


def _build_entry_dimension_leaderboard(
    metrics_by_dimension: dict[str, dict[str, float | int]],
    *,
    dimension_name: str,
) -> list[dict[str, object]]:
    leaderboard: list[dict[str, object]] = []
    for dimension_value, metrics in metrics_by_dimension.items():
        total_candidates = int(metrics.get("total_candidates") or 0)
        total_runs = int(metrics.get("total_runs") or 0)
        if total_candidates <= 0:
            continue
        leaderboard.append(
            {
                dimension_name: dimension_value,
                "total_runs": total_runs,
                "total_candidates": total_candidates,
                "success_rate": round(float(metrics.get("success_weighted_sum") or 0.0) / total_candidates, 3),
                "avg_latency_s": round(float(metrics.get("latency_weighted_sum") or 0.0) / total_candidates, 3),
                "avg_format_adherence": round(float(metrics.get("adherence_weighted_sum") or 0.0) / total_candidates, 3),
                "avg_output_chars": round(float(metrics.get("output_chars_weighted_sum") or 0.0) / total_candidates, 3),
                "avg_groundedness_score": round(float(metrics.get("groundedness_weighted_sum") or 0.0) / total_candidates, 3),
                "avg_schema_adherence": round(float(metrics.get("schema_weighted_sum") or 0.0) / total_candidates, 3),
                "avg_use_case_fit_score": round(float(metrics.get("use_case_fit_weighted_sum") or 0.0) / total_candidates, 3),
            }
        )
    leaderboard.sort(
        key=lambda item: (
            -float(item.get("success_rate") or 0.0),
            -float(item.get("avg_format_adherence") or 0.0),
            float(item.get("avg_latency_s") or 10**9),
        )
    )
    return leaderboard


def load_model_comparison_log(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def save_model_comparison_log(path: Path, entries: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def append_model_comparison_log_entry(path: Path, entry: dict[str, object]) -> list[dict[str, object]]:
    entries = load_model_comparison_log(path)
    entries.append(entry)
    save_model_comparison_log(path, entries)
    return entries


def clear_model_comparison_log(path: Path) -> None:
    if path.exists():
        path.unlink()


def summarize_model_comparison_log(entries: list[dict[str, object]]) -> dict[str, object]:
    if not entries:
        return {
            "total_runs": 0,
            "total_candidates": 0,
            "success_rate": 0.0,
            "avg_latency_s": 0.0,
            "avg_output_chars": 0.0,
            "avg_format_adherence": 0.0,
            "avg_groundedness_score": 0.0,
            "avg_schema_adherence": 0.0,
            "avg_use_case_fit_score": 0.0,
            "provider_counts": {},
            "model_counts": {},
            "format_counts": {},
            "runtime_bucket_counts": {},
            "quantization_family_counts": {},
            "provider_leaderboard": [],
            "model_leaderboard": [],
            "format_leaderboard": [],
            "runtime_bucket_leaderboard": [],
            "quantization_family_leaderboard": [],
            "retrieval_strategy_leaderboard": [],
            "embedding_provider_leaderboard": [],
            "embedding_model_leaderboard": [],
            "prompt_profile_leaderboard": [],
            "document_usage_leaderboard": [],
            "benchmark_use_case_leaderboard": [],
        }

    provider_counter: Counter[str] = Counter()
    model_counter: Counter[str] = Counter()
    format_counter: Counter[str] = Counter()
    runtime_bucket_counter: Counter[str] = Counter()
    quantization_family_counter: Counter[str] = Counter()
    provider_metrics: dict[str, dict[str, list[float] | int]] = {}
    model_metrics: dict[str, dict[str, list[float] | int]] = {}
    format_metrics: dict[str, dict[str, list[float] | int]] = {}
    runtime_bucket_metrics: dict[str, dict[str, list[float] | int]] = {}
    quantization_family_metrics: dict[str, dict[str, list[float] | int]] = {}
    retrieval_strategy_metrics: dict[str, dict[str, float | int]] = {}
    embedding_provider_metrics: dict[str, dict[str, float | int]] = {}
    embedding_model_metrics: dict[str, dict[str, float | int]] = {}
    prompt_profile_metrics: dict[str, dict[str, float | int]] = {}
    document_usage_metrics: dict[str, dict[str, float | int]] = {}
    benchmark_use_case_metrics: dict[str, dict[str, float | int]] = {}
    total_candidates = 0
    success_count = 0
    latencies: list[float] = []
    output_chars: list[int] = []
    adherence_scores: list[float] = []
    groundedness_scores: list[float] = []
    schema_scores: list[float] = []
    use_case_fit_scores: list[float] = []

    for entry in entries:
        response_format = str(entry.get("response_format") or "").strip()
        aggregate = entry.get("aggregate") if isinstance(entry.get("aggregate"), dict) else None
        _accumulate_entry_dimension_metric(
            retrieval_strategy_metrics,
            dimension_value=str(entry.get("retrieval_strategy") or "").strip(),
            aggregate=aggregate,
        )
        _accumulate_entry_dimension_metric(
            embedding_provider_metrics,
            dimension_value=str(entry.get("embedding_provider") or "").strip(),
            aggregate=aggregate,
        )
        _accumulate_entry_dimension_metric(
            embedding_model_metrics,
            dimension_value=str(entry.get("embedding_model") or "").strip(),
            aggregate=aggregate,
        )
        _accumulate_entry_dimension_metric(
            prompt_profile_metrics,
            dimension_value=str(entry.get("prompt_profile") or "").strip(),
            aggregate=aggregate,
        )
        _accumulate_entry_dimension_metric(
            document_usage_metrics,
            dimension_value="with_documents" if bool(entry.get("use_documents")) else "without_documents",
            aggregate=aggregate,
        )
        _accumulate_entry_dimension_metric(
            benchmark_use_case_metrics,
            dimension_value=str(entry.get("benchmark_use_case") or "ad_hoc").strip(),
            aggregate=aggregate,
        )
        if response_format:
            format_counter[response_format] += 1
        for candidate in entry.get("candidate_results") or []:
            if not isinstance(candidate, dict):
                continue
            total_candidates += 1
            provider = str(candidate.get("provider_effective") or candidate.get("provider_requested") or "").strip()
            model = str(candidate.get("model_effective") or candidate.get("model_requested") or "").strip()
            runtime_bucket = str(
                candidate.get("runtime_bucket")
                or infer_model_comparison_runtime_bucket(provider, model)
                or "unknown"
            ).strip()
            quantization_family = str(
                candidate.get("quantization_family")
                or infer_model_comparison_quantization_family(provider, model)
                or "unspecified_local"
            ).strip()
            success = bool(candidate.get("success"))
            latency = float(candidate.get("latency_s")) if isinstance(candidate.get("latency_s"), (int, float)) else None
            adherence = float(candidate.get("format_adherence")) if isinstance(candidate.get("format_adherence"), (int, float)) else None
            output_char_count = int(candidate.get("output_chars")) if isinstance(candidate.get("output_chars"), (int, float)) else None
            groundedness = float(candidate.get("groundedness_score")) if isinstance(candidate.get("groundedness_score"), (int, float)) else None
            schema_score = float(candidate.get("schema_adherence")) if isinstance(candidate.get("schema_adherence"), (int, float)) else None
            use_case_fit = float(candidate.get("use_case_fit_score")) if isinstance(candidate.get("use_case_fit_score"), (int, float)) else None
            if provider:
                provider_counter[provider] += 1
                provider_metrics.setdefault(provider, {"success_count": 0, "total_count": 0, "latencies": [], "adherence_scores": [], "output_chars": [], "groundedness_scores": [], "schema_scores": [], "use_case_fit_scores": []})
                provider_metrics[provider]["total_count"] = int(provider_metrics[provider]["total_count"] or 0) + 1
                if success:
                    provider_metrics[provider]["success_count"] = int(provider_metrics[provider]["success_count"] or 0) + 1
                if latency is not None:
                    provider_metrics[provider]["latencies"].append(latency)  # type: ignore[index]
                if adherence is not None:
                    provider_metrics[provider]["adherence_scores"].append(adherence)  # type: ignore[index]
                if output_char_count is not None:
                    provider_metrics[provider]["output_chars"].append(float(output_char_count))  # type: ignore[index]
                if groundedness is not None:
                    provider_metrics[provider]["groundedness_scores"].append(groundedness)  # type: ignore[index]
                if schema_score is not None:
                    provider_metrics[provider]["schema_scores"].append(schema_score)  # type: ignore[index]
                if use_case_fit is not None:
                    provider_metrics[provider]["use_case_fit_scores"].append(use_case_fit)  # type: ignore[index]
            if model:
                model_counter[model] += 1
                model_metrics.setdefault(model, {"success_count": 0, "total_count": 0, "latencies": [], "adherence_scores": [], "output_chars": [], "groundedness_scores": [], "schema_scores": [], "use_case_fit_scores": []})
                model_metrics[model]["total_count"] = int(model_metrics[model]["total_count"] or 0) + 1
                if success:
                    model_metrics[model]["success_count"] = int(model_metrics[model]["success_count"] or 0) + 1
                if latency is not None:
                    model_metrics[model]["latencies"].append(latency)  # type: ignore[index]
                if adherence is not None:
                    model_metrics[model]["adherence_scores"].append(adherence)  # type: ignore[index]
                if output_char_count is not None:
                    model_metrics[model]["output_chars"].append(float(output_char_count))  # type: ignore[index]
                if groundedness is not None:
                    model_metrics[model]["groundedness_scores"].append(groundedness)  # type: ignore[index]
                if schema_score is not None:
                    model_metrics[model]["schema_scores"].append(schema_score)  # type: ignore[index]
                if use_case_fit is not None:
                    model_metrics[model]["use_case_fit_scores"].append(use_case_fit)  # type: ignore[index]
            if response_format:
                format_metrics.setdefault(response_format, {"success_count": 0, "total_count": 0, "latencies": [], "adherence_scores": [], "output_chars": [], "groundedness_scores": [], "schema_scores": [], "use_case_fit_scores": []})
                format_metrics[response_format]["total_count"] = int(format_metrics[response_format]["total_count"] or 0) + 1
                if success:
                    format_metrics[response_format]["success_count"] = int(format_metrics[response_format]["success_count"] or 0) + 1
                if latency is not None:
                    format_metrics[response_format]["latencies"].append(latency)  # type: ignore[index]
                if adherence is not None:
                    format_metrics[response_format]["adherence_scores"].append(adherence)  # type: ignore[index]
                if output_char_count is not None:
                    format_metrics[response_format]["output_chars"].append(float(output_char_count))  # type: ignore[index]
                if groundedness is not None:
                    format_metrics[response_format]["groundedness_scores"].append(groundedness)  # type: ignore[index]
                if schema_score is not None:
                    format_metrics[response_format]["schema_scores"].append(schema_score)  # type: ignore[index]
                if use_case_fit is not None:
                    format_metrics[response_format]["use_case_fit_scores"].append(use_case_fit)  # type: ignore[index]
            if runtime_bucket:
                runtime_bucket_counter[runtime_bucket] += 1
                runtime_bucket_metrics.setdefault(runtime_bucket, {"success_count": 0, "total_count": 0, "latencies": [], "adherence_scores": [], "output_chars": [], "groundedness_scores": [], "schema_scores": [], "use_case_fit_scores": []})
                runtime_bucket_metrics[runtime_bucket]["total_count"] = int(runtime_bucket_metrics[runtime_bucket]["total_count"] or 0) + 1
                if success:
                    runtime_bucket_metrics[runtime_bucket]["success_count"] = int(runtime_bucket_metrics[runtime_bucket]["success_count"] or 0) + 1
                if latency is not None:
                    runtime_bucket_metrics[runtime_bucket]["latencies"].append(latency)  # type: ignore[index]
                if adherence is not None:
                    runtime_bucket_metrics[runtime_bucket]["adherence_scores"].append(adherence)  # type: ignore[index]
                if output_char_count is not None:
                    runtime_bucket_metrics[runtime_bucket]["output_chars"].append(float(output_char_count))  # type: ignore[index]
                if groundedness is not None:
                    runtime_bucket_metrics[runtime_bucket]["groundedness_scores"].append(groundedness)  # type: ignore[index]
                if schema_score is not None:
                    runtime_bucket_metrics[runtime_bucket]["schema_scores"].append(schema_score)  # type: ignore[index]
                if use_case_fit is not None:
                    runtime_bucket_metrics[runtime_bucket]["use_case_fit_scores"].append(use_case_fit)  # type: ignore[index]
            if quantization_family:
                quantization_family_counter[quantization_family] += 1
                quantization_family_metrics.setdefault(quantization_family, {"success_count": 0, "total_count": 0, "latencies": [], "adherence_scores": [], "output_chars": [], "groundedness_scores": [], "schema_scores": [], "use_case_fit_scores": []})
                quantization_family_metrics[quantization_family]["total_count"] = int(quantization_family_metrics[quantization_family]["total_count"] or 0) + 1
                if success:
                    quantization_family_metrics[quantization_family]["success_count"] = int(quantization_family_metrics[quantization_family]["success_count"] or 0) + 1
                if latency is not None:
                    quantization_family_metrics[quantization_family]["latencies"].append(latency)  # type: ignore[index]
                if adherence is not None:
                    quantization_family_metrics[quantization_family]["adherence_scores"].append(adherence)  # type: ignore[index]
                if output_char_count is not None:
                    quantization_family_metrics[quantization_family]["output_chars"].append(float(output_char_count))  # type: ignore[index]
                if groundedness is not None:
                    quantization_family_metrics[quantization_family]["groundedness_scores"].append(groundedness)  # type: ignore[index]
                if schema_score is not None:
                    quantization_family_metrics[quantization_family]["schema_scores"].append(schema_score)  # type: ignore[index]
                if use_case_fit is not None:
                    quantization_family_metrics[quantization_family]["use_case_fit_scores"].append(use_case_fit)  # type: ignore[index]
            if success:
                success_count += 1
            if latency is not None:
                latencies.append(latency)
            if output_char_count is not None:
                output_chars.append(output_char_count)
            if adherence is not None:
                adherence_scores.append(adherence)
            if groundedness is not None:
                groundedness_scores.append(groundedness)
            if schema_score is not None:
                schema_scores.append(schema_score)
            if use_case_fit is not None:
                use_case_fit_scores.append(use_case_fit)

    provider_leaderboard = _build_dimension_leaderboard(provider_metrics, dimension_name="provider")
    model_leaderboard = _build_dimension_leaderboard(model_metrics, dimension_name="model")
    format_leaderboard = _build_dimension_leaderboard(format_metrics, dimension_name="response_format")
    runtime_bucket_leaderboard = _build_dimension_leaderboard(runtime_bucket_metrics, dimension_name="runtime_bucket")
    quantization_family_leaderboard = _build_dimension_leaderboard(quantization_family_metrics, dimension_name="quantization_family")
    retrieval_strategy_leaderboard = _build_entry_dimension_leaderboard(retrieval_strategy_metrics, dimension_name="retrieval_strategy")
    embedding_provider_leaderboard = _build_entry_dimension_leaderboard(embedding_provider_metrics, dimension_name="embedding_provider")
    embedding_model_leaderboard = _build_entry_dimension_leaderboard(embedding_model_metrics, dimension_name="embedding_model")
    prompt_profile_leaderboard = _build_entry_dimension_leaderboard(prompt_profile_metrics, dimension_name="prompt_profile")
    document_usage_leaderboard = _build_entry_dimension_leaderboard(document_usage_metrics, dimension_name="document_usage")
    benchmark_use_case_leaderboard = _build_entry_dimension_leaderboard(benchmark_use_case_metrics, dimension_name="benchmark_use_case")

    return {
        "total_runs": len(entries),
        "total_candidates": total_candidates,
        "success_rate": round(success_count / max(total_candidates, 1), 3),
        "avg_latency_s": round(sum(latencies) / max(len(latencies), 1), 3) if latencies else 0.0,
        "avg_output_chars": round(sum(output_chars) / max(len(output_chars), 1), 3) if output_chars else 0.0,
        "avg_format_adherence": round(sum(adherence_scores) / max(len(adherence_scores), 1), 3) if adherence_scores else 0.0,
        "avg_groundedness_score": round(sum(groundedness_scores) / max(len(groundedness_scores), 1), 3) if groundedness_scores else 0.0,
        "avg_schema_adherence": round(sum(schema_scores) / max(len(schema_scores), 1), 3) if schema_scores else 0.0,
        "avg_use_case_fit_score": round(sum(use_case_fit_scores) / max(len(use_case_fit_scores), 1), 3) if use_case_fit_scores else 0.0,
        "provider_counts": dict(provider_counter),
        "model_counts": dict(model_counter),
        "format_counts": dict(format_counter),
        "runtime_bucket_counts": dict(runtime_bucket_counter),
        "quantization_family_counts": dict(quantization_family_counter),
        "provider_leaderboard": provider_leaderboard,
        "model_leaderboard": model_leaderboard,
        "format_leaderboard": format_leaderboard,
        "runtime_bucket_leaderboard": runtime_bucket_leaderboard,
        "quantization_family_leaderboard": quantization_family_leaderboard,
        "retrieval_strategy_leaderboard": retrieval_strategy_leaderboard,
        "embedding_provider_leaderboard": embedding_provider_leaderboard,
        "embedding_model_leaderboard": embedding_model_leaderboard,
        "prompt_profile_leaderboard": prompt_profile_leaderboard,
        "document_usage_leaderboard": document_usage_leaderboard,
        "benchmark_use_case_leaderboard": benchmark_use_case_leaderboard,
        "top_provider": _leaderboard_top_entry(provider_leaderboard),
        "top_model": _leaderboard_top_entry(model_leaderboard),
        "top_format": _leaderboard_top_entry(format_leaderboard),
        "top_runtime_bucket": _leaderboard_top_entry(runtime_bucket_leaderboard),
        "top_quantization_family": _leaderboard_top_entry(quantization_family_leaderboard),
        "top_benchmark_use_case": _leaderboard_top_entry(benchmark_use_case_leaderboard),
    }