from __future__ import annotations


def build_product_css(accent_color: str = "#6ae3ff") -> str:
    return f"""
    :root {{
        --product-accent: {accent_color};
        --product-accent-soft: rgba(106, 227, 255, 0.16);
        --product-border: rgba(255, 255, 255, 0.10);
        --product-panel: rgba(15, 23, 42, 0.88);
        --product-panel-strong: rgba(8, 15, 29, 0.94);
        --product-text-soft: #cbd5e1;
        --product-success: #34d399;
        --product-warning: #fbbf24;
        --product-danger: #fb7185;
    }}

    .gradio-container {{
        background: radial-gradient(circle at top, rgba(14, 165, 233, 0.12), transparent 32%), linear-gradient(180deg, #040816 0%, #07101d 48%, #0b1321 100%);
        color: white;
    }}

    .product-shell {{
        max-width: 1260px;
        margin: 0 auto;
    }}

    .product-topbar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        padding: 14px 18px;
        border: 1px solid var(--product-border);
        background: rgba(6, 11, 24, 0.72);
        border-radius: 20px;
        margin-bottom: 18px;
        backdrop-filter: blur(10px);
    }}

    .product-topbar__eyebrow {{
        font-size: 12px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--product-accent);
        margin-bottom: 6px;
    }}

    .product-topbar__title {{
        font-size: 22px;
        font-weight: 700;
    }}

    .product-topbar__hint {{
        font-size: 14px;
        color: var(--product-text-soft);
    }}

    .product-link-pill {{
        display: inline-flex;
        align-items: center;
        padding: 10px 14px;
        border-radius: 999px;
        border: 1px solid var(--product-border);
        color: white;
        text-decoration: none;
        background: rgba(255, 255, 255, 0.02);
    }}

    .product-link-pill:hover {{
        border-color: rgba(106, 227, 255, 0.36);
        background: rgba(255, 255, 255, 0.06);
    }}

    .product-hero {{
        display: grid;
        grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.9fr);
        gap: 18px;
        margin-bottom: 22px;
    }}

    .product-panel {{
        border: 1px solid var(--product-border);
        background: var(--product-panel);
        border-radius: 26px;
        padding: 24px;
        box-shadow: 0 16px 60px rgba(0, 0, 0, 0.28);
    }}

    .product-panel--strong {{
        background: var(--product-panel-strong);
    }}

    .product-hero__eyebrow {{
        font-size: 12px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--product-accent);
        margin-bottom: 10px;
    }}

    .product-hero__title {{
        font-size: 42px;
        line-height: 1.05;
        font-weight: 800;
        margin: 0 0 14px 0;
    }}

    .product-hero__subtitle {{
        color: var(--product-text-soft);
        font-size: 16px;
        line-height: 1.65;
        margin-bottom: 18px;
    }}

    .product-hero__cta-note {{
        margin-top: 18px;
        font-size: 14px;
        line-height: 1.6;
        color: var(--product-text-soft);
    }}

    .product-kpi-grid {{
        display: grid;
        gap: 12px;
    }}

    .product-chip-row, .product-proof-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
    }}

    .product-chip, .product-proof-chip {{
        padding: 10px 12px;
        border-radius: 999px;
        border: 1px solid rgba(106, 227, 255, 0.22);
        background: var(--product-accent-soft);
        color: white;
        font-size: 13px;
    }}

    .product-hero-stat {{
        border-radius: 20px;
        border: 1px solid var(--product-border);
        background: rgba(255, 255, 255, 0.03);
        padding: 16px;
        margin-bottom: 12px;
    }}

    .product-hero-stat__label {{
        color: var(--product-text-soft);
        font-size: 13px;
        margin-bottom: 4px;
    }}

    .product-hero-stat__value {{
        font-size: 24px;
        font-weight: 700;
    }}

    .product-workflow-card-grid {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 14px;
        margin-bottom: 18px;
    }}

    .product-workflow-card {{
        border: 1px solid var(--product-border);
        background: rgba(255, 255, 255, 0.03);
        border-radius: 22px;
        padding: 18px;
        min-height: 220px;
        position: relative;
        overflow: hidden;
    }}

    .product-workflow-card--active {{
        border-color: rgba(106, 227, 255, 0.52);
        box-shadow: 0 0 0 1px rgba(106, 227, 255, 0.18) inset;
        background: linear-gradient(180deg, rgba(106, 227, 255, 0.14), rgba(255, 255, 255, 0.04));
    }}

    .product-workflow-card__icon {{
        width: 44px;
        height: 44px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        background: rgba(255, 255, 255, 0.05);
        font-size: 20px;
        margin-bottom: 14px;
    }}

    .product-workflow-card__title {{
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 8px;
    }}

    .product-workflow-card__headline {{
        color: var(--product-text-soft);
        font-size: 14px;
        line-height: 1.55;
        margin-bottom: 10px;
        min-height: 44px;
    }}

    .product-workflow-card__description {{
        color: rgba(226, 232, 240, 0.94);
        font-size: 13px;
        line-height: 1.6;
        margin-bottom: 14px;
        min-height: 60px;
    }}

    .product-workflow-card__cta {{
        margin-top: 14px;
        font-size: 12px;
        color: var(--product-accent);
        letter-spacing: 0.02em;
    }}

    .product-workflow-card__list {{
        margin: 0;
        padding-left: 18px;
        color: white;
        font-size: 13px;
        line-height: 1.6;
    }}

    .product-status-pill {{
        display: inline-flex;
        gap: 8px;
        align-items: center;
        border-radius: 999px;
        padding: 8px 12px;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 12px;
    }}

    .product-status-pill--completed {{ background: rgba(52, 211, 153, 0.15); color: #bbf7d0; }}
    .product-status-pill--warning {{ background: rgba(251, 191, 36, 0.16); color: #fde68a; }}
    .product-status-pill--error {{ background: rgba(251, 113, 133, 0.16); color: #fecdd3; }}

    .product-section-title {{
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 6px;
    }}

    .product-section-subtitle {{
        font-size: 14px;
        color: var(--product-text-soft);
        margin-bottom: 10px;
        line-height: 1.6;
    }}

    .product-empty-state {{
        border: 1px dashed rgba(255, 255, 255, 0.18);
        border-radius: 20px;
        padding: 18px;
        color: var(--product-text-soft);
        background: rgba(255, 255, 255, 0.02);
    }}

    .product-how-shell {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
        margin-bottom: 22px;
    }}

    .product-how-card {{
        border: 1px solid var(--product-border);
        background: rgba(255, 255, 255, 0.03);
        border-radius: 22px;
        padding: 18px;
    }}

    .product-how-card__step {{
        width: 32px;
        height: 32px;
        border-radius: 999px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: var(--product-accent-soft);
        border: 1px solid rgba(106, 227, 255, 0.22);
        margin-bottom: 12px;
        font-weight: 700;
    }}

    .product-how-card__title {{
        font-size: 16px;
        font-weight: 700;
        margin-bottom: 8px;
    }}

    .product-how-card__body {{
        font-size: 14px;
        line-height: 1.6;
        color: var(--product-text-soft);
    }}

    .product-detail-grid {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin-top: 12px;
    }}

    .product-detail-section {{
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 14px;
        background: rgba(255, 255, 255, 0.02);
    }}

    .product-result-grid {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
        margin-top: 12px;
    }}

    .product-list-card {{
        border: 1px solid var(--product-border);
        background: rgba(255, 255, 255, 0.03);
        border-radius: 18px;
        padding: 16px;
    }}

    .product-list-card__title {{
        font-size: 15px;
        font-weight: 700;
        margin-bottom: 10px;
    }}

    .product-list-card__list {{
        margin: 0;
        padding-left: 18px;
        font-size: 13px;
        line-height: 1.65;
        color: white;
    }}

    .product-list-card__empty {{
        color: var(--product-text-soft);
        font-size: 13px;
        line-height: 1.6;
    }}

    .product-artifact-list {{
        display: grid;
        gap: 10px;
        margin-top: 14px;
    }}

    .product-artifact-item {{
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 12px 14px;
        background: rgba(255, 255, 255, 0.03);
    }}

    .product-artifact-item__label {{
        font-size: 14px;
        font-weight: 700;
        margin-bottom: 4px;
    }}

    .product-artifact-item__meta {{
        color: var(--product-text-soft);
        font-size: 13px;
        line-height: 1.5;
    }}

    .product-shell .gradio-container .gr-button-primary,
    .product-shell .gradio-container button.primary,
    .gradio-container button.primary {{
        background: linear-gradient(135deg, rgba(34, 211, 238, 0.92), rgba(59, 130, 246, 0.92));
        border: none;
        color: #04111c;
        box-shadow: 0 14px 40px rgba(34, 211, 238, 0.18);
    }}

    .gradio-container button.secondary {{
        border-color: rgba(255, 255, 255, 0.14);
        background: rgba(255, 255, 255, 0.04);
        color: white;
    }}

    .gradio-container .tab-nav button {{
        border-radius: 999px !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        background: rgba(255,255,255,0.03) !important;
        color: white !important;
    }}

    .gradio-container .tab-nav button.selected {{
        border-color: rgba(106,227,255,0.28) !important;
        background: rgba(106,227,255,0.14) !important;
        color: white !important;
    }}

    .gradio-container .gr-json,
    .gradio-container .gr-dataframe,
    .gradio-container .gr-file,
    .gradio-container .gr-textbox,
    .gradio-container .gr-checkboxgroup,
    .gradio-container .gr-dropdown,
    .gradio-container .gr-accordion {{
        border-radius: 18px !important;
    }}

    @media (max-width: 1120px) {{
        .product-hero,
        .product-workflow-card-grid,
        .product-how-shell,
        .product-detail-grid,
        .product-result-grid {{
            grid-template-columns: 1fr;
        }}
    }}
    """