"""Renderers for Phase 5 structured outputs."""
from __future__ import annotations

import json
from typing import Any

import streamlit as st

from ..structured.base import (
    ChecklistPayload,
    CVSection,
    CVAnalysisPayload,
    CodeAnalysisPayload,
    ExtractionPayload,
    SummaryPayload,
)
from ..structured.envelope import StructuredResult


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


def _clean_text_value(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


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
    return cleaned.capitalize() if cleaned else "Campo"


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
    status_label = "Validated" if result.success else "Failed"
    status_kind = "success" if result.success else "error"
    context_label = "with document context" if result.context_used else "without document context"
    repair_label = "repair applied" if result.repair_applied else "no repair"
    st.caption(
        f"Task: `{result.task_type}` · Execution: `{result.execution_id[:8]}` · {status_label} · {context_label} · {repair_label}"
    )

    if status_kind == "success":
        st.success("Structured output generated and validated.")
        if result.quality_score is not None and result.quality_score < 0.65:
            st.warning(
                f"This payload validated structurally, but its estimated quality is low ({result.quality_score:.0%}). Review grounding and placeholders before trusting it."
            )
    else:
        error_message = result.validation_error or result.parsing_error or (result.error.message if result.error else "Unknown error")
        st.error(error_message)

    metadata = result.execution_metadata if isinstance(result.execution_metadata, dict) else {}
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
                "Summary mode: full-document map-reduce · o modelo recebeu o documento inteiro em várias partes, depois fez uma síntese final."
            )
            cols = st.columns(3)
            cols[0].metric("Document chars", metadata.get("full_document_chars", 0))
            cols[1].metric("Parts", metadata.get("document_parts", 0))
            cols[2].metric("Partial summaries", metadata.get("partial_summaries_generated", 0))
        elif summary_mode == "single_pass_context":
            st.info("Summary mode: single-pass context · o modelo resumiu usando apenas o contexto recortado mostrado nesta estratégia.")
            cols = st.columns(3)
            cols[0].metric("Document chars", metadata.get("full_document_chars", 0))
            cols[1].metric("Context chars sent", metadata.get("context_chars_sent", 0))
            cols[2].metric("Strategy", str(metadata.get("context_strategy", "-")))
        elif checklist_mode == "full_document_direct":
            st.info("Checklist mode: full-document direct · o modelo recebeu o documento inteiro para gerar o checklist.")
            cols = st.columns(2)
            cols[0].metric("Document chars", metadata.get("full_document_chars", 0))
            cols[1].metric("Context chars sent", metadata.get("context_chars_sent", 0))
        elif checklist_mode == "full_document_map_reduce":
            st.info("Checklist mode: full-document map-reduce · o modelo recebeu o documento inteiro em várias partes e depois consolidou o checklist final.")
            cols = st.columns(2)
            cols[0].metric("Document chars", metadata.get("full_document_chars", 0))
            cols[1].metric("Final chars sent", metadata.get("context_chars_sent", 0))
        elif checklist_mode == "document_scan_context":
            st.info("Checklist mode: document-scan context · o modelo recebeu contexto recortado do documento para gerar o checklist.")
            cols = st.columns(2)
            cols[0].metric("Document chars", metadata.get("full_document_chars", 0))
            cols[1].metric("Context chars sent", metadata.get("context_chars_sent", 0))
        elif extraction_mode == "full_document_direct":
            st.info("Extraction mode: full-document direct · o modelo recebeu o documento inteiro para extrair campos, entidades, riscos e obrigações.")
            cols = st.columns(2)
            cols[0].metric("Document chars", metadata.get("full_document_chars", 0))
            cols[1].metric("Context chars sent", metadata.get("context_chars_sent", 0))
        elif extraction_mode == "document_scan_context":
            st.info("Extraction mode: document-scan context · o modelo recebeu contexto recortado do documento para fazer a extração.")
            cols = st.columns(2)
            cols[0].metric("Document chars", metadata.get("full_document_chars", 0))
            cols[1].metric("Context chars sent", metadata.get("context_chars_sent", 0))

        if metadata.get("context_note"):
            st.caption(str(metadata.get("context_note")))

        stages = metadata.get("stages") if isinstance(metadata.get("stages"), list) else []
        show_stage_debug = result.task_type != "checklist"
        if stages and show_stage_debug:
            st.write("**What was sent to the AI**")
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
                    meta_parts.append("ok" if success else "failed")
                title = label + (f" · {' · '.join(meta_parts)}" if meta_parts else "")
                with st.expander(title, expanded=False):
                    context_preview = stage.get("context_preview")
                    prompt_preview = stage.get("prompt_preview")
                    if context_preview:
                        st.caption("Context preview")
                        st.text_area(
                            f"context_preview_{result.execution_id}_{label}",
                            value=str(context_preview),
                            height=320,
                            disabled=True,
                            label_visibility="collapsed",
                        )
                    if prompt_preview and prompt_preview != context_preview:
                        st.caption("Prompt preview")
                        st.text_area(
                            f"prompt_preview_{result.execution_id}_{label}",
                            value=str(prompt_preview),
                            height=320,
                            disabled=True,
                            label_visibility="collapsed",
                        )


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
        metric_1.metric("Entities", len(payload.entities))
        metric_2.metric("Fields", len(payload.extracted_fields))
        metric_3.metric("Risks", len(payload.risks))
        metric_4.metric("Actions", len(payload.action_items))

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
            highlight_facts, value_facts, other_facts = _split_legal_facts(key_facts)

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
            st.write("**Entities**")
            st.dataframe(entities_table, width="stretch")

        if payload.extracted_fields:
            st.write("**Extracted fields**")
            st.dataframe(
                [
                    {"name": field.name, "value": field.value, "evidence": field.evidence}
                    for field in payload.extracted_fields
                ],
                width="stretch",
            )

        if payload.relationships:
            st.write("**Relationships**")
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
            st.write("**Action items**")
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
    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("Topics", len(payload.topics))
    metric_2.metric("Reading time", f"{payload.reading_time_minutes} min")
    metric_3.metric("Completeness", f"{payload.completeness_score:.0%}")

    st.write("**Executive summary**")
    st.info(payload.executive_summary)

    if payload.key_insights:
        st.write("**Key insights**")
        for insight in payload.key_insights:
            st.write(f"- {insight}")

    if payload.topics:
        st.write("**Topics**")
        for topic in payload.topics:
            with st.expander(f"{topic.title} · relevance {topic.relevance_score:.0%}", expanded=False):
                for point in topic.key_points:
                    st.write(f"- {point}")
                if topic.supporting_evidence:
                    st.caption("Supporting evidence")
                    for evidence in topic.supporting_evidence:
                        st.write(f"- {evidence}")


def _render_checklist_friendly(payload: ChecklistPayload) -> None:
    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("Items", payload.total_items)
    metric_2.metric("Completed", payload.completed_items)
    metric_3.metric("Progress", f"{payload.progress_percentage:.0f}%")
    st.progress(min(max(payload.progress_percentage / 100.0, 0.0), 1.0))
    st.write(f"**{payload.title}**")
    st.caption(payload.description)

    if payload.items:
        show_category = any(item.category for item in payload.items)
        show_evidence = any(getattr(item, "evidence", None) for item in payload.items)
        show_priority = any(item.priority for item in payload.items)
        show_eta = any(item.estimated_time_minutes is not None for item in payload.items)
        show_dependencies = any(item.dependencies for item in payload.items)

        checklist_table = [
            {
                "title": item.title,
                **({"category": item.category} if show_category else {}),
                **({"evidence": item.evidence} if show_evidence else {}),
                **({"priority": item.priority} if show_priority else {}),
                "status": item.status,
                **({"eta_min": item.estimated_time_minutes} if show_eta else {}),
                **({"dependencies": ", ".join(item.dependencies) if item.dependencies else ""} if show_dependencies else {}),
            }
            for item in payload.items
        ]
        st.dataframe(checklist_table, width="stretch")


def _render_checklist_view(payload: ChecklistPayload) -> None:
    st.write(f"**{payload.title}**")
    st.caption(payload.description)
    st.progress(min(max(payload.progress_percentage / 100.0, 0.0), 1.0))
    show_category = any(item.category for item in payload.items)
    show_priority = any(item.priority for item in payload.items)
    show_eta = any(item.estimated_time_minutes is not None for item in payload.items)
    for index, item in enumerate(payload.items, start=1):
        done = item.status == "completed"
        icon = "✅" if done else "⬜"
        st.markdown(f"{icon} **{index}. {item.title}**")
        if _checklist_description_adds_value(item.title, item.description):
            st.caption(item.description)
        meta_parts = []
        if show_category and item.category:
            meta_parts.append(f"category={item.category}")
        if show_priority and item.priority:
            meta_parts.append(f"priority={item.priority}")
        meta_parts.append(f"status={item.status}")
        if show_eta and item.estimated_time_minutes is not None:
            meta_parts.append(f"eta={item.estimated_time_minutes} min")
        if meta_parts:
            st.caption(" · ".join(meta_parts))
        if getattr(item, "source_text", None):
            st.caption(f"source: {item.source_text}")
        if getattr(item, "evidence", None):
            st.caption(f"evidence: {item.evidence}")
        if item.dependencies:
            st.caption(f"depends on: {', '.join(item.dependencies)}")


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
    metric_1.metric("Sections", len(display_sections))
    metric_2.metric("Skills", len(payload.skills))
    metric_3.metric("Experience", f"{payload.experience_years:.1f} years")

    if payload.personal_info:
        info = payload.personal_info
        st.write("**Profile**")
        if info.full_name:
            st.subheader(info.full_name)
        meta_parts = [part for part in [info.location, info.email, info.phone] if part]
        if meta_parts:
            st.caption(" · ".join(meta_parts))
        if info.links:
            st.write("Links: " + " · ".join(info.links))

    if payload.skills:
        st.write("**Skills**")
        st.write(", ".join(payload.skills))

    if payload.languages:
        st.write("**Languages**")
        st.write(", ".join(payload.languages))

    if payload.education_entries:
        st.write("**Education**")
        for entry in payload.education_entries:
            line = entry.description or " | ".join(
                part for part in [entry.degree, entry.institution, entry.location, entry.date_range] if part
            )
            if line:
                st.write(f"- {line}")

    if payload.experience_entries:
        st.write("**Experience entries**")
        for entry in payload.experience_entries:
            title_line = " | ".join(part for part in [entry.title, entry.organization, entry.location, entry.date_range] if part)
            if title_line:
                st.write(f"- {title_line}")
            if entry.bullets:
                for bullet in entry.bullets:
                    st.caption(f"• {bullet}")

    if payload.strengths:
        st.write("**Strengths**")
        for item in payload.strengths:
            st.write(f"- {item}")

    if payload.improvement_areas:
        st.write("**Improvement areas**")
        for item in payload.improvement_areas:
            st.write(f"- {item}")

    if display_sections:
        st.write("**Sections**")
        for section in display_sections:
            label = f"{section.title} · {section.section_type}"
            if not sections_are_derived:
                label += f" · confidence {section.confidence:.0%}"
            with st.expander(label, expanded=False):
                for item in section.content:
                    item_text = _format_cv_section_item_text(item)
                    if item_text:
                        st.write(f"- {item_text}")


def _render_code_analysis(payload: CodeAnalysisPayload) -> None:
    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("Issues", len(payload.detected_issues))
    metric_2.metric("Refactor steps", len(payload.refactor_plan))
    metric_3.metric("Test suggestions", len(payload.test_suggestions))

    st.write("**Snippet summary**")
    st.info(payload.snippet_summary)
    st.write("**Main purpose**")
    st.write(payload.main_purpose)

    if payload.detected_issues:
        st.write("**Detected issues**")
        for issue in payload.detected_issues:
            with st.expander(f"{issue.severity.upper()} · {issue.category} · {issue.title}", expanded=False):
                st.write(issue.description)
                if issue.evidence:
                    st.caption(f"Evidence: {issue.evidence}")
                if issue.recommendation:
                    st.write(f"Recommendation: {issue.recommendation}")

    for heading, items in [
        ("Readability improvements", payload.readability_improvements),
        ("Maintainability improvements", payload.maintainability_improvements),
        ("Refactor plan", payload.refactor_plan),
        ("Test suggestions", payload.test_suggestions),
        ("Risk notes", payload.risk_notes),
    ]:
        if items:
            st.write(f"**{heading}**")
            for item in items:
                st.write(f"- {item}")


def _render_friendly_payload(payload: Any) -> None:
    if isinstance(payload, ExtractionPayload):
        _render_extraction(payload)
    elif isinstance(payload, SummaryPayload):
        _render_summary(payload)
    elif isinstance(payload, ChecklistPayload):
        _render_checklist_friendly(payload)
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
        _render_checklist_view(result.validated_output)
    elif mode == "friendly" and result.validated_output is not None:
        _render_friendly_payload(result.validated_output)
    else:
        if payload_json is not None:
            st.json(payload_json)
        elif result.raw_output_text:
            st.code(result.raw_output_text)

    if result.source_documents:
        st.caption(f"Source documents: {', '.join(result.source_documents)}")

    export_payload = payload_json or {"raw_output_text": result.raw_output_text, "task_type": result.task_type}
    st.download_button(
        "Download structured JSON",
        data=json.dumps(export_payload, ensure_ascii=False, indent=2),
        file_name=f"structured_{result.task_type}_{result.execution_id[:8]}.json",
        mime="application/json",
        width="stretch",
    )