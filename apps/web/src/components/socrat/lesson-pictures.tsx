'use client';
import { useEffect, useMemo, useState } from 'react';
import { ExternalLink } from '@/components/icons';
import { api } from '@/lib/api';

export interface Picture {
  /** The lesson heading this picture belongs under ("" for a lesson without headings). */
  section: string;
  src: string;
  title: string;
  source_url: string;
  provider: 'wikimedia' | 'openverse' | 'web';
  credit: string;
  license: string;
  license_url: string;
  width: number;
  height: number;
}

const FROM: Record<Picture['provider'], string> = { wikimedia: 'Wikimedia Commons', openverse: 'Openverse', web: 'the web' };

/**
 * Pictures for a lesson, one per section (GET /concepts/{id}/images), by section heading.
 * Empty when the feature is off or nothing fits: the lesson stands on its own.
 */
export function useLessonPictures(concept: string): Map<string, Picture> {
  const [items, setItems] = useState<Picture[]>([]);
  useEffect(() => {
    let current = true;
    setItems([]);
    api.get<{ items: Picture[] }>(`/concepts/${concept}/images`)
      .then(r => { if (current) setItems(r.items); })
      .catch(() => undefined);
    return () => { current = false; };
  }, [concept]);
  return useMemo(() => new Map(items.map(p => [p.section, p])), [items]);
}

/** One picture inside the lesson text: a card with what it shows, the image and its credit. */
export function LessonFigure({ picture }: { picture: Picture }) {
  const [open, setOpen] = useState(false);
  const [broken, setBroken] = useState(false);
  if (broken) return null;
  return (
    <figure className="my-6 grid gap-3 rounded-card border border-line bg-card p-4">
      {picture.title ? <figcaption className="text-[15px] text-foreground">{picture.title}</figcaption> : null}
      <button type="button" onClick={() => setOpen(true)} className="block overflow-hidden rounded-[4px] bg-raised" aria-label={`Show larger: ${picture.title || 'picture'}`}>
        {/* eslint-disable-next-line @next/next/no-img-element -- remote images from many hosts, served by their providers */}
        <img src={picture.src} alt={picture.title} loading="lazy" referrerPolicy="no-referrer" onError={() => setBroken(true)} className="mx-auto max-h-96 w-auto object-contain" />
      </button>
      <Credit p={picture} />
      {open ? (
        <div role="dialog" aria-modal="true" aria-label={picture.title || 'Picture'} className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4" onClick={() => setOpen(false)} onKeyDown={e => { if (e.key === 'Escape') setOpen(false); }}>
          <div className="grid max-h-full max-w-5xl gap-2 rounded-card bg-card p-3" onClick={e => e.stopPropagation()}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={picture.src} alt={picture.title} referrerPolicy="no-referrer" className="max-h-[80vh] w-auto rounded-[4px] object-contain" />
            <div className="flex flex-wrap items-start justify-between gap-3">
              <Credit p={picture} />
              <button type="button" autoFocus onClick={() => setOpen(false)} className="rounded-[4px] border border-line px-3 py-1 text-sm">Close</button>
            </div>
          </div>
        </div>
      ) : null}
    </figure>
  );
}

/** Author, licence and source, as the licence asks; a web result says only where it is from. */
function Credit({ p }: { p: Picture }) {
  return (
    <p className="text-[13px] leading-snug text-muted-foreground">
      {p.credit ? `${p.credit} · ` : ''}
      {p.license ? (p.license_url ? <a href={p.license_url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">{p.license}</a> : p.license) : 'Rights belong to its owner'}
      {' · '}
      <a href={p.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 underline underline-offset-2">
        Source: {FROM[p.provider]}<ExternalLink className="size-3" aria-hidden="true" /><span className="sr-only">, opens in a new tab</span>
      </a>
    </p>
  );
}

/** A section's text split after its first paragraph (outside code), where its picture goes. */
export function afterFirstParagraph(body: string): [string, string] {
  const lines = body.split('\n');
  let fenced = false;
  let seen = false;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (/^\s*```/.test(line)) fenced = !fenced;
    if (fenced || line.trim()) { seen = true; continue; }
    if (seen) return [lines.slice(0, i).join('\n'), lines.slice(i + 1).join('\n')];
  }
  return [body, ''];
}
