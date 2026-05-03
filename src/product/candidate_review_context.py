from __future__ import annotations

from dataclasses import asdict, dataclass, field
import inspect
import json
import os
import re
from typing import Any


_SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "title": ("title", "role title", "job title", "position"),
    "seniority": ("seniority", "target seniority", "level", "seniority level"),
    "must_haves": (
        "must have",
        "must-have",
        "must-haves",
        "must haves",
        "must-have requirements",
        "must have requirements",
        "required",
        "requirements",
        "required skills",
        "core requirements",
        "role requirements",
        "minimum requirements",
    ),
    "nice_to_haves": (
        "nice to have",
        "nice-to-have",
        "nice to haves",
        "nice-to-have signals",
        "nice to have signals",
        "preferred",
        "preferred qualifications",
        "bonus",
    ),
    "leadership_expectations": (
        "leadership",
        "leadership expectations",
        "leadership / scope expectations",
        "leadership scope expectations",
        "ownership",
        "scope",
    ),
    "interview_focus": (
        "interview focus",
        "interview priorities",
        "assessment",
        "evaluation focus",
    ),
    "red_flags": (
        "red flags",
        "watchouts",
        "watch-outs",
        "watchout",
        "role-specific watchouts",
        "role specific watchouts",
        "role watchouts",
        "risks",
        "screen outs",
        "screen-outs",
    ),
}


@dataclass(slots=True)
class RoleBriefContext:
    title: str | None = None
    seniority: str | None = None
    must_haves: list[str] = field(default_factory=list)
    nice_to_haves: list[str] = field(default_factory=list)
    leadership_expectations: list[str] = field(default_factory=list)
    interview_focus: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    raw_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _strip_source_decorators(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\[source:[^\]]+\]", "", value, flags=re.IGNORECASE).replace('\n', ' ')).strip()


def _looks_like_document_label(value: str) -> bool:
    lowered = value.casefold()
    role_label_pattern = r"\b(jd|role brief|job description|job brief|hiring brief|position brief|job posting|scorecard|requisition)\b"
    return bool(
        re.search(r"\.(pdf|doc|docx|txt|md)$", value, flags=re.IGNORECASE)
        or (re.search(role_label_pattern, lowered) and any(token in lowered for token in ("pdf", "doc", "docx", "txt", "md")))
    )


def _clean_text(value: object) -> str | None:
    cleaned = _strip_source_decorators(str(value or ""))
    return cleaned or None


_ROLE_BRIEF_PROMPT_NOISE_PATTERNS = (
    r"^evaluate the cv\b",
    r"^keep the same candidate_review\b",
    r"^do not attribute\b",
    r"^prefer grounded evidence\b",
    r"^final instruction\b",
    r"^role title\s*:",
    r"^target seniority\s*:",
    r"^must-have requirements\s*:?",
    r"^nice-to-have signals\s*:?",
    r"^leadership / scope expectations\s*:?",
    r"^interview focus\s*:?",
    r"^role-specific watchouts\s*:?",
    r"\band interview next steps\b",
)

_ROLE_BRIEF_ADMIN_NOISE_PATTERNS = (
    r"^compensation\b",
    r"\$\s?\d",
    r"\bsalary\b",
    r"\bbase pay\b",
    r"\bbenefits\b",
    r"\btravel up to\b",
    r"^travel\s+\d",
    r"^work model\b",
    r"^full[- ]time\b",
    r"^hybrid\b",
)


def _is_role_context_noise(value: str) -> bool:
    cleaned = _strip_source_decorators(value).strip()
    if not cleaned:
        return True
    lowered = cleaned.casefold()
    if lowered in {"areas", "requirements", "responsibilities", "qualifications", "preferred qualifications"}:
        return True
    for pattern in (*_ROLE_BRIEF_PROMPT_NOISE_PATTERNS, *_ROLE_BRIEF_ADMIN_NOISE_PATTERNS):
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            return True
    return False


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    value = str(raw_text or "").strip()
    if not value:
        return None

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", value, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        value = fenced.group(1).strip()

    candidates = [value]
    first = value.find("{")
    last = value.rfind("}")
    if first >= 0 and last > first:
        candidates.append(value[first:last + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _coerce_role_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        lines = [item.strip() for item in re.split(r"\n|;|\u2022", value) if item.strip()]
        return lines
    return []


def _role_context_from_mapping(data: dict[str, Any], *, raw_text: str | None = None) -> RoleBriefContext:
    return RoleBriefContext(
        title=_clean_text(data.get("title") or data.get("role_title") or data.get("job_title")),
        seniority=_clean_text(data.get("seniority") or data.get("target_seniority") or data.get("level")),
        must_haves=_normalize_bullets(_coerce_role_list(data.get("must_haves") or data.get("required_qualifications") or data.get("requirements")), limit=8),
        nice_to_haves=_normalize_bullets(_coerce_role_list(data.get("nice_to_haves") or data.get("preferred_qualifications") or data.get("preferred_signals")), limit=8),
        leadership_expectations=_normalize_bullets(_coerce_role_list(data.get("leadership_expectations") or data.get("scope_expectations")), limit=6),
        interview_focus=_normalize_bullets(_coerce_role_list(data.get("interview_focus") or data.get("assessment_focus")), limit=6),
        red_flags=_normalize_bullets(_coerce_role_list(data.get("red_flags") or data.get("watchouts") or data.get("screen_outs")), limit=6),
        raw_text=_clean_text(raw_text),
    )


def _merge_role_context(primary: RoleBriefContext, fallback: RoleBriefContext) -> RoleBriefContext:
    return RoleBriefContext(
        title=primary.title or fallback.title,
        seniority=primary.seniority or fallback.seniority,
        must_haves=primary.must_haves or fallback.must_haves,
        nice_to_haves=primary.nice_to_haves or fallback.nice_to_haves,
        leadership_expectations=primary.leadership_expectations or fallback.leadership_expectations,
        interview_focus=primary.interview_focus or fallback.interview_focus,
        red_flags=primary.red_flags or fallback.red_flags,
        raw_text=primary.raw_text or fallback.raw_text,
    )


def _role_brief_llm_prompt(raw_text: str) -> list[dict[str, str]]:
    source = raw_text[:24000]
    system = (
        "You normalize hiring role briefs and job descriptions into strict JSON. "
        "Return only valid JSON. Do not include markdown. "
        "Do not copy prompt instructions. Do not include compensation, salary, benefits, travel, location, or work model as role requirements unless they are essential selection criteria. "
        "Prefer concise, complete hiring requirements grounded in the source text."
    )
    user = f"""
Normalize the role brief below into this exact JSON shape:

{{
  "title": string or null,
  "seniority": string or null,
  "must_haves": string[],
  "nice_to_haves": string[],
  "leadership_expectations": string[],
  "interview_focus": string[],
  "red_flags": string[]
}}

Rules:
- Use only the role brief text.
- must_haves are required qualifications/responsibilities needed to evaluate fit.
- nice_to_haves are preferred qualifications or bonus signals.
- leadership_expectations are scope/ownership/collaboration expectations.
- interview_focus are concrete interview probes.
- red_flags are candidate risk areas to validate, not prompt instructions.
- Keep each list item short but complete.
- Return empty arrays when not supported by the source.

ROLE BRIEF TEXT:
{source}
""".strip()
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def normalize_role_brief_text_with_model(
    text: str | None,
    *,
    provider: str | None = "ollama",
    model: str | None = None,
    temperature: float | None = 0.0,
    top_p: float | None = None,
    max_tokens: int | None = 1400,
    context_window: int | None = None,
) -> tuple[RoleBriefContext, dict[str, Any]]:
    """Normalize a JD/role brief with the configured chat model, falling back safely.

    This keeps Candidate Review generic across real role briefs while preserving
    deterministic fallback behavior when the model/provider is unavailable.
    """

    fallback = normalize_role_brief_text(text)
    raw_text = fallback.raw_text
    if not raw_text:
        return fallback, {"source": "empty"}

    disabled = str(os.getenv("AI_DECISION_STUDIO_ROLE_BRIEF_LLM_NORMALIZATION", "1")).strip().lower()
    if disabled in {"0", "false", "no", "off"}:
        return fallback, {"source": "heuristic_disabled"}

    try:
        from src.providers.registry import build_provider_registry, resolve_provider_runtime_profile
        from src.services.runtime_controls import resolve_runtime_fallback_provider

        registry = build_provider_registry()
        runtime = resolve_provider_runtime_profile(
            registry,
            provider,
            capability="chat",
            fallback_provider=resolve_runtime_fallback_provider("chat"),
        )
        provider_instance = runtime.get("provider_instance")
        provider_entry = runtime.get("provider_entry") if isinstance(runtime.get("provider_entry"), dict) else {}
        effective_model = str(model or provider_entry.get("default_model") or runtime.get("default_model") or "").strip()
        if provider_instance is None or not effective_model:
            return fallback, {
                "source": "heuristic_fallback",
                "reason": "chat_provider_unavailable",
                "provider_requested": provider,
                "provider_effective": runtime.get("effective_provider"),
            }

        messages = _role_brief_llm_prompt(raw_text)
        call_kwargs: dict[str, Any] = {
            "messages": messages,
            "model": effective_model,
            "temperature": 0.0 if temperature is None else float(temperature),
            "context_window": int(context_window or provider_entry.get("default_context_window") or 16384),
            "top_p": top_p,
            "max_tokens": int(max_tokens or 1400),
        }
        try:
            signature = inspect.signature(provider_instance.stream_chat_completion)
            if "think" in signature.parameters:
                call_kwargs["think"] = False
        except Exception:
            pass

        stream = provider_instance.stream_chat_completion(**call_kwargs)
        raw_output = "".join(provider_instance.iter_stream_text(stream))
        parsed = _extract_json_object(raw_output)
        if not parsed:
            return fallback, {
                "source": "heuristic_fallback",
                "reason": "model_returned_non_json",
                "provider_effective": runtime.get("effective_provider"),
                "model": effective_model,
                "raw_output_preview": raw_output[:500],
            }

        model_context = _role_context_from_mapping(parsed, raw_text=raw_text)
        merged = _merge_role_context(model_context, fallback)
        return merged, {
            "source": "model",
            "provider_effective": runtime.get("effective_provider"),
            "provider_requested": runtime.get("requested_provider"),
            "model": effective_model,
            "fallback_reason": runtime.get("fallback_reason"),
        }
    except Exception as error:
        return fallback, {
            "source": "heuristic_fallback",
            "reason": "model_normalization_error",
            "error": str(error)[:500],
            "provider_requested": provider,
            "model": model,
        }

def _normalize_bullets(values: list[object], limit: int = 8) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        # Remove only real bullet/list prefixes:
        #   "- item", "* item", "• item", "1. item", "1) item"
        # Do NOT remove requirement numbers such as "3+ years".
        raw = re.sub(r"^\s*(?:[-*\u2022]\s+|\d+[\.)]\s+)", "", str(value or "")).strip()
        cleaned = _clean_text(raw)
        if not cleaned or _is_role_context_noise(cleaned):
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
        if len(normalized) >= limit:
            break
    return normalized



def _canonical_section_name(raw_name: str) -> str | None:
    lowered = _clean_text(raw_name)
    if not lowered:
        return None
    lowered = lowered.casefold().rstrip(":")
    for canonical, aliases in _SECTION_ALIASES.items():
        if lowered == canonical:
            return canonical
        if lowered in aliases:
            return canonical
    return None


def _extract_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading_match = re.match(r"^([A-Za-z][A-Za-z\s\-/]+):\s*(.*)$", line)
        if heading_match:
            maybe_section = _canonical_section_name(heading_match.group(1))
            if maybe_section:
                current = maybe_section
                trailing = _clean_text(heading_match.group(2))
                if trailing:
                    sections.setdefault(current, []).append(trailing)
                continue

            # Unknown headings should not leak into the previous recognized
            # section. This matters for renderer-only instructions such as
            # "Final instruction:" and for future role brief headings.
            current = None
            continue

        if current is not None:
            sections.setdefault(current, []).append(line)
    return sections



def _candidate_lines(text: str) -> list[str]:
    """Return role-brief lines while recovering common headings from flattened PDF text."""
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n")

    heading_pattern = (
        r"ROLE SUMMARY|KEY RESPONSIBILITIES|RESPONSIBILITIES|QUALIFICATIONS|"
        r"REQUIRED QUALIFICATIONS|MINIMUM QUALIFICATIONS|PREFERRED QUALIFICATIONS|"
        r"NICE TO HAVE|NICE-TO-HAVE|BONUS QUALIFICATIONS|LEADERSHIP|"
        r"INTERVIEW FOCUS|RED FLAGS|WATCHOUTS|LEVEL|REPORTS TO|WORK MODEL|"
        r"COMPENSATION"
    )

    # Some indexed PDF excerpts arrive as one long line. Reinsert breaks before
    # common role-brief headings without hardcoding one document.
    raw = re.sub(rf"\s+({heading_pattern})\b", r"\n\1", raw, flags=re.IGNORECASE)

    lines: list[str] = []
    for raw_line in raw.splitlines():
        line = _clean_text(raw_line)
        if not line:
            continue
        line = re.sub(r"^\[Page\s+\d+\]\s*", "", line, flags=re.IGNORECASE).strip()
        if line:
            lines.append(line)
    return lines


def _trim_at_next_heading(value: str) -> str:
    heading_pattern = (
        r"ROLE SUMMARY|KEY RESPONSIBILITIES|RESPONSIBILITIES|QUALIFICATIONS|"
        r"REQUIRED QUALIFICATIONS|MINIMUM QUALIFICATIONS|PREFERRED QUALIFICATIONS|"
        r"NICE TO HAVE|NICE-TO-HAVE|BONUS QUALIFICATIONS|LEADERSHIP|"
        r"INTERVIEW FOCUS|RED FLAGS|WATCHOUTS|LEVEL|REPORTS TO|WORK MODEL|"
        r"COMPENSATION"
    )
    return re.split(rf"\b(?:{heading_pattern})\b", value, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -|:;,")


def _infer_title(text: str) -> str | None:
    title_patterns = [
        r"(?:role|job title|position)\s*:\s*(.+)",
        r"hiring for\s+(.+)",
        r"seeking\s+(.+)",
    ]
    for pattern in title_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            title = _clean_text(_trim_at_next_heading(match.group(1)))
            if title and not _looks_like_document_label(title):
                return title

    for line in _candidate_lines(text)[:10]:
        cleaned = _clean_text(line)
        if not cleaned:
            continue

        if re.search(r"\bjob description\b", cleaned, flags=re.IGNORECASE):
            title = re.split(r"\bjob description\b", cleaned, maxsplit=1, flags=re.IGNORECASE)[0]
            title = _clean_text(title.strip(" |:-"))
            if title and len(title) <= 140 and not _looks_like_document_label(title):
                return title

        if len(cleaned) > 160 or _looks_like_document_label(cleaned):
            continue

        lowered = cleaned.casefold()
        if any(token in lowered for token in ("engineer", "manager", "designer", "analyst", "scientist", "counsel", "specialist", "associate")):
            return cleaned.rstrip(":")

    return None


def _infer_seniority(text: str) -> str | None:
    lines = _candidate_lines(text)
    title = _infer_title(text) or ""

    for line in lines[:30]:
        match = re.search(
            r"\blevel\s*:?\s*([A-Za-z0-9 /\-]+?)(?:\s+Work model\b|\s+Reports to\b|\s+Travel\b|$)",
            line,
            flags=re.IGNORECASE,
        )
        if match:
            value = _clean_text(match.group(1))
            if value and len(value) <= 80:
                return value

    title_lower = title.casefold()
    if re.search(r"\bscientist\s+ii\b", title, flags=re.IGNORECASE):
        return "Scientist II"
    if re.search(r"\bsenior associate\b", title, flags=re.IGNORECASE):
        return "Senior Associate"
    if re.search(r"\bprincipal\b", title_lower):
        return "principal"
    if re.search(r"\bstaff\b", title_lower):
        return "staff"
    if re.search(r"\bsenior\b", title_lower):
        return "senior"
    if re.search(r"\blead\b", title_lower):
        return "lead"
    if re.search(r"\bjunior\b", title_lower):
        return "junior"

    return None


_HEADING_TO_CONTEXT_KEY: tuple[tuple[str, str], ...] = (
    ("required qualifications", "must_haves"),
    ("minimum qualifications", "must_haves"),
    ("qualifications", "must_haves"),
    ("key responsibilities", "must_haves"),
    ("responsibilities", "must_haves"),
    ("preferred qualifications", "nice_to_haves"),
    ("nice to have", "nice_to_haves"),
    ("nice-to-have", "nice_to_haves"),
    ("bonus qualifications", "nice_to_haves"),
    ("leadership", "leadership_expectations"),
    ("interview focus", "interview_focus"),
    ("red flags", "red_flags"),
    ("watchouts", "red_flags"),
)


def _heading_key(line: str) -> tuple[str | None, str]:
    lowered = line.casefold().strip(" :-")
    for heading, key in _HEADING_TO_CONTEXT_KEY:
        if lowered == heading:
            return key, ""
        if lowered.startswith(heading + " "):
            return key, line[len(heading):].strip(" :-")
        if lowered.startswith(heading + " -"):
            return key, line[len(heading):].strip(" :-")
        if lowered.startswith(heading + ":"):
            return key, line[len(heading):].strip(" :-")
    return None, line


def _split_compact_items(value: str) -> list[str]:
    value = _trim_at_next_heading(value)
    value = re.sub(r"\s+", " ", value).strip()
    if not value:
        return []

    # Preserve requirements such as "3+ years" while splitting real bullet text.
    parts = re.split(r"\s+(?:[-•]\s+|;+\s+)", value)
    cleaned = []
    for part in parts:
        item = _clean_text(part)
        if not item:
            continue
        if len(item) > 260:
            sentences = re.split(r"(?<=[.!?])\s+", item)
            item = _clean_text(sentences[0])
        if item:
            cleaned.append(item)
    return cleaned


def _extract_jd_sections(text: str) -> dict[str, list[str]]:
    extracted: dict[str, list[str]] = {
        "must_haves": [],
        "nice_to_haves": [],
        "leadership_expectations": [],
        "interview_focus": [],
        "red_flags": [],
    }

    current: str | None = None

    for line in _candidate_lines(text):
        key, trailing = _heading_key(line)
        if key:
            current = key
            if trailing:
                extracted.setdefault(current, []).extend(_split_compact_items(trailing))
            continue

        if current:
            if re.match(r"^[A-Z][A-Z /\-&]{3,}$", line):
                current = None
                continue
            extracted.setdefault(current, []).extend(_split_compact_items(line))

    # Generic interview focus fallback: use core responsibilities/requirements,
    # not document-specific hardcoding.
    if not extracted["interview_focus"]:
        focus_candidates = []
        for item in extracted["must_haves"]:
            lowered = item.casefold()
            if any(token in lowered for token in ("study", "protocol", "documentation", "test", "laboratory", "cross-functional", "quality", "regulatory", "device")):
                focus_candidates.append(item)
        extracted["interview_focus"] = focus_candidates[:4]

    # Generic leadership/scope fallback.
    if not extracted["leadership_expectations"]:
        leadership_candidates = []
        for item in extracted["must_haves"]:
            lowered = item.casefold()
            if any(token in lowered for token in ("partner", "project", "cross-functional", "stakeholder", "leader", "regulatory", "quality", "external")):
                leadership_candidates.append(item)
        extracted["leadership_expectations"] = leadership_candidates[:4]

    return extracted


def normalize_role_brief_text(text: str | None) -> RoleBriefContext:
    raw_text = _clean_text(text)
    if not raw_text:
        return RoleBriefContext(raw_text=None)

    explicit_sections = _extract_sections(text or "")
    jd_sections = _extract_jd_sections(text or "")

    context = RoleBriefContext(
        title=(lambda explicit: explicit if explicit and not _looks_like_document_label(explicit) else None)(_clean_text((explicit_sections.get("title") or [None])[0])) or _infer_title(text or ""),
        seniority=_clean_text((explicit_sections.get("seniority") or [None])[0]) or _infer_seniority(text or ""),
        must_haves=_normalize_bullets((explicit_sections.get("must_haves") or []) + (jd_sections.get("must_haves") or []), limit=8),
        nice_to_haves=_normalize_bullets((explicit_sections.get("nice_to_haves") or []) + (jd_sections.get("nice_to_haves") or []), limit=8),
        leadership_expectations=_normalize_bullets((explicit_sections.get("leadership_expectations") or []) + (jd_sections.get("leadership_expectations") or []), limit=6),
        interview_focus=_normalize_bullets((explicit_sections.get("interview_focus") or []) + (jd_sections.get("interview_focus") or []), limit=6),
        red_flags=_normalize_bullets((explicit_sections.get("red_flags") or []) + (jd_sections.get("red_flags") or []), limit=6),
        raw_text=raw_text,
    )

    if not context.must_haves:
        inferred_required = re.findall(r"(?:required|must have|needs?)\s+([^\.;\n]+)", text or "", flags=re.IGNORECASE)
        context.must_haves = _normalize_bullets(inferred_required, limit=6)

    if not context.nice_to_haves:
        inferred_preferred = re.findall(r"(?:preferred|bonus|nice to have)\s+([^\.;\n]+)", text or "", flags=re.IGNORECASE)
        context.nice_to_haves = _normalize_bullets(inferred_preferred, limit=6)

    return context




def render_candidate_review_input_text(role_context: RoleBriefContext) -> str:
    """Render a deterministic, workflow-safe input_text for candidate_review.

    The current `candidate_review` workflow already accepts `input_text`, and the
    repository contract positions it as the place to pass hiring context.
    This renderer keeps the request stable and avoids free-form prompt generation.
    """

    lines = [
        "Evaluate the CV against the normalized hiring thesis below.",
        "Keep the same candidate_review output shape: candidate fit summary, strengths, gaps, seniority signals, watchouts and interview next steps.",
        "Do not attribute role requirements to the candidate unless the CV explicitly supports them.",
        "Prefer grounded evidence from the CV over assumptions.",
    ]

    if role_context.title:
        lines.append(f"Role title: {role_context.title}")
    if role_context.seniority:
        lines.append(f"Target seniority: {role_context.seniority}")
    if role_context.must_haves:
        lines.append("Must-have requirements:")
        lines.extend(f"- {item}" for item in role_context.must_haves)
    if role_context.nice_to_haves:
        lines.append("Nice-to-have signals:")
        lines.extend(f"- {item}" for item in role_context.nice_to_haves)
    if role_context.leadership_expectations:
        lines.append("Leadership / scope expectations:")
        lines.extend(f"- {item}" for item in role_context.leadership_expectations)
    if role_context.interview_focus:
        lines.append("Interview focus:")
        lines.extend(f"- {item}" for item in role_context.interview_focus)
    if role_context.red_flags:
        lines.append("Role-specific watchouts:")
        lines.extend(f"- {item}" for item in role_context.red_flags)

    lines.append("Final instruction: preserve the existing candidate_review output style and evaluate fit specifically for this role context.")
    return "\n".join(lines).strip()


def build_candidate_review_input_text(
    *,
    raw_role_brief_text: str | None = None,
    fallback_input_text: str | None = None,
    provider: str | None = "ollama",
    model: str | None = None,
    temperature: float | None = 0.0,
    top_p: float | None = None,
    max_tokens: int | None = 1400,
    context_window: int | None = None,
) -> str | None:
    if _clean_text(raw_role_brief_text):
        role_context, _metadata = normalize_role_brief_text_with_model(
            raw_role_brief_text,
            provider=provider,
            model=model,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            context_window=context_window,
        )
        if role_context.raw_text:
            return render_candidate_review_input_text(role_context)

    if _clean_text(fallback_input_text):
        return _clean_text(fallback_input_text)

    return None
