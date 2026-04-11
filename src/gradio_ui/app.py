from __future__ import annotations

from pathlib import Path
from typing import Any

import gradio as gr

from src.app.product_bootstrap import ProductBootstrap
from src.product.models import ProductWorkflowRequest, ProductWorkflowResult
from src.product.presenters import build_product_result_sections
from src.product.service import (
    build_grounding_preview,
    generate_product_workflow_deck,
    index_loaded_documents,
    list_product_documents,
    run_product_workflow,
)
from src.providers.registry import filter_registry_by_capability
from src.rag.loaders import load_document

from .components import (
    build_artifact_panel_html,
    build_contract_snapshot_html,
    build_credibility_band_html,
    build_document_status_html,
    build_grounding_preview_html,
    build_hero_html,
    build_result_panels_html,
    build_result_summary_html,
    build_step_header_html,
    build_topbar_html,
    build_workflow_button_text,
    build_workflow_detail_html,
)
from .state import ProductSessionState, create_initial_product_state, update_product_state
from .theme import build_product_css


class _UploadAdapter:
    def __init__(self, *, name: str, content: bytes):
        self.name = name
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


def _coerce_uploaded_files(upload_value: Any) -> list[_UploadAdapter]:
    if not upload_value:
        return []
    items = upload_value if isinstance(upload_value, list) else [upload_value]
    normalized: list[_UploadAdapter] = []
    for item in items:
        if isinstance(item, bytes):
            normalized.append(_UploadAdapter(name="upload.bin", content=item))
            continue
        if isinstance(item, str):
            path = Path(item)
            if path.exists() and path.is_file():
                normalized.append(_UploadAdapter(name=path.name, content=path.read_bytes()))
                continue
        if isinstance(item, dict):
            path_value = item.get("path") or item.get("name")
            if isinstance(path_value, str):
                path = Path(path_value)
                if path.exists() and path.is_file():
                    normalized.append(_UploadAdapter(name=path.name, content=path.read_bytes()))
                    continue
        if hasattr(item, "name") and hasattr(item, "read"):
            raw = item.read()
            normalized.append(_UploadAdapter(name=Path(str(item.name)).name, content=raw if isinstance(raw, bytes) else bytes(raw)))
            continue
    return normalized


def _document_rows(documents: list[Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for document in documents:
        if hasattr(document, "model_dump"):
            data = document.model_dump(mode="json")
        elif isinstance(document, dict):
            data = document
        else:
            continue
        rows.append(
            [
                str(data.get("name") or "document"),
                str(data.get("file_type") or "-"),
                str(data.get("chunk_count") or 0),
                str(data.get("char_count") or 0),
                str(data.get("loader_strategy_label") or "-") or "-",
            ]
        )
    return rows


def _document_choices(documents: list[Any]) -> tuple[list[str], list[str]]:
    labels: list[str] = []
    values: list[str] = []
    for document in documents:
        if hasattr(document, "model_dump"):
            data = document.model_dump(mode="json")
        elif isinstance(document, dict):
            data = document
        else:
            continue
        document_id = str(data.get("document_id") or "")
        if not document_id:
            continue
        values.append(document_id)
        labels.append(f"{data.get('name')} ({data.get('file_type') or 'file'})")
    return values, labels


def _document_choice_pairs(documents: list[Any]) -> list[tuple[str, str]]:
    values, labels = _document_choices(documents)
    return list(zip(labels, values))


def _document_status_stats(documents: list[Any]) -> list[str]:
    total_documents = 0
    total_chunks = 0
    total_chars = 0
    for document in documents:
        if hasattr(document, "model_dump"):
            data = document.model_dump(mode="json")
        elif isinstance(document, dict):
            data = document
        else:
            continue
        total_documents += 1
        total_chunks += int(data.get("chunk_count") or 0)
        total_chars += int(data.get("char_count") or 0)
    stats = [f"{total_documents} document(s) ready"]
    if total_chunks:
        stats.append(f"{total_chunks} indexed chunks")
    if total_chars:
        stats.append(f"{total_chars:,} chars of source text")
    return stats


def _run_preset_hint_html(message: str) -> str:
    return f'<div class="product-inline-help">{message}</div>'


def _result_tables(sections: dict[str, Any]) -> tuple[str, list[list[str]], str, list[list[str]], list[list[str]]]:
    tables = sections.get("tables") if isinstance(sections.get("tables"), list) else []
    primary_title = str(tables[0].get("title") or "Top findings") if len(tables) >= 1 and isinstance(tables[0], dict) else "Top findings"
    primary_rows = tables[0].get("rows") if len(tables) >= 1 and isinstance(tables[0], dict) and isinstance(tables[0].get("rows"), list) else []
    secondary_title = str(tables[1].get("title") or "Actions and details") if len(tables) >= 2 and isinstance(tables[1], dict) else "Actions and details"
    secondary_rows = tables[1].get("rows") if len(tables) >= 2 and isinstance(tables[1], dict) and isinstance(tables[1].get("rows"), list) else []
    source_rows = sections.get("sources") if isinstance(sections.get("sources"), list) else []
    return primary_title, primary_rows, secondary_title, secondary_rows, source_rows


def _result_artifact_paths(result: ProductWorkflowResult | None) -> list[str]:
    if result is None:
        return []
    paths: list[str] = []
    for artifact in result.artifacts:
        if artifact.available and artifact.path:
            paths.append(artifact.path)
    return paths


def _workflow_contract_entry(frontend_contract: dict[str, Any], workflow_id: str) -> dict[str, Any]:
    workflows = frontend_contract.get("workflows") if isinstance(frontend_contract, dict) else []
    for item in workflows if isinstance(workflows, list) else []:
        if isinstance(item, dict) and str(item.get("workflow_id") or "") == workflow_id:
            return item
    return {}


def _deck_button_label(definition: Any) -> str:
    if not hasattr(definition, "default_export_label") and not hasattr(definition, "default_export_kind"):
        return "Generate executive deck"
    label = getattr(definition, "default_export_label", None) or getattr(definition, "default_export_kind", None)
    return f"Generate {label}" if label else "Generate executive deck"


def build_gradio_product_app(bootstrap: ProductBootstrap):
    workflow_catalog = bootstrap.workflow_catalog
    default_workflow = bootstrap.product_settings.default_workflow
    if default_workflow not in workflow_catalog:
        default_workflow = next(iter(workflow_catalog))
    initial_documents = list_product_documents(bootstrap.rag_settings)
    initial_doc_values, initial_doc_labels = _document_choices(initial_documents)
    initial_doc_pairs = _document_choice_pairs(initial_documents)
    initial_definition = workflow_catalog[default_workflow]
    initial_state = update_product_state(
        create_initial_product_state(default_workflow),  # type: ignore[arg-type]
        indexed_document_ids=list(initial_doc_values),
    )
    raw_frontend_contract = getattr(bootstrap, "workflow_frontend_contract", {})
    frontend_contract = raw_frontend_contract if isinstance(raw_frontend_contract, dict) else {}
    initial_workflow_contract = _workflow_contract_entry(frontend_contract, default_workflow)
    chat_registry = filter_registry_by_capability(bootstrap.provider_registry, "chat")
    provider_choices = list(chat_registry.keys()) or ["ollama"]
    default_provider = provider_choices[0]
    model_map = {
        provider_key: (
            provider_data["instance"].list_available_models()
            if isinstance(provider_data, dict) and provider_data.get("instance") is not None and hasattr(provider_data["instance"], "list_available_models")
            else []
        )
        for provider_key, provider_data in chat_registry.items()
    }
    default_models = {provider: (models[0] if models else "") for provider, models in model_map.items()}
    initial_document_stats = _document_status_stats(initial_documents)

    def _workflow_button_updates(active_workflow: str) -> list[dict[str, Any]]:
        return [
            gr.update(
                value=build_workflow_button_text(definition, active=(workflow_id == active_workflow)),
                variant="primary" if workflow_id == active_workflow else "secondary",
            )
            for workflow_id, definition in workflow_catalog.items()
        ]

    def _workflow_state_transition(workflow_id: str, state: ProductSessionState, selected_document_ids: list[str]):
        definition = workflow_catalog[str(workflow_id)]
        normalized_document_ids = list(selected_document_ids or getattr(state, "indexed_document_ids", []) or [])
        updated_state = update_product_state(
            state,
            selected_workflow=workflow_id,
            indexed_document_ids=normalized_document_ids,
            last_error=None,
        )
        return (
            updated_state,
            *_workflow_button_updates(workflow_id),
            build_workflow_detail_html(definition, selected_documents=len(normalized_document_ids)),
            gr.update(placeholder=definition.input_placeholder or "Add workflow instructions for the selected flow."),
            gr.update(value=definition.preferred_context_strategy),
            build_contract_snapshot_html(_workflow_contract_entry(frontend_contract, workflow_id)),
            _workflow_contract_entry(frontend_contract, workflow_id),
            gr.update(value=_deck_button_label(definition), interactive=False),
            gr.update(value="Workflow default"),
            _run_preset_hint_html("Workflow default keeps the recommended evidence mode and automatic context sizing for most runs."),
            gr.update(value="auto"),
            gr.update(value=16384, visible=False),
            gr.update(value=0.2),
        )

    def _update_model_dropdown(provider_key: str):
        models = model_map.get(provider_key, [])
        return gr.update(choices=models, value=models[0] if models else "")

    def _update_context_window_visibility(mode: str, current_value: int):
        return gr.update(visible=(str(mode or "auto") == "manual"), value=current_value)

    def _apply_run_preset(preset_key: str, state: ProductSessionState):
        workflow_id = state.selected_workflow if isinstance(state, ProductSessionState) else default_workflow
        definition = workflow_catalog[str(workflow_id)]
        normalized = str(preset_key or "Workflow default")
        if normalized == "Evidence-first":
            mode = "manual"
            context_value = 24576
            strategy = "document_scan"
            temperature = 0.1
            hint = "Evidence-first keeps a conservative temperature and expands manual context for higher-confidence grounded review."
        elif normalized == "Broader synthesis":
            mode = "manual"
            context_value = 28672
            strategy = "retrieval"
            temperature = 0.3
            hint = "Broader synthesis opens more room for wider context and slightly more generative synthesis when you need a fuller executive narrative."
        else:
            mode = "auto"
            context_value = 16384
            strategy = definition.preferred_context_strategy
            temperature = 0.2
            hint = "Workflow default keeps the recommended evidence mode and automatic context sizing for most runs."
        return (
            gr.update(value=mode),
            gr.update(value=context_value, visible=(mode == "manual")),
            gr.update(value=strategy),
            gr.update(value=temperature),
            _run_preset_hint_html(hint),
        )

    def _index_documents(upload_value: Any, state: ProductSessionState):
        uploads = _coerce_uploaded_files(upload_value)
        current_workflow = state.selected_workflow if isinstance(state, ProductSessionState) else default_workflow
        current_definition = workflow_catalog[str(current_workflow)]
        if not uploads:
            return (
                build_document_status_html(
                    title="Document scope ready",
                    body="Upload files to refresh the corpus, or keep the currently indexed documents selected for this run.",
                    stats=initial_document_stats,
                    tone="ready",
                ),
                _document_rows(initial_documents),
                gr.update(choices=initial_doc_pairs, value=initial_doc_values),
                build_workflow_detail_html(current_definition, selected_documents=len(initial_doc_values)),
                state,
            )
        loaded_documents = [load_document(uploaded, bootstrap.rag_settings) for uploaded in uploads[: bootstrap.product_settings.max_upload_files]]
        indexed_documents, index_status = index_loaded_documents(
            loaded_documents,
            rag_settings=bootstrap.rag_settings,
            provider_registry=bootstrap.provider_registry,
        )
        document_values, document_labels = _document_choices(indexed_documents)
        document_pairs = _document_choice_pairs(indexed_documents)
        updated_state = update_product_state(
            state,
            indexed_document_ids=document_values,
            last_error=None,
        )
        summary_html = build_document_status_html(
            title="Documents ready",
            body=str(index_status.get("message") or "The uploaded files were indexed successfully and are now available for this workflow."),
            stats=_document_status_stats(indexed_documents),
            tone="ready",
        )
        return (
            summary_html,
            _document_rows(indexed_documents),
            gr.update(choices=document_pairs, value=document_values),
            build_workflow_detail_html(current_definition, selected_documents=len(document_values)),
            updated_state,
        )

    def _document_selection_changed(state: ProductSessionState, document_ids: list[str]):
        current_workflow = state.selected_workflow if isinstance(state, ProductSessionState) else default_workflow
        definition = workflow_catalog[str(current_workflow)]
        updated_state = update_product_state(state, indexed_document_ids=list(document_ids or []), last_error=None)
        return updated_state, build_workflow_detail_html(definition, selected_documents=len(document_ids or []))

    def _preview_grounding(state: ProductSessionState, document_ids: list[str], input_text: str, strategy: str):
        workflow_id = state.selected_workflow if isinstance(state, ProductSessionState) else default_workflow
        definition = workflow_catalog[str(workflow_id)]
        effective_input = input_text.strip()
        preview = build_grounding_preview(
            query=effective_input or definition.headline,
            document_ids=list(document_ids or []),
            strategy=strategy,
        )
        return build_grounding_preview_html(preview), preview.preview_text

    def _run_workflow(
        state: ProductSessionState,
        document_ids: list[str],
        input_text: str,
        provider: str,
        model: str,
        temperature: float,
        context_window_mode: str,
        context_window: int,
        strategy: str,
    ):
        current_workflow = state.selected_workflow if isinstance(state, ProductSessionState) else default_workflow
        request = ProductWorkflowRequest(
            workflow_id=current_workflow,
            document_ids=list(document_ids or []),
            input_text=input_text,
            provider=provider or default_provider,
            model=model or default_models.get(provider or default_provider),
            temperature=float(temperature),
            context_window_mode=context_window_mode,
            context_window=int(context_window) if context_window_mode == "manual" else None,
            use_document_context=bool(document_ids),
            context_strategy=strategy,
        )
        result = run_product_workflow(request)
        sections = build_product_result_sections(result)
        primary_title, primary_rows, secondary_title, secondary_rows, source_rows = _result_tables(sections)
        updated_state = update_product_state(state, latest_result=result, latest_deck_result=None, last_error=None)
        return (
            build_result_summary_html(result),
            build_result_panels_html(result),
            primary_title,
            primary_rows,
            secondary_title,
            secondary_rows,
            build_grounding_preview_html(result.grounding_preview),
            result.grounding_preview.preview_text if result.grounding_preview is not None else "",
            source_rows,
            build_artifact_panel_html(result),
            _result_artifact_paths(result),
            gr.update(interactive=bootstrap.product_settings.enable_deck_generation),
            updated_state,
        )

    def _generate_deck(state: ProductSessionState):
        result = state.latest_result if isinstance(state, ProductSessionState) else None
        if result is None:
            return {"status": "idle", "message": "Run a workflow before generating a deck."}, [], state
        export_result, artifacts = generate_product_workflow_deck(
            result,
            settings=bootstrap.presentation_export_settings,
            workspace_root=bootstrap.workspace_root,
        )
        updated_result = result.model_copy(update={"artifacts": artifacts})
        updated_state = update_product_state(
            state,
            latest_result=updated_result,
            latest_deck_result=export_result,
            last_error=None,
        )
        return export_result, build_artifact_panel_html(updated_result, export_result), [artifact.path for artifact in artifacts if artifact.path], updated_state

    with gr.Blocks(title=bootstrap.product_settings.app_name) as app:
        gr.HTML(f"<style>{build_product_css(bootstrap.product_settings.accent_color)}</style>")
        workflow_state = gr.State(initial_state)
        gr.HTML(build_topbar_html(app_name=bootstrap.product_settings.app_name, show_ai_lab_entry=bootstrap.product_settings.show_ai_lab_entry))
        gr.HTML(build_hero_html())
        with gr.Row(equal_height=False, elem_classes="product-main-grid"):
            with gr.Column(scale=6, elem_classes="product-setup-rail"):
                gr.HTML(
                    build_step_header_html(
                        step="Workflow setup",
                        title="Choose the workflow and scope the evidence",
                        body="Pick the decision path, refresh the corpus when needed and keep only the documents that should support this run.",
                    )
                )
                with gr.Row(equal_height=True, elem_classes="product-workflow-selector-grid"):
                    workflow_buttons = []
                    for workflow_id, definition in workflow_catalog.items():
                        workflow_buttons.append(
                            gr.Button(
                                build_workflow_button_text(definition, active=(workflow_id == default_workflow)),
                                variant="primary" if workflow_id == default_workflow else "secondary",
                                elem_classes="product-workflow-button",
                            )
                        )

                workflow_detail = gr.HTML(build_workflow_detail_html(workflow_catalog[default_workflow], selected_documents=len(initial_doc_values)))
                gr.HTML(
                    build_step_header_html(
                        step="Step 1",
                        title="Add and scope documents",
                        body="Use the dropzone to refresh the corpus and keep the run focused on the exact documents you want to ground.",
                    )
                )
                ingestion_status = gr.HTML(
                    build_document_status_html(
                        title="Corpus ready for review",
                        body="Upload documents only when you need to refresh the shared corpus. Otherwise, continue with the indexed documents already available.",
                        stats=initial_document_stats,
                        tone="ready",
                    )
                )
                upload_input = gr.File(label="Upload and refresh corpus", file_count="multiple", type="filepath", elem_classes="product-upload-dropzone")
                with gr.Row(elem_classes="product-action-row"):
                    index_button = gr.Button("Refresh document scope", variant="secondary")
                document_selector = gr.CheckboxGroup(
                    choices=initial_doc_pairs,
                    value=initial_doc_values,
                    label="Documents in scope",
                    elem_classes="product-document-selector",
                )
                with gr.Accordion("Corpus snapshot", open=False):
                    document_table = gr.Dataframe(
                        value=_document_rows(initial_documents),
                        headers=["Name", "Type", "Chunks", "Chars", "Loader"],
                        label="Indexed documents",
                        interactive=False,
                    )
                gr.HTML(
                    build_step_header_html(
                        step="Step 2",
                        title="Frame the request",
                        body="Add the business context for this run and open the advanced run configuration only when you need more control.",
                    )
                )
                input_text = gr.Textbox(
                    label="Decision instructions",
                    lines=8,
                    placeholder=initial_definition.input_placeholder or "Add business context, comparison criteria, hiring signals or review instructions.",
                    elem_classes="product-instruction-box",
                )
                with gr.Accordion("Run configuration", open=False):
                    run_preset_dropdown = gr.Dropdown(
                        label="Run preset",
                        choices=["Workflow default", "Evidence-first", "Broader synthesis"],
                        value="Workflow default",
                    )
                    run_preset_hint = gr.HTML(
                        _run_preset_hint_html(
                            "Workflow default keeps the recommended evidence mode and automatic context sizing for most runs."
                        )
                    )
                    provider_dropdown = gr.Dropdown(label="AI provider", choices=provider_choices, value=default_provider)
                    model_dropdown = gr.Dropdown(label="AI model", choices=model_map.get(default_provider, []), value=default_models.get(default_provider, ""))
                    temperature_slider = gr.Slider(label="Temperature", minimum=0.0, maximum=1.2, step=0.1, value=0.2)
                    context_mode = gr.Dropdown(label="Context mode", choices=["auto", "manual"], value="auto")
                    context_window = gr.Slider(label="Manual context size", minimum=1024, maximum=65536, step=512, value=16384, visible=False)
                    strategy_dropdown = gr.Dropdown(
                        label="Evidence mode",
                        choices=["document_scan", "retrieval"],
                        value=initial_definition.preferred_context_strategy,
                    )
                with gr.Row(elem_classes="product-primary-actions"):
                    preview_button = gr.Button("Preview evidence")
                    run_button = gr.Button("Run workflow", variant="primary")
                    deck_button = gr.Button(
                        _deck_button_label(initial_definition),
                        variant="secondary",
                        visible=bootstrap.product_settings.enable_deck_generation,
                        interactive=False,
                    )
            with gr.Column(scale=7, elem_classes="product-insight-canvas"):
                gr.HTML(
                    build_step_header_html(
                        step="Decision review",
                        title="Review the recommendation, evidence and handoff",
                        body="Start with the executive outcome, then drill into evidence, tables, deliverables and workflow contract only when needed.",
                    )
                )
                result_summary = gr.HTML(build_result_summary_html(None))
                result_panels = gr.HTML(build_result_panels_html(None))
                with gr.Tabs():
                    with gr.Tab("Decision tables"):
                        primary_table_title = gr.Markdown("### Top findings")
                        primary_table = gr.Dataframe(headers=["Col 1", "Col 2", "Col 3", "Col 4"], interactive=False)
                        secondary_table_title = gr.Markdown("### Actions and details")
                        secondary_table = gr.Dataframe(headers=["Col 1", "Col 2", "Col 3", "Col 4"], interactive=False)
                    with gr.Tab("Evidence"):
                        grounding_summary = gr.HTML('<div class="product-empty-state">Evidence preview will appear here before execution.</div>')
                        grounding_preview_text = gr.Textbox(label="Evidence context preview", lines=12, interactive=False)
                        sources_table = gr.Dataframe(headers=["Source", "Chunk", "Score", "Snippet"], label="Evidence table", interactive=False)
                    with gr.Tab("Deliverables"):
                        artifact_summary = gr.HTML(build_artifact_panel_html(None))
                        artifact_files = gr.File(label="Deliverables", file_count="multiple")
                        deck_status = gr.JSON(label="Export status")
                    with gr.Tab("Workflow contract"):
                        workflow_contract_html = gr.HTML(build_contract_snapshot_html(initial_workflow_contract))
                        workflow_contract_json = gr.JSON(label="Technical contract JSON", value=initial_workflow_contract)

        gr.HTML(build_credibility_band_html())

        for button, workflow_id in zip(workflow_buttons, workflow_catalog.keys()):
            button.click(
                fn=lambda state, selected_document_ids, selected=workflow_id: _workflow_state_transition(selected, state, selected_document_ids),
                inputs=[workflow_state, document_selector],
                outputs=[
                    workflow_state,
                    *workflow_buttons,
                    workflow_detail,
                    input_text,
                    strategy_dropdown,
                    workflow_contract_html,
                    workflow_contract_json,
                    deck_button,
                    run_preset_dropdown,
                    run_preset_hint,
                    context_mode,
                    context_window,
                    temperature_slider,
                ],
            )

        provider_dropdown.change(
            fn=_update_model_dropdown,
            inputs=[provider_dropdown],
            outputs=[model_dropdown],
        )

        run_preset_dropdown.change(
            fn=_apply_run_preset,
            inputs=[run_preset_dropdown, workflow_state],
            outputs=[context_mode, context_window, strategy_dropdown, temperature_slider, run_preset_hint],
        )

        context_mode.change(
            fn=_update_context_window_visibility,
            inputs=[context_mode, context_window],
            outputs=[context_window],
        )

        index_button.click(
            fn=_index_documents,
            inputs=[upload_input, workflow_state],
            outputs=[ingestion_status, document_table, document_selector, workflow_detail, workflow_state],
        )

        document_selector.change(
            fn=_document_selection_changed,
            inputs=[workflow_state, document_selector],
            outputs=[workflow_state, workflow_detail],
        )

        preview_button.click(
            fn=_preview_grounding,
            inputs=[workflow_state, document_selector, input_text, strategy_dropdown],
            outputs=[grounding_summary, grounding_preview_text],
        )

        run_button.click(
            fn=_run_workflow,
            inputs=[workflow_state, document_selector, input_text, provider_dropdown, model_dropdown, temperature_slider, context_mode, context_window, strategy_dropdown],
            outputs=[
                result_summary,
                result_panels,
                primary_table_title,
                primary_table,
                secondary_table_title,
                secondary_table,
                grounding_summary,
                grounding_preview_text,
                sources_table,
                artifact_summary,
                artifact_files,
                deck_button,
                workflow_state,
            ],
        )

        deck_button.click(
            fn=_generate_deck,
            inputs=[workflow_state],
            outputs=[deck_status, artifact_summary, artifact_files, workflow_state],
        )

    return app