'use client';
// Lessons still being written for the learner's course, and how far along each is
// (GET /me/preparing, read from the writing job's own log). Polled while any lesson is moving,
// so Today and the skill map show a lesson filling up and swap it in the moment it goes live.
import { useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';

export type PreparingState = 'later' | 'scheduled' | 'queued' | 'writing' | 'stuck';
export interface PreparingLesson {
  concept: string;
  title: string;
  module: string;
  state: PreparingState;
  progress: number;
  label: string;
  eta_seconds?: number;
  at?: number;
}

const MOVING: PreparingState[] = ['queued', 'writing', 'scheduled'];
export const isMoving = (l: PreparingLesson) => MOVING.includes(l.state);

/** ``onLive`` runs when a lesson that was being written leaves the list: it is live now. */
export function usePreparing(enabled: boolean, onLive?: () => void): PreparingLesson[] {
  const [lessons, setLessons] = useState<PreparingLesson[]>([]);
  const seen = useRef<Set<string> | null>(null);
  const live = useRef(onLive);
  live.current = onLive;
  useEffect(() => {
    if (!enabled) return;
    let stop = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const tick = async () => {
      let next: PreparingLesson[] | null = null;
      try {
        next = (await api.get<{ lessons: PreparingLesson[] }>('/me/preparing')).lessons;
      } catch { /* try again on the next tick */ }
      if (stop) return;
      if (next) {
        const now = new Set(next.map(l => l.concept));
        if (seen.current && [...seen.current].some(c => !now.has(c))) live.current?.();
        seen.current = now;
        setLessons(next);
      }
      // Quick while something is being written; slow when everything waits.
      const busy = next ? next.some(l => l.state === 'writing' || l.state === 'queued') : true;
      timer = setTimeout(tick, busy ? 5000 : 60000);
    };
    void tick();
    return () => { stop = true; if (timer) clearTimeout(timer); };
  }, [enabled]);
  return lessons;
}

/** "about 3 min left" from a server estimate; never promises under a minute. */
export function timeLeft(seconds?: number): string {
  if (!seconds) return '';
  const minutes = Math.max(1, Math.round(seconds / 60));
  return `about ${minutes} min left`;
}
