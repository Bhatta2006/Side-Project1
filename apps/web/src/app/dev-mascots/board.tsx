'use client';
import { useState } from 'react';
import { Paper } from '@/components/ui/paper';
import { SocFigure } from '@/components/socrat/soc';
import { SocBlob, BLOB_KEYS, BLOB_MOODS, BLOB_SHAPES, BLOB_TREATMENTS, type BlobShape, type BlobTreatment } from '@/components/socrat/soc-blob';
import { cn } from '@/lib/utils';
import { PebbleLab } from './PebbleLab';

const TREAT: Record<BlobTreatment, string> = { ink: 'Ink silhouette', flat: 'Flat colour', colour: 'Marker + outline', sketch: 'Pencil sketch' };

export default function Board() {
  const [focus, setFocus] = useState<BlobShape>('cloud');
  const [treat, setTreat] = useState<BlobTreatment>('ink');
  const chip = (on: boolean) => cn('rounded-[4px] border border-line px-3 py-1.5 text-sm', on ? 'bg-hi-select font-bold text-ink' : 'bg-slip');
  return (
    <main className="min-h-dvh px-4 py-8 sm:px-8">
      <div className="mx-auto grid max-w-6xl gap-6">
        <header className="flex flex-wrap items-end gap-6">
          <div className="grid gap-1">
            <p className="font-script text-xl text-red">pick a Soc</p>
            <h1 className="font-display text-4xl">Mascot directions, round two</h1>
            <p className="max-w-2xl text-muted-foreground">One soft silhouette, two small eyes, nothing else, so Soc reads the same at 16px and 300px. Nine shapes, four treatments, four moods.</p>
          </div>
          <div className="ml-auto flex items-center gap-3">
            <SocFigure size={64} books />
            <span className="text-sm text-muted-foreground">Soc today</span>
          </div>
        </header>

        <PebbleLab />

        <h2 className="mt-6 font-display text-3xl">Round two</h2>
        <div className="grid gap-2">
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="Shape">
            {BLOB_KEYS.map((k, i) => <button key={k} role="tab" aria-selected={focus === k} onClick={() => setFocus(k)} className={chip(focus === k)}>{i + 1}. {BLOB_SHAPES[k].name}</button>)}
          </div>
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="Treatment">
            {BLOB_TREATMENTS.map(t => <button key={t} role="tab" aria-selected={treat === t} onClick={() => setTreat(t)} className={chip(treat === t)}>{TREAT[t]}</button>)}
          </div>
        </div>

        <Paper as="section" stock="paper" tape="top" seed={`focus-${focus}`} className="grid gap-5 p-6">
          <div>
            <h2 className="font-display text-3xl">{BLOB_SHAPES[focus].name}</h2>
            <p className="text-muted-foreground">{BLOB_SHAPES[focus].note}</p>
          </div>
          <div className="flex flex-wrap items-end gap-4">
            {BLOB_MOODS.map(m => (
              <figure key={m} className="grid justify-items-center gap-1">
                <SocBlob shape={focus} treatment={treat} mood={m} size={180} />
                <figcaption className="text-sm text-muted-foreground">{m}</figcaption>
              </figure>
            ))}
          </div>
          <div className="flex flex-wrap items-end gap-6">
            {BLOB_TREATMENTS.map(t => (
              <figure key={t} className="grid justify-items-center gap-1">
                <div className="flex items-end gap-2"><SocBlob shape={focus} treatment={t} size={96} /><SocBlob shape={focus} treatment={t} size={40} /><SocBlob shape={focus} treatment={t} size={24} /></div>
                <figcaption className="text-sm text-muted-foreground">{TREAT[t]}</figcaption>
              </figure>
            ))}
          </div>
        </Paper>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {BLOB_KEYS.map((k, i) => (
            <button key={k} onClick={() => setFocus(k)} className="text-left">
              <Paper stock={i % 3 === 1 ? 'sticky-yellow' : 'card'} seed={`all-${k}`} className={cn('grid justify-items-center gap-2 p-4', focus === k && 'outline-2 outline-ink-you')}>
                <div className="flex items-end gap-1"><SocBlob shape={k} treatment="ink" size={88} /><SocBlob shape={k} treatment="flat" size={64} /></div>
                <span className="font-display text-lg">{BLOB_SHAPES[k].name}</span>
              </Paper>
            </button>
          ))}
        </div>

        <Paper as="section" stock="card" tape="top" seed="lineup" className="grid gap-3 overflow-x-auto p-5" aria-label="Line-up">
          <h2 className="font-display text-2xl">Line-up</h2>
          <div id="lineup" className="grid w-max grid-cols-[8rem_repeat(9,6.5rem)] items-center gap-y-2">
            <span />
            {BLOB_KEYS.map(k => <span key={k} className="text-center text-sm text-muted-foreground">{BLOB_SHAPES[k].name}</span>)}
            {BLOB_TREATMENTS.map(t => (
              <div key={t} className="contents">
                <span className="text-sm font-bold">{TREAT[t]}</span>
                {BLOB_KEYS.map(k => <div key={k} className="grid place-items-center"><SocBlob shape={k} treatment={t} size={92} /></div>)}
              </div>
            ))}
          </div>
        </Paper>
      </div>
    </main>
  );
}
