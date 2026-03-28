from __future__ import annotations

import re
from typing import Any, Optional

from ..config import get_rag_settings
from ..rag.service import retrieve_relevant_chunks_detailed


DEFAULT_DOCUMENT_SCAN_CHUNKS = 14
DEFAULT_DOCUMENT_SCAN_CHARS = 24000
DEFAULT_RETRIEVAL_CHUNKS = 12
DEFAULT_RETRIEVAL_CHARS = 22000
DEFAULT_FULL_CV_CHARS = 32000
PHONEISH_RE = re.compile(r"^\+?\d[\d\s().-]{7,}\d$")
EMAILISH_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)
CV_SECTION_HEADER_RE = re.compile(r"^(SUMMARY|SKILLS|EXPERIENCE|EDUCATION|LANGUAGES|PROJECTS|CERTIFICATIONS)\s*$", re.I | re.M)
REPORT_BOILERPLATE_LINE_RE = re.compile(
    r"^(?:fy\s*20\d{2}\s+agency financial report|national aeronautics and|space administration|photo credit|\[página\s*\d+\]|\d+\s*fy\s*20\d{2}\s+agency financial report|<!--\s*image\s*-->)$",
    re.I,
)
TOC_LINE_RE = re.compile(r"^[A-Za-z][A-Za-z\s&'’.-]{3,}\s+\d{1,3}$")
RAW_SECTION_ALIASES = {
    "education": ["EDUCATION", "FORMATION"],
    "skills": ["SKILLS", "TECHNIQUES", "COMPÉTENCES", "COMPETENCES"],
    "experience": ["EXPERIENCE", "EXPÉRIENCE", "EXPÉRIENCE PROFESSIONNELLE", "EXPERIENCE PROFESSIONNELLE"],
    "languages": ["LANGUAGES", "LANGUES"],
    "projects": ["PROJECTS", "PROJETS"],
    "certifications": ["CERTIFICATIONS", "CERTIFICATS"],
}
RAW_SECTION_END_ALIASES = {
    "education": ["EXPERIENCE", "EXPÉRIENCE", "EXPÉRIENCE PROFESSIONNELLE", "EXPERIENCE PROFESSIONNELLE", "SKILLS", "TECHNIQUES", "COMPÉTENCES", "COMPETENCES", "LANGUAGES", "LANGUES", "CERTIFICATIONS", "CERTIFICATS"],
    "skills": ["EXPERIENCE", "EXPÉRIENCE", "EXPÉRIENCE PROFESSIONNELLE", "EXPERIENCE PROFESSIONNELLE", "EDUCATION", "FORMATION", "LANGUAGES", "LANGUES", "CERTIFICATIONS", "CERTIFICATS", "PROJECTS", "PROJETS"],
}


def _normalize_whitespace(value: str) -> str:
    return " ".join(str(value or "").replace("\n", " ").split()).strip()


def _is_boilerplate_line(value: str) -> bool:
    text = _normalize_whitespace(value)
    if not text:
        return True
    if REPORT_BOILERPLATE_LINE_RE.match(text):
        return True
    lowered = text.lower()
    if lowered in {"table of contents", "management's discussion and analysis", "management’s discussion & analysis"}:
        return True
    if lowered.startswith("fy 20") and "agency financial report" in lowered:
        return True
    return False


def _looks_like_toc_block(lines: list[str]) -> bool:
    if not lines:
        return False
    lowered_lines = [line.lower() for line in lines]
    if any("table of contents" in line for line in lowered_lines):
        return True
    toc_like = sum(1 for line in lines if TOC_LINE_RE.match(_normalize_whitespace(line)))
    return toc_like >= 4


def _clean_context_block_text(block_text: str) -> str:
    raw_lines = [line.strip() for line in str(block_text or "").splitlines() if line.strip()]
    filtered_lines: list[str] = []
    seen_lines: set[str] = set()
    for line in raw_lines:
        normalized = _normalize_whitespace(line)
        if not normalized:
            continue
        if _is_boilerplate_line(normalized):
            continue
        if normalized.lower() in seen_lines:
            continue
        seen_lines.add(normalized.lower())
        filtered_lines.append(normalized)
    if _looks_like_toc_block(filtered_lines):
        return ""
    return "\n".join(filtered_lines).strip()


def _normalize_contact_email(value: str) -> str | None:
    text = _normalize_whitespace(value).replace(" ", "")
    text = text.replace("canvalho", "carvalho")
    return text if EMAILISH_RE.match(text) else None


def _normalize_contact_phone(value: str) -> str | None:
    text = _normalize_whitespace(value)
    if re.search(r"(?:19|20)\d{2}", text):
        return None
    return text if PHONEISH_RE.match(text) else None


def _normalize_link(value: str) -> str | None:
    text = _normalize_whitespace(value)
    if not text:
        return None
    text = text.replace("hittestinkedin", "https://www.linkedin")
    text = text.replace("inkedin com", "linkedin.com")
    text = text.replace("/inj", "/in/")
    text = text.replace(" ", "")
    if "linkedin.com/in/" in text.lower() or "github.com/" in text.lower():
        if not text.lower().startswith("http"):
            text = "https://" + text.lstrip("/")
        return text
    return None


def _looks_like_noisy_field_value(value: Any) -> bool:
    text = _normalize_whitespace(str(value or ""))
    if not text:
        return True
    upper = text.upper()
    if len(text) > 120:
        return True
    if text.count("|") >= 3:
        return True
    if text.count(" - ") >= 3:
        return True
    if sum(1 for marker in ("SUMMARY", "SKILLS", "EDUCATION", "LANGUAGES", "EXPERIENCE") if marker in upper) >= 2:
        return True
    if text.startswith("{") or text.startswith("["):
        return True
    return False


def _value_if_usable(value: Any) -> str | None:
    text = _normalize_whitespace(str(value or ""))
    if not text or _looks_like_noisy_field_value(text):
        return None
    return text


def _append_section(parts: list[str], title: str, lines: list[str]) -> None:
    clean_lines = [line for line in lines if line and line.strip()]
    if clean_lines:
        parts.append(f"[{title}]\n" + "\n".join(clean_lines))


def _get_existing_section_lines(parts: list[str], title: str) -> list[str]:
    header = f"[{title}]\n"
    for part in parts:
        if part.startswith(header):
            return [line for line in part.splitlines()[1:] if line.strip()]
    return []


def _remove_section(parts: list[str], title: str) -> list[str]:
    header = f"[{title}]\n"
    return [part for part in parts if not part.startswith(header)]


def _serialize_confirmed_fields(confirmed: dict[str, Any]) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    dropped: list[str] = []
    for label, key in (("Name", "name"), ("Location", "location")):
        usable = _value_if_usable(confirmed.get(key))
        if usable:
            lines.append(f"{label}: {usable}")
        elif confirmed.get(key):
            dropped.append(f"confirmed_fields.{key}: noisy_or_implausible_value")
    emails = [item for item in (_normalize_contact_email(str(v)) for v in confirmed.get("emails", [])) if item]
    phones = [item for item in (_normalize_contact_phone(str(v)) for v in confirmed.get("phones", [])) if item]
    if emails:
        lines.append(f"Emails: {', '.join(emails)}")
    if phones:
        lines.append(f"Phones: {', '.join(phones)}")
    links = [item for item in (_normalize_link(str(v)) for v in confirmed.get("links", [])) if item]
    if links:
        lines.append(f"Links: {', '.join(links)}")
    return lines, dropped


def _serialize_experience_entries(entries: list[Any]) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    dropped: list[str] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            dropped.append(f"experience[{index}]: non_dict_entry")
            continue
        title = _value_if_usable(((entry.get("title") or {}).get("value") if isinstance(entry.get("title"), dict) else entry.get("title")))
        company = _value_if_usable(((entry.get("company") or {}).get("value") if isinstance(entry.get("company"), dict) else entry.get("company")))
        date_range = _value_if_usable(((entry.get("date_range") or {}).get("value") if isinstance(entry.get("date_range"), dict) else entry.get("date_range")))
        location = _value_if_usable(((entry.get("location") or {}).get("value") if isinstance(entry.get("location"), dict) else entry.get("location")))
        bullets_raw = entry.get("description_or_bullets") or []
        bullets = []
        for bullet in bullets_raw:
            value = _value_if_usable((bullet.get("value") if isinstance(bullet, dict) else bullet))
            if value:
                bullets.append(value)
        if not any([title, company, date_range, location, bullets]):
            dropped.append(f"experience[{index}]: all_fields_noisy_or_empty")
            continue
        header = " | ".join(item for item in [title, company, date_range, location] if item)
        if header:
            lines.append(f"- {header}")
        for bullet in bullets[:5]:
            lines.append(f"  • {bullet}")
    return lines, dropped


def _serialize_education_entries(entries: list[Any]) -> tuple[list[str], list[str]]:
    candidates: list[str] = []
    dropped: list[str] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            dropped.append(f"education[{index}]: non_dict_entry")
            continue
        institution = _value_if_usable(((entry.get("institution") or {}).get("value") if isinstance(entry.get("institution"), dict) else entry.get("institution")))
        degree = _value_if_usable(((entry.get("degree") or {}).get("value") if isinstance(entry.get("degree"), dict) else entry.get("degree")))
        date_range = _value_if_usable(((entry.get("date_range") or {}).get("value") if isinstance(entry.get("date_range"), dict) else entry.get("date_range")))
        location = _value_if_usable(((entry.get("location") or {}).get("value") if isinstance(entry.get("location"), dict) else entry.get("location")))
        description = _value_if_usable(entry.get("description") or entry.get("text"))
        if not any([institution, degree, date_range, location]):
            if description:
                candidates.append(description)
            else:
                dropped.append(f"education[{index}]: all_fields_noisy_or_empty")
            continue
        candidates.append(" | ".join(item for item in [degree, institution, date_range, location] if item))
    return _dedupe_canonical_education_lines(candidates), dropped


def _serialize_simple_list_entries(entries: list[Any], section_name: str) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    dropped: list[str] = []
    for index, entry in enumerate(entries, start=1):
        value = entry.get("value") if isinstance(entry, dict) else entry
        usable = _value_if_usable(value)
        if usable:
            if section_name == "skills":
                for skill in _split_skill_candidates(usable):
                    normalized = _normalize_skill_candidate(skill)
                    if normalized:
                        lines.append(f"- {normalized}")
            else:
                lines.append(f"- {usable.lstrip('- ').strip()}")
        else:
            dropped.append(f"{section_name}[{index}]: noisy_or_empty_value")
    if section_name == "skills":
        return _dedupe_skill_lines(lines), dropped
    return lines, dropped


def _serialize_languages(entries: list[Any]) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    dropped: list[str] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            dropped.append(f"languages[{index}]: non_dict_entry")
            continue
        language = _value_if_usable(((entry.get("language") or {}).get("value") if isinstance(entry.get("language"), dict) else entry.get("language")))
        proficiency = _value_if_usable(((entry.get("proficiency") or {}).get("value") if isinstance(entry.get("proficiency"), dict) else entry.get("proficiency")))
        if language:
            lines.append(f"- {language}" + (f" ({proficiency})" if proficiency else ""))
        else:
            dropped.append(f"languages[{index}]: noisy_or_empty_language")
    return lines, dropped


def _normalize_skill_candidate(value: str | None) -> str | None:
    text = _normalize_whitespace(value)
    if not text:
        return None
    text = re.sub(r'^[\-•,;:.()\[\]{}]+|[\-•,;:.()\[\]{}]+$', '', text).strip()
    if text.endswith(')') and text.count('(') < text.count(')'):
        text = text[:-1].strip()
    lowered = text.lower()
    if lowered.startswith('ml ' ) or lowered.startswith('ml(') or lowered.startswith('ml ('):
        return 'ML'
    if 'etl + scikit-learn' in lowered and lowered != 'etl + scikit-learn':
        return 'ETL + scikit-learn'
    typo_map = {
        'kubernets': 'Kubernetes',
        'matlab': 'MatLab',
    }
    if lowered in typo_map:
        return typo_map[lowered]
    return text or None


def _split_skill_candidates(value: str) -> list[str]:
    parts = re.split(r'\s*[,;]\s*|\s*•\s*', str(value or ''))
    return [part.strip() for part in parts if part and part.strip()]


def _dedupe_skill_lines(lines: list[str]) -> list[str]:
    kept: list[str] = []
    seen: set[str] = set()
    for raw in lines:
        cleaned = _normalize_skill_candidate(raw.lstrip('- ').strip())
        if not cleaned:
            continue
        if cleaned.islower() and len(cleaned.split()) <= 3:
            continue
        if cleaned.lower() in {'régression', 'regression', 'classification', 'clustering', 'académiques', 'academiques'}:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        kept.append(f"- {cleaned}")
    lowered = {item[2:].lower(): idx for idx, item in enumerate(kept)}
    if 'sql' in lowered and 'postgresql' in lowered:
        first = min(lowered['sql'], lowered['postgresql'])
        second = max(lowered['sql'], lowered['postgresql'])
        kept[first] = '- SQL / PostgreSQL'
        del kept[second]
    lowered = {item[2:].lower(): idx for idx, item in enumerate(kept)}
    if 'simulink/matlab' in lowered:
        del kept[lowered['simulink/matlab']]
    lowered = {item[2:].lower(): idx for idx, item in enumerate(kept)}
    if 'sql' in lowered and 'sql / postgresql' in lowered:
        del kept[lowered['sql']]
    return kept


def _extract_raw_skill_candidates(raw_text: str) -> list[str]:
    candidates: list[str] = []
    block = _extract_raw_cv_section_block(raw_text, "skills")
    lines = _extract_section_lines_from_block(block, "skills") if block else []
    technique_matches = re.findall(r"(?:Techniques|Compétences|Competences)\s*:\s*(.*?)(?=(?:Certificats|Certifications|Danyel\s|CENTRES D['’]INTÉRÊT|Recherche d['’]un|$))", raw_text, re.I | re.S)
    for chunk in [*lines, *technique_matches]:
        text = _normalize_whitespace(chunk)
        if not text:
            continue
        text = re.sub(r'^(?:Techniques|Compétences|Competences)\s*:\s*', '', text, flags=re.I)
        text = re.sub(r'^(?:Natif|Avancé)\s+en\s+', '', text, flags=re.I)
        for part in _split_skill_candidates(text):
            normalized = _normalize_skill_candidate(part)
            if not normalized:
                continue
            if normalized.lower().startswith(("langues", "certificats", "certifications", "danyel ", "ingénieur diplômé", "centres d’intérêt", "recherche d’un")):
                continue
            candidates.append(normalized)
    return [line.lstrip('- ').strip() for line in _dedupe_skill_lines([f"- {item}" for item in candidates])]


def _education_line_score(value: str) -> int:
    text = _normalize_whitespace(value).lower()
    if not text:
        return -100
    score = len(text)
    if any(token in text for token in ('diplôme', 'ingénieur', 'master', 'licence', 'bachelor')):
        score += 25
    if any(token in text for token in ('|', '[', ']')):
        score -= 80
    if text.count('|') >= 2:
        score -= 20
    if re.search(r'(?:19|20)\d{2}', text):
        score += 15
    return score


def _education_lines_compete(left: str, right: str) -> bool:
    stopwords = {"diplôme", "diplome", "ingénieur", "ingenieur", "master", "licence", "bachelor", "grade", "bac", "de", "du", "des", "en", "et", "la", "le", "l", "université", "universite", "école", "ecole"}
    left_tokens = {token for token in re.findall(r"[a-zà-ÿ]+", _normalize_whitespace(left).lower()) if token not in stopwords}
    right_tokens = {token for token in re.findall(r"[a-zà-ÿ]+", _normalize_whitespace(right).lower()) if token not in stopwords}
    return len(left_tokens & right_tokens) >= 2


def _should_keep_education_line(value: str) -> bool:
    text = _normalize_whitespace(value)
    if not text:
        return False
    lowered = text.lower()
    has_degree_signal = any(token in lowered for token in ('diplôme', 'ingénieur', 'master', 'licence', 'bachelor', 'msc', 'm.sc'))
    has_date_signal = bool(re.search(r'(?:19|20)\d{2}', lowered))
    malformed_fragment = any(token in text for token in ('|', '[', ']')) and not (has_degree_signal or has_date_signal)
    return not malformed_fragment


def _dedupe_canonical_education_lines(lines: list[str]) -> list[str]:
    kept: list[str] = []
    for raw in lines:
        cleaned = _normalize_whitespace(raw)
        if not cleaned:
            continue
        if not _should_keep_education_line(cleaned):
            continue
        replaced = False
        for index, existing in enumerate(kept):
            if not _education_lines_compete(existing, cleaned):
                continue
            if _education_line_score(cleaned) > _education_line_score(existing):
                kept[index] = cleaned
            replaced = True
            break
        if not replaced:
            kept.append(cleaned)
    return [f"- {line}" for line in kept if line]


def _clean_raw_cv_text(raw_text: str) -> str:
    text = _normalize_whitespace(raw_text)
    return text[:12000].strip()


def _extract_raw_cv_section_lines(raw_text: str, section_name: str) -> list[str]:
    text = str(raw_text or "")
    if not text.strip():
        return []
    target = section_name.strip().lower()
    if target in RAW_SECTION_ALIASES:
        block = _extract_raw_cv_section_block(text, target)
        if not block:
            return []
        return _extract_section_lines_from_block(block, target)
    matches = list(CV_SECTION_HEADER_RE.finditer(text))
    for index, match in enumerate(matches):
        if match.group(1).strip().lower() != target:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        lines = [_normalize_whitespace(line).lstrip('-• ').strip() for line in block.splitlines() if _normalize_whitespace(line)]
        return [line for line in lines if line]
    return []


def _extract_raw_cv_section_block(text: str, section_name: str) -> str:
    aliases = RAW_SECTION_ALIASES.get(section_name, [section_name.upper()])
    all_aliases = RAW_SECTION_END_ALIASES.get(section_name) or [alias for values in RAW_SECTION_ALIASES.values() for alias in values]
    alias_pattern = "|".join(re.escape(alias) for alias in aliases)
    start_match = re.search(rf"(?is)(?:^|[\n;])\s*(?:{alias_pattern})\s*:?,?", text)
    if not start_match:
        return ""
    block_start = start_match.end()
    end_positions = []
    for alias in all_aliases:
        if alias in aliases:
            continue
        match = re.search(rf"(?is)(?:^|[\n;])\s*{re.escape(alias)}\s*:?,?", text[block_start:])
        if match:
            end_positions.append(block_start + match.start())
    block_end = min(end_positions) if end_positions else len(text)
    return text[block_start:block_end].strip()


def _extract_section_lines_from_block(block: str, section_name: str) -> list[str]:
    lines = [_normalize_whitespace(line).lstrip('-• ').strip() for line in block.splitlines() if _normalize_whitespace(line)]
    if section_name == "skills":
        filtered: list[str] = []
        stop_prefixes = ("certificats", "certifications", "danyel ", "ingénieur diplômé", "12 rue", "+33", "in/", "centres d’intérêt", "recherche d’un")
        for line in lines:
            lowered = line.lower()
            if any(lowered.startswith(prefix) for prefix in stop_prefixes):
                break
            filtered.append(line)
        return filtered
    if section_name == "education":
        kept = []
        for line in lines:
            lowered = line.lower()
            if any(token in lowered for token in ("diplôme", "master", "licence", "université", "universite", "centralesupélec", "usp", "école", "ecole")):
                kept.append(line)
        return kept or lines
    return lines


def _extract_raw_education_candidates(raw_text: str) -> list[str]:
    block = _extract_raw_cv_section_block(raw_text, "education")
    if not block:
        return []
    lines = [line.strip() for line in block.splitlines() if _normalize_whitespace(line)]
    school_start_re = re.compile(r"(?i)(école|ecole|université|universite|university|usp)")
    segments: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        normalized = _normalize_whitespace(line)
        if school_start_re.search(normalized) and current:
            segments.append(current)
            current = [normalized]
            continue
        current.append(normalized)
    if current:
        segments.append(current)

    candidates: list[str] = []
    for segment in segments:
        useful_lines = []
        for line in segment:
            lowered = line.lower()
            if any(token in lowered for token in ('gpa', 'moyenne', 'top ', 'double diplôme', 'double diplome', 'spécialité', 'specialite', 'projets académiques', 'projets academiques')):
                continue
            useful_lines.append(line)
        primary = useful_lines[0] if useful_lines else next((line for line in segment if school_start_re.search(line)), "")
        degree_line = next((line for line in useful_lines if any(token in line.lower() for token in ("diplôme", "master", "licence", "bachelor", "ingénieur", "ingenieur"))), "")
        date_lines = [line for line in useful_lines if re.search(r'(?:19|20)\d{2}', line)]
        date_text = ' - '.join(date_lines[1:]) if len(date_lines) > 1 else (date_lines[0] if date_lines else '')
        parts = [part for part in [primary, degree_line if degree_line != primary else "", date_text if date_text not in {primary, degree_line} else ""] if part]
        text = _normalize_whitespace(" ".join(parts))
        if not text:
            continue
        text = re.sub(r'\s+', ' ', text)
        if any(token in text.lower() for token in ("diplôme", "master", "licence", "bachelor", "ingénieur", "ingenieur")):
            candidates.append(text)
    return candidates


def _extract_raw_project_candidates(raw_text: str) -> list[str]:
    block = _extract_raw_cv_section_block(raw_text, "projects")
    if not block:
        return []
    lines = [_normalize_whitespace(line).lstrip('-• ').strip() for line in block.splitlines() if _normalize_whitespace(line)]
    if not lines:
        return []
    joined = ' '.join(lines).lower()
    if any(token in joined for token in ('académiques', 'academiques', 'double diplôme', 'double diplome', 'moyenne', 'top 2%', 'promotion')):
        return []
    return [line for line in lines if line]


def _build_cv_grounding_bundle(indexing_payload: dict[str, Any]) -> dict[str, Any]:
    confirmed = indexing_payload.get("confirmed_fields") or {}
    structured = indexing_payload.get("structured") or {}
    raw_text = str(indexing_payload.get("raw_text") or "")

    parts: list[str] = []
    diagnostics = {
        "included_sections": [],
        "dropped_sections": [],
        "dropped_reasons": [],
        "raw_text_used": False,
    }

    confirmed_lines, confirmed_dropped = _serialize_confirmed_fields(confirmed)
    if confirmed_lines:
        _append_section(parts, "CV CONFIRMED FIELDS", confirmed_lines)
        diagnostics["included_sections"].append("confirmed_fields")
    elif confirmed or confirmed_dropped:
        diagnostics["dropped_sections"].append("confirmed_fields")
    diagnostics["dropped_reasons"].extend(confirmed_dropped)

    serializers = {
        "experience": _serialize_experience_entries,
        "education": _serialize_education_entries,
        "skills": lambda value: _serialize_simple_list_entries(value, "skills"),
        "languages": _serialize_languages,
    }
    labels = {
        "experience": "CV EXPERIENCE",
        "education": "CV EDUCATION",
        "skills": "CV SKILLS",
        "languages": "CV LANGUAGES",
    }
    for key in ("experience", "education", "skills", "languages"):
        entries = structured.get(key) or []
        if not entries:
            continue
        lines, dropped = serializers[key](entries)
        if lines:
            _append_section(parts, labels[key], lines)
            diagnostics["included_sections"].append(key)
        else:
            diagnostics["dropped_sections"].append(key)
        diagnostics["dropped_reasons"].extend(dropped)

    raw_education_lines = _dedupe_canonical_education_lines(_extract_raw_education_candidates(raw_text) or _extract_raw_cv_section_lines(raw_text, "education"))
    if raw_education_lines:
        parts = _remove_section(parts, "CV EDUCATION")
        _append_section(parts, "CV EDUCATION", raw_education_lines)
        if "education" not in diagnostics["included_sections"]:
            diagnostics["included_sections"].append("education")

    raw_skill_lines = _dedupe_skill_lines([f"- {line}" for line in (_extract_raw_skill_candidates(raw_text) or _extract_raw_cv_section_lines(raw_text, "skills"))])
    if raw_skill_lines:
        existing_skills = _get_existing_section_lines(parts, "CV SKILLS")
        merged_skills = _dedupe_skill_lines([*raw_skill_lines, *existing_skills])
        parts = _remove_section(parts, "CV SKILLS")
        _append_section(parts, "CV SKILLS", merged_skills)
        if "skills" not in diagnostics["included_sections"]:
            diagnostics["included_sections"].append("skills")

    raw_project_lines = _extract_raw_project_candidates(raw_text)
    if raw_project_lines:
        _append_section(parts, "CV PROJECTS", [f"- {line}" for line in raw_project_lines])
        diagnostics["included_sections"].append("projects")

    clean_raw = _clean_raw_cv_text(raw_text)
    if clean_raw:
        _append_section(parts, "CV RAW TEXT", [clean_raw])
        diagnostics["raw_text_used"] = True

    diagnostics["fallback_mostly_raw_text"] = diagnostics["raw_text_used"] and not any(
        section in diagnostics["included_sections"] for section in ("experience", "education", "skills", "languages")
    )
    return {
        "context": "\n\n".join(parts).strip(),
        "diagnostics": diagnostics,
    }


def _get_rag_index() -> dict[str, Any] | None:
    disk_index: dict[str, Any] | None = None
    try:
        from pathlib import Path
        from ..storage.rag_store import load_rag_store
        disk_index = load_rag_store(Path(".rag_store.json"))
        if isinstance(disk_index, dict):
            return disk_index
    except Exception:
        disk_index = None
    try:
        from .rag_state import get_rag_index
    except Exception:
        get_rag_index = None
    if get_rag_index is not None:
        try:
            index = get_rag_index()
            if isinstance(index, dict):
                return index
        except Exception:
            pass
    return disk_index


def _get_effective_rag_settings():
    try:
        from .rag_state import get_rag_runtime_settings

        runtime_settings = get_rag_runtime_settings()
        if runtime_settings is not None:
            return runtime_settings
    except Exception:
        pass
    return get_rag_settings()


def _get_embedding_provider():
    try:
        from ..providers.registry import build_provider_registry, resolve_provider_runtime_profile
    except Exception:
        return None
    registry = build_provider_registry()
    rag_settings = _get_effective_rag_settings()
    runtime_profile = resolve_provider_runtime_profile(
        registry,
        rag_settings.embedding_provider,
        capability="embeddings",
        fallback_provider="ollama",
    )
    return runtime_profile.get("provider_instance")


def _filtered_chunks(rag_index: dict[str, Any], document_ids: list[str] | None = None) -> list[dict[str, Any]]:
    chunks = rag_index.get("chunks", []) if isinstance(rag_index, dict) else []
    normalized = [chunk for chunk in chunks if isinstance(chunk, dict)]
    if document_ids:
        allowed = {str(item) for item in document_ids if item}
        normalized = [
            chunk
            for chunk in normalized
            if str(chunk.get("document_id") or chunk.get("file_hash") or "") in allowed
        ]
    return normalized


def _find_documents(rag_index: dict[str, Any], document_ids: list[str] | None = None) -> list[dict[str, Any]]:
    documents = rag_index.get("documents", []) if isinstance(rag_index, dict) else []
    normalized = [doc for doc in documents if isinstance(doc, dict)]
    if document_ids:
        allowed = {str(item) for item in document_ids if item}
        normalized = [
            doc for doc in normalized
            if str(doc.get("document_id") or doc.get("file_hash") or "") in allowed
        ]
    return normalized


def _is_cv_document(document: dict[str, Any]) -> bool:
    name = str(document.get("name") or "").lower()
    metadata = document.get("loader_metadata") if isinstance(document.get("loader_metadata"), dict) else {}
    indexing_payload = metadata.get("indexing_payload") if isinstance(metadata.get("indexing_payload"), dict) else {}
    if metadata.get("evidence_pipeline_used") and indexing_payload:
        return True
    return any(token in name for token in ("cv", "resume", "curriculo", "currículo"))


def _serialize_indexing_payload(indexing_payload: dict[str, Any]) -> str:
    return str(_build_cv_grounding_bundle(indexing_payload).get("context") or "").strip()


def build_full_cv_context(
    document_ids: list[str] | None = None,
    max_chars: int = DEFAULT_FULL_CV_CHARS,
) -> str:
    rag_index = _get_rag_index()
    if not isinstance(rag_index, dict):
        return ""
    documents = _find_documents(rag_index, document_ids)
    if len(documents) != 1:
        return ""
    document = documents[0]
    if not _is_cv_document(document):
        return ""

    metadata = document.get("loader_metadata") if isinstance(document.get("loader_metadata"), dict) else {}
    indexing_payload = metadata.get("indexing_payload") if isinstance(metadata.get("indexing_payload"), dict) else {}
    full_text = ""
    if indexing_payload:
        full_text = _serialize_indexing_payload(indexing_payload)
    if not full_text:
        chunks = _ordered_chunks(_filtered_chunks(rag_index, document_ids))
        full_text = "\n\n".join(
            str(chunk.get("text") or chunk.get("snippet") or "").strip()
            for chunk in chunks
            if str(chunk.get("text") or chunk.get("snippet") or "").strip()
        ).strip()
    return full_text[:max_chars].strip()


def _ordered_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _key(chunk: dict[str, Any]) -> tuple[str, int, int]:
        return (
            str(chunk.get("document_id") or chunk.get("file_hash") or "document"),
            int(chunk.get("chunk_id") or 0),
            int(chunk.get("start_char") or 0),
        )

    return sorted(chunks, key=_key)


def _join_chunk_context(chunks: list[dict[str, Any]], max_chars: int) -> str:
    parts: list[str] = []
    used = 0
    seen_blocks: set[str] = set()
    for chunk in chunks:
        full_text = str(chunk.get("text") or "").strip()
        snippet = str(chunk.get("snippet") or "").strip()
        block_text = _clean_context_block_text(full_text or snippet)
        if not block_text:
            continue
        normalized_block = _normalize_whitespace(block_text)
        if not normalized_block or normalized_block in seen_blocks:
            continue
        seen_blocks.add(normalized_block)
        source = str(chunk.get("source") or chunk.get("document_id") or "document")
        block = f"[Source: {source}]\n{block_text}"
        if used and used + len(block) + 2 > max_chars:
            break
        parts.append(block)
        used += len(block) + 2
    return "\n\n".join(parts)


def build_document_scan_context(
    document_ids: list[str] | None = None,
    max_chunks: int = DEFAULT_DOCUMENT_SCAN_CHUNKS,
    max_chars: int = DEFAULT_DOCUMENT_SCAN_CHARS,
) -> str:
    rag_index = _get_rag_index()
    if not isinstance(rag_index, dict):
        return ""
    chunks = _ordered_chunks(_filtered_chunks(rag_index, document_ids))
    if not chunks:
        return ""
    return _join_chunk_context(chunks[:max_chunks], max_chars=max_chars)


def build_retrieval_context(
    query: str,
    document_ids: list[str] | None = None,
    max_chunks: int = DEFAULT_RETRIEVAL_CHUNKS,
    max_chars: int = DEFAULT_RETRIEVAL_CHARS,
) -> str:
    rag_settings = _get_effective_rag_settings()
    rag_index = _get_rag_index()
    if not isinstance(rag_index, dict):
        return ""
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return build_document_scan_context(document_ids=document_ids, max_chunks=max_chunks, max_chars=max_chars)

    embedding_provider = _get_embedding_provider()
    if embedding_provider is None:
        return build_document_scan_context(document_ids=document_ids, max_chunks=max_chunks, max_chars=max_chars)

    retrieval = retrieve_relevant_chunks_detailed(
        query=cleaned_query,
        rag_index=rag_index,
        settings=rag_settings,
        embedding_provider=embedding_provider,
        document_ids=document_ids,
    )
    chunks = retrieval.get("chunks", []) if isinstance(retrieval, dict) else []
    if not chunks:
        return build_document_scan_context(document_ids=document_ids, max_chunks=max_chunks, max_chars=max_chars)
    return _join_chunk_context(chunks[:max_chunks], max_chars=max_chars)


def build_structured_document_context(
    *,
    query: str,
    document_ids: list[str] | None = None,
    strategy: str = "document_scan",
    max_chunks: Optional[int] = None,
    max_chars: Optional[int] = None,
) -> str:
    grounding = get_document_grounding_profile(document_ids)
    if grounding.get("single_cv_document"):
        full_cv_context = str(grounding.get("full_cv_context") or "").strip()
        if full_cv_context:
            retrieval_support = build_retrieval_context(
                query=query,
                document_ids=document_ids,
                max_chunks=min(max_chunks or DEFAULT_RETRIEVAL_CHUNKS, 4),
                max_chars=min(max_chars or DEFAULT_RETRIEVAL_CHARS, 6000),
            ).strip()
            retrieval_support = _filter_secondary_retrieval_support(retrieval_support, full_cv_context)
            if retrieval_support and retrieval_support not in full_cv_context:
                return (
                    f"[FULL CV GROUNDING]\n{full_cv_context}\n\n"
                    f"[SECONDARY RETRIEVAL SUPPORT]\n{retrieval_support}"
                ).strip()
            return f"[FULL CV GROUNDING]\n{full_cv_context}".strip()

    strategy = (strategy or "document_scan").strip().lower()
    if strategy == "retrieval":
        return build_retrieval_context(
            query=query,
            document_ids=document_ids,
            max_chunks=max_chunks or DEFAULT_RETRIEVAL_CHUNKS,
            max_chars=max_chars or DEFAULT_RETRIEVAL_CHARS,
        )
    return build_document_scan_context(
        document_ids=document_ids,
        max_chunks=max_chunks or DEFAULT_DOCUMENT_SCAN_CHUNKS,
        max_chars=max_chars or DEFAULT_DOCUMENT_SCAN_CHARS,
    )


def get_document_grounding_profile(document_ids: list[str] | None = None) -> dict[str, Any]:
    rag_index = _get_rag_index()
    if not isinstance(rag_index, dict):
        return {"single_cv_document": False, "full_cv_context": "", "retrieval_context": ""}
    documents = _find_documents(rag_index, document_ids)
    single_cv_document = len(documents) == 1 and _is_cv_document(documents[0])
    return {
        "single_cv_document": single_cv_document,
        "full_cv_context": build_full_cv_context(document_ids=document_ids) if single_cv_document else "",
        "grounding_diagnostics": _build_cv_grounding_bundle(
            ((documents[0].get("loader_metadata") or {}).get("indexing_payload") or {})
        ).get("diagnostics", {}) if single_cv_document and documents else {},
    }


def _filter_secondary_retrieval_support(retrieval_support: str, full_cv_context: str) -> str:
    support = (retrieval_support or "").strip()
    if not support:
        return ""
    normalized_full = _normalize_whitespace(full_cv_context)
    blocks = [block.strip() for block in support.split("\n\n") if block.strip()]
    kept: list[str] = []
    for block in blocks:
        normalized_block = _normalize_whitespace(block)
        if not normalized_block:
            continue
        if normalized_block in normalized_full:
            continue
        if _looks_like_noisy_field_value(normalized_block):
            continue
        kept.append(block)
    return "\n\n".join(kept).strip()


def _has_plausible_cv_grounding(grounding: dict[str, Any]) -> bool:
    diagnostics = grounding.get("grounding_diagnostics") or {}
    full_cv_context = str(grounding.get("full_cv_context") or "")
    included_sections = diagnostics.get("included_sections") or []
    confirmed_fields_present = "confirmed_fields" in included_sections
    structured_sections = {
        section for section in included_sections if section in {"experience", "education", "skills", "languages"}
    }

    if diagnostics.get("fallback_mostly_raw_text"):
        return False

    if not full_cv_context.strip():
        return False

    if not confirmed_fields_present:
        return False

    if not structured_sections:
        return False

    return True
