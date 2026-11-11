'use client';

import { useState } from 'react';
import { Check, X } from '@/components/icons';
import { api, explain } from '@/lib/api';
import type { Proposal, ProposalsView } from '@/lib/types';
import { Button } from '@/components/ui/button';

const SOURCE: Record<Proposal['source'], string> = {
  planner: 'Socrat noticed',
  tutor: 'From your chat with Soc',
  review: 'From your weekly review',
  company_sprint: 'From your company sprint',
};

/**
 * Roadmap changes Socrat suggests. Nothing changes until the learner presses Accept; options
 * that share a group are alternatives, and accepting one retires the rest.
 */
export function ProposalList({
  proposals,
  onDecided,
  compact = false,
}: {
  proposals: Proposal[];
  onDecided?: (view: ProposalsView) => void;
  compact?: boolean;
}) {
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [done, setDone] = useState<Record<string, 'accepted' | 'declined'>>({});

  async function decide(id: string, decision: 'accept' | 'decline') {
    setBusy(id);
    setError('');
    try {
      const view = await api.post<ProposalsView & { proposal: Proposal }>(`/adaptive/proposals/${id}/${decision}`);
      setDone(d => ({ ...d, [id]: decision === 'accept' ? 'accepted' : 'declined' }));
      onDecided?.(view);
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy('');
    }
  }

  if (!proposals.length) return null;
  const groups = new Set(proposals.filter(p => p.group).map(p => p.group));
  return (
    <div className="grid gap-2">
      {groups.size ? <p className="text-[13px] text-muted-foreground">Options in the same group are alternatives: pick the one that suits you.</p> : null}
      <ul className="grid gap-2">
        {proposals.map(p => {
          const decided = done[p.id];
          return (
            <li key={p.id} className={`rounded-[4px] border bg-raised ${compact ? 'p-3' : 'p-4'}`}>
              <p className="text-[12px] font-medium tracking-wide text-muted-foreground uppercase">{SOURCE[p.source]}</p>
              <p className="mt-1 font-semibold">{p.title}</p>
              <p className="mt-1 text-[14px] text-muted-foreground">{p.reason}</p>
              {decided ? (
                <p className="mt-2 flex items-center gap-1.5 text-[14px] font-medium" role="status">
                  {decided === 'accepted' ? <><Check className="size-4" aria-hidden="true" /> Added to your plan</> : 'Okay, no change'}
                </p>
              ) : (
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button size="sm" disabled={!!busy} onClick={() => decide(p.id, 'accept')}>
                    <Check data-icon="inline-start" /> Accept
                  </Button>
                  <Button size="sm" variant="ghost" disabled={!!busy} onClick={() => decide(p.id, 'decline')}>
                    <X data-icon="inline-start" /> Not now
                  </Button>
                </div>
              )}
            </li>
          );
        })}
      </ul>
      {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
    </div>
  );
}
