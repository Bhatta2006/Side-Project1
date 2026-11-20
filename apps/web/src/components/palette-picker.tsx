'use client';
import { useEffect, useState } from 'react';
import { Check } from '@/components/icons';
import { play, setSoundOn, soundOn } from '@/lib/game-sound';
import { PALETTES, usePalette, type ColourMode, type Look } from '@/lib/palette';
import { cn } from '@/lib/utils';

const MODES: { id: ColourMode; label: string }[] = [
  { id: 'light', label: 'Light' },
  { id: 'dark', label: 'Dark' },
  { id: 'system', label: 'Match device' },
];

const GROUPS: { look: Look; title: string; note: string }[] = [
  { look: 'daybreak', title: 'Daybreak', note: 'Bright and playful: chunky buttons, the pebble friends.' },
  { look: 'notebook', title: 'Notebook', note: 'The hand-drawn paper look.' },
];

/** Settings: pick a look and its colours, and whether it is light or dark. Saved to the account. */
export function PalettePicker() {
  const [pref, set] = usePalette();
  const [sound, setSound] = useState(true);
  useEffect(() => { setSound(soundOn()); }, []);
  const darkPreview = pref.mode === 'dark';
  return (
    <div className="grid gap-5 py-5">
      <div>
        <p id="palette-label" className="font-semibold">Colours</p>
        <p className="text-sm text-muted-foreground">Saved to your account, so every device matches.</p>
      </div>

      {GROUPS.map(g => (
        <div key={g.look} className="grid gap-3">
          <div>
            <p id={`palette-${g.look}`} className="text-sm font-bold">{g.title}</p>
            <p className="text-xs text-muted-foreground">{g.note}</p>
          </div>
          <div role="radiogroup" aria-labelledby={`palette-label palette-${g.look}`} className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {PALETTES.filter(p => p.look === g.look).map(p => {
              const on = pref.palette === p.id;
              const [a, b, c, d] = darkPreview ? p.dark : p.light;
              return (
                <button
                  key={p.id}
                  type="button"
                  role="radio"
                  aria-checked={on}
                  onClick={() => set({ palette: p.id })}
                  className={cn('group grid gap-2 rounded-[6px] border p-2 text-left transition-colors hover:bg-raised', on ? 'border-ink outline-2 outline-ink-you' : 'border-line')}
                >
                  {g.look === 'daybreak' ? (
                    // A tiny Daybreak screen: the wash, a chunky button on its ledge, and a path stone.
                    <span aria-hidden="true" className="relative block h-16 overflow-hidden rounded-[12px]" style={{ background: d }}>
                      <span className="absolute bottom-3 left-3 h-5 w-16 rounded-[8px]" style={{ background: a, boxShadow: `0 3px 0 ${c}` }} />
                      <span className="absolute top-2.5 right-4 size-7 rounded-full" style={{ background: b, boxShadow: `0 3px 0 ${c}` }} />
                      <span className="absolute top-3 left-3 h-1.5 w-9 rounded-full bg-[#ffb224]" />
                      {on ? <span className="absolute right-1.5 bottom-1.5 grid size-5 place-items-center rounded-full bg-white text-[#221a3a] shadow-sm"><Check className="size-3.5" /></span> : null}
                    </span>
                  ) : (
                    // A tiny notebook: the desk, a sheet on it, a button and a highlighter stroke.
                    <span aria-hidden="true" className="relative block h-16 overflow-hidden rounded-[4px]" style={{ background: a }}>
                      <span className="absolute inset-y-2 left-3 right-6 -rotate-2 rounded-[2px] shadow-sm" style={{ background: b }}>
                        <span className="absolute top-2 left-2 h-1.5 w-10 rounded-full" style={{ background: d }} />
                        <span className="absolute bottom-2 left-2 h-3 w-12 rounded-[3px] border border-black/40" style={{ background: c }} />
                      </span>
                      {on ? <span className="absolute top-1.5 right-1.5 grid size-5 place-items-center rounded-full bg-ink text-paper"><Check className="size-3.5" /></span> : null}
                    </span>
                  )}
                  <span>
                    <span className="block font-semibold">{p.name}</span>
                    <span className="block text-xs leading-snug text-muted-foreground">{p.note}</span>
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      ))}

      <div role="radiogroup" aria-label="Light or dark" className="flex flex-wrap gap-2">
        {MODES.map(m => (
          <button
            key={m.id}
            type="button"
            role="radio"
            aria-checked={pref.mode === m.id}
            onClick={() => set({ mode: m.id })}
            className={cn('rounded-[4px] border border-line px-4 py-2 text-sm', pref.mode === m.id ? 'bg-hi-select font-bold' : 'hover:bg-raised')}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Socrat's own answer sounds and a short buzz on phones; kept in this browser. */}
      <label className="flex items-center justify-between gap-4 rounded-[4px] border border-line px-4 py-3">
        <span>
          <span className="block font-semibold">Sounds</span>
          <span className="block text-xs text-muted-foreground">A pebble chime for right answers, a soft knock for wrong ones.</span>
        </span>
        <input type="checkbox" className="size-5 accent-[var(--db-primary)]" checked={sound} onChange={e => { setSound(e.target.checked); setSoundOn(e.target.checked); if (e.target.checked) play('correct'); }} />
      </label>
    </div>
  );
}
