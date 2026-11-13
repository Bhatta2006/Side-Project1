'use client';

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { api } from '@/lib/api';
import { useSession } from '@/lib/session';
import { Button } from '@/components/ui/button';

interface Note { id: string; title: string; body: string; created_at: number }

/**
 * Notes an admin sent this learner (or everyone). Shown once: closing the panel marks them read.
 * Sits above the Ask Soc button, clear of the report thank-you at the top of the screen.
 */
export function AdminNotes() {
  const { profile } = useSession();
  const [items, setItems] = useState<Note[]>([]);

  useEffect(() => {
    if (!profile?.id) return;
    let live = true;
    api.get<{ items: Note[] }>('/me/notifications')
      .then(r => { if (live) setItems(r.items); })
      .catch(() => undefined);
    return () => { live = false; };
  }, [profile?.id]);

  if (!items.length) return null;
  const close = () => {
    const ids = items.map(i => i.id);
    setItems([]);
    api.post('/me/notifications/seen', { ids }).catch(() => undefined);
  };

  return createPortal(
    <aside
      role="status"
      aria-label="Message from the Socrat team"
      className="fixed inset-x-4 bottom-24 z-[70] grid max-h-[60dvh] gap-3 overflow-y-auto rounded-card border bg-card p-4 text-card-foreground shadow-floating animate-in fade-in slide-in-from-bottom-2 sm:right-4 sm:bottom-24 sm:left-auto sm:w-[380px]"
    >
      <p className="type-label text-muted-foreground">{items.length === 1 ? 'A message for you' : `${items.length} messages for you`}</p>
      <ul className="grid gap-3">
        {items.map(n => (
          <li key={n.id} className="text-[15px] leading-snug">
            {n.title ? <p className="font-semibold [overflow-wrap:anywhere]">{n.title}</p> : null}
            <p className="whitespace-pre-line [overflow-wrap:anywhere]">{n.body}</p>
          </li>
        ))}
      </ul>
      <div><Button size="sm" onClick={close}>Got it</Button></div>
    </aside>,
    document.body,
  );
}
