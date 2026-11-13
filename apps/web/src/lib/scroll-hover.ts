'use client';

/**
 * Pauses hover while the page scrolls.
 *
 * During a wheel scroll the page moves under a still pointer, so every card, link and button it
 * passes starts and stops its hover transition (and paper sheets tilt and repaint). Measured on
 * Skills, that alone made about 8% of scroll frames janky.
 *
 * While the page scrolls, one invisible layer covers the viewport and takes the pointer, so nothing
 * under it hovers. Showing one fixed element is cheap; switching `pointer-events` on the page
 * instead restyles every element twice per scroll, which cost frames of its own on long pages.
 * The layer is removed shortly after the scroll stops, so hover works again as soon as the page is
 * still. Wheel events on it still scroll the page. Only devices with a mouse need this: touch
 * screens do not hover.
 *
 * Returns the stop function.
 */
const SETTLE_MS = 150;

export function pauseHoverWhileScrolling(): () => void {
  if (!window.matchMedia('(hover: hover)').matches) return () => {};
  const shield = document.createElement('div');
  shield.setAttribute('aria-hidden', 'true');
  shield.dataset.scrollShield = '';
  shield.style.cssText = 'position:fixed;inset:0;z-index:2147483647;display:none;';
  document.body.appendChild(shield);
  let timer = 0;
  const settle = () => {
    timer = 0;
    shield.style.display = 'none';
  };
  const onScroll = () => {
    if (timer) window.clearTimeout(timer);
    else shield.style.display = 'block';
    timer = window.setTimeout(settle, SETTLE_MS);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  return () => {
    window.removeEventListener('scroll', onScroll);
    if (timer) window.clearTimeout(timer);
    shield.remove();
  };
}
