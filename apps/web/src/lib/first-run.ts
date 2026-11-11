import { useSyncExternalStore } from 'react';

/**
 * One first-run moment at a time. The launch-offer celebration holds the tour back while it
 * checks for (and shows) the offer; the tour starts once nothing holds it.
 */
let holds = 0;
const listeners = new Set<() => void>();

export function holdTour(): () => void {
  holds += 1;
  listeners.forEach(fn => fn());
  let released = false;
  return () => {
    if (released) return;
    released = true;
    holds -= 1;
    listeners.forEach(fn => fn());
  };
}

export function useTourHeld(): boolean {
  return useSyncExternalStore(
    fn => { listeners.add(fn); return () => listeners.delete(fn); },
    () => holds > 0,
    () => false,
  );
}
