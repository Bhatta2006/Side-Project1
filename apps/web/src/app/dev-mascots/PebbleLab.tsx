'use client';
import { useState } from 'react';
import { Paper } from '@/components/ui/paper';
import {
  SocPebble, PEBBLE_FINISHES, PEBBLE_KEYS, PEBBLE_MOODS, PEBBLE_PROPS, PEBBLE_SHAPES,
  type PebbleFinish, type PebbleProp, type PebbleShape,
} from '@/components/socrat/soc-pebble';
import { cn } from '@/lib/utils';

const FINISHES = Object.keys(PEBBLE_FINISHES) as PebbleFinish[];
const PROPS = Object.keys(PEBBLE_PROPS) as PebbleProp[];

/** The pebble, explored: six shapes by six finishes, then moods and props for the picked pair. */
export function PebbleLab() {
  const [shape, setShape] = useState<PebbleShape>('river');
  const [finish, setFinish] = useState<PebbleFinish>('basalt');
  const [prop, setProp] = useState<PebbleProp>('none');
  const chip = (on: boolean) => cn('rounded-[4px] border border-line px-3 py-1.5 text-sm', on ? 'bg-hi-select font-bold text-ink' : 'bg-slip');
  return (
    <section className="grid gap-4" aria-labelledby="pebble-lab">
      <div>
        <p className="font-script text-xl text-red">the stonemason&apos;s pebble</p>
        <h2 id="pebble-lab" className="font-display text-3xl">Pebble lab</h2>
        <p className="max-w-2xl text-muted-foreground">Black stone with real texture, six shapes, plus the drawn styles: stone colour with an ink outline, ink-dot eyes, Socrates&apos; brows. Click any pebble to look closer.</p>
      </div>

      <Paper as="div" stock="card" tape="top" seed="pebble-grid" className="overflow-x-auto p-5">
        <div id="pebble-grid" className="grid w-max grid-cols-[7rem_repeat(6,7rem)] items-center gap-y-2">
          <span />
          {FINISHES.map(f => <span key={f} className="text-center text-sm font-bold">{PEBBLE_FINISHES[f]}</span>)}
          {PEBBLE_KEYS.map(k => (
            <div key={k} className="contents">
              <span className="text-sm text-muted-foreground">{PEBBLE_SHAPES[k]}</span>
              {FINISHES.map(f => (
                <button key={f} onClick={() => { setShape(k); setFinish(f); }} aria-label={`${PEBBLE_SHAPES[k]}, ${PEBBLE_FINISHES[f]}`}
                  className={cn('grid place-items-center rounded-[4px] py-1', shape === k && finish === f && 'bg-hi-select')}>
                  <SocPebble shape={k} finish={f} size={100} />
                </button>
              ))}
            </div>
          ))}
        </div>
      </Paper>

      <Paper as="div" stock="paper" tape="corner" seed={`pebble-${shape}-${finish}`} className="grid gap-4 p-6">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="mr-2 font-display text-2xl">{PEBBLE_SHAPES[shape]} · {PEBBLE_FINISHES[finish]}</h3>
          {PROPS.map(p => <button key={p} onClick={() => setProp(p)} className={chip(prop === p)}>{PEBBLE_PROPS[p]}</button>)}
        </div>
        <div id="pebble-moods" className="flex flex-wrap items-end gap-4">
          {PEBBLE_MOODS.map(m => (
            <figure key={m} className="grid justify-items-center gap-1">
              <SocPebble shape={shape} finish={finish} prop={prop} mood={m} size={180} />
              <figcaption className="text-sm text-muted-foreground">{m}</figcaption>
            </figure>
          ))}
          <figure className="grid justify-items-center gap-2">
            <div className="flex items-end gap-2"><SocPebble shape={shape} finish={finish} size={56} /><SocPebble shape={shape} finish={finish} size={32} /><SocPebble shape={shape} finish={finish} size={20} /></div>
            <figcaption className="text-sm text-muted-foreground">avatar sizes</figcaption>
          </figure>
        </div>
      </Paper>
    </section>
  );
}
