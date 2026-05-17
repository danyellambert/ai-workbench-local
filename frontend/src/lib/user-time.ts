type DateInput = string | number | Date | null | undefined;

type CoerceOptions = {
  dateOnlyAsLocal?: boolean;
};

function coerceDate(value: DateInput, options: CoerceOptions = {}): Date | null {
  if (value === null || value === undefined || value === '') return null;

  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value;
  }

  if (typeof value === 'number') {
    if (!Number.isFinite(value) || value <= 0) return null;
    // Backend/Nextcloud sometimes sends seconds; JS Date needs milliseconds.
    const millis = value < 10_000_000_000 ? value * 1000 : value;
    const date = new Date(millis);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  let text = String(value).trim();
  if (!text) return null;

  const dateOnlyMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
  if (dateOnlyMatch && options.dateOnlyAsLocal !== false) {
    const [, year, month, day] = dateOnlyMatch;
    const date = new Date(Number(year), Number(month) - 1, Number(day));
    return Number.isNaN(date.getTime()) ? null : date;
  }

  // Docker/AWS/backend histories often store UTC timestamps as ISO strings
  // without an explicit timezone suffix, e.g. "2026-05-10T15:55:00".
  // Browser Date treats that as local time. For product run/history timestamps,
  // treat timezone-less ISO datetimes as UTC so they display in the user's
  // browser timezone.
  const looksLikeIsoDateTime = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(text);
  const hasExplicitTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(text);
  if (looksLikeIsoDateTime && !hasExplicitTimezone) {
    text = `${text}Z`;
  }

  const parsed = new Date(text);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function parseUserDateMs(value: DateInput): number | null {
  const date = coerceDate(value);
  return date ? date.getTime() : null;
}

export function formatUserDateTime(value: DateInput, fallback = '—'): string {
  const date = coerceDate(value);
  if (!date) return value ? String(value) : fallback;

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

export function formatUserDate(value: DateInput, fallback = '—'): string {
  const date = coerceDate(value, { dateOnlyAsLocal: true });
  if (!date) return value ? String(value) : fallback;

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
  }).format(date);
}

export function formatUserTime(value: DateInput, fallback = '—'): string {
  const date = coerceDate(value);
  if (!date) return value ? String(value) : fallback;

  return new Intl.DateTimeFormat(undefined, {
    timeStyle: 'short',
  }).format(date);
}

export function formatUserCompactDateTime(value: DateInput, fallback = '—'): string {
  const date = coerceDate(value);
  if (!date) return value ? String(value) : fallback;

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date);
}

export function getUserTimeZoneLabel(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || 'local time';
}
