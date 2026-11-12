'use client';

import { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from '@/lib/motion';
import { cn } from '@/lib/utils';
import { LiveSoc } from '@/components/socrat/live-soc';
import type { SocMood } from '@/components/socrat/soc';

/**
 * "Scroll down, I'll follow you": once the hero is gone, Soc walks along with the reader. Each
 * section opts in with data-soc="mood|line" and data-soc-x="left|right" (the side he stands on;
 * right only where the page has room). When the section changes he hops across to his new spot,
 * facing the way he walks, then stops and says what the section is about. data-soc="hide" sends
 * him off screen (a section with its own Soc). Large screens only; reduced motion: no walking.
 */
type Spot = { mood: SocMood; line: string | null; side: 'left' | 'right'; hide: boolean };

const SIZE = 96;
const WALK_MS = 1300;

export function FollowSoc({ heroId }: { heroId: string }) {
  const [heroGone, setHeroGone] = useState(false);
  const { reduced: still } = useReducedMotion();
  const [spot, setSpot] = useState<Spot>({ mood: 'neutral', line: null, side: 'left', hide: false });
  const [walking, setWalking] = useState<null | 'left' | 'right'>(null);
  const [wide, setWide] = useState(false);
  const prevSide = useRef<'left' | 'right'>('left');

  useEffect(() => {
    const check = () => setWide(window.innerWidth >= 1720);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return;
    const hero = document.getElementById(heroId);
    const heroWatch = new IntersectionObserver(([entry]) => setHeroGone(!entry.isIntersecting), { threshold: 0.15 });
    if (hero) heroWatch.observe(hero);
    const sections = [...document.querySelectorAll<HTMLElement>('[data-soc]')];
    const sectionWatch = new IntersectionObserver(entries => {
      const visible = entries.filter(e => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!visible) return;
      const el = visible.target as HTMLElement;
      const raw = el.dataset.soc ?? '';
      const [mood, line] = raw.split('|');
      setSpot({
        mood: (mood && mood !== 'hide' ? mood : 'neutral') as SocMood,
        line: line || null,
        side: el.dataset.socX === 'right' ? 'right' : 'left',
        hide: raw === 'hide',
      });
    }, { threshold: [0.3, 0.6], rootMargin: '-20% 0px -30% 0px' });
    sections.forEach(s => sectionWatch.observe(s));
    return () => { heroWatch.disconnect(); sectionWatch.disconnect(); };
  }, [heroId]);

  // Right-hand spots need a wide screen; otherwise he keeps to the left margin.
  const side = wide ? spot.side : 'left';
  const shown = heroGone && !spot.hide;

  // Crossing the page: walk (hop, facing the way he goes) for the length of the trip.
  useEffect(() => {
    if (side === prevSide.current) return;
    const dir = side === 'right' ? 'right' : 'left';
    prevSide.current = side;
    if (still) return;
    setWalking(dir);
    const timer = window.setTimeout(() => setWalking(null), WALK_MS);
    return () => window.clearTimeout(timer);
  }, [side, still]);

  // He speaks once he has arrived, for a few seconds, then just keeps you company.
  const [talking, setTalking] = useState(false);
  useEffect(() => {
    if (!spot.line || walking) return;
    setTalking(true);
    const timer = window.setTimeout(() => setTalking(false), 4600);
    return () => window.clearTimeout(timer);
  }, [spot.line, walking]);

  return (
    <div
      aria-hidden="true"
      inert
      className={cn(
        'follow-soc pointer-events-none fixed bottom-6 left-0 z-40 hidden lg:block',
        !still && 'transition-[opacity,translate] ease-[cubic-bezier(0.45,0,0.25,1)]',
        shown ? 'opacity-100' : 'translate-y-10 opacity-0',
      )}
      style={{
        width: SIZE,
        // Left margin, or the right edge of the viewport.
        translate: `${side === 'right' ? `calc(100vw - ${SIZE + 28}px)` : '10px'} ${shown ? '0px' : '40px'}`,
        transitionDuration: `${WALK_MS}ms, ${WALK_MS}ms`,
      }}
    >
      {/* His line sits above him, inside the margin, so it never covers the section's text. */}
      {shown && talking && !walking && spot.line ? (
        <p key={spot.line} className="soc-bubble font-hand animate-in fade-in zoom-in-90 mb-4 w-[118px] rounded-[4px] border-2 border-[var(--soc-outline)] bg-card px-2.5 py-2 text-[17px] leading-tight text-foreground shadow-[3px_3px_0_var(--soc-outline)] duration-300" data-side={side === 'right' ? 'left' : 'right'}>
          {spot.line}
        </p>
      ) : null}
      <div className={cn(walking && 'soc-walk', walking === 'left' && 'soc-face-left')}>
        <LiveSoc books={false} mood={walking ? 'happy' : spot.mood} say={null} size={SIZE} />
      </div>
    </div>
  );
}
