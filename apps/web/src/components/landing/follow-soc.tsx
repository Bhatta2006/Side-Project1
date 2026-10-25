'use client';

import { useEffect, useState } from 'react';
import { useReducedMotion } from '@/lib/motion';
import { cn } from '@/lib/utils';
import { LiveSoc } from '@/components/socrat/live-soc';
import type { SocMood } from '@/components/socrat/soc';

/**
 * "Scroll down, I'll follow you": once the hero is gone, a small Soc rides in the page margin and reacts
 * to the section in view. Sections opt in with data-soc="mood|line". Large screens only.
 */
export function FollowSoc({ heroId }: { heroId: string }) {
  const [shown, setShown] = useState(false);
  const { reduced: still } = useReducedMotion();
  const [state, setState] = useState<{ mood: SocMood; line: string | null }>({ mood: 'neutral', line: null });

  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return;
    const hero = document.getElementById(heroId);
    const heroWatch = new IntersectionObserver(([entry]) => setShown(!entry.isIntersecting), { threshold: 0.15 });
    if (hero) heroWatch.observe(hero);
    const sections = [...document.querySelectorAll<HTMLElement>('[data-soc]')];
    const sectionWatch = new IntersectionObserver(entries => {
      const visible = entries.filter(e => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!visible) return;
      const [mood, line] = (visible.target.getAttribute('data-soc') ?? '').split('|');
      setState({ mood: (mood || 'neutral') as SocMood, line: line || null });
    }, { threshold: [0.3, 0.6], rootMargin: '-20% 0px -30% 0px' });
    sections.forEach(s => sectionWatch.observe(s));
    return () => { heroWatch.disconnect(); sectionWatch.disconnect(); };
  }, [heroId]);

  // Each section's line shows for a few seconds, then Soc just keeps you company.
  const [talking, setTalking] = useState(false);
  useEffect(() => {
    if (!state.line) return;
    setTalking(true);
    const timer = window.setTimeout(() => setTalking(false), 4200);
    return () => window.clearTimeout(timer);
  }, [state.line]);

  return (
    <div
      aria-hidden={!shown}
      inert={!shown}
      className={cn(
        'fixed bottom-6 left-1.5 z-40 hidden w-[78px] lg:block',
        !still && 'transition-[opacity,translate] duration-500 ease-[var(--ease-soft)]',
        shown ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-8 opacity-0',
      )}
    >
      <LiveSoc books={false} mood={state.mood} say={shown && talking ? state.line : null} size={78} bubbleSide="right" />
    </div>
  );
}
