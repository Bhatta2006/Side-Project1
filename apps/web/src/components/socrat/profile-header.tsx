'use client';
// The header on Progress, in paper: Soc on a taped card, the level tube from skills proven and
// four sticky-note tiles. Game styling around the evidence, never on it: the numbers are the server's.
import { evidencePoints, levelFor } from '@/lib/game';
import { CountUp, FrozenPebbles } from './game-moments';
import { GameEmoji, type GameEmojiName } from './game-emoji';
import { PebbleFriend } from './pebble-friend';

function Tile({ icon, value, label, tone, tilt }: { icon: GameEmojiName; value: number; label: string; tone: 'streak' | 'xp' | 'correct' | 'info'; tilt: number }) {
  return (
    <li className="pp-note grid gap-1 p-3.5" data-tone={tone} style={{ rotate: `${tilt}deg` }}>
      <span className="flex items-center gap-1.5 text-[13px] font-semibold"><GameEmoji name={icon} size={22} />{label}</span>
      <span className="font-display text-[30px] leading-none tabular-nums"><CountUp value={value} /></span>
    </li>
  );
}

export function ProfileHeader({ name, streak, freezes, proven, mastered }: { name: string; streak: number; freezes: number; proven: number; mastered: number }) {
  const level = levelFor(proven);
  const xp = evidencePoints({ learned: proven, mastered });
  return (
    <section aria-label="Your level and totals" className="mb-8 grid gap-5">
      <div className="pp-card pp-tape relative mt-2 flex items-center gap-4 p-5 sm:gap-6 sm:p-6">
        <PebbleFriend kind="soc" mood="happy" size={80} className="db-bob flex-none" />
        <div className="min-w-0 flex-1">
          <p className="font-hand text-[19px] text-pen">{name ? `${name}, level ${level.index + 1}` : `Level ${level.index + 1}`}</p>
          <p className="type-display-m leading-tight">{level.name}</p>
          <div className="mt-3 grid gap-1.5">
            <span className="db-level-track" role="progressbar" aria-label={`Progress to ${level.nextName ?? 'the top level'}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={level.percent}>
              <span style={{ width: `${Math.max(level.percent, 4)}%` }} />
            </span>
            <span className="text-[13px] text-muted-foreground">
              {level.next ? `${level.next - level.proven} more proven ${level.next - level.proven === 1 ? 'skill' : 'skills'} to ${level.nextName}` : 'Top level reached'}
            </span>
          </div>
        </div>
        <GameEmoji name="gem" size={40} className="absolute -top-3 right-5 hidden rotate-12 sm:block" />
      </div>
      <ul className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Tile icon="flame" tone="streak" value={streak} label="Day streak" tilt={-1} />
        <Tile icon="bolt" tone="xp" value={xp} label="Evidence XP" tilt={0.8} />
        <Tile icon="check" tone="correct" value={proven} label="Skills proven" tilt={-0.6} />
        <Tile icon="gem" tone="info" value={mastered} label="Mastered" tilt={1.2} />
      </ul>
      {freezes > 0 ? <FrozenPebbles count={freezes} /> : null}
    </section>
  );
}
