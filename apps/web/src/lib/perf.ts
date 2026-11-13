'use client';

import { useCallback, useEffect, useState } from 'react';

/**
 * Light rendering: the same pages with the paint-heavy texture switched off (see the
 * `html[data-perf="lite"]` block in globals.css), for devices that cannot keep up with it.
 *
 * Three things decide the mode, in this order:
 *   1. The learner's choice in Settings ('lite' or 'full'), kept per browser.
 *   2. What the device says about itself before the first paint: little memory, few cores,
 *      or the data-saver setting. These devices start light and never see the lag.
 *   3. What the device actually does. While the learner scrolls, frame times are sampled; a
 *      device that keeps missing frames is switched to light on the spot and remembered, so a
 *      device that reports good hardware but renders slowly is still caught.
 */
export type PerfSetting = 'auto' | 'lite' | 'full';

const KEY = 'socrat:perf'; // the learner's choice: 'lite' | 'full' (absent = auto)
const MEASURED = 'socrat:perf-measured'; // 'lite' once this device was measured dropping frames

/** Runs before first paint (inline in the root layout) so a light device never paints the heavy page. */
export const PERF_BOOT_SCRIPT = `try{var p=localStorage.getItem('${KEY}'),n=navigator,c=n.connection;if(p==='lite'||(p!=='full'&&(localStorage.getItem('${MEASURED}')==='lite'||(n.deviceMemory&&n.deviceMemory<=4)||(n.hardwareConcurrency&&n.hardwareConcurrency<=4)||(c&&c.saveData))))document.documentElement.dataset.perf='lite'}catch(e){}`;

const isLite = () => document.documentElement.dataset.perf === 'lite';

function apply(lite: boolean) {
  if (lite) document.documentElement.dataset.perf = 'lite';
  else delete document.documentElement.dataset.perf;
  window.dispatchEvent(new Event('socrat:perf'));
}

function read(key: string): string | null {
  try { return localStorage.getItem(key); } catch { return null; }
}

/** Whether the device describes itself as a weak one (the same test the boot script runs). */
function weakDevice(): boolean {
  const n = navigator as Navigator & { deviceMemory?: number; connection?: { saveData?: boolean } };
  return Boolean((n.deviceMemory && n.deviceMemory <= 4) || (n.hardwareConcurrency && n.hardwareConcurrency <= 4) || n.connection?.saveData);
}

// A frame slower than this is under 20 frames a second: lag anyone can see, not a single missed
// refresh. The bar is high on purpose, so a good device having a busy moment is left alone.
const SLOW_FRAME_MS = 50;
// One sampling window: this many frames of scrolling.
const WINDOW_FRAMES = 45;
// A window is bad when this share of its frames were slow.
const BAD_SHARE = 0.4;
// This many bad windows (not necessarily in a row) switch the device to light rendering.
const BAD_WINDOWS = 4;
// Frames are sampled for this long after the last scroll or touch movement.
const ACTIVE_MS = 400;

/**
 * Watches frame times while the page is being scrolled and switches to light rendering when
 * the device keeps missing frames. Costs nothing while the page is still: the frame loop only
 * runs for a moment after each scroll. Mount once, in the root layout.
 */
export function PerfGovernor() {
  useEffect(() => {
    // A development build is several times slower than production and would measure as a weak device.
    if (process.env.NODE_ENV !== 'production' || isLite() || read(KEY) === 'full') return;
    let frame = 0;
    let last = 0;
    let activeUntil = 0;
    let frames = 0;
    let slow = 0;
    let bad = 0;
    let done = false;

    const stop = () => {
      done = true;
      cancelAnimationFrame(frame);
      window.removeEventListener('scroll', wake, true);
      window.removeEventListener('touchmove', wake, true);
    };
    const tick = (now: number) => {
      frame = 0;
      if (done) return;
      // A hidden tab, or the gap after the loop was idle, is not a slow frame.
      if (last && !document.hidden) {
        const delta = now - last;
        if (delta < 1000) {
          frames += 1;
          if (delta > SLOW_FRAME_MS) slow += 1;
        }
      }
      last = now;
      if (frames >= WINDOW_FRAMES) {
        if (slow / frames >= BAD_SHARE) bad += 1;
        frames = 0;
        slow = 0;
        if (bad >= BAD_WINDOWS) {
          try { localStorage.setItem(MEASURED, 'lite'); } catch { /* still applies for this visit */ }
          apply(true);
          stop();
          return;
        }
      }
      if (now < activeUntil) frame = requestAnimationFrame(tick);
      else last = 0;
    };
    function wake() {
      activeUntil = performance.now() + ACTIVE_MS;
      if (!frame && !done) frame = requestAnimationFrame(tick);
    }
    window.addEventListener('scroll', wake, { capture: true, passive: true });
    window.addEventListener('touchmove', wake, { capture: true, passive: true });
    return stop;
  }, []);
  return null;
}

/** The Settings control: the learner's choice, and whether light rendering is on right now. */
export function usePerfSetting(): { setting: PerfSetting; lite: boolean; set(value: PerfSetting): void } {
  const [setting, setSetting] = useState<PerfSetting>('auto');
  const [lite, setLite] = useState(false);
  useEffect(() => {
    const stored = read(KEY);
    setSetting(stored === 'lite' || stored === 'full' ? stored : 'auto');
    const sync = () => setLite(isLite());
    sync();
    window.addEventListener('socrat:perf', sync);
    return () => window.removeEventListener('socrat:perf', sync);
  }, []);
  const set = useCallback((value: PerfSetting) => {
    setSetting(value);
    try {
      if (value === 'auto') localStorage.removeItem(KEY);
      else localStorage.setItem(KEY, value);
      // Choosing Auto or Full again forgets an earlier measurement, so the device is judged afresh.
      if (value !== 'lite') localStorage.removeItem(MEASURED);
    } catch { /* per-browser nicety only */ }
    apply(value === 'lite' || (value === 'auto' && weakDevice()));
  }, []);
  return { setting, lite, set };
}
