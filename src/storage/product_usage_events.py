from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from src.storage.runtime_paths import get_runtime_root

_USAGE_LOCK = threading.Lock()
_MAX_EVENT_BYTES = 8192
_MAX_STRING_LENGTH = 220
_MAX_EVENTS_RETURNED = 2000

ALLOWED_USAGE_EVENTS = {
    "landing_viewed",
    "landing_left",
    "landing_scroll_25",
    "landing_scroll_50",
    "landing_scroll_75",
    "landing_scroll_100",
    "landing_cta_open_app_clicked",
    "landing_meet_danyel_clicked",
    "landing_github_clicked",
    "landing_linkedin_clicked",
    "meet_danyel_opened",
    "meet_danyel_closed",
    "app_opened",
    "page_viewed",
    "page_left",
    "page_scroll_depth",
    "nav_clicked",
    "ui_clicked",
    "topbar_search_clicked",
    "runtime_drawer_opened",
    "admin_login_opened",
    "admin_login_success",
    "admin_login_failed",
    "workflow_catalog_viewed",
    "workflow_page_viewed",
    "workflow_started",
    "workflow_completed",
    "workflow_warning_result",
    "workflow_empty_result",
    "workflow_failed",
    "workflow_result_viewed",
    "workflow_tab_changed",
    "trello_preview_opened",
    "trello_preview_completed",
    "trello_open_current_page_clicked",
    "trello_publish_attempted",
    "trello_publish_blocked_public",
    "trello_publish_completed_admin",
    "notion_preview_opened",
    "notion_preview_completed",
    "notion_open_current_page_clicked",
    "notion_publish_attempted",
    "notion_publish_blocked_public",
    "notion_publish_completed_admin",
    "deck_export_requested",
    "deck_export_completed",
    "deck_export_failed",
    "deck_download_clicked",
    "ai_lab_opened",
    "runtime_controls_opened",
    "preferences_opened",
    "documents_opened",
    "run_history_opened",
    "observability_opened",
    "api_error_seen",
    "timeout_seen",
    "cloudflare_524_seen",
    "workflow_polling_failed",
    "empty_state_seen",
    "admin_only_gate_seen",
}

SAFE_DETAIL_KEYS = {
    "route",
    "page",
    "from_route",
    "to_route",
    "workflow",
    "workflow_id",
    "status",
    "result_status",
    "duration_ms",
    "scroll_depth",
    "button_label",
    "button_id",
    "target",
    "target_kind",
    "href_kind",
    "href_host",
    "tag",
    "tab",
    "section",
    "document_count",
    "artifact_count",
    "finding_count",
    "warning_count",
    "error_kind",
    "error_status",
    "run_id",
    "job_id",
    "deck_available",
    "write_scope",
    "source",
    "entry_url",
    "raw_referrer",
    "referrer_kind",
    "traffic_source",
    "first_seen_at",
    "first_entry_url",
    "first_raw_referrer",
    "first_referrer_kind",
    "first_traffic_source",
    "first_utm_source",
    "first_utm_medium",
    "first_utm_campaign",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "browser_family",
    "language",
    "timezone",
    "viewport_width",
    "viewport_height",
    "screen_width",
    "screen_height",
    "device_pixel_ratio",
}

NUMERIC_DETAIL_KEYS = {
    "duration_ms",
    "scroll_depth",
    "document_count",
    "artifact_count",
    "finding_count",
    "warning_count",
    "error_status",
    "viewport_width",
    "viewport_height",
    "screen_width",
    "screen_height",
}

LONG_DETAIL_KEYS = {
    "entry_url",
    "raw_referrer",
    "first_entry_url",
    "first_raw_referrer",
}

QUALIFIED_EVENTS = {
    "app_opened",
    "landing_scroll_50",
    "landing_scroll_75",
    "landing_scroll_100",
    "landing_cta_open_app_clicked",
    "workflow_catalog_viewed",
    "workflow_page_viewed",
    "workflow_started",
    "workflow_completed",
    "trello_preview_opened",
    "notion_preview_opened",
    "deck_export_requested",
    "deck_download_clicked",
    "meet_danyel_opened",
    "landing_meet_danyel_clicked",
}

STRONG_USAGE_EVENTS = {
    "workflow_started",
    "workflow_completed",
    "workflow_warning_result",
    "trello_preview_opened",
    "notion_preview_opened",
    "deck_export_requested",
    "deck_export_completed",
    "deck_download_clicked",
}


def get_product_usage_events_path(base_dir: Path) -> Path:
    runtime_root = get_runtime_root(base_dir)
    return runtime_root / "logs" / "product" / "usage_events.jsonl"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _clean_string(value: Any, *, max_length: int = _MAX_STRING_LENGTH) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    if not text:
        return None
    return text[:max_length]


def _clean_int(value: Any, *, minimum: int = 0, maximum: int = 24 * 60 * 60 * 1000) -> int | None:
    try:
        number = int(float(value))
    except Exception:
        return None
    if number < minimum:
        return minimum
    if number > maximum:
        return maximum
    return number


def _event_session_hash(identity: object) -> str | None:
    raw_session_id = str(getattr(identity, "session_id", "") or "").strip()
    if not raw_session_id:
        raw_session_id = str(getattr(identity, "user_id", "") or "").strip()
    if not raw_session_id:
        return None
    secret = str(os.getenv("AI_DECISION_STUDIO_SESSION_SECRET") or os.getenv("APP_SECRET") or "axiovance-local-usage-salt")
    return hashlib.sha256(f"{secret}:{raw_session_id}".encode("utf-8")).hexdigest()[:20]


def _header_value(headers: Any, key: str) -> str | None:
    try:
        value = headers.get(key)  # email.message.Message supports case-insensitive get
    except Exception:
        value = None
    return _clean_string(value, max_length=500)


def _classify_referrer(referrer: str | None) -> str | None:
    if not referrer:
        return None
    parsed = urlparse(referrer)
    host = (parsed.netloc or "").lower()
    if not host:
        return "direct"
    if "linkedin" in host:
        return "linkedin"
    if "github" in host:
        return "github"
    if "google" in host:
        return "google"
    if "chatgpt" in host or "openai" in host:
        return "chatgpt"
    if "danyel-lambert.com" in host:
        return "internal"
    return host[:80]


def _normalize_source(value: Any) -> str | None:
    text = _clean_string(value, max_length=120)
    if not text:
        return None
    raw = text.lower()
    if raw.startswith("utm:"):
        source = _normalize_source(raw.removeprefix("utm:"))
        return f"utm:{source}" if source else "utm"
    if raw in {"127.0.0.1", "127.0.0.1:5173", "localhost"} or "localhost" in raw:
        return "internal"
    if "danyel-lambert.com" in raw or "axiovance" in raw:
        return "internal"
    if "linkedin" in raw or raw == "li":
        return "linkedin"
    if "github" in raw:
        return "github"
    if "google" in raw:
        return "google"
    if "bing" in raw:
        return "bing"
    if "chatgpt" in raw or "openai" in raw:
        return "chatgpt"
    if "whatsapp" in raw:
        return "whatsapp"
    if "twitter" in raw or "x.com" in raw:
        return "twitter"
    if "mail" in raw or "email" in raw:
        return "email"
    return re.sub(r"[^a-z0-9_.:-]+", "-", raw)[:80]


def _preferred_referrer_kind(*values: Any) -> str | None:
    normalized_values = [_normalize_source(value) for value in values]
    for value in normalized_values:
        if value and value not in {"direct", "internal"}:
            return value
    for value in normalized_values:
        if value:
            return value
    return None


def _classify_user_agent(user_agent: str | None) -> str | None:
    if not user_agent:
        return None
    ua = user_agent.lower()
    if "edg/" in ua or "edga/" in ua:
        return "Edge"
    if "chrome/" in ua and "chromium" not in ua:
        return "Chrome"
    if "safari/" in ua and "chrome/" not in ua:
        return "Safari"
    if "firefox/" in ua:
        return "Firefox"
    if "curl/" in ua:
        return "curl"
    if "python-requests" in ua:
        return "python-requests"
    if "bot" in ua or "crawler" in ua or "spider" in ua:
        return "bot-like"
    return "Other"


def _href_host(value: Any) -> str | None:
    text = _clean_string(value, max_length=500)
    if not text:
        return None
    parsed = urlparse(text)
    if parsed.netloc:
        return parsed.netloc.lower()[:120]
    return None


def sanitize_usage_detail(payload: dict[str, Any]) -> dict[str, Any]:
    details: dict[str, Any] = {}
    for key in SAFE_DETAIL_KEYS:
        if key not in payload:
            continue
        value = payload.get(key)
        if key in NUMERIC_DETAIL_KEYS:
            cleaned_number = _clean_int(value, maximum=100000000 if key == "duration_ms" else 100000)
            if cleaned_number is not None:
                details[key] = cleaned_number
        elif key == "device_pixel_ratio":
            try:
                ratio = float(value)
            except Exception:
                ratio = None
            if ratio is not None and 0 < ratio <= 20:
                details[key] = round(ratio, 3)
        elif isinstance(value, bool):
            details[key] = value
        else:
            cleaned_text = _clean_string(value, max_length=500 if key in LONG_DETAIL_KEYS else _MAX_STRING_LENGTH)
            if cleaned_text is not None:
                details[key] = cleaned_text
    if "href_host" not in details and payload.get("href"):
        host = _href_host(payload.get("href"))
        if host:
            details["href_host"] = host
    return details


def build_usage_event_record(*, base_dir: Path, identity: object, headers: Any, payload: dict[str, Any]) -> dict[str, Any]:
    raw_event = str(payload.get("event") or "").strip().lower().replace("-", "_")
    if raw_event not in ALLOWED_USAGE_EVENTS:
        raise ValueError(f"Unsupported usage event: {raw_event or '<empty>'}")
    raw_payload_bytes = len(json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"))
    if raw_payload_bytes > _MAX_EVENT_BYTES:
        raise ValueError("Usage event payload is too large.")

    referrer = _header_value(headers, "Referer")
    country = _header_value(headers, "CF-IPCountry")
    user_agent = _header_value(headers, "User-Agent")
    client_ts = _clean_string(payload.get("client_ts"), max_length=80)
    details = sanitize_usage_detail(payload)

    # Browser telemetry POSTs are same-origin, so the HTTP Referer usually points
    # back to Axiovance. Prefer the client-captured document.referrer / first-touch
    # source when it identifies an external source such as Google organic search.
    referrer_kind = _preferred_referrer_kind(
        payload.get("referrer_kind"),
        payload.get("traffic_source"),
        payload.get("first_traffic_source"),
        payload.get("first_referrer_kind"),
        _classify_referrer(_clean_string(payload.get("raw_referrer"), max_length=500)),
        _classify_referrer(referrer),
    )

    record = {
        "ts": _utc_now_iso(),
        "client_ts": client_ts,
        "event": raw_event,
        "session_hash": _event_session_hash(identity),
        "role": str(getattr(identity, "role", "") or "public"),
        "country": country,
        "referrer_kind": referrer_kind,
        "user_agent_family": _classify_user_agent(user_agent),
        "details": details,
    }
    # Keep storage anchored to runtime; included for future migration/debugging but not exposed to visitors.
    get_product_usage_events_path(base_dir).parent.mkdir(parents=True, exist_ok=True)
    return record


def append_usage_event(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    with _USAGE_LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def iter_usage_events(path: Path, *, limit: int = _MAX_EVENTS_RETURNED) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    normalized_limit = max(1, min(int(limit or 500), _MAX_EVENTS_RETURNED))
    with _USAGE_LOCK:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return []
    events: list[dict[str, Any]] = []
    for line in lines[-normalized_limit:]:
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                events.append(item)
        except json.JSONDecodeError:
            continue
    return events


def _counter_payload(counter: Counter, *, limit: int = 20) -> list[dict[str, Any]]:
    return [{"key": key, "count": count} for key, count in counter.most_common(limit)]


def _event_route(event: dict[str, Any]) -> str:
    details = event.get("details") if isinstance(event.get("details"), dict) else {}
    return str(details.get("route") or details.get("page") or "unknown")


def _event_workflow(event: dict[str, Any]) -> str | None:
    details = event.get("details") if isinstance(event.get("details"), dict) else {}
    workflow = str(details.get("workflow") or details.get("workflow_id") or "").strip()
    return workflow or None


def build_usage_summary(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    event_list = list(events)
    now = datetime.now(timezone.utc)
    cutoffs = {
        "24h": now - timedelta(hours=24),
        "7d": now - timedelta(days=7),
        "30d": now - timedelta(days=30),
        "all": None,
    }

    event_counts = Counter(str(item.get("event") or "unknown") for item in event_list)
    country_counts = Counter(str(item.get("country") or "unknown") for item in event_list)
    referrer_counts = Counter(str(item.get("referrer_kind") or "direct") for item in event_list)
    user_agent_counts = Counter(str(item.get("user_agent_family") or "unknown") for item in event_list)
    page_counts = Counter(_event_route(item) for item in event_list if str(item.get("event")) == "page_viewed")
    click_counts = Counter(
        str((item.get("details") or {}).get("button_label") or (item.get("details") or {}).get("button_id") or "unknown")
        for item in event_list
        if str(item.get("event")) == "ui_clicked"
    )

    sessions_by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in event_list:
        session_hash = str(item.get("session_hash") or "unknown")
        sessions_by_hash[session_hash].append(item)

    workflow_stats: dict[str, Counter] = defaultdict(Counter)
    for item in event_list:
        workflow = _event_workflow(item)
        if not workflow:
            continue
        workflow_stats[workflow][str(item.get("event") or "unknown")] += 1

    duration_by_route: dict[str, list[int]] = defaultdict(list)
    for item in event_list:
        if str(item.get("event")) != "page_left":
            continue
        details = item.get("details") if isinstance(item.get("details"), dict) else {}
        duration = details.get("duration_ms")
        if isinstance(duration, int):
            duration_by_route[_event_route(item)].append(duration)

    page_duration = []
    for route, durations in duration_by_route.items():
        if not durations:
            continue
        total = sum(durations)
        page_duration.append(
            {
                "route": route,
                "views": len(durations),
                "avg_duration_ms": int(total / len(durations)),
                "max_duration_ms": max(durations),
            }
        )
    page_duration.sort(key=lambda item: item["avg_duration_ms"], reverse=True)

    windows: dict[str, dict[str, Any]] = {}
    for label, cutoff in cutoffs.items():
        scoped = event_list
        if cutoff is not None:
            scoped = [item for item in event_list if (_parse_iso(item.get("ts")) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff]
        sessions = {str(item.get("session_hash") or "unknown") for item in scoped}
        qualified_sessions = {
            str(item.get("session_hash") or "unknown")
            for item in scoped
            if str(item.get("event") or "") in QUALIFIED_EVENTS
        }
        strong_sessions = {
            str(item.get("session_hash") or "unknown")
            for item in scoped
            if str(item.get("event") or "") in STRONG_USAGE_EVENTS
        }
        windows[label] = {
            "events": len(scoped),
            "unique_sessions": len(sessions - {"unknown"}) + (1 if "unknown" in sessions else 0),
            "qualified_sessions": len(qualified_sessions - {"unknown"}) + (1 if "unknown" in qualified_sessions else 0),
            "strong_usage_sessions": len(strong_sessions - {"unknown"}) + (1 if "unknown" in strong_sessions else 0),
        }

    session_rows = []
    for session_hash, session_events in sessions_by_hash.items():
        parsed_times = [_parse_iso(item.get("ts")) for item in session_events]
        parsed_times = [item for item in parsed_times if item is not None]
        session_event_names = {str(item.get("event") or "") for item in session_events}
        countries = Counter(str(item.get("country") or "unknown") for item in session_events)
        workflows = sorted({workflow for item in session_events for workflow in [_event_workflow(item)] if workflow})
        session_rows.append(
            {
                "session_hash": session_hash,
                "first_seen": min(parsed_times).isoformat() if parsed_times else None,
                "last_seen": max(parsed_times).isoformat() if parsed_times else None,
                "country": countries.most_common(1)[0][0] if countries else "unknown",
                "event_count": len(session_events),
                "qualified": bool(session_event_names & QUALIFIED_EVENTS),
                "strong_usage": bool(session_event_names & STRONG_USAGE_EVENTS),
                "workflows": workflows[:8],
                "completed_workflows": sum(1 for item in session_events if str(item.get("event")) == "workflow_completed"),
                "failed_workflows": sum(1 for item in session_events if str(item.get("event")) == "workflow_failed"),
                "meet_danyel": any(str(item.get("event")) in {"meet_danyel_opened", "landing_meet_danyel_clicked"} for item in session_events),
            }
        )
    session_rows.sort(key=lambda item: str(item.get("last_seen") or ""), reverse=True)

    return {
        "ok": True,
        "generated_at": _utc_now_iso(),
        "total_events": len(event_list),
        "windows": windows,
        "event_counts": _counter_payload(event_counts, limit=60),
        "countries": _counter_payload(country_counts, limit=30),
        "referrers": _counter_payload(referrer_counts, limit=30),
        "user_agents": _counter_payload(user_agent_counts, limit=20),
        "top_pages": _counter_payload(page_counts, limit=40),
        "top_clicks": _counter_payload(click_counts, limit=40),
        "page_duration": page_duration[:40],
        "workflows": [
            {"workflow": workflow, **dict(counter)}
            for workflow, counter in sorted(workflow_stats.items())
        ],
        "sessions": session_rows[:200],
        "recent_events": event_list[-80:][::-1],
    }
