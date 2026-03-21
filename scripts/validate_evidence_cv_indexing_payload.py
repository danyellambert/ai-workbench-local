from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.evidence_cv.config import EvidencePipelineConfig
from src.evidence_cv.pipeline.runner import run_cv_pipeline


def select_sample(pdf_dir: Path) -> list[Path]:
    all_pdfs = sorted(pdf_dir.glob('*.pdf'))
    layouts = [
        'classic_one_column',
        'modern_two_column',
        'compact_sidebar',
        'dense_executive',
        'scan_like_image_pdf',
    ]
    selected: list[Path] = []
    for level in ('simple', 'medium', 'hard'):
        for layout in layouts:
            match = next((path for path in all_pdfs if f'_{level}_' in path.name and layout in path.name), None)
            if match is not None:
                selected.append(match)
                if len(selected) >= 10:
                    break
        if len(selected) >= 10:
            break
    deduped = []
    seen = set()
    for path in selected:
        if path.name in seen:
            continue
        seen.add(path.name)
        deduped.append(path)
    return deduped[:10]


def judge_area(raw) -> str:
    if isinstance(raw, str):
        return 'acceptable' if len(raw.strip()) >= 120 else 'weak'
    if isinstance(raw, list):
        return 'acceptable' if len(raw) > 0 else 'weak'
    if isinstance(raw, dict):
        return 'acceptable' if any(raw.values()) else 'weak'
    return 'weak'


def validate_cv(pdf_path: Path) -> dict[str, object]:
    result = run_cv_pipeline(pdf_path, EvidencePipelineConfig(enable_vl=False))
    payload = result.runtime_metadata.get('indexing_payload', {})
    structured = payload.get('structured', {}) or {}
    judgments = {
        'raw_text': judge_area(payload.get('raw_text', '')),
        'confirmed_fields': judge_area(payload.get('confirmed_fields', {})),
        'experience': judge_area(structured.get('experience', [])),
        'education': judge_area(structured.get('education', [])),
        'skills': judge_area(structured.get('skills', [])),
        'languages': judge_area(structured.get('languages', [])),
    }
    acceptable_count = sum(1 for value in judgments.values() if value == 'acceptable')
    if acceptable_count >= 5:
        verdict = 'ready_for_indexing'
    elif acceptable_count >= 3:
        verdict = 'usable_with_caution'
    else:
        verdict = 'not_ready'
    return {
        'file': str(pdf_path),
        'judgments': judgments,
        'verdict': verdict,
        'payload_summary': {
            'confirmed_fields': payload.get('confirmed_fields', {}),
            'experience_count': len(structured.get('experience', [])),
            'education_count': len(structured.get('education', [])),
            'skills_count': len(structured.get('skills', [])),
            'languages_count': len(structured.get('languages', [])),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate evidence_cv indexing payload on a small stratified sample')
    parser.add_argument('--pdf-dir', default='data/synthetic/resumes/pdf')
    parser.add_argument('--out', default='phase5_eval/reports/evidence_cv_indexing_payload_validation.json')
    args = parser.parse_args()

    pdf_dir = Path(args.pdf_dir)
    sample = select_sample(pdf_dir)
    per_file = [validate_cv(path) for path in sample]

    verdict_counts: dict[str, int] = {}
    area_strength = {
        'raw_text': 0,
        'confirmed_fields': 0,
        'experience': 0,
        'education': 0,
        'skills': 0,
        'languages': 0,
    }
    for item in per_file:
        verdict = item['verdict']
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        for key, value in item['judgments'].items():
            if value == 'acceptable':
                area_strength[key] += 1

    if verdict_counts.get('ready_for_indexing', 0) >= len(per_file) // 2:
        aggregate_verdict = 'structured_payload_already_useful_with_caution'
        recommended_strategy = 'raw_text + confirmed_fields + structured payload'
    elif verdict_counts.get('usable_with_caution', 0) >= len(per_file) // 2:
        aggregate_verdict = 'indexing_can_start_but_structured_should_be_secondary'
        recommended_strategy = 'raw_text + confirmed_fields + structured payload'
    else:
        aggregate_verdict = 'wait_for_one_more_parser_refinement'
        recommended_strategy = 'raw_text + confirmed_fields only'

    payload = {
        'sampled_cvs': [path.name for path in sample],
        'aggregate': {
            'sample_size': len(sample),
            'verdict_counts': verdict_counts,
            'area_strength': area_strength,
            'aggregate_verdict': aggregate_verdict,
            'recommended_indexing_strategy': recommended_strategy,
        },
        'per_file': per_file,
    }
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())