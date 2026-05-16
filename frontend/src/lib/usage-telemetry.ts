const rawBaseUrl = (import.meta.env.VITE_PRODUCT_API_BASE_URL as string | undefined)?.trim();
const PRODUCT_API_BASE_URL = rawBaseUrl ? rawBaseUrl.replace(/\/$/, '') : '';
const FIRST_TOUCH_STORAGE_KEY = 'axiovance_first_touch_v1';

type UsagePayload = Record<string, unknown>;

const WORKFLOW_COMPLETED_STATUSES = new Set(['completed', 'success', 'ready']);
const WORKFLOW_WARNING_STATUSES = new Set(['warning', 'warnings']);
const WORKFLOW_FAILED_STATUSES = new Set(['failed', 'error', 'timeout']);

function safeString(value: unknown): string | undefined {
  if (value === null || value === undefined) return undefined;
  const text = String(value).trim();
  return text || undefined;
}

function classifyReferrer(referrer?: string | null): string {
  const value = String(referrer || '').trim().toLowerCase();
  if (!value) return 'direct';
  try {
    const host = new URL(value).hostname.replace(/^www\./, '');
    if (host === '127.0.0.1' || host === 'localhost') return 'internal';
    if (typeof window !== 'undefined' && host === window.location.hostname.replace(/^www\./, '')) return 'internal';
    if (host.includes('linkedin')) return 'linkedin';
    if (host.includes('github')) return 'github';
    if (host.includes('google')) return 'google';
    if (host.includes('bing')) return 'bing';
    if (host.includes('danyel-lambert.com')) return host.includes('aidstudio') ? 'legacy_domain' : 'internal';
    return host;
  } catch {
    return value.slice(0, 80);
  }
}

function normalizeTrafficSource(value?: string | null): string {
  const text = String(value || '').trim().toLowerCase();
  if (!text) return '';
  if (text.includes('linkedin') || text === 'li') return 'linkedin';
  if (text.includes('github')) return 'github';
  if (text.includes('google')) return 'google';
  if (text.includes('bing')) return 'bing';
  if (text.includes('x.com') || text.includes('twitter')) return 'twitter';
  if (text.includes('whatsapp')) return 'whatsapp';
  if (text.includes('email') || text.includes('mail')) return 'email';
  return text.replace(/[^a-z0-9_.:-]+/g, '-').slice(0, 80);
}

type FirstTouch = {
  first_seen_at: string;
  first_entry_url: string;
  first_referrer_kind: string;
  first_raw_referrer?: string;
  first_utm_source?: string;
  first_utm_medium?: string;
  first_utm_campaign?: string;
  first_traffic_source: string;
};

function readFirstTouch(): FirstTouch | null {
  try {
    const raw = window.sessionStorage.getItem(FIRST_TOUCH_STORAGE_KEY) || window.localStorage.getItem(FIRST_TOUCH_STORAGE_KEY);
    return raw ? JSON.parse(raw) as FirstTouch : null;
  } catch {
    return null;
  }
}

function writeFirstTouch(value: FirstTouch) {
  try {
    const raw = JSON.stringify(value);
    window.sessionStorage.setItem(FIRST_TOUCH_STORAGE_KEY, raw);
    window.localStorage.setItem(FIRST_TOUCH_STORAGE_KEY, raw);
  } catch {
    // ignore storage failures
  }
}

function getFirstTouch(current: {
  entryUrl: string;
  rawReferrer?: string;
  referrerKind: string;
  utm: Record<string, string>;
}): FirstTouch {
  const existing = readFirstTouch();
  const utmSource = normalizeTrafficSource(current.utm.utm_source);
  const currentSource = utmSource || (current.referrerKind === 'internal' ? '' : normalizeTrafficSource(current.referrerKind));

  // If an older local/internal/direct first touch exists, allow the current
  // external entry source (for example organic Google) to replace it.
  if (existing) {
    const existingSource = normalizeTrafficSource(existing.first_traffic_source);
    if (!currentSource || !['direct', 'internal', ''].includes(existingSource)) {
      return existing;
    }
  }

  const trafficSource = currentSource || current.referrerKind || 'direct';

  const firstTouch: FirstTouch = {
    first_seen_at: new Date().toISOString(),
    first_entry_url: current.entryUrl,
    first_referrer_kind: current.referrerKind,
    first_raw_referrer: current.rawReferrer || undefined,
    first_utm_source: current.utm.utm_source,
    first_utm_medium: current.utm.utm_medium,
    first_utm_campaign: current.utm.utm_campaign,
    first_traffic_source: trafficSource,
  };
  writeFirstTouch(firstTouch);
  return firstTouch;
}

function browserFamily(userAgent: string): string {
  const ua = userAgent.toLowerCase();
  if (ua.includes('edg/')) return 'Edge';
  if (ua.includes('chrome/') && !ua.includes('edg/')) return 'Chrome';
  if (ua.includes('safari/') && !ua.includes('chrome/')) return 'Safari';
  if (ua.includes('firefox/')) return 'Firefox';
  if (ua.includes('opera') || ua.includes('opr/')) return 'Opera';
  if (ua.includes('bot') || ua.includes('crawler') || ua.includes('spider')) return 'Bot-like';
  return 'Other';
}

function getUtmParams(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const params = new URLSearchParams(window.location.search);
  const out: Record<string, string> = {};
  for (const key of ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term']) {
    const value = params.get(key);
    if (value) out[key] = value;
  }
  return out;
}

function clientContext(): UsagePayload {
  if (typeof window === 'undefined') return {};
  const nav = window.navigator;
  const utm = getUtmParams();
  const entryUrl = window.location.href;
  const rawReferrer = typeof document !== 'undefined' ? document.referrer || undefined : undefined;
  const referrerKind = typeof document !== 'undefined' ? classifyReferrer(document.referrer) : 'direct';
  const utmSource = normalizeTrafficSource(utm.utm_source);
  const trafficSource = utmSource || (referrerKind === 'internal' ? '' : referrerKind) || readFirstTouch()?.first_traffic_source || referrerKind || 'direct';
  const firstTouch = getFirstTouch({ entryUrl, rawReferrer, referrerKind, utm });

  return {
    route: window.location.pathname + window.location.search,
    page: window.location.pathname,
    title: typeof document !== 'undefined' ? document.title : undefined,
    raw_referrer: rawReferrer,
    referrer_kind: utmSource ? `utm:${utmSource}` : referrerKind,
    traffic_source: trafficSource,
    entry_url: entryUrl,
    first_seen_at: firstTouch.first_seen_at,
    first_entry_url: firstTouch.first_entry_url,
    first_referrer_kind: firstTouch.first_referrer_kind,
    first_raw_referrer: firstTouch.first_raw_referrer,
    first_utm_source: firstTouch.first_utm_source,
    first_utm_medium: firstTouch.first_utm_medium,
    first_utm_campaign: firstTouch.first_utm_campaign,
    first_traffic_source: firstTouch.first_traffic_source,
    language: nav.language,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    browser_family: browserFamily(nav.userAgent || ''),
    viewport_width: window.innerWidth,
    viewport_height: window.innerHeight,
    screen_width: window.screen?.width,
    screen_height: window.screen?.height,
    device_pixel_ratio: window.devicePixelRatio,
    source: 'frontend',
    ...utm,
  };
}

function sanitizePayload(payload: UsagePayload): UsagePayload {
  const blocked = new Set([
    'password',
    'token',
    'secret',
    'api_key',
    'authorization',
    'cookie',
    'document_text',
    'raw_text',
    'prompt',
    'output_text',
    'content',
  ]);
  const out: UsagePayload = {};
  for (const [key, value] of Object.entries(payload || {})) {
    const normalized = key.toLowerCase();
    if (blocked.has(normalized) || normalized.includes('password') || normalized.includes('secret') || normalized.includes('token')) continue;
    if (typeof value === 'string' && value.length > 1000) {
      out[key] = `${value.slice(0, 1000)}…`;
    } else if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'string' || value === null || value === undefined) {
      out[key] = value;
    } else if (Array.isArray(value)) {
      out[key] = value.slice(0, 20).map((item) => (typeof item === 'string' || typeof item === 'number' || typeof item === 'boolean' ? item : String(item).slice(0, 200)));
    } else {
      try {
        out[key] = JSON.parse(JSON.stringify(value)).toString?.() ? value : JSON.stringify(value).slice(0, 1000);
      } catch {
        out[key] = String(value).slice(0, 1000);
      }
    }
  }
  return out;
}

export function trackUsageEvent(event: string, payload: UsagePayload = {}, options: { beacon?: boolean } = {}) {
  if (typeof window === 'undefined') return;
  const name = safeString(event);
  if (!name) return;

  const body = JSON.stringify(sanitizePayload({
    ...clientContext(),
    ...payload,
    event: name,
    client_ts: new Date().toISOString(),
  }));

  const url = `${PRODUCT_API_BASE_URL}/api/product/usage-event`;

  if (options.beacon && typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
    try {
      const ok = navigator.sendBeacon(url, new Blob([body], { type: 'application/json' }));
      if (ok) return;
    } catch {
      // fall back to fetch
    }
  }

  void fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
    credentials: 'include',
    keepalive: body.length < 60_000,
  }).catch(() => {
    // telemetry must never break the product
  });
}

export function workflowCompletionEvent(response: any): string {
  const status = String(response?.status || response?.result?.status || '').toLowerCase();
  const result = response?.result || response || {};
  const summary = result?.summary || result?.view || {};
  const findingCount = Number(
    result?.finding_count ??
    result?.findings_count ??
    summary?.finding_count ??
    summary?.findings_count ??
    (Array.isArray(result?.findings) ? result.findings.length : 0),
  );
  const warningCount = Number(
    result?.warning_count ??
    result?.warnings_count ??
    (Array.isArray(result?.warnings) ? result.warnings.length : 0),
  );

  if (WORKFLOW_FAILED_STATUSES.has(status)) return 'workflow_failed';
  if (WORKFLOW_WARNING_STATUSES.has(status) || warningCount > 0) return 'workflow_warning_result';
  if (findingCount === 0 && !WORKFLOW_COMPLETED_STATUSES.has(status)) return 'workflow_empty_result';
  return 'workflow_completed';
}

export function summarizeWorkflowResponse(response: any): UsagePayload {
  const result = response?.result || response || {};
  const view = result?.view || {};
  const workflow = safeString(result?.workflow_id || response?.workflow_id || response?.workflow);
  const status = safeString(response?.status || result?.status);
  const findingCount = Number(
    result?.finding_count ??
    result?.findings_count ??
    view?.finding_count ??
    view?.findings_count ??
    (Array.isArray(result?.findings) ? result.findings.length : 0),
  );
  const warningCount = Number(
    result?.warning_count ??
    result?.warnings_count ??
    (Array.isArray(result?.warnings) ? result.warnings.length : 0),
  );
  const artifactCount = Array.isArray(result?.artifacts) ? result.artifacts.length : undefined;

  return {
    workflow,
    status,
    result_status: status,
    finding_count: Number.isFinite(findingCount) ? findingCount : undefined,
    warning_count: Number.isFinite(warningCount) ? warningCount : undefined,
    artifact_count: artifactCount,
    run_id: safeString(result?.run_id || response?.run_id),
  };
}

export function trackWorkflowFailure(workflow: string | undefined, error: unknown, durationMs?: number) {
  trackUsageEvent('workflow_failed', {
    workflow,
    duration_ms: durationMs,
    error_kind: error instanceof Error ? error.name || error.message : 'unknown',
    error_message: error instanceof Error ? error.message.slice(0, 500) : undefined,
  });
}
