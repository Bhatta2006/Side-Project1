'use client';

import { Minus, Plus, Settings2 } from 'lucide-react';
import type { EditorPrefs } from '@/lib/editor-prefs';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

/** Font size and indent for the code editor. */
export default function EditorSettings({ prefs, setPrefs }: { prefs: EditorPrefs; setPrefs(patch: Partial<EditorPrefs>): void }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Editor settings"><Settings2 /></Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="grid w-60 gap-4">
        <div className="grid gap-2">
          <p className="text-sm font-medium">Font size</p>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon-sm" aria-label="Smaller text" disabled={prefs.fontSize <= 12} onClick={() => setPrefs({ fontSize: prefs.fontSize - 1 })}><Minus /></Button>
            <span className="w-12 text-center text-sm tabular-nums" aria-live="polite">{prefs.fontSize} px</span>
            <Button variant="outline" size="icon-sm" aria-label="Larger text" disabled={prefs.fontSize >= 20} onClick={() => setPrefs({ fontSize: prefs.fontSize + 1 })}><Plus /></Button>
          </div>
        </div>
        <div className="grid gap-2">
          <p className="text-sm font-medium" id="indent-label">Indent</p>
          <div className="flex gap-2" role="radiogroup" aria-labelledby="indent-label">
            {([2, 4] as const).map(n => (
              <Button key={n} variant={prefs.tabSize === n ? 'default' : 'outline'} size="sm" role="radio" aria-checked={prefs.tabSize === n} onClick={() => setPrefs({ tabSize: n })}>{n} spaces</Button>
            ))}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
