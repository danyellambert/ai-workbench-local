from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import ValidationError

from ppt_creator.preview import (
    render_previews_for_rendered_artifact,
)
from ppt_creator.qa import review_presentation
from ppt_creator.renderer import PresentationRenderer
from ppt_creator.schema import PresentationInput
from ppt_creator_ai.briefing import (
    BriefingInput,
    build_generation_feedback_from_preview,
    build_generation_feedback_from_review,
    build_slide_critiques_from_review,
)
from ppt_creator_ai.evals import run_generation_benchmark
from ppt_creator_ai.providers import get_provider, list_provider_names
from ppt_creator_ai.refine import refine_presentation_input


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate deck JSON from a structured briefing.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate", help="Generate presentation JSON from briefing JSON")
    generate_parser.add_argument("input_briefing", help="Path to the structured briefing JSON")
    generate_parser.add_argument("output_json", help="Destination deck JSON path")
    generate_parser.add_argument(
        "--provider",
        default="heuristic",
        choices=list_provider_names(),
        help="Provider used to transform briefing into deck JSON",
    )
    generate_parser.add_argument("--theme", help="Override the theme declared in the briefing")
    generate_parser.add_argument(
        "--analysis-json",
        help="Optional path to write a JSON analysis report with summary bullets, image suggestions, and density review",
    )
    generate_parser.add_argument(
        "--review-json",
        help="Optional path to write a heuristic QA review for the generated deck JSON",
    )
    generate_parser.add_argument(
        "--render-pptx",
        help="Optional path to immediately render the generated deck into a .pptx file",
    )
    generate_parser.add_argument(
        "--asset-root",
        help="Optional asset root to use when rendering the generated deck or reviewing asset references",
    )
    generate_parser.add_argument(
        "--preview-dir",
        help="Optional directory to generate PNG previews for the generated deck",
    )
    generate_parser.add_argument(
        "--preview-report-json",
        help="Optional path to write a JSON report for the generated preview set",
    )
    generate_parser.add_argument(
        "--preview-backend",
        choices=["auto", "synthetic", "office"],
        default="auto",
        help="Preview backend used when --preview-dir is requested",
    )
    generate_parser.add_argument(
        "--preview-baseline-dir",
        help="Optional baseline preview directory for visual regression when generating previews",
    )
    generate_parser.add_argument(
        "--preview-write-diff-images",
        action="store_true",
        help="Write diff images when preview regression is enabled",
    )
    generate_parser.add_argument(
        "--preview-from-rendered-pptx",
        action="store_true",
        help="When rendering a PPTX in the same run, derive previews from the final rendered .pptx instead of the intermediate JSON/spec path",
    )
    generate_parser.add_argument(
        "--auto-regenerate",
        action="store_true",
        help="Ask the provider to regenerate the deck using heuristic QA feedback when review flags issues",
    )
    generate_parser.add_argument(
        "--regenerate-passes",
        type=int,
        default=1,
        help="Maximum number of provider regeneration passes to attempt when --auto-regenerate is enabled",
    )
    generate_parser.add_argument(
        "--auto-refine",
        action="store_true",
        help="Run a heuristic refine pass on the generated deck when QA signals issues",
    )
    generate_parser.add_argument(
        "--refine-passes",
        type=int,
        default=1,
        help="Maximum number of heuristic refine passes to attempt when --auto-refine is enabled",
    )
    generate_parser.add_argument(
        "--auto-llm-review",
        action="store_true",
        help="Ask the selected provider to revise the generated deck using QA review + slide critiques",
    )
    generate_parser.add_argument(
        "--llm-review-passes",
        type=int,
        default=1,
        help="Maximum number of provider-backed post-QA review/revision passes to attempt when --auto-llm-review is enabled",
    )
    generate_parser.add_argument(
        "--llm-critique-json",
        help="Optional path to write slide-by-slide provider-backed critique JSON combining briefing + QA feedback",
    )
    generate_parser.add_argument("--report-json", help="Optional path to write a JSON generation report")

    benchmark_parser = subparsers.add_parser(
        "benchmark",
        help="Run a prompt-to-deck benchmark across built-in briefing scenarios",
    )
    benchmark_parser.add_argument("output_dir", help="Directory to store optional generated deck JSON artifacts")
    benchmark_parser.add_argument(
        "--provider",
        default="heuristic",
        choices=list_provider_names(),
        help="Provider used during the benchmark run",
    )
    benchmark_parser.add_argument(
        "--compare-provider",
        dest="compare_providers",
        action="append",
        choices=list_provider_names(),
        help="Optional additional provider to benchmark side-by-side against the primary provider",
    )
    benchmark_parser.add_argument("--theme", help="Optional theme override applied to every benchmark scenario")
    benchmark_parser.add_argument(
        "--write-json-decks",
        action="store_true",
        help="Persist each generated deck JSON in the benchmark output directory",
    )
    benchmark_parser.add_argument("--report-json", help="Optional path to write the benchmark report JSON")

    providers_parser = subparsers.add_parser("providers", help="List available briefing providers")
    providers_parser.add_argument("--report-json", help="Optional path to write a JSON provider report")
    return parser


def print_error(message: str) -> None:
    print(f"[ERROR] {message}", file=sys.stderr)


def print_info(message: str) -> None:
    print(f"[INFO] {message}")


def write_json(path: str | Path, payload: dict[str, object]) -> Path:
    output_path = Path(path)
    if output_path.suffix.lower() != ".json":
        raise ValueError(f"Output path must end with .json: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def _provider_generate(
    provider,
    briefing: BriefingInput,
    *,
    theme_name: str | None = None,
    feedback_messages: list[str] | None = None,
):
    if feedback_messages:
        return provider.generate(briefing, theme_name=theme_name, feedback_messages=feedback_messages)
    return provider.generate(briefing, theme_name=theme_name)


def _merge_feedback_messages(*message_groups: list[str]) -> list[str]:
    merged: list[str] = []
    for group in message_groups:
        for message in group:
            normalized = message.strip()
            if normalized and normalized not in merged:
                merged.append(normalized)
    return merged


def _preview_feedback_score(preview_result: dict[str, object] | None) -> float | None:
    if not preview_result:
        return None

    artifact_review = preview_result.get("preview_artifact_review") or {}
    visual_regression = preview_result.get("visual_regression") or {}
    quality_review = preview_result.get("quality_review") or {}
    return (
        float(artifact_review.get("edge_contact_count") or 0) * 3.0
        + float(artifact_review.get("safe_area_intrusion_count") or 0) * 3.0
        + float(artifact_review.get("body_edge_contact_count") or 0) * 2.5
        + float(artifact_review.get("footer_intrusion_count") or 0) * 2.0
        + float(artifact_review.get("corner_density_warning_count") or 0) * 1.5
        + float(artifact_review.get("edge_density_warning_count") or 0) * 1.0
        + float(visual_regression.get("diff_count") or 0) * 4.0
        + float(quality_review.get("warning_count") or quality_review.get("issue_count") or 0) * 0.5
    )


def _iteration_stop_reason(
    *,
    before_issue_count: int,
    after_issue_count: int,
    before_average_score: int,
    after_average_score: int,
    before_preview_score: float | None,
    after_preview_score: float | None,
    payload_changed: bool,
) -> tuple[bool, str]:
    if after_issue_count < before_issue_count:
        return True, "issue_count_improved"
    if after_average_score > before_average_score:
        return True, "average_score_improved"
    if (
        before_preview_score is not None
        and after_preview_score is not None
        and after_preview_score < before_preview_score
    ):
        return True, "preview_score_improved"
    if (
        payload_changed
        and after_issue_count <= before_issue_count
        and after_average_score >= before_average_score
        and (
            before_preview_score is None
            or after_preview_score is None
            or after_preview_score <= before_preview_score
        )
    ):
        return True, "payload_changed_without_regression"
    if not payload_changed:
        return False, "no_payload_change"
    if after_issue_count > before_issue_count:
        return False, "issue_count_regressed"
    if after_average_score < before_average_score:
        return False, "average_score_regressed"
    if (
        before_preview_score is not None
        and after_preview_score is not None
        and after_preview_score > before_preview_score
    ):
        return False, "preview_score_regressed"
    return False, "no_material_improvement"


def _build_preview_feedback_for_spec(
    spec: PresentationInput,
    *,
    preview_enabled: bool,
    prefer_rendered_pptx: bool,
    resolved_asset_root: Path,
    preview_backend: str,
    preview_baseline_dir: str | Path | None,
    preview_write_diff_images: bool,
    basename: str,
) -> tuple[dict[str, object] | None, list[str], str | None]:
    if not preview_enabled:
        return None, [], None

    with TemporaryDirectory(prefix="ppt_creator_ai_preview_feedback_") as tmpdir:
        temp_root = Path(tmpdir)
        temp_preview_dir = temp_root / "previews"
        rendered_candidate = None
        if prefer_rendered_pptx:
            temp_pptx = temp_root / f"{basename}.pptx"
            PresentationRenderer(theme_name=spec.presentation.theme, asset_root=resolved_asset_root).render(spec, temp_pptx)
            rendered_candidate = temp_pptx

        preview_result, preview_source = render_previews_for_rendered_artifact(
            spec,
            temp_preview_dir,
            rendered_pptx=rendered_candidate,
            theme_name=spec.presentation.theme,
            asset_root=resolved_asset_root,
            basename=basename,
            backend=preview_backend,
            baseline_dir=preview_baseline_dir,
            write_diff_images=preview_write_diff_images,
        )

    return preview_result, build_generation_feedback_from_preview(preview_result), preview_source


def generate_from_briefing(
    input_briefing: str | Path,
    output_json: str | Path,
    *,
    provider_name: str = "heuristic",
    theme_name: str | None = None,
    analysis_json: str | Path | None = None,
    review_json: str | Path | None = None,
    render_pptx: str | Path | None = None,
    asset_root: str | Path | None = None,
    preview_dir: str | Path | None = None,
    preview_report_json: str | Path | None = None,
    preview_backend: str = "auto",
    preview_baseline_dir: str | Path | None = None,
    preview_write_diff_images: bool = False,
    preview_from_rendered_pptx: bool = False,
    auto_regenerate: bool = False,
    regenerate_passes: int = 1,
    auto_refine: bool = False,
    refine_passes: int = 1,
    auto_llm_review: bool = False,
    llm_review_passes: int = 1,
    llm_critique_json: str | Path | None = None,
) -> dict[str, object]:
    input_path = Path(input_briefing)
    output_json_path = Path(output_json)
    preview_feedback_basename = output_json_path.stem
    print_info(f"Loading briefing: {input_path}")
    briefing = BriefingInput.from_path(input_path)
    provider = get_provider(provider_name)
    print_info(f"Using provider: {provider.name}")
    result = _provider_generate(provider, briefing, theme_name=theme_name)
    payload = result.payload
    spec = PresentationInput.model_validate(payload)
    resolved_asset_root = Path(asset_root).resolve() if asset_root else input_path.parent.resolve()
    analysis_path: str | None = None
    analysis = result.analysis
    initial_deck_review = review_presentation(spec, asset_root=resolved_asset_root, theme_name=spec.presentation.theme)
    deck_review = initial_deck_review
    preview_feedback_enabled = bool(preview_dir)
    regeneration_history: list[dict[str, object]] = []
    regenerate_applied = False

    if auto_regenerate:
        current_result = result
        current_spec = spec
        current_review = initial_deck_review
        current_preview_result, current_preview_feedback, current_preview_source = _build_preview_feedback_for_spec(
            current_spec,
            preview_enabled=preview_feedback_enabled,
            prefer_rendered_pptx=preview_from_rendered_pptx or preview_backend != "synthetic",
            resolved_asset_root=resolved_asset_root,
            preview_backend=preview_backend,
            preview_baseline_dir=preview_baseline_dir,
            preview_write_diff_images=preview_write_diff_images,
            basename=preview_feedback_basename,
        )
        current_preview_score = _preview_feedback_score(current_preview_result)
        for pass_index in range(max(1, regenerate_passes)):
            if current_review["issue_count"] == 0 and (current_preview_score is None or current_preview_score == 0):
                break
            feedback_messages = _merge_feedback_messages(
                build_generation_feedback_from_review(current_review),
                current_preview_feedback,
            )
            if not feedback_messages:
                break
            candidate_result = _provider_generate(
                provider,
                briefing,
                theme_name=theme_name,
                feedback_messages=feedback_messages,
            )
            candidate_spec = PresentationInput.model_validate(candidate_result.payload)
            candidate_review = review_presentation(
                candidate_spec,
                asset_root=resolved_asset_root,
                theme_name=candidate_spec.presentation.theme,
            )
            candidate_preview_result, candidate_preview_feedback, candidate_preview_source = _build_preview_feedback_for_spec(
                candidate_spec,
                preview_enabled=preview_feedback_enabled,
                prefer_rendered_pptx=preview_from_rendered_pptx or preview_backend != "synthetic",
                resolved_asset_root=resolved_asset_root,
                preview_backend=preview_backend,
                preview_baseline_dir=preview_baseline_dir,
                preview_write_diff_images=preview_write_diff_images,
                basename=preview_feedback_basename,
            )
            candidate_preview_score = _preview_feedback_score(candidate_preview_result)
            payload_changed = candidate_spec.model_dump(mode="json") != current_spec.model_dump(mode="json")
            regeneration_history.append(
                {
                    "pass": pass_index + 1,
                    "feedback_messages": feedback_messages,
                    "before_issue_count": current_review["issue_count"],
                    "after_issue_count": candidate_review["issue_count"],
                    "before_average_score": current_review["average_score"],
                    "after_average_score": candidate_review["average_score"],
                    "preview_feedback_messages": current_preview_feedback,
                    "preview_feedback_source": current_preview_source,
                    "before_preview_score": current_preview_score,
                    "after_preview_score": candidate_preview_score,
                }
            )
            improved, stop_reason = _iteration_stop_reason(
                before_issue_count=current_review["issue_count"],
                after_issue_count=candidate_review["issue_count"],
                before_average_score=current_review["average_score"],
                after_average_score=candidate_review["average_score"],
                before_preview_score=current_preview_score,
                after_preview_score=candidate_preview_score,
                payload_changed=payload_changed,
            )
            regeneration_history[-1]["decision"] = stop_reason
            if not improved:
                break
            current_result = candidate_result
            current_spec = candidate_spec
            current_review = candidate_review
            current_preview_result = candidate_preview_result
            current_preview_feedback = candidate_preview_feedback
            current_preview_source = candidate_preview_source
            current_preview_score = candidate_preview_score
            regenerate_applied = True

        result = current_result
        analysis = current_result.analysis
        spec = current_spec
        deck_review = current_review

    refinement_history: list[dict[str, object]] = []
    refine_applied = False

    if auto_refine:
        current_spec = spec
        current_review = deck_review
        current_preview_result, _, _ = _build_preview_feedback_for_spec(
            current_spec,
            preview_enabled=preview_feedback_enabled,
            prefer_rendered_pptx=preview_from_rendered_pptx or preview_backend != "synthetic",
            resolved_asset_root=resolved_asset_root,
            preview_backend=preview_backend,
            preview_baseline_dir=preview_baseline_dir,
            preview_write_diff_images=preview_write_diff_images,
            basename=preview_feedback_basename,
        )
        current_preview_score = _preview_feedback_score(current_preview_result)
        for pass_index in range(max(1, refine_passes)):
            if current_review["issue_count"] == 0 and (current_preview_score is None or current_preview_score == 0):
                break
            candidate_spec = refine_presentation_input(
                current_spec,
                review=current_review,
                briefing=briefing,
                slide_critiques=build_slide_critiques_from_review(current_spec, current_review),
            )
            candidate_review = review_presentation(
                candidate_spec,
                asset_root=resolved_asset_root,
                theme_name=candidate_spec.presentation.theme,
            )
            candidate_preview_result, _, _ = _build_preview_feedback_for_spec(
                candidate_spec,
                preview_enabled=preview_feedback_enabled,
                prefer_rendered_pptx=preview_from_rendered_pptx or preview_backend != "synthetic",
                resolved_asset_root=resolved_asset_root,
                preview_backend=preview_backend,
                preview_baseline_dir=preview_baseline_dir,
                preview_write_diff_images=preview_write_diff_images,
                basename=preview_feedback_basename,
            )
            candidate_preview_score = _preview_feedback_score(candidate_preview_result)
            refinement_history.append(
                {
                    "pass": pass_index + 1,
                    "before_issue_count": current_review["issue_count"],
                    "after_issue_count": candidate_review["issue_count"],
                    "before_average_score": current_review["average_score"],
                    "after_average_score": candidate_review["average_score"],
                    "before_preview_score": current_preview_score,
                    "after_preview_score": candidate_preview_score,
                }
            )
            payload_changed = candidate_spec.model_dump(mode="json") != current_spec.model_dump(mode="json")
            improved, stop_reason = _iteration_stop_reason(
                before_issue_count=current_review["issue_count"],
                after_issue_count=candidate_review["issue_count"],
                before_average_score=current_review["average_score"],
                after_average_score=candidate_review["average_score"],
                before_preview_score=current_preview_score,
                after_preview_score=candidate_preview_score,
                payload_changed=payload_changed,
            )
            refinement_history[-1]["decision"] = stop_reason
            if not improved:
                break
            current_spec = candidate_spec
            current_review = candidate_review
            current_preview_score = candidate_preview_score
            refine_applied = True
        spec = current_spec
        deck_review = current_review

    llm_review_history: list[dict[str, object]] = []
    llm_review_applied = False

    if auto_llm_review:
        revision_callable = getattr(provider, "revise_generated_deck", None)
        if not callable(revision_callable):
            raise ValueError(f"Provider '{provider.name}' does not support post-QA LLM review")

        current_result = result
        current_spec = spec
        current_review = deck_review
        current_preview_result, current_preview_feedback, current_preview_source = _build_preview_feedback_for_spec(
            current_spec,
            preview_enabled=preview_feedback_enabled,
            prefer_rendered_pptx=preview_from_rendered_pptx or preview_backend != "synthetic",
            resolved_asset_root=resolved_asset_root,
            preview_backend=preview_backend,
            preview_baseline_dir=preview_baseline_dir,
            preview_write_diff_images=preview_write_diff_images,
            basename=preview_feedback_basename,
        )
        current_preview_score = _preview_feedback_score(current_preview_result)

        for pass_index in range(max(1, llm_review_passes)):
            if current_review["issue_count"] == 0 and (current_preview_score is None or current_preview_score == 0):
                break

            current_slide_critiques = build_slide_critiques_from_review(current_spec, current_review)
            feedback_messages = _merge_feedback_messages(
                build_generation_feedback_from_review(current_review),
                current_preview_feedback,
            )
            candidate_result = revision_callable(
                briefing,
                current_spec.model_dump(mode="json"),
                current_review,
                current_slide_critiques,
                theme_name=theme_name,
                feedback_messages=feedback_messages,
            )
            candidate_spec = PresentationInput.model_validate(candidate_result.payload)
            candidate_review = review_presentation(
                candidate_spec,
                asset_root=resolved_asset_root,
                theme_name=candidate_spec.presentation.theme,
            )
            candidate_preview_result, candidate_preview_feedback, candidate_preview_source = _build_preview_feedback_for_spec(
                candidate_spec,
                preview_enabled=preview_feedback_enabled,
                prefer_rendered_pptx=preview_from_rendered_pptx or preview_backend != "synthetic",
                resolved_asset_root=resolved_asset_root,
                preview_backend=preview_backend,
                preview_baseline_dir=preview_baseline_dir,
                preview_write_diff_images=preview_write_diff_images,
                basename=preview_feedback_basename,
            )
            candidate_preview_score = _preview_feedback_score(candidate_preview_result)
            payload_changed = candidate_spec.model_dump(mode="json") != current_spec.model_dump(mode="json")
            llm_review_history.append(
                {
                    "pass": pass_index + 1,
                    "feedback_messages": feedback_messages,
                    "slide_critique_count": len(current_slide_critiques),
                    "before_issue_count": current_review["issue_count"],
                    "after_issue_count": candidate_review["issue_count"],
                    "before_average_score": current_review["average_score"],
                    "after_average_score": candidate_review["average_score"],
                    "preview_feedback_source": current_preview_source,
                    "before_preview_score": current_preview_score,
                    "after_preview_score": candidate_preview_score,
                }
            )
            improved, stop_reason = _iteration_stop_reason(
                before_issue_count=current_review["issue_count"],
                after_issue_count=candidate_review["issue_count"],
                before_average_score=current_review["average_score"],
                after_average_score=candidate_review["average_score"],
                before_preview_score=current_preview_score,
                after_preview_score=candidate_preview_score,
                payload_changed=payload_changed,
            )
            llm_review_history[-1]["decision"] = stop_reason
            if not improved:
                break

            current_result = candidate_result
            current_spec = candidate_spec
            current_review = candidate_review
            current_preview_result = candidate_preview_result
            current_preview_feedback = candidate_preview_feedback
            current_preview_source = candidate_preview_source
            current_preview_score = candidate_preview_score
            llm_review_applied = True

        result = current_result
        analysis = current_result.analysis
        spec = current_spec
        deck_review = current_review

    slide_critiques = build_slide_critiques_from_review(spec, deck_review)
    llm_slide_critiques: list[dict[str, object]] | None = None
    llm_critique_output_path: str | None = None
    if llm_critique_json:
        critique_preview_result, critique_preview_feedback, critique_preview_source = _build_preview_feedback_for_spec(
            spec,
            preview_enabled=preview_feedback_enabled,
            prefer_rendered_pptx=preview_from_rendered_pptx or preview_backend != "synthetic",
            resolved_asset_root=resolved_asset_root,
            preview_backend=preview_backend,
            preview_baseline_dir=preview_baseline_dir,
            preview_write_diff_images=preview_write_diff_images,
            basename=preview_feedback_basename,
        )
        critique_result = provider.critique_generated_deck(
            briefing,
            spec.model_dump(mode="json"),
            deck_review,
            slide_critiques,
            theme_name=theme_name,
            feedback_messages=_merge_feedback_messages(
                build_generation_feedback_from_review(deck_review),
                critique_preview_feedback,
            ),
        )
        llm_slide_critiques = critique_result.critiques
        llm_critique_payload = {
            "provider": critique_result.provider_name,
            "analysis": critique_result.analysis,
            "preview_feedback_source": critique_preview_source,
            "critiques": llm_slide_critiques,
            "preview_feedback_enabled": bool(critique_preview_result),
        }
        llm_critique_output_path = str(write_json(llm_critique_json, llm_critique_payload))

    payload = spec.model_dump(mode="json")
    output_path = write_json(output_json, payload)
    review_path: str | None = None
    rendered_pptx_path: str | None = None
    preview_path: str | None = None
    preview_result: dict[str, object] | None = None
    preview_source: str | None = None
    if analysis_json:
        analysis_output = write_json(
            analysis_json,
            {
                **analysis,
                "initial_generated_deck_review": initial_deck_review,
                "generated_deck_review": deck_review,
                "regeneration_history": regeneration_history,
                "refinement_history": refinement_history,
                "llm_review_history": llm_review_history,
                "slide_critiques": slide_critiques,
                "llm_slide_critiques": llm_slide_critiques,
            },
        )
        analysis_path = str(analysis_output)
    if review_json:
        review_output = write_json(review_json, deck_review)
        review_path = str(review_output)
    if render_pptx:
        renderer = PresentationRenderer(theme_name=spec.presentation.theme, asset_root=resolved_asset_root)
        rendered_output = renderer.render(spec, render_pptx)
        rendered_pptx_path = str(rendered_output)
        print_info(f"Rendered PPTX from generated deck: {rendered_output}")
    if preview_dir:
        preview_output_dir = Path(preview_dir)
        if preview_from_rendered_pptx:
            if not rendered_pptx_path:
                raise ValueError("--preview-from-rendered-pptx requires --render-pptx in the same command")
        effective_preview_backend = preview_backend
        if preview_from_rendered_pptx and effective_preview_backend == "synthetic":
            effective_preview_backend = "auto"
        preview_result, preview_source = render_previews_for_rendered_artifact(
            spec,
            preview_output_dir,
            rendered_pptx=rendered_pptx_path if rendered_pptx_path and effective_preview_backend != "synthetic" else None,
            theme_name=spec.presentation.theme,
            asset_root=resolved_asset_root,
            basename=output_path.stem,
            backend=effective_preview_backend,
            baseline_dir=preview_baseline_dir,
            write_diff_images=preview_write_diff_images,
        )
        preview_path = str(preview_output_dir)
        print_info(f"Generated previews from generated deck: {preview_output_dir}")
        if preview_report_json:
            write_json(preview_report_json, preview_result)
    print(f"[OK] Generated deck JSON: {output_path} ({len(payload['slides'])} slides)")
    preview_quality_review = preview_result.get("quality_review") if preview_result else None
    preview_artifact_review = preview_result.get("preview_artifact_review") if preview_result else None
    preview_visual_regression = preview_result.get("visual_regression") if preview_result else None
    return {
        "mode": "briefing-generate",
        "provider": provider.name,
        "input_briefing": str(input_path),
        "output_json": str(output_path),
        "presentation_title": payload["presentation"]["title"],
        "theme": payload["presentation"]["theme"],
        "slide_count": len(payload["slides"]),
        "analysis_output_json": analysis_path,
        "review_output_json": review_path,
        "render_output_pptx": rendered_pptx_path,
        "preview_output_dir": preview_path,
        "preview_source": preview_source,
        "preview_report_json": str(preview_report_json) if preview_report_json else None,
        "preview_from_rendered_pptx": preview_from_rendered_pptx,
        "auto_regenerate_enabled": auto_regenerate,
        "auto_regenerate_applied": regenerate_applied,
        "regenerate_passes_requested": regenerate_passes if auto_regenerate else 0,
        "regenerate_passes_completed": len(regeneration_history),
        "auto_refine_enabled": auto_refine,
        "auto_refine_applied": refine_applied,
        "refine_passes_requested": refine_passes if auto_refine else 0,
        "refine_passes_completed": len(refinement_history),
        "auto_llm_review_enabled": auto_llm_review,
        "auto_llm_review_applied": llm_review_applied,
        "llm_review_passes_requested": llm_review_passes if auto_llm_review else 0,
        "llm_review_passes_completed": len(llm_review_history),
        "llm_critique_output_json": llm_critique_output_path,
        "llm_slide_critique_count": len(llm_slide_critiques or []),
        "image_suggestion_count": len(analysis["image_suggestions"]),
        "density_review_status": analysis["density_review"]["status"],
        "initial_generated_deck_review_status": initial_deck_review["status"],
        "initial_generated_deck_issue_count": initial_deck_review["issue_count"],
        "generated_deck_review_status": deck_review["status"],
        "generated_deck_issue_count": deck_review["issue_count"],
        "slide_critique_count": len(slide_critiques),
        "preview_quality_review_status": preview_quality_review["status"] if preview_quality_review else None,
        "preview_artifact_review_status": preview_artifact_review["status"] if preview_artifact_review else None,
        "preview_regression_status": preview_visual_regression["status"] if preview_visual_regression else None,
    }


def list_providers() -> dict[str, object]:
    providers = []
    for name in list_provider_names():
        provider = get_provider(name)
        providers.append({"name": provider.name, "description": provider.description})
    print_info(f"Available providers: {', '.join(item['name'] for item in providers)}")
    return {"mode": "briefing-providers", "providers": providers}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "providers":
            result = list_providers()
            if args.report_json:
                write_json(args.report_json, result)
            return 0

        if args.command == "benchmark":
            result = run_generation_benchmark(
                args.output_dir,
                provider_name=args.provider,
                compare_provider_names=args.compare_providers,
                theme_name=args.theme,
                write_json_decks=args.write_json_decks,
            )
            if args.report_json:
                write_json(args.report_json, result)
            if result.get("mode") == "briefing-benchmark-comparison":
                summary = result.get("comparison_summary") or {}
                print(
                    f"[OK] Benchmark comparison finished for {', '.join(result.get('providers', []))}; "
                    f"best provider: {summary.get('best_provider_by_success_then_quality') or 'n/a'}"
                )
            else:
                print(
                    f"[OK] Benchmark finished: {result['successful_generations']}/{result['scenario_count']} scenarios valid; "
                    f"{result['unique_slide_type_count']} unique slide types covered"
                )
            return 0

        result = generate_from_briefing(
            args.input_briefing,
            args.output_json,
            provider_name=args.provider,
            theme_name=args.theme,
            analysis_json=args.analysis_json,
            review_json=args.review_json,
            render_pptx=args.render_pptx,
            asset_root=args.asset_root,
            preview_dir=args.preview_dir,
            preview_report_json=args.preview_report_json,
            preview_backend=args.preview_backend,
            preview_baseline_dir=args.preview_baseline_dir,
            preview_write_diff_images=args.preview_write_diff_images,
            preview_from_rendered_pptx=args.preview_from_rendered_pptx,
            auto_regenerate=args.auto_regenerate,
            regenerate_passes=args.regenerate_passes,
            auto_refine=args.auto_refine,
            refine_passes=args.refine_passes,
            auto_llm_review=args.auto_llm_review,
            llm_review_passes=args.llm_review_passes,
            llm_critique_json=args.llm_critique_json,
        )
        if args.report_json:
            write_json(args.report_json, result)
        return 0
    except FileNotFoundError as exc:
        print_error(str(exc))
        return 2
    except ValidationError as exc:
        print_error(str(exc))
        return 2
    except ValueError as exc:
        print_error(str(exc))
        return 2
    except Exception as exc:
        print_error(f"Unexpected failure: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
