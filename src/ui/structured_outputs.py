"""Renderers for Phase 5 structured outputs."""
from __future__ import annotations

import json
import re
from typing import Any

import streamlit as st

from ..structured.base import (
    ChecklistItem,
    ChecklistPayload,
    CVSection,
    CVAnalysisPayload,
    CodeIssue,
    CodeAnalysisPayload,
    ExtractionPayload,
    SummaryPayload,
)
from ..structured.envelope import StructuredResult


_FIELD_LABEL_OVERRIDES = {
    "agreement type": "Tipo do acordo",
    "classification": "Classificação",
    "closing date": "Data de fechamento",
    "confidentiality": "Confidencialidade",
    "consideration": "Contraprestação",
    "counterparties": "Contrapartes",
    "counterparty": "Contraparte",
    "document type": "Tipo do documento",
    "effective date": "Data de vigência",
    "effective dates": "Datas de vigência",
    "execution date": "Data de assinatura",
    "governing law": "Lei aplicável",
    "jurisdiction": "Jurisdição",
    "parties": "Partes",
    "party": "Parte",
    "payment terms": "Condições de pagamento",
    "purchase price": "Preço",
    "retention period": "Prazo de retenção",
    "share value": "Valor da participação",
    "signature date": "Data de assinatura",
    "termination date": "Data de término",
}

_CHECKLIST_LABEL_STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "to",
    "of",
    "for",
    "in",
    "on",
    "at",
    "by",
    "with",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "do",
    "does",
    "did",
    "done",
    "has",
    "have",
    "had",
    "can",
    "could",
    "should",
    "would",
    "will",
    "may",
    "might",
    "must",
    "this",
    "that",
    "these",
    "those",
    "his",
    "her",
    "their",
    "its",
    "our",
    "your",
    "my",
}

_CODE_ANALYSIS_SEVERITY_LABELS = {
    "high": "Alta",
    "medium": "Média",
    "low": "Baixa",
}

_CODE_ANALYSIS_SEVERITY_ICONS = {
    "high": "🔴",
    "medium": "🟠",
    "low": "🟡",
}

_CODE_ANALYSIS_SEVERITY_RANK = {
    "high": 0,
    "medium": 1,
    "low": 2,
}

_CODE_ANALYSIS_CATEGORY_LABELS = {
    "api_contract": "Contrato da API",
    "bug": "Bug",
    "correctness": "Correção",
    "error_handling": "Tratamento de erro",
    "input_mutation": "Mutação da entrada",
    "maintainability": "Manutenibilidade",
    "performance": "Performance",
    "readability": "Legibilidade",
    "runtime_failure": "Falha em tempo de execução",
    "shared_reference": "Referência compartilhada",
    "type_assumption": "Suposição de tipo",
    "type_validation": "Validação de tipo",
}


def _payload_to_json(payload: Any) -> dict[str, Any] | list[Any] | None:
    if payload is None:
        return None
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")
    return payload


def _normalize_checklist_text_for_compare(text: str | None) -> str:
    cleaned = " ".join(str(text or "").split()).strip()
    cleaned = cleaned.rstrip(" .!?;:-").strip()
    return cleaned.casefold()


def _checklist_description_adds_value(title: str | None, description: str | None) -> bool:
    normalized_title = _normalize_checklist_text_for_compare(title)
    normalized_description = _normalize_checklist_text_for_compare(description)
    if not normalized_description:
        return False
    if normalized_description == normalized_title:
        return False
    if normalized_title and normalized_description.startswith(normalized_title):
        suffix = normalized_description[len(normalized_title):].strip(" .!?;:-")
        if not suffix:
            return False
    return True


def _checklist_aux_text_adds_value(candidate: str | None, references: list[str | None]) -> bool:
    normalized_candidate = _normalize_checklist_text_for_compare(candidate)
    if not normalized_candidate:
        return False

    for reference in references:
        normalized_reference = _normalize_checklist_text_for_compare(reference)
        if not normalized_reference:
            continue
        if normalized_candidate == normalized_reference:
            return False
        if normalized_candidate.startswith(normalized_reference):
            suffix = normalized_candidate[len(normalized_reference):].strip(" .!?;:-")
            if not suffix:
                return False
        if normalized_reference.startswith(normalized_candidate):
            suffix = normalized_reference[len(normalized_candidate):].strip(" .!?;:-")
            if not suffix:
                return False

    return True


def _clean_text_value(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_checklist_category(value: str | None) -> str | None:
    cleaned = _clean_text_value(value).strip(":- ")
    if not cleaned:
        return None
    lowered = cleaned.lower()
    if lowered in {"general", "checklist", "phase", "procedure", "preparation"}:
        return None
    if re.match(r"^(is|are|what|how|does|do|did|has|have|had|can|could|should|would|will|may|might|must)\b", lowered):
        return None
    if "?" in cleaned or len(cleaned) > 80 or len(cleaned.split()) > 10:
        return None
    return cleaned


def _checklist_status_icon(status: str) -> str:
    return {
        "completed": "✅",
        "skipped": "⏭️",
        "pending": "⬜",
    }.get(status, "•")


def _checklist_status_label(status: str) -> str:
    return {
        "completed": "Concluído",
        "skipped": "Ignorado",
        "pending": "Pendente",
    }.get(status, status.capitalize())


def _format_checklist_scan_word(word: str) -> str:
    return word if word.isupper() or any(char.isdigit() for char in word) else word.capitalize()


def _build_checklist_scan_label(text: str | None, fallback: str | None = None) -> str:
    cleaned = _clean_text_value(text or fallback)
    if not cleaned:
        return "Item do checklist"

    question_like = cleaned.endswith("?") or bool(
        re.match(r"^(is|are|was|were|do|does|did|has|have|had|can|could|should|would|will|may|might|must)\b", cleaned.lower())
    )
    core = cleaned.rstrip(" ?!.;:")
    if not question_like and len(core.split()) <= 9 and len(core) <= 72:
        return core

    words = re.findall(r"[A-Za-zÀ-ÿ0-9/%+-]+(?:/[A-Za-zÀ-ÿ0-9%+-]+)?", core)
    filtered_words = [word for word in words if word.lower() not in _CHECKLIST_LABEL_STOPWORDS]
    chosen_words = filtered_words[:7] if len(filtered_words) >= 2 else words[:7]
    label = " ".join(_format_checklist_scan_word(word) for word in chosen_words).strip()
    if not label:
        label = core
    if len(label) > 64:
        label = _truncate_text(label, max_chars=64)
    return label


def _group_checklist_items(payload: ChecklistPayload) -> list[tuple[str, list[ChecklistItem]]]:
    ordered_titles: list[str] = []
    grouped: dict[str, list[ChecklistItem]] = {}
    fallback_title = "Sem fase explícita"
    last_valid_title: str | None = None

    for item in payload.items:
        normalized_category = _normalize_checklist_category(item.category)
        if normalized_category and last_valid_title:
            lowered_current = normalized_category.casefold()
            lowered_previous = last_valid_title.casefold()
            if lowered_previous.endswith(lowered_current) or lowered_current in lowered_previous:
                normalized_category = last_valid_title

        title = normalized_category or fallback_title
        if normalized_category:
            last_valid_title = normalized_category

        if title not in grouped:
            grouped[title] = []
            ordered_titles.append(title)
        grouped[title].append(item)

    return [(title, grouped[title]) for title in ordered_titles]


def _count_checklist_statuses(items: list[ChecklistItem]) -> dict[str, int]:
    counts = {"pending": 0, "completed": 0, "skipped": 0}
    for item in items:
        counts[item.status] = counts.get(item.status, 0) + 1
    return counts


def _extract_checklist_badges(item: ChecklistItem, *, section_title: str | None = None) -> list[str]:
    badges: list[str] = []
    section_category = _normalize_checklist_category(section_title)
    item_category = _normalize_checklist_category(item.category)
    if item_category and item_category != section_category:
        badges.append(item_category)

    for candidate_text in (item.source_text, item.evidence):
        cleaned = _clean_text_value(candidate_text)
        if not cleaned:
            continue

        if ":" in cleaned:
            prefix = _clean_text_value(cleaned.split(":", 1)[0])
            normalized_prefix = _normalize_checklist_category(prefix)
            if normalized_prefix and normalized_prefix != section_category:
                badges.append(normalized_prefix)

        for match in re.findall(r"\(([^)]+)\)", cleaned):
            candidate = _normalize_checklist_category(match)
            if candidate and candidate != section_category:
                badges.append(candidate)

    return _unique_preserve_order(badges)


def _render_checklist_phase_progress(grouped_items: list[tuple[str, list[ChecklistItem]]]) -> None:
    if len(grouped_items) <= 1:
        return

    st.subheader("Progresso por fase")
    columns_count = min(3, len(grouped_items))
    cols = st.columns(columns_count)

    for index, (title, items) in enumerate(grouped_items):
        counts = _count_checklist_statuses(items)
        total = len(items)
        completed = counts.get("completed", 0)
        skipped = counts.get("skipped", 0)
        progress = (completed / total) if total else 0.0
        with cols[index % columns_count]:
            with st.container(border=True):
                st.caption(title)
                st.markdown(f"**{completed}/{total} concluídos**")
                st.progress(progress)
                meta_parts: list[str] = []
                if counts.get("pending", 0):
                    meta_parts.append(f"{counts['pending']} pendentes")
                if skipped:
                    meta_parts.append(f"{skipped} ignorados")
                if meta_parts:
                    st.caption(" · ".join(meta_parts))


def _render_checklist_item_card(
    item: ChecklistItem,
    *,
    index: int,
    section_title: str | None = None,
    interactive: bool = False,
    execution_id: str | None = None,
) -> None:
    display_title = _build_checklist_scan_label(item.title, fallback=item.source_text or item.description)
    full_title_adds_value = _checklist_aux_text_adds_value(item.title, [display_title])
    description_adds_value = _checklist_aux_text_adds_value(item.description, [display_title, item.title])
    source_adds_value = _checklist_aux_text_adds_value(item.source_text, [display_title, item.title, item.description])
    evidence_adds_value = _checklist_aux_text_adds_value(item.evidence, [display_title, item.title, item.description, item.source_text])

    badges = _extract_checklist_badges(item, section_title=section_title)
    current_status = item.status
    if interactive and execution_id:
        state_key = _checklist_item_state_key(execution_id, item.id)
        is_checked = st.checkbox(
            f"{index}. {display_title}",
            key=state_key,
            value=item.status == "completed",
        )
        current_status = "completed" if is_checked else ("skipped" if item.status == "skipped" else "pending")

    meta_parts = [_checklist_status_label(current_status)]
    if _clean_text_value(item.priority):
        meta_parts.append(f"prioridade {item.priority}")
    if item.estimated_time_minutes is not None:
        meta_parts.append(f"{item.estimated_time_minutes} min")

    details_available = any(
        [
            full_title_adds_value,
            description_adds_value,
            source_adds_value,
            evidence_adds_value,
            bool(item.dependencies),
        ]
    )

    with st.container(border=True):
        if not interactive:
            st.markdown(f"{_checklist_status_icon(current_status)} **{index}. {display_title}**")
        if badges:
            st.caption(" ".join(f"[{badge}]" for badge in badges))
        if meta_parts:
            st.caption(" · ".join(meta_parts))

        if details_available:
            with st.expander("Ver detalhes", expanded=False):
                if full_title_adds_value and item.title:
                    st.caption("Pergunta / texto completo")
                    st.write(item.title)
                if description_adds_value and item.description:
                    st.caption("Descrição")
                    st.write(item.description)
                if source_adds_value and item.source_text:
                    st.caption("Trecho do documento")
                    st.write(item.source_text)
                if evidence_adds_value and item.evidence:
                    st.caption("Evidência")
                    st.write(item.evidence)
                if item.dependencies:
                    st.caption("Dependências")
                    st.write(", ".join(item.dependencies))


def _build_checklist_debug_table(payload: ChecklistPayload) -> list[dict[str, Any]]:
    return [
        {
            "label": _build_checklist_scan_label(item.title, fallback=item.source_text or item.description),
            "title": item.title,
            "category": item.category,
            "status": item.status,
            "priority": item.priority,
            "evidence": item.evidence,
        }
        for item in payload.items
    ]


def _checklist_state_prefix(execution_id: str | None) -> str | None:
    if not execution_id:
        return None
    safe_execution_id = re.sub(r"[^0-9A-Za-z_-]+", "_", execution_id)
    return f"structured_checklist_{safe_execution_id}"


def _checklist_item_state_key(execution_id: str, item_id: str) -> str:
    safe_item_id = re.sub(r"[^0-9A-Za-z_-]+", "_", item_id)
    return f"{_checklist_state_prefix(execution_id)}_{safe_item_id}"


def _reset_checklist_state(payload: ChecklistPayload, execution_id: str) -> None:
    for item in payload.items:
        st.session_state.pop(_checklist_item_state_key(execution_id, item.id), None)


def _build_checklist_payload_from_state(payload: ChecklistPayload, execution_id: str | None) -> ChecklistPayload:
    if not execution_id:
        return payload

    for item in payload.items:
        state_key = _checklist_item_state_key(execution_id, item.id)
        if state_key not in st.session_state:
            st.session_state[state_key] = item.status == "completed"

    updated_items: list[ChecklistItem] = []
    completed_items = 0
    total_items = len(payload.items)
    for item in payload.items:
        is_completed = bool(st.session_state.get(_checklist_item_state_key(execution_id, item.id), False))
        if is_completed:
            status = "completed"
            completed_items += 1
        elif item.status == "skipped":
            status = "skipped"
        else:
            status = "pending"
        updated_items.append(item.model_copy(update={"status": status}))

    progress_percentage = round((completed_items / total_items) * 100.0, 1) if total_items else 0.0
    return payload.model_copy(
        update={
            "items": updated_items,
            "completed_items": completed_items,
            "total_items": total_items,
            "progress_percentage": progress_percentage,
        }
    )


def _render_checklist_content(
    payload: ChecklistPayload,
    *,
    show_debug_table: bool = False,
    interactive: bool = False,
    execution_id: str | None = None,
) -> ChecklistPayload:
    rendered_payload = _build_checklist_payload_from_state(payload, execution_id) if interactive else payload
    grouped_items = _group_checklist_items(rendered_payload)
    counts = _count_checklist_statuses(rendered_payload.items)
    completed_groups = sum(
        1
        for _, items in grouped_items
        if items and _count_checklist_statuses(items).get("completed", 0) == len(items)
    )

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Itens", rendered_payload.total_items)
    metric_2.metric("Concluídos", counts.get("completed", rendered_payload.completed_items))
    metric_3.metric("Progresso", f"{rendered_payload.progress_percentage:.0f}%")
    metric_4.metric("Etapas", f"{completed_groups}/{len(grouped_items)}")

    if counts.get("skipped", 0):
        st.caption(f"Itens ignorados: {counts['skipped']}")

    st.progress(min(max(rendered_payload.progress_percentage / 100.0, 0.0), 1.0))
    st.write(f"**{rendered_payload.title}**")
    st.caption(rendered_payload.description)

    if interactive and execution_id:
        prefix = _checklist_state_prefix(execution_id)
        action_col, info_col = st.columns([0.35, 0.65])
        with action_col:
            if st.button("Resetar checklist", key=f"{prefix}_reset"):
                _reset_checklist_state(payload, execution_id)
                st.rerun()
        with info_col:
            st.caption("As marcações ficam salvas localmente na sessão atual da página.")

    _render_checklist_phase_progress(grouped_items)

    running_index = 1
    for section_title, items in grouped_items:
        if len(grouped_items) > 1:
            section_counts = _count_checklist_statuses(items)
            section_completed = section_counts.get("completed", 0)
            st.subheader(section_title)
            st.caption(f"{section_completed}/{len(items)} concluídos")

        for item in items:
            _render_checklist_item_card(
                item,
                index=running_index,
                section_title=section_title,
                interactive=interactive,
                execution_id=execution_id,
            )
            running_index += 1

    if show_debug_table and rendered_payload.items:
        with st.expander("Ver tabela bruta do checklist", expanded=False):
            st.dataframe(_build_checklist_debug_table(rendered_payload), width="stretch")

    return rendered_payload


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = _clean_text_value(value)
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _humanize_field_name(name: str | None) -> str:
    cleaned = _clean_text_value(name).replace("_", " ")
    override = _FIELD_LABEL_OVERRIDES.get(cleaned.casefold())
    if override:
        return override
    return cleaned.capitalize() if cleaned else "Campo"


def _filter_legal_key_facts_for_display(key_facts: list[dict[str, str]]) -> list[dict[str, str]]:
    hidden_tokens = (
        "document type",
        "agreement type",
        "classification",
        "counterparty",
        "counterparties",
        "party",
        "parties",
        "law",
        "jurisdiction",
    )
    filtered: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for fact in key_facts:
        label = _clean_text_value(fact.get("label")).lower()
        if any(token in label for token in hidden_tokens):
            continue
        value = _clean_text_value(fact.get("value"))
        key = (label, value.casefold())
        if key in seen:
            continue
        seen.add(key)
        filtered.append(fact)
    return filtered


def _should_explain_full_document_match(metadata: dict[str, Any]) -> bool:
    full_chars = metadata.get("full_document_chars")
    context_chars = metadata.get("context_chars_sent")
    return (
        isinstance(full_chars, int)
        and isinstance(context_chars, int)
        and full_chars > 0
        and full_chars == context_chars
    )


def _looks_like_legal_text(text: str | None) -> bool:
    lowered = _clean_text_value(text).lower()
    keywords = [
        "agreement",
        "contract",
        "exhibit",
        "policy",
        "legal",
        "compliance",
        "settlement",
        "separation",
        "confidentiality",
        "indemn",
        "obligation",
    ]
    return any(keyword in lowered for keyword in keywords)


def _is_legal_extraction(payload: ExtractionPayload) -> bool:
    haystacks = [payload.main_subject, *payload.categories]
    haystacks.extend(field.name for field in payload.extracted_fields)
    return any(_looks_like_legal_text(item) for item in haystacks)


def _build_extraction_parties(payload: ExtractionPayload) -> list[str]:
    organizations = [
        entity.value
        for entity in payload.entities
        if _clean_text_value(entity.type).lower() == "organization"
    ]
    if organizations:
        return _unique_preserve_order(organizations)

    field_parties: list[str] = []
    for field in payload.extracted_fields:
        field_name = _clean_text_value(field.name).lower()
        if not any(token in field_name for token in ("party", "parties", "counterparty", "counterparties")):
            continue
        raw_value = _clean_text_value(field.value)
        if not raw_value:
            continue
        field_parties.extend(part.strip() for part in raw_value.split(";") if part.strip())
    if field_parties:
        return _unique_preserve_order(field_parties)

    return _unique_preserve_order([entity.value for entity in payload.entities])


def _build_extraction_dates(payload: ExtractionPayload) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[str] = set()

    for field in payload.extracted_fields:
        if "date" not in _clean_text_value(field.name).lower():
            continue
        value = _clean_text_value(field.value)
        if not value or value.casefold() in seen:
            continue
        seen.add(value.casefold())
        items.append(
            {
                "label": _humanize_field_name(field.name),
                "value": value,
                "evidence": _clean_text_value(field.evidence),
            }
        )

    for item in _unique_preserve_order(payload.important_dates):
        if item.casefold() in seen:
            continue
        seen.add(item.casefold())
        items.append({"label": "Data citada", "value": item, "evidence": ""})

    return items


def _build_extraction_key_facts(payload: ExtractionPayload) -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []
    for field in payload.extracted_fields:
        if "date" in _clean_text_value(field.name).lower():
            continue
        value = _clean_text_value(field.value)
        if not value:
            continue
        facts.append(
            {
                "label": _humanize_field_name(field.name),
                "value": value,
                "evidence": _clean_text_value(field.evidence),
            }
        )
    return facts


def _field_name_matches(name: str | None, tokens: tuple[str, ...]) -> bool:
    lowered = _clean_text_value(name).lower()
    return any(token in lowered for token in tokens)


def _pick_document_type(payload: ExtractionPayload) -> str | None:
    for field in payload.extracted_fields:
        if _field_name_matches(field.name, ("document_type", "agreement_type", "classification")):
            value = _clean_text_value(field.value)
            if value:
                return value

    categories = _unique_preserve_order(payload.categories)
    for category in categories:
        lowered = category.lower()
        if any(keyword in lowered for keyword in ("agreement", "contract", "policy", "exhibit", "legal", "settlement")):
            return category

    return categories[0] if categories else None


def _pick_primary_date_item(dates: list[dict[str, str]]) -> dict[str, str] | None:
    if not dates:
        return None

    priority_tokens = (
        "effective",
        "agreement",
        "execution",
        "signature",
        "signing",
        "closing",
        "termination",
    )
    for item in dates:
        label = _clean_text_value(item.get("label")).lower()
        if any(token in label for token in priority_tokens):
            return item
    return dates[0]


def _find_fact_by_tokens(facts: list[dict[str, str]], tokens: tuple[str, ...]) -> dict[str, str] | None:
    for fact in facts:
        if _field_name_matches(fact.get("label"), tokens):
            return fact
    return None


def _build_legal_overview_items(
    payload: ExtractionPayload,
    parties: list[str],
    dates: list[dict[str, str]],
    key_facts: list[dict[str, str]],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []

    document_type = _pick_document_type(payload)
    if document_type:
        items.append({"label": "Tipo do documento", "value": document_type, "evidence": ""})

    if parties:
        parties_value = ", ".join(parties[:3])
        if len(parties) > 3:
            parties_value += " e outras partes"
        items.append({"label": "Partes", "value": parties_value, "evidence": ""})

    primary_date = _pick_primary_date_item(dates)
    if primary_date:
        items.append(
            {
                "label": "Data principal", 
                "value": primary_date.get("value", ""),
                "evidence": primary_date.get("evidence", ""),
            }
        )

    law_fact = _find_fact_by_tokens(key_facts, ("law", "jurisdiction"))
    if law_fact:
        items.append(
            {
                "label": "Lei aplicável / jurisdição",
                "value": law_fact.get("value", ""),
                "evidence": law_fact.get("evidence", ""),
            }
        )

    return items


def _build_legal_summary_sentence(
    payload: ExtractionPayload,
    parties: list[str],
    dates: list[dict[str, str]],
) -> str | None:
    document_type = _pick_document_type(payload)
    primary_date = _pick_primary_date_item(dates)
    parts: list[str] = []

    if document_type:
        parts.append(f"Documento identificado como {document_type}")

    if parties:
        if len(parties) == 1:
            parts.append(f"com foco na parte {parties[0]}")
        elif len(parties) == 2:
            parts.append(f"entre {parties[0]} e {parties[1]}")
        else:
            parts.append(f"entre {', '.join(parties[:2])} e outras partes")

    if primary_date and primary_date.get("value"):
        parts.append(f"com data principal em {primary_date['value']}")

    if not parts:
        return None

    return " ".join(parts) + "."


def _split_legal_facts(key_facts: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    highlight_tokens = (
        "law",
        "jurisdiction",
        "confidentiality",
        "survival",
        "termination",
        "restriction",
        "retention",
        "governance",
    )
    value_tokens = (
        "amount",
        "price",
        "payment",
        "consideration",
        "share",
        "stock",
        "number",
        "percent",
        "percentage",
        "value",
    )

    highlights: list[dict[str, str]] = []
    values: list[dict[str, str]] = []
    others: list[dict[str, str]] = []

    for fact in key_facts:
        label = _clean_text_value(fact.get("label")).lower()
        if any(token in label for token in value_tokens):
            values.append(fact)
        elif any(token in label for token in highlight_tokens):
            highlights.append(fact)
        else:
            others.append(fact)

    return highlights, values, others


def _looks_like_timebound_action(item: dict[str, str]) -> bool:
    due_date = _clean_text_value(item.get("due_date")).lower()
    status = _clean_text_value(item.get("status")).lower()
    description = _clean_text_value(item.get("description")).lower()
    if due_date and due_date not in {"ongoing", "continuous"}:
        return True
    if status in {"pending", "scheduled", "completed", "due"}:
        return True
    return any(token in f"{description} {due_date}" for token in ("within", "thereafter", "concurrently", "before", "after", "immediately", "365"))


def _split_action_groups(grouped_actions: dict[str, list[dict[str, str]]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    immediate: list[dict[str, str]] = []
    ongoing: list[dict[str, str]] = []
    for owner, items in grouped_actions.items():
        for item in items:
            enriched = {"owner": owner, **item}
            if _looks_like_timebound_action(enriched):
                immediate.append(enriched)
            else:
                ongoing.append(enriched)
    return immediate, ongoing


def _render_stat_cards(items: list[dict[str, str]], columns_count: int = 2) -> None:
    if not items:
        return
    cols = st.columns(columns_count)
    for index, item in enumerate(items):
        with cols[index % columns_count]:
            with st.container(border=True):
                st.caption(item["label"])
                st.markdown(f"**{item['value']}**")
                if item.get("evidence"):
                    st.caption(f"Base no texto: {item['evidence']}")


def _render_bullet_cards(
    items: list[dict[str, str]],
    primary_key: str,
    secondary_keys: list[tuple[str, str]],
    evidence_label: str = "Trecho do documento",
    columns_count: int = 2,
) -> None:
    if not items:
        return
    cols = st.columns(columns_count)
    for index, item in enumerate(items):
        with cols[index % columns_count]:
            with st.container(border=True):
                st.write(f"**{item.get(primary_key, '').strip() or '—'}**")
                meta_parts: list[str] = []
                for key, label in secondary_keys:
                    value = _clean_text_value(item.get(key))
                    if value:
                        meta_parts.append(f"{label}: {value}")
                if meta_parts:
                    st.caption(" · ".join(meta_parts))
                if item.get("evidence"):
                    st.caption(f"{evidence_label}: {item['evidence']}")


def _render_simple_list_card(title: str, values: list[str], icon: str = "•") -> None:
    if not values:
        return
    with st.container(border=True):
        st.caption(title)
        for value in values:
            st.write(f"{icon} {value}")


def _truncate_text(text: str | None, *, max_chars: int = 170) -> str:
    cleaned = _clean_text_value(text)
    if len(cleaned) <= max_chars:
        return cleaned
    truncated = cleaned[:max_chars].rsplit(" ", 1)[0].strip()
    if not truncated:
        truncated = cleaned[:max_chars].strip()
    return f"{truncated}…"


def _build_compact_evidence_preview(
    evidence_items: list[str],
    *,
    limit: int = 3,
    max_chars: int = 170,
) -> tuple[list[str], bool, list[str]]:
    cleaned = _unique_preserve_order(evidence_items)
    preview: list[str] = []
    has_hidden_content = len(cleaned) > limit
    for item in cleaned[:limit]:
        compact = _truncate_text(item, max_chars=max_chars)
        if compact != item:
            has_hidden_content = True
        preview.append(compact)
    return preview, has_hidden_content, cleaned


def _render_summary_insight_cards(insights: list[str]) -> None:
    cleaned = _unique_preserve_order(insights)
    if not cleaned:
        return
    columns_count = min(3, max(1, len(cleaned)))
    cols = st.columns(columns_count)
    for index, insight in enumerate(cleaned):
        with cols[index % columns_count]:
            with st.container(border=True):
                st.caption(f"Insight {index + 1}")
                st.write(insight)


def _render_summary_supporting_evidence(evidence_items: list[str]) -> None:
    preview, has_hidden_content, full_items = _build_compact_evidence_preview(evidence_items)
    if not preview:
        return
    st.caption("Trechos-base")
    for item in preview:
        st.write(f"• {item}")
    if has_hidden_content:
        with st.expander("Ver evidências completas", expanded=False):
            for item in full_items:
                st.write(f"- {item}")


def _humanize_code_issue_category(category: str | None) -> str:
    cleaned = _clean_text_value(category).replace("_", " ")
    if not cleaned:
        return "Categoria não informada"
    override = _CODE_ANALYSIS_CATEGORY_LABELS.get(cleaned.casefold().replace(" ", "_"))
    if override:
        return override
    return cleaned.capitalize()


def _code_issue_severity_label(severity: str | None) -> str:
    cleaned = _clean_text_value(severity).lower()
    if not cleaned:
        return "Nível não informado"
    return _CODE_ANALYSIS_SEVERITY_LABELS.get(cleaned, cleaned.capitalize())


def _code_issue_severity_icon(severity: str | None) -> str:
    cleaned = _clean_text_value(severity).lower()
    return _CODE_ANALYSIS_SEVERITY_ICONS.get(cleaned, "•")


def _sort_code_issues(issues: list[CodeIssue]) -> list[CodeIssue]:
    return sorted(
        issues,
        key=lambda issue: (
            _CODE_ANALYSIS_SEVERITY_RANK.get(_clean_text_value(issue.severity).lower(), 99),
            _humanize_code_issue_category(issue.category).casefold(),
            _clean_text_value(issue.title).casefold(),
        ),
    )


def _render_code_issue_card(issue: CodeIssue, *, expanded: bool = False) -> None:
    severity = _clean_text_value(issue.severity).lower()
    severity_label = _code_issue_severity_label(severity)
    severity_icon = _code_issue_severity_icon(severity)
    category_label = _humanize_code_issue_category(issue.category)

    with st.expander(
        f"{severity_icon} {severity_label} · {category_label} · {issue.title}",
        expanded=expanded,
    ):
        st.write(issue.description)
        if issue.evidence:
            st.caption("Trecho que motivou o achado")
            st.code(issue.evidence, language="text")
        if issue.recommendation:
            st.caption("Ação sugerida")
            st.write(issue.recommendation)


def _render_legal_hero(payload: ExtractionPayload, parties: list[str], dates: list[dict[str, str]]) -> None:
    summary_sentence = _build_legal_summary_sentence(payload, parties, dates)
    with st.container(border=True):
        st.caption("Visão geral rápida")
        if summary_sentence:
            st.markdown(f"#### {summary_sentence}")
        elif payload.main_subject:
            st.markdown(f"#### {payload.main_subject}")
        else:
            st.markdown("#### Documento jurídico identificado")

        if payload.main_subject and summary_sentence and payload.main_subject != summary_sentence.rstrip("."):
            st.caption(payload.main_subject)


def _render_legal_parties(parties: list[str]) -> None:
    if not parties:
        return
    st.subheader("Quem está envolvido")
    _render_simple_list_card("Partes principais", parties, icon="-" )


def _render_legal_dates(dates: list[dict[str, str]]) -> None:
    if not dates:
        return
    st.subheader("Datas e prazos")
    timeline_items = [
        {
            "description": f"{item['label']}: {item['value']}",
            "status": "",
            "due_date": "",
            "owner": "",
            "evidence": item.get("evidence", ""),
        }
        for item in dates
    ]
    _render_bullet_cards(timeline_items, "description", [], columns_count=1)


def _render_legal_values(value_facts: list[dict[str, str]], important_numbers: list[str]) -> None:
    if not value_facts and not important_numbers:
        return
    st.subheader("Valores e números relevantes")
    if value_facts:
        _render_stat_cards(value_facts, columns_count=2)
    remaining_numbers = _unique_preserve_order(important_numbers)
    if remaining_numbers:
        _render_simple_list_card("Outros números citados", remaining_numbers)


def _render_legal_missing_information(items: list[str]) -> None:
    if not items:
        return
    st.subheader("O que não ficou claro")
    _render_simple_list_card("Pontos pendentes ou ambíguos", items, icon="-" )


def _group_extraction_actions(payload: ExtractionPayload) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for item in payload.action_items:
        owner = _clean_text_value(item.owner) or "Parte não identificada"
        grouped.setdefault(owner, []).append(
            {
                "description": _clean_text_value(item.description),
                "due_date": _clean_text_value(item.due_date),
                "status": _clean_text_value(item.status),
                "evidence": _clean_text_value(item.evidence),
            }
        )
    return grouped


def _collect_extraction_evidence(payload: ExtractionPayload) -> list[dict[str, str]]:
    evidence_items: list[dict[str, str]] = []
    seen: set[str] = set()

    def _push(label: str, text: str | None) -> None:
        cleaned = _clean_text_value(text)
        if not cleaned:
            return
        key = cleaned.casefold()
        if key in seen:
            return
        seen.add(key)
        evidence_items.append({"label": label, "text": cleaned})

    for field in payload.extracted_fields:
        _push(_humanize_field_name(field.name), field.evidence)
    for item in payload.action_items:
        _push("Obrigação / ação", item.evidence)
    for item in payload.risks:
        _push("Risco / atenção", item.evidence)
    for item in payload.relationships:
        _push("Relação", item.evidence)

    return evidence_items


def _render_result_header(result: StructuredResult) -> None:
    status_label = "Validado" if result.success else "Falhou"
    status_kind = "success" if result.success else "error"
    context_label = "com contexto do documento" if result.context_used else "sem contexto do documento"
    repair_label = "com reparo automático" if result.repair_applied else "sem reparo"
    st.caption(
        f"Tarefa: `{result.task_type}` · Execução: `{result.execution_id[:8]}` · {status_label} · {context_label} · {repair_label}"
    )

    if status_kind == "success":
        st.success("Saída estruturada gerada e validada.")
        if result.quality_score is not None and result.quality_score < 0.65:
            st.warning(
                f"Este payload passou na validação estrutural, mas a qualidade estimada é baixa ({result.quality_score:.0%}). Revise grounding e possíveis placeholders antes de confiar no resultado."
            )
    else:
        error_message = result.validation_error or result.parsing_error or (result.error.message if result.error else "Unknown error")
        st.error(error_message)

    metadata = result.execution_metadata if isinstance(result.execution_metadata, dict) else {}
    execution_strategy = _clean_text_value(metadata.get("execution_strategy_used") or metadata.get("execution_strategy_requested"))
    workflow_id = _clean_text_value(metadata.get("workflow_id"))
    workflow_route_decision = _clean_text_value(metadata.get("workflow_route_decision"))
    workflow_guardrail_decision = _clean_text_value(metadata.get("workflow_guardrail_decision"))
    workflow_trace = metadata.get("workflow_trace") if isinstance(metadata.get("workflow_trace"), list) else []
    execution_shadow_summary = metadata.get("execution_shadow_summary") if isinstance(metadata.get("execution_shadow_summary"), dict) else {}
    needs_review = bool(metadata.get("needs_review"))
    needs_review_reason = _clean_text_value(metadata.get("needs_review_reason"))

    if execution_strategy:
        extra_parts = [f"estratégia `{execution_strategy}`"]
        if workflow_id:
            extra_parts.append(f"workflow `{workflow_id}`")
        st.caption("Execução estruturada: " + " · ".join(extra_parts))
    if workflow_route_decision or workflow_guardrail_decision:
        details = []
        if workflow_route_decision:
            details.append(f"route={workflow_route_decision}")
        if workflow_guardrail_decision:
            details.append(f"guardrail={workflow_guardrail_decision}")
        st.caption("Workflow: " + " · ".join(details))
    if needs_review:
        st.warning(
            "Resultado marcado para revisão humana"
            + (f" · motivo: {needs_review_reason}" if needs_review_reason else "")
        )

    telemetry = metadata.get("telemetry") if isinstance(metadata.get("telemetry"), dict) else {}
    parse_recovery = telemetry.get("parse_recovery") if isinstance(telemetry.get("parse_recovery"), dict) else {}
    if parse_recovery.get("used"):
        attempt_count = parse_recovery.get("attempt_count")
        strategies = parse_recovery.get("strategies") if isinstance(parse_recovery.get("strategies"), list) else []
        strategy_label = ", ".join(str(item) for item in strategies if item)
        if parse_recovery.get("final_success"):
            st.info(
                "Auto-recovery estruturado aplicado"
                + (f" · tentativas={attempt_count}" if attempt_count is not None else "")
                + (f" · estratégias={strategy_label}" if strategy_label else "")
            )
        else:
            st.warning(
                "Auto-recovery estruturado tentou corrigir a saída, mas ainda falhou"
                + (f" · tentativas={attempt_count}" if attempt_count is not None else "")
                + (f" · estratégias={strategy_label}" if strategy_label else "")
            )

    if result.task_type in {"summary", "checklist", "extraction"} and metadata:
        summary_mode = metadata.get("summary_mode")
        checklist_mode = metadata.get("checklist_mode")
        extraction_mode = metadata.get("extraction_mode")

        if summary_mode == "full_document_map_reduce":
            st.info(
                "Modo de resumo: map-reduce com documento completo · o modelo recebeu o documento inteiro em várias partes e depois consolidou uma síntese final."
            )
            cols = st.columns(3)
            cols[0].metric("Tamanho do documento", metadata.get("full_document_chars", 0))
            cols[1].metric("Partes", metadata.get("document_parts", 0))
            cols[2].metric("Resumos parciais", metadata.get("partial_summaries_generated", 0))
        elif summary_mode == "single_pass_context":
            st.info("Modo de resumo: contexto em passo único · o modelo resumiu usando apenas o contexto recortado desta estratégia.")
            cols = st.columns(3)
            cols[0].metric("Tamanho do documento", metadata.get("full_document_chars", 0))
            cols[1].metric("Chars do contexto enviados", metadata.get("context_chars_sent", 0))
            cols[2].metric("Estratégia", str(metadata.get("context_strategy", "-")))
        elif checklist_mode == "full_document_direct":
            st.info("Modo de checklist: documento completo direto · o modelo recebeu o documento inteiro para gerar o checklist.")
            cols = st.columns(2)
            cols[0].metric("Tamanho do documento", metadata.get("full_document_chars", 0))
            cols[1].metric("Chars enviados ao modelo", metadata.get("context_chars_sent", 0))
            if _should_explain_full_document_match(metadata):
                st.caption("Como o documento inteiro foi enviado ao modelo, o tamanho do documento e os chars enviados podem coincidir.")
        elif checklist_mode == "full_document_map_reduce":
            st.info("Modo de checklist: map-reduce com documento completo · o modelo recebeu o documento inteiro em várias partes e depois consolidou o checklist final.")
            cols = st.columns(2)
            cols[0].metric("Tamanho do documento", metadata.get("full_document_chars", 0))
            cols[1].metric("Chars enviados na síntese final", metadata.get("context_chars_sent", 0))
        elif checklist_mode == "document_scan_context":
            st.info("Modo de checklist: document-scan context · o modelo recebeu contexto recortado do documento para gerar o checklist.")
            cols = st.columns(2)
            cols[0].metric("Tamanho do documento", metadata.get("full_document_chars", 0))
            cols[1].metric("Chars do contexto enviados", metadata.get("context_chars_sent", 0))
        elif extraction_mode == "full_document_direct":
            st.info("Modo de extração: documento completo direto · o modelo recebeu o documento inteiro para extrair campos, entidades, riscos e obrigações.")
            cols = st.columns(2)
            cols[0].metric("Tamanho do documento", metadata.get("full_document_chars", 0))
            cols[1].metric("Chars enviados ao modelo", metadata.get("context_chars_sent", 0))
            if _should_explain_full_document_match(metadata):
                st.caption("Como o documento inteiro foi enviado ao modelo, o tamanho do documento e os chars enviados podem coincidir.")
        elif extraction_mode == "document_scan_context":
            st.info("Modo de extração: document-scan context · o modelo recebeu contexto recortado do documento para fazer a extração.")
            cols = st.columns(2)
            cols[0].metric("Tamanho do documento", metadata.get("full_document_chars", 0))
            cols[1].metric("Chars do contexto enviados", metadata.get("context_chars_sent", 0))

        if metadata.get("context_note"):
            st.caption(str(metadata.get("context_note")))

        stages = metadata.get("stages") if isinstance(metadata.get("stages"), list) else []
        show_stage_debug = result.task_type != "checklist"
        if stages and show_stage_debug:
            with st.expander("Ver detalhes técnicos da execução", expanded=False):
                st.write("**O que foi enviado ao modelo**")
                for stage in stages:
                    if not isinstance(stage, dict):
                        continue
                    label = str(stage.get("label") or stage.get("stage_type") or "Stage")
                    chars_sent = stage.get("chars_sent")
                    duration_s = stage.get("duration_s")
                    success = stage.get("success")
                    meta_parts = []
                    if chars_sent is not None:
                        meta_parts.append(f"chars={chars_sent}")
                    if duration_s is not None:
                        meta_parts.append(f"time={duration_s}s")
                    if success is not None:
                        meta_parts.append("ok" if success else "falhou")
                    title = label + (f" · {' · '.join(meta_parts)}" if meta_parts else "")
                    with st.expander(title, expanded=False):
                        context_preview = stage.get("context_preview")
                        prompt_preview = stage.get("prompt_preview")
                        if context_preview:
                            st.caption("Prévia do contexto")
                            st.text_area(
                                f"context_preview_{result.execution_id}_{label}",
                                value=str(context_preview),
                                height=320,
                                disabled=True,
                                label_visibility="collapsed",
                            )
                        if prompt_preview and prompt_preview != context_preview:
                            st.caption("Prévia do prompt")
                            st.text_area(
                                f"prompt_preview_{result.execution_id}_{label}",
                                value=str(prompt_preview),
                                height=320,
                                disabled=True,
                                label_visibility="collapsed",
                            )

    if workflow_trace:
        with st.expander("Traço do workflow LangGraph", expanded=False):
            st.dataframe(workflow_trace, width="stretch")

    if execution_shadow_summary:
        st.info("Comparação shadow direct vs LangGraph disponível para esta execução.")
        metric_1, metric_2, metric_3, metric_4 = st.columns(4)
        metric_1.metric("Mesmo sucesso", "Sim" if execution_shadow_summary.get("same_success") else "Não")
        metric_2.metric(
            "Δ qualidade",
            f"{float(execution_shadow_summary.get('quality_delta')):+.3f}"
            if isinstance(execution_shadow_summary.get("quality_delta"), (int, float))
            else "n/d",
        )
        metric_3.metric(
            "Δ latência",
            f"{float(execution_shadow_summary.get('latency_delta_s')):+.3f}s"
            if isinstance(execution_shadow_summary.get("latency_delta_s"), (int, float))
            else "n/d",
        )
        metric_4.metric(
            "Alt evitou review",
            "Sim" if execution_shadow_summary.get("alternate_avoided_review") else "Não",
        )
        with st.expander("Ver comparação direct vs LangGraph", expanded=False):
            st.write(execution_shadow_summary)


def _render_extraction(payload: ExtractionPayload) -> None:
    legal_view = _is_legal_extraction(payload)
    parties = _build_extraction_parties(payload)
    dates = _build_extraction_dates(payload)
    key_facts = _build_extraction_key_facts(payload)
    grouped_actions = _group_extraction_actions(payload)
    evidence_items = _collect_extraction_evidence(payload)

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    if legal_view:
        metric_1.metric("Partes", len(parties))
        metric_2.metric("Obrigações", len(payload.action_items))
        metric_3.metric("Riscos", len(payload.risks))
        metric_4.metric("Datas", len(dates) if dates else len(payload.important_dates))
    else:
        metric_1.metric("Entidades", len(payload.entities))
        metric_2.metric("Campos", len(payload.extracted_fields))
        metric_3.metric("Riscos", len(payload.risks))
        metric_4.metric("Ações", len(payload.action_items))

    if legal_view:
        _render_legal_hero(payload, parties, dates)

        overview_items = _build_legal_overview_items(payload, parties, dates, key_facts)
        if overview_items:
            st.subheader("Resumo executivo")
            _render_stat_cards(overview_items, columns_count=2)

        if payload.categories:
            st.caption("Temas identificados: " + ", ".join(_unique_preserve_order(payload.categories)))
    else:
        if payload.main_subject:
            st.write("**Assunto principal**")
            st.info(payload.main_subject)

        if payload.categories:
            st.write("**Categorias**")
            st.write(", ".join(_unique_preserve_order(payload.categories)))

    if legal_view and parties:
        _render_legal_parties(parties)

    if grouped_actions:
        if legal_view:
            immediate_actions, ongoing_actions = _split_action_groups(grouped_actions)
            if immediate_actions:
                st.subheader("O que precisa acontecer")
                _render_bullet_cards(
                    immediate_actions,
                    "description",
                    [("owner", "parte"), ("due_date", "prazo"), ("status", "status")],
                )
            if ongoing_actions:
                st.subheader("O que continua valendo")
                _render_bullet_cards(
                    ongoing_actions,
                    "description",
                    [("owner", "parte"), ("status", "status")],
                )
        else:
            st.subheader("Ações / próximos passos")
            flat_items = [{"owner": owner, **item} for owner, items in grouped_actions.items() for item in items]
            _render_bullet_cards(
                flat_items,
                "description",
                [("owner", "owner"), ("due_date", "prazo"), ("status", "status")],
            )

    if payload.risks:
        heading = "Riscos e pontos de atenção" if legal_view else "Riscos"
        st.subheader(heading)
        risk_cards = [
            {
                "description": item.description,
                "owner": _clean_text_value(item.owner),
                "due_date": _clean_text_value(item.due_date),
                "status": _clean_text_value(item.impact),
                "evidence": _clean_text_value(getattr(item, "evidence", None)),
            }
            for item in payload.risks
        ]
        _render_bullet_cards(
            risk_cards,
            "description",
            [("status", "impacto"), ("owner", "responsável"), ("due_date", "prazo")],
        )

    if dates:
        if legal_view:
            _render_legal_dates(dates)
        else:
            st.subheader("Prazos e datas relevantes")
            for item in dates:
                st.write(f"- **{item['label']}:** {item['value']}")
                if item["evidence"]:
                    st.caption(f"Trecho do documento: {item['evidence']}")

    if key_facts:
        if legal_view:
            display_key_facts = _filter_legal_key_facts_for_display(key_facts)
            highlight_facts, value_facts, other_facts = _split_legal_facts(display_key_facts)

            notable_facts = highlight_facts + other_facts
            if notable_facts:
                st.subheader("O que este documento estabelece")
                _render_stat_cards(notable_facts, columns_count=2)

            _render_legal_values(value_facts, payload.important_numbers)
        else:
            st.write("**Campos extraídos principais**")
            for fact in key_facts:
                st.write(f"- **{fact['label']}:** {fact['value']}")
                if fact["evidence"]:
                    st.caption(f"Evidência: {fact['evidence']}")

    if not legal_view and (payload.important_dates or payload.important_numbers):
        cols = st.columns(2)
        with cols[0]:
            if payload.important_dates and not dates:
                st.write("**Datas importantes**")
                for item in payload.important_dates:
                    st.write(f"- {item}")
        with cols[1]:
            if payload.important_numbers:
                label = "Números citados"
                if legal_view:
                    label = "Valores, percentuais e números adicionais"
                st.write(f"**{label}**")
                for item in _unique_preserve_order(payload.important_numbers):
                    st.write(f"- {item}")

    if payload.missing_information:
        if legal_view:
            _render_legal_missing_information(payload.missing_information)
        else:
            st.subheader("Informações ausentes / ambiguidades")
            for item in payload.missing_information:
                st.write(f"- {item}")

    if evidence_items:
        title = "Trechos de evidência do documento" if legal_view else "Trechos-evidência destacados"
        st.subheader(title)
        evidence_cards = [
            {
                "description": f"{item['label']}: {item['text']}",
                "owner": "",
                "due_date": "",
                "status": "",
                "evidence": "",
            }
            for item in evidence_items[:10]
        ]
        _render_bullet_cards(evidence_cards, "description", [], evidence_label="", columns_count=1)

    with st.expander("Ver detalhes técnicos da extração", expanded=False):
        if payload.entities:
            entities_table = [
                {
                    "type": entity.type,
                    "value": entity.value,
                    "confidence": entity.confidence,
                    "source_text": entity.source_text,
                    "position": f"{entity.position_start}-{entity.position_end}",
                }
                for entity in payload.entities
            ]
            st.write("**Entidades**")
            st.dataframe(entities_table, width="stretch")

        if payload.extracted_fields:
            st.write("**Campos extraídos**")
            st.dataframe(
                [
                    {"name": field.name, "value": field.value, "evidence": field.evidence}
                    for field in payload.extracted_fields
                ],
                width="stretch",
            )

        if payload.relationships:
            st.write("**Relações**")
            st.dataframe(
                [
                    {
                        "from": relationship.from_entity,
                        "to": relationship.to_entity,
                        "relationship": relationship.relationship,
                        "confidence": relationship.confidence,
                        "evidence": relationship.evidence,
                    }
                    for relationship in payload.relationships
                ],
                width="stretch",
            )

        if payload.action_items and not grouped_actions:
            st.write("**Ações identificadas**")
            for item in payload.action_items:
                line = item.description
                meta = []
                if item.owner:
                    meta.append(f"owner={item.owner}")
                if item.due_date:
                    meta.append(f"due={item.due_date}")
                if item.status:
                    meta.append(f"status={item.status}")
                if meta:
                    line += f" ({' · '.join(meta)})"
                st.write(f"- {line}")
                if getattr(item, "evidence", None):
                    st.caption(f"Evidência: {item.evidence}")


def _render_summary(payload: SummaryPayload) -> None:
    insights = _unique_preserve_order(payload.key_insights)
    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Temas", len(payload.topics))
    metric_2.metric("Insights-chave", len(insights))
    metric_3.metric("Leitura", f"{payload.reading_time_minutes} min")
    metric_4.metric("Completude estimada", f"{payload.completeness_score:.0%}")

    st.write("**Resumo executivo**")
    st.info(payload.executive_summary)

    if insights:
        st.write("**Insights-chave**")
        _render_summary_insight_cards(insights)

    if payload.topics:
        st.write("**Tópicos detalhados**")
        for index, topic in enumerate(payload.topics, start=1):
            with st.expander(f"{index}. {topic.title} · relevância {topic.relevance_score:.0%}", expanded=False):
                for point in topic.key_points:
                    st.write(f"- {point}")
                if topic.supporting_evidence:
                    _render_summary_supporting_evidence(topic.supporting_evidence)


def _render_checklist_friendly(payload: ChecklistPayload, *, execution_id: str | None = None) -> None:
    _render_checklist_content(
        payload,
        show_debug_table=False,
        interactive=False,
        execution_id=execution_id,
    )


def _render_checklist_view(payload: ChecklistPayload, *, execution_id: str | None = None) -> None:
    _render_checklist_content(
        payload,
        show_debug_table=False,
        interactive=True,
        execution_id=execution_id,
    )


def _build_cv_display_sections(payload: CVAnalysisPayload) -> tuple[list[CVSection], bool]:
    if payload.sections:
        return list(payload.sections), False

    derived_sections: list[CVSection] = []

    if payload.experience_entries:
        derived_sections.append(
            CVSection(
                section_type="experience",
                title="Experience",
                content=[
                    {
                        "text": entry.description or " | ".join(
                            part for part in [entry.title, entry.organization, entry.location, entry.date_range] if part
                        ),
                        "details": {
                            "title": entry.title,
                            "organization": entry.organization,
                            "location": entry.location,
                            "date_range": entry.date_range,
                            "bullets": entry.bullets,
                        },
                    }
                    for entry in payload.experience_entries
                ],
                confidence=0.9,
            )
        )

    if payload.education_entries:
        derived_sections.append(
            CVSection(
                section_type="education",
                title="Education",
                content=[
                    {
                        "text": entry.description or " | ".join(
                            part for part in [entry.degree, entry.institution, entry.location, entry.date_range] if part
                        )
                    }
                    for entry in payload.education_entries
                ],
                confidence=0.9,
            )
        )

    if payload.skills:
        derived_sections.append(
            CVSection(
                section_type="skills",
                title="Skills",
                content=[{"text": item} for item in payload.skills],
                confidence=0.9,
            )
        )

    if payload.languages:
        derived_sections.append(
            CVSection(
                section_type="languages",
                title="Languages",
                content=[{"text": item} for item in payload.languages],
                confidence=0.9,
            )
        )

    return derived_sections, True


def _format_cv_section_item_text(item: Any) -> str | None:
    if getattr(item, "text", None):
        return str(item.text)

    details = getattr(item, "details", None) or {}
    if not isinstance(details, dict):
        return None

    ordered_values = [
        details.get("title"),
        details.get("organization"),
        details.get("institution"),
        details.get("degree"),
        details.get("location"),
        details.get("date_range"),
    ]
    parts = [str(value).strip() for value in ordered_values if value]
    if parts:
        return " | ".join(parts)

    return None


def _render_cv_analysis(payload: CVAnalysisPayload) -> None:
    display_sections, sections_are_derived = _build_cv_display_sections(payload)
    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("Seções", len(display_sections))
    metric_2.metric("Habilidades", len(payload.skills))
    metric_3.metric("Experiência", f"{payload.experience_years:.1f} anos")

    if payload.personal_info:
        info = payload.personal_info
        st.write("**Perfil**")
        if info.full_name:
            st.subheader(info.full_name)
        meta_parts = [part for part in [info.location, info.email, info.phone] if part]
        if meta_parts:
            st.caption(" · ".join(meta_parts))
        if info.links:
            st.write("Links: " + " · ".join(info.links))

    if payload.skills:
        st.write("**Habilidades**")
        st.write(", ".join(payload.skills))

    if payload.languages:
        st.write("**Idiomas**")
        st.write(", ".join(payload.languages))

    if payload.education_entries:
        st.write("**Formação**")
        for entry in payload.education_entries:
            line = entry.description or " | ".join(
                part for part in [entry.degree, entry.institution, entry.location, entry.date_range] if part
            )
            if line:
                st.write(f"- {line}")

    if payload.experience_entries:
        st.write("**Experiências**")
        for entry in payload.experience_entries:
            title_line = " | ".join(part for part in [entry.title, entry.organization, entry.location, entry.date_range] if part)
            if title_line:
                st.write(f"- {title_line}")
            if entry.bullets:
                for bullet in entry.bullets:
                    st.caption(f"• {bullet}")

    if payload.strengths:
        st.write("**Pontos fortes**")
        for item in payload.strengths:
            st.write(f"- {item}")

    if payload.improvement_areas:
        st.write("**Pontos a melhorar**")
        for item in payload.improvement_areas:
            st.write(f"- {item}")

    if display_sections:
        st.write("**Seções**")
        for section in display_sections:
            label = f"{section.title} · {section.section_type}"
            if not sections_are_derived:
                label += f" · confiança {section.confidence:.0%}"
            with st.expander(label, expanded=False):
                for item in section.content:
                    item_text = _format_cv_section_item_text(item)
                    if item_text:
                        st.write(f"- {item_text}")


def _render_code_analysis(payload: CodeAnalysisPayload) -> None:
    issues = _sort_code_issues(payload.detected_issues)
    high_severity_count = sum(1 for issue in issues if _clean_text_value(issue.severity).lower() == "high")

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Problemas", len(issues))
    metric_2.metric("Alta severidade", high_severity_count)
    metric_3.metric("Passos de refatoração", len(payload.refactor_plan))
    metric_4.metric("Sugestões de teste", len(payload.test_suggestions))

    st.write("**Resumo do trecho**")
    st.info(payload.snippet_summary)
    st.write("**Objetivo principal**")
    st.write(payload.main_purpose)

    if issues:
        if high_severity_count:
            st.warning(f"Foram encontrados {high_severity_count} problema(s) de alta severidade que merecem revisão primeiro.")
        else:
            st.info("Não foram identificados problemas de alta severidade; os achados parecem mais localizados ou de médio/baixo risco.")

    if issues:
        st.write("**Problemas detectados**")
        for index, issue in enumerate(issues):
            _render_code_issue_card(
                issue,
                expanded=index == 0 and _clean_text_value(issue.severity).lower() == "high",
            )

    for heading, items, numbered in [
        ("Melhorias de legibilidade", payload.readability_improvements, False),
        ("Melhorias de manutenibilidade", payload.maintainability_improvements, False),
        ("Plano de refatoração sugerido", payload.refactor_plan, True),
        ("Sugestões de teste", payload.test_suggestions, False),
        ("Riscos observados", payload.risk_notes, False),
    ]:
        if items:
            st.write(f"**{heading}**")
            for index, item in enumerate(items, start=1):
                prefix = f"{index}." if numbered else "-"
                st.write(f"{prefix} {item}")


def _render_friendly_payload(payload: Any, *, execution_id: str | None = None) -> None:
    if isinstance(payload, ExtractionPayload):
        _render_extraction(payload)
    elif isinstance(payload, SummaryPayload):
        _render_summary(payload)
    elif isinstance(payload, ChecklistPayload):
        _render_checklist_friendly(payload, execution_id=execution_id)
    elif isinstance(payload, CVAnalysisPayload):
        _render_cv_analysis(payload)
    elif isinstance(payload, CodeAnalysisPayload):
        _render_code_analysis(payload)
    else:
        st.json(_payload_to_json(payload))


def render_structured_result(result: StructuredResult, requested_mode: str | None = None) -> None:
    """Render a structured result using the requested mode when available."""
    _render_result_header(result)

    available_modes = sorted(
        [mode for mode in result.available_render_modes if mode.available],
        key=lambda mode: mode.priority,
    )
    available_mode_names = [mode.mode for mode in available_modes]
    mode = requested_mode or result.primary_render_mode or (available_mode_names[0] if available_mode_names else "json")
    if mode not in available_mode_names and available_mode_names:
        mode = available_mode_names[0]

    payload_json = _payload_to_json(result.validated_output) if result.validated_output is not None else result.parsed_json

    if mode == "checklist" and isinstance(result.validated_output, ChecklistPayload):
        _render_checklist_view(result.validated_output, execution_id=result.execution_id)
    elif mode == "friendly" and result.validated_output is not None:
        _render_friendly_payload(result.validated_output, execution_id=result.execution_id)
    else:
        if payload_json is not None:
            st.json(payload_json)
        elif result.raw_output_text:
            st.code(result.raw_output_text)

    if result.source_documents:
        st.caption(f"Documentos-fonte: {', '.join(result.source_documents)}")

    export_payload = payload_json or {"raw_output_text": result.raw_output_text, "task_type": result.task_type}
    st.download_button(
        "Baixar JSON estruturado",
        data=json.dumps(export_payload, ensure_ascii=False, indent=2),
        file_name=f"structured_{result.task_type}_{result.execution_id[:8]}.json",
        mime="application/json",
        width="stretch",
    )