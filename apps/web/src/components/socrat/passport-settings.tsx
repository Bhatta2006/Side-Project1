'use client';

import { useEffect, useState } from 'react';
import { Copy, ExternalLink, Share2 } from '@/components/icons';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import type { PassportSettings } from '@/lib/types';
import { ErrorNote } from '@/components/common';
import { PassportCard } from '@/components/passport-view';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';

/** The learner's control for their public Skill Passport: on/off, copy, share, preview. */
export function PassportSettingsCard() {
  const [data, setData] = useState<PassportSettings | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [preview, setPreview] = useState(false);

  useEffect(() => {
    api.get<PassportSettings>('/me/passport').then(setData).catch(e => setError(explain(e)));
  }, []);

  async function toggle(next: boolean) {
    if (!data) return;
    setBusy(true);
    setError('');
    try {
      const saved = await api.put<Omit<PassportSettings, 'preview'>>('/me/passport', { public: next });
      setData({ ...data, ...saved });
      toast.success(next ? 'Your Skill Passport is public.' : 'Your Skill Passport is private. The link no longer works.');
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  const url = data?.path && typeof window !== 'undefined' ? `${window.location.origin}${data.path}` : '';
  const live = Boolean(data?.public && url);

  async function copy() {
    try { await navigator.clipboard.writeText(url); toast.success('Link copied.'); } catch { toast.error('Copy did not work. Select the link and copy it.'); }
  }

  return (
    <section aria-labelledby="passport-heading" className="paper rounded-card p-5 lg:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-2xl">
          <h2 id="passport-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">Skill Passport</h2>
          <p className="mt-1 text-[15px] text-muted-foreground">A public page of what you have proven: unaided solves, checks passed and skills mastered. It shows your display name and nothing else about you.</p>
        </div>
        {data ? (
          <label className="flex min-h-11 items-center gap-3 text-[15px] font-semibold">
            <Switch checked={data.public} disabled={busy} onCheckedChange={toggle} aria-describedby="passport-heading" />
            {data.public ? 'Public' : 'Private'}
          </label>
        ) : <Skeleton className="h-11 w-28 rounded-full" />}
      </div>

      {data ? (
        <div className="mt-5 grid gap-3">
          {live ? (
            <div className="flex flex-wrap items-center gap-2">
              <input readOnly value={url} aria-label="Your passport link" onFocus={e => e.currentTarget.select()} className="h-11 min-w-0 flex-1 basis-64 rounded-control border border-border-strong bg-background px-3 text-[15px]" />
              <Button variant="outline" onClick={copy}><Copy data-icon="inline-start" /> Copy</Button>
              <Button asChild variant="outline">
                <a href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`} target="_blank" rel="noopener noreferrer">
                  <Share2 data-icon="inline-start" /> Share on LinkedIn<span className="sr-only"> (opens LinkedIn)</span>
                </a>
              </Button>
              <Button asChild variant="ghost"><a href={data.path!} target="_blank" rel="noopener noreferrer">Open<ExternalLink data-icon="inline-end" /></a></Button>
            </div>
          ) : (
            <p className="text-[15px]">Turn it on to get a link you can add to your resume or LinkedIn. Turning it off stops the link working straight away.</p>
          )}
          <div><Button variant="link" className="px-0" onClick={() => setPreview(true)}>Preview what others see</Button></div>
        </div>
      ) : null}
      {error ? <ErrorNote message={error} className="mt-4" /> : null}

      <Dialog open={preview} onOpenChange={setPreview}>
        <DialogContent className="sm:max-w-3xl">
          <DialogHeader><DialogTitle>Passport preview</DialogTitle></DialogHeader>
          {data ? <PassportCard passport={data.preview} headingLevel={2} /> : null}
        </DialogContent>
      </Dialog>
    </section>
  );
}
