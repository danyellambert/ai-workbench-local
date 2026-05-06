from __future__ import annotations

import json
import math
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'docs' / 'data' / 'phase_4_5_benchmark_data.json'
OUTPUT_DIR = ROOT / 'docs' / 'assets' / 'phase_4_5'


def load_data() -> dict:
    with DATA_PATH.open('r', encoding='utf-8') as f:
        return json.load(f)


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def save(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / name, dpi=200, bbox_inches='tight')
    plt.close(fig)


def shorten_labels(labels: list[str], width: int = 18) -> list[str]:
    return ['\n'.join(textwrap.wrap(label, width=width, break_long_words=False)) for label in labels]


def annotate_bars(ax: plt.Axes, fmt: str = '{:.2f}', rotation: int = 0) -> None:
    for patch in ax.patches:
        height = patch.get_height()
        if math.isnan(height):
            continue
        ax.annotate(
            fmt.format(height),
            (patch.get_x() + patch.get_width() / 2, height),
            ha='center',
            va='bottom',
            fontsize=8,
            rotation=rotation,
            xytext=(0, 3),
            textcoords='offset points',
        )


def grouped_bar(ax: plt.Axes, categories: list[str], series: list[tuple[str, list[float]]], ylabel: str, title: str) -> None:
    x = np.arange(len(categories))
    width = 0.8 / len(series)
    for idx, (series_name, values) in enumerate(series):
        ax.bar(x + (idx - (len(series) - 1) / 2) * width, values, width=width, label=series_name)
    ax.set_xticks(x)
    ax.set_xticklabels(shorten_labels(categories, 16))
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()


def scatter_with_labels(ax: plt.Axes, x: list[float], y: list[float], labels: list[str], xlabel: str, ylabel: str, title: str, y_limits: tuple[float, float] | None = None) -> None:
    ax.scatter(x, y, s=80)
    for xi, yi, label in zip(x, y, labels):
        ax.annotate(label, (xi, yi), textcoords='offset points', xytext=(6, 6), fontsize=8)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if y_limits:
        ax.set_ylim(*y_limits)
    ax.grid(True, alpha=0.3)


def render_pdf_extraction_aggregate(data: dict) -> None:
    rows = data['pdf_extraction_aggregate']['modes']
    modes = [r['mode'] for r in rows]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(modes, [r['avg_manual_score'] for r in rows])
    ax.set_title('Average manual score by extraction mode')
    ax.set_ylabel('Average manual score (0-2)')
    annotate_bars(ax, '{:.4f}')
    save(fig, '01_pdf_extraction_aggregate_manual_score.png')

    fig, ax = plt.subplots(figsize=(7, 4))
    scatter_with_labels(
        ax,
        [r['avg_extraction_seconds'] for r in rows],
        [r['avg_manual_score'] for r in rows],
        modes,
        'Average extraction time (seconds)',
        'Average manual score (0-2)',
        'PDF extraction: quality vs extraction cost',
    )
    ax.set_xscale('log')
    save(fig, '02_pdf_extraction_aggregate_quality_vs_cost.png')

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(modes, [r['avg_indexing_seconds'] for r in rows])
    ax.set_title('Average indexing time by extraction mode')
    ax.set_ylabel('Average indexing time (seconds)')
    annotate_bars(ax, '{:.2f}')
    save(fig, '03_pdf_extraction_aggregate_indexing_time.png')

    fig, ax = plt.subplots(figsize=(7, 4))
    grouped_bar(
        ax,
        modes,
        [('Manual-review packets', [r['packets'] for r in rows]), ('Reviewed questions', [r['questions'] for r in rows])],
        'Count',
        'Manual-review coverage by extraction mode',
    )
    save(fig, '04_pdf_extraction_aggregate_review_coverage.png')


def render_pdf_extraction_document_level(data: dict) -> None:
    docs = data['pdf_extraction_document_level']['documents']
    names = [d['pdf_name'] for d in docs]

    fig, ax = plt.subplots(figsize=(11, 4.5))
    grouped_bar(
        ax,
        names,
        [
            ('basic', [d['basic_score'] for d in docs]),
            ('hybrid', [d['hybrid_score'] for d in docs]),
            ('complete', [d['complete_score'] for d in docs]),
        ],
        'Average manual score (0-2)',
        'Manual score by document and extraction mode',
    )
    save(fig, '05_pdf_extraction_doc_level_manual_score.png')

    fig, ax = plt.subplots(figsize=(11, 4.5))
    grouped_bar(
        ax,
        names,
        [
            ('basic', [d['basic_extraction'] for d in docs]),
            ('hybrid', [d['hybrid_extraction'] for d in docs]),
            ('complete', [d['complete_extraction'] for d in docs]),
        ],
        'Extraction time (seconds)',
        'Extraction time by document and mode',
    )
    ax.set_yscale('log')
    save(fig, '06_pdf_extraction_doc_level_extraction_time.png')

    fig, ax = plt.subplots(figsize=(11, 4.5))
    grouped_bar(
        ax,
        names,
        [
            ('basic', [d['basic_chars'] for d in docs]),
            ('hybrid', [d['hybrid_chars'] for d in docs]),
            ('complete', [d['complete_chars'] for d in docs]),
        ],
        'Extracted characters',
        'Character count by document and mode',
    )
    save(fig, '07_pdf_extraction_doc_level_char_count.png')

    fig, ax = plt.subplots(figsize=(11, 4.5))
    grouped_bar(
        ax,
        names,
        [
            ('basic', [d['basic_chunks'] for d in docs]),
            ('hybrid', [d['hybrid_chunks'] for d in docs]),
            ('complete', [d['complete_chunks'] for d in docs]),
        ],
        'Chunk count',
        'Chunk count by document and mode',
    )
    save(fig, '08_pdf_extraction_doc_level_chunk_count.png')


def render_embedding_models(data: dict) -> None:
    rows = data['embedding_models']['models']
    labels = [r['model'] for r in rows]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    scatter_with_labels(
        ax,
        [r['avg_retrieval_seconds'] for r in rows],
        [r['mrr'] for r in rows],
        labels,
        'Average retrieval time (seconds)',
        'MRR',
        'Embedding models: quality vs retrieval latency',
        y_limits=(0.75, 1.03),
    )
    save(fig, '09_embedding_models_quality_vs_latency.png')

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(shorten_labels(labels, 16), [r['indexing_seconds'] for r in rows])
    ax.set_title('Indexing time by embedding model')
    ax.set_ylabel('Indexing time (seconds)')
    save(fig, '10_embedding_models_indexing_time.png')

    fig, ax = plt.subplots(figsize=(10, 4.5))
    grouped_bar(
        ax,
        labels,
        [
            ('Hit@1', [r['hit_at_1'] for r in rows]),
            ('Hit@K', [r['hit_at_k'] for r in rows]),
            ('MRR', [r['mrr'] for r in rows]),
        ],
        'Score',
        'Quality metrics by embedding model',
    )
    ax.set_ylim(0, 1.05)
    save(fig, '11_embedding_models_quality_metrics.png')

    fig, ax = plt.subplots(figsize=(10, 4.5))
    grouped_bar(
        ax,
        labels,
        [
            ('Average retrieval', [r['avg_retrieval_seconds'] for r in rows]),
            ('P95 retrieval', [r['p95_retrieval_seconds'] for r in rows]),
        ],
        'Seconds',
        'Retrieval latency by embedding model',
    )
    save(fig, '12_embedding_models_latency.png')


def render_context_windows(data: dict) -> None:
    track = data['embedding_context_windows']['embeddinggemma_track']
    contexts = [str(r['context_window']) for r in track]
    x = np.arange(len(contexts))

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(x, [r['avg_retrieval_seconds'] for r in track], marker='o')
    ax.set_xticks(x)
    ax.set_xticklabels(contexts)
    ax.set_xlabel('Context window')
    ax.set_ylabel('Average retrieval time (seconds)')
    ax.set_title('embeddinggemma:300m retrieval latency vs context window')
    ax.grid(True, alpha=0.3)
    save(fig, '13_embedding_ctx_retrieval_vs_window.png')

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(x, [r['indexing_seconds'] for r in track], marker='o')
    ax.set_xticks(x)
    ax.set_xticklabels(contexts)
    ax.set_xlabel('Context window')
    ax.set_ylabel('Indexing time (seconds)')
    ax.set_title('embeddinggemma:300m indexing time vs context window')
    ax.grid(True, alpha=0.3)
    save(fig, '14_embedding_ctx_indexing_vs_window.png')

    cross = data['embedding_context_windows']['cross_model_selected']
    fig, ax = plt.subplots(figsize=(9, 4.8))
    scatter_with_labels(
        ax,
        [r['avg_retrieval_seconds'] for r in cross],
        [r['mrr'] for r in cross],
        [r['label'] for r in cross],
        'Average retrieval time (seconds)',
        'MRR',
        'Embedding context: cross-model selected comparison',
        y_limits=(0.88, 1.03),
    )
    save(fig, '15_embedding_ctx_cross_model_scatter.png')

    extreme = data['embedding_context_windows']['winner_vs_extreme']
    fig, ax = plt.subplots(figsize=(8, 4.8))
    grouped_bar(
        ax,
        ['Average retrieval seconds', 'Indexing seconds'],
        [(r['label'], [r['avg_retrieval_seconds'], r['indexing_seconds']]) for r in extreme],
        'Seconds',
        'Extreme-context cautionary example',
    )
    ax.set_yscale('log')
    save(fig, '16_embedding_ctx_extreme_context_warning.png')


def render_retrieval_tuning(data: dict) -> None:
    rows = data['retrieval_tuning']['configs']
    labels = [r['label'] for r in rows]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    scatter_with_labels(
        ax,
        [r['avg_retrieval_seconds'] for r in rows],
        [r['mrr'] for r in rows],
        labels,
        'Average retrieval time (seconds)',
        'MRR',
        'Retrieval tuning: quality vs retrieval latency',
        y_limits=(0.84, 1.03),
    )
    save(fig, '17_retrieval_tuning_quality_vs_latency.png')

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(shorten_labels(labels, 14), [r['indexing_seconds'] for r in rows])
    ax.set_title('Indexing time by retrieval configuration')
    ax.set_ylabel('Indexing time (seconds)')
    save(fig, '18_retrieval_tuning_indexing_time.png')

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(shorten_labels(labels, 14), [r['avg_retrieval_seconds'] for r in rows])
    ax.set_title('Retrieval latency by retrieval configuration')
    ax.set_ylabel('Average retrieval time (seconds)')
    save(fig, '19_retrieval_tuning_latency.png')

    fig, ax = plt.subplots(figsize=(11, 4.8))
    grouped_bar(
        ax,
        labels,
        [
            ('Hit@1', [r['hit_at_1'] for r in rows]),
            ('Hit@K', [r['hit_at_k'] for r in rows]),
            ('MRR', [r['mrr'] for r in rows]),
        ],
        'Score',
        'Quality metrics by retrieval configuration',
    )
    ax.set_ylim(0, 1.05)
    save(fig, '20_retrieval_tuning_quality_metrics.png')


def table_figure(title: str, headers: list[str], rows: list[list[str]], filename: str, col_widths: list[float] | None = None, font_size: int = 10, fig_width: float = 12.0) -> None:
    fig_height = 1.5 + 0.52 * (len(rows) + 1)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis('off')
    ax.set_title(title, loc='left', pad=16, fontsize=14, fontweight='bold')
    table = ax.table(cellText=rows, colLabels=headers, loc='center', cellLoc='left', colLoc='left', colWidths=col_widths)
    table.auto_set_font_size(False)
    table.set_fontsize(font_size)
    table.scale(1, 1.75)
    save(fig, filename)


def render_executive_summary(data: dict) -> None:
    winner_rows = []
    for row in data['executive_summary']['winner_matrix']:
        winner_rows.append([
            textwrap.fill(row['benchmark_block'], 22),
            textwrap.fill(row['winner'], 20),
            textwrap.fill(row['quality_metric'], 18),
            textwrap.fill(row['cost_metric'], 18),
            textwrap.fill(row['decision_reason'], 24),
        ])
    table_figure(
        'Phase 4.5 benchmark winner matrix',
        ['Benchmark block', 'Winner', 'Quality metric', 'Cost metric', 'Decision reason'],
        winner_rows,
        '21_phase_4_5_winner_matrix.png',
        col_widths=[0.22, 0.18, 0.18, 0.16, 0.26],
        font_size=8,
        fig_width=15.0,
    )

    config = data['executive_summary']['final_config']
    config_rows = [[textwrap.fill(k, 28), textwrap.fill(v, 28)] for k, v in config.items()]
    table_figure(
        'Phase 4.5 final recommended configuration',
        ['Setting', 'Value'],
        config_rows,
        '22_phase_4_5_final_config_card.png',
        col_widths=[0.45, 0.55],
        font_size=10,
        fig_width=11.0,
    )

    summary = data['executive_summary']['tradeoff_summary']
    summary_rows = []
    for row in summary:
        summary_rows.append([
            textwrap.fill(row['decision_area'], 18),
            textwrap.fill(row['chosen_option'], 18),
            textwrap.fill(row['evidence'], 30),
            textwrap.fill(row['why'], 22),
        ])
    table_figure(
        'Phase 4.5 cost/quality decision summary',
        ['Decision area', 'Chosen option', 'Evidence supporting the choice', 'Why this matters'],
        summary_rows,
        '23_phase_4_5_cost_quality_summary.png',
        col_widths=[0.17, 0.18, 0.38, 0.27],
        font_size=8,
        fig_width=14.0,
    )


def main() -> None:
    ensure_output_dir()
    data = load_data()
    render_pdf_extraction_aggregate(data)
    render_pdf_extraction_document_level(data)
    render_embedding_models(data)
    render_context_windows(data)
    render_retrieval_tuning(data)
    render_executive_summary(data)
    print(f'Rendered Phase 4.5 charts to: {OUTPUT_DIR}')


if __name__ == '__main__':
    main()
