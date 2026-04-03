from __future__ import annotations

import json
import re
import time
from typing import Any

from ..config import RagSettings
from ..prompt_profiles import build_prompt_messages
from ..providers.registry import resolve_provider_runtime_profile
from ..rag.prompting import inject_rag_context


MODEL_COMPARISON_FORMAT_OPTIONS = {
    "plain_text": "Texto livre",
    "bullet_list": "Lista com bullets",
    "json": "JSON válido",
}

MODEL_COMPARISON_USE_CASE_PRESETS = {
    "ad_hoc": {
        "label": "Ad hoc / livre",
        "description": "Comparação livre com prompt manual.",
        "prompt_text": "",
        "response_format": "plain_text",
        "prompt_profile": "neutro",
    },
    "executive_summary": {
        "label": "Resumo executivo",
        "description": "Comparar capacidade de resumir contexto documental com clareza executiva.",
        "prompt_text": "Resuma os principais pontos, riscos e próximos passos em linguagem executiva e objetiva.",
        "response_format": "bullet_list",
        "prompt_profile": "neutro",
    },
    "risk_review": {
        "label": "Revisão de riscos",
        "description": "Comparar qualidade na identificação de riscos, controles e lacunas.",
        "prompt_text": "Identifique os principais riscos, controles existentes, lacunas e próximos passos recomendados.",
        "response_format": "bullet_list",
        "prompt_profile": "neutro",
    },
    "policy_compliance": {
        "label": "Policy / compliance",
        "description": "Comparar análise documental com foco em obrigações, restrições e necessidade de revisão.",
        "prompt_text": "Liste obrigações, restrições, pontos de compliance, ambiguidades e itens que exigem revisão humana.",
        "response_format": "bullet_list",
        "prompt_profile": "neutro",
    },
    "structured_extraction": {
        "label": "Extração estruturada",
        "description": "Comparar aderência a formato estruturado em JSON.",
        "prompt_text": "Extraia os principais campos do conteúdo em JSON com chaves: summary, risks, actions, entities.",
        "response_format": "json",
        "prompt_profile": "extrator",
    },
    "technical_review": {
        "label": "Revisão técnica",
        "description": "Comparar capacidade de explicar problemas técnicos e recomendações.",
        "prompt_text": "Explique os principais problemas técnicos, impactos e recomendações priorizadas.",
        "response_format": "bullet_list",
        "prompt_profile": "programador",
    },
}

MODEL_COMPARISON_RUNTIME_BUCKET_LABELS = {
    "local": "Local",
    "cloud": "Cloud",
    "experimental_local": "Experimental local",
}

MODEL_COMPARISON_QUANTIZATION_LABELS = {
    "cloud_managed": "Cloud managed",
    "q2": "Q2",
    "q3": "Q3",
    "q4": "Q4",
    "q5": "Q5",
    "q6": "Q6",
    "q8": "Q8",
    "int4": "INT4",
    "int8": "INT8",
    "fp16": "FP16",
    "fp32": "FP32",
    "gguf_unspecified": "GGUF unspecified",
    "unspecified_local": "Local unspecified",
    "unspecified_experimental": "Experimental unspecified",
}

MODEL_COMPARISON_JSON_REQUIRED_KEYS_BY_USE_CASE = {
    "structured_extraction": ["summary", "risks", "actions", "entities"],
}

MODEL_COMPARISON_TOKEN_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "have",
    "into",
    "your",
    "about",
    "para",
    "como",
    "mais",
    "esse",
    "essa",
    "isso",
    "com",
    "dos",
    "das",
    "uma",
    "uns",
    "umas",
    "sobre",
    "entre",
}


def _extract_metric_tokens(text: str) -> set[str]:
    normalized = re.findall(r"[a-zA-ZÀ-ÿ0-9_]+", str(text or "").lower())
    return {
        token
        for token in normalized
        if len(token) >= 4 and token not in MODEL_COMPARISON_TOKEN_STOPWORDS
    }


def _coerce_json_payload(response_text: str) -> Any | None:
    cleaned = str(response_text or "").strip()
    if not cleaned:
        return None
    fenced_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fenced_match:
        cleaned = fenced_match.group(1).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        return None


def estimate_groundedness_score(response_text: str, retrieved_chunks: list[dict[str, object]]) -> float | None:
    if not response_text or not retrieved_chunks:
        return None
    response_tokens = _extract_metric_tokens(response_text)
    if not response_tokens:
        return None

    context_parts = []
    for chunk in retrieved_chunks:
        if not isinstance(chunk, dict):
            continue
        snippet = str(chunk.get("snippet") or chunk.get("text") or "").strip()
        if snippet:
            context_parts.append(snippet)
    context_tokens = _extract_metric_tokens("\n".join(context_parts))
    if not context_tokens:
        return None

    overlap = len(response_tokens & context_tokens)
    return round(overlap / max(len(response_tokens), 1), 3)


def estimate_schema_adherence_score(
    response_text: str,
    response_format: str,
    benchmark_use_case: str,
) -> float | None:
    if response_format != "json":
        return None

    parsed = _coerce_json_payload(response_text)
    if parsed is None:
        return 0.0
    if not isinstance(parsed, dict):
        return 0.7 if isinstance(parsed, list) else 0.3

    expected_keys = MODEL_COMPARISON_JSON_REQUIRED_KEYS_BY_USE_CASE.get(benchmark_use_case) or []
    if not expected_keys:
        return 1.0

    present_keys = 0
    non_empty_keys = 0
    for key in expected_keys:
        if key not in parsed:
            continue
        present_keys += 1
        value = parsed.get(key)
        if value is not None and value != "":
            non_empty_keys += 1

    coverage = present_keys / max(len(expected_keys), 1)
    completeness = non_empty_keys / max(len(expected_keys), 1)
    return round((coverage * 0.5) + (completeness * 0.5), 3)


def estimate_use_case_fit_score(
    response_text: str,
    response_format: str,
    benchmark_use_case: str,
    *,
    format_adherence: float,
    schema_adherence: float | None,
) -> float:
    cleaned = str(response_text or "").strip()
    if not cleaned:
        return 0.0

    if benchmark_use_case == "structured_extraction":
        return round(float(schema_adherence if schema_adherence is not None else format_adherence), 3)

    if response_format == "bullet_list":
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        bullet_lines = sum(
            1
            for line in lines
            if line.startswith(("-", "•", "*")) or re.match(r"^\d+[.)]\s+", line)
        )
        bullet_coverage = min(bullet_lines / 4, 1.0) if bullet_lines else 0.0
        return round((float(format_adherence) * 0.4) + (bullet_coverage * 0.6), 3)

    if response_format == "json":
        return round(float(schema_adherence if schema_adherence is not None else format_adherence), 3)

    word_count = len(cleaned.split())
    length_signal = min(word_count / 80, 1.0)
    return round((float(format_adherence) * 0.6) + (length_signal * 0.4), 3)


def infer_model_comparison_runtime_bucket(provider_name: str, model_name: str) -> str:
    normalized_provider = str(provider_name or "").strip().lower()
    normalized_model = str(model_name or "").strip().lower()

    if normalized_provider in {"openai", "huggingface_inference"}:
        return "cloud"
    if normalized_provider == "huggingface_server":
        return "local"
    if normalized_provider == "huggingface_local":
        return "experimental_local"
    if "cloud" in normalized_model:
        return "cloud"
    return "local"


def infer_model_comparison_quantization_family(provider_name: str, model_name: str) -> str:
    runtime_bucket = infer_model_comparison_runtime_bucket(provider_name, model_name)
    normalized_model = str(model_name or "").strip().lower()

    if runtime_bucket == "cloud":
        return "cloud_managed"

    quantization_patterns = {
        "q2": r"(^|[^a-z0-9])q2([^a-z0-9]|$)",
        "q3": r"(^|[^a-z0-9])q3([^a-z0-9]|$)",
        "q4": r"(^|[^a-z0-9])q4([^a-z0-9]|$)",
        "q5": r"(^|[^a-z0-9])q5([^a-z0-9]|$)",
        "q6": r"(^|[^a-z0-9])q6([^a-z0-9]|$)",
        "q8": r"(^|[^a-z0-9])q8([^a-z0-9]|$)",
    }
    for family, pattern in quantization_patterns.items():
        if re.search(pattern, normalized_model):
            return family

    if "int4" in normalized_model or "4bit" in normalized_model:
        return "int4"
    if "int8" in normalized_model or "8bit" in normalized_model:
        return "int8"
    if "fp16" in normalized_model or re.search(r"(^|[^a-z0-9])f16([^a-z0-9]|$)", normalized_model):
        return "fp16"
    if "fp32" in normalized_model or re.search(r"(^|[^a-z0-9])f32([^a-z0-9]|$)", normalized_model):
        return "fp32"
    if "gguf" in normalized_model:
        return "gguf_unspecified"
    if runtime_bucket == "experimental_local":
        return "unspecified_experimental"
    return "unspecified_local"


def build_model_comparison_ranking(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    successful_latencies = [
        float(item.get("latency_s"))
        for item in results
        if bool(item.get("success")) and isinstance(item.get("latency_s"), (int, float)) and float(item.get("latency_s")) > 0
    ]
    fastest_latency = min(successful_latencies) if successful_latencies else None

    ranking: list[dict[str, Any]] = []
    for item in results:
        success = bool(item.get("success"))
        adherence = float(item.get("format_adherence") or 0.0)
        latency = float(item.get("latency_s")) if isinstance(item.get("latency_s"), (int, float)) else None
        latency_component = 0.0
        if success and fastest_latency is not None and latency is not None and latency > 0:
            latency_component = min(float(fastest_latency) / float(latency), 1.0)

        comparison_score = round(
            (1.0 if success else 0.0) * 0.45
            + adherence * 0.35
            + latency_component * 0.20,
            3,
        )
        ranking.append(
            {
                "provider": item.get("provider_effective") or item.get("provider_requested"),
                "model": item.get("model_effective") or item.get("model_requested"),
                "runtime_bucket": item.get("runtime_bucket"),
                "quantization_family": item.get("quantization_family"),
                "success": success,
                "latency_s": latency,
                "format_adherence": adherence,
                "groundedness_score": item.get("groundedness_score"),
                "schema_adherence": item.get("schema_adherence"),
                "use_case_fit_score": item.get("use_case_fit_score"),
                "output_chars": int(item.get("output_chars") or 0),
                "output_words": int(item.get("output_words") or 0),
                "used_chunks": int(item.get("used_chunks") or 0),
                "comparison_score": comparison_score,
            }
        )

    ranking.sort(
        key=lambda item: (
            -float(item.get("comparison_score") or 0.0),
            not bool(item.get("success")),
            float(item.get("latency_s")) if isinstance(item.get("latency_s"), (int, float)) else 10**9,
            -float(item.get("format_adherence") or 0.0),
        )
    )
    return ranking


def build_model_comparison_prompt_text(prompt_text: str, response_format: str) -> str:
    cleaned = " ".join(str(prompt_text or "").split()).strip()
    format_instructions = {
        "plain_text": "Responda em texto livre, com clareza e objetividade.",
        "bullet_list": "Responda em bullets curtos, cada linha começando com '-'.",
        "json": "Responda somente com JSON válido, sem markdown e sem texto adicional.",
    }
    extra_instruction = format_instructions.get(response_format, format_instructions["plain_text"])
    return f"{cleaned}\n\nFormato desejado: {extra_instruction}".strip()


def estimate_response_format_adherence(response_text: str, response_format: str) -> float:
    cleaned = str(response_text or "").strip()
    if not cleaned:
        return 0.0

    if response_format == "plain_text":
        return 1.0

    if response_format == "bullet_list":
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if not lines:
            return 0.0
        bullet_lines = sum(
            1
            for line in lines
            if line.startswith(("-", "•", "*")) or re.match(r"^\d+[.)]\s+", line)
        )
        if len(lines) == 1 and bullet_lines == 0:
            return 0.2
        return round(bullet_lines / max(len(lines), 1), 3)

    if response_format == "json":
        try:
            parsed = json.loads(cleaned)
        except Exception:
            return 0.2 if cleaned.startswith(("{", "[")) and cleaned.endswith(("}", "]")) else 0.0
        return 1.0 if isinstance(parsed, (dict, list)) else 0.7

    return 0.0


def run_model_comparison_candidate(
    *,
    registry: dict[str, dict[str, object]],
    provider_name: str,
    model_name: str,
    prompt_profile: str,
    prompt_text: str,
    benchmark_use_case: str,
    response_format: str,
    temperature: float,
    context_window: int,
    retrieved_chunks: list[dict[str, object]],
    rag_settings: RagSettings,
) -> dict[str, Any]:
    runtime_profile = resolve_provider_runtime_profile(
        registry,
        provider_name,
        capability="chat",
        fallback_provider="ollama",
    )
    provider_entry = runtime_profile.get("provider_entry") if isinstance(runtime_profile.get("provider_entry"), dict) else {}
    provider_instance = provider_entry.get("instance")
    effective_provider = str(runtime_profile.get("effective_provider") or provider_name)
    effective_model = str(model_name or provider_entry.get("default_model") or "")

    result: dict[str, Any] = {
        "provider_requested": provider_name,
        "provider_effective": effective_provider,
        "provider_label": provider_entry.get("label") or effective_provider,
        "model_requested": model_name,
        "model_effective": effective_model,
        "runtime_bucket": infer_model_comparison_runtime_bucket(effective_provider, effective_model),
        "quantization_family": infer_model_comparison_quantization_family(effective_provider, effective_model),
        "response_format": response_format,
        "success": False,
        "latency_s": None,
        "output_chars": 0,
        "output_words": 0,
        "format_adherence": 0.0,
        "response_text": "",
        "error": None,
        "context_injected": False,
        "used_chunks": 0,
        "dropped_chunks": 0,
        "context_preview_chars": 0,
        "groundedness_score": None,
        "schema_adherence": None,
        "use_case_fit_score": 0.0,
    }

    if provider_instance is None:
        result["error"] = runtime_profile.get("fallback_reason") or "provider_unavailable"
        return result

    prepared_prompt_text = build_model_comparison_prompt_text(prompt_text, response_format)
    base_messages = build_prompt_messages(
        prompt_profile,
        [{"role": "user", "content": prepared_prompt_text}],
    )

    prompt_context_details: dict[str, Any] = {
        "context_injected": False,
        "used_chunks": 0,
        "dropped_chunks": 0,
        "context_preview_chars": 0,
    }
    if retrieved_chunks:
        messages_for_model, prompt_context_details = inject_rag_context(
            base_messages,
            retrieved_chunks,
            context_window=context_window,
            settings=rag_settings,
        )
    else:
        messages_for_model = base_messages

    started_at = time.perf_counter()
    try:
        stream = provider_instance.stream_chat_completion(
            messages=messages_for_model,
            model=effective_model,
            temperature=temperature,
            context_window=context_window,
        )
        response_text = "".join(provider_instance.iter_stream_text(stream)).strip()
        result["success"] = True
        result["response_text"] = response_text
    except Exception as error:
        result["error"] = str(error)
    finally:
        result["latency_s"] = round(time.perf_counter() - started_at, 4)

    response_text = str(result.get("response_text") or "")
    result["output_chars"] = len(response_text)
    result["output_words"] = len(response_text.split())
    result["format_adherence"] = estimate_response_format_adherence(response_text, response_format)
    result["schema_adherence"] = estimate_schema_adherence_score(
        response_text,
        response_format,
        benchmark_use_case,
    )
    result["groundedness_score"] = estimate_groundedness_score(response_text, retrieved_chunks)
    result["use_case_fit_score"] = estimate_use_case_fit_score(
        response_text,
        response_format,
        benchmark_use_case,
        format_adherence=float(result.get("format_adherence") or 0.0),
        schema_adherence=result.get("schema_adherence") if isinstance(result.get("schema_adherence"), (int, float)) else None,
    )
    result["context_injected"] = bool(prompt_context_details.get("context_injected"))
    result["used_chunks"] = int(prompt_context_details.get("used_chunks") or 0)
    result["dropped_chunks"] = int(prompt_context_details.get("dropped_chunks") or 0)
    result["context_preview_chars"] = int(prompt_context_details.get("context_preview_chars") or 0)
    return result


def summarize_model_comparison_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {
            "total_candidates": 0,
            "success_rate": 0.0,
            "avg_latency_s": 0.0,
            "avg_output_chars": 0.0,
            "avg_output_words": 0.0,
            "avg_format_adherence": 0.0,
            "avg_groundedness_score": 0.0,
            "avg_schema_adherence": 0.0,
            "avg_use_case_fit_score": 0.0,
            "best_latency_candidate": None,
            "best_format_candidate": None,
            "best_groundedness_candidate": None,
            "best_use_case_fit_candidate": None,
            "best_overall_candidate": None,
            "candidate_ranking": [],
        }

    total_candidates = len(results)
    successful = [item for item in results if bool(item.get("success"))]
    latencies = [float(item.get("latency_s")) for item in successful if isinstance(item.get("latency_s"), (int, float))]
    output_chars = [int(item.get("output_chars")) for item in successful if isinstance(item.get("output_chars"), (int, float))]
    output_words = [int(item.get("output_words")) for item in successful if isinstance(item.get("output_words"), (int, float))]
    adherence_scores = [float(item.get("format_adherence")) for item in results if isinstance(item.get("format_adherence"), (int, float))]
    groundedness_scores = [float(item.get("groundedness_score")) for item in results if isinstance(item.get("groundedness_score"), (int, float))]
    schema_scores = [float(item.get("schema_adherence")) for item in results if isinstance(item.get("schema_adherence"), (int, float))]
    use_case_fit_scores = [float(item.get("use_case_fit_score")) for item in results if isinstance(item.get("use_case_fit_score"), (int, float))]
    candidate_ranking = build_model_comparison_ranking(results)

    best_latency_candidate = None
    if successful:
        best_latency_candidate = min(successful, key=lambda item: float(item.get("latency_s") or 10**9))
    best_format_candidate = max(results, key=lambda item: float(item.get("format_adherence") or 0.0)) if results else None
    best_groundedness_candidate = max(
        [item for item in results if isinstance(item.get("groundedness_score"), (int, float))],
        key=lambda item: float(item.get("groundedness_score") or 0.0),
    ) if groundedness_scores else None
    best_use_case_fit_candidate = max(
        [item for item in results if isinstance(item.get("use_case_fit_score"), (int, float))],
        key=lambda item: float(item.get("use_case_fit_score") or 0.0),
    ) if use_case_fit_scores else None
    best_overall_candidate = candidate_ranking[0] if candidate_ranking else None

    return {
        "total_candidates": total_candidates,
        "success_rate": round(len(successful) / max(total_candidates, 1), 3),
        "avg_latency_s": round(sum(latencies) / max(len(latencies), 1), 3) if latencies else 0.0,
        "avg_output_chars": round(sum(output_chars) / max(len(output_chars), 1), 3) if output_chars else 0.0,
        "avg_output_words": round(sum(output_words) / max(len(output_words), 1), 3) if output_words else 0.0,
        "avg_format_adherence": round(sum(adherence_scores) / max(len(adherence_scores), 1), 3) if adherence_scores else 0.0,
        "avg_groundedness_score": round(sum(groundedness_scores) / max(len(groundedness_scores), 1), 3) if groundedness_scores else 0.0,
        "avg_schema_adherence": round(sum(schema_scores) / max(len(schema_scores), 1), 3) if schema_scores else 0.0,
        "avg_use_case_fit_score": round(sum(use_case_fit_scores) / max(len(use_case_fit_scores), 1), 3) if use_case_fit_scores else 0.0,
        "best_latency_candidate": {
            "provider": best_latency_candidate.get("provider_effective"),
            "model": best_latency_candidate.get("model_effective"),
            "latency_s": best_latency_candidate.get("latency_s"),
        } if best_latency_candidate else None,
        "best_format_candidate": {
            "provider": best_format_candidate.get("provider_effective"),
            "model": best_format_candidate.get("model_effective"),
            "format_adherence": best_format_candidate.get("format_adherence"),
        } if best_format_candidate else None,
        "best_groundedness_candidate": {
            "provider": best_groundedness_candidate.get("provider_effective"),
            "model": best_groundedness_candidate.get("model_effective"),
            "groundedness_score": best_groundedness_candidate.get("groundedness_score"),
        } if best_groundedness_candidate else None,
        "best_use_case_fit_candidate": {
            "provider": best_use_case_fit_candidate.get("provider_effective"),
            "model": best_use_case_fit_candidate.get("model_effective"),
            "use_case_fit_score": best_use_case_fit_candidate.get("use_case_fit_score"),
        } if best_use_case_fit_candidate else None,
        "best_overall_candidate": best_overall_candidate,
        "candidate_ranking": candidate_ranking,
    }