from __future__ import annotations

import json
from pathlib import Path

from ppt_creator.qa import review_presentation
from ppt_creator.schema import PresentationInput
from ppt_creator_ai.briefing import (
    BriefingInput,
    assess_generated_payload_quality,
    build_llm_generation_contract,
)
from ppt_creator_ai.providers import get_provider

BENCHMARK_SCENARIOS: list[dict[str, object]] = [
    {
        "name": "sales_qbr_prompt",
        "briefing": {
            "title": "Sales QBR turnaround",
            "audience": "Revenue leadership",
            "objective": "Tighten the operating rhythm and focus the quarter on higher-conviction deals.",
            "briefing_text": "Pipeline quality is uneven, managers are overloaded with deck preparation, and the quarter needs a narrower execution focus.",
            "metrics": [
                {"label": "Win rate", "value": "31%"},
                {"label": "Pipeline added", "value": "$8.4M"},
                {"label": "Plan attainment", "value": "104%"},
            ],
            "milestones": [
                {"title": "Reset forecast rules", "detail": "Clarify qualification rules and weekly governance.", "phase": "Month 1"},
                {"title": "Coach deal reviews", "detail": "Focus managers on conversion moments.", "phase": "Month 2"},
            ],
            "options": [
                {"title": "Keep current cadence", "body": "More activity, but limited quality improvement."},
                {"title": "Narrow the motion", "bullets": ["Tighter forecast hygiene", "Fewer priorities", "Stronger coaching"]},
            ],
            "faqs": [
                {"question": "What changes first?", "answer": "Forecast governance and deal review discipline."},
                {"question": "How do we measure it?", "answer": "Track conversion lift and slippage reduction."},
            ],
            "recommendations": [
                "Focus the quarter on fewer pipeline moves.",
                "Make forecast governance more explicit.",
                "Use manager coaching on high-value opportunities.",
            ],
        },
    },
    {
        "name": "board_strategy_prompt",
        "briefing": {
            "title": "Board strategy review",
            "audience": "Board of directors",
            "objective": "Turn strategic ambiguity into a clearer sequence of choices.",
            "briefing_text": "The company has too many simultaneous bets, weak sequencing, and recurring debates about where leadership focus should go first.",
            "metrics": [
                {"label": "Priority themes", "value": "5"},
                {"label": "Capital at risk", "value": "$12M"},
                {"label": "Execution score", "value": "68%"},
            ],
            "milestones": [
                {"title": "Diagnose", "detail": "Clarify the critical strategic questions.", "phase": "Q1"},
                {"title": "Decide", "detail": "Choose the explicit trade-offs.", "phase": "Q2"},
                {"title": "Sequence", "detail": "Stage execution deliberately.", "phase": "Q3"},
            ],
            "options": [
                {"title": "Broad portfolio", "body": "Retains optionality but increases management noise."},
                {"title": "Focused portfolio", "bullets": ["Sharper bets", "Better capital discipline", "Faster learning"]},
            ],
            "faqs": [
                {"question": "Why focus now?", "answer": "Because portfolio sprawl is already diluting execution quality."},
                {"question": "What does success look like?", "answer": "Fewer bets with clearer milestone accountability."},
            ],
            "recommendations": [
                "Reduce simultaneous strategic bets.",
                "Sequence investments against explicit milestones.",
                "Use board reviews to reinforce trade-off discipline.",
            ],
        },
    },
    {
        "name": "product_operating_prompt",
        "briefing": {
            "title": "Product operating review",
            "audience": "Product leadership",
            "objective": "Concentrate roadmap effort on the workflows with the strongest adoption pull.",
            "briefing_text": "The product roadmap is too parallel, adoption signals are mixed, and leadership needs a cleaner operating decision for the next quarter.",
            "metrics": [
                {"label": "Active teams", "value": "29"},
                {"label": "Release velocity", "value": "12"},
                {"label": "Adoption lift", "value": "18%"},
            ],
            "milestones": [
                {"title": "Protect core workflow", "detail": "Keep the strongest adoption motion healthy.", "phase": "Sprint 1"},
                {"title": "Pause low-conviction bets", "detail": "Reduce parallel roadmap load.", "phase": "Sprint 2"},
            ],
            "faqs": [
                {"question": "What moves first?", "answer": "The workflow with the strongest usage pull."},
                {"question": "What should wait?", "answer": "Initiatives without a clear adoption signal."},
            ],
            "recommendations": [
                "Concentrate roadmap scope.",
                "Use explicit decision gates.",
                "Tie expansion to adoption evidence.",
            ],
        },
    },
    {
        "name": "consulting_steerco_prompt",
        "briefing": {
            "title": "Consulting steerco",
            "audience": "Steering committee",
            "objective": "Reduce operating complexity before scaling the new model.",
            "briefing_text": "The program is absorbing too much complexity, ownership is unclear, and the steerco needs a cleaner recommendation with a practical action plan.",
            "metrics": [
                {"label": "Workstreams", "value": "7"},
                {"label": "Decision owners", "value": "3"},
                {"label": "Timeline slip", "value": "14%"},
            ],
            "options": [
                {"title": "Scale now", "body": "Keeps momentum but locks in complexity."},
                {"title": "Simplify first", "bullets": ["Clarify decisions", "Reduce scope", "Stabilize governance"]},
            ],
            "faqs": [
                {"question": "Why not scale now?", "answer": "The current model would scale unnecessary complexity."},
                {"question": "What unlocks scale later?", "answer": "Decision clarity and a narrower operating cadence."},
            ],
            "recommendations": [
                "Simplify the model before scaling.",
                "Clarify decision ownership.",
                "Use a staged operating plan.",
            ],
        },
    },
    {
        "name": "ai_engineer_interview_prompt",
        "briefing": {
            "title": "AI Engineer interview",
            "audience": "Hiring panel",
            "objective": "Show technical depth, production execution, and the ability to turn business problems into useful AI systems.",
            "briefing_text": "Create a presentation for an AI Engineer interview covering my background, major AI projects, architecture, production, scalability, measurable results, and the value I can create for the company.",
            "recommendations": [
                "Connect background, technical depth, and real impact.",
                "Show projects with concrete evidence and architecture decisions.",
                "Close with a clear value proposition for the company.",
            ],
        },
    },
    {
        "name": "client_proposal_prompt",
        "briefing": {
            "title": "Client AI proposal",
            "audience": "Client steering committee",
            "objective": "Defend an AI proposal with clear differentiators, evidence, risks, and a credible execution plan.",
            "briefing_text": "Build a proposal deck for a client explaining why this AI approach is the best commercial option, with differentiators, risks, expected metrics, and a phased execution plan.",
            "metrics": [
                {"label": "Savings potential", "value": "$2.4M"},
                {"label": "Cycle-time reduction", "value": "22%"},
                {"label": "Adoption target", "value": "70%"},
            ],
            "milestones": [
                {"title": "Diagnose workflows", "detail": "Map the highest-friction process", "phase": "Month 1"},
                {"title": "Pilot one workflow", "detail": "Instrument success and adoption", "phase": "Month 2"},
            ],
            "options": [
                {"title": "Generic automation", "body": "Lower commitment but weaker differentiation."},
                {"title": "Tailored AI workflow", "bullets": ["Better fit", "Stronger adoption", "Higher strategic value"]},
            ],
            "faqs": [
                {"question": "Why this approach?", "answer": "It balances value, feasibility and measurable rollout."},
                {"question": "What is the main risk?", "answer": "Scaling before usage evidence is clear."},
            ],
            "recommendations": [
                "Start with one high-friction workflow.",
                "Use measurable proof before expanding.",
                "Keep the proposal tied to commercial value.",
            ],
        },
    },
    {
        "name": "support_operations_prompt",
        "briefing": {
            "title": "AI for support operations",
            "audience": "Operations leadership",
            "objective": "Improve support operations with less rework, better SLA performance, and a clearer execution sequence.",
            "briefing_text": "Create a deck about improving support operations with AI, showing bottlenecks, execution metrics, risks, dependencies, and the recommended operating sequence.",
            "metrics": [
                {"label": "SLA hit rate", "value": "82%"},
                {"label": "Rework share", "value": "19%"},
                {"label": "Resolution time", "value": "-14%"},
            ],
            "milestones": [
                {"title": "Stabilize triage", "detail": "Reduce noisy intake and routing variance", "phase": "Sprint 1"},
                {"title": "Pilot agent assist", "detail": "Instrument resolution quality and SLA impact", "phase": "Sprint 2"},
                {"title": "Scale with guardrails", "detail": "Expand only after quality stabilizes", "phase": "Sprint 3"},
            ],
            "faqs": [
                {"question": "What is the operating risk?", "answer": "Automating unstable workflows too early."},
                {"question": "How will success be measured?", "answer": "By SLA lift, reduced rework and faster resolution."},
            ],
            "recommendations": [
                "Fix routing before scaling automation.",
                "Measure quality and resolution outcomes explicitly.",
                "Keep the operating sequence narrow and staged.",
            ],
        },
    },
]


def _run_generation_benchmark_for_provider(
    output_dir: str | Path,
    *,
    provider_name: str = "heuristic",
    theme_name: str | None = None,
    write_json_decks: bool = False,
) -> dict[str, object]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    provider = get_provider(provider_name)
    asset_root = Path(".").resolve()

    results: list[dict[str, object]] = []
    unique_slide_types: set[str] = set()
    coverage: dict[str, int] = {}
    successful_generations = 0
    fallback_used_count = 0
    resolved_models: set[str] = set()
    specificity_scores: list[float] = []
    specificity_thresholds: list[float] = []
    specificity_margins: list[float] = []
    below_specificity_threshold_count = 0
    unsupported_claim_scenarios = 0
    unsupported_claim_slide_count = 0
    model_breakdown: dict[str, dict[str, object]] = {}

    for scenario in BENCHMARK_SCENARIOS:
        scenario_name = str(scenario["name"])
        briefing = BriefingInput.model_validate(dict(scenario["briefing"]))
        try:
            generation = provider.generate(briefing, theme_name=theme_name)
            spec = PresentationInput.model_validate(generation.payload)
            review = review_presentation(spec, asset_root=asset_root, theme_name=spec.presentation.theme)
            analysis = generation.analysis if isinstance(generation.analysis, dict) else {}
            quality = assess_generated_payload_quality(spec.model_dump(mode="json"), briefing)
            fallback_used = bool(analysis.get("fallback_used", False))
            if fallback_used:
                fallback_used_count += 1
            resolved_model = str(analysis.get("resolved_model") or analysis.get("backend_provider") or "").strip()
            if resolved_model:
                resolved_models.add(resolved_model)
            specificity_score = float(quality.get("specificity_score") or 0.0)
            specificity_threshold = float(quality.get("specificity_threshold") or 0.0)
            specificity_margin = round(specificity_score - specificity_threshold, 1)
            specificity_scores.append(specificity_score)
            specificity_thresholds.append(specificity_threshold)
            specificity_margins.append(specificity_margin)
            if specificity_score < specificity_threshold:
                below_specificity_threshold_count += 1
            claim_without_proof_slides = [
                str(item) for item in (quality.get("claim_without_proof_slides") or []) if str(item).strip()
            ]
            if claim_without_proof_slides:
                unsupported_claim_scenarios += 1
                unsupported_claim_slide_count += len(claim_without_proof_slides)

            model_key = resolved_model or provider.name
            model_stats = model_breakdown.setdefault(
                model_key,
                {
                    "scenario_count": 0,
                    "average_specificity_score": 0.0,
                    "average_specificity_threshold": 0.0,
                    "average_specificity_margin": 0.0,
                    "below_threshold_count": 0,
                    "claim_without_proof_scenarios": 0,
                },
            )
            model_stats["scenario_count"] = int(model_stats["scenario_count"]) + 1
            model_stats["average_specificity_score"] = float(model_stats["average_specificity_score"]) + specificity_score
            model_stats["average_specificity_threshold"] = float(model_stats["average_specificity_threshold"]) + specificity_threshold
            model_stats["average_specificity_margin"] = float(model_stats["average_specificity_margin"]) + specificity_margin
            model_stats["below_threshold_count"] = int(model_stats["below_threshold_count"]) + int(
                specificity_score < specificity_threshold
            )
            model_stats["claim_without_proof_scenarios"] = int(model_stats["claim_without_proof_scenarios"]) + int(
                bool(claim_without_proof_slides)
            )
            slide_types = sorted({slide.type.value for slide in spec.slides})
            for slide_type in slide_types:
                unique_slide_types.add(slide_type)
                coverage[slide_type] = coverage.get(slide_type, 0) + 1

            deck_path = None
            if write_json_decks:
                deck_path = destination / f"{scenario_name}.json"
                deck_path.write_text(
                    json.dumps(spec.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )

            results.append(
                {
                    "scenario": scenario_name,
                    "provider": generation.provider_name,
                    "valid": True,
                    "slide_count": len(spec.slides),
                    "review_status": review["status"],
                    "issue_count": review["issue_count"],
                    "average_score": review["average_score"],
                    "fallback_used": fallback_used,
                    "fallback_reason": analysis.get("fallback_reason"),
                    "repair_loop_used": bool(analysis.get("repair_loop_used", False)),
                    "repair_attempt_count": int(analysis.get("repair_attempt_count") or 0),
                    "specificity_score": specificity_score,
                    "specificity_threshold": specificity_threshold,
                    "specificity_margin": specificity_margin,
                    "claim_without_proof_slides": claim_without_proof_slides,
                    "claim_proof_relationships": quality.get("claim_proof_relationships") or [],
                    "resolved_model": resolved_model or None,
                    "slide_types": slide_types,
                    "output_json": str(deck_path) if deck_path else None,
                }
            )
            successful_generations += 1
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "scenario": scenario_name,
                    "provider": provider.name,
                    "valid": False,
                    "error": str(exc),
                    "fallback_used": None,
                    "repair_loop_used": None,
                    "repair_attempt_count": None,
                }
            )

    scenario_count = len(BENCHMARK_SCENARIOS)
    normalized_model_breakdown: dict[str, dict[str, object]] = {}
    for model_name, stats in model_breakdown.items():
        count = int(stats["scenario_count"]) or 1
        normalized_model_breakdown[model_name] = {
            "scenario_count": count,
            "average_specificity_score": round(float(stats["average_specificity_score"]) / count, 2),
            "average_specificity_threshold": round(float(stats["average_specificity_threshold"]) / count, 2),
            "average_specificity_margin": round(float(stats["average_specificity_margin"]) / count, 2),
            "below_threshold_count": int(stats["below_threshold_count"]),
            "claim_without_proof_scenarios": int(stats["claim_without_proof_scenarios"]),
        }
    return {
        "mode": "briefing-benchmark",
        "provider": provider.name,
        "scenario_count": scenario_count,
        "successful_generations": successful_generations,
        "failed_generations": scenario_count - successful_generations,
        "unique_slide_type_count": len(unique_slide_types),
        "unique_slide_types": sorted(unique_slide_types),
        "slide_type_coverage": dict(sorted(coverage.items())),
        "fallback_used_count": fallback_used_count,
        "fallback_rate": round((fallback_used_count / scenario_count) * 100, 1) if scenario_count else 0.0,
        "resolved_models": sorted(resolved_models),
        "specificity_summary": {
            "average_specificity_score": round(sum(specificity_scores) / len(specificity_scores), 2) if specificity_scores else None,
            "average_specificity_threshold": round(sum(specificity_thresholds) / len(specificity_thresholds), 2) if specificity_thresholds else None,
            "average_specificity_margin": round(sum(specificity_margins) / len(specificity_margins), 2) if specificity_margins else None,
            "below_threshold_count": below_specificity_threshold_count,
        },
        "claim_proof_summary": {
            "unsupported_claim_scenarios": unsupported_claim_scenarios,
            "unsupported_claim_slide_count": unsupported_claim_slide_count,
        },
        "model_breakdown": normalized_model_breakdown,
        "write_json_decks": write_json_decks,
        "generation_contract": build_llm_generation_contract(),
        "scenarios": results,
    }


def run_generation_benchmark(
    output_dir: str | Path,
    *,
    provider_name: str = "heuristic",
    compare_provider_names: list[str] | None = None,
    theme_name: str | None = None,
    write_json_decks: bool = False,
) -> dict[str, object]:
    requested_provider_names = [provider_name, *(compare_provider_names or [])]
    normalized_provider_names: list[str] = []
    for requested_name in requested_provider_names:
        normalized_name = get_provider(requested_name).name
        if normalized_name not in normalized_provider_names:
            normalized_provider_names.append(normalized_name)

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    if len(normalized_provider_names) == 1:
        return _run_generation_benchmark_for_provider(
            destination,
            provider_name=normalized_provider_names[0],
            theme_name=theme_name,
            write_json_decks=write_json_decks,
        )

    provider_runs: list[dict[str, object]] = []
    for normalized_name in normalized_provider_names:
        provider_output_dir = destination / normalized_name if write_json_decks else destination
        provider_runs.append(
            _run_generation_benchmark_for_provider(
                provider_output_dir,
                provider_name=normalized_name,
                theme_name=theme_name,
                write_json_decks=write_json_decks,
            )
        )

    scenario_names = [str(item["name"]) for item in BENCHMARK_SCENARIOS]
    scenario_comparison: list[dict[str, object]] = []
    fallback_rates: dict[str, float] = {}
    average_issue_counts: dict[str, float | None] = {}
    repair_loop_rates: dict[str, float] = {}
    specificity_averages: dict[str, float | None] = {}
    specificity_margin_averages: dict[str, float | None] = {}
    claim_without_proof_rates: dict[str, float] = {}
    provider_model_breakdown: dict[str, dict[str, object]] = {}
    for provider_run in provider_runs:
        provider = str(provider_run["provider"])
        fallback_rates[provider] = float(provider_run.get("fallback_rate") or 0.0)
        valid_issue_counts = [
            int(item.get("issue_count") or 0)
            for item in provider_run.get("scenarios", [])
            if item.get("valid") is True
        ]
        average_issue_counts[provider] = (
            round(sum(valid_issue_counts) / len(valid_issue_counts), 2)
            if valid_issue_counts
            else None
        )
        valid_repair_count = sum(
            1
            for item in provider_run.get("scenarios", [])
            if item.get("repair_loop_used") is True
        )
        scenario_count = int(provider_run.get("scenario_count") or 0)
        repair_loop_rates[provider] = round((valid_repair_count / scenario_count) * 100, 1) if scenario_count else 0.0
        specificity_summary = provider_run.get("specificity_summary") or {}
        specificity_averages[provider] = specificity_summary.get("average_specificity_score")
        specificity_margin_averages[provider] = specificity_summary.get("average_specificity_margin")
        claim_summary = provider_run.get("claim_proof_summary") or {}
        unsupported_claim_scenarios = int(claim_summary.get("unsupported_claim_scenarios") or 0)
        claim_without_proof_rates[provider] = round((unsupported_claim_scenarios / scenario_count) * 100, 1) if scenario_count else 0.0
        provider_model_breakdown[provider] = dict(provider_run.get("model_breakdown") or {})

    for scenario_name in scenario_names:
        row: dict[str, object] = {"scenario": scenario_name}
        for provider_run in provider_runs:
            provider = str(provider_run["provider"])
            scenario_payload = next(
                (item for item in provider_run.get("scenarios", []) if item.get("scenario") == scenario_name),
                {"scenario": scenario_name, "valid": False, "error": "scenario missing from provider comparison"},
            )
            row[provider] = {
                "valid": scenario_payload.get("valid"),
                "issue_count": scenario_payload.get("issue_count"),
                "average_score": scenario_payload.get("average_score"),
                "fallback_used": scenario_payload.get("fallback_used"),
                "repair_loop_used": scenario_payload.get("repair_loop_used"),
                "specificity_score": scenario_payload.get("specificity_score"),
                "specificity_threshold": scenario_payload.get("specificity_threshold"),
                "specificity_margin": scenario_payload.get("specificity_margin"),
                "claim_without_proof_slide_count": len(scenario_payload.get("claim_without_proof_slides") or []),
                "resolved_model": scenario_payload.get("resolved_model"),
                "error": scenario_payload.get("error"),
            }
        scenario_comparison.append(row)

    best_provider = None
    if provider_runs:
        best_provider = sorted(
            provider_runs,
            key=lambda item: (
                -int(item.get("successful_generations") or 0),
                float(average_issue_counts.get(str(item.get("provider"))) or 9999.0),
                float(item.get("fallback_rate") or 9999.0),
            ),
        )[0]["provider"]

    return {
        "mode": "briefing-benchmark-comparison",
        "providers": normalized_provider_names,
        "scenario_count": len(BENCHMARK_SCENARIOS),
        "write_json_decks": write_json_decks,
        "generation_contract": build_llm_generation_contract(),
        "provider_runs": provider_runs,
        "scenario_comparison": scenario_comparison,
        "comparison_summary": {
            "best_provider_by_success_then_quality": best_provider,
            "fallback_rates": fallback_rates,
            "repair_loop_rates": repair_loop_rates,
            "average_issue_counts": average_issue_counts,
            "specificity_averages": specificity_averages,
            "specificity_margin_averages": specificity_margin_averages,
            "claim_without_proof_rates": claim_without_proof_rates,
            "provider_model_breakdown": provider_model_breakdown,
        },
    }