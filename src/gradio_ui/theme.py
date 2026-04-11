from __future__ import annotations


def build_product_css(accent_color: str = "#6ae3ff") -> str:
    return f"""
    :root {{
        --product-accent: {accent_color};
        --product-accent-soft: rgba(106, 227, 255, 0.10);
        --product-accent-strong: rgba(106, 227, 255, 0.22);
        --product-border: rgba(148, 163, 184, 0.18);
        --product-border-strong: rgba(106, 227, 255, 0.34);
        --product-bg: #08111f;
        --product-bg-elevated: #0d1728;
        --product-panel: rgba(12, 20, 33, 0.92);
        --product-panel-muted: rgba(15, 23, 42, 0.82);
        --product-panel-strong: rgba(10, 18, 30, 0.98);
        --product-text: #f8fafc;
        --product-text-soft: #cbd5e1;
        --product-text-muted: #94a3b8;
        --product-success: #34d399;
        --product-warning: #fbbf24;
        --product-danger: #fb7185;
        --product-shadow: 0 18px 48px rgba(2, 8, 23, 0.28);
        --product-radius-lg: 18px;
        --product-radius-md: 14px;
    }}

    .gradio-container {{
        background:
            radial-gradient(circle at top, rgba(56, 189, 248, 0.08), transparent 26%),
            linear-gradient(180deg, #050b15 0%, #07111d 42%, #0a1422 100%);
        color: var(--product-text);
        padding-top: 12px;
    }}

    .product-shell {{
        max-width: 1320px;
        margin: 0 auto;
    }}

    .product-topbar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        padding: 14px 18px;
        border: 1px solid var(--product-border);
        background: rgba(8, 14, 24, 0.82);
        border-radius: var(--product-radius-lg);
        margin-bottom: 14px;
        box-shadow: 0 10px 30px rgba(2, 8, 23, 0.16);
    }}

    .product-topbar__eyebrow {{
        font-size: 11px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--product-accent);
        margin-bottom: 4px;
    }}

    .product-topbar__title {{
        font-size: 21px;
        font-weight: 700;
    }}

    .product-topbar__hint {{
        font-size: 13px;
        color: var(--product-text-soft);
    }}

    .product-link-pill {{
        display: inline-flex;
        align-items: center;
        padding: 10px 14px;
        border-radius: 999px;
        border: 1px solid var(--product-border);
        color: var(--product-text);
        text-decoration: none;
        background: rgba(255, 255, 255, 0.03);
        transition: 180ms ease;
    }}

    .product-link-pill:hover {{
        border-color: var(--product-border-strong);
        background: rgba(255, 255, 255, 0.06);
    }}

    .product-hero {{
        display: block;
        margin-bottom: 12px;
    }}

    .product-masthead {{
        padding: 6px 0 10px 0;
    }}

    .product-panel {{
        border: 1px solid var(--product-border);
        background: var(--product-panel);
        border-radius: var(--product-radius-lg);
        padding: 20px;
        box-shadow: var(--product-shadow);
    }}

    .product-panel--strong {{
        background:
            linear-gradient(180deg, rgba(9, 17, 29, 0.98), rgba(11, 20, 34, 0.98));
        border-color: rgba(148, 163, 184, 0.22);
    }}

    .product-hero__eyebrow {{
        font-size: 11px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--product-accent);
        margin-bottom: 8px;
    }}

    .product-hero__title {{
        font-size: 34px;
        line-height: 1.08;
        font-weight: 800;
        margin: 0 0 12px 0;
    }}

    .product-hero__subtitle {{
        color: var(--product-text-soft);
        font-size: 15px;
        line-height: 1.62;
        margin-bottom: 16px;
    }}

    .product-hero__cta-note {{
        margin-top: 14px;
        font-size: 13px;
        line-height: 1.58;
        color: var(--product-text-muted);
    }}

    .product-kpi-grid {{
        display: grid;
        gap: 10px;
    }}

    .product-chip-row, .product-proof-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
    }}

    .product-chip, .product-proof-chip {{
        padding: 8px 11px;
        border-radius: 999px;
        border: 1px solid rgba(106, 227, 255, 0.18);
        background: rgba(106, 227, 255, 0.08);
        color: var(--product-text);
        font-size: 12px;
    }}

    .product-hero-stat {{
        border-radius: var(--product-radius-md);
        border: 1px solid var(--product-border);
        background: rgba(255, 255, 255, 0.025);
        padding: 14px;
    }}

    .product-hero-stat__label {{
        color: var(--product-text-muted);
        font-size: 12px;
        margin-bottom: 4px;
    }}

    .product-hero-stat__value {{
        font-size: 18px;
        font-weight: 700;
        line-height: 1.35;
    }}

    .product-main-grid {{
        align-items: start;
        gap: 18px;
        margin-bottom: 18px;
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: var(--product-radius-lg);
        background: linear-gradient(180deg, rgba(9, 17, 29, 0.95), rgba(11, 20, 34, 0.96));
        box-shadow: var(--product-shadow);
        padding: 18px;
    }}

    .product-setup-rail,
    .product-insight-canvas {{
        gap: 0;
        border: none;
        border-radius: 0;
        padding: 0 !important;
        box-shadow: none;
        background: transparent;
    }}

    .product-setup-rail {{
        padding-right: 18px !important;
        border-right: 1px solid rgba(148, 163, 184, 0.14);
    }}

    .product-insight-canvas {{
        padding-left: 8px !important;
    }}

    .product-setup-rail .product-step-card,
    .product-insight-canvas .product-step-card {{
        background: transparent;
        border: none;
        border-bottom: 1px solid rgba(148, 163, 184, 0.12);
        border-radius: 0;
        padding: 0 0 12px 0;
        margin: 0 0 12px 0;
    }}

    .product-setup-rail .product-panel,
    .product-setup-rail .product-status-card {{
        box-shadow: none;
    }}

    .product-setup-rail .product-workflow-detail-shell,
    .product-setup-rail .product-status-card {{
        background: transparent;
        border: none;
        border-bottom: 1px solid rgba(148, 163, 184, 0.12);
        border-radius: 0;
        padding: 0 0 14px 0;
        margin-bottom: 14px;
    }}

    .product-setup-rail .product-status-card__body,
    .product-setup-rail .product-status-card__title {{
        max-width: 52ch;
    }}

    .product-insight-canvas .product-summary-hero {{
        border-color: var(--product-border-strong);
        box-shadow: 0 22px 52px rgba(2, 8, 23, 0.32);
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
        font-size: 12px;
        font-weight: 600;
        margin-bottom: 12px;
    }}

    .product-status-pill--completed {{ background: rgba(52, 211, 153, 0.15); color: #bbf7d0; }}
    .product-status-pill--warning {{ background: rgba(251, 191, 36, 0.16); color: #fde68a; }}
    .product-status-pill--error {{ background: rgba(251, 113, 133, 0.16); color: #fecdd3; }}

    .product-section-title {{
        font-size: 20px;
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

    .product-step-card {{
        border: 1px solid rgba(148, 163, 184, 0.12);
        background: rgba(255, 255, 255, 0.022);
        border-radius: var(--product-radius-md);
        padding: 14px 16px;
        margin: 0 0 12px 0;
        max-width: none;
    }}

    .product-step-card__eyebrow {{
        font-size: 11px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--product-accent);
        margin-bottom: 8px;
    }}

    .product-step-card__title {{
        font-size: 17px;
        font-weight: 700;
        margin-bottom: 6px;
    }}

    .product-step-card__body {{
        font-size: 14px;
        color: var(--product-text-soft);
        line-height: 1.6;
    }}

    .product-workflow-selector-grid {{
        gap: 12px;
        margin-bottom: 12px;
    }}

    .product-workflow-button button {{
        min-height: 118px;
        width: 100%;
        white-space: pre-wrap;
        text-align: left;
        justify-content: flex-start;
        align-items: flex-start;
        padding: 16px !important;
        line-height: 1.45;
        border-radius: var(--product-radius-lg) !important;
        border: 1px solid var(--product-border) !important;
        background: rgba(255, 255, 255, 0.03) !important;
        color: var(--product-text) !important;
        box-shadow: none !important;
        font-size: 13px !important;
        transition: 180ms ease !important;
    }}

    .product-workflow-button button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 12px 24px rgba(2, 8, 23, 0.16) !important;
    }}

    .product-workflow-button button.primary {{
        background: linear-gradient(180deg, rgba(106, 227, 255, 0.12), rgba(255, 255, 255, 0.03)) !important;
        border-color: var(--product-border-strong) !important;
        color: var(--product-text) !important;
        box-shadow: 0 0 0 1px rgba(106, 227, 255, 0.16) inset !important;
    }}

    .product-workflow-button button.secondary:hover {{
        border-color: rgba(106, 227, 255, 0.28) !important;
        background: rgba(255, 255, 255, 0.05) !important;
    }}

    .product-workflow-detail-shell {{
        margin-bottom: 14px;
    }}

    .product-status-card {{
        border: 1px dashed rgba(148, 163, 184, 0.24);
        background: rgba(255, 255, 255, 0.025);
        border-radius: var(--product-radius-lg);
        padding: 16px;
        margin-bottom: 12px;
    }}

    .product-status-card--ready {{
        border-style: solid;
        border-color: rgba(52, 211, 153, 0.26);
        background: linear-gradient(180deg, rgba(52, 211, 153, 0.08), rgba(255, 255, 255, 0.02));
    }}

    .product-status-card__eyebrow {{
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--product-accent);
        margin-bottom: 6px;
    }}

    .product-status-card__title {{
        font-size: 16px;
        font-weight: 700;
        margin-bottom: 6px;
    }}

    .product-status-card__body {{
        font-size: 13px;
        line-height: 1.58;
        color: var(--product-text-soft);
        margin-bottom: 10px;
    }}

    .product-detail-grid {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin-top: 12px;
    }}

    .product-detail-grid--compact {{
        align-items: stretch;
    }}

    .product-detail-section {{
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: var(--product-radius-md);
        padding: 14px;
        background: rgba(255, 255, 255, 0.02);
    }}

    .product-quote-card {{
        border-left: 3px solid rgba(106, 227, 255, 0.55);
        background: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 12px;
        font-size: 13px;
        line-height: 1.6;
        color: var(--product-text);
    }}

    .product-inline-details {{
        margin-top: 14px;
        border: 1px solid rgba(148, 163, 184, 0.14);
        border-radius: var(--product-radius-md);
        background: rgba(255, 255, 255, 0.02);
        overflow: hidden;
    }}

    .product-inline-details summary {{
        list-style: none;
        cursor: pointer;
        padding: 14px 16px;
        font-size: 13px;
        font-weight: 700;
        color: var(--product-accent);
    }}

    .product-inline-details summary::-webkit-details-marker {{
        display: none;
    }}

    .product-inline-details__body {{
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        padding: 0 16px 16px 16px;
    }}

    .product-inline-meta-list {{
        margin: 14px 0;
        padding-left: 18px;
        color: var(--product-text-soft);
        font-size: 13px;
        line-height: 1.7;
    }}

    .product-callout {{
        margin-top: 14px;
        border-radius: var(--product-radius-md);
        padding: 14px 16px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }}

    .product-callout--warning {{
        background: rgba(251, 191, 36, 0.09);
        border-color: rgba(251, 191, 36, 0.28);
    }}

    .product-callout__title {{
        font-size: 13px;
        font-weight: 700;
        color: #fde68a;
        margin-bottom: 8px;
    }}

    .product-result-grid {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
        margin-top: 12px;
    }}

    .product-summary-hero {{
        margin-bottom: 14px;
    }}

    .product-summary-hero__eyebrow {{
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--product-accent);
        margin-bottom: 8px;
    }}

    .product-summary-hero__title {{
        font-size: 24px;
        font-weight: 700;
        line-height: 1.32;
        margin-bottom: 10px;
    }}

    .product-summary-hero__recommendation {{
        font-size: 14px;
        line-height: 1.6;
        color: var(--product-text-soft);
        margin-bottom: 12px;
    }}

    .product-summary-confidence {{
        font-size: 12px;
        line-height: 1.55;
        color: var(--product-text-muted);
        margin-bottom: 12px;
        padding-bottom: 12px;
        border-bottom: 1px solid rgba(148, 163, 184, 0.12);
    }}

    .product-summary-identity {{
        padding: 14px 0 4px 0;
    }}

    .product-summary-identity__title {{
        font-size: 16px;
        font-weight: 700;
        margin-bottom: 4px;
    }}

    .product-summary-identity__meta {{
        color: var(--product-text-soft);
        font-size: 13px;
        line-height: 1.55;
    }}

    .product-list-card {{
        border: 1px solid var(--product-border);
        background: rgba(255, 255, 255, 0.025);
        border-radius: var(--product-radius-md);
        padding: 16px;
    }}

    .product-list-card__title {{
        font-size: 14px;
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
        border: 1px solid rgba(148, 163, 184, 0.14);
        border-radius: var(--product-radius-md);
        padding: 12px 14px;
        background: rgba(255, 255, 255, 0.025);
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

    .product-proof-band {{
        background: transparent;
        margin-top: 8px;
        padding-top: 6px;
    }}

    .product-action-row,
    .product-primary-actions {{
        gap: 10px;
    }}

    .product-inline-help {{
        font-size: 12px;
        line-height: 1.55;
        color: var(--product-text-muted);
        padding: 2px 2px 10px 2px;
    }}

    .product-upload-dropzone,
    .product-document-selector,
    .product-instruction-box {{
        margin-bottom: 12px;
    }}

    .product-upload-dropzone {{
        border: 1px dashed rgba(106, 227, 255, 0.28);
        border-radius: var(--product-radius-lg);
        background: rgba(106, 227, 255, 0.05);
        padding: 6px;
    }}

    .product-upload-dropzone button {{
        border-radius: 12px !important;
    }}

    .gradio-container .gr-file {{
        border-style: dashed !important;
    }}

    .product-instruction-box textarea,
    .product-instruction-box input {{
        font-size: 14px !important;
        line-height: 1.6 !important;
    }}

    .gradio-container .gr-checkboxgroup label {{
        border: 1px solid rgba(148, 163, 184, 0.14);
        background: rgba(255, 255, 255, 0.025);
        border-radius: 12px;
        padding: 8px 10px;
        margin-bottom: 8px;
    }}

    .gradio-container .gr-accordion summary {{
        color: var(--product-text) !important;
        font-weight: 600 !important;
    }}

    .product-shell .gradio-container .gr-button-primary,
    .product-shell .gradio-container button.primary,
    .gradio-container button.primary {{
        background: linear-gradient(135deg, rgba(103, 232, 249, 0.92), rgba(96, 165, 250, 0.86));
        border: none;
        color: #07111d;
        box-shadow: 0 12px 28px rgba(34, 211, 238, 0.14);
    }}

    .gradio-container button.secondary {{
        border-color: rgba(148, 163, 184, 0.18);
        background: rgba(255, 255, 255, 0.04);
        color: var(--product-text);
    }}

    .gradio-container .tab-nav button {{
        border-radius: 12px !important;
        border: 1px solid rgba(148, 163, 184, 0.14) !important;
        background: rgba(255, 255, 255, 0.03) !important;
        color: var(--product-text) !important;
        min-height: 40px !important;
    }}

    .gradio-container .tab-nav button.selected {{
        border-color: rgba(106, 227, 255, 0.28) !important;
        background: rgba(106, 227, 255, 0.10) !important;
        color: var(--product-text) !important;
    }}

    .gradio-container .gr-json,
    .gradio-container .gr-dataframe,
    .gradio-container .gr-file,
    .gradio-container .gr-textbox,
    .gradio-container .gr-checkboxgroup,
    .gradio-container .gr-dropdown,
    .gradio-container .gr-accordion {{
        border-radius: var(--product-radius-md) !important;
        border-color: rgba(148, 163, 184, 0.18) !important;
        background: rgba(255, 255, 255, 0.03) !important;
    }}

    .gradio-container .gr-group,
    .gradio-container .block,
    .gradio-container .gr-box,
    .gradio-container .gr-panel {{
        box-shadow: none !important;
    }}

    .gradio-container label,
    .gradio-container .gr-form label,
    .gradio-container .gr-block-label {{
        color: var(--product-text-soft) !important;
    }}

    .gradio-container textarea,
    .gradio-container input,
    .gradio-container select {{
        color: var(--product-text) !important;
    }}

    .gradio-container .gr-dataframe table,
    .gradio-container .gr-dataframe th,
    .gradio-container .gr-dataframe td {{
        background: transparent !important;
        color: var(--product-text) !important;
    }}

    .gradio-container .gr-dataframe th {{
        color: var(--product-text-soft) !important;
        font-size: 12px !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}

    @media (max-width: 1120px) {{
        .product-hero,
        .product-workflow-card-grid,
        .product-detail-grid,
        .product-result-grid,
        .product-main-grid {{
            grid-template-columns: 1fr;
        }}

        .product-main-grid {{
            padding: 16px;
        }}

        .product-setup-rail {{
            border-right: none;
            padding-right: 0 !important;
            margin-bottom: 6px;
        }}

        .product-insight-canvas {{
            padding-left: 0 !important;
        }}

        .product-workflow-button button {{
            min-height: 108px;
        }}

        .product-hero__title {{
            font-size: 28px;
        }}
    }}

    @media (max-width: 768px) {{
        .product-topbar {{
            flex-direction: column;
            align-items: flex-start;
        }}

        .product-panel,
        .product-step-card {{
            padding: 16px;
        }}

        .product-summary-hero__title {{
            font-size: 20px;
        }}
    }}
    """