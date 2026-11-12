'use client';

import { api } from './api';

/**
 * The reads each signed-in page starts with. Asked for at the same time as the session check
 * (and when a nav link is hovered), so the page's data is on its way before the page is allowed
 * to render. Pages read them with api.cached(path, PAGE_MS); keep both lists in step.
 */
const ROUTE_DATA: Record<string, string[]> = {
  '/today': ['/today', '/plan', '/library/recommendations?limit=4', '/assessments'],
  '/plan': ['/plan', '/projects'],
  '/progress': ['/progress', '/assessments'],
  '/graph': ['/plan'],
  '/library': ['/library/meta', '/library/recommendations?limit=6'],
};

export function prefetchRoute(pathname: string) {
  for (const path of ROUTE_DATA[pathname] ?? []) api.prefetch(path);
}
