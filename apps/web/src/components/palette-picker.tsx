'use client';
import { Check } from '@/components/icons';
import { PALETTES, usePalette, type ColourMode } from '@/lib/palette';
import { cn } from '@/lib/utils';

const MODES: { id: ColourMode; label: string }[] = [
  { id: 'light', label: 'Light' },
  { id: 'dark', label: 'Dark' },
  { id: 'system', label: 'Match device' },
];

/** Settings: pick the notebook's colours and whether the desk is light or dark. Saved to the account. */
export function PalettePicker() {
  const [pref, set] = usePalette();
  const darkPreview = pref.mode === 'dark';
  return (
    <div className="grid gap-4 py-5">
      <div>
        <p id="palette-label" className="font-semibold">Colours</p>
        <p className="text-sm text-muted-foreground">The desk, paper and pens across Socrat. Saved to your account, so every device matches.</p>
      </div>

      <div role="radiogroup" aria-labelledby="palette-label" className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {PALETTES.map(p => {
          const on = pref.palette === p.id;
          const [desk, sheet, marker, hi] = darkPreview ? p.dark : p.light;
          return (
            <button
              key={p.id}
              type="button"
              role="radio"
              aria-checked={on}
              onClick={() => set({ palette: p.id })}
              className={cn('group grid gap-2 rounded-[6px] border p-2 text-left transition-colors hover:bg-raised', on ? 'border-ink outline-2 outline-ink-you' : 'border-line')}
            >
              {/* A tiny notebook: the desk, a sheet on it, a button and a highlighter stroke. */}
              <span aria-hidden="true" className="relative block h-16 overflow-hidden rounded-[4px]" style={{ background: desk }}>
                <span className="absolute inset-y-2 left-3 right-6 -rotate-2 rounded-[2px] shadow-sm" style={{ background: sheet }}>
                  <span className="absolute top-2 left-2 h-1.5 w-10 rounded-full" style={{ background: hi }} />
                  <span className="absolute bottom-2 left-2 h-3 w-12 rounded-[3px] border border-black/40" style={{ background: marker }} />
                </span>
                {on ? <span className="absolute top-1.5 right-1.5 grid size-5 place-items-center rounded-full bg-ink text-paper"><Check className="size-3.5" /></span> : null}
              </span>
              <span>
                <span className="block font-semibold">{p.name}</span>
                <span className="block text-xs leading-snug text-muted-foreground">{p.note}</span>
              </span>
            </button>
          );
        })}
      </div>

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
    </div>
  );
}
