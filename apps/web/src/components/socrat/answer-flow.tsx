'use client';

import { useEffect, useRef, type ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { play } from '@/lib/game-sound';
import { GameEmoji } from './game-emoji';
import { PebbleFriend } from './pebble-friend';

/**
 * Lesson feel (item 2 of docs/research/duolingo-teardown.md), behind `features.lesson_feel`.
 * How answering feels, never what counts: everything here is display and input, and the
 * practice round of missed questions runs in the browser and records nothing.
 */

/** A run is shown from this many right answers in a row, and the bar is highlighted from RUN_GLOW. */
export const RUN_SHOWN = 3;
export const RUN_GLOW = 5;

/** Right answers in a row at the end of `results` (oldest first). */
export function runOf(results: readonly boolean[]): number {
  let n = 0;
  for (let i = results.length - 1; i >= 0 && results[i]; i--) n++;
  return n;
}

const PRAISE = ['Right.', 'Nice work.', 'Exactly.', "That's it.", 'Spot on.'];

/** The heading of a correct answer: varied, short, and a count once there is a run. */
export function praise(run: number, seed: number): string {
  return run >= RUN_SHOWN ? `${run} in a row.` : PRAISE[Math.abs(seed) % PRAISE.length];
}

/** "n in a row" as pen tally marks: groups of four strokes crossed by a fifth. */
export function RunTally({ run, className }: { run: number; className?: string }) {
  if (run < RUN_SHOWN) return null;
  const groups = Math.floor(run / 5);
  const rest = run % 5;
  const marks = [...Array.from({ length: Math.min(groups, 4) }, () => 5), ...(rest && groups < 4 ? [rest] : [])];
  return (
    <>
    {/* Daybreak: a combo chip with Ember's flame that pops on every new answer in the run. */}
    <p key={run} className={cn('db-only db-pop inline-flex w-fit items-center gap-1.5 rounded-full bg-[var(--db-streak-tint)] py-1 pr-3.5 pl-1.5 text-[15px] font-extrabold text-[var(--db-streak-ink)] shadow-[inset_0_0_0_2px_color-mix(in_srgb,var(--db-streak)_30%,transparent)]', className)} aria-live="polite">
      <GameEmoji name="flame" size={24} className={run >= RUN_GLOW ? 'db-flicker' : undefined} />
      {run} in a row{run >= RUN_GLOW ? '. On fire.' : ''}
    </p>
    <p className={cn('nb-only inline-flex items-center gap-2 text-[15px] font-semibold text-pen animate-pop', className)} aria-live="polite">
      <span className="inline-flex gap-1.5" aria-hidden="true">
        {marks.map((count, i) => (
          <svg key={i} viewBox="0 0 26 18" className="h-[18px] w-[26px]" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
            {Array.from({ length: Math.min(count, 4) }, (_, j) => <path key={j} d={`M${4 + j * 5} 3.5l-.6 11`} />)}
            {count === 5 ? <path d="M1.5 13.5L23.5 4" /> : null}
          </svg>
        ))}
      </span>
      {run} in a row
    </p>
    </>
  );
}

function typing(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName);
}

/**
 * Answer from the keyboard: 1-9 or A-I picks an option, Enter checks or continues.
 * Enter on a focused button or link is left to the browser, except on an answer option.
 */
export function useAnswerKeys({ enabled, count, onPick, onSubmit }: {
  enabled: boolean;
  count: number;
  onPick?(index: number): void;
  onSubmit(): void;
}) {
  const latest = useRef({ count, onPick, onSubmit });
  useEffect(() => { latest.current = { count, onPick, onSubmit }; });
  useEffect(() => {
    if (!enabled) return;
    function onKey(e: KeyboardEvent) {
      if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || e.repeat || typing(e.target)) return;
      // A dialog (the paywall, a confirm) owns the keyboard while it is open.
      if (document.querySelector('[role="dialog"][data-state="open"], [role="alertdialog"][data-state="open"]')) return;
      const { count, onPick, onSubmit } = latest.current;
      if (e.key === 'Enter') {
        const el = e.target instanceof HTMLElement ? e.target : null;
        const control = el?.closest('button, a, [role="button"]');
        if (control && control.getAttribute('role') !== 'radio') return;
        e.preventDefault();
        onSubmit();
        return;
      }
      if (!onPick) return;
      const digit = /^[1-9]$/.test(e.key) ? Number(e.key) - 1 : -1;
      const letter = /^[a-i]$/i.test(e.key) ? e.key.toLowerCase().charCodeAt(0) - 97 : -1;
      const index = digit >= 0 ? digit : letter;
      if (index >= 0 && index < count) {
        e.preventDefault();
        onPick(index);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [enabled]);
}

/** A key hint shown once, under the options, on devices with a keyboard. */
export function KeyHint({ count }: { count: number }) {
  const last = String.fromCharCode(64 + Math.min(count, 9));
  return (
    <p className="hidden text-[13px] text-muted-foreground [@media(hover:hover)_and_(pointer:fine)]:block">
      Keys: <kbd className="font-mono">1</kbd>–<kbd className="font-mono">{Math.min(count, 9)}</kbd> or <kbd className="font-mono">A</kbd>–<kbd className="font-mono">{last}</kbd> to choose, <kbd className="font-mono">Enter</kbd> to check and continue.
    </p>
  );
}

/**
 * A pressable "stamped" button: a solid ink ledge under the face that it sinks into when
 * pressed. Plain CSS (see .stamp in globals.css), so it costs nothing to draw.
 */
export function StampButton({ className, children, ...props }: React.ComponentProps<'button'>) {
  return <button type="button" className={cn('stamp', className)} {...props}>{children}</button>;
}

export type SheetTone = 'correct' | 'wrong' | 'neutral';

/**
 * Feedback after an answer, in a sheet that sticks to the bottom of the column: highlighter
 * for right, red pen for wrong. Its button takes focus, so Enter continues.
 */
export function FeedbackSheet({ tone, title, children, action, onContinue, run = 0 }: {
  tone: SheetTone;
  title: string;
  children?: ReactNode;
  action: string;
  onContinue(): void;
  /** Right answers in a row, counting this one: the correct sound climbs with it. */
  run?: number;
}) {
  const button = useRef<HTMLButtonElement>(null);
  useEffect(() => { button.current?.focus({ preventScroll: true }); }, []);
  // Heard once, when the sheet opens.
  useEffect(() => { if (tone !== 'neutral') play(tone, run); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div
      role="status"
      data-tone={tone}
      // On phones the main tab bar (components/shell.tsx: 68px, a 1px border and the safe area)
      // is fixed at the bottom, so the sheet sticks just above it.
      className="feedback-sheet sticky bottom-[calc(69px+env(safe-area-inset-bottom))] z-30 -mx-4 mt-2 border-t-[3px] px-4 pt-4 pb-4 sm:-mx-6 sm:px-6 md:bottom-0 md:pb-[calc(1rem+env(safe-area-inset-bottom))] animate-in fade-in slide-in-from-bottom-3 duration-200 motion-reduce:animate-none"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <p className="flex items-center gap-2 font-display text-xl font-semibold tracking-[-0.02em]">
            {/* Daybreak: the game emoji, with Jade cheering a right answer and Soc for a wrong one. */}
            <span aria-hidden="true" className="db-only relative flex-none">
              {tone === 'correct' ? <PebbleFriend kind="jade" mood="happy" size={46} className="db-pop" /> : tone === 'wrong' ? <PebbleFriend kind="soc" size={46} className="db-pop" /> : null}
              {tone !== 'neutral' ? <GameEmoji name={tone === 'correct' ? 'check' : 'cross'} size={22} className="absolute -right-1.5 -bottom-1 db-pop [animation-delay:120ms]" /> : null}
            </span>
            <span aria-hidden="true" className="nb-only feedback-mark grid size-8 flex-none place-items-center rounded-full">
              {tone === 'correct' ? (
                <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
              ) : tone === 'wrong' ? (
                <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M7 7l10 10M17 7L7 17" /></svg>
              ) : (
                <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M6 12h12" /></svg>
              )}
            </span>
            {title}
          </p>
          {children ? <div className="mt-2 grid gap-1.5 text-[15px]">{children}</div> : null}
        </div>
        <StampButton ref={button} data-tone={tone} className="w-full flex-none sm:w-auto" onClick={onContinue}>{action}</StampButton>
      </div>
    </div>
  );
}

export interface PracticeItem {
  key: string;
  prompt: ReactNode;
  code?: string | null;
  options: string[];
  answer: number;
  explanation?: string | null;
}
