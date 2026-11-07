'use client';

import dynamic from 'next/dynamic';

// Field metrics are measured by the browser itself and sent when the tab is hidden, so the
// reporter can load after first paint instead of counting against every route's first load.
export const DeferredWebVitals = dynamic(() => import('@/components/web-vitals').then(m => m.WebVitals), { ssr: false });
