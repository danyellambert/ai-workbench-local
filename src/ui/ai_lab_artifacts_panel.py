from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

import streamlit as st

from .ai_lab_common import build_selectbox_options, compact_rows, compact_text, render_bar_chart_from_rows, render_labeled_value_grid, render_panel_header, render_status_badges
from .ai_lab_benchmarks_panel import render_retrieval_embedding_experiments_panel
from .ai_lab_runtime_panel import render_runtime_observability_diagnostics


def _safe_read_text(path: Path, *, max_chars: int = 24000) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as error:  # pragma: no cover - defensive UI helper
        return f"Could not read file: {error}"
    if len(content) <= max_chars:
        return content
    return content[:max_chars].rstrip() + "\n\n...[truncated]"


def _relative_to_workspace(path: Path, workspace_root: Path) -> str:
    try:
        return str(path.relative_to(workspace_root))
    except Exception:
        return str(path)


def _format_modified_at(path: Path) -> str:
    if not path.exists():
        return "n/a"
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")


def _build_artifact_preview_summary(path: Path) -> dict[str, Any]:
    summary = {
        "relative_path": str(path),
        "suffix": path.suffix.lower(),
        "modified_at": _format_modified_at(path),
        "size_kb": round((path.stat().st_size if path.exists() else 0) / 1024, 1),
    }
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(_safe_read_text(path, max_chars=24000))
            if isinstance(payload, dict):
                summary["json_type"] = "object"
                summary["top_level_keys"] = list(payload.keys())[:10]
            elif isinstance(payload, list):
                summary["json_type"] = "array"
                summary["items"] = len(payload)
        except Exception:
            summary["json_type"] = "invalid_or_truncated"
    return summary


def _artifact_group_metadata() -> dict[str, dict[str, str]]:
    return {
        "Relatórios da Fase 5": {
            "category": "structured_outputs",
            "surface": "Workflow / Structured + Runtime",
            "why": "Explica parsing estruturado, OCR-first/VL-on-demand e evidence_cv.",
        },
        "Configurações e fixtures da Fase 8": {
            "category": "evals",
            "surface": "Evals & Diagnóstico",
            "why": "Explica suites, fixtures e critérios da disciplina de qualidade.",
        },
        "Logs operacionais do AI Lab": {
            "category": "runtime_ops",
            "surface": "Runtime / Workflow / MCP",
            "why": "Explica execuções reais, tracing, logs locais e operações do lab.",
        },
        "Snapshots de benchmark": {
            "category": "benchmark",
            "surface": "Benchmarks & Comparação de Modelos",
            "why": "Explica decisões de provider/modelo/runtime/quantização.",
        },
        "Documentação da Fase 10.25": {
            "category": "roadmap",
            "surface": "Shell / Governança do AI Lab",
            "why": "Explica o racional arquitetural e a evolução da superfície.",
        },
    }


def _build_artifact_registry_rows(groups: dict[str, list[Path]], workspace_root: Path) -> list[dict[str, Any]]:
    metadata = _artifact_group_metadata()
    rows: list[dict[str, Any]] = []
    for group_name, paths in groups.items():
        if not paths:
            continue
        latest_path = max(
            [path for path in paths if path.exists()],
            key=lambda item: item.stat().st_mtime,
            default=None,
        )
        group_meta = metadata.get(group_name, {})
        rows.append(
            {
                "group": group_name,
                "category": group_meta.get("category", "general"),
                "surface": group_meta.get("surface", "AI Lab"),
                "artifacts": len(paths),
                "latest_artifact": _relative_to_workspace(latest_path, workspace_root) if latest_path else "n/a",
                "updated_at": _format_modified_at(latest_path) if latest_path else "n/a",
                "why_it_matters": group_meta.get("why", "Operational evidence registry."),
            }
        )
    return rows


def _build_artifact_group_distribution_rows(groups: dict[str, list[Path]]) -> list[dict[str, Any]]:
    return [
        {"group": group_name, "artifacts": len(paths)}
        for group_name, paths in groups.items()
        if paths
    ]


def _build_registry_table_rows(registry_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in registry_rows:
        rows.append(
            {
                "grupo": compact_text(row.get("group"), max_chars=32),
                "categoria": compact_text(row.get("category"), max_chars=24),
                "artefatos": int(row.get("artifacts") or 0),
                "atualizado": str(row.get("updated_at") or "n/a"),
            }
        )
    return rows


def _discover_artifact_groups(workspace_root: Path) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}

    def _collect(label: str, patterns: list[str], *, limit: int = 30) -> None:
        collected: list[Path] = []
        seen: set[Path] = set()
        for pattern in patterns:
            for candidate in workspace_root.glob(pattern):
                if candidate.is_file() and candidate not in seen:
                    collected.append(candidate)
                    seen.add(candidate)
        collected.sort(key=lambda item: item.stat().st_mtime if item.exists() else 0.0, reverse=True)
        groups[label] = collected[:limit]

    _collect("Relatórios da Fase 5", ["phase5_eval/reports/*.json"], limit=40)
    _collect("Configurações e fixtures da Fase 8", ["phase8_eval/configs/*.json", "phase8_eval/fixtures/*.json"], limit=30)
    _collect(
        "Logs operacionais do AI Lab",
        [
            ".phase55_langchain_shadow_log.json",
            ".phase55_langgraph_shadow_log.json",
            ".phase6_document_agent_log.json",
            ".phase7_model_comparison_log.json",
            ".phase95_evidenceops_worklog.json",
            ".runtime_execution_log.json",
        ],
        limit=30,
    )
    _collect(
        "Snapshots de benchmark",
        [
            "benchmark_runs/**/aggregated/latest_case_results.json",
            "benchmark_runs/**/environment_snapshot.json",
            "benchmark_runs/**/manifest.resolved.json",
        ],
        limit=40,
    )
    _collect(
        "Documentação da Fase 10.25",
        [
            "docs/architecture/executive-deck-generation/*.md",
        ],
        limit=30,
    )
    return groups


def render_report_explorer_panel(*, workspace_root: Path) -> None:
    render_panel_header(
        "Explorador de artefatos",
        "Esta guia transforma artefatos antes dispersos em `phase5_eval/`, `phase8_eval/`, `benchmark_runs/` e logs locais do AI Lab em uma leitura navegável de engenharia.",
    )

    groups = _discover_artifact_groups(workspace_root)
    available_groups = [label for label, paths in groups.items() if paths]
    if not available_groups:
        st.info("Nenhum artefato local foi encontrado nas trilhas monitoradas do AI Lab.")
        return

    total_artifacts = sum(len(groups.get(group_name, [])) for group_name in available_groups)
    latest_artifact = max(
        (path for group_name in available_groups for path in groups.get(group_name, []) if path.exists()),
        key=lambda item: item.stat().st_mtime,
        default=None,
    )

    render_labeled_value_grid(
        [
            {"label": "Grupos ativos", "value": len(available_groups)},
            {"label": "Artefatos monitorados", "value": total_artifacts},
            {
                "label": "Último artefato",
                "value": _relative_to_workspace(latest_artifact, workspace_root) if latest_artifact else "n/a",
                "compact": True,
                "compact_middle": True,
                "show_full": True,
                "max_chars": 80,
            },
            {"label": "Atualizado em", "value": _format_modified_at(latest_artifact) if latest_artifact else "n/a"},
        ],
        columns=4,
    )

    registry_rows = _build_artifact_registry_rows({label: groups[label] for label in available_groups}, workspace_root)
    if registry_rows:
        render_panel_header(
            "Mapa do registro de evidências",
            "Leia os artefatos por categoria operacional e pela aba do AI Lab que eles ajudam a explicar, não apenas como arquivos soltos.",
        )
        st.dataframe(_build_registry_table_rows(registry_rows), width="stretch")
        render_bar_chart_from_rows(
            _build_artifact_group_distribution_rows({label: groups[label] for label in available_groups}),
            index_field="group",
            value_fields=["artifacts"],
            height=220,
        )

    render_panel_header(
        "Leitura resumida por grupo",
        "Cada grupo aparece com nome completo, contagem e surface principal sem depender de métricas estreitas com reticências.",
    )
    render_labeled_value_grid(
        [
            {
                "label": f"Grupo {index + 1}",
                "value": group_name,
                "detail": (
                    f"{len(groups.get(group_name, []))} artefatos · "
                    f"{_artifact_group_metadata().get(group_name, {}).get('surface', 'AI Lab')}"
                ),
                "compact": True,
                "show_full": True,
                "max_chars": 56,
            }
            for index, group_name in enumerate(available_groups[:4])
        ],
        columns=min(2, len(available_groups[:4])) or 1,
    )

    group_options = build_selectbox_options(available_groups, max_chars=54)
    selected_group_label = st.selectbox(
        "Grupo de artefatos",
        options=list(group_options.keys()),
        key="phase10_ai_lab_artifact_group",
    )
    selected_group = group_options[selected_group_label]

    group_paths = groups.get(selected_group, [])
    raw_path_labels = [_relative_to_workspace(path, workspace_root) for path in group_paths]
    path_option_labels = build_selectbox_options(raw_path_labels, max_chars=92, middle=True)
    path_lookup = {_relative_to_workspace(path, workspace_root): path for path in group_paths}
    artifact_rows = [
        {
            "arquivo": _relative_to_workspace(path, workspace_root),
            "última_modificação": _format_modified_at(path),
            "tamanho_kb": round((path.stat().st_size if path.exists() else 0) / 1024, 1),
        }
        for path in group_paths
    ]
    selected_label = st.selectbox(
        "Arquivo / artefato",
        options=list(path_option_labels.keys()),
        key="phase10_ai_lab_artifact_path",
    )
    selected_path = path_lookup[path_option_labels[selected_label]]

    render_labeled_value_grid(
        [
            {"label": "Grupo", "value": selected_group, "compact": True, "show_full": True, "max_chars": 54},
            {"label": "Última modificação", "value": _format_modified_at(selected_path)},
            {"label": "Tamanho (KB)", "value": round((selected_path.stat().st_size if selected_path.exists() else 0) / 1024, 1)},
        ],
        columns=3,
    )

    selected_group_meta = _artifact_group_metadata().get(selected_group, {})
    render_labeled_value_grid(
        [
            {"label": "Categoria operacional", "value": selected_group_meta.get("category", "general")},
            {
                "label": "Explica a aba",
                "value": selected_group_meta.get("surface", "AI Lab"),
                "compact": True,
                "show_full": True,
                "max_chars": 56,
            },
        ],
        columns=2,
    )
    render_status_badges(
        [
            (f"grupo {selected_group}", "info"),
            (f"categoria {selected_group_meta.get('category', 'general')}", "neutral"),
            (f"surface {selected_group_meta.get('surface', 'AI Lab')}", "info"),
            (f"suffix {selected_path.suffix.lower() or 'sem extensão'}", "neutral"),
        ]
    )
    if selected_group_meta.get("why"):
        st.info(str(selected_group_meta.get("why")))

    with st.expander("Artefatos disponíveis neste grupo", expanded=False):
        st.dataframe(
            compact_rows(
                artifact_rows[:20],
                field_limits={"arquivo": 82},
                middle_fields=["arquivo"],
            ),
            width="stretch",
        )

    preview_summary = _build_artifact_preview_summary(selected_path)
    render_panel_header(
        "Resumo do artefato selecionado",
        "Mostre o path completo e os metadados do arquivo fora da tabela para não depender de colunas estreitas.",
    )
    render_labeled_value_grid(
        [
            {
                "label": "Path completo",
                "value": preview_summary.get("relative_path") or _relative_to_workspace(selected_path, workspace_root),
                "compact": True,
                "compact_middle": True,
                "show_full": True,
                "max_chars": 98,
            },
            {"label": "Formato", "value": preview_summary.get("suffix") or selected_path.suffix.lower()},
            {"label": "Atualizado", "value": preview_summary.get("modified_at") or _format_modified_at(selected_path)},
            {"label": "Tamanho (KB)", "value": preview_summary.get("size_kb")},
            {"label": "Tipo JSON", "value": preview_summary.get("json_type", "n/a")},
            {
                "label": "Top-level keys",
                "value": ", ".join(preview_summary.get("top_level_keys") or []) or "n/a",
                "compact": True,
                "show_full": True,
                "max_chars": 84,
            },
        ],
        columns=3,
    )
    with st.expander("Preview detalhado do artefato", expanded=False):
        if selected_path.suffix.lower() == ".json":
            raw_text = _safe_read_text(selected_path)
            try:
                st.json(json.loads(raw_text))
            except Exception:
                st.code(raw_text, language="json")
        else:
            st.code(_safe_read_text(selected_path), language="text")


def render_advanced_experiments_panel(
    *,
    workspace_root: Path,
    indexed_documents: list[dict[str, Any]],
    vector_backend_status: dict[str, Any],
    embedding_compatibility: dict[str, Any],
    rag_settings: Any,
    phase55_shadow_log_summary: dict[str, Any],
    phase7_model_comparison_log_summary: dict[str, Any],
    phase8_eval_summary: dict[str, Any],
    runtime_execution_summary: dict[str, Any],
) -> None:
    render_panel_header(
        "Experimentos avançados & artefatos",
        "O Slice 10.25B expõe explicitamente OCR/VLM diagnostics, experiments de retrieval/embedding/reranking e o explorador de artefatos versionados como superfície oficial do AI Lab.",
    )

    groups = _discover_artifact_groups(workspace_root)
    available_groups = {label: paths for label, paths in groups.items() if paths}
    if available_groups:
        densest_group = max(available_groups.items(), key=lambda item: len(item[1]))[0]
        render_labeled_value_grid(
            [
                {"label": "Grupos com evidência", "value": len(available_groups)},
                {"label": "Artefatos rastreados", "value": sum(len(paths) for paths in available_groups.values())},
                {
                    "label": "Grupo mais denso",
                    "value": densest_group,
                    "compact": True,
                    "show_full": True,
                    "max_chars": 56,
                },
            ],
            columns=3,
        )

    with st.container(border=True):
        st.markdown("#### Diagnóstico de OCR / VLM / extração de PDF")
        st.caption(
            "Superfície explícita para parsing documental avançado, OCR fallback, Docling, VLM e sinais de PDF extraction observados no índice atual."
        )
        render_runtime_observability_diagnostics(
            indexed_documents=indexed_documents,
            vector_backend_status=vector_backend_status,
            embedding_compatibility=embedding_compatibility,
        )

    with st.container(border=True):
        st.markdown("#### Experimentos de embeddings / retrieval / reranking")
        st.caption(
            "Superfície explícita para strategy benchmark, compatibilidade de embedding, retrieval shadow, reranking e trilhas de benchmark já persistidas no repositório."
        )
        render_retrieval_embedding_experiments_panel(
            indexed_documents=indexed_documents,
            vector_backend_status=vector_backend_status,
            embedding_compatibility=embedding_compatibility,
            rag_settings=rag_settings,
            phase55_shadow_log_summary=phase55_shadow_log_summary,
            phase7_model_comparison_log_summary=phase7_model_comparison_log_summary,
            phase8_eval_summary=phase8_eval_summary,
            runtime_execution_summary=runtime_execution_summary,
        )

    with st.container(border=True):
        st.markdown("#### Reports & artifacts explorer")
        st.caption(
            "Explorador dos relatórios e artefatos versionados do AI Lab, incluindo `phase5_eval`, `phase8_eval`, `benchmark_runs` e logs operacionais locais. A leitura agora prioriza resumo e navegação antes do preview cru."
        )
        render_report_explorer_panel(workspace_root=workspace_root)