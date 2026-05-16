import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Clock,
  Copy,
  Database,
  Download,
  Eye,
  Filter,
  Globe2,
  MousePointerClick,
  RefreshCcw,
  Search,
  ShieldCheck,
  Sparkles,
  Table2,
  Timer,
  Users,
  Workflow,
  X,
} from 'lucide-react';

type UsageEvent = Record<string, any>;

type UsageSummaryPayload = {
  ok?: boolean;
  error?: string;
  read_scope?: string;
  windows?: Record<string, any>;
  top_pages?: Array<Record<string, any>>;
  top_workflows?: Array<Record<string, any>>;
  top_countries?: Array<Record<string, any>>;
  top_events?: Array<Record<string, any>>;
  sessions?: Array<Record<string, any>>;
  [key: string]: any;
};

type RawEventsPayload = {
  ok?: boolean;
  error?: string;
  count?: number;
  events?: UsageEvent[];
};

const QUALIFIED_EVENTS = new Set([
  'landing_scroll_50',
  'landing_scroll_75',
  'landing_scroll_100',
  'landing_cta_open_app_clicked',
  'open_app_clicked',
  'app_opened',
  'page_viewed',
  'workflow_page_viewed',
  'workflow_started',
  'trello_preview_opened',
  'notion_preview_opened',
  'deck_export_requested',
  'deck_download_clicked',
  'meet_danyel_opened',
  'meet_danyel_clicked',
  'ui_clicked',
]);

const STRONG_USAGE_EVENTS = new Set([
  'workflow_started',
  'workflow_completed',
  'workflow_warning_result',
  'workflow_failed',
  'workflow_empty_result',
  'trello_preview_opened',
  'trello_preview_completed',
  'notion_preview_opened',
  'notion_preview_completed',
  'deck_export_requested',
  'deck_export_completed',
  'deck_download_clicked',
]);

const EVENT_GROUPS: Record<string, string> = {
  landing_viewed: 'Landing',
  landing_scroll_25: 'Landing',
  landing_scroll_50: 'Landing',
  landing_scroll_75: 'Landing',
  landing_scroll_100: 'Landing',
  landing_cta_open_app_clicked: 'Landing',
  landing_meet_danyel_clicked: 'Landing',
  meet_danyel_opened: 'Contact',
  meet_danyel_clicked: 'Contact',
  meet_danyel_link_clicked: 'Contact',
  app_opened: 'Navigation',
  page_viewed: 'Navigation',
  page_left: 'Navigation',
  page_time_spent: 'Navigation',
  ui_clicked: 'Click',
  topbar_nav_clicked: 'Navigation',
  workflow_page_viewed: 'Workflow',
  workflow_started: 'Workflow',
  workflow_completed: 'Workflow',
  workflow_warning_result: 'Workflow',
  workflow_empty_result: 'Workflow',
  workflow_failed: 'Workflow',
  workflow_result_viewed: 'Workflow',
  workflow_tab_changed: 'Workflow',
  trello_preview_opened: 'Trello',
  trello_preview_completed: 'Trello',
  trello_open_current_page_clicked: 'Trello',
  trello_publish_attempted: 'Trello',
  trello_publish_blocked_public: 'Trello',
  trello_publish_completed_admin: 'Trello',
  notion_preview_opened: 'Notion',
  notion_preview_completed: 'Notion',
  notion_open_current_page_clicked: 'Notion',
  notion_publish_attempted: 'Notion',
  notion_publish_blocked_public: 'Notion',
  notion_publish_completed_admin: 'Notion',
  deck_export_requested: 'Deck',
  deck_export_completed: 'Deck',
  deck_export_failed: 'Deck',
  deck_download_clicked: 'Deck',
  ai_lab_opened: 'AI Lab',
  runtime_controls_opened: 'Runtime',
  preferences_opened: 'Preferences',
  documents_opened: 'Documents',
  run_history_opened: 'Run History',
  observability_opened: 'Observability',
  api_error_seen: 'Error',
  timeout_seen: 'Error',
  cloudflare_524_seen: 'Error',
  workflow_polling_failed: 'Error',
  empty_state_seen: 'Error',
  admin_only_gate_seen: 'Access',
};

const RANGE_OPTIONS = [
  { value: '24h', label: 'Last 24h' },
  { value: '7d', label: 'Last 7d' },
  { value: '30d', label: 'Last 30d' },
  { value: 'all', label: 'All time' },
];

function asString(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return '';
}

function eventDetails(event: UsageEvent): Record<string, any> {
  const details = event.details;
  if (details && typeof details === 'object' && !Array.isArray(details)) {
    return details as Record<string, any>;
  }
  return {};
}

function firstText(...values: unknown[]): string {
  for (const value of values) {
    const text = asString(value);
    if (text) return text;
  }
  return '';
}

function firstNumber(...values: unknown[]): number {
  for (const value of values) {
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    if (typeof value === 'string' && value.trim()) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) return parsed;
    }
  }
  return 0;
}

function extractUtmSourceFromText(...values: unknown[]): string {
  for (const value of values) {
    const text = asString(value);
    if (!text) continue;
    try {
      const query = text.includes('?') ? text.split('?').slice(1).join('?') : text.startsWith('utm_') ? text : '';
      if (!query) continue;
      const params = new URLSearchParams(query);
      const source = params.get('utm_source');
      if (source) return source.trim().toLowerCase();
    } catch {
      // ignore malformed URL/query
    }
  }
  return '';
}

function normalizeSource(value: unknown): string {
  const raw = asString(value).trim().toLowerCase();
  if (!raw) return '';
  if (raw === '127.0.0.1:5173' || raw === 'localhost' || raw.includes('localhost') || raw.includes('127.0.0.1')) return 'internal';
  if (raw.includes('linkedin') || raw === 'li') return 'linkedin';
  if (raw.includes('github')) return 'github';
  if (raw.includes('google')) return 'google';
  if (raw.includes('bing')) return 'bing';
  if (raw.includes('whatsapp')) return 'whatsapp';
  if (raw.includes('twitter') || raw.includes('x.com')) return 'twitter';
  if (raw.includes('mail') || raw.includes('email')) return 'email';
  if (raw.includes('danyel-lambert.com') || raw.includes('axiovance')) return 'internal';
  return raw.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0] || raw;
}

function inferWorkflowFromPage(value: unknown): string {
  const page = asString(value);
  const match = page.match(/\/app\/workflows\/([^/?#]+)/);
  return match?.[1] || '';
}

function cleanPageForDisplay(value: unknown): string {
  const page = asString(value);
  if (!page) return '';
  const [pathPart, query] = page.split('?');
  if (!query) return page;

  const params = new URLSearchParams(query);
  for (const key of Array.from(params.keys())) {
    if (key.startsWith('utm_')) params.delete(key);
  }

  const remaining = params.toString();
  return remaining ? `${pathPart || '/'}?${remaining}` : (pathPart || '/');
}

function eventName(event: UsageEvent): string {
  return asString(event.event || event.name || event.type || 'unknown');
}

function eventGroup(event: UsageEvent): string {
  const explicit = asString(event.event_group || event.group || event.category || event.event_category);
  if (explicit) return titleCase(explicit);
  const name = eventName(event);
  return EVENT_GROUPS[name] || titleCase(name.split('_')[0] || 'Other');
}

function titleCase(value: string): string {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\w\S*/g, (word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase());
}

function eventTs(event: UsageEvent): Date | null {
  const raw = event.ts || event.timestamp || event.created_at || event.time;
  if (!raw) return null;
  const date = new Date(raw);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatTs(value: unknown): string {
  if (!value) return '—';
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function formatDuration(ms: unknown): string {
  const n = typeof ms === 'number' ? ms : Number(ms || 0);
  if (!Number.isFinite(n) || n <= 0) return '—';
  if (n < 1000) return `${Math.round(n)}ms`;
  if (n < 60_000) return `${Math.round(n / 1000)}s`;
  const minutes = Math.floor(n / 60_000);
  const seconds = Math.round((n % 60_000) / 1000);
  return `${minutes}m ${seconds}s`;
}

function eventDurationMs(event: UsageEvent): number {
  const details = eventDetails(event);
  return firstNumber(
    details.duration_ms,
    details.elapsed_ms,
    event.duration_ms,
    event.elapsed_ms,
  );
}

function eventPage(event: UsageEvent): string {
  const details = eventDetails(event);
  const page = firstText(
    details.page,
    details.route,
    details.path,
    details.pathname,
    event.page,
    event.route,
    event.path,
    event.pathname,
    'unknown',
  ) || 'unknown';
  return cleanPageForDisplay(page);
}

function eventRoute(event: UsageEvent): string {
  const details = eventDetails(event);
  return firstText(
    details.route,
    event.route,
    details.page,
    event.page,
    details.path,
    event.path,
  );
}

function eventButtonLabel(event: UsageEvent): string {
  const details = eventDetails(event);
  return firstText(
    details.button_label,
    details.button_id,
    details.label,
    details.text,
    event.button_label,
    event.button_id,
    event.label,
    event.text,
  );
}

function eventContext(event: UsageEvent): string {
  const details = eventDetails(event);
  const tokens: string[] = [];

  const route = eventRoute(event);
  const query = route.includes('?') ? route.split('?').slice(1).join('?') : '';
  if (query) {
    try {
      const params = new URLSearchParams(query);
      const tour = params.get('tour');
      const utmSource = params.get('utm_source');
      const utmMedium = params.get('utm_medium');
      const utmCampaign = params.get('utm_campaign');

      if (tour) tokens.push(`tour=${tour}`);
      if (utmSource) tokens.push(`utm=${utmSource}`);
      if (utmMedium) tokens.push(`medium=${utmMedium}`);
      if (utmCampaign) tokens.push(`campaign=${utmCampaign}`);
    } catch {
      tokens.push(query.slice(0, 80));
    }
  }

  const button = eventButtonLabel(event);
  if (button) tokens.push(`button=${button}`);

  const scroll = firstText(details.scroll_depth, event.scroll_depth);
  if (scroll) tokens.push(`scroll=${scroll}%`);

  const href = firstText(details.href, event.href);
  if (href) {
    try {
      const url = new URL(href);
      tokens.push(`href=${url.pathname}`);
    } catch {
      tokens.push(`href=${href.slice(0, 60)}`);
    }
  }

  const target = firstText(details.link_target, details.target, event.link_target, event.target);
  if (target) tokens.push(`target=${target}`);

  return tokens.length ? tokens.slice(0, 5).join(' · ') : '—';
}

function shortOption(value: string, maxLength = 72): string {
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength - 1)}…`;
}

function isMeetDanyelClick(event: UsageEvent): boolean {
  const name = eventName(event);
  if (name.includes('meet_danyel') || name === 'landing_meet_danyel_clicked') return true;
  if (name !== 'ui_clicked') return false;
  const label = eventButtonLabel(event).toLowerCase();
  return label.includes('meet danyel') || label.includes('danyel lambert');
}

function eventWorkflow(event: UsageEvent): string {
  const details = eventDetails(event);
  const explicit = firstText(
    details.workflow,
    details.workflow_id,
    details.workflowId,
    event.workflow,
    event.workflow_id,
    event.workflowId,
  );
  return explicit || inferWorkflowFromPage(firstText(details.page, details.route, event.page, event.route));
}

function eventCountry(event: UsageEvent): string {
  return asString(event.country || event.cf_country || event.country_code || 'unknown') || 'unknown';
}

function eventReferrer(event: UsageEvent): string {
  const details = eventDetails(event);
  const utm = firstText(
    details.utm_source,
    event.utm_source,
    extractUtmSourceFromText(details.page, details.route, details.entry_url, event.page, event.route),
  );
  const traffic = firstText(details.traffic_source, event.traffic_source);
  const firstTouch = firstText(
    details.first_traffic_source,
    event.first_traffic_source,
    details.first_utm_source,
    event.first_utm_source,
    details.first_referrer_kind,
    event.first_referrer_kind,
  );

  const normalizedTraffic = normalizeSource(traffic);
  const normalizedFirstTouch = normalizeSource(firstTouch);

  if (utm) return `utm:${normalizeSource(utm)}`;

  // If the current event is internal navigation but the session entered
  // through a known external/UTM source, keep the original source.
  if (normalizedTraffic && normalizedTraffic !== 'internal' && normalizedTraffic !== 'direct') {
    return normalizedTraffic;
  }
  if (normalizedFirstTouch && normalizedFirstTouch !== 'internal' && normalizedFirstTouch !== 'direct') {
    return normalizedFirstTouch;
  }
  if (normalizedTraffic) return normalizedTraffic;

  return normalizeSource(firstText(
    details.referrer_kind,
    event.referrer_kind,
    details.referrer,
    event.referrer,
    details.raw_referrer,
    event.raw_referrer,
    'direct',
  )) || 'direct';
}

function eventSession(event: UsageEvent): string {
  return asString(event.session_hash || event.session_id_hash || event.session || 'unknown') || 'unknown';
}

function eventStatus(event: UsageEvent): string {
  const details = eventDetails(event);
  return firstText(
    details.status,
    details.result_status,
    details.outcome,
    event.status,
    event.result_status,
    event.outcome,
  );
}

function shortSession(value: string): string {
  if (!value || value === 'unknown') return 'unknown';
  if (value.length <= 14) return value;
  return `${value.slice(0, 8)}…${value.slice(-6)}`;
}

function countBy(events: UsageEvent[], getter: (event: UsageEvent) => string): Array<{ key: string; count: number }> {
  const map = new Map<string, number>();
  for (const event of events) {
    const key = getter(event) || 'unknown';
    map.set(key, (map.get(key) || 0) + 1);
  }
  return [...map.entries()]
    .map(([key, count]) => ({ key, count }))
    .sort((a, b) => b.count - a.count || a.key.localeCompare(b.key));
}

function uniq(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b));
}

function csvEscape(value: unknown): string {
  const str = value === null || value === undefined ? '' : String(value);
  if (/[",\n\r]/.test(str)) return `"${str.replace(/"/g, '""')}"`;
  return str;
}

function downloadText(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function getDetails(event: UsageEvent): Record<string, unknown> {
  const hidden = new Set([
    'ts',
    'timestamp',
    'created_at',
    'event',
    'name',
    'type',
    'session_hash',
    'session_id_hash',
    'country',
    'cf_country',
    'country_code',
    'role',
    'user_agent_family',
    'referrer_kind',
  ]);
  const out: Record<string, unknown> = {
    normalized: {
      page: eventPage(event),
      workflow: eventWorkflow(event),
      status: eventStatus(event),
      duration_ms: eventDurationMs(event),
      referrer: eventReferrer(event),
      country: eventCountry(event),
    },
  };
  for (const [key, value] of Object.entries(event)) {
    if (!hidden.has(key)) out[key] = value;
  }
  return out;
}

function matchesRange(event: UsageEvent, range: string): boolean {
  if (range === 'all') return true;
  const date = eventTs(event);
  if (!date) return true;
  const now = Date.now();
  const age = now - date.getTime();
  if (range === '24h') return age <= 24 * 60 * 60 * 1000;
  if (range === '7d') return age <= 7 * 24 * 60 * 60 * 1000;
  if (range === '30d') return age <= 30 * 24 * 60 * 60 * 1000;
  return true;
}

function isQualifiedSession(events: UsageEvent[]): boolean {
  return events.some((event) => QUALIFIED_EVENTS.has(eventName(event)));
}

function isStrongSession(events: UsageEvent[]): boolean {
  return events.some((event) => STRONG_USAGE_EVENTS.has(eventName(event)));
}

function buildSessionRows(events: UsageEvent[]) {
  const map = new Map<string, UsageEvent[]>();
  for (const event of events) {
    const session = eventSession(event);
    if (!map.has(session)) map.set(session, []);
    map.get(session)!.push(event);
  }

  return [...map.entries()]
    .map(([session, sessionEvents]) => {
      const dates = sessionEvents
        .map(eventTs)
        .filter((date): date is Date => Boolean(date))
        .sort((a, b) => a.getTime() - b.getTime());
      const first = dates[0] || null;
      const last = dates[dates.length - 1] || null;
      const pages = uniq(sessionEvents.map(eventPage)).filter((page) => page !== 'unknown');
      const workflows = uniq(sessionEvents.map(eventWorkflow)).filter(Boolean);
      const countries = uniq(sessionEvents.map(eventCountry)).filter((item) => item !== 'unknown');
      const referrers = uniq(sessionEvents.map(eventReferrer)).filter(Boolean);
      const totalDuration = sessionEvents.reduce((sum, event) => sum + eventDurationMs(event), 0);
      return {
        session,
        events: sessionEvents.length,
        first,
        last,
        pages,
        workflows,
        countries,
        referrers,
        totalDuration,
        qualified: isQualifiedSession(sessionEvents),
        strong: isStrongSession(sessionEvents),
        raw: sessionEvents,
      };
    })
    .sort((a, b) => (b.last?.getTime() || 0) - (a.last?.getTime() || 0));
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { credentials: 'include' });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload?.error || payload?.message || `Request failed: ${response.status}`;
    throw new Error(message);
  }
  return payload as T;
}

function StatCard({
  icon: Icon,
  label,
  value,
  detail,
}: {
  icon: any;
  label: string;
  value: string | number;
  detail?: string;
}) {
  return (
    <div className="rounded-2xl border border-border/60 bg-card/80 p-4 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
          <p className="mt-2 text-2xl font-semibold text-foreground">{value}</p>
          {detail ? <p className="mt-1 text-xs text-muted-foreground">{detail}</p> : null}
        </div>
        <div className="rounded-xl border border-border/60 bg-secondary/40 p-2 text-muted-foreground">
          <Icon className="h-4 w-4" />
        </div>
      </div>
    </div>
  );
}

function BarList({ title, items, empty = 'No data yet' }: { title: string; items: Array<{ key: string; count: number }>; empty?: string }) {
  const max = Math.max(1, ...items.map((item) => item.count));
  return (
    <div className="rounded-2xl border border-border/60 bg-card/80 p-4">
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      <div className="mt-4 space-y-3">
        {items.length === 0 ? <p className="text-sm text-muted-foreground">{empty}</p> : null}
        {items.slice(0, 10).map((item) => (
          <div key={item.key}>
            <div className="mb-1 flex items-center justify-between gap-3 text-xs">
              <span className="truncate text-muted-foreground">{item.key || 'unknown'}</span>
              <span className="font-medium text-foreground">{item.count}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-secondary">
              <div className="h-full rounded-full bg-primary" style={{ width: `${Math.max(4, (item.count / max) * 100)}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

type SelectOption = string | { value: string; label: string };

function optionValue(option: SelectOption): string {
  return typeof option === 'string' ? option : option.value;
}

function optionLabel(option: SelectOption): string {
  return typeof option === 'string' ? option : option.label;
}

function SelectFilter({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
}) {
  return (
    <label className="space-y-1 text-xs text-muted-foreground">
      <span>{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground outline-none"
      >
        <option value="">All</option>
        {options.map((option) => {
          const value = optionValue(option);
          const label = optionLabel(option);
          return (
            <option key={value} value={value}>
              {label}
            </option>
          );
        })}
      </select>
    </label>
  );
}

export default function AdminUsagePage() {
  const [summary, setSummary] = useState<UsageSummaryPayload | null>(null);
  const [events, setEvents] = useState<UsageEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [accessDenied, setAccessDenied] = useState(false);
  const [showRaw, setShowRaw] = useState(true);
  const [selectedSession, setSelectedSession] = useState<string>('');
  const [expandedEvent, setExpandedEvent] = useState<number | null>(null);

  const [query, setQuery] = useState('');
  const [range, setRange] = useState('7d');
  const [eventFilter, setEventFilter] = useState('');
  const [groupFilter, setGroupFilter] = useState('');
  const [countryFilter, setCountryFilter] = useState('');
  const [workflowFilter, setWorkflowFilter] = useState('');
  const [pageFilter, setPageFilter] = useState('');
  const [referrerFilter, setReferrerFilter] = useState('');
  const [buttonFilter, setButtonFilter] = useState('');
  const [contextQuery, setContextQuery] = useState('');
  const [sessionFilter, setSessionFilter] = useState('');
  const [clicksOnly, setClicksOnly] = useState(false);
  const [qualifiedOnly, setQualifiedOnly] = useState(false);
  const [strongOnly, setStrongOnly] = useState(false);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [summaryPayload, eventsPayload] = await Promise.all([
        fetchJson<UsageSummaryPayload>('/api/product/usage-summary?limit=10000&range=all'),
        fetchJson<RawEventsPayload>('/api/product/usage-events?limit=10000&range=all'),
      ]);
      setSummary(summaryPayload);
      setEvents(Array.isArray(eventsPayload.events) ? eventsPayload.events : []);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      if (message.toLowerCase().includes('admin access') || message.toLowerCase().includes('admin')) {
        setAccessDenied(true);
        setError(null);
      } else {
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  const sessionRowsAll = useMemo(() => buildSessionRows(events), [events]);
  const sessionMap = useMemo(() => {
    const map = new Map<string, ReturnType<typeof buildSessionRows>[number]>();
    for (const row of sessionRowsAll) map.set(row.session, row);
    return map;
  }, [sessionRowsAll]);

  const sourceBySession = useMemo(() => {
    const score = (source: string) => {
      const normalized = normalizeSource(source);
      if (!normalized || normalized === 'unknown') return 0;
      if (normalized === 'internal') return 1;
      if (normalized === 'direct') return 2;
      if (normalized.startsWith('utm:')) return 5;
      return 4;
    };

    const map = new Map<string, string>();

    for (const event of [...events].sort((a, b) => (eventTs(a)?.getTime() || 0) - (eventTs(b)?.getTime() || 0))) {
      const session = eventSession(event);
      const source = eventReferrer(event);
      const current = map.get(session) || '';

      if (!current || score(source) > score(current)) {
        map.set(session, source);
      }
    }

    return map;
  }, [events]);

  const displayReferrer = (event: UsageEvent): string => {
    const own = eventReferrer(event);
    const sessionSource = sourceBySession.get(eventSession(event));

    if (sessionSource) {
      const normalized = normalizeSource(sessionSource);
      if (normalized && normalized !== 'internal' && normalized !== 'direct') {
        return sessionSource;
      }
    }

    return own;
  };

  const facets = useMemo(() => {
    return {
      events: uniq(events.map(eventName)),
      groups: uniq(events.map(eventGroup)),
      countries: uniq(events.map(eventCountry)),
      workflows: uniq(events.map(eventWorkflow)).filter(Boolean),
      pages: uniq(events.map(eventPage)),
      referrers: uniq(events.map(displayReferrer)),
      buttons: uniq(events.map(eventButtonLabel)).filter(Boolean),
      contexts: uniq(events.map(eventContext)).filter((context) => context !== '—'),
      sessions: uniq(events.map(eventSession)),
    };
  }, [events]);

  const filteredEvents = useMemo(() => {
    const q = query.trim().toLowerCase();
    const contextQ = contextQuery.trim().toLowerCase();
    return events.filter((event) => {
      if (!matchesRange(event, range)) return false;
      if (eventFilter && eventName(event) !== eventFilter) return false;
      if (groupFilter && eventGroup(event) !== groupFilter) return false;
      if (countryFilter && eventCountry(event) !== countryFilter) return false;
      if (workflowFilter && eventWorkflow(event) !== workflowFilter) return false;
      if (pageFilter && eventPage(event) !== pageFilter) return false;
      if (referrerFilter && displayReferrer(event) !== referrerFilter) return false;
      if (buttonFilter && eventButtonLabel(event) !== buttonFilter) return false;
      if (sessionFilter && eventSession(event) !== sessionFilter) return false;

      const context = eventContext(event).toLowerCase();
      if (contextQ && !context.includes(contextQ)) return false;
      if (clicksOnly && eventName(event) !== 'ui_clicked' && !eventButtonLabel(event)) return false;

      const session = sessionMap.get(eventSession(event));
      if (qualifiedOnly && !session?.qualified) return false;
      if (strongOnly && !session?.strong) return false;

      if (!q) return true;
      const haystack = `${eventName(event)} ${eventGroup(event)} ${eventPage(event)} ${eventContext(event)} ${displayReferrer(event)} ${JSON.stringify(event)}`.toLowerCase();
      return haystack.includes(q);
    });
  }, [
    events,
    range,
    eventFilter,
    groupFilter,
    countryFilter,
    workflowFilter,
    pageFilter,
    referrerFilter,
    buttonFilter,
    contextQuery,
    sessionFilter,
    clicksOnly,
    qualifiedOnly,
    strongOnly,
    query,
    sessionMap,
  ]);

  const sessionRows = useMemo(() => buildSessionRows(filteredEvents), [filteredEvents]);

  const selectedSessionRow = useMemo(() => {
    if (!selectedSession) return null;
    return sessionRowsAll.find((row) => row.session === selectedSession) || null;
  }, [selectedSession, sessionRowsAll]);

  const metrics = useMemo(() => {
    const uniqueSessions = new Set(filteredEvents.map(eventSession));
    const qualifiedSessions = sessionRows.filter((row) => row.qualified).length;
    const strongSessions = sessionRows.filter((row) => row.strong).length;
    const countries = new Set(filteredEvents.map(eventCountry).filter((item) => item !== 'unknown'));
    const workflowStarts = filteredEvents.filter((event) => eventName(event) === 'workflow_started').length;
    const workflowCompleted = filteredEvents.filter((event) => eventName(event) === 'workflow_completed').length;
    const workflowFailed = filteredEvents.filter((event) => eventName(event) === 'workflow_failed').length;
    const emptyResults = filteredEvents.filter((event) => eventName(event) === 'workflow_empty_result').length;
    const meetClicks = filteredEvents.filter(isMeetDanyelClick).length;
    const previewClicks = filteredEvents.filter((event) => eventName(event).includes('preview')).length;
    const deckExports = filteredEvents.filter((event) => eventName(event).startsWith('deck_export')).length;
    const durations = filteredEvents.map((event) => eventDurationMs(event)).filter((value) => Number.isFinite(value) && value > 0);
    const avgDuration = durations.length ? durations.reduce((a, b) => a + b, 0) / durations.length : 0;

    return {
      events: filteredEvents.length,
      uniqueSessions: uniqueSessions.size,
      qualifiedSessions,
      strongSessions,
      countries: countries.size,
      workflowStarts,
      workflowCompleted,
      workflowFailed,
      emptyResults,
      meetClicks,
      previewClicks,
      deckExports,
      avgDuration,
    };
  }, [filteredEvents, sessionRows]);

  const topEvents = useMemo(() => countBy(filteredEvents, eventName), [filteredEvents]);
  const topGroups = useMemo(() => countBy(filteredEvents, eventGroup), [filteredEvents]);
  const topCountries = useMemo(() => countBy(filteredEvents, eventCountry), [filteredEvents]);
  const topPages = useMemo(() => countBy(filteredEvents, eventPage), [filteredEvents]);
  const topWorkflows = useMemo(() => countBy(filteredEvents.filter((event) => eventWorkflow(event)), eventWorkflow), [filteredEvents]);
  const topReferrers = useMemo(() => countBy(filteredEvents, displayReferrer), [filteredEvents, sourceBySession]);
  const topButtons = useMemo(() => countBy(filteredEvents.filter((event) => eventButtonLabel(event)), eventButtonLabel), [filteredEvents]);
  const topContexts = useMemo(() => countBy(filteredEvents.filter((event) => eventContext(event) !== '—'), eventContext), [filteredEvents]);

  const timelineEvents = useMemo(() => {
    return [...filteredEvents].sort((a, b) => {
      const da = eventTs(a)?.getTime() || 0;
      const db = eventTs(b)?.getTime() || 0;
      return db - da;
    });
  }, [filteredEvents]);

  const funnel = useMemo(() => {
    const names = filteredEvents.map(eventName);
    const count = (list: string[]) => names.filter((name) => list.includes(name)).length;
    return [
      { key: 'Landing viewed', count: count(['landing_viewed']) },
      { key: 'Scrolled 50%+', count: count(['landing_scroll_50', 'landing_scroll_75', 'landing_scroll_100']) },
      { key: 'Opened app / page', count: count(['open_app_clicked', 'app_opened', 'page_viewed']) },
      { key: 'Workflow page viewed', count: count(['workflow_page_viewed']) },
      { key: 'Workflow started', count: count(['workflow_started']) },
      { key: 'Workflow completed', count: count(['workflow_completed', 'workflow_warning_result']) },
      { key: 'Preview / deck', count: count(['trello_preview_opened', 'notion_preview_opened', 'deck_export_requested', 'deck_download_clicked']) },
      { key: 'Meet Danyel', count: filteredEvents.filter(isMeetDanyelClick).length },
    ];
  }, [filteredEvents]);

  function clearFilters() {
    setQuery('');
    setRange('7d');
    setEventFilter('');
    setGroupFilter('');
    setCountryFilter('');
    setWorkflowFilter('');
    setPageFilter('');
    setReferrerFilter('');
    setButtonFilter('');
    setContextQuery('');
    setSessionFilter('');
    setClicksOnly(false);
    setQualifiedOnly(false);
    setStrongOnly(false);
    setSelectedSession('');
  }

  function exportJson() {
    downloadText(
      `axiovance-usage-events-${new Date().toISOString().slice(0, 10)}.json`,
      JSON.stringify({ exported_at: new Date().toISOString(), filters: { query, range, eventFilter, groupFilter, countryFilter, workflowFilter, pageFilter, referrerFilter, buttonFilter, contextQuery, sessionFilter, clicksOnly, qualifiedOnly, strongOnly }, events: filteredEvents }, null, 2),
      'application/json;charset=utf-8',
    );
  }

  function exportCsv() {
    const columns = [
      'ts',
      'event',
      'group',
      'session_hash',
      'country',
      'page',
      'context',
      'workflow',
      'referrer',
      'status',
      'duration_ms',
      'source',
      'button_label',
      'utm_source',
      'utm_medium',
      'utm_campaign',
      'browser_family',
      'viewport_width',
      'viewport_height',
      'screen_width',
      'screen_height',
      'language',
      'timezone',
    ];

    const rows = filteredEvents.map((event) => {
      const details = eventDetails(event);
      return [
        asString(event.ts || event.timestamp),
        eventName(event),
        eventGroup(event),
        eventSession(event),
        eventCountry(event),
        eventPage(event),
        eventContext(event),
        eventWorkflow(event),
        displayReferrer(event),
        eventStatus(event),
        asString(eventDurationMs(event) || ''),
        asString(details.source || event.source),
        eventButtonLabel(event),
        asString(details.utm_source || event.utm_source),
        asString(details.utm_medium || event.utm_medium),
        asString(details.utm_campaign || event.utm_campaign),
        asString(details.browser_family || event.browser_family),
        asString(details.viewport_width || event.viewport_width),
        asString(details.viewport_height || event.viewport_height),
        asString(details.screen_width || event.screen_width),
        asString(details.screen_height || event.screen_height),
        asString(details.language || event.language),
        asString(details.timezone || event.timezone),
      ];
    });

    const csv = [columns.join(','), ...rows.map((row) => row.map(csvEscape).join(','))].join('\n');
    downloadText(`axiovance-usage-events-${new Date().toISOString().slice(0, 10)}.csv`, csv, 'text/csv;charset=utf-8');
  }

  async function copyRawJson() {
    await navigator.clipboard.writeText(JSON.stringify(filteredEvents, null, 2));
  }

  if (accessDenied) {
    return (
      <div className="min-h-screen bg-background text-foreground">
        <div className="mx-auto flex min-h-screen max-w-3xl items-center justify-center px-6">
          <div className="rounded-3xl border border-border/60 bg-card/80 p-8 text-center shadow-sm">
            <h1 className="text-2xl font-semibold">This page is not available.</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Return to the product workspace or sign in with an authorized admin session.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-8">
        <div className="flex flex-col justify-between gap-4 rounded-3xl border border-border/60 bg-card/80 p-6 shadow-sm lg:flex-row lg:items-center">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
              <ShieldCheck className="h-3.5 w-3.5" />
              Admin-only private analytics
            </div>
            <h1 className="text-3xl font-semibold tracking-tight">Public demo usage dashboard</h1>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              Track public product usage across landing, pages, workflows, previews, exports, sessions, countries, referrers and raw events.
              Admin sessions are ignored by the event endpoint.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void loadData()}
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2 text-sm font-medium hover:bg-secondary"
            >
              <RefreshCcw className="h-4 w-4" />
              Refresh
            </button>
            <button
              type="button"
              onClick={exportCsv}
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2 text-sm font-medium hover:bg-secondary"
            >
              <Download className="h-4 w-4" />
              Export CSV
            </button>
            <button
              type="button"
              onClick={exportJson}
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2 text-sm font-medium hover:bg-secondary"
            >
              <Download className="h-4 w-4" />
              Export JSON
            </button>
            <button
              type="button"
              onClick={() => void copyRawJson()}
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2 text-sm font-medium hover:bg-secondary"
            >
              <Copy className="h-4 w-4" />
              Copy raw
            </button>
          </div>
        </div>

        {error ? (
          <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
            <div className="flex items-center gap-2 font-semibold">
              <AlertTriangle className="h-4 w-4" />
              Could not load usage data
            </div>
            <p className="mt-1">{error}</p>
            <p className="mt-2 text-xs opacity-80">This page requires an active admin session.</p>
          </div>
        ) : null}

        <div className="rounded-3xl border border-border/60 bg-card/80 p-5 shadow-sm">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
            <Filter className="h-4 w-4" />
            Filters and search
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <label className="space-y-1 text-xs text-muted-foreground xl:col-span-2">
              <span>Search all raw fields</span>
              <div className="flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2">
                <Search className="h-4 w-4 text-muted-foreground" />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search event, page, workflow, referrer, UTM, button label..."
                  className="w-full bg-transparent text-sm text-foreground outline-none"
                />
              </div>
            </label>

            <label className="space-y-1 text-xs text-muted-foreground">
              <span>Range</span>
              <select value={range} onChange={(event) => setRange(event.target.value)} className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground outline-none">
                {RANGE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>

            <div className="flex items-end">
              <button
                type="button"
                onClick={clearFilters}
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-background px-3 py-2 text-sm font-medium hover:bg-secondary"
              >
                <X className="h-4 w-4" />
                Clear filters
              </button>
            </div>

            <SelectFilter label="Event" value={eventFilter} onChange={setEventFilter} options={facets.events} />
            <SelectFilter label="Event group" value={groupFilter} onChange={setGroupFilter} options={facets.groups} />
            <SelectFilter label="Country" value={countryFilter} onChange={setCountryFilter} options={facets.countries} />
            <SelectFilter label="Workflow" value={workflowFilter} onChange={setWorkflowFilter} options={facets.workflows} />
            <SelectFilter label="Page / route" value={pageFilter} onChange={setPageFilter} options={facets.pages} />
            <SelectFilter label="Referrer" value={referrerFilter} onChange={setReferrerFilter} options={facets.referrers} />
            <SelectFilter label="Button / CTA" value={buttonFilter} onChange={setButtonFilter} options={facets.buttons} />
            <label className="space-y-1 text-xs text-muted-foreground">
              <span>Context contains</span>
              <input
                value={contextQuery}
                onChange={(event) => setContextQuery(event.target.value)}
                placeholder="button=Meet, href=/cv, utm=google..."
                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground outline-none"
              />
            </label>
            <SelectFilter
              label="Session"
              value={sessionFilter}
              onChange={setSessionFilter}
              options={facets.sessions.map((session) => ({
                value: session,
                label: shortSession(session),
              }))}
            />

            <label className="flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2 text-sm">
              <input type="checkbox" checked={clicksOnly} onChange={(event) => setClicksOnly(event.target.checked)} />
              Button/link clicks only
            </label>
            <label className="flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2 text-sm">
              <input type="checkbox" checked={qualifiedOnly} onChange={(event) => setQualifiedOnly(event.target.checked)} />
              Qualified sessions only
            </label>
            <label className="flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2 text-sm">
              <input type="checkbox" checked={strongOnly} onChange={(event) => setStrongOnly(event.target.checked)} />
              Strong usage only
            </label>
          </div>

          <div className="mt-4 text-xs text-muted-foreground">
            Showing <span className="font-medium text-foreground">{filteredEvents.length}</span> of <span className="font-medium text-foreground">{events.length}</span> raw events.
            {summary?.read_scope ? <span> Scope: {summary.read_scope}.</span> : null}
            {buttonFilter ? <span> Button: {buttonFilter}.</span> : null}
            {contextQuery ? <span> Context contains: {contextQuery}.</span> : null}
          </div>
        </div>

        {loading ? (
          <div className="rounded-2xl border border-border/60 bg-card/80 p-8 text-center text-sm text-muted-foreground">
            Loading usage analytics...
          </div>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard icon={Database} label="Raw events" value={metrics.events} detail={`${events.length} total loaded`} />
          <StatCard icon={Users} label="Unique sessions" value={metrics.uniqueSessions} detail={`${metrics.qualifiedSessions} qualified`} />
          <StatCard icon={Sparkles} label="Strong usage" value={metrics.strongSessions} detail="Workflow/export/preview activity" />
          <StatCard icon={Globe2} label="Countries" value={metrics.countries} detail="From Cloudflare country header when available" />
          <StatCard icon={Workflow} label="Workflow starts" value={metrics.workflowStarts} detail={`${metrics.workflowCompleted} completed`} />
          <StatCard icon={AlertTriangle} label="Failures / empty" value={`${metrics.workflowFailed}/${metrics.emptyResults}`} detail="Failed and empty workflow results" />
          <StatCard icon={MousePointerClick} label="Previews / Meet" value={`${metrics.previewClicks}/${metrics.meetClicks}`} detail="Trello/Notion previews and contact intent" />
          <StatCard icon={Timer} label="Avg duration" value={formatDuration(metrics.avgDuration)} detail={`${metrics.deckExports} deck export events`} />
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <BarList title="Product funnel" items={funnel} />
          <BarList title="Top event groups" items={topGroups} />
          <BarList title="Top events" items={topEvents} />
          <BarList title="Top countries" items={topCountries} />
          <BarList title="Top pages" items={topPages} />
          <BarList title="Top workflows" items={topWorkflows} />
          <BarList title="Top referrers / sources" items={topReferrers} />
          <BarList title="Top buttons / CTAs" items={topButtons} />
          <BarList title="Top contexts" items={topContexts.map((item) => ({ ...item, key: shortOption(item.key) }))} />
        </div>

        <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-3xl border border-border/60 bg-card/80 p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Sessions</h2>
                <p className="text-sm text-muted-foreground">Click a session to inspect the full journey.</p>
              </div>
              <Users className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="max-h-[520px] overflow-auto rounded-2xl border border-border/60">
              <table className="w-full min-w-[860px] text-left text-xs">
                <thead className="sticky top-0 bg-secondary text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">Session</th>
                    <th className="px-3 py-2">Country</th>
                    <th className="px-3 py-2">Events</th>
                    <th className="px-3 py-2">Pages</th>
                    <th className="px-3 py-2">Workflows</th>
                    <th className="px-3 py-2">Duration</th>
                    <th className="px-3 py-2">Qualified</th>
                    <th className="px-3 py-2">Strong</th>
                    <th className="px-3 py-2">Last seen</th>
                  </tr>
                </thead>
                <tbody>
                  {sessionRows.map((row) => (
                    <tr
                      key={row.session}
                      onClick={() => setSelectedSession(row.session)}
                      className="cursor-pointer border-t border-border/50 hover:bg-secondary/50"
                    >
                      <td className="px-3 py-2 font-mono text-[11px]">{shortSession(row.session)}</td>
                      <td className="px-3 py-2">{row.countries.join(', ') || 'unknown'}</td>
                      <td className="px-3 py-2">{row.events}</td>
                      <td className="px-3 py-2">{row.pages.length}</td>
                      <td className="px-3 py-2">{row.workflows.join(', ') || '—'}</td>
                      <td className="px-3 py-2">{formatDuration(row.totalDuration)}</td>
                      <td className="px-3 py-2">{row.qualified ? 'yes' : 'no'}</td>
                      <td className="px-3 py-2">{row.strong ? 'yes' : 'no'}</td>
                      <td className="px-3 py-2">{formatTs(row.last?.toISOString())}</td>
                    </tr>
                  ))}
                  {sessionRows.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="px-3 py-8 text-center text-muted-foreground">No sessions match the current filters.</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-3xl border border-border/60 bg-card/80 p-5">
            <div className="mb-4 flex items-center gap-2">
              <Eye className="h-5 w-5 text-muted-foreground" />
              <div>
                <h2 className="text-lg font-semibold">Session drilldown</h2>
                <p className="text-sm text-muted-foreground">Raw journey for a selected session.</p>
              </div>
            </div>

            {!selectedSessionRow ? (
              <div className="rounded-2xl border border-dashed border-border p-6 text-sm text-muted-foreground">
                Select a session from the table.
              </div>
            ) : (
              <div className="space-y-4">
                <div className="rounded-2xl border border-border/60 bg-background p-3 text-xs">
                  <div className="font-mono text-foreground">{selectedSessionRow.session}</div>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-muted-foreground">
                    <span>Events: {selectedSessionRow.events}</span>
                    <span>Pages: {selectedSessionRow.pages.length}</span>
                    <span>Country: {selectedSessionRow.countries.join(', ') || 'unknown'}</span>
                    <span>Duration: {formatDuration(selectedSessionRow.totalDuration)}</span>
                  </div>
                </div>

                <div className="max-h-[430px] space-y-3 overflow-auto pr-1">
                  {[...selectedSessionRow.raw]
                    .sort((a, b) => (eventTs(a)?.getTime() || 0) - (eventTs(b)?.getTime() || 0))
                    .map((event, index) => (
                      <div key={`${eventName(event)}-${index}`} className="rounded-2xl border border-border/60 bg-background p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="text-sm font-semibold">{eventName(event)}</div>
                            <div className="text-xs text-muted-foreground">{eventPage(event)}</div>
                          </div>
                          <div className="text-right text-xs text-muted-foreground">{formatTs(event.ts || event.timestamp)}</div>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                          <span className="rounded-full bg-secondary px-2 py-1">{eventGroup(event)}</span>
                          {eventWorkflow(event) ? <span className="rounded-full bg-secondary px-2 py-1">{eventWorkflow(event)}</span> : null}
                          {eventDurationMs(event) ? <span className="rounded-full bg-secondary px-2 py-1">{formatDuration(eventDurationMs(event))}</span> : null}
                          {eventStatus(event) ? <span className="rounded-full bg-secondary px-2 py-1">{eventStatus(event)}</span> : null}
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="rounded-3xl border border-border/60 bg-card/80 p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Table2 className="h-5 w-5 text-muted-foreground" />
              <div>
                <h2 className="text-lg font-semibold">Raw event table</h2>
                <p className="text-sm text-muted-foreground">Everything stored for each public product event. Use filters/search above.</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setShowRaw((value) => !value)}
              className="rounded-xl border border-border bg-background px-3 py-2 text-sm font-medium hover:bg-secondary"
            >
              {showRaw ? 'Hide raw events' : 'Show raw events'}
            </button>
          </div>

          {showRaw ? (
            <div className="max-h-[680px] overflow-auto rounded-2xl border border-border/60">
              <table className="w-full min-w-[1320px] text-left text-xs">
                <thead className="sticky top-0 bg-secondary text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">Time</th>
                    <th className="px-3 py-2">Event</th>
                    <th className="px-3 py-2">Group</th>
                    <th className="px-3 py-2">Session</th>
                    <th className="px-3 py-2">Country</th>
                    <th className="px-3 py-2">Page</th>
                    <th className="px-3 py-2">Context</th>
                    <th className="px-3 py-2">Workflow</th>
                    <th className="px-3 py-2">Referrer</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Duration</th>
                    <th className="px-3 py-2">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {timelineEvents.slice(0, 1000).map((event, index) => {
                    const details = getDetails(event);
                    const expanded = expandedEvent === index;
                    return (
                      <tr key={`${eventName(event)}-${index}-${event.ts || ''}`} className="border-t border-border/50 align-top">
                        <td className="px-3 py-2 whitespace-nowrap">{formatTs(event.ts || event.timestamp)}</td>
                        <td className="px-3 py-2 font-medium">{eventName(event)}</td>
                        <td className="px-3 py-2">{eventGroup(event)}</td>
                        <td className="px-3 py-2 font-mono text-[11px]">{shortSession(eventSession(event))}</td>
                        <td className="px-3 py-2">{eventCountry(event)}</td>
                        <td className="px-3 py-2 max-w-[220px] truncate">{eventPage(event)}</td>
                        <td className="px-3 py-2 max-w-[220px] truncate">{eventContext(event)}</td>
                        <td className="px-3 py-2">{eventWorkflow(event) || '—'}</td>
                        <td className="px-3 py-2 max-w-[180px] truncate">{displayReferrer(event)}</td>
                        <td className="px-3 py-2">{eventStatus(event) || '—'}</td>
                        <td className="px-3 py-2">{formatDuration(eventDurationMs(event))}</td>
                        <td className="px-3 py-2">
                          <button
                            type="button"
                            onClick={() => setExpandedEvent(expanded ? null : index)}
                            className="inline-flex items-center gap-1 rounded-lg border border-border px-2 py-1 text-[11px] hover:bg-secondary"
                          >
                            Raw
                            <ArrowRight className={`h-3 w-3 transition-transform ${expanded ? 'rotate-90' : ''}`} />
                          </button>
                          {expanded ? (
                            <pre className="mt-2 max-w-[420px] overflow-auto rounded-xl bg-background p-3 text-[11px] text-muted-foreground">
                              {JSON.stringify({ ...details, full_event: event }, null, 2)}
                            </pre>
                          ) : null}
                        </td>
                      </tr>
                    );
                  })}
                  {timelineEvents.length === 0 ? (
                    <tr>
                      <td colSpan={12} className="px-3 py-8 text-center text-muted-foreground">No raw events match the current filters.</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          ) : null}

          {timelineEvents.length > 1000 ? (
            <p className="mt-3 text-xs text-muted-foreground">
              Showing first 1000 filtered events in the table. Export CSV/JSON includes all {timelineEvents.length} filtered events.
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
