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
    build_credibility_band_html,
    build_grounding_preview_html,
    build_hero_html,
    build_result_summary_html,
    build_topbar_html,
    build_workflow_cards_html,
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


def _result_tables(sections: dict[str, Any]) -> tuple[str, list[list[str]], str, list[list[str]], list[list[str]]]:
    tables = sections.get("tables") if isinstance(sections.get("tables"), list) else []
    primary_title = str(tables[0].get("title") or "Primary findings") if len(tables) >= 1 and isinstance(tables[0], dict) else "Primary findings"
    primary_rows = tables[0].get("rows") if len(tables) >= 1 and isinstance(tables[0], dict) and isinstance(tables[0].get("rows"), list) else []
    secondary_title = str(tables[1].get("title") or "Actionable details") if len(tables) >= 2 and isinstance(tables[1], dict) else "Actionable details"
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


def build_gradio_product_app(bootstrap: ProductBootstrap):
    workflow_catalog = bootstrap.workflow_catalog
    default_workflow = bootstrap.product_settings.default_workflow
    if default_workflow not in workflow_catalog:
        default_workflow = next(iter(workflow_catalog))
    initial_state = create_initial_product_state(default_workflow)  # type: ignore[arg-type]
    initial_documents = list_product_documents(bootstrap.rag_settings)
    initial_doc_values, initial_doc_labels = _document_choices(initial_documents)
    initial_doc_pairs = _document_choice_pairs(initial_documents)
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

    def _workflow_state_transition(workflow_id: str, state: ProductSessionState):
        definition = workflow_catalog[str(workflow_id)]
        updated_state = update_product_state(state, selected_workflow=workflow_id, last_error=None)
        return (
            updated_state,
            build_workflow_cards_html(workflow_catalog, active_workflow=workflow_id),
            build_workflow_detail_html(definition, selected_documents=len(updated_state.indexed_document_ids)),
        )

    def _update_model_dropdown(provider_key: str):
        models = model_map.get(provider_key, [])
        return gr.update(choices=models, value=models[0] if models else "")

    def _index_documents(upload_value: Any, state: ProductSessionState):
        uploads = _coerce_uploaded_files(upload_value)
        if not uploads:
            return (
                build_result_summary_html(None),
                _document_rows(initial_documents),
                gr.update(choices=initial_doc_labels, value=initial_doc_values),
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
        summary_html = f'<div class="product-panel"><div class="product-section-title">Documents indexed</div><div class="product-section-subtitle">{index_status.get("message")}</div></div>'
        return (
            summary_html,
            _document_rows(indexed_documents),
            gr.update(choices=document_pairs, value=document_values),
            updated_state,
        )

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
            "\n".join(f"- {item}" for item in sections.get("highlights") or []) or "- No highlights captured yet.",
            "\n".join(f"- {item}" for item in sections.get("warnings") or []) or "- No active warning.",
            primary_title,
            primary_rows,
            secondary_title,
            secondary_rows,
            source_rows,
            _result_artifact_paths(result),
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
        return export_result, [artifact.path for artifact in artifacts if artifact.path], updated_state

    with gr.Blocks(title=bootstrap.product_settings.app_name) as app:
        gr.HTML(f"<style>{build_product_css(bootstrap.product_settings.accent_color)}</style>")
        workflow_state = gr.State(initial_state)
        gr.HTML(build_topbar_html(app_name=bootstrap.product_settings.app_name, show_ai_lab_entry=bootstrap.product_settings.show_ai_lab_entry))
        gr.HTML(build_hero_html())

        workflow_cards = gr.HTML(build_workflow_cards_html(workflow_catalog, active_workflow=default_workflow))
        workflow_detail = gr.HTML(build_workflow_detail_html(workflow_catalog[default_workflow], selected_documents=len(initial_doc_values)))

        with gr.Row(equal_height=True):
            workflow_buttons = []
            for workflow_id, definition in workflow_catalog.items():
                workflow_buttons.append(gr.Button(definition.label))

        with gr.Row():
            with gr.Column(scale=8):
                ingestion_status = gr.HTML('<div class="product-empty-state">Index documents to create the shared product corpus.</div>')
                document_table = gr.Dataframe(
                    value=_document_rows(initial_documents),
                    headers=["Name", "Type", "Chunks", "Chars", "Loader"],
                    label="Indexed document base",
                    interactive=False,
                )
                upload_input = gr.File(label="Add documents", file_count="multiple", type="filepath")
                index_button = gr.Button("Index / refresh uploaded documents", variant="primary")
                document_selector = gr.CheckboxGroup(
                    choices=initial_doc_pairs,
                    value=initial_doc_values,
                    label="Documents available for the current workflow",
                )
                input_text = gr.Textbox(
                    label="Workflow instructions (optional)",
                    lines=6,
                    placeholder="Add business context, comparison criteria, hiring signals or review instructions.",
                )
                with gr.Accordion("Advanced runtime", open=False):
                    provider_dropdown = gr.Dropdown(label="Generation provider", choices=provider_choices, value=default_provider)
                    model_dropdown = gr.Dropdown(label="Generation model", choices=model_map.get(default_provider, []), value=default_models.get(default_provider, ""))
                    temperature_slider = gr.Slider(label="Temperature", minimum=0.0, maximum=1.2, step=0.1, value=0.2)
                    context_mode = gr.Dropdown(label="Context window mode", choices=["auto", "manual"], value="auto")
                    context_window = gr.Slider(label="Manual context window", minimum=1024, maximum=65536, step=512, value=16384)
                    strategy_dropdown = gr.Dropdown(label="Grounding strategy", choices=["document_scan", "retrieval"], value="document_scan")
                with gr.Row():
                    preview_button = gr.Button("Preview grounding")
                    run_button = gr.Button("Run workflow", variant="primary")
                    deck_button = gr.Button(
                        "Generate executive deck",
                        variant="secondary",
                        visible=bootstrap.product_settings.enable_deck_generation,
                    )
            with gr.Column(scale=7):
                grounding_summary = gr.HTML('<div class="product-empty-state">Grounding preview will appear here before execution.</div>')
                grounding_preview_text = gr.Textbox(label="Grounding preview text", lines=12, interactive=False)
                result_summary = gr.HTML(build_result_summary_html(None))
                highlights_md = gr.Markdown("- No highlights yet.")
                warnings_md = gr.Markdown("- No active warning.")
                primary_table_title = gr.Markdown("### Primary findings")
                primary_table = gr.Dataframe(headers=["Col 1", "Col 2", "Col 3", "Col 4"], interactive=False)
                secondary_table_title = gr.Markdown("### Actionable details")
                secondary_table = gr.Dataframe(headers=["Col 1", "Col 2", "Col 3", "Col 4"], interactive=False)
                sources_table = gr.Dataframe(headers=["Source", "Chunk", "Score", "Snippet"], label="Grounded evidence", interactive=False)
                artifact_files = gr.File(label="Artifacts", file_count="multiple")
                deck_status = gr.JSON(label="Deck export status")

        gr.HTML(build_credibility_band_html())

        for button, workflow_id in zip(workflow_buttons, workflow_catalog.keys()):
            button.click(
                fn=lambda state, selected=workflow_id: _workflow_state_transition(selected, state),
                inputs=[workflow_state],
                outputs=[workflow_state, workflow_cards, workflow_detail],
            )

        provider_dropdown.change(
            fn=_update_model_dropdown,
            inputs=[provider_dropdown],
            outputs=[model_dropdown],
        )

        index_button.click(
            fn=_index_documents,
            inputs=[upload_input, workflow_state],
            outputs=[ingestion_status, document_table, document_selector, workflow_state],
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
                highlights_md,
                warnings_md,
                primary_table_title,
                primary_table,
                secondary_table_title,
                secondary_table,
                sources_table,
                artifact_files,
                workflow_state,
            ],
        )

        deck_button.click(
            fn=_generate_deck,
            inputs=[workflow_state],
            outputs=[deck_status, artifact_files, workflow_state],
        )

    return app