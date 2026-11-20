'use client';
// Game moments, behind features.game_moments (docs/implementation/gamified-ui-backlog.md,
// item 4). Each one dresses evidence the server already holds: today's minutes, skills proven, the
// streak, badges earned. Nothing here records, counts or awards anything new. Every moment is
// Shown once, remembered in this browser.
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { levelFor, levelUpDue, nextStreakMilestone, streakMilestone } from '@/lib/game';
import { playInGame } from '@/lib/game-sound';
import { Button } from '@/components/ui/button';
import { Celebrate } from './celebrate';
import { GameEmoji, type GameEmojiName } from './game-emoji';
import { PebbleFriend, type PebbleKind } from './pebble-friend';

function read(key: string): string | null {
  try { return localStorage.getItem(key); } catch { return null; }
}
function write(key: string, value: string) {
  try { localStorage.setItem(key, value); } catch { /* blocked: this visit only */ }
}

/** Counts up to `value` once, about half a second. Still under reduced motion. */
export function useCountUp(value: number, ms = 600): number {
  const [shown, setShown] = useState(value);
  const from = useRef(0);
  useEffect(() => {
    const still = typeof window === 'undefined'
      || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
      || document.documentElement.dataset.motion === 'reduced';
    if (still || value <= 0) { setShown(value); from.current = value; return; }
    const start = performance.now();
    const base = from.current;
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / ms);
      setShown(Math.round(base + (value - base) * (1 - (1 - t) ** 3)));
      if (t < 1) frame = requestAnimationFrame(tick);
      else from.current = value;
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value, ms]);
  return shown;
}

export function CountUp({ value }: { value: number }) {
  return <>{useCountUp(value)}</>;
}

/** A moment card: a pebble on its sun, a title, a line and a button to put it away. */
function Moment({ kind, emoji, label, title, children, onClose, className }: { kind: PebbleKind; emoji: GameEmojiName; label: string; title: ReactNode; children?: ReactNode; onClose(): void; className?: string }) {
  const button = useRef<HTMLButtonElement>(null);
  useEffect(() => { button.current?.focus({ preventScroll: true }); }, []);
  return (
    <section role="status" aria-label={label} className={cn('pp-card pp-tape db-rise mt-3 mb-6 grid items-center gap-4 p-5 sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:gap-6', className)}>
      <Celebrate kind={kind} emoji={emoji} className="size-32 [&>[data-slot=pebble-friend]]:size-20" />
      <div className="min-w-0">
        <p className="font-hand text-[19px] text-pen">{label}</p>
        <h2 className="type-title mt-1 text-balance">{title}</h2>
        {children ? <div className="mt-1.5 text-[15px] text-muted-foreground">{children}</div> : null}
      </div>
      <Button ref={button} size="lg" onClick={onClose}>Nice</Button>
    </section>
  );
}

/** Today: the daily goal is done. Jade, once per day. */
export function GoalReachedMoment({ on, reached, day, minutes }: { on: boolean; reached: boolean; day: string; minutes: number }) {
  const key = 'socrat:goal-moment';
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!on || !reached || read(key) === day) return;
    write(key, day);
    setOpen(true);
    playInGame('streak');
  }, [on, reached, day]);
  if (!open) return null;
  return (
    <Moment kind="jade" emoji="target" label="Daily goal reached" title={`${minutes} minutes done today`} onClose={() => setOpen(false)}>
      That is today&apos;s goal. Keep going if you like, or stop here with it kept.
    </Moment>
  );
}

/** A new level, from skills proven: Ami, shown once per level. The first visit only records. */
export function LevelUpMoment({ on, proven }: { on: boolean; proven: number }) {
  const key = 'socrat:level-seen';
  const [open, setOpen] = useState(false);
  const level = levelFor(proven);
  useEffect(() => {
    if (!on) return;
    const seen = read(key);
    const seenIndex = seen === null ? null : Number(seen);
    if (seenIndex === null || Number.isNaN(seenIndex) || level.index < seenIndex) { write(key, String(level.index)); return; }
    if (!levelUpDue(proven, seenIndex)) return;
    write(key, String(level.index));
    setOpen(true);
    playInGame('finish');
  }, [on, proven, level.index]);
  if (!open) return null;
  return (
    <Moment kind="amethyst" emoji="gem" label={`Level ${level.index + 1}`} title={`You are a ${level.name} now`} onClose={() => setOpen(false)}>
      {proven} skills proven by passing their checks.{level.next ? ` ${level.next - proven} more to ${level.nextName}.` : ' The top level.'}
    </Moment>
  );
}

/** Session end, streak screen: the milestone ribbon and the freezes as frozen pebbles. */
export function StreakMilestone({ current, freezes }: { current: number; freezes: number }) {
  const hit = streakMilestone(current);
  const next = nextStreakMilestone(current);
  return (
    <div className="grid gap-3">
      {hit ? (
        <p className="db-ribbon db-pop w-fit"><GameEmoji name="flame" size={22} />{hit}-day milestone</p>
      ) : next ? (
        <p className="text-[14px] text-muted-foreground">{next - current} more {next - current === 1 ? 'day' : 'days'} to the {next}-day milestone</p>
      ) : null}
      {freezes > 0 ? <FrozenPebbles count={freezes} /> : null}
    </div>
  );
}

/** Freezes banked for a missed study day, as frozen pebbles. */
export function FrozenPebbles({ count, className }: { count: number; className?: string }) {
  const shown = Math.min(count, 5);
  return (
    <p className={cn('flex flex-wrap items-center gap-2 text-[14px] font-semibold', className)} aria-label={`${count} streak ${count === 1 ? 'freeze' : 'freezes'} saved`}>
      <span className="flex -space-x-2" aria-hidden="true">
        {Array.from({ length: shown }, (_, i) => (
          <span key={i} className="db-frozen relative"><PebbleFriend kind="sky" size={34} shadow={false} /><GameEmoji name="snow" size={16} className="absolute -right-1 -bottom-1" /></span>
        ))}
      </span>
      {count} {count === 1 ? 'freeze' : 'freezes'} saved
    </p>
  );
}

const STICKER: PebbleKind[] = ['amber', 'jade', 'amethyst', 'ember', 'sky'];
const STICKER_TONE = ['xp', 'correct', 'info', 'streak', 'wrong'] as const;

/** Badges as pebble stickers: earned ones in colour, the rest grey with how close they are. */
export function BadgeStickers({ badges }: { badges: { id: string; title: string; description: string; earned: boolean; value?: number; goal?: number }[] }) {
  if (!badges.length) return null;
  const earned = badges.filter(b => b.earned).length;
  return (
    <section aria-labelledby="badges-heading" className="grid gap-3">
      <h2 id="badges-heading" className="font-display text-2xl font-semibold tracking-[-0.03em]">Badges <span className="text-base font-semibold text-muted-foreground tabular-nums">{earned} of {badges.length}</span></h2>
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {badges.map((b, i) => (
          <li key={b.id} className={cn('pp-note grid justify-items-center gap-2 p-4 text-center', !b.earned && 'db-sticker-locked')} data-tone={b.earned ? STICKER_TONE[i % STICKER_TONE.length] : 'paper'} style={{ rotate: `${((i * 37) % 5) - 2}deg` }}>
            <span className="relative">
              <PebbleFriend kind={STICKER[i % STICKER.length]} mood={b.earned ? 'happy' : 'idle'} size={60} shadow={b.earned} />
              {b.earned ? <GameEmoji name="star" size={22} className="absolute -right-1 -bottom-1" /> : <GameEmoji name="lock" size={20} className="absolute -right-1 -bottom-1" />}
            </span>
            <span className="text-[15px] leading-tight font-bold">{b.title}</span>
            <span className="text-[13px] leading-snug text-muted-foreground">
              {b.earned ? b.description : b.goal ? `${Math.min(b.value ?? 0, b.goal)} of ${b.goal}` : b.description}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
