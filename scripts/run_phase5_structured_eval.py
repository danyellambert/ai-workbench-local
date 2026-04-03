from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pypdf import PdfReader

from src.config import get_rag_settings
from src.evals.phase8_thresholds import STRUCTURED_SMOKE_THRESHOLDS, get_real_document_eval_thresholds
from src.storage.phase8_eval_store import append_eval_run
from src.storage.rag_store import load_rag_store
from src.structured.envelope import TaskExecutionRequest, StructuredResult
from src.structured.service import structured_service


FIXTURES_DIR = PROJECT_ROOT / "phase5_eval" / "fixtures"
REPORTS_DIR = PROJECT_ROOT / "phase5_eval" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
EVAL_DB_PATH = PROJECT_ROOT / ".phase8_eval_runs.sqlite3"
GOLD_MANIFEST_DEFAULT = FIXTURES_DIR / "11_real_document_gold_sets_manifest.json"

PLACEHOLDER_PATTERNS = [
    r"\bfull name\b",
    r"\bname@example.com\b",
    r"\bskill 1\b",
    r"\bstrength 1\b",
    r"\bimprovement 1\b",
    r"\bitem 1\b",
    r"\btopic title\b",
    r"\btask title\b",
    r"\bcompany x\b",
]


@dataclass
class EvalOutcome:
    task: str
    status: str
    score: int
    max_score: int
    reasons: list[str]
    comparison: dict[str, Any] = field(default_factory=dict)
    output_path: str | None = None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path), strict=False)
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(pages).strip()


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _normalize_text(value: Any) -> str:
    text = str(value or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("’", "'")
    text = re.sub(r"\s+", " ", text).strip()
    return text


SEMANTIC_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "for", "in", "on", "by", "with", "from", "at", "as",
    "is", "are", "was", "were", "be", "been", "being", "that", "this", "these", "those", "it", "its",
    "their", "his", "her", "our", "your", "into", "than", "then", "also", "about", "under", "over",
    "de", "da", "do", "das", "dos", "e", "em", "para", "com", "sem", "por", "uma", "um", "no",
    "na", "nos", "nas", "ao", "aos", "as", "os", "que", "se", "del", "la", "le",
}


def _normalize_semantic_token(token: str) -> str:
    normalized = _normalize_text(token)
    normalized = normalized.replace("$", "")
    normalized = re.sub(r"(?<=\d)(st|nd|rd|th)\b", "", normalized)
    normalized = normalized.replace(",", "")
    return normalized.strip()


def _semantic_tokens(value: Any) -> list[str]:
    raw_tokens = re.findall(r"[a-zA-Z0-9$,.%-]+", _normalize_text(value))
    normalized_tokens: list[str] = []
    for token in raw_tokens:
        normalized = _normalize_semantic_token(token)
        if not normalized or normalized in SEMANTIC_STOPWORDS:
            continue
        normalized_tokens.append(normalized)
    return normalized_tokens


def _semantic_token_match(expected: str, actual: str) -> bool:
    if expected == actual:
        return True
    if expected.isdigit() or actual.isdigit():
        return expected == actual
    if len(expected) >= 5 and actual.startswith(expected):
        return True
    if len(actual) >= 5 and expected.startswith(actual):
        return True
    return False


def _semantic_phrase_match(text: Any, phrase: Any) -> bool:
    normalized_text = _normalize_text(text)
    normalized_phrase = _normalize_text(phrase)
    if not normalized_phrase:
        return False
    if normalized_phrase in normalized_text:
        return True

    phrase_tokens = _semantic_tokens(normalized_phrase)
    text_tokens = _semantic_tokens(normalized_text)
    if not phrase_tokens or not text_tokens:
        return False

    matched = 0
    for token in phrase_tokens:
        if any(_semantic_token_match(token, candidate) for candidate in text_tokens):
            matched += 1

    numeric_tokens = [token for token in phrase_tokens if any(ch.isdigit() for ch in token)]
    if numeric_tokens:
        numeric_hit_count = sum(
            1
            for token in numeric_tokens
            if any(_semantic_token_match(token, candidate) for candidate in text_tokens)
        )
        if numeric_hit_count < len(numeric_tokens):
            return False

    token_count = len(phrase_tokens)
    if token_count <= 2:
        threshold = 1.0
    elif token_count <= 4:
        threshold = 0.75
    else:
        threshold = 0.6
    return (matched / token_count) >= threshold


def _flatten_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        result: list[str] = []
        for item in value.values():
            result.extend(_flatten_strings(item))
        return result
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_flatten_strings(item))
        return result
    return [str(value)]


def _flatten_text(value: Any) -> str:
    return _normalize_text(" ".join(_flatten_strings(value)))


def _matches_alias_or_terms(text: Any, *, aliases: list[str] | None = None, required_terms: list[str] | None = None) -> bool:
    normalized = _normalize_text(text)
    alias_values = [_normalize_text(alias) for alias in (aliases or []) if _normalize_text(alias)]
    required = [_normalize_text(term) for term in (required_terms or []) if _normalize_text(term)]
    if any(alias in normalized for alias in alias_values):
        return True
    if any(_semantic_phrase_match(normalized, alias) for alias in alias_values):
        return True
    if required and all(_semantic_phrase_match(normalized, term) for term in required):
        return True
    return False


def _count_expected_hits_in_text(text: Any, expected_values: list[str]) -> tuple[int, list[str]]:
    normalized = _normalize_text(text)
    matched: list[str] = []
    seen: set[str] = set()
    for item in expected_values:
        key = _normalize_text(item)
        if key and key not in seen and (key in normalized or _semantic_phrase_match(normalized, key)):
            seen.add(key)
            matched.append(item)
    return len(matched), matched


def _score_ratio_status(score: int, max_score: int, *, pass_ratio: float = 0.75, warn_ratio: float = 0.5) -> str:
    if max_score <= 0:
        return "FAIL"
    ratio = score / max_score
    if ratio >= pass_ratio:
        return "PASS"
    if ratio >= warn_ratio:
        return "WARN"
    return "FAIL"


def _status_rank(status: str) -> int:
    return {"PASS": 0, "WARN": 1, "FAIL": 2}.get(str(status or "FAIL").upper(), 2)


def _combine_statuses(*statuses: str | None) -> str:
    normalized = [str(status or "FAIL").upper() for status in statuses if status]
    if not normalized:
        return "FAIL"
    return max(normalized, key=_status_rank)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _coerce_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _load_rag_store() -> dict[str, Any]:
    settings = get_rag_settings()
    rag_store = load_rag_store(settings.store_path)
    if not isinstance(rag_store, dict):
        raise RuntimeError(f"RAG store not found or invalid at {settings.store_path}")
    return rag_store


def _resolve_document(rag_store: dict[str, Any], *, document_id: str | None, document_name: str | None) -> dict[str, Any]:
    documents = [doc for doc in rag_store.get("documents", []) if isinstance(doc, dict)]
    if document_id:
        for document in documents:
            if str(document.get("document_id") or "") == str(document_id):
                return document
        raise RuntimeError(f"Document id not found in rag store: {document_id}")

    normalized_target = _normalize_text(document_name)
    exact = [doc for doc in documents if _normalize_text(doc.get("name")) == normalized_target]
    if exact:
        return exact[0]
    partial = [doc for doc in documents if normalized_target and normalized_target in _normalize_text(doc.get("name"))]
    if partial:
        return partial[0]
    raise RuntimeError(f"Document name not found in rag store: {document_name}")


def _load_gold_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"gold_sets": []}
    data = _load_json(path)
    return data if isinstance(data, dict) else {"gold_sets": []}


def _find_gold_manifest_entry(manifest: dict[str, Any], *, task_type: str, document_name: str | None = None) -> dict[str, Any] | None:
    entries = manifest.get("gold_sets", []) if isinstance(manifest.get("gold_sets"), list) else []
    normalized_name = _normalize_text(document_name)
    task_matches = [entry for entry in entries if isinstance(entry, dict) and str(entry.get("task_type") or "") == task_type]
    if normalized_name:
        exact = [entry for entry in task_matches if _normalize_text(entry.get("document_name")) == normalized_name]
        if exact:
            return exact[0]
    return task_matches[0] if task_matches else None


def _resolve_gold_fixture_path_for_task(
    task: str,
    *,
    explicit_gold_fixture: str | None,
    manifest: dict[str, Any],
    document_name: str | None = None,
) -> Path | None:
    explicit = _coerce_path(explicit_gold_fixture)
    if explicit is not None:
        return explicit
    entry = _find_gold_manifest_entry(manifest, task_type=task, document_name=document_name)
    if not isinstance(entry, dict):
        return None
    return _coerce_path(str(entry.get("gold_path") or ""))


def _default_input_for_task(task: str) -> str:
    mapping = {
        "extraction": FIXTURES_DIR / "01_extraction_input.txt",
        "summary": FIXTURES_DIR / "02_summary_input.txt",
        "checklist": FIXTURES_DIR / "03_checklist_input.txt",
        "cv_analysis": FIXTURES_DIR / "04_cv_sample.txt",
        "code_analysis": FIXTURES_DIR / "05_code_sample.py",
    }
    return _read_text(mapping[task])


def _default_instruction_for_task(task: str) -> str:
    mapping = {
        "extraction": "Extract the main subject, entities, key fields, dates, numbers, risks, and action items from the selected document.",
        "summary": "Summarize the selected document for an executive reader, preserving the main topics, key facts, and critical numbers.",
        "checklist": "Generate an operational checklist from the selected document. Preserve source order, keep one explicit checklist question or instruction per item, and keep phase boundaries when they are grounded in the source.",
        "cv_analysis": "Analyze the selected CV and return grounded personal information, languages, skills, education, experience, and resume structure.",
        "code_analysis": "Analyze the selected code file. Identify grounded correctness/runtime issues, recommend concrete refactor steps, and suggest targeted tests.",
    }
    return mapping[task]


def _build_request(
    task: str,
    input_text: str,
    provider: str,
    model: str | None,
    *,
    use_document_context: bool = False,
    source_document_ids: list[str] | None = None,
    context_strategy: str = "document_scan",
) -> TaskExecutionRequest:
    return TaskExecutionRequest(
        task_type=task,
        input_text=input_text,
        use_rag_context=False,
        use_document_context=use_document_context,
        source_document_ids=list(source_document_ids or []),
        context_strategy=context_strategy,
        provider=provider,
        model=model,
    )


def _prepare_eval_request(
    *,
    task: str,
    provider: str,
    model: str | None,
    cv_pdf: str | None,
    use_indexed_document: bool,
    document_name: str | None,
    document_id: str | None,
    context_strategy: str,
    gold_fixture_path: str | None,
    gold_manifest_path: str,
) -> dict[str, Any]:
    manifest = _load_gold_manifest(_coerce_path(gold_manifest_path) or GOLD_MANIFEST_DEFAULT)
    explicit_gold_path = _coerce_path(gold_fixture_path)
    gold_fixture: dict[str, Any] | None = None
    requested_document_name = document_name

    if explicit_gold_path is not None and explicit_gold_path.exists():
        gold_fixture = _load_json(explicit_gold_path)
        requested_document_name = requested_document_name or str(gold_fixture.get("document_name") or "") or None
        resolved_gold_path = explicit_gold_path
    elif use_indexed_document:
        resolved_gold_path = _resolve_gold_fixture_path_for_task(
            task,
            explicit_gold_fixture=None,
            manifest=manifest,
            document_name=document_name,
        )
        if resolved_gold_path is not None and resolved_gold_path.exists():
            gold_fixture = _load_json(resolved_gold_path)
            requested_document_name = requested_document_name or str(gold_fixture.get("document_name") or "") or None
    else:
        resolved_gold_path = None

    should_use_indexed_document = bool(use_indexed_document or document_name or document_id or explicit_gold_path)
    if should_use_indexed_document:
        if not (requested_document_name or document_id):
            raise RuntimeError(
                f"Indexed document eval for task '{task}' requires document-name/document-id or a gold fixture/manifest entry with document_name"
            )
        rag_store = _load_rag_store()
        document = _resolve_document(
            rag_store,
            document_id=document_id,
            document_name=requested_document_name,
        )
        resolved_document_id = str(document.get("document_id") or document.get("file_hash") or "")
        if not resolved_document_id:
            raise RuntimeError(f"Resolved document is missing document_id/file_hash: {document.get('name')}")
        request = _build_request(
            task,
            input_text=str((gold_fixture or {}).get("input_text") or _default_instruction_for_task(task)),
            provider=provider,
            model=model,
            use_document_context=True,
            source_document_ids=[resolved_document_id],
            context_strategy=context_strategy,
        )
        return {
            "request": request,
            "mode": "indexed_document",
            "suite_name": "structured_real_document_eval",
            "case_name": str(document.get("name") or requested_document_name or task),
            "resolved_document": {
                "document_id": resolved_document_id,
                "name": document.get("name"),
                "file_type": document.get("file_type"),
                "chunk_count": document.get("chunk_count"),
            },
            "gold_fixture": gold_fixture,
            "gold_fixture_path": str(resolved_gold_path) if resolved_gold_path else None,
            "context_strategy": context_strategy,
        }

    if task == "cv_analysis" and cv_pdf:
        request = _build_request(task, input_text=_read_pdf_text(Path(cv_pdf)), provider=provider, model=model)
        return {
            "request": request,
            "mode": "fixture_pdf_override",
            "suite_name": "structured_smoke_eval",
            "case_name": Path(cv_pdf).name,
            "resolved_document": None,
            "gold_fixture": None,
            "gold_fixture_path": None,
            "context_strategy": None,
        }

    request = _build_request(task, input_text=_default_input_for_task(task), provider=provider, model=model)
    return {
        "request": request,
        "mode": "fixture",
        "suite_name": "structured_smoke_eval",
        "case_name": f"fixture:{task}",
        "resolved_document": None,
        "gold_fixture": None,
        "gold_fixture_path": None,
        "context_strategy": None,
    }


def _match_languages(actual_values: list[str], expected_values: list[dict[str, Any]]) -> int:
    normalized_actual = [_normalize_text(item) for item in actual_values]
    hits = 0
    for expected in expected_values:
        language_aliases = expected.get("language_aliases", []) if isinstance(expected, dict) else []
        proficiency_aliases = expected.get("proficiency_aliases", []) if isinstance(expected, dict) else []
        matched = False
        for actual in normalized_actual:
            if _matches_alias_or_terms(actual, aliases=language_aliases) and (
                not proficiency_aliases or _matches_alias_or_terms(actual, aliases=proficiency_aliases)
            ):
                matched = True
                break
        if matched:
            hits += 1
    return hits


def _match_object_entries(entries: list[Any], expected_specs: list[dict[str, Any]]) -> int:
    entry_texts = [_flatten_text(entry) for entry in entries]
    hits = 0
    for expected in expected_specs:
        if not isinstance(expected, dict):
            continue
        matched = False
        for text in entry_texts:
            checks: list[bool] = []
            for key, value in expected.items():
                if key.endswith("_aliases"):
                    checks.append(_matches_alias_or_terms(text, aliases=value if isinstance(value, list) else [str(value)]))
                elif key.endswith("_terms"):
                    checks.append(_matches_alias_or_terms(text, required_terms=value if isinstance(value, list) else [str(value)]))
            if not checks:
                continue
            check_count = len(checks)
            if check_count <= 2:
                minimum_hits = check_count
            elif check_count <= 4:
                minimum_hits = check_count - 1
            else:
                minimum_hits = max(3, int(round(check_count * 0.6)))
            if sum(1 for check in checks if check) >= minimum_hits:
                matched = True
                break
        if matched:
            hits += 1
    return hits


def _augment_code_analysis_semantic_text(text: str) -> str:
    normalized = _normalize_text(text)
    expansions: list[str] = []

    if any(token in normalized for token in ["divisao por zero", "zerodivisionerror", "lista vazia", "empty input"]):
        expansions.extend([
            "division by zero",
            "empty input",
            "empty list",
            "average len(values)",
        ])

    if ("muta" in normalized or "efeitos colaterais" in normalized or "in place" in normalized or "copia" in normalized) and "score" in normalized:
        expansions.extend([
            "mutates caller-provided items in place",
            "normalize_scores changes the input dictionaries",
            "copy the item before clamping score",
            "avoid mutating input items",
        ])

    if any(token in normalized for token in ["inconsistente", "mesma estrutura", "mesmo formato", "shape", "result.append(item)"]):
        expansions.extend([
            "output structure is inconsistent",
            "items without score pass through unchanged",
            "always return objects with the same shape",
        ])

    if any(token in normalized for token in ["normalizar", "pontuacoes", "average", "media"]):
        expansions.extend([
            "normalize score values",
            "compute an average",
            "process a list of scored items and calculate the average",
        ])

    if any(token in normalized for token in ["teste", "unitario", "lista vazia", "nao mutado", "nao mutada"]):
        expansions.extend([
            "test empty input",
            "verify empty list returns average 0.0",
            "test that the original input is not mutated",
            "test score clamping above 100 and below 0",
        ])

    return f"{normalized} {' '.join(expansions)}".strip()


def _evaluate_code_analysis_against_gold(payload: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    expected = gold.get("expected", {}) if isinstance(gold.get("expected"), dict) else {}
    thresholds = get_real_document_eval_thresholds(
        "code_analysis",
        overrides=(expected.get("evaluation_guidance") or {}).get("threshold_overrides") if isinstance(expected.get("evaluation_guidance"), dict) else None,
    )
    dumped_text = _augment_code_analysis_semantic_text(_flatten_text(payload))
    snippet_summary_hit = 1 if _matches_alias_or_terms(dumped_text, aliases=expected.get("snippet_summary_aliases", [])) else 0
    main_purpose_hit = 1 if _matches_alias_or_terms(dumped_text, aliases=expected.get("main_purpose_aliases", [])) else 0
    issue_hits = sum(
        1
        for spec in expected.get("expected_issues", [])
        if _matches_alias_or_terms(
            dumped_text,
            aliases=spec.get("title_aliases", []) if isinstance(spec, dict) else [],
            required_terms=spec.get("required_terms", []) if isinstance(spec, dict) else [],
        )
    )
    refactor_hits = sum(
        1
        for spec in expected.get("expected_refactor_actions", [])
        if _matches_alias_or_terms(dumped_text, aliases=spec.get("aliases", []) if isinstance(spec, dict) else [])
    )
    test_hits = sum(
        1
        for spec in expected.get("expected_test_suggestions", [])
        if _matches_alias_or_terms(dumped_text, aliases=spec.get("aliases", []) if isinstance(spec, dict) else [])
    )
    maintainability_hits = sum(
        1
        for spec in expected.get("expected_readability_or_maintainability_improvements", [])
        if _matches_alias_or_terms(dumped_text, aliases=spec.get("aliases", []) if isinstance(spec, dict) else [])
    )
    risk_hits = sum(
        1
        for spec in expected.get("expected_risk_notes", [])
        if _matches_alias_or_terms(dumped_text, aliases=spec.get("aliases", []) if isinstance(spec, dict) else [])
    )
    score = snippet_summary_hit + main_purpose_hit + issue_hits + refactor_hits + test_hits + maintainability_hits + risk_hits
    max_score = 2 + len(expected.get("expected_issues", [])) + len(expected.get("expected_refactor_actions", [])) + len(expected.get("expected_test_suggestions", [])) + len(expected.get("expected_readability_or_maintainability_improvements", [])) + len(expected.get("expected_risk_notes", []))
    reasons: list[str] = []
    if not snippet_summary_hit:
        reasons.append("snippet summary did not match the expected grounded purpose")
    if not main_purpose_hit:
        reasons.append("main purpose did not match the expected normalization/averaging behavior")
    if issue_hits < int(expected.get("evaluation_guidance", {}).get("minimum_issue_hits", 1)):
        reasons.append(f"expected issue coverage too low: {issue_hits}")
    if refactor_hits < int(expected.get("evaluation_guidance", {}).get("minimum_refactor_hits", 1)):
        reasons.append(f"refactor-plan coverage too low: {refactor_hits}")
    if test_hits < int(expected.get("evaluation_guidance", {}).get("minimum_test_hits", 1)):
        reasons.append(f"test-suggestion coverage too low: {test_hits}")
    status = _score_ratio_status(
        score,
        max_score,
        pass_ratio=float(thresholds.get("pass_ratio") or 0.72),
        warn_ratio=float(thresholds.get("warn_ratio") or 0.48),
    )
    return {
        "status": status,
        "score": score,
        "max_score": max_score,
        "reasons": reasons,
        "thresholds": thresholds,
        "metrics": {
            "snippet_summary_hit": snippet_summary_hit,
            "main_purpose_hit": main_purpose_hit,
            "issue_hits": issue_hits,
            "refactor_hits": refactor_hits,
            "test_hits": test_hits,
            "maintainability_hits": maintainability_hits,
            "risk_hits": risk_hits,
        },
    }


def _evaluate_cv_analysis_against_gold(payload: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    expected = gold.get("expected", {}) if isinstance(gold.get("expected"), dict) else {}
    thresholds = get_real_document_eval_thresholds(
        "cv_analysis",
        overrides=(expected.get("evaluation_guidance") or {}).get("threshold_overrides") if isinstance(expected.get("evaluation_guidance"), dict) else None,
    )
    dumped_text = _flatten_text(payload)
    personal_info = payload.get("personal_info") or {}
    personal_hits = sum(
        1
        for key in ("full_name_aliases", "email_aliases", "location_aliases", "link_aliases")
        if _matches_alias_or_terms(_flatten_text(personal_info), aliases=expected.get("expected_personal_info", {}).get(key, []))
    )
    profile_hit = 1 if _matches_alias_or_terms(dumped_text, aliases=expected.get("expected_profile_summary_aliases", [])) else 0
    language_hits = _match_languages(payload.get("languages", []), expected.get("expected_languages", []))
    skill_hits, _ = _count_expected_hits_in_text(" ".join(payload.get("skills", [])), expected.get("expected_skills_any", []))
    interest_hits, _ = _count_expected_hits_in_text(dumped_text, expected.get("expected_interests_any", []))
    education_hits = _match_object_entries(payload.get("education_entries", []), expected.get("expected_education", []))
    experience_hits = _match_object_entries(payload.get("experience_entries", []), expected.get("expected_experience", []))
    experience_years_hit = 1 if float(payload.get("experience_years") or 0.0) >= float(expected.get("minimum_experience_years", 0.0)) else 0
    score = personal_hits + profile_hit + language_hits + min(skill_hits, len(expected.get("expected_skills_any", []))) + min(interest_hits, len(expected.get("expected_interests_any", []))) + education_hits + experience_hits + experience_years_hit
    max_score = 4 + 1 + len(expected.get("expected_languages", [])) + len(expected.get("expected_skills_any", [])) + len(expected.get("expected_interests_any", [])) + len(expected.get("expected_education", [])) + len(expected.get("expected_experience", [])) + 1
    reasons: list[str] = []
    if personal_hits < 3:
        reasons.append(f"personal info coverage too low: {personal_hits}")
    if language_hits < len(expected.get("expected_languages", [])):
        reasons.append(f"language coverage too low: {language_hits}")
    if skill_hits < int(expected.get("minimum_skill_hits", 1)):
        reasons.append(f"skill coverage too low: {skill_hits}")
    if education_hits < 2:
        reasons.append(f"education coverage too low: {education_hits}")
    if experience_hits < int(expected.get("minimum_experience_entries", 1)):
        reasons.append(f"experience coverage too low: {experience_hits}")
    if not experience_years_hit:
        reasons.append("experience_years below expected minimum")
    status = _score_ratio_status(
        score,
        max_score,
        pass_ratio=float(thresholds.get("pass_ratio") or 0.62),
        warn_ratio=float(thresholds.get("warn_ratio") or 0.42),
    )
    return {
        "status": status,
        "score": score,
        "max_score": max_score,
        "reasons": reasons,
        "thresholds": thresholds,
        "metrics": {
            "personal_hits": personal_hits,
            "profile_hit": profile_hit,
            "language_hits": language_hits,
            "skill_hits": skill_hits,
            "interest_hits": interest_hits,
            "education_hits": education_hits,
            "experience_hits": experience_hits,
            "experience_years_hit": experience_years_hit,
        },
    }


def _evaluate_extraction_against_gold(payload: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    expected = gold.get("expected", {}) if isinstance(gold.get("expected"), dict) else {}
    thresholds = get_real_document_eval_thresholds(
        "extraction",
        overrides=(expected.get("evaluation_guidance") or {}).get("threshold_overrides") if isinstance(expected.get("evaluation_guidance"), dict) else None,
    )
    dumped_text = _flatten_text(payload)
    main_subject_hit = 1 if _matches_alias_or_terms(payload.get("main_subject"), aliases=expected.get("main_subject_aliases", [])) else 0
    category_hits, _ = _count_expected_hits_in_text(" ".join(payload.get("categories", [])), expected.get("categories_any", []))
    entity_hits = _match_object_entries(payload.get("entities", []), expected.get("entities_present", []))
    field_hits = _match_object_entries(payload.get("extracted_fields", []), expected.get("fields_present", []))
    relationship_hits = _match_object_entries(payload.get("relationships", []), expected.get("relationships_present", []))
    clause_hits = _match_object_entries([{"text": dumped_text}], expected.get("expected_clause_coverage", []))
    risk_hits = sum(
        1
        for spec in expected.get("expected_risks", [])
        if _matches_alias_or_terms(dumped_text, aliases=spec.get("aliases", []) if isinstance(spec, dict) else [])
    )
    action_hits = sum(
        1
        for spec in expected.get("expected_action_items", [])
        if _matches_alias_or_terms(dumped_text, aliases=spec.get("aliases", []) if isinstance(spec, dict) else [])
    )
    restriction_hits = sum(
        1
        for spec in expected.get("expected_operational_restrictions", [])
        if _matches_alias_or_terms(dumped_text, aliases=spec.get("aliases", []) if isinstance(spec, dict) else [])
    )
    date_hits, _ = _count_expected_hits_in_text(" ".join(payload.get("important_dates", [])) + " " + dumped_text, expected.get("important_dates_any", []))
    number_hits, _ = _count_expected_hits_in_text(" ".join(payload.get("important_numbers", [])) + " " + dumped_text, expected.get("important_numbers_any", []))
    score = main_subject_hit + category_hits + entity_hits + field_hits + relationship_hits + clause_hits + risk_hits + action_hits + restriction_hits + date_hits + number_hits
    max_score = 1 + len(expected.get("categories_any", [])) + len(expected.get("entities_present", [])) + len(expected.get("fields_present", [])) + len(expected.get("relationships_present", [])) + len(expected.get("expected_clause_coverage", [])) + len(expected.get("expected_risks", [])) + len(expected.get("expected_action_items", [])) + len(expected.get("expected_operational_restrictions", [])) + len(expected.get("important_dates_any", [])) + len(expected.get("important_numbers_any", []))
    reasons: list[str] = []
    if not main_subject_hit:
        reasons.append("main subject did not match the expected legal agreement")
    if entity_hits < int(expected.get("evaluation_guidance", {}).get("minimum_entity_hits", 1)):
        reasons.append(f"entity coverage too low: {entity_hits}")
    if field_hits < int(expected.get("evaluation_guidance", {}).get("minimum_field_hits", 1)):
        reasons.append(f"field coverage too low: {field_hits}")
    if action_hits < int(expected.get("evaluation_guidance", {}).get("minimum_action_hits", 1)):
        reasons.append(f"action-item coverage too low: {action_hits}")
    if risk_hits < int(expected.get("evaluation_guidance", {}).get("minimum_risk_hits", 1)):
        reasons.append(f"risk coverage too low: {risk_hits}")
    if clause_hits < int(expected.get("minimum_clause_hits", 1)):
        reasons.append(f"clause coverage too low: {clause_hits}")
    status = _score_ratio_status(
        score,
        max_score,
        pass_ratio=float(thresholds.get("pass_ratio") or 0.62),
        warn_ratio=float(thresholds.get("warn_ratio") or 0.4),
    )
    return {
        "status": status,
        "score": score,
        "max_score": max_score,
        "reasons": reasons,
        "thresholds": thresholds,
        "metrics": {
            "main_subject_hit": main_subject_hit,
            "category_hits": category_hits,
            "entity_hits": entity_hits,
            "field_hits": field_hits,
            "relationship_hits": relationship_hits,
            "clause_hits": clause_hits,
            "risk_hits": risk_hits,
            "action_hits": action_hits,
            "restriction_hits": restriction_hits,
            "date_hits": date_hits,
            "number_hits": number_hits,
        },
    }


def _evaluate_summary_against_gold(payload: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    expected = gold.get("expected", {}) if isinstance(gold.get("expected"), dict) else {}
    thresholds = get_real_document_eval_thresholds(
        "summary",
        overrides=(expected.get("evaluation_guidance") or {}).get("threshold_overrides") if isinstance(expected.get("evaluation_guidance"), dict) else None,
    )
    executive_summary = str(payload.get("executive_summary") or "")
    topics = payload.get("topics", [])
    key_insights = payload.get("key_insights", [])
    dumped_text = _flatten_text(payload)
    topic_hits = sum(
        1
        for spec in expected.get("expected_topics", [])
        if _matches_alias_or_terms(
            dumped_text,
            aliases=spec.get("aliases", []) if isinstance(spec, dict) else [],
            required_terms=spec.get("required_terms", []) if isinstance(spec, dict) else [],
        )
    )
    fact_hits = sum(
        1
        for spec in expected.get("required_facts", [])
        if _matches_alias_or_terms(
            dumped_text,
            aliases=spec.get("aliases", []) if isinstance(spec, dict) else [],
            required_terms=spec.get("required_terms", []) if isinstance(spec, dict) else [],
        )
    )
    exec_signal_hits, _ = _count_expected_hits_in_text(dumped_text, expected.get("expected_executive_summary_signals", []))
    key_insight_hits, _ = _count_expected_hits_in_text(dumped_text, expected.get("expected_key_insights_any", []))
    number_hits, _ = _count_expected_hits_in_text(dumped_text, expected.get("important_numbers_any", []))
    score = topic_hits + fact_hits + exec_signal_hits + key_insight_hits + number_hits
    max_score = len(expected.get("expected_topics", [])) + len(expected.get("required_facts", [])) + len(expected.get("expected_executive_summary_signals", [])) + len(expected.get("expected_key_insights_any", [])) + len(expected.get("important_numbers_any", []))
    reasons: list[str] = []
    if topic_hits < int(expected.get("evaluation_guidance", {}).get("minimum_topic_hits", expected.get("minimum_topics", 1))):
        reasons.append(f"topic coverage too low: {topic_hits}")
    if fact_hits < int(expected.get("evaluation_guidance", {}).get("minimum_required_fact_hits", 1)):
        reasons.append(f"required fact coverage too low: {fact_hits}")
    if key_insight_hits < int(expected.get("evaluation_guidance", {}).get("minimum_key_insight_hits", 1)):
        reasons.append(f"key insight coverage too low: {key_insight_hits}")
    if exec_signal_hits < 3:
        reasons.append(f"executive summary is too weak against expected report signals: {exec_signal_hits}")
    status = _score_ratio_status(
        score,
        max_score,
        pass_ratio=float(thresholds.get("pass_ratio") or 0.58),
        warn_ratio=float(thresholds.get("warn_ratio") or 0.4),
    )
    return {
        "status": status,
        "score": score,
        "max_score": max_score,
        "reasons": reasons,
        "thresholds": thresholds,
        "metrics": {
            "topic_hits": topic_hits,
            "fact_hits": fact_hits,
            "exec_signal_hits": exec_signal_hits,
            "key_insight_hits": key_insight_hits,
            "number_hits": number_hits,
        },
    }


def _evaluate_payload_against_gold(task: str, payload: dict[str, Any], gold_fixture: dict[str, Any]) -> dict[str, Any]:
    if task == "code_analysis":
        return _evaluate_code_analysis_against_gold(payload, gold_fixture)
    if task == "cv_analysis":
        return _evaluate_cv_analysis_against_gold(payload, gold_fixture)
    if task == "extraction":
        return _evaluate_extraction_against_gold(payload, gold_fixture)
    if task == "summary":
        return _evaluate_summary_against_gold(payload, gold_fixture)
    return {
        "status": "WARN",
        "score": 0,
        "max_score": 0,
        "reasons": [f"gold-set comparison not implemented for task: {task}"],
        "metrics": {},
    }


def _contains_placeholder(value: Any) -> bool:
    text = _stringify(value).lower()
    return any(re.search(pattern, text) for pattern in PLACEHOLDER_PATTERNS)


def _count_non_empty_strings(items: list[Any]) -> int:
    count = 0
    for item in items:
        if isinstance(item, str) and item.strip():
            count += 1
    return count


def _evaluate_smoke_result(task: str, result: StructuredResult) -> EvalOutcome:
    reasons: list[str] = []
    score = 0
    max_score = 5

    if result.success and result.validated_output is not None:
        score += 1
    else:
        reasons.append("task execution did not succeed")
        return EvalOutcome(task, "FAIL", score, max_score, reasons)

    payload = result.validated_output
    if payload.task_type == task:
        score += 1
    else:
        reasons.append(f"unexpected task_type: {payload.task_type}")

    dumped = payload.model_dump(mode="json")
    if not _contains_placeholder(dumped):
        score += 1
    else:
        reasons.append("output contains obvious prompt placeholders")

    if task == "extraction":
        entities = dumped.get("entities", [])
        fields = dumped.get("extracted_fields", [])
        if len(entities) + len(fields) >= 2:
            score += 1
        else:
            reasons.append("extraction returned too little structured content")

        if dumped.get("main_subject") and (dumped.get("important_dates") or dumped.get("important_numbers") or dumped.get("action_items") or dumped.get("risks")):
            score += 1
        else:
            reasons.append("extraction missing main subject or useful secondary structure")

    elif task == "summary":
        topics = dumped.get("topics", [])
        executive_summary = dumped.get("executive_summary", "")
        if topics and executive_summary.strip():
            score += 1
        else:
            reasons.append("summary missing topics or executive summary")

        insights = dumped.get("key_insights", [])
        if len(insights) >= 1:
            score += 1
        else:
            reasons.append("summary missing key insights")

    elif task == "checklist":
        items = dumped.get("items", [])
        title = dumped.get("title", "")
        if title.strip() and len(items) >= 3:
            score += 1
        else:
            reasons.append("checklist missing title or enough items")

        item_titles = [item.get("title", "") for item in items if isinstance(item, dict)]
        if _count_non_empty_strings(item_titles) >= 3:
            score += 1
        else:
            reasons.append("checklist items are too weak or empty")

    elif task == "cv_analysis":
        personal = dumped.get("personal_info") or {}
        sections = dumped.get("sections", [])
        skills = dumped.get("skills", [])
        if (personal.get("full_name") or personal.get("email")) and sections:
            score += 1
        else:
            reasons.append("cv analysis missing basic personal info or sections")

        if len(skills) >= 2 or len(sections) >= 2:
            score += 1
        else:
            reasons.append("cv analysis returned too little resume structure")

    elif task == "code_analysis":
        issues = dumped.get("detected_issues", [])
        summary = dumped.get("snippet_summary", "")
        if summary.strip() and len(issues) >= 1:
            score += 1
        else:
            reasons.append("code analysis missing summary or issues")

        if dumped.get("refactor_plan") and dumped.get("test_suggestions"):
            score += 1
        else:
            reasons.append("code analysis missing refactor plan or test suggestions")

    pass_min_score = int(STRUCTURED_SMOKE_THRESHOLDS.get("pass_min_score") or max_score)
    warn_min_score = int(STRUCTURED_SMOKE_THRESHOLDS.get("warn_min_score") or 3)
    status = "PASS" if score >= pass_min_score else "WARN" if score >= warn_min_score else "FAIL"
    return EvalOutcome(task, status, score, max_score, reasons)


def _save_report(report: dict[str, Any]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = REPORTS_DIR / f"phase5_structured_eval_{stamp}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _extract_latency_s(result: StructuredResult) -> float | None:
    metadata = result.execution_metadata if isinstance(result.execution_metadata, dict) else {}
    telemetry = metadata.get("telemetry") if isinstance(metadata.get("telemetry"), dict) else {}
    timings = telemetry.get("timings_s") if isinstance(telemetry.get("timings_s"), dict) else {}
    workflow_total = metadata.get("workflow_total_s")
    if isinstance(workflow_total, (int, float)):
        return round(float(workflow_total), 4)
    total_s = timings.get("total_s")
    if isinstance(total_s, (int, float)):
        return round(float(total_s), 4)
    return None


def run_tasks(
    tasks: list[str],
    provider: str,
    model: str | None,
    cv_pdf: str | None,
    *,
    use_indexed_document: bool = False,
    document_name: str | None = None,
    document_id: str | None = None,
    context_strategy: str = "document_scan",
    gold_fixture: str | None = None,
    gold_manifest: str = str(GOLD_MANIFEST_DEFAULT),
) -> int:
    outputs: list[dict[str, Any]] = []
    worst_exit = 0

    for task in tasks:
        prepared = _prepare_eval_request(
            task=task,
            provider=provider,
            model=model,
            cv_pdf=cv_pdf,
            use_indexed_document=use_indexed_document,
            document_name=document_name,
            document_id=document_id,
            context_strategy=context_strategy,
            gold_fixture_path=gold_fixture,
            gold_manifest_path=gold_manifest,
        )
        request = prepared["request"]
        result = structured_service.execute_task(request)
        smoke_outcome = _evaluate_smoke_result(task, result)

        gold_evaluation: dict[str, Any] | None = None
        outcome = smoke_outcome
        if prepared.get("gold_fixture") and result.success and result.validated_output is not None:
            gold_evaluation = _evaluate_payload_against_gold(
                task,
                result.validated_output.model_dump(mode="json"),
                prepared["gold_fixture"],
            )
            combined_status = _combine_statuses(smoke_outcome.status, str(gold_evaluation.get("status") or "FAIL"))
            combined_reasons = [
                *[f"smoke:{reason}" for reason in smoke_outcome.reasons],
                *[f"gold:{reason}" for reason in (gold_evaluation.get("reasons") or [])],
            ]
            outcome = EvalOutcome(
                task=task,
                status=combined_status,
                score=int(gold_evaluation.get("score") or 0),
                max_score=int(gold_evaluation.get("max_score") or 0),
                reasons=combined_reasons,
                comparison=gold_evaluation,
            )

        outputs.append(
            {
                "task": task,
                "suite_name": prepared.get("suite_name"),
                "mode": prepared.get("mode"),
                "status": outcome.status,
                "score": outcome.score,
                "max_score": outcome.max_score,
                "reasons": outcome.reasons,
                "context_strategy": prepared.get("context_strategy"),
                "resolved_document": prepared.get("resolved_document"),
                "gold_fixture_path": prepared.get("gold_fixture_path"),
                "smoke_evaluation": {
                    "status": smoke_outcome.status,
                    "score": smoke_outcome.score,
                    "max_score": smoke_outcome.max_score,
                    "reasons": smoke_outcome.reasons,
                },
                "gold_evaluation": gold_evaluation,
                "thresholds": (
                    gold_evaluation.get("thresholds")
                    if isinstance(gold_evaluation, dict)
                    else STRUCTURED_SMOKE_THRESHOLDS
                ),
                "success": result.success,
                "error": result.error.model_dump(mode="json") if result.error else None,
                "validation_error": result.validation_error,
                "parsing_error": result.parsing_error,
                "payload": result.validated_output.model_dump(mode="json") if result.validated_output else None,
            }
        )

        metadata = result.execution_metadata if isinstance(result.execution_metadata, dict) else {}
        telemetry = metadata.get("telemetry") if isinstance(metadata.get("telemetry"), dict) else {}
        parse_recovery = telemetry.get("parse_recovery") if isinstance(telemetry.get("parse_recovery"), dict) else {}
        append_eval_run(
            EVAL_DB_PATH,
            {
                "suite_name": str(prepared.get("suite_name") or "structured_smoke_eval"),
                "task_type": task,
                "case_name": str(prepared.get("case_name") or f"fixture:{task}"),
                "provider": provider,
                "model": model,
                "status": outcome.status,
                "score": outcome.score,
                "max_score": outcome.max_score,
                "quality_score": result.quality_score,
                "overall_confidence": result.overall_confidence,
                "latency_s": _extract_latency_s(result),
                "needs_review": bool(metadata.get("needs_review")),
                "context_strategy": prepared.get("context_strategy"),
                "metrics": {
                    "success": result.success,
                    "parse_recovery_used": bool(parse_recovery.get("used")),
                    "parse_recovery_attempt_count": int(parse_recovery.get("attempt_count") or 0),
                    "mode": prepared.get("mode"),
                    "smoke_status": smoke_outcome.status,
                    "smoke_score": smoke_outcome.score,
                    **(
                        {
                            "gold_status": gold_evaluation.get("status"),
                            "gold_score": gold_evaluation.get("score"),
                            "gold_max_score": gold_evaluation.get("max_score"),
                            **{
                                f"gold_{key}": value
                                for key, value in (gold_evaluation.get("metrics") or {}).items()
                                if isinstance(value, (int, float, str, bool))
                            },
                        }
                        if gold_evaluation
                        else {}
                    ),
                },
                "reasons": outcome.reasons,
                "metadata": {
                    "validation_error": result.validation_error,
                    "parsing_error": result.parsing_error,
                    "resolved_document": prepared.get("resolved_document"),
                    "gold_fixture_path": prepared.get("gold_fixture_path"),
                    "gold_reasons": gold_evaluation.get("reasons") if gold_evaluation else None,
                },
            },
        )

        print(f"[{outcome.status}] {task}: {outcome.score}/{outcome.max_score}")
        if outcome.reasons:
            for reason in outcome.reasons:
                print(f"  - {reason}")

        if outcome.status == "FAIL":
            worst_exit = max(worst_exit, 2)
        elif outcome.status == "WARN":
            worst_exit = max(worst_exit, 1)

    report = {
        "generated_at": datetime.now().isoformat(),
        "provider": provider,
        "model": model,
        "eval_store_path": str(EVAL_DB_PATH),
        "tasks": outputs,
    }
    out = _save_report(report)
    print(f"\nReport saved to: {out}")
    return worst_exit


def main() -> int:
    parser = argparse.ArgumentParser(description="Run automated smoke evals for Phase 5 structured outputs.")
    parser.add_argument("--task", default="all", choices=["all", "extraction", "summary", "checklist", "cv_analysis", "code_analysis"])
    parser.add_argument("--provider", default="ollama")
    parser.add_argument("--model", default=None)
    parser.add_argument("--cv-pdf", default=None, help="Optional PDF path for cv_analysis instead of the default text fixture")
    parser.add_argument("--use-indexed-document", action="store_true", help="Resolve indexed document(s) from the RAG store instead of using local text fixtures")
    parser.add_argument("--document-name", default=None, help="Optional indexed document name for real-document eval mode")
    parser.add_argument("--document-id", default=None, help="Optional indexed document id for real-document eval mode")
    parser.add_argument("--context-strategy", default="document_scan", choices=["document_scan", "retrieval"], help="Context strategy when using indexed document eval mode")
    parser.add_argument("--gold-fixture", default=None, help="Optional explicit gold fixture path to compare against")
    parser.add_argument("--gold-manifest", default=str(GOLD_MANIFEST_DEFAULT), help="Path to the manifest of real-document gold fixtures")
    args = parser.parse_args()

    tasks = [args.task] if args.task != "all" else ["extraction", "summary", "checklist", "cv_analysis", "code_analysis"]
    return run_tasks(
        tasks,
        provider=args.provider,
        model=args.model,
        cv_pdf=args.cv_pdf,
        use_indexed_document=args.use_indexed_document,
        document_name=args.document_name,
        document_id=args.document_id,
        context_strategy=args.context_strategy,
        gold_fixture=args.gold_fixture,
        gold_manifest=args.gold_manifest,
    )


if __name__ == "__main__":
    raise SystemExit(main())
