from __future__ import annotations

import sys


def estimate_process_peak_memory_mb() -> float | None:
    try:
        import resource
    except Exception:
        return None

    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
    except Exception:
        return None

    peak_value = getattr(usage, "ru_maxrss", None)
    if not isinstance(peak_value, (int, float)) or peak_value <= 0:
        return None

    if sys.platform == "darwin":
        return round(float(peak_value) / (1024 * 1024), 4)
    return round(float(peak_value) / 1024, 4)


def build_operational_metrics_bundle(
    *,
    total_wall_time_s: float | None,
    repetition: int | None = None,
    ttft_s: float | None = None,
    throughput_tokens_per_s: float | None = None,
) -> dict[str, object]:
    bundle: dict[str, object] = {
        "total_wall_time_s": round(float(total_wall_time_s), 4) if isinstance(total_wall_time_s, (int, float)) else None,
        "total_wall_time_status": "measured" if isinstance(total_wall_time_s, (int, float)) else "not_supported",
        "ttft_s": round(float(ttft_s), 4) if isinstance(ttft_s, (int, float)) else None,
        "ttft_status": "measured" if isinstance(ttft_s, (int, float)) else "not_supported",
        "throughput_tokens_per_s": round(float(throughput_tokens_per_s), 4) if isinstance(throughput_tokens_per_s, (int, float)) else None,
        "throughput_status": "measured" if isinstance(throughput_tokens_per_s, (int, float)) else "not_supported",
        "cold_start_wall_time_s": None,
        "cold_start_status": "not_supported",
        "warm_start_wall_time_s": None,
        "warm_start_status": "not_supported",
        "memory_peak_estimate_mb": None,
        "memory_status": "not_supported",
        "memory_measurement_method": None,
    }

    if isinstance(total_wall_time_s, (int, float)) and int(repetition or 1) <= 1:
        bundle["cold_start_wall_time_s"] = round(float(total_wall_time_s), 4)
        bundle["cold_start_status"] = "estimated"
    elif isinstance(total_wall_time_s, (int, float)):
        bundle["warm_start_wall_time_s"] = round(float(total_wall_time_s), 4)
        bundle["warm_start_status"] = "estimated"

    peak_memory_mb = estimate_process_peak_memory_mb()
    if isinstance(peak_memory_mb, (int, float)):
        bundle["memory_peak_estimate_mb"] = round(float(peak_memory_mb), 4)
        bundle["memory_status"] = "estimated"
        bundle["memory_measurement_method"] = "resource_ru_maxrss_process_peak"
    return bundle