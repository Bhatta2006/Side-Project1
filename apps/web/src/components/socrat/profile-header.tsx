'use client';
// The Daybreak header on Progress: Soc on the main colour, the level bar from skills proven and
// four stat tiles. Game styling around the evidence, never on it: the numbers are the server's.
import { cn } from '@/lib/utils';
import { evidencePoints, levelFor } from '@/lib/game';
import { CountUp, FrozenPebbles } from './game-moments';
import { GameEmoji, type GameEmojiName } from './game-emoji';
import { PebbleFriend } from './pebble-friend';

function Tile({ icon, value, label, tone }: { icon: GameEmojiName; value: number; label: string; tone: 'streak' | 'xp' | 'correct' | 'primary' }) {
  return (
    <li className={cn('db-stat grid gap-1 p-3.5', `db-stat-${tone}`)}>
      <span className="flex items-center gap-1.5 text-[12.5px] font-extrabold"><GameEmoji name={icon} size={20} />{label}</span>
      <span className="font-display text-[28px] leading-none font-bold tabular-nums"><CountUp value={value} /></span>
    </li>
  );
}

export function ProfileHeader({ name, streak, freezes, proven, mastered }: { name: string; streak: number; freezes: number; proven: number; mastered: number }) {
  const level = levelFor(proven);
  const xp = evidencePoints({ learned: proven, mastered });
  return (
    <section aria-label="Your level and totals" className="db-only mb-6 grid gap-4">
      <div className="db-profile-hero relative flex items-center gap-4 overflow-hidden p-5 sm:gap-6 sm:p-6">
        <PebbleFriend kind="soc" mood="happy" size={84} className="db-bob flex-none" />
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-extrabold opacity-85">{name ? `${name}, level ${level.index + 1}` : `Level ${level.index + 1}`}</p>
          <h1 className="text-[30px] leading-tight">{level.name}</h1>
          <div className="mt-3 grid gap-1.5">
            <span className="db-level-track" role="progressbar" aria-label={`Progress to ${level.nextName ?? 'the top level'}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={level.percent}>
              <span style={{ width: `${Math.max(level.percent, 4)}%` }} />
            </span>
            <span className="text-[13px] font-bold opacity-90">
              {level.next ? `${level.next - level.proven} more proven ${level.next - level.proven === 1 ? 'skill' : 'skills'} to ${level.nextName}` : 'Top level reached'}
            </span>
          </div>
        </div>
        <PebbleFriend kind="amethyst" size={48} className="absolute -top-2 right-4 hidden rotate-12 sm:block" shadow={false} />
      </div>
      <ul className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Tile icon="flame" tone="streak" value={streak} label="Day streak" />
        <Tile icon="bolt" tone="xp" value={xp} label="Evidence XP" />
        <Tile icon="check" tone="correct" value={proven} label="Skills proven" />
        <Tile icon="gem" tone="primary" value={mastered} label="Mastered" />
      </ul>
      {freezes > 0 ? <FrozenPebbles count={freezes} /> : null}
    </section>
  );
}
