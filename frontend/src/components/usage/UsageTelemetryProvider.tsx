import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { trackUsageEvent } from '@/lib/usage-telemetry';

function readableElementLabel(element: Element | null): string | undefined {
  if (!element) return undefined;
  const aria = element.getAttribute('aria-label');
  const title = element.getAttribute('title');
  const data = element.getAttribute('data-usage-label') || element.getAttribute('data-testid');
  const text = element.textContent?.replace(/\s+/g, ' ').trim();
  return (aria || title || data || text || '').slice(0, 180) || undefined;
}

function classifyPage(pathname: string): string {
  if (pathname === '/') return 'landing';
  if (pathname.includes('/admin/usage')) return 'admin_usage';
  if (pathname.includes('/workflows')) return 'workflow';
  if (pathname.includes('/lab')) return 'ai_lab';
  if (pathname.includes('/settings/runtime')) return 'runtime';
  if (pathname.includes('/settings/preferences')) return 'preferences';
  if (pathname.includes('/documents')) return 'documents';
  if (pathname.includes('/history')) return 'run_history';
  return 'app';
}

export default function UsageTelemetryProvider() {
  const location = useLocation();
  const pageStartRef = useRef<number>(Date.now());
  const pageRef = useRef<string>(location.pathname + location.search);
  const scrollMarksRef = useRef<Set<number>>(new Set());

  useEffect(() => {
    const previousPage = pageRef.current;
    const previousDuration = Date.now() - pageStartRef.current;
    if (previousPage) {
      trackUsageEvent('page_left', {
        page: previousPage,
        route: previousPage,
        duration_ms: previousDuration,
        source: 'route-change',
      }, { beacon: true });
    }

    const route = location.pathname + location.search;
    pageRef.current = route;
    pageStartRef.current = Date.now();
    scrollMarksRef.current = new Set();

    const pageKind = classifyPage(location.pathname);

    trackUsageEvent(location.pathname === '/' ? 'landing_viewed' : 'page_viewed', {
      page: location.pathname,
      route,
      page_kind: pageKind,
    });

    if (pageKind === 'ai_lab') trackUsageEvent('ai_lab_opened', { page: location.pathname, route });
    if (pageKind === 'runtime') trackUsageEvent('runtime_controls_opened', { page: location.pathname, route });
    if (pageKind === 'preferences') trackUsageEvent('preferences_opened', { page: location.pathname, route });
    if (pageKind === 'documents') trackUsageEvent('documents_opened', { page: location.pathname, route });
    if (pageKind === 'run_history') trackUsageEvent('run_history_opened', { page: location.pathname, route });
    if (pageKind === 'workflow') {
      const workflow = location.pathname.split('/').filter(Boolean).at(-1);
      trackUsageEvent('workflow_page_viewed', { page: location.pathname, route, workflow });
    }
  }, [location.pathname, location.search]);

  useEffect(() => {
    const onScroll = () => {
      const doc = document.documentElement;
      const scrollTop = window.scrollY || doc.scrollTop || 0;
      const scrollable = Math.max(1, doc.scrollHeight - window.innerHeight);
      const percent = Math.min(100, Math.round((scrollTop / scrollable) * 100));
      for (const mark of [25, 50, 75, 100]) {
        if (percent >= mark && !scrollMarksRef.current.has(mark)) {
          scrollMarksRef.current.add(mark);
          const event = location.pathname === '/' ? `landing_scroll_${mark}` : 'page_scroll_depth';
          trackUsageEvent(event, {
            page: location.pathname,
            route: location.pathname + location.search,
            scroll_depth: mark,
          });
        }
      }
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener('scroll', onScroll);
  }, [location.pathname, location.search]);

  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      const target = event.target instanceof Element ? event.target : null;
      const clickable = target?.closest('a,button,[role="button"],[data-usage-event]');
      if (!clickable) return;

      const tag = clickable.tagName.toLowerCase();
      const href = clickable instanceof HTMLAnchorElement ? clickable.href : clickable.getAttribute('href') || undefined;
      const label = readableElementLabel(clickable);
      const explicitEvent = clickable.getAttribute('data-usage-event');

      let eventName = explicitEvent || 'ui_clicked';
      const labelLower = (label || '').toLowerCase();
      const hrefLower = (href || '').toLowerCase();

      if (labelLower.includes('meet danyel') || hrefLower.includes('linkedin')) eventName = 'meet_danyel_clicked';
      if (labelLower.includes('open app') || labelLower.includes('enter app')) eventName = 'open_app_clicked';
      if (labelLower.includes('trello') && labelLower.includes('preview')) eventName = 'trello_preview_opened';
      if (labelLower.includes('notion') && labelLower.includes('preview')) eventName = 'notion_preview_opened';
      if (labelLower.includes('download') && labelLower.includes('deck')) eventName = 'deck_download_clicked';

      trackUsageEvent(eventName, {
        page: location.pathname,
        route: location.pathname + location.search,
        element_tag: tag,
        button_label: label,
        href,
        click_x: event.clientX,
        click_y: event.clientY,
      });
    };

    document.addEventListener('click', onClick, true);
    return () => document.removeEventListener('click', onClick, true);
  }, [location.pathname, location.search]);

  useEffect(() => {
    const flushPageTime = () => {
      const duration = Date.now() - pageStartRef.current;
      trackUsageEvent('page_time_spent', {
        page: pageRef.current,
        route: pageRef.current,
        duration_ms: duration,
        visibility_state: document.visibilityState,
      }, { beacon: true });
    };

    const onVisibility = () => {
      if (document.visibilityState === 'hidden') flushPageTime();
    };

    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('beforeunload', flushPageTime);

    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('beforeunload', flushPageTime);
    };
  }, []);

  return null;
}
