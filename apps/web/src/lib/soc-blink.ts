'use client';

import { prefersReducedMotion } from './motion';

/**
 * Soc's blink and his idle gesture: brief swaps to another drawing every few seconds.
 *
 * Both used to be endless CSS animations on the frames of every Soc. An animation like that keeps
 * the page producing a frame on every refresh just to find nothing has changed, and with a sticker
 * shadow around each Soc and a page of paper under it, that was a large share of the work while
 * scrolling. Here a timer sets `data-blinking` / `data-beating` on the figure for a moment instead
 * (CSS does the swap), so a Soc that is not moving costs nothing, and one that is off screen or on
 * a hidden tab never moves.
 */
const BLINK_CYCLE_MS = 4800;
const BLINK_MS = 145; // 3% of the cycle, as the animation had it
const BEAT_CYCLE_MS = 9600;
const BEAT_MS = 336; // 3.5% of the cycle
const BEAT_AT = [1920, 2592]; // twice in a row, early in the cycle, clear of the blink

function visible(el: HTMLElement): boolean {
  if (document.hidden || prefersReducedMotion()) return false;
  const r = el.getBoundingClientRect();
  return r.width > 0 && r.bottom > 0 && r.top < window.innerHeight && r.right > 0 && r.left < window.innerWidth;
}

/** Sets `attr` on `el` for `ms`; returns the timer that will clear it. */
function flash(el: HTMLElement, attr: string, ms: number): number {
  el.setAttribute(attr, '');
  return window.setTimeout(() => el.removeAttribute(attr), ms);
}

/**
 * Starts the blink (and, for an idle Soc with hands to move, the gesture) on `el`. `shift` (0 to 1,
 * steady per Soc) keeps a page of Socs from moving in step. Returns the stop function.
 */
export function watchFigure(el: HTMLElement, shift: number, o: { blinks: boolean; beats: boolean }): () => void {
  const timers = new Set<number>();
  const later = (fn: () => void, ms: number) => {
    const id = window.setTimeout(() => { timers.delete(id); fn(); }, ms);
    timers.add(id);
  };
  // The first one comes 2.2 to 4.6 s in, as the animations' own delay did.
  const wait = 2200 + shift * 2400;

  const blink = () => {
    if (visible(el)) timers.add(flash(el, 'data-blinking', BLINK_MS));
    later(blink, BLINK_CYCLE_MS);
  };
  const beat = () => {
    if (visible(el)) for (const at of BEAT_AT) later(() => { if (visible(el)) timers.add(flash(el, 'data-beating', BEAT_MS)); }, at);
    later(beat, BEAT_CYCLE_MS);
  };
  if (o.blinks) later(blink, wait);
  if (o.beats) later(beat, wait);

  return () => {
    timers.forEach(id => window.clearTimeout(id));
    el.removeAttribute('data-blinking');
    el.removeAttribute('data-beating');
  };
}
