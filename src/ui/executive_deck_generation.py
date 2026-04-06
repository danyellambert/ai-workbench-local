from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from src.config import PresentationExportSettings
from src.services.app_errors import build_ui_error_message
from src.services.presentation_export import (
    ACTION_PLAN_EXPORT_KIND,
    CANDIDATE_REVIEW_EXPORT_KIND,
    DEFAULT_PRESENTATION_EXPORT_KIND,
    DOCUMENT_REVIEW_EXPORT_KIND,
    EVIDENCE_PACK_EXPORT_KIND,
    EXECUTIVE_DECK_EXPORT_KIND_LABELS,
    POLICY_CONTRACT_COMPARISON_EXPORT_KIND,
    normalize_executive_deck_export_kind,
)
from src.services.presentation_export_service import generate_executive_deck, is_export_kind_enabled, resolve_enabled_export_kinds
from src.storage.phase95_evidenceops_action_store import load_evidenceops_actions
from src.storage.phase95_evidenceops_worklog import load_evidenceops_worklog
from src.structured.base import DocumentAgentPayload
from src.structured.envelope import StructuredResult


PRESENTATION_EXPORT_RESULT_STATE_KEY = "phase10_executive_deck_generation_result"
PRESENTATION_EXPORT_SELECTED_KIND_STATE_KEY = "phase10_executive_deck_generation_selected_kind"


def _safe_read_bytes(path_value: object) -> bytes | None:
    normalized = str(path_value or "").strip()
    if not normalized:
        return None
    path = Path(normalized)
    if not path.exists() or not path.is_file():
        return None
    return path.read_bytes()


def _safe_read_text(path_value: object) -> str | None:
    normalized = str(path_value or "").strip()
    if not normalized:
        return None
    path = Path(normalized)
    if not path.exists() or not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _load_structured_result(raw_value: object) -> StructuredResult | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, StructuredResult):
        return raw_value
    if isinstance(raw_value, dict):
        return StructuredResult.model_validate(raw_value)
    return None


def _build_availability_map(
    *,
    model_comparison_entries: list[dict[str, Any]],
    structured_result: StructuredResult | None,
    evidenceops_worklog_entries: list[dict[str, Any]],
    evidenceops_action_entries: list[dict[str, Any]],
    settings: PresentationExportSettings,
) -> dict[str, dict[str, Any]]:
    payload = structured_result.validated_output if structured_result is not None else None
    task_type = structured_result.task_type if structured_result is not None else None
    is_document_agent = isinstance(payload, DocumentAgentPayload)
    has_comparison_context = bool(
        is_document_agent
        and (list(payload.comparison_findings or []) or len(payload.compared_documents or []) >= 2)
    )

    availability_map = {
        DEFAULT_PRESENTATION_EXPORT_KIND: {
            "available": bool(model_comparison_entries),
            "source": "Benchmark log + eval store",
            "reason": (
                "Uses the Phase 7 logs and the persisted evals from Phase 8."
                if model_comparison_entries
                else "Run at least one comparison in Phase 7 before generating this deck."
            ),
        },
        DOCUMENT_REVIEW_EXPORT_KIND: {
            "available": task_type in {"document_agent", "extraction", "summary"},
            "source": "Latest structured result",
            "reason": (
                f"Will use the latest structured result from the `{task_type}` task."
                if task_type in {"document_agent", "extraction", "summary"}
                else "Run a `document_agent`, `extraction`, or `summary` task to generate this deck."
            ),
        },
        POLICY_CONTRACT_COMPARISON_EXPORT_KIND: {
            "available": has_comparison_context,
            "source": "Latest document_agent with comparison findings",
            "reason": (
                "Will use the latest `document_agent` with grounded comparison findings."
                if has_comparison_context
                else "Run a `document_agent` with document comparison before generating this deck."
            ),
        },
        ACTION_PLAN_EXPORT_KIND: {
            "available": bool(evidenceops_action_entries) or task_type in {"checklist", "document_agent"},
            "source": "EvidenceOps action store or latest structured result",
            "reason": (
                "Will use the local EvidenceOps action store as the primary source."
                if evidenceops_action_entries
                else f"Will use the latest structured result from the `{task_type}` task."
                if task_type in {"checklist", "document_agent"}
                else "Run a checklist/document_agent flow or generate actions in EvidenceOps before generating this deck."
            ),
        },
        CANDIDATE_REVIEW_EXPORT_KIND: {
            "available": task_type == "cv_analysis",
            "source": "Latest cv_analysis",
            "reason": (
                "Will use the latest validated `cv_analysis`."
                if task_type == "cv_analysis"
                else "Run a `cv_analysis` before generating this deck."
            ),
        },
        EVIDENCE_PACK_EXPORT_KIND: {
            "available": bool(evidenceops_worklog_entries or evidenceops_action_entries),
            "source": "EvidenceOps worklog + action store",
            "reason": (
                "Will use the EvidenceOps worklog and/or local action store."
                if (evidenceops_worklog_entries or evidenceops_action_entries)
                else "Run the Document Operations Copilot with EvidenceOps logging before generating this deck."
            ),
        },
    }

    enabled_export_kinds = resolve_enabled_export_kinds(settings)
    if enabled_export_kinds:
        enabled_export_kinds_text = ", ".join(enabled_export_kinds)
        for export_kind, payload in availability_map.items():
            if not is_export_kind_enabled(export_kind=export_kind, settings=settings):
                payload["available"] = False
                payload["reason"] = (
                    f"Deck type disabled by configuration (`PRESENTATION_EXPORT_ENABLED_EXPORT_KINDS`). "
                    f"Currently enabled: {enabled_export_kinds_text}."
                )
    return availability_map


def render_executive_deck_generation_panel(
    *,
    model_comparison_entries: list[dict[str, Any]],
    phase8_eval_db_path: str | Path,
    structured_result: StructuredResult | dict[str, Any] | None,
    phase95_evidenceops_worklog_path: str | Path,
    phase95_evidenceops_action_store_path: str | Path,
    settings: PresentationExportSettings,
    allowed_export_kinds: list[str] | tuple[str, ...] | None = None,
    surface_label: str | None = None,
) -> None:
    loaded_structured_result = _load_structured_result(structured_result)
    evidenceops_worklog_entries = load_evidenceops_worklog(Path(phase95_evidenceops_worklog_path)) if Path(phase95_evidenceops_worklog_path).exists() else []
    evidenceops_action_entries = load_evidenceops_actions(Path(phase95_evidenceops_action_store_path), limit=250) if Path(phase95_evidenceops_action_store_path).exists() else []
    availability_map = _build_availability_map(
        model_comparison_entries=model_comparison_entries,
        structured_result=loaded_structured_result,
        evidenceops_worklog_entries=evidenceops_worklog_entries,
        evidenceops_action_entries=evidenceops_action_entries,
        settings=settings,
    )
    export_kind_options = list(EXECUTIVE_DECK_EXPORT_KIND_LABELS.keys())
    normalized_allowed_export_kinds = [
        normalize_executive_deck_export_kind(item)
        for item in (allowed_export_kinds or [])
        if str(item or "").strip()
    ]
    if normalized_allowed_export_kinds:
        export_kind_options = [item for item in export_kind_options if item in normalized_allowed_export_kinds]
    if not export_kind_options:
        st.info("No deck type is enabled for this surface right now.")
        return
    panel_label = surface_label or "Product"
    selected_export_kind = st.selectbox(
        "Deck type",
        options=export_kind_options,
        index=export_kind_options.index(st.session_state.get(PRESENTATION_EXPORT_SELECTED_KIND_STATE_KEY, DEFAULT_PRESENTATION_EXPORT_KIND))
        if st.session_state.get(PRESENTATION_EXPORT_SELECTED_KIND_STATE_KEY, DEFAULT_PRESENTATION_EXPORT_KIND) in export_kind_options
        else 0,
        format_func=lambda key: f"{EXECUTIVE_DECK_EXPORT_KIND_LABELS.get(key, key)} {'✅' if availability_map.get(key, {}).get('available') else '⚠️'}",
        key=PRESENTATION_EXPORT_SELECTED_KIND_STATE_KEY,
    )
    selected_availability = availability_map.get(selected_export_kind, {})

    st.markdown(f"### Executive Deck Generation · {panel_label}")
    if panel_label.lower() == "ai lab":
        st.caption(
            "On the AI Lab surface, the focus is executive export for benchmark/eval review. Workflow-oriented decks move to the product surface in Gradio."
        )
    else:
        st.caption(
            "Generate all Executive Deck Generation slices using the product signals already available: benchmark/evals, structured outputs, comparison findings, cv_analysis, and EvidenceOps."
        )
    st.caption(f"Configured renderer: `{settings.base_url or 'n/a'}` · timeout `{settings.timeout_seconds}s` · review `{settings.include_review}`")
    enabled_export_kinds = resolve_enabled_export_kinds(settings)
    if enabled_export_kinds:
        st.caption(f"Deck types enabled by configuration: `{', '.join(enabled_export_kinds)}`")
    with st.expander("Recommended setup — host-native renderer", expanded=False):
        st.code("bash scripts/run_ppt_creator_renderer_host.sh", language="bash")
        st.code(f"curl {settings.base_url.rstrip('/')}/health", language="bash")
        st.caption(
            "The Docker path for `ppt_creator_app` was prepared in the sibling repository, but the recommended operating mode right now is still host-native in order to preserve the full deck-app capability set."
        )
    if not settings.enabled:
        st.info(
            "`PRESENTATION_EXPORT_ENABLED=false`: in this configuration the app can still generate and persist the contract/payload locally, but it will not call the remote renderer until the feature is enabled."
        )

    st.write(
        {
            "selected_deck_type": EXECUTIVE_DECK_EXPORT_KIND_LABELS.get(selected_export_kind, selected_export_kind),
            "available_now": bool(selected_availability.get("available")),
            "input_source": selected_availability.get("source"),
            "reason": selected_availability.get("reason"),
            "latest_structured_task": loaded_structured_result.task_type if loaded_structured_result is not None else None,
            "evidenceops_worklog_entries": len(evidenceops_worklog_entries),
            "evidenceops_action_entries": len(evidenceops_action_entries),
        }
    )

    can_generate = bool(selected_availability.get("available"))
    if not can_generate:
        st.caption(str(selected_availability.get("reason") or "There is not enough input yet to generate this deck."))

    if st.button(
        f"Generate {EXECUTIVE_DECK_EXPORT_KIND_LABELS.get(selected_export_kind, selected_export_kind)}",
        disabled=not can_generate,
        key="phase10_generate_executive_review_deck",
    ):
        with st.spinner("Generating contract, calling renderer, and downloading artifacts..."):
            try:
                result = generate_executive_deck(
                    export_kind=selected_export_kind,
                    model_comparison_entries=model_comparison_entries,
                    phase8_eval_db_path=phase8_eval_db_path,
                    structured_result=loaded_structured_result,
                    evidenceops_worklog_entries=evidenceops_worklog_entries,
                    evidenceops_action_entries=evidenceops_action_entries,
                    settings=settings,
                )
                stored_results = st.session_state.get(PRESENTATION_EXPORT_RESULT_STATE_KEY)
                if not isinstance(stored_results, dict):
                    stored_results = {}
                stored_results[selected_export_kind] = result
                st.session_state[PRESENTATION_EXPORT_RESULT_STATE_KEY] = stored_results
            except Exception as error:  # pragma: no cover - defensive UI path
                st.error(build_ui_error_message("Failed to generate the executive review deck", error))

    stored_results = st.session_state.get(PRESENTATION_EXPORT_RESULT_STATE_KEY)
    stored_result = stored_results.get(selected_export_kind) if isinstance(stored_results, dict) else None
    if not isinstance(stored_result, dict):
        return

    status = str(stored_result.get("status") or "unknown")
    export_id = str(stored_result.get("export_id") or "n/a")
    export_kind_label = str(stored_result.get("export_kind_label") or EXECUTIVE_DECK_EXPORT_KIND_LABELS.get(selected_export_kind, selected_export_kind))
    if status == "completed":
        st.success(f"{export_kind_label} generated successfully. Export ID: `{export_id}`")
    elif status in {"disabled", "service_unavailable", "artifact_download_failed"}:
        st.warning(f"{export_kind_label} finished with status `{status}`. Export ID: `{export_id}`")
    else:
        st.error(f"{export_kind_label} failed with status `{status}`. Export ID: `{export_id}`")

    summary_col_1, summary_col_2, summary_col_3, summary_col_4 = st.columns(4)
    summary_col_1.metric("Status", status)
    summary_col_2.metric("Bench runs", int(stored_result.get("model_comparison_entry_count") or 0))
    summary_col_3.metric("Eval runs", int(stored_result.get("eval_entry_count") or 0))
    summary_col_4.metric("Deck size", f"{int(stored_result.get('pptx_size_bytes') or 0)} bytes")
    st.caption(
        f"Renderer health: `{stored_result.get('service_health')}` · render={stored_result.get('render_latency_s')}s · download={stored_result.get('artifact_download_latency_s')}s"
    )
    if stored_result.get("remote_output_path"):
        st.caption(f"Remote artifact: `{stored_result.get('remote_output_path')}`")
    if stored_result.get("local_artifact_dir"):
        st.caption(f"Local artifacts: `{stored_result.get('local_artifact_dir')}`")

    warnings = stored_result.get("warnings") if isinstance(stored_result.get("warnings"), list) else []
    for warning in warnings:
        st.warning(str(warning))
    if stored_result.get("error_message"):
        st.error(str(stored_result.get("error_message")))

    st.markdown("**Export downloads**")
    download_col_1, download_col_2, download_col_3 = st.columns(3)
    pptx_bytes = _safe_read_bytes(stored_result.get("local_pptx_path"))
    if pptx_bytes is not None:
        download_col_1.download_button(
            "Download PPTX",
            data=pptx_bytes,
            file_name=Path(str(stored_result.get("local_pptx_path"))).name,
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            key="phase10_download_executive_deck_pptx",
        )
    contract_text = _safe_read_text(stored_result.get("local_contract_path"))
    if contract_text is not None:
        download_col_2.download_button(
            "Download contract.json",
            data=contract_text,
            file_name=Path(str(stored_result.get("local_contract_path"))).name,
            mime="application/json",
            key="phase10_download_executive_deck_contract",
        )
    payload_text = _safe_read_text(stored_result.get("local_payload_path"))
    if payload_text is not None:
        download_col_3.download_button(
            "Download payload.json",
            data=payload_text,
            file_name=Path(str(stored_result.get("local_payload_path"))).name,
            mime="application/json",
            key="phase10_download_executive_deck_payload",
        )

    extra_col_1, extra_col_2, extra_col_3 = st.columns(3)
    render_response_text = _safe_read_text(stored_result.get("local_render_response_path"))
    if render_response_text is not None:
        extra_col_1.download_button(
            "Download render_response.json",
            data=render_response_text,
            file_name=Path(str(stored_result.get("local_render_response_path"))).name,
            mime="application/json",
            key="phase10_download_executive_deck_render_response",
        )
    review_text = _safe_read_text(stored_result.get("local_review_path"))
    if review_text is not None:
        extra_col_2.download_button(
            "Download review.json",
            data=review_text,
            file_name=Path(str(stored_result.get("local_review_path"))).name,
            mime="application/json",
            key="phase10_download_executive_deck_review",
        )
    preview_manifest_text = _safe_read_text(stored_result.get("local_preview_manifest_path"))
    if preview_manifest_text is not None:
        extra_col_3.download_button(
            "Download preview_manifest.json",
            data=preview_manifest_text,
            file_name=Path(str(stored_result.get("local_preview_manifest_path"))).name,
            mime="application/json",
            key="phase10_download_executive_deck_preview_manifest",
        )

    thumbnail_bytes = _safe_read_bytes(stored_result.get("local_thumbnail_sheet_path"))
    if thumbnail_bytes is not None:
        st.markdown("**Thumbnail sheet**")
        st.image(thumbnail_bytes)

    metadata_text = _safe_read_text(Path(str(stored_result.get("local_artifact_dir") or "")) / "metadata.json")
    if metadata_text is not None:
        with st.expander("View export metadata", expanded=False):
            st.json(json.loads(metadata_text))
