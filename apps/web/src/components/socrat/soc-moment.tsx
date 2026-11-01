'use client';

import dynamic from 'next/dynamic';
import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Soc reacting to a moment: flies in from the corner, grows, says one line, leaves.
 * Used for an accepted solution (a wink and a joke) and for a screenshot during a test
 * (a little bigger, angry, one line of mock). Reduced motion gets a plain fade.
 * The view and its lines load on first use (soc-moment-view.tsx).
 */

export type MomentKind = 'celebrate' | 'mock' | 'paste';

export interface Moment { kind: MomentKind; id: number }

const SocMomentView = dynamic(() => import('@/components/socrat/soc-moment-view'), { ssr: false });

/** Show Soc for a moment. `show('celebrate')` picks a line no one has seen in a while. */
export function useSocMoment() {
  const [moment, setMoment] = useState<Moment | null>(null);
  const counter = useRef(0);
  const show = useCallback((kind: MomentKind) => {
    counter.current += 1;
    setMoment({ kind, id: counter.current });
  }, []);
  const done = useCallback(() => setMoment(null), []);
  return { show, element: moment ? <SocMomentView moment={moment} onDone={done} /> : null };
}

const SCREENSHOT_KEYS = (e: KeyboardEvent) =>
  e.key === 'PrintScreen'
  // Windows snipping (Win+Shift+S) and macOS captures (Cmd+Shift+3/4/5), when the page sees them.
  || (e.shiftKey && (e.metaKey || e.ctrlKey) && ['s', 'S', '3', '4', '5'].includes(e.key));

/**
 * While `active`: no copy, cut, paste, drag or right-click menu anywhere on the page
 * (including the code editor), and a screenshot shortcut earns an angry Soc.
 * Browsers cannot stop a screenshot; this makes the rule visible and the attempt awkward.
 */
export function useExamGuard(active: boolean) {
  const { show: showNow, element } = useSocMoment();
  const last = useRef(0);
  // One reaction per gesture: a shortcut fires both keydown and keyup.
  const show = useCallback((kind: MomentKind) => {
    if (Date.now() - last.current < 1500) return;
    last.current = Date.now();
    showNow(kind);
  }, [showNow]);
  useEffect(() => {
    if (!active) return;
    const block = (e: Event) => {
      e.preventDefault();
      e.stopImmediatePropagation();
      if (e.type === 'paste' || e.type === 'copy' || e.type === 'cut') show('paste');
    };
    const keys = (e: KeyboardEvent) => {
      if (SCREENSHOT_KEYS(e)) {
        if (e.key === 'PrintScreen') {
          // Overwrite whatever the capture put on the clipboard, where the browser allows it.
          navigator.clipboard?.writeText('').catch(() => undefined);
        }
        show('mock');
      }
    };
    const events = ['copy', 'cut', 'paste', 'contextmenu', 'dragstart', 'drop'] as const;
    // Capture on window runs before the editor's own handlers, so its paste is blocked too.
    events.forEach(name => window.addEventListener(name, block, true));
    window.addEventListener('keyup', keys, true);
    window.addEventListener('keydown', keys, true);
    return () => {
      events.forEach(name => window.removeEventListener(name, block, true));
      window.removeEventListener('keyup', keys, true);
      window.removeEventListener('keydown', keys, true);
    };
  }, [active, show]);
  return element;
}

/** Drop-in for pages: `<ExamGuard active />` renders nothing until Soc has something to say. */
export function ExamGuard({ active }: { active: boolean }) {
  return useExamGuard(active);
}
