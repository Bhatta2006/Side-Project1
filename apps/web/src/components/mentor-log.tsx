'use client';

import { useEffect, useState } from 'react';
import { Undo2 } from '@/components/icons';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { formatStamp } from '@/lib/routes';

interface Entry { id: string; at: number; kind: string; concept: string; title: string; why: string; undone: boolean }
interface MentorView { log: Entry[]; recall: string[] }

/** What your mentor changed about how you are taught, and why. Admin-only while it is tested. */
export function MentorLog() {
  const [view, setView] = useState<MentorView | null>(null);
  const [busy, setBusy] = useState('');

  useEffect(() => {
    // 404 means the mentor is not enabled for this account: show nothing.
    api.post<MentorView>('/mentor/refresh').then(setView).catch(() => setView(null));
  }, []);

  async function undo(id: string) {
    setBusy(id);
    try { setView(await api.post<MentorView>('/mentor/undo', { id })); }
    catch (e) { toast.error(explain(e)); }
    finally { setBusy(''); }
  }

  const shown = view?.log.slice(0, 6) ?? [];
  if (!view || !shown.length) return null;
  return (
    <Card aria-labelledby="mentor-heading">
      <div className="grid gap-3 px-(--card-spacing)">
        <div>
          <h2 id="mentor-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">Your mentor</h2>
          <p className="text-sm text-muted-foreground">Small changes to how you are taught, each with its reason. Undo any of them.</p>
        </div>
        <ul className="grid gap-2">
          {shown.map(e => (
            <li key={e.id} className="flex items-start justify-between gap-3 rounded-md border p-3 text-sm">
              <div className={e.undone ? 'text-muted-foreground line-through' : ''}>
                <p className="font-medium">{e.title}</p>
                <p className="text-muted-foreground">{e.why}</p>
                <p className="mt-1 text-xs text-muted-foreground">{formatStamp(e.at)}</p>
              </div>
              {e.undone ? null : (
                <Button size="sm" variant="outline" disabled={busy === e.id} onClick={() => undo(e.id)}>
                  <Undo2 data-icon="inline-start" /> Undo
                </Button>
              )}
            </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}
