'use client';
// The whole course as one long trail on the desk: every module in order, each opened by a
// milestone slip, its skills as stones (skill-path.tsx), stickers and doodles in the margins.
// The page scrolls the trail; on load it brings the current stone into view.
import dynamic from 'next/dynamic';
import { useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';
import { SkillPath, type PathNode } from './skill-path';
import { PebbleFriend, type PebbleKind } from './pebble-friend';

// The sticker catalogue is large: load it after the page paints.
const Sticker = dynamic(() => import('@/components/ui/sticker').then(m => m.Sticker), { ssr: false });

export interface PathModule { id: string; title: string; nodes: PathNode[]; current: boolean; locked: boolean }

const DONE = ['mastered', 'practised', 'learned', 'assumed'];

/**
 * What the margin says about a milestone. Every mark means one thing, matching the pebble family
 * (pebble-friend.tsx): Amber hands out quests, Jade brings back reviews; a stamp is a milestone
 * reached, a pencil cup means lessons are still being written. Nothing is decoration only.
 */
function markFor(m: PathModule, done: number): { pebble?: PebbleKind; sticker?: string; note: string } | null {
  const total = m.nodes.length;
  if (total && done === total) return { sticker: 'stamp-approved', note: 'milestone reached' };
  const reviews = m.nodes.filter(n => n.reviewDue).length;
  if (reviews) return { pebble: 'jade', note: `${reviews} review${reviews === 1 ? '' : 's'} due here` };
  if (m.current) return { pebble: 'amber', note: `quest: ${total - done} skill${total - done === 1 ? '' : 's'} to go` };
  if (m.nodes.some(n => n.writing)) return { sticker: 'pencil-cup', note: 'lessons being written' };
  return null;
}

export function CoursePath({ modules, startLabel }: { modules: PathModule[]; startLabel: string }) {
  const root = useRef<HTMLDivElement>(null);
  // Bring the current stone into view once, when it is out of sight.
  useEffect(() => {
    const el = root.current?.querySelector<HTMLElement>('[data-current]');
    if (!el) return;
    const box = el.getBoundingClientRect();
    if (box.top < 0 || box.bottom > window.innerHeight) el.scrollIntoView({ block: 'center' });
  }, []);

  return (
    <div ref={root} className="relative mx-auto w-full max-w-[880px] pt-2 pb-16">
      {modules.map((m, i) => {
        const done = m.nodes.filter(n => DONE.includes(n.status)).length;
        const mark = markFor(m, done);
        return (
          <section key={m.id} aria-labelledby={`mod-${m.id}`} className="relative lg:min-h-[200px]">
            {/* The milestone card, flat, in the empty space left of the trail (above it on narrow screens). */}
            <div className="relative z-10 mx-auto mb-8 w-fit max-w-full px-4 pt-4 lg:absolute lg:top-2 lg:left-0 lg:mx-0 lg:mb-0 lg:w-[240px] lg:px-0">
              <div className={cn('paper relative rounded-[6px] px-5 py-3 shadow-[3px_3px_0_var(--pp-ink,#15161E)] lg:text-left', 'text-center', m.current && 'outline-3 outline-offset-4 outline-[var(--ll-hi,var(--highlight))]', m.locked && 'opacity-75')}>
                <span aria-hidden="true" className="absolute -top-3 left-1/2 h-5 w-16 -translate-x-1/2 bg-[color-mix(in_srgb,var(--ll-paper-shade,#e8e2d4),transparent_25%)] shadow-[0_1px_0_rgba(0,0,0,0.08)]" />
                <p className="type-label text-muted-foreground">{m.current ? 'Next milestone' : 'Milestone'} · {done}/{m.nodes.length}</p>
                <h3 id={`mod-${m.id}`} className="font-display text-lg leading-tight font-semibold tracking-[-0.02em]">{m.title}</h3>
                {m.current ? <p className="font-script mt-1 text-[18px] text-red">you are here</p> : null}
              </div>
            </div>

            {/* Margin stickers, each saying something true about this milestone (wide screens only). */}
            {mark ? (
              <div aria-hidden="true" className="pointer-events-none absolute top-6 right-0 hidden w-[200px] flex-col items-center gap-1 text-center lg:flex">
                {mark.pebble ? <PebbleFriend kind={mark.pebble} size={64} className="db-bob" /> : <Sticker name={mark.sticker!} size={80} rotate={-4} seed={`path-${m.id}`} />}
                <span className="font-hand text-[20px] leading-tight text-pen">{mark.note}</span>
              </div>
            ) : null}

            <SkillPath nodes={m.nodes} label={m.title} startLabel={startLabel} friend={false} />
            {i < modules.length - 1 ? (
              <svg aria-hidden="true" className="mx-auto -mt-6 mb-0 block" width="4" height="36"><line x1="2" y1="0" x2="2" y2="36" stroke="var(--ll-pencil-mark, var(--border))" strokeWidth="2.5" strokeLinecap="round" strokeDasharray="1 9" /></svg>
            ) : (
              <div className="mx-auto mt-2 flex w-fit flex-col items-center gap-1 text-center">
                <Sticker name="first-place" size={72} rotate={0} seed="path-finish" />
                <p className="font-hand text-[20px] text-pen">the finish line</p>
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
