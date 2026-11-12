'use client';

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { api } from '@/lib/api';
import { useSession } from '@/lib/session';
import { Soc } from '@/components/socrat/illustration';
import { Button } from '@/components/ui/button';

interface Thanks { id: string; category: string | null; message: string; resolved_at: number | null }

const short = (text: string) => (text.length > 90 ? `${text.slice(0, 87).trimEnd()}…` : text);

/**
 * A thank-you from Soc when an admin resolves something the learner reported. Shown once:
 * closing it marks those reports as thanked. Off unless the server has report thanks switched on.
 */
export function ReportThanks() {
  const { profile } = useSession();
  const [items, setItems] = useState<Thanks[]>([]);

  useEffect(() => {
    if (!profile?.id) return;
    let live = true;
    api.get<{ items: Thanks[] }>('/problem-reports/thanks')
      .then(r => { if (live) setItems(r.items); })
      .catch(() => undefined);
    return () => { live = false; };
  }, [profile?.id]);

  if (!items.length) return null;
  const close = () => {
    const ids = items.map(i => i.id);
    setItems([]);
    api.post('/problem-reports/thanks/seen', { ids }).catch(() => undefined);
  };

  return createPortal(
    <aside
      role="status"
      aria-label="Thank you from Soc"
      className="fixed inset-x-4 top-4 z-[70] flex gap-3 rounded-card border bg-card p-4 text-card-foreground shadow-floating animate-in fade-in slide-in-from-top-2 sm:left-auto sm:w-[360px]"
    >
      <Soc size={44} mood="proud" className="flex-none" />
      <div className="min-w-0 flex-1 text-[14px] leading-snug">
        <p className="font-hand text-[22px] leading-tight text-pen">thank you!</p>
        {items.length === 1 ? (
          <p className="mt-1">You reported “{short(items[0].message)}”. It’s fixed now. Thanks for helping make Socrat better.</p>
        ) : (
          <>
            <p className="mt-1">{items.length} things you reported are fixed now. Thanks for helping make Socrat better.</p>
            <ul className="mt-1.5 grid list-disc gap-0.5 pl-4 text-muted-foreground">
              {items.slice(0, 3).map(i => <li key={i.id}>{short(i.message)}</li>)}
            </ul>
          </>
        )}
        <Button size="sm" className="mt-3" onClick={close}>You’re welcome</Button>
      </div>
    </aside>,
    document.body,
  );
}
