from __future__ import annotations

from collections import defaultdict


def infer_resolved_runtime_family(
    *,
    provider_effective: str,
    model_effective: str,
    runtime_artifact: dict[str, object] | None = None,
) -> str | None:
    effective = str(provider_effective or "").strip().lower()
    model = str(model_effective or "").strip().lower()
    artifact = runtime_artifact if isinstance(runtime_artifact, dict) else {}
    backend_provider = str(artifact.get("backend_provider") or "").strip().lower()
    runtime_name = str(artifact.get("runtime") or "").strip().lower()

    if effective == "ollama":
        return "ollama_local"
    if effective == "huggingface_server":
        if backend_provider == "ollama":
            return "ollama_via_hf_local_llm_service"
        return "hf_local_llm_service"
    if effective == "huggingface_local":
        if "mlx" in model or "mlx" in runtime_name:
            return "mlx_local"
        return "huggingface_local"
    if effective == "huggingface_inference":
        return "huggingface_inference_cloud"
    if effective == "openai":
        return "openai_cloud"
    if runtime_name:
        return runtime_name
    return effective or None


def _runtime_family_aliases(requested_runtime_family: str | None) -> set[str]:
    normalized = str(requested_runtime_family or "").strip().lower()
    aliases = {
        "ollama_local": {"ollama_local"},
        "hf_local_or_mlx": {"huggingface_local", "mlx_local"},
        "hf_local_llm_service": {"hf_local_llm_service", "ollama_via_hf_local_llm_service"},
        "huggingface_local": {"huggingface_local"},
        "mlx_local": {"mlx_local"},
        "openai_cloud": {"openai_cloud"},
        "huggingface_inference_cloud": {"huggingface_inference_cloud"},
        "evidence_pipeline_local": {"evidence_pipeline_local", "ocr_local_pipeline", "docling_local_pipeline"},
        "ollama_vl_local": {"ollama_vl_local", "ollama_local"},
    }
    return aliases.get(normalized, {normalized} if normalized else set())


def build_runtime_family_metadata(
    *,
    requested_runtime_family: str | None,
    provider_effective: str,
    model_effective: str,
    runtime_artifact: dict[str, object] | None = None,
) -> dict[str, object]:
    resolved_runtime_family = infer_resolved_runtime_family(
        provider_effective=provider_effective,
        model_effective=model_effective,
        runtime_artifact=runtime_artifact,
    )
    requested_aliases = _runtime_family_aliases(requested_runtime_family)
    if not requested_runtime_family:
        resolution_status = None
    elif resolved_runtime_family and resolved_runtime_family in requested_aliases:
        resolution_status = "exact"
    else:
        resolution_status = "closest_available"
    note = None
    if requested_runtime_family and resolved_runtime_family and str(requested_runtime_family).strip().lower() != resolved_runtime_family:
        note = f"requested_runtime_family={requested_runtime_family} resolved_runtime_family={resolved_runtime_family}"
    return {
        "requested_runtime_family": requested_runtime_family,
        "resolved_runtime_family": resolved_runtime_family,
        "runtime_family_resolution_status": resolution_status,
        "runtime_family_resolution_note": note,
    }


def summarize_runtime_family_artifacts(resolved_case_artifacts: list[dict[str, object]] | None) -> dict[str, object]:
    counts: dict[str, int] = defaultdict(int)
    substitutions: list[dict[str, object]] = []
    seen_keys: set[tuple[str, str, str, str]] = set()
    for artifact in resolved_case_artifacts or []:
        if not isinstance(artifact, dict):
            continue
        status = str(artifact.get("runtime_family_resolution_status") or "unreported").strip() or "unreported"
        counts[status] += 1
        requested = str(artifact.get("requested_runtime_family") or "").strip()
        resolved = str(artifact.get("resolved_runtime_family") or "").strip()
        if not requested or not resolved or requested == resolved:
            continue
        key = (
            str(artifact.get("group") or ""),
            str(artifact.get("provider_requested") or ""),
            requested,
            resolved,
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        substitutions.append(
            {
                "group": artifact.get("group"),
                "provider_requested": artifact.get("provider_requested"),
                "requested_runtime_family": requested,
                "resolved_runtime_family": resolved,
                "runtime_family_resolution_status": artifact.get("runtime_family_resolution_status"),
                "runtime_family_resolution_note": artifact.get("runtime_family_resolution_note"),
            }
        )
    return {"counts": dict(counts), "substitutions": substitutions}