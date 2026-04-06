from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..storage.phase95_evidenceops_action_store import summarize_evidenceops_actions
from ..storage.phase95_evidenceops_worklog import summarize_evidenceops_worklog
from ..storage.phase7_model_comparison_log import summarize_model_comparison_log
from ..storage.phase8_eval_store import summarize_eval_runs
from ..structured.base import (
    CVAnalysisPayload,
    ChecklistPayload,
    DocumentAgentPayload,
    ExtractionPayload,
    SummaryPayload,
)
from ..structured.envelope import StructuredResult


DEFAULT_PRESENTATION_EXPORT_CONTRACT_VERSION = "presentation_export.v1"
DEFAULT_PRESENTATION_EXPORT_KIND = "benchmark_eval_executive_deck"
DEFAULT_EXECUTIVE_DECK_CONTRACT_VERSION = "executive_deck_generation.v1"
BENCHMARK_EVAL_EXECUTIVE_REVIEW_PRODUCT_EXPORT_KIND = "benchmark_eval_executive_review"
DEFAULT_PRESENTATION_THEME = "executive_premium_minimal"
DEFAULT_PRESENTATION_TITLE = "AI Workbench Local — Benchmark & Eval Review"
DEFAULT_PRESENTATION_SUBTITLE = "Resumo executivo da rodada atual"
DEFAULT_PRESENTATION_AUTHOR = "AI Workbench Local"
DEFAULT_PRESENTATION_FOOTER = "AI Workbench Local • Benchmark & Eval Review"

DOCUMENT_REVIEW_EXPORT_KIND = "document_review_deck"
POLICY_CONTRACT_COMPARISON_EXPORT_KIND = "policy_contract_comparison_deck"
ACTION_PLAN_EXPORT_KIND = "action_plan_deck"
CANDIDATE_REVIEW_EXPORT_KIND = "candidate_review_deck"
EVIDENCE_PACK_EXPORT_KIND = "evidence_pack_deck"

EXECUTIVE_DECK_EXPORT_KIND_LABELS = {
    DEFAULT_PRESENTATION_EXPORT_KIND: "Benchmark & Eval Executive Review Deck",
    DOCUMENT_REVIEW_EXPORT_KIND: "Document Review Deck",
    POLICY_CONTRACT_COMPARISON_EXPORT_KIND: "Policy / Contract Comparison Deck",
    ACTION_PLAN_EXPORT_KIND: "Action Plan Deck",
    CANDIDATE_REVIEW_EXPORT_KIND: "Candidate Review Deck",
    EVIDENCE_PACK_EXPORT_KIND: "Evidence Pack / Audit Deck",
}

SUPPORTED_EXECUTIVE_DECK_EXPORT_KINDS = list(EXECUTIVE_DECK_EXPORT_KIND_LABELS.keys())

EXECUTIVE_DECK_EXPORT_KIND_ALIASES = {
    BENCHMARK_EVAL_EXECUTIVE_REVIEW_PRODUCT_EXPORT_KIND: DEFAULT_PRESENTATION_EXPORT_KIND,
}


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(str(value).split()).strip()
    return cleaned or None


def normalize_executive_deck_export_kind(export_kind: object) -> str:
    cleaned = _clean_text(export_kind)
    if not cleaned:
        raise ValueError("Executive deck export kind is required.")
    return EXECUTIVE_DECK_EXPORT_KIND_ALIASES.get(cleaned, cleaned)


def _coerce_float(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _coerce_int(value: object) -> int:
    return int(value) if isinstance(value, (int, float)) else 0


def _format_percentage(value: float | None) -> str:
    if value is None:
        return "N/A"
    percentage = round(float(value) * 100, 1)
    return f"{int(percentage)}%" if float(percentage).is_integer() else f"{percentage:.1f}%"


def _format_ratio(value: float | None) -> str:
    if value is None:
        return "N/A"
    percentage = round(float(value) * 100, 1)
    return f"{int(percentage)}%" if float(percentage).is_integer() else f"{percentage:.1f}%"


def _format_seconds(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.2f}s"


def _format_signal(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):.3f}"


class PresentationExportMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    subtitle: str | None = None
    author: str | None = None
    date: str | None = None
    theme: str = DEFAULT_PRESENTATION_THEME
    footer_text: str | None = None


class ModelComparisonSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_runs: int = 0
    total_candidates: int = 0
    success_rate: float | None = None
    avg_latency_s: float | None = None
    avg_format_adherence: float | None = None
    avg_use_case_fit_score: float | None = None
    top_model: str | None = None
    top_runtime_bucket: str | None = None


class EvalSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_runs: int = 0
    pass_rate: float | None = None
    warn_rate: float | None = None
    fail_rate: float | None = None
    avg_score_ratio: float | None = None
    avg_latency_s: float | None = None
    needs_review_rate: float | None = None
    top_suite_name: str | None = None


class ExecutiveDeckMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    value: str
    detail: str | None = None
    trend: str | None = None


class ModelLeaderboardEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    model: str
    provider: str | None = None
    runtime_bucket: str | None = None
    comparison_score: float | None = None
    avg_latency_s: float | None = None
    format_adherence: float | None = None
    use_case_fit_score: float | None = None
    success_rate: float | None = None


class EvalSuiteLeaderboardEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    suite_name: str
    pass_rate: float | None = None
    avg_score_ratio: float | None = None
    avg_latency_s: float | None = None
    total_runs: int | None = None


class BenchmarkEvalExecutiveDeckContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal[DEFAULT_PRESENTATION_EXPORT_CONTRACT_VERSION] = (
        DEFAULT_PRESENTATION_EXPORT_CONTRACT_VERSION
    )
    export_kind: Literal[DEFAULT_PRESENTATION_EXPORT_KIND] = DEFAULT_PRESENTATION_EXPORT_KIND
    presentation: PresentationExportMetadata
    model_comparison_snapshot: ModelComparisonSnapshot
    eval_snapshot: EvalSnapshot
    executive_summary: str
    key_highlights: list[str] = Field(default_factory=list)
    key_metrics: list[ExecutiveDeckMetric] = Field(default_factory=list)
    model_leaderboard: list[ModelLeaderboardEntry] = Field(default_factory=list)
    eval_suite_leaderboard: list[EvalSuiteLeaderboardEntry] = Field(default_factory=list)
    recommendation: str
    watchouts: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)


class PptCreatorMetricItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str
    label: str
    detail: str | None = None
    trend: str | None = None


class PptCreatorComparisonColumn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    body: str | None = None
    bullets: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_content(self) -> "PptCreatorComparisonColumn":
        if not self.body and not self.bullets:
            raise ValueError("comparison column requires body or bullets")
        return self


class PptCreatorCardItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    body: str
    footer: str | None = None


class PptCreatorTimelineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    body: str | None = None
    tag: str | None = None
    footer: str | None = None


class PptCreatorPresentationMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    subtitle: str | None = None
    author: str | None = None
    date: str | None = None
    theme: str = DEFAULT_PRESENTATION_THEME
    footer_text: str | None = None


class PptCreatorSlide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["title", "summary", "metrics", "table", "comparison", "bullets", "cards", "timeline", "two_column"]
    title: str | None = None
    subtitle: str | None = None
    body: str | None = None
    bullets: list[str] = Field(default_factory=list)
    cards: list[PptCreatorCardItem] = Field(default_factory=list)
    metrics: list[PptCreatorMetricItem] = Field(default_factory=list)
    timeline_items: list[PptCreatorTimelineItem] = Field(default_factory=list)
    table_columns: list[str] = Field(default_factory=list)
    table_rows: list[list[str]] = Field(default_factory=list)
    comparison_columns: list[PptCreatorComparisonColumn] = Field(default_factory=list)
    two_column_columns: list[PptCreatorComparisonColumn] = Field(default_factory=list)
    speaker_notes: str | None = None

    @model_validator(mode="after")
    def validate_by_type(self) -> "PptCreatorSlide":
        if self.type == "title" and not self.title:
            raise ValueError("title slide requires title")
        if self.type in {"summary", "bullets"} and (not self.title or (not self.body and not self.bullets)):
            raise ValueError(f"{self.type} slide requires title and body or bullets")
        if self.type == "cards" and (not self.title or len(self.cards) != 3):
            raise ValueError("cards slide requires title and exactly 3 cards")
        if self.type == "metrics" and (not self.title or not self.metrics):
            raise ValueError("metrics slide requires title and metrics")
        if self.type == "timeline" and (not self.title or len(self.timeline_items) < 2):
            raise ValueError("timeline slide requires title and at least 2 timeline items")
        if self.type == "table" and (not self.title or len(self.table_columns) < 2 or not self.table_rows):
            raise ValueError("table slide requires title, columns and rows")
        if self.type == "comparison" and (not self.title or len(self.comparison_columns) != 2):
            raise ValueError("comparison slide requires title and exactly 2 comparison columns")
        if self.type == "two_column" and (not self.title or len(self.two_column_columns) != 2):
            raise ValueError("two_column slide requires title and exactly 2 columns")
        return self


class PptCreatorPresentationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    presentation: PptCreatorPresentationMeta
    slides: list[PptCreatorSlide] = Field(min_length=1)


def _normalize_model_leaderboard_item(rank: int, item: dict[str, Any]) -> ModelLeaderboardEntry | None:
    model = _clean_text(item.get("model") or item.get("model_effective") or item.get("model_requested"))
    if not model:
        return None
    provider = _clean_text(item.get("provider") or item.get("provider_effective") or item.get("provider_requested"))
    success_rate = _coerce_float(item.get("success_rate"))
    if success_rate is None and "success" in item:
        success_rate = 1.0 if bool(item.get("success")) else 0.0
    return ModelLeaderboardEntry(
        rank=rank,
        model=model,
        provider=provider,
        runtime_bucket=_clean_text(item.get("runtime_bucket")),
        comparison_score=_coerce_float(item.get("comparison_score")),
        avg_latency_s=_coerce_float(item.get("avg_latency_s") if item.get("avg_latency_s") is not None else item.get("latency_s")),
        format_adherence=_coerce_float(item.get("avg_format_adherence") if item.get("avg_format_adherence") is not None else item.get("format_adherence")),
        use_case_fit_score=_coerce_float(item.get("avg_use_case_fit_score") if item.get("avg_use_case_fit_score") is not None else item.get("use_case_fit_score")),
        success_rate=success_rate,
    )


def _normalize_model_leaderboard(summary: dict[str, Any], *, max_items: int) -> list[ModelLeaderboardEntry]:
    raw_items = summary.get("model_leaderboard") or summary.get("candidate_ranking") or []
    leaderboard: list[ModelLeaderboardEntry] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        entry = _normalize_model_leaderboard_item(len(leaderboard) + 1, raw_item)
        if entry is None:
            continue
        leaderboard.append(entry)
        if len(leaderboard) >= max_items:
            break
    return leaderboard


def _normalize_eval_suite_leaderboard(summary: dict[str, Any], *, max_items: int) -> list[EvalSuiteLeaderboardEntry]:
    raw_items = summary.get("suite_leaderboard") or []
    leaderboard: list[EvalSuiteLeaderboardEntry] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        suite_name = _clean_text(raw_item.get("suite_name"))
        if not suite_name:
            continue
        leaderboard.append(
            EvalSuiteLeaderboardEntry(
                rank=len(leaderboard) + 1,
                suite_name=suite_name,
                pass_rate=_coerce_float(raw_item.get("pass_rate")),
                avg_score_ratio=_coerce_float(raw_item.get("avg_score_ratio")),
                avg_latency_s=_coerce_float(raw_item.get("avg_latency_s")),
                total_runs=_coerce_int(raw_item.get("total_runs")) or None,
            )
        )
        if len(leaderboard) >= max_items:
            break
    return leaderboard


def _build_model_snapshot(summary: dict[str, Any]) -> ModelComparisonSnapshot:
    top_model_entry = summary.get("top_model") if isinstance(summary.get("top_model"), dict) else None
    best_overall = summary.get("best_overall_candidate") if isinstance(summary.get("best_overall_candidate"), dict) else None
    top_runtime_entry = summary.get("top_runtime_bucket") if isinstance(summary.get("top_runtime_bucket"), dict) else None
    total_candidates = _coerce_int(summary.get("total_candidates"))
    total_runs = _coerce_int(summary.get("total_runs")) or (1 if total_candidates else 0)
    return ModelComparisonSnapshot(
        total_runs=total_runs,
        total_candidates=total_candidates,
        success_rate=_coerce_float(summary.get("success_rate")),
        avg_latency_s=_coerce_float(summary.get("avg_latency_s")),
        avg_format_adherence=_coerce_float(summary.get("avg_format_adherence")),
        avg_use_case_fit_score=_coerce_float(summary.get("avg_use_case_fit_score")),
        top_model=_clean_text(
            (top_model_entry or {}).get("model")
            or (best_overall or {}).get("model")
            or (best_overall or {}).get("model_effective")
        ),
        top_runtime_bucket=_clean_text((top_runtime_entry or {}).get("runtime_bucket") or (best_overall or {}).get("runtime_bucket")),
    )


def _build_eval_snapshot(summary: dict[str, Any]) -> EvalSnapshot:
    suite_leaderboard = summary.get("suite_leaderboard") or []
    top_suite = suite_leaderboard[0] if suite_leaderboard and isinstance(suite_leaderboard[0], dict) else {}
    return EvalSnapshot(
        total_runs=_coerce_int(summary.get("total_runs")),
        pass_rate=_coerce_float(summary.get("pass_rate")),
        warn_rate=_coerce_float(summary.get("warn_rate")),
        fail_rate=_coerce_float(summary.get("fail_rate")),
        avg_score_ratio=_coerce_float(summary.get("avg_score_ratio")),
        avg_latency_s=_coerce_float(summary.get("avg_latency_s")),
        needs_review_rate=_coerce_float(summary.get("needs_review_rate")),
        top_suite_name=_clean_text(top_suite.get("suite_name")),
    )


def _build_key_highlights(
    model_snapshot: ModelComparisonSnapshot,
    eval_snapshot: EvalSnapshot,
    *,
    max_items: int = 6,
) -> list[str]:
    highlights: list[str] = []

    def add(message: str | None) -> None:
        cleaned = _clean_text(message)
        if cleaned and cleaned not in highlights and len(highlights) < max_items:
            highlights.append(cleaned)

    if model_snapshot.top_model:
        add(f"Top benchmark candidate atual: {model_snapshot.top_model}.")
    if model_snapshot.success_rate is not None:
        add(
            f"Benchmark success rate agregado em { _format_percentage(model_snapshot.success_rate) }."
        )
    if model_snapshot.avg_use_case_fit_score is not None:
        add(
            f"Use-case fit médio de benchmark em { _format_percentage(model_snapshot.avg_use_case_fit_score) }."
        )
    if eval_snapshot.top_suite_name:
        add(f"Suite líder de eval atual: {eval_snapshot.top_suite_name}.")
    if eval_snapshot.pass_rate is not None:
        add(f"PASS rate de eval em { _format_percentage(eval_snapshot.pass_rate) }.")
    if eval_snapshot.needs_review_rate is not None:
        add(f"Needs review rate atual em { _format_percentage(eval_snapshot.needs_review_rate) }.")
    if not highlights:
        add("Slice pronto para consolidar benchmarks e evals em formato executivo.")
    return highlights


def _build_key_metrics(
    model_snapshot: ModelComparisonSnapshot,
    eval_snapshot: EvalSnapshot,
) -> list[ExecutiveDeckMetric]:
    metrics: list[ExecutiveDeckMetric] = []

    if model_snapshot.total_candidates:
        metrics.append(
            ExecutiveDeckMetric(
                label="Benchmark candidates",
                value=str(model_snapshot.total_candidates),
                detail=(
                    f"Top model: {model_snapshot.top_model}"
                    if model_snapshot.top_model
                    else None
                ),
            )
        )
    if model_snapshot.success_rate is not None:
        metrics.append(
            ExecutiveDeckMetric(
                label="Benchmark success",
                value=_format_percentage(model_snapshot.success_rate),
                detail=f"Avg latency: {_format_seconds(model_snapshot.avg_latency_s)}",
            )
        )
    if eval_snapshot.total_runs:
        metrics.append(
            ExecutiveDeckMetric(
                label="Eval runs",
                value=str(eval_snapshot.total_runs),
                detail=(
                    f"Top suite: {eval_snapshot.top_suite_name}"
                    if eval_snapshot.top_suite_name
                    else None
                ),
            )
        )
    if eval_snapshot.pass_rate is not None:
        metrics.append(
            ExecutiveDeckMetric(
                label="Eval PASS rate",
                value=_format_percentage(eval_snapshot.pass_rate),
                detail=f"Avg score: {_format_ratio(eval_snapshot.avg_score_ratio)}",
            )
        )
    if len(metrics) < 4 and eval_snapshot.needs_review_rate is not None:
        metrics.append(
            ExecutiveDeckMetric(
                label="Needs review",
                value=_format_percentage(eval_snapshot.needs_review_rate),
                detail=f"Fail rate: {_format_percentage(eval_snapshot.fail_rate)}",
            )
        )
    return metrics[:4]


def _build_executive_summary(
    model_snapshot: ModelComparisonSnapshot,
    eval_snapshot: EvalSnapshot,
) -> str:
    parts: list[str] = []
    if model_snapshot.total_candidates:
        model_part = (
            f"{model_snapshot.total_candidates} candidatos foram consolidados no benchmark"
        )
        if model_snapshot.success_rate is not None:
            model_part += f", com success rate médio de {_format_percentage(model_snapshot.success_rate)}"
        if model_snapshot.top_model:
            model_part += f" e liderança atual de {model_snapshot.top_model}"
        parts.append(model_part + ".")
    if eval_snapshot.total_runs:
        eval_part = f"A camada de eval registrou {eval_snapshot.total_runs} runs"
        if eval_snapshot.pass_rate is not None:
            eval_part += f", com PASS rate de {_format_percentage(eval_snapshot.pass_rate)}"
        if eval_snapshot.needs_review_rate is not None:
            eval_part += f" e needs review de {_format_percentage(eval_snapshot.needs_review_rate)}"
        parts.append(eval_part + ".")
    if not parts:
        parts.append(
            "Contrato executivo v1 pronto para consolidar benchmark e eval em um payload apresentável."
        )
    return " ".join(parts)


def _build_recommendation(
    model_snapshot: ModelComparisonSnapshot,
    eval_snapshot: EvalSnapshot,
) -> str:
    if model_snapshot.top_model and eval_snapshot.pass_rate is not None:
        return (
            f"Promover {model_snapshot.top_model} como candidato principal da próxima rodada controlada, "
            f"mantendo o quality gate apoiado no PASS rate atual de {_format_percentage(eval_snapshot.pass_rate)}."
        )
    if model_snapshot.top_model:
        return (
            f"Promover {model_snapshot.top_model} para a próxima rodada controlada e manter comparação contínua "
            "com os demais candidatos líderes."
        )
    return (
        "Usar este contrato v1 como fundação estável para exportar benchmark e eval em formato executivo."
    )


def _build_watchouts(
    model_snapshot: ModelComparisonSnapshot,
    eval_snapshot: EvalSnapshot,
) -> list[str]:
    watchouts: list[str] = []
    if model_snapshot.success_rate is not None and model_snapshot.success_rate < 0.8:
        watchouts.append(
            f"Benchmark success rate ainda abaixo do ideal ({_format_percentage(model_snapshot.success_rate)})."
        )
    if eval_snapshot.fail_rate is not None and eval_snapshot.fail_rate > 0:
        watchouts.append(
            f"Ainda existem runs em FAIL ({_format_percentage(eval_snapshot.fail_rate)})."
        )
    if eval_snapshot.needs_review_rate is not None and eval_snapshot.needs_review_rate > 0.1:
        watchouts.append(
            f"Needs review rate acima do conforto operacional ({_format_percentage(eval_snapshot.needs_review_rate)})."
        )
    if model_snapshot.avg_use_case_fit_score is not None and model_snapshot.avg_use_case_fit_score < 0.75:
        watchouts.append(
            "Use-case fit médio do benchmark ainda pede ajuste antes de promoção ampla."
        )
    if not watchouts:
        watchouts.append("Sem watchouts críticos agregados nesta rodada; seguir monitorando qualidade e latência.")
    return watchouts[:4]


def _build_next_steps(
    model_snapshot: ModelComparisonSnapshot,
    eval_snapshot: EvalSnapshot,
) -> list[str]:
    next_steps: list[str] = []
    if model_snapshot.top_model:
        next_steps.append(
            f"Promover {model_snapshot.top_model} para uma rodada shadow/controlada como candidato default."
        )
    if eval_snapshot.fail_rate is not None and eval_snapshot.fail_rate > 0:
        next_steps.append("Revisar suites em FAIL/WARN e transformar os achados em gates repetíveis.")
    if eval_snapshot.needs_review_rate is not None and eval_snapshot.needs_review_rate > 0:
        next_steps.append("Reduzir backlog de needs_review antes de ampliar o escopo da rodada seguinte.")
    next_steps.append("Serializar este contrato e chamar o `ppt_creator_app` por API HTTP no próximo slice.")
    return next_steps[:6]


def build_benchmark_eval_contract(
    *,
    model_comparison_summary: dict[str, Any] | None = None,
    eval_summary: dict[str, Any] | None = None,
    title: str = DEFAULT_PRESENTATION_TITLE,
    subtitle: str = DEFAULT_PRESENTATION_SUBTITLE,
    author: str = DEFAULT_PRESENTATION_AUTHOR,
    report_date: str | None = None,
    theme: str = DEFAULT_PRESENTATION_THEME,
    footer_text: str = DEFAULT_PRESENTATION_FOOTER,
    max_models: int = 5,
    max_suites: int = 5,
    data_sources: list[str] | None = None,
) -> BenchmarkEvalExecutiveDeckContract:
    model_summary = model_comparison_summary or {}
    eval_summary_payload = eval_summary or {}
    model_snapshot = _build_model_snapshot(model_summary)
    eval_snapshot = _build_eval_snapshot(eval_summary_payload)
    inferred_data_sources = data_sources or []
    if not inferred_data_sources and model_summary:
        inferred_data_sources.append("phase7_model_comparison_log")
    if not inferred_data_sources and eval_summary_payload:
        inferred_data_sources.append("phase8_eval_store")
    elif eval_summary_payload and "phase8_eval_store" not in inferred_data_sources:
        inferred_data_sources.append("phase8_eval_store")
    if model_summary and "phase7_model_comparison_log" not in inferred_data_sources:
        inferred_data_sources.insert(0, "phase7_model_comparison_log")

    return BenchmarkEvalExecutiveDeckContract(
        presentation=PresentationExportMetadata(
            title=title,
            subtitle=subtitle,
            author=author,
            date=report_date or date.today().isoformat(),
            theme=theme,
            footer_text=footer_text,
        ),
        model_comparison_snapshot=model_snapshot,
        eval_snapshot=eval_snapshot,
        executive_summary=_build_executive_summary(model_snapshot, eval_snapshot),
        key_highlights=_build_key_highlights(model_snapshot, eval_snapshot),
        key_metrics=_build_key_metrics(model_snapshot, eval_snapshot),
        model_leaderboard=_normalize_model_leaderboard(model_summary, max_items=max_models),
        eval_suite_leaderboard=_normalize_eval_suite_leaderboard(eval_summary_payload, max_items=max_suites),
        recommendation=_build_recommendation(model_snapshot, eval_snapshot),
        watchouts=_build_watchouts(model_snapshot, eval_snapshot),
        next_steps=_build_next_steps(model_snapshot, eval_snapshot),
        data_sources=inferred_data_sources,
    )


def build_benchmark_eval_contract_from_logs(
    *,
    model_comparison_entries: list[dict[str, Any]] | None = None,
    eval_entries: list[dict[str, Any]] | None = None,
    title: str = DEFAULT_PRESENTATION_TITLE,
    subtitle: str = DEFAULT_PRESENTATION_SUBTITLE,
    author: str = DEFAULT_PRESENTATION_AUTHOR,
    report_date: str | None = None,
    theme: str = DEFAULT_PRESENTATION_THEME,
    footer_text: str = DEFAULT_PRESENTATION_FOOTER,
    max_models: int = 5,
    max_suites: int = 5,
) -> BenchmarkEvalExecutiveDeckContract:
    model_summary = summarize_model_comparison_log(model_comparison_entries or [])
    eval_summary = summarize_eval_runs(eval_entries or [])
    return build_benchmark_eval_contract(
        model_comparison_summary=model_summary,
        eval_summary=eval_summary,
        title=title,
        subtitle=subtitle,
        author=author,
        report_date=report_date,
        theme=theme,
        footer_text=footer_text,
        max_models=max_models,
        max_suites=max_suites,
    )


def build_ppt_creator_payload_from_benchmark_eval_contract(
    contract: BenchmarkEvalExecutiveDeckContract | dict[str, Any],
) -> dict[str, Any]:
    normalized = (
        contract
        if isinstance(contract, BenchmarkEvalExecutiveDeckContract)
        else BenchmarkEvalExecutiveDeckContract.model_validate(contract)
    )
    data_sources_text = ", ".join(normalized.data_sources) if normalized.data_sources else "n/a"
    slides: list[PptCreatorSlide] = [
        PptCreatorSlide(
            type="title",
            title=normalized.presentation.title,
            subtitle=normalized.presentation.subtitle,
            speaker_notes=f"Export kind: {normalized.export_kind}. Sources: {data_sources_text}.",
        ),
        PptCreatorSlide(
            type="summary",
            title="Executive summary",
            body=normalized.executive_summary,
            bullets=_compact_text_list(normalized.key_highlights, limit=3, max_chars=76),
            speaker_notes="Resumo executivo consolidado a partir dos agregados de benchmark/eval.",
        ),
    ]

    if normalized.key_metrics:
        slides.append(
            PptCreatorSlide(
                type="metrics",
                title="Benchmark and eval snapshot",
                metrics=[
                    PptCreatorMetricItem(
                        value=item.value,
                        label=item.label,
                        detail=item.detail,
                        trend=item.trend,
                    )
                    for item in normalized.key_metrics[:4]
                ],
                speaker_notes="Métricas executivas consolidadas para leitura rápida.",
            )
        )

    if normalized.model_leaderboard:
        slides.append(
            PptCreatorSlide(
                type="table",
                title="Model leaderboard",
                table_columns=["Model", "Signal", "Latency (s)", "Fit"],
                table_rows=[
                    [
                        item.model,
                        _format_signal(
                            item.comparison_score
                            if item.comparison_score is not None
                            else item.use_case_fit_score
                            if item.use_case_fit_score is not None
                            else item.success_rate
                        ),
                        _format_seconds(item.avg_latency_s).replace("s", ""),
                        _format_percentage(item.use_case_fit_score),
                    ]
                    for item in normalized.model_leaderboard
                ],
                speaker_notes="Leaderboard agregado de modelos para o slice benchmark/eval.",
            )
        )

    if normalized.eval_suite_leaderboard:
        slides.append(
            PptCreatorSlide(
                type="table",
                title="Eval suite leaderboard",
                table_columns=["Suite", "Pass rate", "Avg score", "Latency (s)"],
                table_rows=[
                    [
                        item.suite_name,
                        _format_percentage(item.pass_rate),
                        _format_ratio(item.avg_score_ratio),
                        _format_seconds(item.avg_latency_s).replace("s", ""),
                    ]
                    for item in normalized.eval_suite_leaderboard
                ],
                speaker_notes="Suites de eval ordenadas por qualidade agregada.",
            )
        )

    recommendation_bullets = _compact_text_list(normalized.next_steps[:2], limit=2, max_chars=72)
    watchout_body = normalized.watchouts[0] if normalized.watchouts else "Current round still requires attention to failures and evaluation quality."
    watchout_bullets = _compact_text_list(
        [
            f"Fail rate: {_format_percentage(normalized.eval_snapshot.fail_rate)}",
            f"Avg eval latency: {_format_seconds(normalized.eval_snapshot.avg_latency_s)}",
            *normalized.watchouts[1:4],
        ],
        limit=2,
        max_chars=70,
    )
    slides.append(
        _build_two_column_slide(
            "Recommendation vs watchouts",
            left_title="Recommendation",
            left_body=normalized.recommendation,
            left_bullets=recommendation_bullets,
            right_title="Watchouts",
            right_body=watchout_body,
            right_bullets=watchout_bullets,
            speaker_notes="Comparação entre decisão recomendada e pontos de atenção operacionais.",
        )
    )

    if normalized.next_steps:
        slides.append(
            PptCreatorSlide(
                type="bullets",
                title="Next steps",
                bullets=_compact_text_list(normalized.next_steps, limit=4, max_chars=80),
                speaker_notes="Próximos passos sugeridos para o próximo slice da integração.",
            )
        )

    payload = PptCreatorPresentationRequest(
        presentation=PptCreatorPresentationMeta(
            title=normalized.presentation.title,
            subtitle=normalized.presentation.subtitle,
            author=normalized.presentation.author,
            date=normalized.presentation.date,
            theme=normalized.presentation.theme,
            footer_text=normalized.presentation.footer_text,
        ),
        slides=slides,
    )
    return payload.model_dump(exclude_none=True)


class GenericDeckTableSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    columns: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    speaker_notes: str | None = None


class GenericExecutiveDeckContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = DEFAULT_EXECUTIVE_DECK_CONTRACT_VERSION
    export_kind: str
    deck_family: str
    presentation: PresentationExportMetadata
    context: dict[str, Any] = Field(default_factory=dict)
    candidate_profile: dict[str, Any] | None = None
    executive_summary: str
    key_highlights: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    evidence_highlights: list[ExecutiveDeckMetric] = Field(default_factory=list)
    key_metrics: list[ExecutiveDeckMetric] = Field(default_factory=list)
    tables: list[GenericDeckTableSection] = Field(default_factory=list)
    recommendation: str | None = None
    watchouts: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_export_kind(self) -> "GenericExecutiveDeckContract":
        self.export_kind = normalize_executive_deck_export_kind(self.export_kind)
        if self.export_kind not in SUPPORTED_EXECUTIVE_DECK_EXPORT_KINDS:
            raise ValueError(f"Unsupported executive deck export kind: {self.export_kind}")
        return self


ExecutiveDeckContract = BenchmarkEvalExecutiveDeckContract | GenericExecutiveDeckContract


def _dedupe_texts(values: list[object], *, limit: int = 8) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean_text(value)
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
        if len(normalized) >= limit:
            break
    return normalized


def _truncate_cell(value: object, *, max_chars: int = 120) -> str:
    cleaned = _clean_text(value) or "-"
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip() + "…"


def _build_metric(label: str, value: object, detail: object | None = None) -> ExecutiveDeckMetric:
    return ExecutiveDeckMetric(
        label=label,
        value=_truncate_cell(value, max_chars=40),
        detail=_clean_text(detail),
    )


def _bool_to_label(value: bool) -> str:
    return "Yes" if bool(value) else "No"


def _normalize_agent_sources(payload: DocumentAgentPayload) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in payload.sources:
        if hasattr(source, "model_dump"):
            rows.append(source.model_dump(mode="json"))
        elif isinstance(source, dict):
            rows.append(dict(source))
    return rows


def _extract_structured_payload(
    structured_result: StructuredResult | dict[str, Any] | None,
) -> tuple[StructuredResult | None, Any | None]:
    if structured_result is None:
        return None, None
    normalized = (
        structured_result
        if isinstance(structured_result, StructuredResult)
        else StructuredResult.model_validate(structured_result)
    )
    return normalized, normalized.validated_output


def _normalize_table_rows(rows: list[list[object]], *, max_rows: int = 8) -> list[list[str]]:
    normalized_rows: list[list[str]] = []
    for row in rows:
        if not isinstance(row, list):
            continue
        normalized_rows.append([_truncate_cell(cell) for cell in row])
        if len(normalized_rows) >= max_rows:
            break
    return normalized_rows


def _derive_document_ids_from_sources(source_rows: list[dict[str, Any]]) -> list[str]:
    document_ids = []
    for item in source_rows:
        if not isinstance(item, dict):
            continue
        value = _clean_text(item.get("document_id") or item.get("source"))
        if value and value not in document_ids:
            document_ids.append(value)
    return document_ids


def _extract_extraction_payload(loaded_payload: object) -> dict[str, Any]:
    if isinstance(loaded_payload, ExtractionPayload):
        return loaded_payload.model_dump(mode="json")
    return dict(loaded_payload) if isinstance(loaded_payload, dict) else {}


def _recommended_action_or_fallback(recommended_actions: list[str], fallback: str) -> str:
    return _dedupe_texts(recommended_actions, limit=1)[0] if _dedupe_texts(recommended_actions, limit=1) else fallback


def _compact_text_list(values: list[object], *, limit: int = 4, max_chars: int = 84) -> list[str]:
    return [_truncate_cell(value, max_chars=max_chars) for value in _dedupe_texts(values, limit=limit)]


def _humanize_watchout(value: object) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    mapping = {
        "legal_signoff_missing": "Legal sign-off still missing",
        "risk_review_has_gaps_without_grounded_risks": "Grounded evidence is still insufficient for a final decision",
        "Há ações abertas sem owner definido.": "Open actions still lack named owners",
        "Há ações abertas sem owner definido no action store.": "Open actions still lack named owners",
        "Há ações sensíveis pendentes de aprovação.": "Some sensitive actions still require formal approval",
        "Há ações em atraso que merecem repriorização imediata.": "Some actions are overdue and need reprioritization",
        "Validação jurídica final ainda pendente.": "Final legal validation is still pending",
    }
    return mapping.get(cleaned, cleaned.replace("_", " ").strip().capitalize())


def _candidate_profile_name(payload: CVAnalysisPayload) -> str:
    return _clean_text(getattr(payload.personal_info, "full_name", None) if payload.personal_info else None) or "Candidate"


def _candidate_profile_location(payload: CVAnalysisPayload) -> str | None:
    return _clean_text(getattr(payload.personal_info, "location", None) if payload.personal_info else None)


def _candidate_profile_headline(payload: CVAnalysisPayload) -> str:
    primary_role = next((_clean_text(item.title) for item in payload.experience_entries if _clean_text(item.title)), None)
    skills = _dedupe_texts(list(payload.skills or []), limit=3)
    if primary_role and skills:
        return f"{primary_role} · {', '.join(skills[:2])}"
    if primary_role:
        return primary_role
    if skills:
        return ", ".join(skills)
    return "Profile under review"


def _candidate_profile_haystack(payload: CVAnalysisPayload) -> str:
    parts: list[str] = []
    for values in (payload.skills, payload.languages, payload.strengths, payload.improvement_areas, payload.projects):
        parts.extend(str(item or "") for item in (values or []))
    for item in payload.experience_entries:
        parts.extend(
            [
                str(item.title or ""),
                str(item.organization or ""),
                str(item.location or ""),
                str(item.date_range or ""),
                str(item.description or ""),
                *(str(bullet or "") for bullet in (item.bullets or [])),
            ]
        )
    return " ".join(parts).lower()


def _candidate_has_keywords(payload: CVAnalysisPayload, keywords: tuple[str, ...]) -> bool:
    haystack = _candidate_profile_haystack(payload)
    return any(keyword in haystack for keyword in keywords)


def _candidate_strengths(payload: CVAnalysisPayload) -> list[str]:
    strengths = _dedupe_texts(list(payload.strengths or []), limit=4)
    if strengths:
        return strengths
    fallback: list[object] = []
    skills = _dedupe_texts(list(payload.skills or []), limit=3)
    if skills:
        fallback.append(f"Relevant technical skill evidence includes {', '.join(skills)}.")
    if float(payload.experience_years or 0.0) >= 5:
        fallback.append("Grounded experience suggests a solid senior execution profile.")
    if _candidate_has_keywords(payload, ("lead", "leader", "leadership", "manager", "owner", "ownership")):
        fallback.append("Leadership or ownership language appears in the current CV.")
    return _dedupe_texts(fallback, limit=4)


def _candidate_gaps(payload: CVAnalysisPayload) -> list[str]:
    gaps: list[object] = [*(payload.improvement_areas or [])]
    if not payload.experience_entries:
        gaps.append("Experience history is sparse or weakly structured in the current CV grounding.")
    if not payload.skills:
        gaps.append("The CV exposes limited explicit skill evidence for a confident fit assessment.")
    if payload.experience_entries and not _candidate_has_keywords(payload, ("lead", "leader", "leadership", "manager", "owner", "ownership")):
        gaps.append("Leadership and ownership signals are not explicit in the current CV.")
    if payload.experience_entries and not _candidate_has_keywords(payload, ("product", "stakeholder", "customer", "business", "roadmap", "strategy")):
        gaps.append("Product thinking / stakeholder management should be validated with concrete examples.")
    return _dedupe_texts(gaps, limit=4)


def _candidate_evidence_highlights(payload: CVAnalysisPayload) -> list[ExecutiveDeckMetric]:
    metrics: list[ExecutiveDeckMetric] = []
    years = float(payload.experience_years or 0.0)
    if years > 0 or payload.experience_entries:
        metrics.append(
            ExecutiveDeckMetric(
                label="Experience",
                value=(f"{years:.1f} years" if years > 0 else "Not explicit"),
                detail=f"{len(payload.experience_entries or [])} structured role(s)",
            )
        )
    skills = _dedupe_texts(list(payload.skills or []), limit=3)
    if skills:
        metrics.append(
            ExecutiveDeckMetric(
                label="Core skills",
                value=", ".join(skills),
                detail=f"{len(payload.skills or [])} mapped skill(s)",
            )
        )
    languages = _dedupe_texts(list(payload.languages or []), limit=2)
    if languages:
        metrics.append(
            ExecutiveDeckMetric(
                label="Languages",
                value=", ".join(languages),
                detail=f"{len(payload.languages or [])} language(s)",
            )
        )
    if payload.experience_entries:
        latest = payload.experience_entries[0]
        metrics.append(
            ExecutiveDeckMetric(
                label="Recent anchor",
                value=_clean_text(latest.title) or "-",
                detail=_clean_text(latest.organization) or _clean_text(latest.date_range) or "-",
            )
        )
    elif payload.education_entries:
        latest_education = payload.education_entries[0]
        metrics.append(
            ExecutiveDeckMetric(
                label="Education",
                value=_clean_text(latest_education.degree) or "-",
                detail=_clean_text(latest_education.institution) or "-",
            )
        )
    if not metrics:
        metrics.append(
            ExecutiveDeckMetric(
                label="Grounding status",
                value="Sparse CV evidence",
                detail="Manual review required because the current CV exposes few explicit signals.",
            )
        )
    return metrics[:4]


def _candidate_next_steps(payload: CVAnalysisPayload, gaps: list[str]) -> list[str]:
    next_steps: list[object] = []
    for item in gaps[:2]:
        normalized = _clean_text(item).rstrip(".")
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered.startswith(("validate", "confirm", "probe", "assess", "review")):
            next_steps.append(normalized)
        else:
            next_steps.append(f"Validate {normalized[0].lower() + normalized[1:]}")
    if _candidate_has_keywords(payload, ("lead", "leader", "leadership", "manager", "owner", "ownership")):
        next_steps.append("Probe measurable scope, business impact and cross-functional ownership in interview.")
    else:
        next_steps.append("Run a focused interview on leadership, ownership and stakeholder management examples.")
    next_steps.append("Validate delivery depth with concrete examples of architecture, execution and business outcomes.")
    return _dedupe_texts(next_steps, limit=4)


def _candidate_recommendation(payload: CVAnalysisPayload, gaps: list[str]) -> str:
    strengths = len(payload.strengths or [])
    skills = len(payload.skills or [])
    years = float(payload.experience_years or 0.0)
    experience_entries = len(payload.experience_entries or [])
    positive_score = 0
    risk_score = 0

    if years >= 7:
        positive_score += 2
    elif years >= 3:
        positive_score += 1
    if experience_entries >= 2:
        positive_score += 1
    if strengths:
        positive_score += 1
    if skills >= 4:
        positive_score += 1
    if _candidate_has_keywords(payload, ("lead", "leader", "leadership", "manager", "owner", "ownership", "principal", "staff")):
        positive_score += 1
    if _candidate_has_keywords(payload, ("product", "stakeholder", "customer", "business", "roadmap", "strategy")):
        positive_score += 1
    if _candidate_has_keywords(payload, ("production", "scale", "architecture", "platform", "mlops", "rag", "eval")):
        positive_score += 1

    if not payload.experience_entries:
        risk_score += 2
    if not payload.skills:
        risk_score += 1
    if years > 0 and years < 2:
        risk_score += 1
    if len(gaps) >= max(strengths + 2, 3):
        risk_score += 2
    if positive_score >= 4 and risk_score <= 1:
        return "Advance to the next stage with focused validation of leadership, scope and business impact."
    if positive_score >= 3 and risk_score <= 3:
        return "Keep the candidate in the active pipeline and run a targeted interview on ownership, stakeholder management and delivery depth."
    return "Hold before advancing and validate the current gaps with a focused technical and hiring screen."


def _candidate_executive_summary(
    payload: CVAnalysisPayload,
    *,
    candidate_name: str,
    headline: str,
    location: str | None,
    strengths: list[str],
    gaps: list[str],
) -> str:
    years = float(payload.experience_years or 0.0)
    experience_entries = len(payload.experience_entries or [])
    opening = f"{candidate_name} presents as a hiring profile centered on {headline}"
    if location:
        opening += f" from {location}"
    opening += "."
    evidence = "The current CV exposes limited explicit duration signals"
    if years > 0:
        evidence = f"Grounded evidence suggests about {years:.1f} year(s) of experience"
    if experience_entries:
        evidence += f" across {experience_entries} structured role(s)"
    evidence += "."
    trailing: list[str] = []
    if strengths:
        trailing.append(f"Top strengths: {'; '.join(strengths[:2])}.")
    if gaps:
        trailing.append(f"Primary watchout: {gaps[0]}.")
    return " ".join([opening, evidence, *trailing]).strip()


def _build_cards_slide(
    title: str,
    cards: list[PptCreatorCardItem],
    *,
    speaker_notes: str | None = None,
) -> PptCreatorSlide:
    padded_cards = list(cards[:3])
    while len(padded_cards) < 3:
        padded_cards.append(
            PptCreatorCardItem(
                title=f"Signal {len(padded_cards) + 1}",
                body="Additional executive signal not populated in this slice.",
                footer="Optional",
            )
        )
    return PptCreatorSlide(type="cards", title=title, cards=padded_cards[:3], speaker_notes=speaker_notes)


def _build_timeline_slide(
    title: str,
    steps: list[object],
    *,
    speaker_notes: str | None = None,
) -> PptCreatorSlide | None:
    compact_steps = _compact_text_list(list(steps), limit=4, max_chars=80)
    if len(compact_steps) < 2:
        return None
    return PptCreatorSlide(
        type="timeline",
        title=title,
        timeline_items=[
            PptCreatorTimelineItem(title=f"Step {index}", body=step, tag=f"P{index}")
            for index, step in enumerate(compact_steps, start=1)
        ],
        speaker_notes=speaker_notes,
    )


def _build_two_column_slide(
    title: str,
    *,
    left_title: str,
    left_body: str | None = None,
    left_bullets: list[str] | None = None,
    right_title: str,
    right_body: str | None = None,
    right_bullets: list[str] | None = None,
    speaker_notes: str | None = None,
) -> PptCreatorSlide:
    return PptCreatorSlide(
        type="two_column",
        title=title,
        two_column_columns=[
            PptCreatorComparisonColumn(
                title=left_title,
                body=left_body,
                bullets=list(left_bullets or []),
            ),
            PptCreatorComparisonColumn(
                title=right_title,
                body=right_body,
                bullets=list(right_bullets or []),
            ),
        ],
        speaker_notes=speaker_notes,
    )


def build_document_review_deck_contract(
    *,
    structured_result: StructuredResult | dict[str, Any],
) -> GenericExecutiveDeckContract:
    normalized_result, payload = _extract_structured_payload(structured_result)
    if payload is None:
        raise ValueError("Structured result is required for document review deck generation.")

    summary_text = ""
    highlights: list[str] = []
    watchouts: list[str] = []
    next_steps: list[str] = []
    tables: list[GenericDeckTableSection] = []
    key_metrics: list[ExecutiveDeckMetric] = []
    context: dict[str, Any] = {
        "task_type": normalized_result.task_type if normalized_result else None,
        "source_documents": list(normalized_result.source_documents or []) if normalized_result else [],
    }

    if isinstance(payload, DocumentAgentPayload):
        structured_response = payload.structured_response if isinstance(payload.structured_response, dict) else {}
        extraction_payload = _extract_extraction_payload(structured_response.get("extraction_payload"))
        risks = extraction_payload.get("risks") if isinstance(extraction_payload.get("risks"), list) else []
        gaps = structured_response.get("gaps") if isinstance(structured_response.get("gaps"), list) else []
        if not gaps:
            gaps = extraction_payload.get("missing_information") if isinstance(extraction_payload.get("missing_information"), list) else []
        action_items = extraction_payload.get("action_items") if isinstance(extraction_payload.get("action_items"), list) else []
        source_rows = _normalize_agent_sources(payload)
        source_document_ids = _derive_document_ids_from_sources(source_rows)

        finding_rows: list[list[object]] = []
        for item in risks:
            if not isinstance(item, dict):
                continue
            finding_rows.append(
                [
                    "risk",
                    item.get("description"),
                    item.get("owner") or "-",
                    item.get("due_date") or "-",
                    item.get("evidence") or item.get("impact") or "-",
                ]
            )
        for gap in gaps:
            finding_rows.append(["gap", gap, "-", "-", "-"])
        if payload.comparison_findings and not finding_rows:
            for finding in payload.comparison_findings:
                finding_rows.append(
                    [
                        finding.finding_type,
                        finding.title,
                        ", ".join(finding.documents or []) or "-",
                        "-",
                        " | ".join(finding.evidence[:2]) or finding.description,
                    ]
                )

        if finding_rows:
            tables.append(
                GenericDeckTableSection(
                    title="Top findings",
                    columns=["Type", "Finding", "Owner", "Due", "Evidence"],
                    rows=_normalize_table_rows(finding_rows),
                    speaker_notes="Findings grounded no payload estruturado/document agent.",
                )
            )
        action_rows = []
        for item in action_items[:8]:
            if not isinstance(item, dict):
                continue
            action_rows.append(
                [
                    item.get("description"),
                    item.get("owner") or "-",
                    item.get("due_date") or "-",
                    item.get("status") or "suggested",
                ]
            )
        if action_rows:
            tables.append(
                GenericDeckTableSection(
                    title="Action plan",
                    columns=["Action", "Owner", "Due", "Status"],
                    rows=_normalize_table_rows(action_rows),
                )
            )

        summary_text = payload.summary or "Executive review grounded no payload do agente documental."
        highlights = _dedupe_texts(list(payload.key_points or []), limit=6)
        watchouts = _dedupe_texts(list(payload.limitations or []), limit=4)
        if payload.needs_review and payload.needs_review_reason:
            watchouts = _dedupe_texts([payload.needs_review_reason, *watchouts], limit=4)
        next_steps = _dedupe_texts(list(payload.recommended_actions or []), limit=6)
        key_metrics = [
            _build_metric("Source count", len(source_rows)),
            _build_metric("Findings", len(finding_rows)),
            _build_metric("Actions", len(action_rows)),
            _build_metric("Needs review", _bool_to_label(payload.needs_review)),
        ]
        context.update(
            {
                "tool_used": payload.tool_used,
                "review_type": structured_response.get("review_type") or payload.tool_used,
                "document_ids": source_document_ids or list(normalized_result.source_documents or []),
            }
        )
        recommendation = _recommended_action_or_fallback(
            list(payload.recommended_actions or []),
            "Consolidar os findings principais e validar os próximos passos com revisão humana antes da execução.",
        )
        data_sources = ["structured_result", "document_agent"]
    elif isinstance(payload, ExtractionPayload):
        risk_rows = [
            ["risk", item.description, item.owner or "-", item.due_date or "-", item.evidence or item.impact or "-"]
            for item in payload.risks[:8]
        ]
        if risk_rows:
            tables.append(
                GenericDeckTableSection(
                    title="Risk review",
                    columns=["Type", "Finding", "Owner", "Due", "Evidence"],
                    rows=_normalize_table_rows(risk_rows),
                )
            )
        action_rows = [
            [item.description, item.owner or "-", item.due_date or "-", item.status or "suggested"]
            for item in payload.action_items[:8]
        ]
        if action_rows:
            tables.append(
                GenericDeckTableSection(
                    title="Action plan",
                    columns=["Action", "Owner", "Due", "Status"],
                    rows=_normalize_table_rows(action_rows),
                )
            )
        summary_text = (
            f"{payload.main_subject or 'Documento'}: {len(payload.risks)} risco(s), "
            f"{len(payload.action_items)} ação(ões) e {len(payload.missing_information)} lacuna(s) identificada(s)."
        )
        highlights = _dedupe_texts([*payload.categories, *payload.important_dates, *payload.important_numbers], limit=6)
        watchouts = _dedupe_texts(list(payload.missing_information or []), limit=4)
        next_steps = _dedupe_texts([item.description for item in payload.action_items], limit=6)
        key_metrics = [
            _build_metric("Entities", len(payload.entities)),
            _build_metric("Risks", len(payload.risks)),
            _build_metric("Actions", len(payload.action_items)),
            _build_metric("Gaps", len(payload.missing_information)),
        ]
        recommendation = _recommended_action_or_fallback(next_steps, "Transformar os riscos e gaps mais relevantes em plano de revisão priorizado.")
        data_sources = ["structured_result", "extraction"]
    elif isinstance(payload, SummaryPayload):
        topic_rows = [
            [topic.title, _format_percentage(topic.relevance_score), " | ".join(topic.key_points[:2]) or "-"]
            for topic in payload.topics[:8]
        ]
        if topic_rows:
            tables.append(
                GenericDeckTableSection(
                    title="Topic review",
                    columns=["Topic", "Relevance", "Key points"],
                    rows=_normalize_table_rows(topic_rows),
                )
            )
        summary_text = payload.executive_summary
        highlights = _dedupe_texts([*payload.key_insights, *(point for topic in payload.topics for point in topic.key_points)], limit=6)
        key_metrics = [
            _build_metric("Topics", len(payload.topics)),
            _build_metric("Reading time", f"{payload.reading_time_minutes} min"),
            _build_metric("Completeness", _format_ratio(payload.completeness_score)),
            _build_metric("Insights", len(payload.key_insights)),
        ]
        recommendation = "Usar os tópicos e insights consolidados como base de revisão executiva do documento."
        watchouts = ["O resumo pode omitir detalhes operacionais finos; consulte o documento completo quando necessário."]
        next_steps = _dedupe_texts(list(payload.key_insights or []), limit=6)
        data_sources = ["structured_result", "summary"]
    else:
        raise ValueError("Document review deck currently supports document_agent, extraction or summary structured outputs.")

    return GenericExecutiveDeckContract(
        export_kind=DOCUMENT_REVIEW_EXPORT_KIND,
        deck_family="review",
        presentation=PresentationExportMetadata(
            title="AI Workbench Local — Document Review",
            subtitle="Executive review of the latest grounded document analysis",
            author=DEFAULT_PRESENTATION_AUTHOR,
            date=date.today().isoformat(),
            theme=DEFAULT_PRESENTATION_THEME,
            footer_text="AI Workbench Local • Document Review",
        ),
        context=context,
        executive_summary=summary_text,
        key_highlights=highlights,
        key_metrics=key_metrics,
        tables=tables,
        recommendation=recommendation,
        watchouts=watchouts,
        next_steps=next_steps,
        data_sources=data_sources,
    )


def build_policy_contract_comparison_deck_contract(
    *,
    structured_result: StructuredResult | dict[str, Any],
) -> GenericExecutiveDeckContract:
    normalized_result, payload = _extract_structured_payload(structured_result)
    if not isinstance(payload, DocumentAgentPayload):
        raise ValueError("Policy / contract comparison deck requires a document_agent structured result.")
    if not payload.comparison_findings and len(payload.compared_documents or []) < 2:
        raise ValueError("Comparison deck requires comparison findings or at least two compared documents.")

    comparison_rows = [
        [
            finding.finding_type,
            finding.title,
            ", ".join(finding.documents or []) or "-",
            " | ".join(finding.evidence[:2]) or finding.description,
        ]
        for finding in payload.comparison_findings[:8]
    ]
    tables = []
    if comparison_rows:
        tables.append(
            GenericDeckTableSection(
                title="Comparison findings",
                columns=["Type", "Finding", "Documents", "Evidence"],
                rows=_normalize_table_rows(comparison_rows),
                speaker_notes="Diferenças e impactos extraídos do fluxo de comparação documental.",
            )
        )

    review_type = None
    if isinstance(payload.structured_response, dict):
        review_type = payload.structured_response.get("review_type")

    return GenericExecutiveDeckContract(
        export_kind=POLICY_CONTRACT_COMPARISON_EXPORT_KIND,
        deck_family="comparison",
        presentation=PresentationExportMetadata(
            title="AI Workbench Local — Policy / Contract Comparison",
            subtitle="Executive comparison review of grounded document differences",
            author=DEFAULT_PRESENTATION_AUTHOR,
            date=date.today().isoformat(),
            theme=DEFAULT_PRESENTATION_THEME,
            footer_text="AI Workbench Local • Comparison Review",
        ),
        context={
            "task_type": normalized_result.task_type if normalized_result else None,
            "review_type": review_type or payload.tool_used,
            "compared_documents": list(payload.compared_documents or []),
        },
        executive_summary=payload.summary or "Comparison review grounded no fluxo de comparação documental.",
        key_highlights=_dedupe_texts(list(payload.key_points or []) + [item.title for item in payload.comparison_findings], limit=6),
        key_metrics=[
            _build_metric("Compared docs", len(payload.compared_documents or [])),
            _build_metric("Findings", len(payload.comparison_findings or [])),
            _build_metric("Sources", len(payload.sources or [])),
            _build_metric("Needs review", _bool_to_label(payload.needs_review)),
        ],
        tables=tables,
        recommendation=_recommended_action_or_fallback(
            list(payload.recommended_actions or []),
            "Validar as diferenças críticas e usar o comparativo para suportar a decisão final com revisão humana.",
        ),
        watchouts=_dedupe_texts(
            [*(payload.limitations or []), payload.needs_review_reason] if payload.needs_review_reason else list(payload.limitations or []),
            limit=4,
        ),
        next_steps=_dedupe_texts(list(payload.recommended_actions or []), limit=6),
        data_sources=["structured_result", "document_agent_comparison"],
    )


def build_action_plan_deck_contract(
    *,
    structured_result: StructuredResult | dict[str, Any] | None = None,
    evidenceops_action_entries: list[dict[str, Any]] | None = None,
) -> GenericExecutiveDeckContract:
    if evidenceops_action_entries:
        action_summary = summarize_evidenceops_actions(evidenceops_action_entries)
        action_rows = [
            [
                entry.get("action_type") or "action",
                entry.get("description"),
                entry.get("owner") or "-",
                entry.get("due_date") or "-",
                entry.get("status") or "-",
            ]
            for entry in evidenceops_action_entries[:8]
            if isinstance(entry, dict)
        ]
        watchouts = []
        if int(action_summary.get("unassigned_open_actions") or 0) > 0:
            watchouts.append("Há ações abertas sem owner definido.")
        if int(action_summary.get("overdue_actions") or 0) > 0:
            watchouts.append("Há ações em atraso que merecem repriorização imediata.")
        if int(action_summary.get("pending_approval_actions") or 0) > 0:
            watchouts.append("Há ações sensíveis aguardando aprovação formal.")
        next_steps = _dedupe_texts(
            [
                entry.get("description")
                for entry in evidenceops_action_entries
                if isinstance(entry, dict) and str(entry.get("status") or "").strip().lower() in {"open", "recommended", "suggested", "pending"}
            ],
            limit=6,
        )
        return GenericExecutiveDeckContract(
            export_kind=ACTION_PLAN_EXPORT_KIND,
            deck_family="action_plan",
            presentation=PresentationExportMetadata(
                title="AI Workbench Local — Action Plan",
                subtitle="Operational action plan grounded in current action backlog",
                author=DEFAULT_PRESENTATION_AUTHOR,
                date=date.today().isoformat(),
                theme=DEFAULT_PRESENTATION_THEME,
                footer_text="AI Workbench Local • Action Plan",
            ),
            context={
                "review_type_counts": dict(action_summary.get("review_type_counts") or {}),
            },
            executive_summary=(
                f"O action backlog atual contém {int(action_summary.get('total_actions') or 0)} ação(ões), "
                f"com {int(action_summary.get('open_actions') or 0)} aberta(s), "
                f"{int(action_summary.get('review_required_actions') or 0)} sensível(is) e "
                f"{int(action_summary.get('overdue_actions') or 0)} em atraso."
            ),
            key_highlights=_dedupe_texts(next_steps, limit=6),
            key_metrics=[
                _build_metric("Total actions", int(action_summary.get("total_actions") or 0)),
                _build_metric("Open", int(action_summary.get("open_actions") or 0)),
                _build_metric("Overdue", int(action_summary.get("overdue_actions") or 0)),
                _build_metric("Approval required", int(action_summary.get("review_required_actions") or 0)),
            ],
            tables=[
                GenericDeckTableSection(
                    title="Action backlog",
                    columns=["Type", "Action", "Owner", "Due", "Status"],
                    rows=_normalize_table_rows(action_rows),
                )
            ],
            recommendation=_recommended_action_or_fallback(
                next_steps,
                "Priorizar o fechamento das ações abertas com maior criticidade e menor definição operacional.",
            ),
            watchouts=_dedupe_texts(watchouts, limit=4),
            next_steps=next_steps,
            data_sources=["evidenceops_action_store"],
        )

    normalized_result, payload = _extract_structured_payload(structured_result)
    if isinstance(payload, ChecklistPayload):
        action_rows = [
            [
                item.status,
                item.priority or "-",
                item.title,
                item.category or "-",
                item.evidence or item.source_text or "-",
            ]
            for item in payload.items[:8]
        ]
        next_steps = _dedupe_texts([item.title for item in payload.items if item.status != "completed"], limit=6)
        return GenericExecutiveDeckContract(
            export_kind=ACTION_PLAN_EXPORT_KIND,
            deck_family="action_plan",
            presentation=PresentationExportMetadata(
                title="AI Workbench Local — Action Plan",
                subtitle="Operational plan derived from structured checklist",
                author=DEFAULT_PRESENTATION_AUTHOR,
                date=date.today().isoformat(),
                theme=DEFAULT_PRESENTATION_THEME,
                footer_text="AI Workbench Local • Checklist Action Plan",
            ),
            context={
                "task_type": normalized_result.task_type if normalized_result else None,
                "checklist_title": payload.title,
            },
            executive_summary=payload.description,
            key_highlights=_dedupe_texts([item.title for item in payload.items], limit=6),
            key_metrics=[
                _build_metric("Total items", payload.total_items),
                _build_metric("Completed", payload.completed_items),
                _build_metric("Progress", f"{payload.progress_percentage:.0f}%"),
                _build_metric("Pending", max(payload.total_items - payload.completed_items, 0)),
            ],
            tables=[
                GenericDeckTableSection(
                    title="Checklist actions",
                    columns=["Status", "Priority", "Action", "Category", "Evidence"],
                    rows=_normalize_table_rows(action_rows),
                )
            ],
            recommendation=_recommended_action_or_fallback(
                next_steps,
                "Executar o checklist em ordem de prioridade e revisar itens pendentes antes do handoff operacional.",
            ),
            watchouts=_dedupe_texts([item.title for item in payload.items if item.status == "skipped"], limit=4),
            next_steps=next_steps,
            data_sources=["structured_result", "checklist"],
        )

    if isinstance(payload, DocumentAgentPayload):
        structured_response = payload.structured_response if isinstance(payload.structured_response, dict) else {}
        actions_from_structured = structured_response.get("actions") if isinstance(structured_response.get("actions"), list) else []
        extraction_payload = _extract_extraction_payload(structured_response.get("extraction_payload"))
        action_items = extraction_payload.get("action_items") if isinstance(extraction_payload.get("action_items"), list) else []
        rows: list[list[object]] = []
        for item in action_items[:8]:
            if not isinstance(item, dict):
                continue
            rows.append(["action_item", item.get("description"), item.get("owner") or "-", item.get("due_date") or "-", item.get("status") or "suggested"])
        for action in actions_from_structured[:8 - len(rows)]:
            rows.append(["recommended_action", action, "-", "-", "recommended"])
        next_steps = _dedupe_texts(
            [*(payload.recommended_actions or []), *actions_from_structured, *(item.get("description") for item in action_items if isinstance(item, dict))],
            limit=6,
        )
        return GenericExecutiveDeckContract(
            export_kind=ACTION_PLAN_EXPORT_KIND,
            deck_family="action_plan",
            presentation=PresentationExportMetadata(
                title="AI Workbench Local — Action Plan",
                subtitle="Operational plan derived from document-agent outputs",
                author=DEFAULT_PRESENTATION_AUTHOR,
                date=date.today().isoformat(),
                theme=DEFAULT_PRESENTATION_THEME,
                footer_text="AI Workbench Local • Action Plan",
            ),
            context={"task_type": normalized_result.task_type if normalized_result else None, "tool_used": payload.tool_used},
            executive_summary=payload.summary,
            key_highlights=_dedupe_texts(list(payload.key_points or []) + next_steps, limit=6),
            key_metrics=[
                _build_metric("Actions", len(rows)),
                _build_metric("Recommended", len(payload.recommended_actions or [])),
                _build_metric("Sources", len(payload.sources or [])),
                _build_metric("Needs review", _bool_to_label(payload.needs_review)),
            ],
            tables=[
                GenericDeckTableSection(
                    title="Action backlog",
                    columns=["Type", "Action", "Owner", "Due", "Status"],
                    rows=_normalize_table_rows(rows),
                )
            ]
            if rows
            else [],
            recommendation=_recommended_action_or_fallback(next_steps, "Traduzir os próximos passos em owners, prazos e critérios de acompanhamento."),
            watchouts=_dedupe_texts([*(payload.limitations or []), payload.needs_review_reason] if payload.needs_review_reason else list(payload.limitations or []), limit=4),
            next_steps=next_steps,
            data_sources=["structured_result", "document_agent_action_plan"],
        )

    raise ValueError("Action plan deck requires checklist/document_agent output or EvidenceOps action entries.")


def build_candidate_review_deck_contract(
    *,
    structured_result: StructuredResult | dict[str, Any],
) -> GenericExecutiveDeckContract:
    normalized_result, payload = _extract_structured_payload(structured_result)
    if not isinstance(payload, CVAnalysisPayload):
        raise ValueError("Candidate review deck requires a cv_analysis structured result.")

    candidate_name = _candidate_profile_name(payload)
    location = _candidate_profile_location(payload)
    headline = _candidate_profile_headline(payload)
    strengths = _candidate_strengths(payload)
    gaps = _candidate_gaps(payload)
    evidence_highlights = _candidate_evidence_highlights(payload)
    next_steps = _candidate_next_steps(payload, gaps)
    experience_rows = [
        [
            item.title or "-",
            item.organization or "-",
            item.date_range or "-",
            " | ".join(item.bullets[:2]) or item.description or "-",
        ]
        for item in payload.experience_entries[:6]
    ]
    education_rows = [
        [
            item.degree or "-",
            item.institution or "-",
            item.date_range or "-",
            item.location or "-",
        ]
        for item in payload.education_entries[:4]
    ]
    tables = []
    if experience_rows:
        tables.append(
            GenericDeckTableSection(
                title="Experience highlights",
                columns=["Role", "Organization", "Date", "Evidence"],
                rows=_normalize_table_rows(experience_rows),
            )
        )
    if education_rows:
        tables.append(
            GenericDeckTableSection(
                title="Education snapshot",
                columns=["Degree", "Institution", "Date", "Location"],
                rows=_normalize_table_rows(education_rows),
            )
        )
    recommendation = _candidate_recommendation(payload, gaps)
    summary_text = _candidate_executive_summary(
        payload,
        candidate_name=candidate_name,
        headline=headline,
        location=location,
        strengths=strengths,
        gaps=gaps,
    )
    return GenericExecutiveDeckContract(
        export_kind=CANDIDATE_REVIEW_EXPORT_KIND,
        deck_family="candidate_review",
        presentation=PresentationExportMetadata(
            title=f"AI Workbench Local — Candidate Review · {candidate_name}",
            subtitle="Executive hiring summary grounded in cv_analysis",
            author=DEFAULT_PRESENTATION_AUTHOR,
            date=date.today().isoformat(),
            theme=DEFAULT_PRESENTATION_THEME,
            footer_text="AI Workbench Local • Candidate Review",
        ),
        context={
            "task_type": normalized_result.task_type if normalized_result else None,
            "candidate_name": candidate_name,
            "headline": headline,
            "location": location or "n/d",
            "experience_entries": len(payload.experience_entries or []),
        },
        candidate_profile={
            "name": candidate_name,
            "headline": headline,
            "location": location or "n/d",
        },
        executive_summary=summary_text,
        key_highlights=_dedupe_texts([*strengths, *(payload.skills or [])], limit=6),
        strengths=strengths,
        gaps=gaps,
        evidence_highlights=evidence_highlights,
        key_metrics=[
            _build_metric("Experience years", f"{payload.experience_years:.1f}"),
            _build_metric("Skills", len(payload.skills or [])),
            _build_metric("Languages", len(payload.languages or [])),
            _build_metric("Experience entries", len(payload.experience_entries or [])),
        ],
        tables=tables,
        recommendation=recommendation,
        watchouts=_dedupe_texts(gaps, limit=4),
        next_steps=next_steps,
        data_sources=["structured_result", "cv_analysis"],
    )


def build_evidence_pack_deck_contract(
    *,
    evidenceops_worklog_entries: list[dict[str, Any]] | None = None,
    evidenceops_action_entries: list[dict[str, Any]] | None = None,
) -> GenericExecutiveDeckContract:
    worklog_entries = [item for item in (evidenceops_worklog_entries or []) if isinstance(item, dict)]
    action_entries = [item for item in (evidenceops_action_entries or []) if isinstance(item, dict)]
    if not worklog_entries and not action_entries:
        raise ValueError("Evidence pack deck requires EvidenceOps worklog and/or action store entries.")

    worklog_summary = summarize_evidenceops_worklog(worklog_entries) if worklog_entries else {}
    action_summary = summarize_evidenceops_actions(action_entries) if action_entries else {}
    latest_entry = worklog_entries[-1] if worklog_entries else {}
    latest_findings = latest_entry.get("findings") if isinstance(latest_entry.get("findings"), list) else []
    latest_actions = latest_entry.get("action_items") if isinstance(latest_entry.get("action_items"), list) else []
    recommended_actions = latest_entry.get("recommended_actions") if isinstance(latest_entry.get("recommended_actions"), list) else []
    limitations = latest_entry.get("limitations") if isinstance(latest_entry.get("limitations"), list) else []

    finding_rows = [
        [
            item.get("finding_type") or "finding",
            item.get("title") or item.get("description") or "-",
            item.get("description") or "-",
            " | ".join(item.get("evidence") or []) or "-",
        ]
        for item in latest_findings[:8]
        if isinstance(item, dict)
    ]
    action_rows = [
        [
            item.get("action_type") or "action",
            item.get("description") or "-",
            item.get("owner") or "-",
            item.get("due_date") or "-",
            item.get("status") or "-",
        ]
        for item in (action_entries[:8] if action_entries else latest_actions[:8])
        if isinstance(item, dict)
    ]
    tables = []
    if finding_rows:
        tables.append(
            GenericDeckTableSection(
                title="Findings",
                columns=["Type", "Title", "Description", "Evidence"],
                rows=_normalize_table_rows(finding_rows),
            )
        )
    if action_rows:
        tables.append(
            GenericDeckTableSection(
                title="Action status",
                columns=["Type", "Action", "Owner", "Due", "Status"],
                rows=_normalize_table_rows(action_rows),
            )
        )
    watchouts = []
    if int(action_summary.get("unassigned_open_actions") or 0) > 0:
        watchouts.append("Há ações abertas sem owner definido no action store.")
    if int(action_summary.get("pending_approval_actions") or 0) > 0:
        watchouts.append("Há ações sensíveis pendentes de aprovação.")
    watchouts.extend(limitations)

    return GenericExecutiveDeckContract(
        export_kind=EVIDENCE_PACK_EXPORT_KIND,
        deck_family="evidence_audit",
        presentation=PresentationExportMetadata(
            title="AI Workbench Local — Evidence Pack Review",
            subtitle="Audit / compliance executive handoff grounded in EvidenceOps",
            author=DEFAULT_PRESENTATION_AUTHOR,
            date=date.today().isoformat(),
            theme=DEFAULT_PRESENTATION_THEME,
            footer_text="AI Workbench Local • Evidence Pack",
        ),
        context={
            "review_type": latest_entry.get("review_type") if isinstance(latest_entry, dict) else None,
            "workflow_id": latest_entry.get("workflow_id") if isinstance(latest_entry, dict) else None,
        },
        executive_summary=_clean_text(latest_entry.get("summary"))
        or (
            f"EvidenceOps consolidou {int(worklog_summary.get('total_findings') or 0)} finding(s), "
            f"{int(worklog_summary.get('total_action_items') or 0)} action item(ns) e "
            f"{int(action_summary.get('open_actions') or 0)} ação(ões) aberta(s) no backlog atual."
        ),
        key_highlights=_dedupe_texts(
            [
                *(item.get("title") for item in latest_findings if isinstance(item, dict)),
                *(recommended_actions or []),
            ],
            limit=6,
        ),
        key_metrics=[
            _build_metric("Findings", int(worklog_summary.get("total_findings") or 0)),
            _build_metric("Action items", int(worklog_summary.get("total_action_items") or 0)),
            _build_metric("Open actions", int(action_summary.get("open_actions") or 0)),
            _build_metric("Unique docs", int(worklog_summary.get("unique_document_count") or 0)),
        ],
        tables=tables,
        recommendation=_recommended_action_or_fallback(
            _dedupe_texts(list(recommended_actions or []), limit=4),
            "Priorizar o fechamento dos findings críticos e consolidar o handoff executivo do evidence pack.",
        ),
        watchouts=_dedupe_texts(watchouts, limit=4),
        next_steps=_dedupe_texts(
            [
                *(recommended_actions or []),
                *(entry.get("description") for entry in action_entries if isinstance(entry, dict) and str(entry.get("status") or "").strip().lower() in {"open", "recommended", "suggested", "pending"}),
            ],
            limit=6,
        ),
        data_sources=["evidenceops_worklog", "evidenceops_action_store"],
    )


def build_executive_deck_contract(
    *,
    export_kind: str,
    model_comparison_entries: list[dict[str, Any]] | None = None,
    eval_entries: list[dict[str, Any]] | None = None,
    structured_result: StructuredResult | dict[str, Any] | None = None,
    evidenceops_worklog_entries: list[dict[str, Any]] | None = None,
    evidenceops_action_entries: list[dict[str, Any]] | None = None,
) -> ExecutiveDeckContract:
    export_kind = normalize_executive_deck_export_kind(export_kind)
    if export_kind == DEFAULT_PRESENTATION_EXPORT_KIND:
        return build_benchmark_eval_contract_from_logs(
            model_comparison_entries=model_comparison_entries,
            eval_entries=eval_entries,
        )
    if export_kind == DOCUMENT_REVIEW_EXPORT_KIND:
        if structured_result is None:
            raise ValueError("Document review deck requires a structured_result input.")
        return build_document_review_deck_contract(structured_result=structured_result)
    if export_kind == POLICY_CONTRACT_COMPARISON_EXPORT_KIND:
        if structured_result is None:
            raise ValueError("Comparison deck requires a structured_result input.")
        return build_policy_contract_comparison_deck_contract(structured_result=structured_result)
    if export_kind == ACTION_PLAN_EXPORT_KIND:
        return build_action_plan_deck_contract(
            structured_result=structured_result,
            evidenceops_action_entries=evidenceops_action_entries,
        )
    if export_kind == CANDIDATE_REVIEW_EXPORT_KIND:
        if structured_result is None:
            raise ValueError("Candidate review deck requires a structured_result input.")
        return build_candidate_review_deck_contract(structured_result=structured_result)
    if export_kind == EVIDENCE_PACK_EXPORT_KIND:
        return build_evidence_pack_deck_contract(
            evidenceops_worklog_entries=evidenceops_worklog_entries,
            evidenceops_action_entries=evidenceops_action_entries,
        )
    raise ValueError(f"Unsupported executive deck export kind: {export_kind}")


def build_ppt_creator_payload_from_executive_deck_contract(
    contract: ExecutiveDeckContract | dict[str, Any],
) -> dict[str, Any]:
    if isinstance(contract, BenchmarkEvalExecutiveDeckContract):
        return build_ppt_creator_payload_from_benchmark_eval_contract(contract)
    if isinstance(contract, dict) and contract.get("export_kind") == DEFAULT_PRESENTATION_EXPORT_KIND:
        return build_ppt_creator_payload_from_benchmark_eval_contract(contract)

    normalized = (
        contract
        if isinstance(contract, GenericExecutiveDeckContract)
        else GenericExecutiveDeckContract.model_validate(contract)
    )
    data_sources_text = ", ".join(normalized.data_sources) if normalized.data_sources else "n/a"
    metric_map = {str(item.label): str(item.value) for item in normalized.key_metrics}
    slides: list[PptCreatorSlide] = [
        PptCreatorSlide(
            type="title",
            title=normalized.presentation.title,
            subtitle=normalized.presentation.subtitle,
            speaker_notes=f"Export kind: {normalized.export_kind}. Deck family: {normalized.deck_family}. Sources: {data_sources_text}.",
        ),
        PptCreatorSlide(
            type="summary",
            title="Executive summary",
            body=normalized.executive_summary,
            bullets=_compact_text_list(normalized.key_highlights, limit=3, max_chars=76),
            speaker_notes="Resumo executivo consolidado a partir dos sinais grounded do produto.",
        ),
    ]
    if normalized.key_metrics:
        slides.append(
            PptCreatorSlide(
                type="metrics",
                title="Executive snapshot",
                metrics=[
                    PptCreatorMetricItem(
                        value=item.value,
                        label=item.label,
                        detail=item.detail,
                        trend=item.trend,
                    )
                    for item in normalized.key_metrics[:4]
                ],
            )
        )

    if normalized.export_kind == ACTION_PLAN_EXPORT_KIND:
        open_actions = metric_map.get("Open", "0")
        overdue_actions = metric_map.get("Overdue", "0")
        approval_required = metric_map.get("Approval required", "0")
        action_execution_steps = _compact_text_list(
            [
                f"Assign owners to the {open_actions} open action(s)",
                "Validate cited evidence before acting on the backlog",
                "Close the human-review gate before final decision",
                "Reprioritize overdue actions" if overdue_actions != "0" else None,
                "Escalate approval-required items" if approval_required != "0" else None,
            ],
            limit=3,
            max_chars=70,
        )
        slides[1] = PptCreatorSlide(
            type="summary",
            title="Executive summary",
            body=(
                f"{open_actions} open action(s) remain in the backlog and require owner assignment plus execution sequencing before closure."
            ),
            bullets=_compact_text_list(
                [
                    f"{metric_map.get('Total actions', open_actions)} total actions are tracked in this backlog",
                    _humanize_watchout(normalized.watchouts[0]) if normalized.watchouts else None,
                    "Human review remains the final decision gate",
                ],
                limit=2,
                max_chars=68,
            ),
            speaker_notes="Short executive framing for the backlog state and required execution posture.",
        )
        action_table = normalized.tables[0] if normalized.tables else None
        compact_action_rows: list[list[str]] = []
        seen_actions: set[str] = set()
        if action_table:
            for row in action_table.rows:
                if len(row) < 5:
                    continue
                action_label = str(row[1]).strip()
                key = action_label.casefold()
                if key in seen_actions:
                    continue
                seen_actions.add(key)
                compact_action_rows.append([
                    _truncate_cell(action_label, max_chars=44),
                    row[2] if row[2] and row[2] != "-" else "Unassigned",
                    str(row[4]).strip().title() or "Open",
                ])
        priority_signals = action_execution_steps[:2] or _compact_text_list(normalized.next_steps or normalized.key_highlights, limit=2, max_chars=68)
        priority_cards = [
            PptCreatorCardItem(title=f"Priority {index}", body=item, footer="Open")
            for index, item in enumerate(priority_signals, start=1)
        ]
        priority_cards.append(
            PptCreatorCardItem(
                title="Execution posture",
                body=(_humanize_watchout(normalized.watchouts[0]) if normalized.watchouts else "Backlog requires owners and sequencing before execution."),
                footer="Risk signal",
            )
        )
        slides.append(_build_cards_slide("Priority workstreams", priority_cards, speaker_notes="Priority actions grouped as execution workstreams."))
        if compact_action_rows:
            slides.append(
                PptCreatorSlide(
                    type="table",
                    title="Action backlog",
                    table_columns=["Action", "Owner", "Status"],
                    table_rows=compact_action_rows[:8],
                )
            )
        timeline_slide = _build_timeline_slide("Execution timeline", action_execution_steps, speaker_notes="Condensed execution sequence.")
        if timeline_slide is not None:
            slides.append(timeline_slide)
        slides.append(
            _build_two_column_slide(
                "Blockers vs mitigations",
                left_title="Blockers",
                left_body=_humanize_watchout(normalized.watchouts[0]) if normalized.watchouts else "No major blocker flagged in the backlog.",
                left_bullets=_compact_text_list(
                    [
                        "Overdue actions require reprioritization" if overdue_actions != "0" else None,
                        "Formal approval is still required for some items" if approval_required != "0" else None,
                    ],
                    limit=1,
                    max_chars=66,
                ),
                right_title="Mitigations",
                right_body="Assign owners, validate evidence and close the human-review gate before execution.",
                right_bullets=_compact_text_list(action_execution_steps, limit=1, max_chars=66),
                speaker_notes="Execution blockers versus mitigation actions.",
            )
        )
    elif normalized.export_kind == EVIDENCE_PACK_EXPORT_KIND:
        review_type = _humanize_watchout((normalized.context or {}).get("review_type")) or "Evidence review"
        evidence_execution_steps = _compact_text_list(
            [
                "Assign an owner to the missing migration task",
                "Validate source snippets before external handoff",
                "Keep human review active until evidence closure",
            ],
            limit=3,
            max_chars=70,
        )
        slides[1] = PptCreatorSlide(
            type="summary",
            title="Executive summary",
            body=(
                f"{review_type} surfaced {metric_map.get('Findings', '0')} key finding(s), "
                f"{metric_map.get('Open actions', '0')} open action(s) and a live human-review requirement for this audit slice."
            ),
            bullets=_compact_text_list(
                [
                    f"{metric_map.get('Findings', '0')} grounded finding(s) in the current review",
                    f"{metric_map.get('Open actions', '0')} open follow-up action(s) remain",
                    "Human review gate is still active",
                ],
                limit=2,
                max_chars=66,
            ),
            speaker_notes="Reframed summary for audit / evidence executive handoff.",
        )
        for table in normalized.tables[:2]:
            if not (table.columns and table.rows):
                continue
            if table.title == "Findings":
                compact_rows = []
                for row in table.rows:
                    if len(row) < 4:
                        continue
                    compact_rows.append([row[0], _truncate_cell(row[1], max_chars=44), _truncate_cell(row[3] or row[2], max_chars=54)])
                slides.append(
                    PptCreatorSlide(
                        type="table",
                        title=table.title,
                        table_columns=["Type", "Finding", "Evidence"],
                        table_rows=compact_rows[:8],
                        speaker_notes=table.speaker_notes,
                    )
                )
            elif table.title == "Action status":
                compact_rows = []
                seen_actions: set[str] = set()
                for row in table.rows:
                    if len(row) < 5:
                        continue
                    key = str(row[1]).strip().casefold()
                    if key in seen_actions:
                        continue
                    seen_actions.add(key)
                    compact_rows.append([
                        _truncate_cell(row[1], max_chars=44),
                        row[2] if row[2] and row[2] != "-" else "Unassigned",
                        str(row[4]).strip().title() or "Open",
                    ])
                slides.append(
                    PptCreatorSlide(
                        type="table",
                        title=table.title,
                        table_columns=["Action", "Owner", "Status"],
                        table_rows=compact_rows[:8],
                        speaker_notes=table.speaker_notes,
                    )
                )
        slides.append(
            _build_two_column_slide(
                "Risks vs mitigations",
                left_title="Risks / watchouts",
                left_body=_compact_text_list(normalized.key_highlights, limit=1, max_chars=68)[0] if normalized.key_highlights else (_humanize_watchout(normalized.watchouts[0]) if normalized.watchouts else "No critical unresolved risk was captured in this slice."),
                left_bullets=_compact_text_list([_humanize_watchout(item) for item in normalized.watchouts[:1]], limit=1, max_chars=64),
                right_title="Mitigations / actions",
                right_body="Assign an owner, validate evidence and confirm human sign-off before externalizing the pack.",
                right_bullets=_compact_text_list(evidence_execution_steps, limit=1, max_chars=64),
                speaker_notes="Risk versus mitigation framing for the evidence pack handoff.",
            )
        )
        if normalized.next_steps:
            slides.append(
                PptCreatorSlide(
                    type="bullets",
                    title="Next steps",
                    bullets=evidence_execution_steps,
                )
            )
    elif normalized.export_kind == CANDIDATE_REVIEW_EXPORT_KIND:
        strength_source = normalized.strengths or normalized.key_highlights
        strength_cards = [
            PptCreatorCardItem(title=f"Strength {index}", body=item, footer="Positive signal")
            for index, item in enumerate(_compact_text_list(strength_source, limit=3, max_chars=70), start=1)
        ]
        slides.append(_build_cards_slide("Strengths snapshot", strength_cards, speaker_notes="Top candidate strengths."))
        if normalized.evidence_highlights:
            slides.append(
                PptCreatorSlide(
                    type="table",
                    title="Evidence highlights",
                    table_columns=["Signal", "Value", "Detail"],
                    table_rows=[
                        [item.label, item.value, item.detail or "-"]
                        for item in normalized.evidence_highlights[:6]
                    ],
                    speaker_notes="Grounded evidence highlights supporting the candidate review.",
                )
            )
        if normalized.tables:
            primary_table = normalized.tables[0]
            slides.append(
                PptCreatorSlide(
                    type="table",
                    title=primary_table.title,
                    table_columns=primary_table.columns,
                    table_rows=primary_table.rows,
                    speaker_notes=primary_table.speaker_notes,
                )
            )
        slides.append(
            _build_two_column_slide(
                "Gaps vs hiring thesis",
                left_title="Gaps / risks",
                left_body=_humanize_watchout((normalized.gaps or normalized.watchouts)[0]) if (normalized.gaps or normalized.watchouts) else "No critical gap surfaced in the structured review.",
                left_bullets=_compact_text_list([_humanize_watchout(item) for item in (normalized.gaps or normalized.watchouts)[1:]], limit=2, max_chars=72),
                right_title="Hiring thesis",
                right_body=normalized.recommendation or "Proceed to interview with focused validation.",
                right_bullets=_compact_text_list(normalized.next_steps[:2], limit=2, max_chars=72),
                speaker_notes="Candidate gaps versus hiring thesis.",
            )
        )
        if normalized.next_steps:
            slides.append(
                PptCreatorSlide(
                    type="bullets",
                    title="Next steps",
                    bullets=_compact_text_list(normalized.next_steps, limit=4, max_chars=80),
                )
            )
    elif normalized.export_kind == DOCUMENT_REVIEW_EXPORT_KIND:
        for table in normalized.tables[:2]:
            if not (table.columns and table.rows):
                continue
            if table.title == "Top findings":
                compact_rows = []
                for row in table.rows:
                    if len(row) < 5:
                        continue
                    compact_rows.append([row[0], _truncate_cell(row[1], max_chars=46), _truncate_cell(row[4] or row[3] or row[2], max_chars=52), row[2]])
                slides.append(
                    PptCreatorSlide(
                        type="table",
                        title=table.title,
                        table_columns=["Type", "Finding", "Evidence", "Owner"],
                        table_rows=compact_rows[:8],
                        speaker_notes=table.speaker_notes,
                    )
                )
            else:
                slides.append(
                    PptCreatorSlide(
                        type="table",
                        title=table.title,
                        table_columns=table.columns,
                        table_rows=table.rows,
                        speaker_notes=table.speaker_notes,
                    )
                )
        slides.append(
            _build_two_column_slide(
                "Recommendation vs watchouts",
                left_title="Recommendation",
                left_body=normalized.recommendation or "Proceed with grounded review and human validation.",
                left_bullets=_compact_text_list(normalized.next_steps[:2], limit=2, max_chars=72),
                right_title="Watchouts",
                right_body=_humanize_watchout(normalized.watchouts[0]) if normalized.watchouts else "No critical watchout recorded for this slice.",
                right_bullets=_compact_text_list([_humanize_watchout(item) for item in normalized.watchouts[1:]], limit=2, max_chars=72),
                speaker_notes="Decision framing for the grounded document review.",
            )
        )
        if normalized.next_steps:
            slides.append(
                PptCreatorSlide(
                    type="bullets",
                    title="Next steps",
                    bullets=_compact_text_list(normalized.next_steps, limit=4, max_chars=80),
                )
            )
    else:
        for table in normalized.tables[:3]:
            if table.columns and table.rows:
                slides.append(
                    PptCreatorSlide(
                        type="table",
                        title=table.title,
                        table_columns=table.columns,
                        table_rows=table.rows,
                        speaker_notes=table.speaker_notes,
                    )
                )
        slides.append(
            _build_two_column_slide(
                "Recommendation vs watchouts",
                left_title="Recommendation",
                left_body=normalized.recommendation or "Proceed with grounded review and human validation.",
                left_bullets=_compact_text_list(normalized.next_steps[:2], limit=2, max_chars=72),
                right_title="Watchouts",
                right_body=_humanize_watchout(normalized.watchouts[0]) if normalized.watchouts else "No critical watchouts recorded for this slice.",
                right_bullets=_compact_text_list([_humanize_watchout(item) for item in normalized.watchouts[1:]], limit=2, max_chars=72),
                speaker_notes="Executive decision framing for this slice.",
            )
        )
        if normalized.next_steps:
            slides.append(
                PptCreatorSlide(
                    type="bullets",
                    title="Next steps",
                    bullets=_compact_text_list(normalized.next_steps, limit=4, max_chars=80),
                )
            )
    payload = PptCreatorPresentationRequest(
        presentation=PptCreatorPresentationMeta(
            title=normalized.presentation.title,
            subtitle=normalized.presentation.subtitle,
            author=normalized.presentation.author,
            date=normalized.presentation.date,
            theme=normalized.presentation.theme,
            footer_text=normalized.presentation.footer_text,
        ),
        slides=slides,
    )
    return payload.model_dump(exclude_none=True)
