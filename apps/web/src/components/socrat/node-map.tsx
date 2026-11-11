'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { STATUS_LABEL, StatusIcon, type Status } from './status';

export interface MapNode { id: string; title: string; href: string; status: Status; current?: boolean; reviewDue?: boolean }

/**
 * Skills of one module as a left-to-right sequence. The plan has no prerequisite edges, so the
 * line is labelled "Order in module" and never implies a dependency graph. The list view is
 * equivalent and is the default on narrow phones.
 */
export function NodeMap({ nodes, label }: { nodes: MapNode[]; label: string }) {
  const [view, setView] = useState<'map' | 'list'>('map');
  useEffect(() => { if (window.matchMedia('(max-width: 479px)').matches) setView('list'); }, []);
  const name = (n: MapNode) => `${n.title}: ${n.status === 'locked' ? 'Locked' : STATUS_LABEL[n.status]}${n.reviewDue ? ', review due' : ''}${n.current ? ', current' : ''}`;
  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="type-label text-(--card-muted,var(--muted-foreground))">Order in module</p>
        <div className="inline-flex h-10 rounded-[4px] border border-line p-1" role="group" aria-label="Skill view">
          {(['map', 'list'] as const).map(v => (
            <button
              key={v}
              type="button"
              aria-pressed={view === v}
              onClick={() => setView(v)}
              className={cn('min-h-8 rounded-[3px] px-4 text-sm font-medium capitalize', view === v && 'bg-hi-select font-bold text-ink')}
            >
              {v}
            </button>
          ))}
        </div>
      </div>
      {view === 'map' ? (
        <div className="-mx-2 overflow-x-auto px-2 pb-2" tabIndex={0} role="region" aria-label={`${label}, skill map`} style={{ scrollSnapType: 'x mandatory' }}>
          <ol className="flex min-w-max items-start">
            {nodes.map((n, i) => (
              <li key={n.id} className="relative flex w-28 flex-none snap-start flex-col items-center" style={{ scrollSnapAlign: 'start' }}>
                {i > 0 ? <span aria-hidden="true" className="absolute top-[22px] right-1/2 h-px w-full bg-current opacity-40" /> : null}
                <Link href={n.href} aria-label={name(n)} title={name(n)} className="relative z-10 grid size-11 place-items-center rounded-full bg-(--node-bg,var(--card))">
                  <StatusIcon status={n.status} size={32} />
                </Link>
                <span className={cn('mt-2 line-clamp-2 px-1 text-center text-xs leading-4', n.current && 'font-bold')} aria-hidden="true">{n.title}</span>
              </li>
            ))}
          </ol>
        </div>
      ) : (
        <ol className="grid gap-1">
          {nodes.map(n => (
            <li key={n.id}>
              <Link href={n.href} className="flex min-h-12 items-center gap-3 rounded-[4px] px-2 py-2 transition-colors hover:bg-[color-mix(in_srgb,currentColor,transparent_90%)]">
                <StatusIcon status={n.status} size={24} />
                <span className="min-w-0 flex-1 font-semibold">{n.title}</span>
                <span className="text-[13px] font-medium">{n.status === 'locked' ? 'Locked' : STATUS_LABEL[n.status]}{n.current ? ', current' : ''}</span>
              </Link>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
