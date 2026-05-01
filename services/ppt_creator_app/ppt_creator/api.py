from __future__ import annotations

import argparse
import json
import mimetypes
import os
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlparse

from pydantic import ValidationError

from ppt_creator.assets import get_asset_collection, list_asset_collections
from ppt_creator.brand_packs import get_brand_pack, list_brand_packs
from ppt_creator.catalog import build_marketplace_catalog
from ppt_creator.preview import (
    compare_pptx_artifacts,
    format_visual_regression_failure,
    promote_preview_baseline,
    render_previews,
    render_previews_for_rendered_artifact,
    render_previews_from_pptx,
    review_pptx_artifact,
    visual_regression_has_failures,
)
from ppt_creator.profiles import get_audience_profile, list_audience_profiles
from ppt_creator.qa import augment_review_with_preview_artifacts, review_presentation
from ppt_creator.renderer import PresentationRenderer
from ppt_creator.schema import PresentationInput
from ppt_creator.templates import (
    build_domain_template,
    build_template_packet,
    list_template_domains,
)
from ppt_creator.workflows import build_workflow_packet, get_workflow_preset, list_workflow_presets


class APIRequestError(ValueError):
    def __init__(self, message: str, status_code: int = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.status_code = status_code


def ai_status_payload(
    *,
    provider_name: str = "local_service",
    base_url: str | None = None,
    model_name: str | None = None,
    generation_attempts: int | None = None,
) -> dict[str, object]:
    from ppt_creator_ai.providers import build_provider, get_provider, list_provider_names

    provider_names = list_provider_names()
    provider = build_provider(
        provider_name,
        base_url=base_url,
        model_name=model_name,
        generation_attempts=str(generation_attempts) if generation_attempts is not None else None,
    )
    provider_details = [
        {
            "name": get_provider(name).name,
            "description": get_provider(name).description,
            "supports_model_listing": callable(getattr(get_provider(name), "list_models", None)),
        }
        for name in provider_names
    ]
    status_callable = getattr(provider, "status_payload", None)
    if callable(status_callable):
        selected_status = status_callable()
    else:
        selected_status = {
            "provider_name": provider.name,
            "health_status": "not_applicable",
            "health_error": None,
            "model_name": None,
            "model_source": "n/a",
            "supports_model_listing": False,
        }

    return {
        "mode": "ai-status",
        "providers": provider_names,
        "provider_details": provider_details,
        "selected_provider": provider.name,
        "provider_status": selected_status,
    }


def _build_playground_html() -> str:
    default_spec = build_domain_template("sales")
    initial_json = json.dumps(default_spec, indent=2, ensure_ascii=False)
    initial_briefing_json = json.dumps(
        {
            "title": "AI copilots for sales teams",
            "audience": "Revenue leadership",
            "briefing_text": (
                "Sales teams lose time in repetitive drafting and follow-up work. "
                "Managers need better visibility into execution quality. "
                "Start with one narrow workflow, measure lift, and scale only after the signal is clear."
            ),
            "recommendations": [
                "Start with one workflow that already has executive pull.",
                "Measure adoption and quality lift before expansion.",
                "Keep the narrative focused on decision utility, not AI novelty.",
            ],
        },
        indent=2,
        ensure_ascii=False,
    )
    js_newline = r"\n"
    js_newline_pattern = r"\n+"
    return rf"""<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <title>PPT Creator Playground</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f3f6fb;
      --surface: #ffffff;
      --panel-muted: #f7f9fc;
      --border: #d9e1ec;
      --border-strong: #c4d0df;
      --text: #132238;
      --text-muted: #607089;
      --accent: #355cde;
      --accent-strong: #7c3aed;
      --accent-soft: rgba(53, 92, 222, 0.12);
      --success: #15803d;
      --danger: #b42318;
      --shadow: 0 20px 60px rgba(15, 23, 42, 0.10);
      --code-bg: #0f172a;
      --code-text: #e2e8f0;
    }}
    body[data-theme='dark'] {{
      color-scheme: dark;
      --bg: #08111f;
      --surface: #0f1b2d;
      --panel-muted: #142338;
      --border: #263247;
      --border-strong: #31435f;
      --text: #e8eef8;
      --text-muted: #9fb0c7;
      --accent: #7aa2ff;
      --accent-strong: #a78bfa;
      --accent-soft: rgba(122, 162, 255, 0.14);
      --success: #4ade80;
      --danger: #fb7185;
      --shadow: 0 20px 60px rgba(2, 6, 23, 0.48);
      --code-bg: #081120;
      --code-text: #dbeafe;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(53, 92, 222, 0.12), transparent 28%),
        radial-gradient(circle at top right, rgba(124, 58, 237, 0.10), transparent 24%),
        var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      transition: background 0.25s ease, color 0.25s ease;
    }}
    .app-shell {{ max-width: 1540px; margin: 0 auto; padding: 28px 24px 48px; }}
    .hero {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 24px;
      padding: 28px 30px;
      border-radius: 28px;
      border: 1px solid var(--border);
      background: linear-gradient(135deg, rgba(53, 92, 222, 0.16), rgba(124, 58, 237, 0.08)), var(--surface);
      box-shadow: var(--shadow);
    }}
    .eyebrow {{
      display: inline-block;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--accent);
    }}
    h1 {{ margin: 10px 0 10px; font-size: 40px; line-height: 1.02; letter-spacing: -0.04em; }}
    .hero-copy {{ max-width: 760px; margin: 0; color: var(--text-muted); font-size: 16px; line-height: 1.6; }}
    .hero-chips {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }}
    .chip {{
      display: inline-flex;
      align-items: center;
      padding: 8px 12px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }}
    .theme-toolbar {{ display: flex; flex-wrap: wrap; justify-content: flex-end; align-items: center; gap: 12px; }}
    .status-pill {{
      display: inline-flex;
      align-items: center;
      padding: 10px 12px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: var(--panel-muted);
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }}
    label {{
      display: block;
      margin-bottom: 6px;
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    input, select, textarea {{
      width: 100%;
      margin: 0 0 12px;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--border);
      background: var(--panel-muted);
      color: var(--text);
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
    }}
    textarea {{ min-height: 380px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; line-height: 1.55; resize: vertical; }}
    #briefingInput {{ min-height: 220px; }}
    input:focus, select:focus, textarea:focus {{
      border-color: var(--accent);
      box-shadow: 0 0 0 4px var(--accent-soft);
    }}
    button {{
      border: none;
      border-radius: 14px;
      padding: 12px 16px;
      background: linear-gradient(135deg, var(--accent), var(--accent-strong));
      color: white;
      font-size: 14px;
      font-weight: 800;
      cursor: pointer;
      box-shadow: 0 12px 28px rgba(53, 92, 222, 0.24);
      transition: transform 0.12s ease, box-shadow 0.2s ease, opacity 0.2s ease;
    }}
    button:hover {{ transform: translateY(-1px); box-shadow: 0 16px 30px rgba(53, 92, 222, 0.28); }}
    button:disabled {{ opacity: 0.55; cursor: not-allowed; transform: none; box-shadow: none; }}
    #themeToggleButton, #aiRefreshStatusButton, #aiLoadBriefingButton {{
      background: var(--panel-muted);
      color: var(--text);
      border: 1px solid var(--border);
      box-shadow: none;
    }}
    .row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }}
    .toolbar {{ margin-top: 16px; display: flex; flex-wrap: wrap; gap: 10px; }}
    .editor-section {{
      margin-top: 18px;
      padding: 20px;
      border-radius: 24px;
      border: 1px solid var(--border);
      background: var(--surface);
      box-shadow: var(--shadow);
    }}
    .section-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 18px; }}
    .section-kicker {{ color: var(--accent); font-size: 12px; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; }}
    .section-title {{ margin: 6px 0; font-size: 22px; line-height: 1.2; letter-spacing: -0.03em; }}
    .section-copy {{ margin: 0; max-width: 760px; color: var(--text-muted); font-size: 14px; line-height: 1.6; }}
    .toggles {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; align-items: center; }}
    .toggles label {{
      margin: 0;
      padding: 10px 12px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: var(--panel-muted);
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.02em;
      text-transform: none;
    }}
    .toggles input {{ width: auto; margin: 0; accent-color: var(--accent); }}
    .editor-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }}
    .editor-card {{
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 14px;
      background: var(--panel-muted);
    }}
    .editor-card h3 {{ margin: 0 0 8px; font-size: 13px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; }}
    .editor-hint {{ font-size: 12px; color: var(--text-muted); margin-top: 6px; line-height: 1.5; }}
    .status {{
      margin-top: 12px;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--border);
      background: var(--panel-muted);
      color: var(--text-muted);
      font-size: 14px;
    }}
    .links {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 16px 0 12px; }}
    .links a {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 12px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: var(--panel-muted);
      color: var(--text);
      text-decoration: none;
      font-weight: 700;
    }}
    .insights {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin-top: 16px; }}
    .insight-card {{ border: 1px solid var(--border); border-radius: 18px; padding: 14px; background: var(--panel-muted); }}
    .insight-card h3 {{ margin: 0 0 8px; font-size: 13px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; }}
    .insight-card ul {{ margin: 0; padding-left: 18px; color: var(--text); line-height: 1.55; }}
    pre {{
      margin: 0;
      padding: 18px;
      border-radius: 18px;
      border: 1px solid var(--border);
      background: var(--code-bg);
      color: var(--code-text);
      overflow: auto;
      max-height: 360px;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
    }}
    .gallery {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; margin-top: 20px; }}
    .gallery-card {{
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 12px;
      background: var(--panel-muted);
      box-shadow: var(--shadow);
    }}
    .gallery-card button {{
      all: unset;
      display: block;
      width: 100%;
      cursor: pointer;
    }}
    .gallery-card button:focus-visible {{
      outline: 3px solid var(--accent);
      border-radius: 14px;
    }}
    .gallery-card img {{ width: 100%; border-radius: 12px; display: block; border: 1px solid var(--border); }}
    .thumb-meta {{ margin-top: 8px; font-size: 12px; color: var(--text-muted); }}
    .action-toolbar {{ margin-top: 18px; }}
    .action-toolbar button {{ min-width: 132px; }}
    @media (max-width: 960px) {{
      .app-shell {{ padding: 20px 16px 40px; }}
      .hero {{ flex-direction: column; }}
      h1 {{ font-size: 32px; }}
      .theme-toolbar {{ justify-content: flex-start; }}
    }}
  </style>
</head>
<body data-theme='light'>
  <div class='app-shell'>
  <div class='hero'>
    <div>
      <div class='eyebrow'>Deck studio + AI copilot</div>
      <h1>PPT Creator Playground</h1>
      <p class='hero-copy'>Build decks, inspect QA, compare versions and generate structured slides from briefing without embedding model runtimes in the app.</p>
      <div class='hero-chips'>
        <span class='chip'>JSON → PPTX</span>
        <span class='chip'>Preview & QA</span>
        <span class='chip'>External AI runtime</span>
      </div>
    </div>
    <div class='theme-toolbar'>
      <div class='status-pill'>Interactive studio</div>
      <button id='themeToggleButton' onclick='toggleTheme()'>🌙 Dark mode</button>
    </div>
  </div>
  <div class='editor-section'>
    <div class='section-header'>
      <div>
        <div class='section-kicker'>Workspace setup</div>
        <h2 class='section-title'>Configure output, templates and review flow</h2>
        <p class='section-copy'>Choose where artifacts go, bootstrap from templates or workflows, and decide how previews, regression and baseline management should behave.</p>
      </div>
    </div>
  <div class='row'>
    <div>
      <label>Output PPTX path</label>
      <input id='outputPath' value='outputs/playground_output.pptx' />
    </div>
    <div>
      <label>Preview directory</label>
      <input id='previewDir' value='outputs/playground_previews' />
    </div>
  </div>
  <div class='row'>
    <div>
      <label>Workflow preset</label>
      <select id='workflowPreset'></select>
    </div>
    <div>
      <label>Template domain</label>
      <select id='templateDomain'></select>
    </div>
    <div>
      <label>Brand pack</label>
      <select id='brandPack'></select>
    </div>
  </div>
  <div class='row'>
    <div>
      <label>Audience profile</label>
      <select id='audienceProfile'></select>
    </div>
    <div>
      <label>Preview backend</label>
      <select id='previewBackend'>
        <option value='auto'>auto</option>
        <option value='synthetic'>synthetic</option>
        <option value='office'>office</option>
      </select>
    </div>
    <div>
      <label>Baseline directory</label>
      <input id='baselineDir' value='' placeholder='optional baseline preview dir' />
    </div>
  </div>
  <div class='row'>
    <div>
      <label>Compare before PPTX</label>
      <input id='compareBeforePptx' value='outputs/before.pptx' />
    </div>
    <div>
      <label>Compare after PPTX</label>
      <input id='compareAfterPptx' value='outputs/after.pptx' />
    </div>
    <div>
      <label>Compare output directory</label>
      <input id='compareOutputDir' value='outputs/playground_compare' />
    </div>
  </div>
  <div class='toggles'>
    <label><input id='autoValidate' type='checkbox' /> Auto validate</label>
    <label><input id='autoReview' type='checkbox' /> Auto review</label>
    <label><input id='autoPreviewWithReview' type='checkbox' /> Include preview in auto review</label>
    <label><input id='requireRealPreviews' type='checkbox' /> Require real previews</label>
    <label><input id='failOnRegression' type='checkbox' /> Fail on regression</label>
  </div>
  <div class='insights'>
    <div class='insight-card'>
      <h3>Default trusted workflow</h3>
      <ul>
        <li>1. Review the JSON draft</li>
        <li>2. Render the final PPTX</li>
        <li>3. Review the rendered PPTX artifacts</li>
        <li>4. Compare against the approved baseline</li>
        <li>5. Promote the new baseline only after sign-off</li>
      </ul>
    </div>
    <div class='insight-card'>
      <h3>Daily iteration loop</h3>
      <ul>
        <li>Use workflows + brand packs to bootstrap faster.</li>
        <li>Keep auto review on while editing the spec.</li>
        <li>Use rendered previews for sign-off instead of trusting only synthetic previews.</li>
      </ul>
    </div>
    <div class='insight-card'>
      <h3>Live review mode</h3>
      <ul id='liveReviewSummary'>
        <li>Auto review is off. Use Iterate flow for one-click QA.</li>
      </ul>
      <div class='editor-hint'>Tip: Ctrl/Cmd+Enter runs the iterate flow. Ctrl/Cmd+Shift+Enter exports the current deck.</div>
    </div>
  </div>
  </div>
  <div class='editor-section'>
    <div class='section-header'>
      <div>
        <div class='section-kicker'>AI copilot</div>
        <h2 class='section-title'>Generate a deck from briefing</h2>
        <p class='section-copy'>Pick a provider, inspect runtime health, and turn briefing JSON into a draft deck. You can stop at JSON, trigger QA + preview automatically or render immediately.</p>
      </div>
    </div>
    <div class='row'>
      <div>
        <label>AI provider</label>
        <select id='aiProvider'></select>
      </div>
      <div>
        <label>AI theme override</label>
        <input id='aiThemeName' value='' placeholder='optional theme override' />
      </div>
      <div>
        <label>Authoring mode</label>
        <select id='aiAuthoringMode'>
          <option value='ai_first'>AI-first (send raw prompt to the AI author)</option>
          <option value='hybrid'>Hybrid (app structures intent before calling AI)</option>
        </select>
      </div>
    </div>
    <div class='row'>
      <div>
        <label>AI runtime URL</label>
        <input id='aiBaseUrl' value='' placeholder='optional override, e.g. http://127.0.0.1:11434' />
      </div>
      <div>
        <label>AI model override / selection</label>
        <input id='aiModelName' value='' list='aiModelOptions' placeholder='auto-discover or type a model' />
        <datalist id='aiModelOptions'></datalist>
      </div>
      <div>
        <label>Generation attempts</label>
        <input id='aiGenerationAttempts' type='number' min='1' step='1' value='3' />
      </div>
    </div>
    <label>Describe the deck you want</label>
    <textarea id='intentInput' style='min-height: 180px;' placeholder='Example: Create a board deck explaining why we should launch a sales copilot now, with premium visuals, KPIs, a timeline, option comparison, and a strong close.'></textarea>
    <div class='editor-hint'>Write in plain language. In <strong>AI-first</strong> mode, the raw prompt is sent directly to the AI so it can author the whole deck structure. The structured JSON below remains an advanced/manual override.</div>
    <div class='toggles'>
      <label><input id='aiUseIntentMode' type='checkbox' checked /> Use the freeform description as the primary AI input</label>
      <label><input id='aiAutoPreview' type='checkbox' checked /> Review + preview after AI generate</label>
      <label><input id='aiAutoRender' type='checkbox' /> Render after AI generate</label>
    </div>
    <label>Structured briefing JSON (advanced)</label>
    <textarea id='briefingInput' style='min-height: 220px;'>{initial_briefing_json}</textarea>
    <div class='toolbar'>
      <button id='aiLoadBriefingButton' onclick='loadBriefingExample()'>Load briefing example</button>
      <button id='aiRefreshStatusButton' onclick='refreshAiStatus()'>Refresh AI status</button>
      <button id='aiGenerateButton' onclick='generateFromBriefing()'>Generate from AI briefing</button>
      <button id='aiGenerateRenderButton' onclick='generateAndRenderFromBriefing()'>Generate + Render with AI</button>
    </div>
    <div id='aiActionStatus' class='status'>AI section ready.</div>
    <div id='aiRuntimeStatus' class='insight-card' style='margin-top: 12px;'></div>
    <div class='editor-hint'>This uses the optional AI layer through the existing API endpoints while keeping Ollama/service runtimes external to the app.</div>
  </div>
  <div class='editor-section'>
    <div class='section-header'>
      <div>
        <div class='section-kicker'>Deck editor</div>
        <h2 class='section-title'>Inspect and refine the generated spec</h2>
        <p class='section-copy'>Edit the raw presentation JSON directly, then use the guided editor below for the most common slide structures.</p>
      </div>
    </div>
    <textarea id='spec'>{initial_json}</textarea>
    <div class='row'>
      <div>
        <label>Guided editor — selected slide</label>
        <select id='slideSelector'></select>
      </div>
      <div>
        <label>Slide focus</label>
        <input id='slideTypeBadge' value='No slide selected' readonly />
      </div>
    </div>
    <div id='slideFields' class='editor-grid'></div>
    <div class='toolbar'>
      <button onclick='applyGuidedEdits()'>Apply guided edits</button>
      <button onclick='refreshSlideEditor()'>Reload from JSON</button>
    </div>
  </div>
  <div class='toolbar action-toolbar'>
    <button onclick='runIterateFlow()'>Iterate flow</button>
    <button onclick='focusTopRiskSlide()'>Focus top risk slide</button>
    <button onclick='exportCurrentDeck()'>Export current deck</button>
    <button onclick='loadWorkflow()'>Load workflow</button>
    <button onclick='loadTemplate()'>Load starter</button>
    <button onclick='runAction("/review")'>1. Review draft</button>
    <button onclick='runAction("/render")'>2. Render PPTX</button>
    <button onclick='reviewRenderedPptx()'>3. Review rendered PPTX</button>
    <button onclick='comparePptxArtifacts()'>4. Compare PPTX</button>
    <button onclick='promoteBaseline()'>5. Promote baseline</button>
    <button onclick='runAction("/preview")'>Preview spec</button>
    <button onclick='runAction("/validate")'>Validate JSON</button>
  </div>
  <div class='editor-section results-shell'>
    <div class='section-header'>
      <div>
        <div class='section-kicker'>Execution output</div>
        <h2 class='section-title'>Inspect results, artifacts and previews</h2>
        <p class='section-copy'>Use this area to read raw API responses, open generated artifacts and visually inspect QA insights and preview thumbnails.</p>
      </div>
    </div>
  <div id='status' class='status'>Ready.</div>
  <div id='artifactLinks' class='links'></div>
  <pre id='result'>Ready.</pre>
  <div id='insights' class='insights'></div>
  <div id='previewGallery' class='gallery'></div>
  </div>
  <script>
    const storageKey = 'ppt_creator_playground_state_v3';
    const themeStorageKey = 'ppt_creator_playground_theme_v1';
    let aiProviderMetadata = {{}};
    let latestActionResult = null;

    function applyTheme(theme) {{
      const resolved = theme === 'dark' ? 'dark' : 'light';
      document.body.dataset.theme = resolved;
      document.documentElement.style.colorScheme = resolved;
      const button = document.getElementById('themeToggleButton');
      if (button) {{
        button.textContent = resolved === 'dark' ? '☀️ Light mode' : '🌙 Dark mode';
      }}
    }}

    function initializeTheme() {{
      const saved = localStorage.getItem(themeStorageKey);
      const fallback = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      applyTheme(saved || fallback);
    }}

    function toggleTheme() {{
      const next = document.body.dataset.theme === 'dark' ? 'light' : 'dark';
      localStorage.setItem(themeStorageKey, next);
      applyTheme(next);
    }}

    function artifactUrl(path) {{
      return `/artifact?path=${{encodeURIComponent(path)}}`;
    }}

    function setStatus(message) {{
      document.getElementById('status').textContent = message;
    }}

    function collectState() {{
      return {{
        outputPath: document.getElementById('outputPath').value,
        previewDir: document.getElementById('previewDir').value,
        slideSelector: document.getElementById('slideSelector').value,
        workflowPreset: document.getElementById('workflowPreset').value,
        templateDomain: document.getElementById('templateDomain').value,
        brandPack: document.getElementById('brandPack').value,
        audienceProfile: document.getElementById('audienceProfile').value,
        previewBackend: document.getElementById('previewBackend').value,
        baselineDir: document.getElementById('baselineDir').value,
        requireRealPreviews: document.getElementById('requireRealPreviews').checked,
        failOnRegression: document.getElementById('failOnRegression').checked,
        compareBeforePptx: document.getElementById('compareBeforePptx').value,
        compareAfterPptx: document.getElementById('compareAfterPptx').value,
        compareOutputDir: document.getElementById('compareOutputDir').value,
        aiProvider: document.getElementById('aiProvider').value,
        aiBaseUrl: document.getElementById('aiBaseUrl').value,
        aiModelName: document.getElementById('aiModelName').value,
        aiGenerationAttempts: document.getElementById('aiGenerationAttempts').value,
        aiThemeName: document.getElementById('aiThemeName').value,
        aiAuthoringMode: document.getElementById('aiAuthoringMode').value,
        aiUseIntentMode: document.getElementById('aiUseIntentMode').checked,
        aiAutoPreview: document.getElementById('aiAutoPreview').checked,
        aiAutoRender: document.getElementById('aiAutoRender').checked,
        intentInput: document.getElementById('intentInput').value,
        briefingInput: document.getElementById('briefingInput').value,
        autoValidate: document.getElementById('autoValidate').checked,
        autoReview: document.getElementById('autoReview').checked,
        autoPreviewWithReview: document.getElementById('autoPreviewWithReview').checked,
        spec: document.getElementById('spec').value,
      }};
    }}

    function persistState() {{
      localStorage.setItem(storageKey, JSON.stringify(collectState()));
    }}

    function restoreState() {{
      const raw = localStorage.getItem(storageKey);
      if (!raw) return;
      try {{
        const state = JSON.parse(raw);
        for (const [key, value] of Object.entries(state)) {{
          const element = document.getElementById(key);
          if (element && value !== undefined && value !== null) {{
            if (element.type === 'checkbox') element.checked = Boolean(value);
            else element.value = value;
          }}
        }}
      }} catch (_error) {{
        localStorage.removeItem(storageKey);
      }}
    }}

    let autoRunHandle = null;
    let autoRunSequence = 0;

    function renderPreviewGallery(previews) {{
      const gallery = document.getElementById('previewGallery');
      gallery.innerHTML = '';
      for (const [index, preview] of previews.entries()) {{
        const card = document.createElement('div');
        card.className = 'gallery-card';
        card.innerHTML = `<button type="button" onclick="focusSlide(${{index}})"><img src="${{artifactUrl(preview)}}" alt="Preview ${{index + 1}}" /><div class="thumb-meta">Slide ${{String(index + 1).padStart(2, '0')}} · jump to editor</div></button>`;
        gallery.appendChild(card);
      }}
    }}

    function focusEditor() {{
      const node = document.getElementById('slideFields');
      if (node) node.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
    }}

    function focusSlide(index, options = {{}}) {{
      const selector = document.getElementById('slideSelector');
      if (!selector || !selector.options.length) return;
      const normalized = Math.max(0, Math.min(selector.options.length - 1, Number(index) || 0));
      selector.value = String(normalized);
      renderSelectedSlideEditor();
      if (options.scroll !== false) focusEditor();
    }}

    function syncLiveReviewSummary() {{
      const node = document.getElementById('liveReviewSummary');
      if (!node) return;
      const autoValidate = document.getElementById('autoValidate').checked;
      const autoReview = document.getElementById('autoReview').checked;
      const includePreview = document.getElementById('autoPreviewWithReview').checked;
      const previewBackend = document.getElementById('previewBackend').value || 'auto';
      const requireReal = document.getElementById('requireRealPreviews').checked;
      const topRiskSlides = ((latestActionResult && (latestActionResult.top_risk_slides || (latestActionResult.quality_review && latestActionResult.quality_review.top_risk_slides))) || []).slice(0, 1);
      const messages = [];
      if (autoReview) {{
        messages.push(`Auto review is on${{includePreview ? ' with preview artifacts.' : '.'}}`);
      }} else if (autoValidate) {{
        messages.push('Auto validate is on.');
      }} else {{
        messages.push('Auto review is off. Use Iterate flow for one-click QA.');
      }}
      if (includePreview) {{
        messages.push(`Preview backend: ${{previewBackend}}${{requireReal ? ' (real preview required)' : ''}}.`);
      }}
      if (topRiskSlides.length) {{
        const topRisk = topRiskSlides[0];
        messages.push(`Top risk right now: slide ${{String(topRisk.slide_number || 1).padStart(2, '0')}}${{topRisk.title ? ` • ${{escapeHtml(topRisk.title)}}` : ''}}.`);
      }}
      messages.push('Click a preview thumbnail to jump back to that slide in the editor.');
      node.innerHTML = messages.map(item => `<li>${{escapeHtml(item)}}</li>`).join('');
    }}

    function focusTopRiskSlide() {{
      const topRiskSlides = ((latestActionResult && (latestActionResult.top_risk_slides || (latestActionResult.quality_review && latestActionResult.quality_review.top_risk_slides))) || []).slice(0, 1);
      if (!topRiskSlides.length) {{
        setStatus('No risky slide available yet. Run review first.');
        return;
      }}
      focusSlide(Math.max(0, (topRiskSlides[0].slide_number || 1) - 1));
      setStatus(`Focused top-risk slide ${{String(topRiskSlides[0].slide_number || 1).padStart(2, '0')}}.`);
    }}

    function updateArtifactLinks(result) {{
      const links = [];
      if (result.output_path) links.push(`<a href="${{artifactUrl(result.output_path)}}">output</a>`);
      if (result.preview_result && result.preview_result.thumbnail_sheet) links.push(`<a href="${{artifactUrl(result.preview_result.thumbnail_sheet)}}">thumbnail sheet</a>`);
      if (result.preview_result && result.preview_result.preview_manifest) links.push(`<a href="${{artifactUrl(result.preview_result.preview_manifest)}}">preview manifest</a>`);
      if (result.before_preview_manifest) links.push(`<a href="${{artifactUrl(result.before_preview_manifest)}}">before manifest</a>`);
      if (result.after_preview_manifest) links.push(`<a href="${{artifactUrl(result.after_preview_manifest)}}">after manifest</a>`);
      if (result.preview_manifest) links.push(`<a href="${{artifactUrl(result.preview_manifest)}}">baseline manifest</a>`);
      document.getElementById('artifactLinks').innerHTML = links.join(' ');
    }}

    function renderInsights(result) {{
      const container = document.getElementById('insights');
      container.innerHTML = '';
      latestActionResult = result || {{}};
      const previewPayload = result.preview_result || result;
      const packet = result.packet || (result.preview_recommendation ? result : {{}});
      const regression = previewPayload.visual_regression || result.comparison;
      const guidance = regression && regression.guidance ? regression.guidance : [];
      const topRegressions = regression && regression.top_regressions ? regression.top_regressions : [];
      const cards = [];
      const generationResult = result.generation || (result.mode === 'generate' ? result : null);
      const generationAnalysis = generationResult ? (generationResult.analysis || {{}}) : {{}};
      const aiExchange = generationAnalysis.ai_exchange || null;

      if (result.quality_review) {{
        const qr = result.quality_review;
        cards.push(`
          <div class="insight-card">
            <h3>Quality review</h3>
            <ul>
              <li>Status: ${{qr.status || 'n/a'}}</li>
              <li>Average score: ${{qr.average_score ?? 'n/a'}}</li>
              <li>Issues: ${{qr.issue_count ?? 0}}</li>
              <li>High / Medium / Low: ${{(qr.severity_counts || {{}}).high || 0}} / ${{(qr.severity_counts || {{}}).medium || 0}} / ${{(qr.severity_counts || {{}}).low || 0}}</li>
            </ul>
          </div>
        `);
      }}
      if (result.status || result.average_score !== undefined) {{
        cards.push(`
          <div class="insight-card">
            <h3>Review summary</h3>
            <ul>
              <li>Status: ${{result.status || 'n/a'}}</li>
              <li>Average score: ${{result.average_score ?? 'n/a'}}</li>
              <li>Issues: ${{result.issue_count ?? 0}}</li>
              <li>High / Medium / Low: ${{(result.severity_counts || {{}}).high || 0}} / ${{(result.severity_counts || {{}}).medium || 0}} / ${{(result.severity_counts || {{}}).low || 0}}</li>
            </ul>
          </div>
        `);
      }}
      const topRiskSlides = (result.top_risk_slides || (result.quality_review && result.quality_review.top_risk_slides) || []).slice(0, 3);
      if (topRiskSlides.length) {{
        cards.push(`
          <div class="insight-card">
            <h3>Focus risky slides</h3>
            <ul>${{topRiskSlides.map(item => `<li><a href="#" onclick="focusSlide(${{Math.max(0, (item.slide_number || 1) - 1)}}); return false;">Slide ${{String(item.slide_number || 1).padStart(2, '0')}}</a>${{item.title ? ` • ${{escapeHtml(item.title)}}` : ''}}</li>`).join('')}}</ul>
          </div>
        `);
      }}
      if (previewPayload && (previewPayload.backend_used || previewPayload.preview_source || previewPayload.preview_manifest)) {{
        cards.push(`
          <div class="insight-card">
            <h3>Preview artifact</h3>
            <ul>
              <li>Source: ${{previewPayload.preview_source || 'n/a'}}</li>
              <li>Backend: ${{previewPayload.backend_used || previewPayload.backend_requested || 'n/a'}}</li>
              <li>Real preview: ${{previewPayload.real_preview === true ? 'yes' : 'no'}}</li>
              <li>Count: ${{previewPayload.preview_count ?? 0}}</li>
            </ul>
          </div>
        `);
      }}
      if (result.mode === 'compare-pptx' || result.before_preview_manifest || result.after_preview_manifest) {{
        cards.push(`
          <div class="insight-card">
            <h3>Comparison workflow</h3>
            <ul>
              <li>Use rendered `.pptx` artifacts for critical regression checks.</li>
              <li>Promote a new baseline only after reviewing top regressions and slide-set changes.</li>
              <li>Keep provenance manifests with the preview set for more reliable debugging.</li>
            </ul>
          </div>
        `);
      }}
      if (packet.brand_pack) {{
        cards.push(`
          <div class="insight-card">
            <h3>Brand pack</h3>
            <ul>
              <li>${{packet.brand_pack.display_name}}</li>
              <li>${{packet.brand_pack.description}}</li>
            </ul>
          </div>
        `);
      }}
      if (packet.preview_recommendation) {{
        const recommendation = packet.preview_recommendation;
        cards.push(`
          <div class="insight-card">
            <h3>Preview recommendation</h3>
            <ul>
              <li>Backend: ${{recommendation.backend || 'auto'}}</li>
              <li>Real preview required: ${{recommendation.require_real_previews ? 'yes' : 'no'}}</li>
              <li>Baseline dir: ${{recommendation.baseline_dir || 'n/a'}}</li>
              <li>Recommended source: ${{recommendation.recommended_source || 'rendered_pptx'}}</li>
              <li>Flow: ${{(recommendation.critical_regression_flow || []).join(' → ') || 'n/a'}}</li>
              <li>${{recommendation.guidance || 'Use rendered PPTX preview for critical regression checks.'}}</li>
            </ul>
          </div>
        `);
      }}
      if (packet.asset_collections && packet.asset_collections.length) {{
        cards.push(`
          <div class="insight-card">
            <h3>Asset presets</h3>
            <ul>${{packet.asset_collections.slice(0, 4).map(collection => `<li>${{collection.display_name || collection.name || 'collection'}} — ${{collection.description || ''}}</li>`).join('')}}</ul>
          </div>
        `);
      }}
      if (packet.slide_asset_suggestions && packet.slide_asset_suggestions.length) {{
        cards.push(`
          <div class="insight-card">
            <h3>Slide visual suggestions</h3>
            <ul>${{packet.slide_asset_suggestions.slice(0, 4).map(item => `<li>Slide ${{String(item.slide_number).padStart(2, '0')}} · ${{item.visual_type}} · ${{(item.recommended_asset_collections || []).join(', ') || 'no preset'}}</li>`).join('')}}</ul>
          </div>
        `);
      }}
      if (packet.asset_strategy) {{
        cards.push(`
          <div class="insight-card">
            <h3>Asset strategy</h3>
            <ul>
              <li>Visual language: ${{packet.asset_strategy.visual_language || 'n/a'}}</li>
              <li>Cover asset collection: ${{packet.asset_strategy.cover_asset_collection || 'n/a'}}</li>
              <li>Placeholder style: ${{packet.asset_strategy.placeholder_style || 'n/a'}}</li>
            </ul>
          </div>
        `);
      }}
      if (generationResult) {{
        const summaryBullets = (generationAnalysis.executive_summary_bullets || []).slice(0, 3);
        const fallbackUsed = generationAnalysis.fallback_used === true;
        cards.push(`
          <div class="insight-card">
            <h3>AI generation</h3>
            <ul>
              <li>Provider: ${{generationResult.provider || result.provider || 'n/a'}}</li>
              <li>Backend model: ${{(generationAnalysis.resolved_model || 'n/a')}}</li>
              <li>Theme: ${{generationResult.theme || result.theme || 'n/a'}}</li>
              <li>Slides: ${{generationResult.slide_count ?? result.slide_count ?? 0}}</li>
              <li>Fallback used: ${{fallbackUsed ? 'yes' : 'no'}}</li>
              <li>Image suggestions: ${{(generationAnalysis.image_suggestions || []).length}}</li>
            </ul>
          </div>
        `);
        if (fallbackUsed && generationAnalysis.fallback_reason) {{
          cards.push(`
            <div class="insight-card">
              <h3>Fallback reason</h3>
              <ul><li>${{escapeHtml(generationAnalysis.fallback_reason)}}</li></ul>
            </div>
          `);
        }}
        if (summaryBullets.length) {{
          cards.push(`
            <div class="insight-card">
              <h3>Executive summary bullets</h3>
              <ul>${{summaryBullets.map(item => `<li>${{item}}</li>`).join('')}}</ul>
            </div>
          `);
        }}
        if (aiExchange) {{
          cards.push(`
            <div class="insight-card">
              <h3>AI request / response</h3>
              <ul>
                <li>Transport: ${{escapeHtml(aiExchange.transport || 'n/a')}}</li>
                <li>Target URL: ${{escapeHtml(aiExchange.target_url || 'n/a')}}</li>
                <li>Prompt chars: ${{String((aiExchange.prompt || '').length)}}</li>
                <li>Raw response chars: ${{String((aiExchange.raw_response || '').length)}}</li>
              </ul>
            </div>
          `);
          cards.push(renderJsonCard('AI request payload', aiExchange.request_payload, 'Show request JSON'));
          cards.push(renderCodeCard('Prompt sent to AI', aiExchange.prompt || '', 'Show prompt'));
          cards.push(renderCodeCard('Raw AI response', aiExchange.raw_response || '', 'Show raw response'));
          cards.push(renderJsonCard('AI response envelope', aiExchange.response_payload, 'Show response JSON'));
        }}
      }}

      if (guidance.length) {{
        cards.push(`
          <div class="insight-card">
            <h3>Regression guidance</h3>
            <ul>${{guidance.map(item => `<li>${{item}}</li>`).join('')}}</ul>
          </div>
        `);
      }}
      if (topRegressions.length) {{
        cards.push(`
          <div class="insight-card">
            <h3>Top regressions</h3>
            <ul>${{topRegressions.map(item => `<li>Slide ${{String(item.slide_number).padStart(2, '0')}} • score ${{item.diff_score}}</li>`).join('')}}</ul>
          </div>
        `);
      }}
      if (regression && (regression.added_slide_numbers?.length || regression.removed_slide_numbers?.length)) {{
        cards.push(`
          <div class="insight-card">
            <h3>Slide set changes</h3>
            <ul>
              <li>Added: ${{(regression.added_slide_numbers || []).join(', ') || 'none'}}</li>
              <li>Removed: ${{(regression.removed_slide_numbers || []).join(', ') || 'none'}}</li>
            </ul>
          </div>
        `);
      }}

      container.innerHTML = cards.join('');
    }}

    function renderErrorInsights(errorPayload) {{
      const container = document.getElementById('insights');
      container.innerHTML = '';
      const rawError = errorPayload && errorPayload.error ? errorPayload.error : errorPayload;
      const messages = Array.isArray(rawError)
        ? rawError.map(item => `${{(item.loc || []).join('.') || 'input'}}: ${{item.msg || 'validation error'}}`)
        : [typeof rawError === 'string' ? rawError : JSON.stringify(rawError)];
      container.innerHTML = `
        <div class="insight-card">
          <h3>Actionable errors</h3>
          <ul>${{messages.map(item => `<li>${{item}}</li>`).join('')}}</ul>
        </div>
      `;
    }}

    function setAiActionStatus(message, tone = 'info') {{
      const node = document.getElementById('aiActionStatus');
      if (!node) return;
      node.textContent = message;
      node.style.color = tone === 'error' ? '#a94442' : tone === 'success' ? '#2f6b3b' : '#44576d';
      setStatus(message);
    }}

    function setAiButtonsDisabled(disabled) {{
      for (const id of ['aiLoadBriefingButton', 'aiRefreshStatusButton', 'aiGenerateButton', 'aiGenerateRenderButton']) {{
        const node = document.getElementById(id);
        if (node) node.disabled = disabled;
      }}
    }}

    function buildAiQueryParams(includeModelName = true) {{
      const params = new URLSearchParams();
      const providerName = document.getElementById('aiProvider')?.value || 'local_service';
      params.set('provider_name', providerName);
      const baseUrl = String(document.getElementById('aiBaseUrl')?.value || '').trim();
      if (baseUrl) params.set('base_url', baseUrl);
      if (includeModelName) {{
        const modelName = String(document.getElementById('aiModelName')?.value || '').trim();
        if (modelName) params.set('model_name', modelName);
      }}
      const generationAttempts = String(document.getElementById('aiGenerationAttempts')?.value || '').trim();
      if (generationAttempts) params.set('generation_attempts', generationAttempts);
      return params;
    }}

    function renderAiRuntimeStatus(payload) {{
      const node = document.getElementById('aiRuntimeStatus');
      if (!node) return;
      const result = payload || {{}};
      const selectedProvider = result.selected_provider || 'local_service';
      const providerStatus = result.provider_status || result.local_service || {{}};
      const providerMeta = aiProviderMetadata[selectedProvider] || {{}};
      const health = providerStatus.health_payload || {{}};
      const service = health.service || {{}};
      const registry = health.registry || {{}};
      const providerSource = providerStatus.provider_source === 'environment' ? 'env' : 'app default';
      const modelSource = providerStatus.model_source === 'environment' ? 'env' : providerStatus.model_source || 'app default';
      const healthError = providerStatus.health_error ? `<li>Error: ${{escapeHtml(providerStatus.health_error)}}</li>` : '';
      const models = Array.isArray(providerStatus.models) ? providerStatus.models : [];
      const visibleModels = models
        .map(item => escapeHtml(item.name || item.model || ''))
        .filter(Boolean)
        .slice(0, 6);
      const supportsModelListing = providerStatus.supports_model_listing === true || providerMeta.supports_model_listing === true;
      const modelsSummary = supportsModelListing
        ? `<li>Available models: ${{visibleModels.length ? visibleModels.join(', ') : 'none detected'}}</li>`
        : '';
      node.innerHTML = `
        <h3>AI runtime status</h3>
        <ul>
          <li>Selected provider: ${{escapeHtml(selectedProvider)}}</li>
          <li>Service URL: ${{escapeHtml(providerStatus.service_url || 'n/a')}}</li>
          <li>Request provider: ${{escapeHtml(providerStatus.provider_name || 'n/a')}} <strong>(${{escapeHtml(providerSource)}})</strong></li>
          <li>Request model: ${{escapeHtml(providerStatus.model_name || 'n/a')}} <strong>(${{escapeHtml(modelSource)}})</strong></li>
          <li>Timeout: ${{escapeHtml(providerStatus.timeout_seconds ?? 'n/a')}}s</li>
          <li>Retries: ${{escapeHtml(providerStatus.retry_attempts ?? 'n/a')}} (backoff ${{escapeHtml(providerStatus.retry_backoff_seconds ?? 'n/a')}}s)</li>
          <li>Health: ${{escapeHtml(providerStatus.health_status || 'unknown')}}</li>
          ${{healthError}}
          <li>Model listing: ${{supportsModelListing ? 'supported' : 'not supported'}}</li>
          ${{modelsSummary}}
          <li>Service default provider: ${{escapeHtml(service.default_provider || 'n/a')}}</li>
          <li>Service default model: ${{escapeHtml(service.default_model || 'n/a')}}</li>
          <li>Registry default provider: ${{escapeHtml(registry.default_provider || 'n/a')}}</li>
          <li>Registry default model: ${{escapeHtml(registry.default_model || 'n/a')}}</li>
        </ul>
      `;
    }}

    async function refreshAiModelOptions(preferredModelName = undefined) {{
      const optionsNode = document.getElementById('aiModelOptions');
      const modelInput = document.getElementById('aiModelName');
      const providerName = document.getElementById('aiProvider')?.value || 'local_service';
      const providerMeta = aiProviderMetadata[providerName] || {{}};
      if (!optionsNode || !modelInput) return null;
      optionsNode.innerHTML = '';
      if (!providerMeta.supports_model_listing) {{
        modelInput.placeholder = 'optional override, type a model if needed';
        return null;
      }}
      try {{
        const response = await fetch(`/ai/models?${{buildAiQueryParams(false).toString()}}`);
        const data = await response.json();
        if (!response.ok) {{
          modelInput.placeholder = 'could not load models automatically';
          return null;
        }}
        const result = data.result || data;
        const models = Array.isArray(result.models) ? result.models : [];
        for (const model of models) {{
          const option = document.createElement('option');
          option.value = model.name || model.model || '';
          optionsNode.appendChild(option);
        }}
        modelInput.placeholder = models.length
          ? 'select one of the available local models or type one manually'
          : 'no local models detected';
        if (!String(modelInput.value || '').trim() && preferredModelName) {{
          modelInput.value = preferredModelName;
        }}
        return result;
      }} catch (_error) {{
        modelInput.placeholder = 'could not load models automatically';
        return null;
      }}
    }}

    async function refreshAiStatus(showReadyMessage = true) {{
      const providerName = document.getElementById('aiProvider')?.value || 'local_service';
      try {{
        const response = await fetch(`/ai/status?${{buildAiQueryParams().toString()}}`);
        const data = await response.json();
        if (!response.ok) {{
          renderAiRuntimeStatus({{
            selected_provider: providerName,
            provider_status: {{ health_status: 'error', health_error: data.error || 'status request failed' }},
          }});
          setAiActionStatus(`AI status refresh failed (${{response.status}}).`, 'error');
          return null;
        }}
        const result = data.result || data;
        renderAiRuntimeStatus(result);
        await refreshAiModelOptions(result.provider_status && result.provider_status.model_name ? String(result.provider_status.model_name) : undefined);
        if (showReadyMessage) {{
          const healthStatus = (result.provider_status || result.local_service || {{}}).health_status || 'unknown';
          setAiActionStatus(
            `AI status refreshed for ${{result.selected_provider || providerName}}: ${{healthStatus}}.`,
            healthStatus === 'ok' ? 'success' : 'info',
          );
        }}
        return result;
      }} catch (error) {{
        renderAiRuntimeStatus({{
          selected_provider: providerName,
          provider_status: {{ health_status: 'error', health_error: String(error) }},
        }});
        setAiActionStatus(`AI status refresh failed: ${{error}}`, 'error');
        return null;
      }}
    }}

    function escapeHtml(value) {{
      return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }}

    function renderCodeCard(title, content, summary = 'Open details') {{
      const normalized = String(content ?? '').trim();
      return `
        <div class="insight-card">
          <h3>${{escapeHtml(title)}}</h3>
          <details>
            <summary>${{escapeHtml(summary)}}</summary>
            <pre>${{escapeHtml(normalized || 'n/a')}}</pre>
          </details>
        </div>
      `;
    }}

    function renderJsonCard(title, value, summary = 'Open JSON') {{
      let serialized = 'n/a';
      try {{
        serialized = value === undefined || value === null ? 'n/a' : JSON.stringify(value, null, 2);
      }} catch (_error) {{
        serialized = String(value ?? 'n/a');
      }}
      return renderCodeCard(title, serialized, summary);
    }}

    function optionalText(value) {{
      const normalized = String(value || '').trim();
      return normalized || undefined;
    }}

    function optionalUnitFloat(value) {{
      const normalized = String(value || '').trim();
      if (!normalized) return undefined;
      const parsed = Number.parseFloat(normalized);
      if (!Number.isFinite(parsed)) return undefined;
      return Math.max(0, Math.min(1, parsed));
    }}

    function splitDelimitedLine(line) {{
      return line.split('|').map(part => part.trim());
    }}

    function deriveTitleFromIntent(intentText) {{
      const lines = String(intentText || '').split(/\\n+/).map(line => line.trim()).filter(Boolean);
      const seed = (lines[0] || 'Intent-driven presentation').replace(/^[-*•\\d\\.\\)\\s]+/, '').trim();
      const words = seed.split(/\\s+/).filter(Boolean).slice(0, 8);
      const title = words.join(' ').replace(/[\.:;,-]+$/, '').trim();
      if (!title) return 'Intent-driven presentation';
      return title.charAt(0).toUpperCase() + title.slice(1);
    }}

    function refreshSlideEditor() {{
      const selector = document.getElementById('slideSelector');
      const fields = document.getElementById('slideFields');
      const badge = document.getElementById('slideTypeBadge');
      let spec;
      try {{
        spec = JSON.parse(document.getElementById('spec').value);
      }} catch (_error) {{
        selector.innerHTML = '';
        badge.value = 'Invalid JSON';
        fields.innerHTML = `<div class="editor-card"><h3>Guided editor unavailable</h3><div class="editor-hint">Fix the JSON first to enable guided editing.</div></div>`;
        return;
      }}

      const slides = Array.isArray(spec.slides) ? spec.slides : [];
      const previousValue = selector.value;
      selector.innerHTML = '';
      slides.forEach((slide, index) => {{
        const option = document.createElement('option');
        option.value = String(index);
        option.textContent = `${{String(index + 1).padStart(2, '0')}} · ${{slide.type || 'slide'}} · ${{slide.title || 'Untitled slide'}}`;
        selector.appendChild(option);
      }});

      if (!slides.length) {{
        badge.value = 'No slides in current spec';
        fields.innerHTML = `<div class="editor-card"><h3>No slides</h3><div class="editor-hint">Load a template or add slides in JSON mode first.</div></div>`;
        return;
      }}

      const selectedIndex = Number.isNaN(Number.parseInt(previousValue, 10))
        ? 0
        : Math.min(slides.length - 1, Math.max(0, Number.parseInt(previousValue, 10)));
      selector.value = String(selectedIndex);
      renderSelectedSlideEditor();
    }}

    function renderSelectedSlideEditor() {{
      const selector = document.getElementById('slideSelector');
      const fields = document.getElementById('slideFields');
      const badge = document.getElementById('slideTypeBadge');
      let spec;
      try {{
        spec = JSON.parse(document.getElementById('spec').value);
      }} catch (_error) {{
        return;
      }}
      const slides = Array.isArray(spec.slides) ? spec.slides : [];
      const index = Math.max(0, Math.min(slides.length - 1, Number.parseInt(selector.value || '0', 10)));
      const slide = slides[index] || {{}};
      badge.value = `Slide ${{String(index + 1).padStart(2, '0')}} · ${{slide.type || 'slide'}}`;

      const cards = [];
      cards.push(`
        <div class="editor-card">
          <h3>Core fields</h3>
          <label>Title</label>
          <input id="guidedTitle" value="${{escapeHtml(slide.title || '')}}" />
          <label>Subtitle</label>
          <input id="guidedSubtitle" value="${{escapeHtml(slide.subtitle || '')}}" />
          <label>Eyebrow</label>
          <input id="guidedEyebrow" value="${{escapeHtml(slide.eyebrow || '')}}" />
          <label>Body</label>
          <textarea id="guidedBody">${{escapeHtml(slide.body || '')}}</textarea>
        </div>
      `);

      const supportsImageFields = ['title', 'section', 'image_text', 'summary', 'closing'].includes(slide.type);
      if (supportsImageFields) {{
        cards.push(`
          <div class="editor-card">
            <h3>Visual slot</h3>
            <label>Image asset path</label>
            <input id="guidedImagePath" value="${{escapeHtml(slide.image_path || '')}}" />
            <label>Image caption</label>
            <input id="guidedImageCaption" value="${{escapeHtml(slide.image_caption || '')}}" />
            <label>Focal point X</label>
            <input id="guidedImageFocalX" value="${{escapeHtml(slide.image_focal_x ?? '')}}" placeholder="0.0 - 1.0" />
            <label>Focal point Y</label>
            <input id="guidedImageFocalY" value="${{escapeHtml(slide.image_focal_y ?? '')}}" placeholder="0.0 - 1.0" />
            <div class="editor-hint">Use focal values between 0 and 1 to bias cropping around the subject.</div>
          </div>
        `);
      }}

      if (Array.isArray(slide.bullets)) {{
        cards.push(`
          <div class="editor-card">
            <h3>Bullets</h3>
            <textarea id="guidedBullets">${{escapeHtml((slide.bullets || []).join('{js_newline}'))}}</textarea>
            <div class="editor-hint">One bullet per line.</div>
          </div>
        `);
      }}

      if (Array.isArray(slide.metrics) && slide.metrics.length) {{
        cards.push(`
          <div class="editor-card">
            <h3>Metrics</h3>
            <textarea id="guidedMetrics">${{escapeHtml(slide.metrics.map(item => [item.value || '', item.label || '', item.detail || '', item.trend || ''].join(' | ')).join('{js_newline}'))}}</textarea>
            <div class="editor-hint">Each line: value | label | detail | trend</div>
          </div>
        `);
      }}

      if (Array.isArray(slide.comparison_columns) && slide.comparison_columns.length) {{
        cards.push(`
          <div class="editor-card">
            <h3>Comparison columns</h3>
            <textarea id="guidedComparisonColumns">${{escapeHtml(slide.comparison_columns.map(item => [item.title || '', item.body || '', (item.bullets || []).join('; '), item.footer || '', item.tag || ''].join(' | ')).join('{js_newline}'))}}</textarea>
            <div class="editor-hint">Each line: title | body | bullet1; bullet2 | footer | tag</div>
          </div>
        `);
      }}

      if (Array.isArray(slide.two_column_columns) && slide.two_column_columns.length) {{
        cards.push(`
          <div class="editor-card">
            <h3>Two-column panels</h3>
            <textarea id="guidedTwoColumnColumns">${{escapeHtml(slide.two_column_columns.map(item => [item.title || '', item.body || '', (item.bullets || []).join('; '), item.footer || '', item.tag || ''].join(' | ')).join('{js_newline}'))}}</textarea>
            <div class="editor-hint">Each line: title | body | bullet1; bullet2 | footer | tag</div>
          </div>
        `);
      }}

      if (Array.isArray(slide.cards) && slide.cards.length) {{
        cards.push(`
          <div class="editor-card">
            <h3>Cards</h3>
            <textarea id="guidedCards">${{escapeHtml(slide.cards.map(item => [item.title || '', item.body || '', item.footer || ''].join(' | ')).join('{js_newline}'))}}</textarea>
            <div class="editor-hint">Each line: title | body | footer</div>
          </div>
        `);
      }}

      if (Array.isArray(slide.table_columns) && Array.isArray(slide.table_rows) && slide.table_columns.length) {{
        cards.push(`
          <div class="editor-card">
            <h3>Table</h3>
            <label>Columns</label>
            <input id="guidedTableColumns" value="${{escapeHtml((slide.table_columns || []).join(', '))}}" />
            <label>Rows</label>
            <textarea id="guidedTableRows">${{escapeHtml((slide.table_rows || []).map(row => row.join(' | ')).join('{js_newline}'))}}</textarea>
            <div class="editor-hint">Rows use: column1 | column2 | column3</div>
          </div>
        `);
      }}

      if (Array.isArray(slide.faq_items) && slide.faq_items.length) {{
        cards.push(`
          <div class="editor-card">
            <h3>FAQ items</h3>
            <textarea id="guidedFaqItems">${{escapeHtml(slide.faq_items.map(item => [item.title || '', item.body || ''].join(' | ')).join('{js_newline}'))}}</textarea>
            <div class="editor-hint">Each line: question | answer</div>
          </div>
        `);
      }}

      if (Array.isArray(slide.timeline_items) && slide.timeline_items.length) {{
        cards.push(`
          <div class="editor-card">
            <h3>Timeline items</h3>
            <textarea id="guidedTimelineItems">${{escapeHtml(slide.timeline_items.map(item => [item.title || '', item.body || '', item.tag || '', item.footer || ''].join(' | ')).join('{js_newline}'))}}</textarea>
            <div class="editor-hint">Each line: title | body | tag | footer</div>
          </div>
        `);
      }}

      fields.innerHTML = cards.join('');
    }}

    function applyGuidedEdits() {{
      let spec;
      try {{
        spec = JSON.parse(document.getElementById('spec').value);
      }} catch (error) {{
        renderErrorInsights({{ error: `Invalid JSON syntax: ${{error.message}}` }});
        setStatus('Cannot apply guided edits until JSON is valid.');
        return;
      }}
      const selector = document.getElementById('slideSelector');
      const slides = Array.isArray(spec.slides) ? spec.slides : [];
      if (!slides.length) return;
      const index = Math.max(0, Math.min(slides.length - 1, Number.parseInt(selector.value || '0', 10)));
      const slide = slides[index];

      slide.title = optionalText(document.getElementById('guidedTitle')?.value);
      slide.subtitle = optionalText(document.getElementById('guidedSubtitle')?.value);
      slide.eyebrow = optionalText(document.getElementById('guidedEyebrow')?.value);
      slide.body = optionalText(document.getElementById('guidedBody')?.value);
      if (document.getElementById('guidedImagePath')) slide.image_path = optionalText(document.getElementById('guidedImagePath')?.value);
      if (document.getElementById('guidedImageCaption')) slide.image_caption = optionalText(document.getElementById('guidedImageCaption')?.value);
      if (document.getElementById('guidedImageFocalX')) slide.image_focal_x = optionalUnitFloat(document.getElementById('guidedImageFocalX')?.value);
      if (document.getElementById('guidedImageFocalY')) slide.image_focal_y = optionalUnitFloat(document.getElementById('guidedImageFocalY')?.value);

      const bulletsField = document.getElementById('guidedBullets');
      if (bulletsField) {{
        slide.bullets = bulletsField.value.split(/{js_newline_pattern}/).map(item => item.trim()).filter(Boolean);
      }}

      const metricsField = document.getElementById('guidedMetrics');
      if (metricsField) {{
        slide.metrics = metricsField.value.split(/{js_newline_pattern}/).map(line => splitDelimitedLine(line)).filter(parts => parts.some(Boolean)).map(parts => {{
          const [value, label, detail, trend] = parts;
          return {{
            value: value || '',
            label: label || '',
            ...(detail ? {{ detail }} : {{}}),
            ...(trend ? {{ trend }} : {{}}),
          }};
        }});
      }}

      const comparisonField = document.getElementById('guidedComparisonColumns');
      if (comparisonField) {{
        slide.comparison_columns = comparisonField.value.split(/{js_newline_pattern}/).map(line => splitDelimitedLine(line)).filter(parts => parts.some(Boolean)).map(parts => {{
          const [title, body, bullets, footer, tag] = parts;
          return {{
            title: title || 'Column',
            ...(body ? {{ body }} : {{}}),
            ...(bullets ? {{ bullets: bullets.split(';').map(item => item.trim()).filter(Boolean) }} : {{ bullets: [] }}),
            ...(footer ? {{ footer }} : {{}}),
            ...(tag ? {{ tag }} : {{}}),
          }};
        }});
      }}

      const twoColumnField = document.getElementById('guidedTwoColumnColumns');
      if (twoColumnField) {{
        slide.two_column_columns = twoColumnField.value.split(/{js_newline_pattern}/).map(line => splitDelimitedLine(line)).filter(parts => parts.some(Boolean)).map(parts => {{
          const [title, body, bullets, footer, tag] = parts;
          return {{
            title: title || 'Column',
            ...(body ? {{ body }} : {{}}),
            ...(bullets ? {{ bullets: bullets.split(';').map(item => item.trim()).filter(Boolean) }} : {{ bullets: [] }}),
            ...(footer ? {{ footer }} : {{}}),
            ...(tag ? {{ tag }} : {{}}),
          }};
        }});
      }}

      const cardsField = document.getElementById('guidedCards');
      if (cardsField) {{
        slide.cards = cardsField.value.split(/{js_newline_pattern}/).map(line => splitDelimitedLine(line)).filter(parts => parts.some(Boolean)).map(parts => {{
          const [title, body, footer] = parts;
          return {{
            title: title || 'Card',
            ...(body ? {{ body }} : {{ body: '' }}),
            ...(footer ? {{ footer }} : {{}}),
          }};
        }});
      }}

      const tableColumnsField = document.getElementById('guidedTableColumns');
      const tableRowsField = document.getElementById('guidedTableRows');
      if (tableColumnsField && tableRowsField) {{
        slide.table_columns = tableColumnsField.value.split(',').map(item => item.trim()).filter(Boolean);
        slide.table_rows = tableRowsField.value.split(/{js_newline_pattern}/).map(line => splitDelimitedLine(line)).filter(parts => parts.some(Boolean));
      }}

      const faqField = document.getElementById('guidedFaqItems');
      if (faqField) {{
        slide.faq_items = faqField.value.split(/{js_newline_pattern}/).map(line => splitDelimitedLine(line)).filter(parts => parts.some(Boolean)).map(parts => {{
          const [title, body] = parts;
          return {{ title: title || 'Question', body: body || '' }};
        }});
      }}

      const timelineField = document.getElementById('guidedTimelineItems');
      if (timelineField) {{
        slide.timeline_items = timelineField.value.split(/{js_newline_pattern}/).map(line => splitDelimitedLine(line)).filter(parts => parts.some(Boolean)).map(parts => {{
          const [title, body, tag, footer] = parts;
          return {{
            title: title || 'Step',
            ...(body ? {{ body }} : {{ body: '' }}),
            ...(tag ? {{ tag }} : {{}}),
            ...(footer ? {{ footer }} : {{}}),
          }};
        }});
      }}

      document.getElementById('spec').value = JSON.stringify(spec, null, 2);
      persistState();
      refreshSlideEditor();
      scheduleAutoRun();
      focusEditor();
      focusTopRiskSlide();
      setStatus('Guided edits applied to JSON spec.');
    }}

    async function exportCurrentDeck() {{
      setStatus('Exporting current deck...');
      const ok = await runAction('/render');
      if (ok) setStatus('Deck exported and latest artifacts refreshed.');
      return ok;
    }}

    async function runIterateFlow() {{
      setStatus('Running iterate flow...');
      const reviewed = await runAction('/review');
      if (!reviewed) return false;
      focusTopRiskSlide();
      const rendered = await runAction('/render');
      if (!rendered) return false;
      if (document.getElementById('previewDir').value.trim()) {{
        const reviewedRendered = await reviewRenderedPptx();
        if (!reviewedRendered) return false;
      }}
      setStatus('Iterate flow complete. Review artifacts, adjust risky slides, and export when ready.');
      return true;
    }}

    function parseBriefingInput() {{
      const useIntentMode = document.getElementById('aiUseIntentMode').checked;
      const intentText = document.getElementById('intentInput').value.trim();
      const authoringMode = document.getElementById('aiAuthoringMode').value || 'ai_first';
      if (useIntentMode && intentText) {{
        return {{ mode: 'intent', intent_text: intentText, authoring_mode: authoringMode }};
      }}

      const raw = document.getElementById('briefingInput').value;
      try {{
        const briefing = JSON.parse(raw);
        if (!briefing || Array.isArray(briefing) || typeof briefing !== 'object') {{
          throw new Error('briefing must be a JSON object');
        }}
        return {{ mode: 'briefing', briefing }};
      }} catch (error) {{
        renderErrorInsights({{ error: `Invalid AI briefing JSON: ${{error.message}}` }});
        setStatus('AI briefing JSON error.');
        throw error;
      }}
    }}

    function loadBriefingExample() {{
      const field = document.getElementById('briefingInput');
      field.value = field.defaultValue;
      document.getElementById('aiUseIntentMode').checked = false;
      persistState();
      setAiActionStatus('Briefing example loaded. Structured briefing mode enabled.', 'success');
    }}

    async function generateFromBriefing() {{
      setAiButtonsDisabled(true);
      let aiInput;
      try {{
        aiInput = parseBriefingInput();
      }} catch (_error) {{
        setAiButtonsDisabled(false);
        return;
      }}
      const providerName = document.getElementById('aiProvider').value || 'heuristic';
      const themeName = document.getElementById('aiThemeName').value || undefined;
      const aiBaseUrl = document.getElementById('aiBaseUrl').value || undefined;
      const aiModelName = document.getElementById('aiModelName').value || undefined;
      const aiGenerationAttempts = Number.parseInt(document.getElementById('aiGenerationAttempts').value || '3', 10) || 3;
      const inputLabel = aiInput.mode === 'intent'
        ? `freeform intent (${{aiInput.authoring_mode === 'hybrid' ? 'hybrid' : 'AI-first'}})`
        : 'structured briefing';
      setAiActionStatus(`Generating AI deck from ${{inputLabel}} with provider ${{providerName}}...`, 'info');
      const response = await executeAction('/generate', {{
        base_url: aiBaseUrl,
        model_name: aiModelName,
        generation_attempts: aiGenerationAttempts,
        ...(aiInput.mode === 'intent' ? {{ intent_text: aiInput.intent_text, authoring_mode: aiInput.authoring_mode }} : {{ briefing: aiInput.briefing }}),
        provider_name: providerName,
        theme_name: themeName,
      }});
      document.getElementById('result').textContent = JSON.stringify(response.data, null, 2);
      if (!response.ok) {{
        renderPreviewGallery([]);
        updateArtifactLinks({{}});
        renderErrorInsights(response.data);
        await refreshAiStatus(false);
        setAiActionStatus(`AI generation failed (${{response.status}}).`, 'error');
        setAiButtonsDisabled(false);
        return;
      }}
      const result = response.data.result || response.data;
      document.getElementById('spec').value = JSON.stringify(result.payload, null, 2);
      refreshSlideEditor();
      renderPreviewGallery([]);
      updateArtifactLinks({{}});
      renderInsights(result);
      persistState();
      await refreshAiStatus(false);
      if (document.getElementById('aiAutoRender').checked) {{
        await runAction('/render', {{ generationResult: result }});
        setAiActionStatus(`AI deck generated and rendered with provider ${{result.provider}}.`, 'success');
      }} else if (document.getElementById('aiAutoPreview').checked) {{
        await runAction('/review', {{ generationResult: result }});
        setAiActionStatus(`AI deck generated and reviewed with provider ${{result.provider}}.`, 'success');
      }} else {{
        scheduleAutoRun();
        setAiActionStatus(`AI deck generated with provider ${{result.provider}}.`, 'success');
      }}
      setAiButtonsDisabled(false);
    }}

    async function generateAndRenderFromBriefing() {{
      setAiButtonsDisabled(true);
      let aiInput;
      try {{
        aiInput = parseBriefingInput();
      }} catch (_error) {{
        setAiButtonsDisabled(false);
        return;
      }}
      const providerName = document.getElementById('aiProvider').value || 'heuristic';
      const themeName = document.getElementById('aiThemeName').value || undefined;
      const outputPath = document.getElementById('outputPath').value;
      const previewDir = document.getElementById('previewDir').value;
      const previewBackend = document.getElementById('previewBackend').value;
      const baselineDir = document.getElementById('baselineDir').value;
      const requireRealPreviews = document.getElementById('requireRealPreviews').checked;
      const failOnRegression = document.getElementById('failOnRegression').checked;
      const aiBaseUrl = document.getElementById('aiBaseUrl').value || undefined;
      const aiModelName = document.getElementById('aiModelName').value || undefined;
      const aiGenerationAttempts = Number.parseInt(document.getElementById('aiGenerationAttempts').value || '3', 10) || 3;
      const inputLabel = aiInput.mode === 'intent'
        ? `freeform intent (${{aiInput.authoring_mode === 'hybrid' ? 'hybrid' : 'AI-first'}})`
        : 'structured briefing';
      setAiActionStatus(`Generating and rendering AI deck from ${{inputLabel}} with provider ${{providerName}}...`, 'info');
      const response = await executeAction('/generate-and-render', {{
        ...(aiInput.mode === 'intent' ? {{ intent_text: aiInput.intent_text, authoring_mode: aiInput.authoring_mode }} : {{ briefing: aiInput.briefing }}),
        provider_name: providerName,
        theme_name: themeName,
        output_path: outputPath,
        include_review: true,
        preview_output_dir: previewDir,
        preview_backend: previewBackend,
        preview_baseline_dir: baselineDir || undefined,
        preview_require_real: requireRealPreviews,
        preview_fail_on_regression: failOnRegression,
        base_url: aiBaseUrl,
        model_name: aiModelName,
        generation_attempts: aiGenerationAttempts,
      }});
      document.getElementById('result').textContent = JSON.stringify(response.data, null, 2);
      if (!response.ok) {{
        renderPreviewGallery([]);
        updateArtifactLinks({{}});
        renderErrorInsights(response.data);
        await refreshAiStatus(false);
        setAiActionStatus(`AI generate+render failed (${{response.status}}).`, 'error');
        setAiButtonsDisabled(false);
        return;
      }}
      const result = response.data.result || response.data;
      const generation = result.generation || {{}};
      const render = result.render || {{}};
      if (generation.payload) {{
        document.getElementById('spec').value = JSON.stringify(generation.payload, null, 2);
        refreshSlideEditor();
      }}
      const previewPayload = render.preview_result || render;
      renderPreviewGallery(previewPayload.previews || []);
      updateArtifactLinks(render);
      renderInsights({{ ...render, generation, mode: 'generate-and-render' }});
      persistState();
      await refreshAiStatus(false);
      setAiActionStatus(`AI deck generated and rendered with provider ${{generation.provider || providerName}}.`, 'success');
      setAiButtonsDisabled(false);
    }}

    async function executeAction(path, payload) {{
      const response = await fetch(path, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(payload),
      }});
      const data = await response.json();
      return {{ ok: response.ok, status: response.status, data }};
    }}

    function attachGenerationContextToActionData(data, generationResult) {{
      const baseResult = (data && typeof data === 'object' && data.result) ? data.result : data;
      if (!generationResult || !baseResult || typeof baseResult !== 'object') {{
        return {{
          data,
          result: baseResult,
        }};
      }}

      const mergedResult = {{ ...baseResult, generation: generationResult }};
      if (data && typeof data === 'object' && Object.prototype.hasOwnProperty.call(data, 'result')) {{
        return {{
          data: {{ ...data, result: mergedResult }},
          result: mergedResult,
        }};
      }}

      return {{
        data: mergedResult,
        result: mergedResult,
      }};
    }}

    function scheduleAutoRun() {{
      if (autoRunHandle) clearTimeout(autoRunHandle);
      autoRunHandle = setTimeout(() => autoRun(), 700);
    }}

    async function autoRun() {{
      const autoValidate = document.getElementById('autoValidate').checked;
      const autoReview = document.getElementById('autoReview').checked;
      if (!autoValidate && !autoReview) return;

      const sequence = ++autoRunSequence;
      setStatus('Checking changes...');
      let spec;
      try {{
        spec = JSON.parse(document.getElementById('spec').value);
      }} catch (error) {{
        renderErrorInsights({{ error: `Invalid JSON syntax: ${{error.message}}` }});
        document.getElementById('result').textContent = `Invalid JSON syntax: ${{error.message}}`;
        setStatus('JSON syntax error.');
        return;
      }}

      const previewDir = document.getElementById('previewDir').value;
      const previewBackend = document.getElementById('previewBackend').value;
      const baselineDir = document.getElementById('baselineDir').value;
      const requireRealPreviews = document.getElementById('requireRealPreviews').checked;
      const failOnRegression = document.getElementById('failOnRegression').checked;
      const includePreview = document.getElementById('autoPreviewWithReview').checked;

      const path = autoReview ? '/review' : '/validate';
      const payload = {{ spec }};
      if (autoReview && includePreview) {{
        payload.preview_output_dir = previewDir;
        payload.preview_backend = previewBackend;
        payload.preview_baseline_dir = baselineDir || undefined;
        payload.preview_require_real = requireRealPreviews;
        payload.preview_fail_on_regression = failOnRegression;
      }}

      const response = await executeAction(path, payload);
      if (sequence !== autoRunSequence) return;
      document.getElementById('result').textContent = JSON.stringify(response.data, null, 2);

      if (!response.ok) {{
        renderPreviewGallery([]);
        updateArtifactLinks({{}});
        renderErrorInsights(response.data);
        setStatus(`Auto check failed (${{response.status}}).`);
        return;
      }}

      const result = response.data.result || response.data;
      const previewPayload = result.preview_result || result;
      renderPreviewGallery(previewPayload.previews || []);
      updateArtifactLinks(result);
      renderInsights(result);
      const topRiskSlides = (result.top_risk_slides || []).slice(0, 1);
      if (autoReview && topRiskSlides.length) {{
        const focusSlideNumber = String(topRiskSlides[0].slide_number || '').padStart(2, '0');
        setStatus(`Auto review up to date. Start with slide ${{focusSlideNumber}}.`);
      }} else {{
        setStatus(autoReview ? 'Auto review up to date.' : 'Auto validation up to date.');
      }}
      syncLiveReviewSummary();
    }}

    async function initControls() {{
      const templates = await fetch('/templates').then(r => r.json());
      const brandPacks = await fetch('/brand-packs').then(r => r.json());
      const profiles = await fetch('/profiles').then(r => r.json());
      const workflows = await fetch('/workflows').then(r => r.json());
      const aiProviders = await fetch('/ai/providers').then(r => r.json());
      aiProviderMetadata = Object.fromEntries((aiProviders.provider_details || []).map(item => [item.name, item]));
      const workflowSelect = document.getElementById('workflowPreset');
      const domainSelect = document.getElementById('templateDomain');
      const brandPackSelect = document.getElementById('brandPack');
      const profileSelect = document.getElementById('audienceProfile');
      const aiProviderSelect = document.getElementById('aiProvider');
      const workflowNone = document.createElement('option');
      workflowNone.value = '';
      workflowNone.textContent = '(none)';
      workflowSelect.appendChild(workflowNone);
      for (const workflow of workflows.workflows) {{
        const option = document.createElement('option');
        option.value = workflow.name;
        option.textContent = workflow.display_name;
        workflowSelect.appendChild(option);
      }}
      for (const domain of templates.domains) {{
        const option = document.createElement('option');
        option.value = domain;
        option.textContent = domain;
        domainSelect.appendChild(option);
      }}
      const brandPackNone = document.createElement('option');
      brandPackNone.value = '';
      brandPackNone.textContent = '(none)';
      brandPackSelect.appendChild(brandPackNone);
      for (const brandPack of brandPacks.brand_packs) {{
        const option = document.createElement('option');
        option.value = brandPack.name;
        option.textContent = brandPack.display_name;
        brandPackSelect.appendChild(option);
      }}
      const none = document.createElement('option');
      none.value = '';
      none.textContent = '(none)';
      profileSelect.appendChild(none);
      for (const profile of profiles.profiles) {{
        const option = document.createElement('option');
        option.value = profile.display_name.toLowerCase();
        option.textContent = profile.display_name;
        profileSelect.appendChild(option);
      }}
      for (const providerName of aiProviders.providers) {{
        const option = document.createElement('option');
        option.value = providerName;
        option.textContent = providerName;
        aiProviderSelect.appendChild(option);
      }}
      if (!aiProviderSelect.value && aiProviders.providers.length) {{
        aiProviderSelect.value = aiProviders.providers.includes('local_service') ? 'local_service' : aiProviders.providers[0];
      }}
      restoreState();
      document.getElementById('slideSelector').addEventListener('change', renderSelectedSlideEditor);
      document.getElementById('spec').addEventListener('input', refreshSlideEditor);
      document.getElementById('spec').addEventListener('change', refreshSlideEditor);
      document.getElementById('aiProvider').addEventListener('change', async () => {{
        document.getElementById('aiModelName').value = '';
        persistState();
        await refreshAiStatus(true);
      }});
      document.getElementById('aiBaseUrl').addEventListener('change', async () => {{
        persistState();
        await refreshAiStatus(false);
      }});
      document.getElementById('aiModelName').addEventListener('change', async () => {{
        persistState();
        await refreshAiStatus(false);
      }});
      document.getElementById('aiGenerationAttempts').addEventListener('change', async () => {{
        persistState();
        await refreshAiStatus(false);
      }});
      refreshSlideEditor();
      syncLiveReviewSummary();
      await refreshAiStatus(false);
      setAiActionStatus('AI section ready.', 'info');
      for (const id of ['outputPath', 'previewDir', 'workflowPreset', 'templateDomain', 'brandPack', 'audienceProfile', 'previewBackend', 'baselineDir', 'requireRealPreviews', 'failOnRegression', 'compareBeforePptx', 'compareAfterPptx', 'compareOutputDir', 'aiProvider', 'aiBaseUrl', 'aiModelName', 'aiGenerationAttempts', 'aiThemeName', 'aiAuthoringMode', 'aiUseIntentMode', 'aiAutoPreview', 'aiAutoRender', 'intentInput', 'briefingInput', 'spec', 'autoValidate', 'autoReview', 'autoPreviewWithReview']) {{
        const element = document.getElementById(id);
        element.addEventListener('change', persistState);
        element.addEventListener('input', persistState);
        element.addEventListener('change', syncLiveReviewSummary);
        element.addEventListener('input', syncLiveReviewSummary);
        if (id !== 'briefingInput' && id !== 'intentInput' && id !== 'aiProvider' && id !== 'aiBaseUrl' && id !== 'aiModelName' && id !== 'aiGenerationAttempts' && id !== 'aiThemeName' && id !== 'aiAuthoringMode') {{
          element.addEventListener('change', scheduleAutoRun);
          element.addEventListener('input', scheduleAutoRun);
        }}
      }}
      document.addEventListener('keydown', event => {{
        if (!(event.metaKey || event.ctrlKey) || event.repeat) return;
        if (event.key !== 'Enter') return;
        event.preventDefault();
        if (event.shiftKey) exportCurrentDeck();
        else runIterateFlow();
      }});
    }}

    async function loadWorkflow() {{
      const workflowName = document.getElementById('workflowPreset').value;
      const brandPack = document.getElementById('brandPack').value;
      if (!workflowName) return;
      const response = await fetch('/workflow-template', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ workflow_name: workflowName, brand_pack: brandPack || undefined }}),
      }});
      const data = await response.json();
      document.getElementById('spec').value = JSON.stringify(data.packet.template, null, 2);
      document.getElementById('templateDomain').value = data.packet.workflow.domain;
      document.getElementById('brandPack').value = (data.packet.brand_pack && data.packet.brand_pack.name) || '';
      document.getElementById('audienceProfile').value = data.packet.workflow.audience_profile;
      document.getElementById('previewBackend').value = data.packet.workflow.default_preview_backend;
      document.getElementById('outputPath').value = data.packet.workflow.default_output_pptx;
      document.getElementById('previewDir').value = data.packet.workflow.default_preview_dir;
      document.getElementById('baselineDir').value = (data.packet.preview_recommendation && data.packet.preview_recommendation.baseline_dir) || '';
      document.getElementById('requireRealPreviews').checked = Boolean(data.packet.preview_recommendation && data.packet.preview_recommendation.require_real_previews);
      document.getElementById('failOnRegression').checked = Boolean(data.packet.preview_recommendation && data.packet.preview_recommendation.fail_on_regression);
      document.getElementById('result').textContent = JSON.stringify(data, null, 2);
      setStatus(`Workflow loaded: ${{data.packet.workflow.display_name}}`);
      updateArtifactLinks({{}});
      renderInsights({{ packet: data.packet }});
      renderPreviewGallery([]);
      refreshSlideEditor();
      syncLiveReviewSummary();
      persistState();
    }}

    async function loadTemplate() {{
      const domain = document.getElementById('templateDomain').value;
      const brandPack = document.getElementById('brandPack').value;
      const audienceProfile = document.getElementById('audienceProfile').value;
      const response = await fetch('/template', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ domain, brand_pack: brandPack || undefined, audience_profile: audienceProfile || undefined }}),
      }});
      const data = await response.json();
      document.getElementById('spec').value = JSON.stringify(data.template, null, 2);
      document.getElementById('result').textContent = JSON.stringify(data, null, 2);
      setStatus('Starter template loaded.');
      updateArtifactLinks({{}});
      renderInsights({{}});
      renderPreviewGallery([]);
      refreshSlideEditor();
      syncLiveReviewSummary();
      persistState();
    }}

    async function promoteBaseline() {{
      const previewDir = document.getElementById('previewDir').value;
      const baselineDir = document.getElementById('baselineDir').value;
      if (!previewDir || !baselineDir) {{
        setStatus('Preview directory and baseline directory are required to promote a baseline.');
        return false;
      }}
      const response = await fetch('/promote-baseline', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ source_dir: previewDir, baseline_dir: baselineDir }}),
      }});
      const data = await response.json();
      document.getElementById('result').textContent = JSON.stringify(data, null, 2);
      const result = data.result || data;
      updateArtifactLinks(result);
      renderInsights(result);
      setStatus('Baseline promoted.');
      persistState();
      return true;
    }}

    async function comparePptxArtifacts() {{
      const beforePptx = document.getElementById('compareBeforePptx').value;
      const afterPptx = document.getElementById('compareAfterPptx').value;
      const outputDir = document.getElementById('compareOutputDir').value;
      if (!beforePptx || !afterPptx || !outputDir) {{
        setStatus('Before PPTX, after PPTX and compare output directory are required.');
        return false;
      }}
      const response = await executeAction('/compare-pptx', {{
        before_pptx: beforePptx,
        after_pptx: afterPptx,
        output_dir: outputDir,
        write_diff_images: true,
        require_real_previews: document.getElementById('requireRealPreviews').checked,
        fail_on_regression: document.getElementById('failOnRegression').checked,
      }});
      const data = response.data;
      document.getElementById('result').textContent = JSON.stringify(data, null, 2);
      if (!response.ok) {{
        renderPreviewGallery([]);
        updateArtifactLinks({{}});
        renderErrorInsights(data);
        setStatus(`Compare failed (${{response.status}}).`);
        persistState();
        return false;
      }}
      const result = data.result || data;
      renderPreviewGallery([]);
      updateArtifactLinks(result);
      renderInsights(result);
      setStatus('Finished compare-pptx flow.');
      persistState();
      return true;
    }}

    async function reviewRenderedPptx() {{
      const inputPptx = document.getElementById('outputPath').value;
      const outputDir = document.getElementById('previewDir').value;
      if (!inputPptx || !outputDir) {{
        setStatus('Output PPTX path and preview directory are required for review-pptx.');
        return false;
      }}
      const response = await executeAction('/review-pptx', {{
        input_pptx: inputPptx,
        output_dir: outputDir,
        baseline_dir: document.getElementById('baselineDir').value || undefined,
        require_real_previews: document.getElementById('requireRealPreviews').checked,
        fail_on_regression: document.getElementById('failOnRegression').checked,
        write_diff_images: true,
      }});
      const data = response.data;
      document.getElementById('result').textContent = JSON.stringify(data, null, 2);
      if (!response.ok) {{
        renderPreviewGallery([]);
        updateArtifactLinks({{}});
        renderErrorInsights(data);
        setStatus(`review-pptx failed (${{response.status}}).`);
        persistState();
        return false;
      }}
      const result = data.result || data;
      const previewPayload = result.preview_result || result;
      renderPreviewGallery(previewPayload.previews || []);
      updateArtifactLinks(result);
      renderInsights(result);
      setStatus('Finished review-pptx flow.');
      persistState();
      return true;
    }}

    async function runAction(path, options = {{}}) {{
      let spec;
      try {{
        spec = JSON.parse(document.getElementById('spec').value);
      }} catch (error) {{
        renderErrorInsights({{ error: `Invalid JSON syntax: ${{error.message}}` }});
        setStatus('Cannot run action until JSON is valid.');
        return false;
      }}
      const outputPath = document.getElementById('outputPath').value;
      const previewDir = document.getElementById('previewDir').value;
      const previewBackend = document.getElementById('previewBackend').value;
      const baselineDir = document.getElementById('baselineDir').value;
      const requireRealPreviews = document.getElementById('requireRealPreviews').checked;
      const failOnRegression = document.getElementById('failOnRegression').checked;
      const payload = {{ spec }};
      if (path === '/render') {{
        payload.output_path = outputPath;
        payload.preview_output_dir = previewDir;
        payload.preview_backend = previewBackend;
        payload.preview_baseline_dir = baselineDir || undefined;
        payload.preview_require_real = requireRealPreviews;
        payload.preview_fail_on_regression = failOnRegression;
      }}
      if (path === '/preview') {{
        payload.output_dir = previewDir;
        payload.preview_backend = previewBackend;
        payload.baseline_dir = baselineDir || undefined;
        payload.require_real_previews = requireRealPreviews;
        payload.fail_on_regression = failOnRegression;
      }}
      if (path === '/review') {{
        payload.preview_output_dir = previewDir;
        payload.preview_backend = previewBackend;
        payload.preview_baseline_dir = baselineDir || undefined;
        payload.preview_require_real = requireRealPreviews;
        payload.preview_fail_on_regression = failOnRegression;
      }}
      const response = await executeAction(path, payload);
      const merged = attachGenerationContextToActionData(response.data, options.generationResult);
      const data = merged.data;
      document.getElementById('result').textContent = JSON.stringify(data, null, 2);
      if (!response.ok) {{
        renderPreviewGallery([]);
        updateArtifactLinks({{}});
        renderErrorInsights(data);
        setStatus(`Action failed (${{response.status}}).`);
        persistState();
        return false;
      }}
      const result = merged.result;
      const previewPayload = result.preview_result || result;
      renderPreviewGallery(previewPayload.previews || []);
      updateArtifactLinks(result);
      renderInsights(result);
      setStatus(`Finished ${{path.replace('/', '')}} flow.`);
      persistState();
      return true;
    }}
    initializeTheme();
    initControls();
  </script>
  </div>
</body>
</html>"""


def _resolve_service_asset_root(asset_root: str | Path | None) -> Path:
    return Path(asset_root or ".").resolve()


def _resolve_workspace_artifact_path(requested_path: str | Path) -> Path:
    workspace_root = Path(".").resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    candidate = Path(requested_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (workspace_root / candidate).resolve()
    try:
        resolved.relative_to(workspace_root)
    except ValueError:
        try:
            resolved.relative_to(temp_root)
        except ValueError as exc:
            raise APIRequestError(
                "artifact path must stay inside the current workspace or the system temp directory",
                HTTPStatus.FORBIDDEN,
            ) from exc
    if not resolved.exists() or not resolved.is_file():
        raise APIRequestError(f"artifact not found: {resolved}", HTTPStatus.NOT_FOUND)
    return resolved


def _extract_spec_payload(payload: dict[str, object]) -> dict[str, object]:
    if "spec" in payload:
        spec_payload = payload["spec"]
        if not isinstance(spec_payload, dict):
            raise APIRequestError("'spec' must be a JSON object")
        return spec_payload

    if "presentation" in payload and "slides" in payload:
        return {
            "presentation": payload["presentation"],
            "slides": payload["slides"],
        }

    raise APIRequestError("Request must include 'spec' or top-level presentation/slides")


def _maybe_raise_for_visual_regression(
    visual_regression: dict[str, object] | None,
    *,
    enabled: bool,
    context: str,
) -> None:
    if enabled and visual_regression_has_failures(visual_regression):
        raise APIRequestError(
            format_visual_regression_failure(visual_regression, context=context),
            HTTPStatus.CONFLICT,
        )


def validate_spec_payload(
    spec_payload: dict[str, object],
    *,
    asset_root: str | Path | None = None,
    check_assets: bool = False,
) -> dict[str, object]:
    spec = PresentationInput.model_validate(spec_payload)
    missing_assets: list[str] = []

    if check_assets:
        renderer = PresentationRenderer(
            theme_name=spec.presentation.theme,
            asset_root=_resolve_service_asset_root(asset_root),
        )
        missing_assets = renderer.collect_missing_assets(spec)

    return {
        "mode": "validate",
        "valid": True,
        "presentation_title": spec.presentation.title,
        "theme": spec.presentation.theme,
        "slide_count": len(spec.slides),
        "missing_asset_count": len(missing_assets),
        "missing_assets": missing_assets,
    }


def render_spec_payload(
    spec_payload: dict[str, object],
    *,
    output_path: str | Path,
    theme_name: str | None = None,
    asset_root: str | Path | None = None,
    primary_color: str | None = None,
    secondary_color: str | None = None,
    dry_run: bool = False,
    check_assets: bool = False,
    include_review: bool = False,
    preview_output_dir: str | Path | None = None,
    preview_backend: str = "auto",
    preview_baseline_dir: str | Path | None = None,
    preview_write_diff_images: bool = False,
    preview_require_real: bool = False,
    preview_fail_on_regression: bool = False,
) -> dict[str, object]:
    spec = PresentationInput.model_validate(spec_payload)
    effective_theme = theme_name or spec.presentation.theme
    renderer = PresentationRenderer(
        theme_name=effective_theme,
        asset_root=_resolve_service_asset_root(asset_root),
        primary_color=primary_color,
        secondary_color=secondary_color,
    )
    destination = renderer.validate_output_path(output_path)
    missing_assets = renderer.collect_missing_assets(spec)
    quality_review = (
        review_presentation(
            spec,
            theme_name=effective_theme,
            asset_root=_resolve_service_asset_root(asset_root),
        )
        if include_review
        else None
    )
    preview_result: dict[str, object] | None = None
    preview_source: str | None = None

    if dry_run:
        if preview_output_dir:
            preview_result, preview_source = render_previews_for_rendered_artifact(
                spec,
                preview_output_dir,
                rendered_pptx=None,
                theme_name=effective_theme,
                asset_root=_resolve_service_asset_root(asset_root),
                primary_color=primary_color,
                secondary_color=secondary_color,
                basename=destination.stem,
                backend=preview_backend,
                baseline_dir=preview_baseline_dir,
                write_diff_images=preview_write_diff_images,
                require_real_previews=preview_require_real,
            )
            _maybe_raise_for_visual_regression(
                preview_result.get("visual_regression"),
                enabled=preview_fail_on_regression,
                context="render dry-run preview regression",
            )
        return {
            "mode": "render",
            "rendered": False,
            "dry_run": True,
            "output_path": str(destination),
            "presentation_title": spec.presentation.title,
            "theme": effective_theme,
            "slide_count": len(spec.slides),
            "missing_asset_count": len(missing_assets) if check_assets else 0,
            "missing_assets": missing_assets if check_assets else [],
            "quality_review": quality_review,
            "preview_output_dir": str(preview_output_dir) if preview_output_dir else None,
            "preview_source": preview_source,
            "preview_result": preview_result,
        }

    rendered_output = renderer.render(spec, destination)
    if preview_output_dir:
        preview_result, preview_source = render_previews_for_rendered_artifact(
            spec,
            preview_output_dir,
            rendered_pptx=rendered_output,
            theme_name=effective_theme,
            asset_root=_resolve_service_asset_root(asset_root),
            primary_color=primary_color,
            secondary_color=secondary_color,
            basename=destination.stem,
            backend=preview_backend,
            baseline_dir=preview_baseline_dir,
            write_diff_images=preview_write_diff_images,
            require_real_previews=preview_require_real,
        )
        _maybe_raise_for_visual_regression(
            preview_result.get("visual_regression"),
            enabled=preview_fail_on_regression,
            context="render preview regression",
        )
    return {
        "mode": "render",
        "rendered": True,
        "dry_run": False,
        "output_path": str(rendered_output),
        "presentation_title": spec.presentation.title,
        "theme": effective_theme,
        "slide_count": len(spec.slides),
        "missing_asset_count": len(missing_assets) if check_assets else 0,
        "missing_assets": missing_assets if check_assets else [],
        "quality_review": quality_review,
        "preview_output_dir": str(preview_output_dir) if preview_output_dir else None,
        "preview_source": preview_source,
        "preview_result": preview_result,
    }


def review_spec_payload(
    spec_payload: dict[str, object],
    *,
    theme_name: str | None = None,
    asset_root: str | Path | None = None,
    preview_output_dir: str | Path | None = None,
    preview_backend: str = "auto",
    preview_baseline_dir: str | Path | None = None,
    preview_write_diff_images: bool = False,
    preview_require_real: bool = False,
    preview_fail_on_regression: bool = False,
) -> dict[str, object]:
    spec = PresentationInput.model_validate(spec_payload)
    review_result = review_presentation(
        spec,
        theme_name=theme_name or spec.presentation.theme,
        asset_root=_resolve_service_asset_root(asset_root),
    )
    preview_result: dict[str, object] | None = None
    preview_source: str | None = None
    if preview_output_dir:
        resolved_asset_root = _resolve_service_asset_root(asset_root)
        if preview_backend != "synthetic":
            with TemporaryDirectory(prefix="ppt_creator_api_review_preview_") as tmpdir:
                temp_pptx = Path(tmpdir) / "review-preview.pptx"
                PresentationRenderer(
                    theme_name=theme_name or spec.presentation.theme,
                    asset_root=resolved_asset_root,
                ).render(spec, temp_pptx)
                preview_result, preview_source = render_previews_for_rendered_artifact(
                    spec,
                    preview_output_dir,
                    rendered_pptx=temp_pptx,
                    theme_name=theme_name or spec.presentation.theme,
                    asset_root=resolved_asset_root,
                    basename="review-preview",
                    backend=preview_backend,
                    baseline_dir=preview_baseline_dir,
                    write_diff_images=preview_write_diff_images,
                    require_real_previews=preview_require_real,
                )
        else:
            preview_result, preview_source = render_previews_for_rendered_artifact(
                spec,
                preview_output_dir,
                rendered_pptx=None,
                theme_name=theme_name or spec.presentation.theme,
                asset_root=resolved_asset_root,
                basename="review-preview",
                backend=preview_backend,
                baseline_dir=preview_baseline_dir,
                write_diff_images=preview_write_diff_images,
                require_real_previews=preview_require_real,
            )
        review_result = augment_review_with_preview_artifacts(review_result, preview_result)
        _maybe_raise_for_visual_regression(
            preview_result.get("visual_regression"),
            enabled=preview_fail_on_regression,
            context="review preview regression",
        )
    return {
        **review_result,
        "preview_output_dir": str(preview_output_dir) if preview_output_dir else None,
        "preview_source": preview_source,
        "preview_result": preview_result,
    }


def preview_spec_payload(
    spec_payload: dict[str, object],
    *,
    output_dir: str | Path,
    theme_name: str | None = None,
    asset_root: str | Path | None = None,
    primary_color: str | None = None,
    secondary_color: str | None = None,
    basename: str | None = None,
    debug_grid: bool = False,
    debug_safe_areas: bool = False,
    backend: str = "auto",
    baseline_dir: str | Path | None = None,
    diff_threshold: float = 0.01,
    write_diff_images: bool = False,
    require_real_previews: bool = False,
    fail_on_regression: bool = False,
) -> dict[str, object]:
    spec = PresentationInput.model_validate(spec_payload)
    effective_theme = theme_name or spec.presentation.theme
    result = render_previews(
        spec,
        output_dir,
        theme_name=effective_theme,
        asset_root=_resolve_service_asset_root(asset_root),
        primary_color=primary_color,
        secondary_color=secondary_color,
        basename=basename,
        debug_grid=debug_grid,
        debug_safe_areas=debug_safe_areas,
        backend=backend,
        baseline_dir=baseline_dir,
        diff_threshold=diff_threshold,
        write_diff_images=write_diff_images,
        require_real_previews=require_real_previews,
    )
    _maybe_raise_for_visual_regression(
        result.get("visual_regression"),
        enabled=fail_on_regression,
        context="preview regression",
    )
    return result


def preview_pptx_payload(
    input_pptx: str | Path,
    *,
    output_dir: str | Path,
    theme_name: str | None = None,
    basename: str | None = None,
    baseline_dir: str | Path | None = None,
    diff_threshold: float = 0.01,
    write_diff_images: bool = False,
    require_real_previews: bool = False,
    fail_on_regression: bool = False,
) -> dict[str, object]:
    result = render_previews_from_pptx(
        input_pptx,
        output_dir,
        theme_name=theme_name,
        basename=basename,
        baseline_dir=baseline_dir,
        diff_threshold=diff_threshold,
        write_diff_images=write_diff_images,
        require_real_previews=require_real_previews,
    )
    _maybe_raise_for_visual_regression(
        result.get("visual_regression"),
        enabled=fail_on_regression,
        context="preview-pptx regression",
    )
    return result


def generate_briefing_payload(
    briefing_payload: dict[str, object] | None = None,
    *,
    provider_name: str | None = None,
    theme_name: str | None = None,
    feedback_messages: list[str] | None = None,
    intent_text: str | None = None,
    authoring_mode: str = "ai_first",
    base_url: str | None = None,
    model_name: str | None = None,
    generation_attempts: int | None = None,
) -> dict[str, object]:
    from ppt_creator_ai.briefing import (
        BriefingInput,
        build_briefing_from_intent_text,
        build_minimal_briefing_from_intent_text,
    )
    from ppt_creator_ai.providers import build_provider

    requested_provider_name = (provider_name or "").strip().lower().replace("-", "_")
    normalized_mode = (authoring_mode or "ai_first").strip().lower().replace("-", "_")
    effective_authoring_mode = normalized_mode
    if intent_text and str(intent_text).strip():
        raw_intent = str(intent_text)
        resolved_provider_name = requested_provider_name or "local_service"
        ai_first = normalized_mode in {"auto", "ai_first"} and resolved_provider_name in {
            "local_service",
            "service",
            "local",
            "hf_local_llm_service",
            "ollama_local",
            "ollama",
            "ollama_direct",
        }
        effective_authoring_mode = "ai_first" if ai_first else "hybrid"
        briefing = (
            build_minimal_briefing_from_intent_text(raw_intent)
            if ai_first
            else build_briefing_from_intent_text(raw_intent)
        )
    else:
        resolved_provider_name = requested_provider_name or "heuristic"
        if briefing_payload is None:
            raise APIRequestError("Request must include 'briefing' or 'intent_text'")
        briefing = BriefingInput.model_validate(briefing_payload)
    provider = build_provider(
        resolved_provider_name,
        base_url=base_url,
        model_name=model_name,
        generation_attempts=str(generation_attempts) if generation_attempts is not None else None,
    )
    result = provider.generate(
        briefing,
        theme_name=theme_name,
        feedback_messages=feedback_messages,
    )
    spec = PresentationInput.model_validate(result.payload)
    return {
        "mode": "generate",
        "provider": result.provider_name or provider.name,
        "transport_provider": provider.name,
        "authoring_mode": effective_authoring_mode,
        "presentation_title": spec.presentation.title,
        "theme": spec.presentation.theme,
        "slide_count": len(spec.slides),
        "payload": spec.model_dump(mode="json"),
        "analysis": result.analysis,
    }


def review_pptx_payload(
    input_pptx: str | Path,
    *,
    output_dir: str | Path,
    theme_name: str | None = None,
    basename: str | None = None,
    baseline_dir: str | Path | None = None,
    diff_threshold: float = 0.01,
    write_diff_images: bool = False,
    require_real_previews: bool = False,
    fail_on_regression: bool = False,
) -> dict[str, object]:
    result = review_pptx_artifact(
        input_pptx,
        output_dir,
        theme_name=theme_name,
        basename=basename,
        baseline_dir=baseline_dir,
        diff_threshold=diff_threshold,
        write_diff_images=write_diff_images,
        require_real_previews=require_real_previews,
    )
    _maybe_raise_for_visual_regression(
        (result.get("preview_result") or {}).get("visual_regression") if isinstance(result, dict) else None,
        enabled=fail_on_regression,
        context="review-pptx regression",
    )
    return result


def compare_pptx_payload(
    before_pptx: str | Path,
    after_pptx: str | Path,
    *,
    output_dir: str | Path,
    theme_name: str | None = None,
    basename: str | None = None,
    diff_threshold: float = 0.01,
    write_diff_images: bool = False,
    require_real_previews: bool = False,
    fail_on_regression: bool = False,
) -> dict[str, object]:
    result = compare_pptx_artifacts(
        before_pptx,
        after_pptx,
        output_dir,
        theme_name=theme_name,
        basename=basename,
        diff_threshold=diff_threshold,
        write_diff_images=write_diff_images,
        require_real_previews=require_real_previews,
    )
    _maybe_raise_for_visual_regression(
        result.get("comparison"),
        enabled=fail_on_regression,
        context="compare-pptx",
    )
    return result


def promote_baseline_payload(
    source_dir: str | Path,
    baseline_dir: str | Path,
    *,
    keep_existing: bool = False,
    skip_thumbnail_sheet: bool = False,
) -> dict[str, object]:
    return promote_preview_baseline(
        source_dir,
        baseline_dir,
        clean=not keep_existing,
        include_thumbnail_sheet=not skip_thumbnail_sheet,
    )


def build_api_server(
    host: str = "127.0.0.1",
    port: int = 8787,
    *,
    asset_root: str | Path | None = None,
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), PptCreatorAPIHandler)
    server.asset_root = _resolve_service_asset_root(asset_root)
    return server


def serve_api(
    host: str = "127.0.0.1",
    port: int = 8787,
    *,
    asset_root: str | Path | None = None,
) -> None:
    server = build_api_server(host, port, asset_root=asset_root)
    try:
        print(f"[OK] API server listening on http://{host}:{server.server_address[1]}")
        server.serve_forever()
    except KeyboardInterrupt:
        print("[INFO] API server interrupted")
    finally:
        server.server_close()


def build_health_payload(server: ThreadingHTTPServer) -> dict[str, object]:
    asset_root = getattr(server, "asset_root", None)
    return {
        "status": "ok",
        "service": "ppt_creator_api",
        "runtime_mode": os.getenv("PPT_CREATOR_RUNTIME_MODE", "host_native"),
        "pid": os.getpid(),
        "bind_host": str(server.server_address[0]),
        "bind_port": int(server.server_address[1]),
        "asset_root": str(asset_root) if asset_root is not None else None,
    }


class PptCreatorAPIHandler(BaseHTTPRequestHandler):
    server_version = "ppt-creator-api/0.1"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _json_response(self, status_code: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html_response(self, status_code: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _binary_response(self, status_code: int, content_type: str, body: bytes) -> None:
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict[str, object]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise APIRequestError("Request body is required")

        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise APIRequestError(f"Invalid JSON body: {exc.msg}") from exc

        if not isinstance(payload, dict):
            raise APIRequestError("Request body must be a JSON object")
        return payload

    def _handle_exception(self, exc: Exception) -> None:
        if isinstance(exc, APIRequestError):
            self._json_response(exc.status_code, {"error": str(exc)})
            return
        if isinstance(exc, ValidationError):
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": exc.errors()})
            return
        self._json_response(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._json_response(HTTPStatus.OK, build_health_payload(self.server))
            return
        if parsed.path == "/playground":
            self._html_response(HTTPStatus.OK, _build_playground_html())
            return
        if parsed.path == "/profiles":
            self._json_response(
                HTTPStatus.OK,
                {"profiles": [get_audience_profile(name) for name in list_audience_profiles()]},
            )
            return
        if parsed.path == "/assets":
            self._json_response(
                HTTPStatus.OK,
                {"collections": [get_asset_collection(name) for name in list_asset_collections()]},
            )
            return
        if parsed.path == "/workflows":
            self._json_response(
                HTTPStatus.OK,
                {"workflows": [get_workflow_preset(name) for name in list_workflow_presets()]},
            )
            return
        if parsed.path == "/marketplace":
            self._json_response(HTTPStatus.OK, build_marketplace_catalog())
            return
        if parsed.path == "/ai/providers":
            from ppt_creator_ai.providers import get_provider, list_provider_names

            provider_names = list_provider_names()
            self._json_response(
                HTTPStatus.OK,
                {
                    "providers": provider_names,
                    "provider_details": [
                        {
                            "name": get_provider(name).name,
                            "description": get_provider(name).description,
                            "supports_model_listing": callable(getattr(get_provider(name), "list_models", None)),
                        }
                        for name in provider_names
                    ],
                },
            )
            return
        if parsed.path == "/ai/status":
            query = parse_qs(parsed.query)
            provider_name = (query.get("provider_name") or ["local_service"])[0]
            base_url = (query.get("base_url") or [None])[0] or None
            model_name = (query.get("model_name") or [None])[0] or None
            generation_attempts_raw = (query.get("generation_attempts") or [None])[0]
            generation_attempts = int(generation_attempts_raw) if generation_attempts_raw not in {None, ""} else None
            self._json_response(
                HTTPStatus.OK,
                {
                    "result": ai_status_payload(
                        provider_name=provider_name,
                        base_url=base_url,
                        model_name=model_name,
                        generation_attempts=generation_attempts,
                    )
                },
            )
            return
        if parsed.path == "/ai/models":
            from ppt_creator_ai.providers import build_provider

            query = parse_qs(parsed.query)
            provider_name = (query.get("provider_name") or ["ollama_local"])[0]
            base_url = (query.get("base_url") or [None])[0] or None
            provider = build_provider(provider_name, base_url=base_url)
            list_models = getattr(provider, "list_models", None)
            if not callable(list_models):
                raise APIRequestError(f"Provider '{provider.name}' does not support model listing")
            self._json_response(HTTPStatus.OK, {"result": list_models()})
            return
        if parsed.path == "/templates":
            self._json_response(HTTPStatus.OK, {"domains": list_template_domains()})
            return
        if parsed.path == "/brand-packs":
            self._json_response(
                HTTPStatus.OK,
                {"brand_packs": [get_brand_pack(name) for name in list_brand_packs()]},
            )
            return
        if parsed.path == "/artifact":
            query = parse_qs(parsed.query)
            requested_path = (query.get("path") or [""])[0]
            if not requested_path:
                self._json_response(HTTPStatus.BAD_REQUEST, {"error": "artifact path is required"})
                return
            artifact_path = _resolve_workspace_artifact_path(requested_path)
            content_type = mimetypes.guess_type(str(artifact_path))[0] or "application/octet-stream"
            self._binary_response(HTTPStatus.OK, content_type, artifact_path.read_bytes())
            return
        self._json_response(HTTPStatus.NOT_FOUND, {"error": "Route not found"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json_body()
            default_asset_root = getattr(self.server, "asset_root", Path(".").resolve())

            if self.path == "/validate":
                spec_payload = _extract_spec_payload(payload)
                result = validate_spec_payload(
                    spec_payload,
                    asset_root=payload.get("asset_root") or default_asset_root,
                    check_assets=bool(payload.get("check_assets", False)),
                )
                self._json_response(HTTPStatus.OK, {"result": result})
                return

            if self.path == "/render":
                if "output_path" not in payload:
                    raise APIRequestError("'output_path' is required for /render")
                spec_payload = _extract_spec_payload(payload)
                result = render_spec_payload(
                    spec_payload,
                    output_path=str(payload["output_path"]),
                    theme_name=str(payload["theme_name"]) if payload.get("theme_name") else None,
                    asset_root=payload.get("asset_root") or default_asset_root,
                    primary_color=str(payload["primary_color"]) if payload.get("primary_color") else None,
                    secondary_color=str(payload["secondary_color"]) if payload.get("secondary_color") else None,
                    dry_run=bool(payload.get("dry_run", False)),
                    check_assets=bool(payload.get("check_assets", False)),
                    include_review=bool(payload.get("include_review", False)),
                    preview_output_dir=payload.get("preview_output_dir"),
                    preview_backend=str(payload["preview_backend"]) if payload.get("preview_backend") else "auto",
                    preview_baseline_dir=payload.get("preview_baseline_dir"),
                    preview_write_diff_images=bool(payload.get("preview_write_diff_images", False)),
                    preview_require_real=bool(payload.get("preview_require_real", False)),
                    preview_fail_on_regression=bool(payload.get("preview_fail_on_regression", False)),
                )
                self._json_response(HTTPStatus.OK, {"result": result})
                return

            if self.path == "/review":
                spec_payload = _extract_spec_payload(payload)
                result = review_spec_payload(
                    spec_payload,
                    theme_name=str(payload["theme_name"]) if payload.get("theme_name") else None,
                    asset_root=payload.get("asset_root") or default_asset_root,
                    preview_output_dir=payload.get("preview_output_dir"),
                    preview_backend=str(payload["preview_backend"]) if payload.get("preview_backend") else "auto",
                    preview_baseline_dir=payload.get("preview_baseline_dir"),
                    preview_write_diff_images=bool(payload.get("preview_write_diff_images", False)),
                    preview_require_real=bool(payload.get("preview_require_real", False)),
                    preview_fail_on_regression=bool(payload.get("preview_fail_on_regression", False)),
                )
                self._json_response(HTTPStatus.OK, {"result": result})
                return

            if self.path == "/preview":
                if "output_dir" not in payload:
                    raise APIRequestError("'output_dir' is required for /preview")
                spec_payload = _extract_spec_payload(payload)
                result = preview_spec_payload(
                    spec_payload,
                    output_dir=str(payload["output_dir"]),
                    theme_name=str(payload["theme_name"]) if payload.get("theme_name") else None,
                    asset_root=payload.get("asset_root") or default_asset_root,
                    primary_color=str(payload["primary_color"]) if payload.get("primary_color") else None,
                    secondary_color=str(payload["secondary_color"]) if payload.get("secondary_color") else None,
                    basename=str(payload["basename"]) if payload.get("basename") else None,
                    debug_grid=bool(payload.get("debug_grid", False)),
                    debug_safe_areas=bool(payload.get("debug_safe_areas", False)),
                    backend=str(payload["preview_backend"]) if payload.get("preview_backend") else "auto",
                    baseline_dir=payload.get("baseline_dir"),
                    diff_threshold=float(payload.get("diff_threshold", 0.01)),
                    write_diff_images=bool(payload.get("write_diff_images", False)),
                    require_real_previews=bool(payload.get("require_real_previews", False)),
                    fail_on_regression=bool(payload.get("fail_on_regression", False)),
                )
                self._json_response(HTTPStatus.OK, {"result": result})
                return

            if self.path == "/generate":
                briefing_payload = payload.get("briefing") if isinstance(payload.get("briefing"), dict) else None
                intent_text = str(payload.get("intent_text") or "").strip() or None
                if briefing_payload is None and intent_text is None:
                    briefing_payload = payload
                result = generate_briefing_payload(
                    briefing_payload,
                    provider_name=(str(payload["provider_name"]) if payload.get("provider_name") else None),
                    theme_name=str(payload["theme_name"]) if payload.get("theme_name") else None,
                    feedback_messages=[
                        str(item) for item in (payload.get("feedback_messages") or []) if str(item).strip()
                    ],
                    intent_text=intent_text,
                    authoring_mode=str(payload.get("authoring_mode") or "ai_first"),
                    base_url=str(payload["base_url"]) if payload.get("base_url") else None,
                    model_name=str(payload["model_name"]) if payload.get("model_name") else None,
                    generation_attempts=(
                        int(payload["generation_attempts"])
                        if payload.get("generation_attempts") not in {None, ""}
                        else None
                    ),
                )
                self._json_response(HTTPStatus.OK, {"result": result})
                return

            if self.path == "/generate-and-render":
                if "output_path" not in payload:
                    raise APIRequestError("'output_path' is required for /generate-and-render")
                briefing_payload = payload.get("briefing") if isinstance(payload.get("briefing"), dict) else None
                intent_text = str(payload.get("intent_text") or "").strip() or None
                if briefing_payload is None and intent_text is None:
                    briefing_payload = payload
                generation_result = generate_briefing_payload(
                    briefing_payload,
                    provider_name=(str(payload["provider_name"]) if payload.get("provider_name") else None),
                    theme_name=str(payload["theme_name"]) if payload.get("theme_name") else None,
                    feedback_messages=[
                        str(item) for item in (payload.get("feedback_messages") or []) if str(item).strip()
                    ],
                    intent_text=intent_text,
                    authoring_mode=str(payload.get("authoring_mode") or "ai_first"),
                    base_url=str(payload["base_url"]) if payload.get("base_url") else None,
                    model_name=str(payload["model_name"]) if payload.get("model_name") else None,
                    generation_attempts=(
                        int(payload["generation_attempts"])
                        if payload.get("generation_attempts") not in {None, ""}
                        else None
                    ),
                )
                render_result = render_spec_payload(
                    generation_result["payload"],
                    output_path=str(payload["output_path"]),
                    theme_name=str(payload["theme_name"]) if payload.get("theme_name") else None,
                    asset_root=payload.get("asset_root") or default_asset_root,
                    primary_color=str(payload["primary_color"]) if payload.get("primary_color") else None,
                    secondary_color=str(payload["secondary_color"]) if payload.get("secondary_color") else None,
                    dry_run=bool(payload.get("dry_run", False)),
                    check_assets=bool(payload.get("check_assets", False)),
                    include_review=bool(payload.get("include_review", False)),
                    preview_output_dir=payload.get("preview_output_dir"),
                    preview_backend=str(payload["preview_backend"]) if payload.get("preview_backend") else "auto",
                    preview_baseline_dir=payload.get("preview_baseline_dir"),
                    preview_write_diff_images=bool(payload.get("preview_write_diff_images", False)),
                    preview_require_real=bool(payload.get("preview_require_real", False)),
                    preview_fail_on_regression=bool(payload.get("preview_fail_on_regression", False)),
                )
                self._json_response(
                    HTTPStatus.OK,
                    {"result": {"generation": generation_result, "render": render_result}},
                )
                return

            if self.path == "/preview-pptx":
                if "input_pptx" not in payload:
                    raise APIRequestError("'input_pptx' is required for /preview-pptx")
                if "output_dir" not in payload:
                    raise APIRequestError("'output_dir' is required for /preview-pptx")
                result = preview_pptx_payload(
                    str(payload["input_pptx"]),
                    output_dir=str(payload["output_dir"]),
                    theme_name=str(payload["theme_name"]) if payload.get("theme_name") else None,
                    basename=str(payload["basename"]) if payload.get("basename") else None,
                    baseline_dir=payload.get("baseline_dir"),
                    diff_threshold=float(payload.get("diff_threshold", 0.01)),
                    write_diff_images=bool(payload.get("write_diff_images", False)),
                    require_real_previews=bool(payload.get("require_real_previews", False)),
                    fail_on_regression=bool(payload.get("fail_on_regression", False)),
                )
                self._json_response(HTTPStatus.OK, {"result": result})
                return

            if self.path == "/review-pptx":
                if "input_pptx" not in payload:
                    raise APIRequestError("'input_pptx' is required for /review-pptx")
                if "output_dir" not in payload:
                    raise APIRequestError("'output_dir' is required for /review-pptx")
                result = review_pptx_payload(
                    str(payload["input_pptx"]),
                    output_dir=str(payload["output_dir"]),
                    theme_name=str(payload["theme_name"]) if payload.get("theme_name") else None,
                    basename=str(payload["basename"]) if payload.get("basename") else None,
                    baseline_dir=payload.get("baseline_dir"),
                    diff_threshold=float(payload.get("diff_threshold", 0.01)),
                    write_diff_images=bool(payload.get("write_diff_images", False)),
                    require_real_previews=bool(payload.get("require_real_previews", False)),
                    fail_on_regression=bool(payload.get("fail_on_regression", False)),
                )
                self._json_response(HTTPStatus.OK, {"result": result})
                return

            if self.path == "/compare-pptx":
                if "before_pptx" not in payload:
                    raise APIRequestError("'before_pptx' is required for /compare-pptx")
                if "after_pptx" not in payload:
                    raise APIRequestError("'after_pptx' is required for /compare-pptx")
                if "output_dir" not in payload:
                    raise APIRequestError("'output_dir' is required for /compare-pptx")
                result = compare_pptx_payload(
                    str(payload["before_pptx"]),
                    str(payload["after_pptx"]),
                    output_dir=str(payload["output_dir"]),
                    theme_name=str(payload["theme_name"]) if payload.get("theme_name") else None,
                    basename=str(payload["basename"]) if payload.get("basename") else None,
                    diff_threshold=float(payload.get("diff_threshold", 0.01)),
                    write_diff_images=bool(payload.get("write_diff_images", False)),
                    require_real_previews=bool(payload.get("require_real_previews", False)),
                    fail_on_regression=bool(payload.get("fail_on_regression", False)),
                )
                self._json_response(HTTPStatus.OK, {"result": result})
                return

            if self.path == "/promote-baseline":
                if "source_dir" not in payload:
                    raise APIRequestError("'source_dir' is required for /promote-baseline")
                if "baseline_dir" not in payload:
                    raise APIRequestError("'baseline_dir' is required for /promote-baseline")
                result = promote_baseline_payload(
                    str(payload["source_dir"]),
                    str(payload["baseline_dir"]),
                    keep_existing=bool(payload.get("keep_existing", False)),
                    skip_thumbnail_sheet=bool(payload.get("skip_thumbnail_sheet", False)),
                )
                self._json_response(HTTPStatus.OK, {"result": result})
                return

            if self.path == "/template":
                if "domain" not in payload:
                    raise APIRequestError("'domain' is required for /template")
                packet = build_template_packet(
                    str(payload["domain"]),
                    theme_name=str(payload["theme_name"]) if payload.get("theme_name") else None,
                    audience_profile=str(payload["audience_profile"]) if payload.get("audience_profile") else None,
                    brand_pack=str(payload["brand_pack"]) if payload.get("brand_pack") else None,
                )
                self._json_response(HTTPStatus.OK, {"template": packet["template"], "packet": packet})
                return

            if self.path == "/workflow-template":
                if "workflow_name" not in payload:
                    raise APIRequestError("'workflow_name' is required for /workflow-template")
                packet = build_workflow_packet(
                    str(payload["workflow_name"]),
                    theme_name=str(payload["theme_name"]) if payload.get("theme_name") else None,
                    brand_pack=str(payload["brand_pack"]) if payload.get("brand_pack") else None,
                )
                self._json_response(HTTPStatus.OK, {"packet": packet})
                return

            self._json_response(HTTPStatus.NOT_FOUND, {"error": "Route not found"})
        except Exception as exc:  # noqa: BLE001
            self._handle_exception(exc)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a lightweight HTTP API for PPT Creator.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=8787, help="Port to listen on")
    parser.add_argument("--asset-root", help="Default asset root for API requests")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    serve_api(args.host, args.port, asset_root=args.asset_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
