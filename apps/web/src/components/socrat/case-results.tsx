'use client';

import { Check, ChevronDown } from '@/components/icons';
import type { Case } from '@/lib/types';
import { AttentionIcon } from '@/components/socrat/states';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';

/** Passed: a check in a cream circle. Anything else: the coral triangle. */
function CaseMark({ ok }: { ok: boolean }) {
  return ok
    ? <span className="grid size-6 flex-none place-items-center rounded-full bg-cream text-cream-foreground"><Check className="size-3.5" strokeWidth={2.5} aria-hidden="true" /></span>
    : <AttentionIcon size={22} />;
}
const CASE_LABEL: Record<string, string> = {
  passed: 'Passed', wrong_answer: 'Wrong answer', runtime_error: 'Runtime error', timeout: 'Too slow',
  output_limit: 'Too much output', memory_limit: 'Too much memory', compile_error: 'Did not compile', executed: 'Ran', not_run: 'Not run',
};

function CaseDetail({ c, index }: { c: Case; index: number }) {
  const ok = c.status === 'passed' || c.status === 'executed';
  return (
    <Collapsible defaultOpen={!ok && index < 3} className="rounded-[4px] border">
      <CollapsibleTrigger className="group flex min-h-12 w-full items-center justify-between gap-3 px-3 py-2 text-[15px]">
        <span className="flex items-center gap-2.5">
          <CaseMark ok={ok} />
          <span className={ok ? '' : 'font-semibold'}>{ok ? 'Passed' : CASE_LABEL[c.status] ?? c.status}</span>
          <span className="text-muted-foreground">{c.expected === null ? 'Your custom input' : `Example ${index + 1}`}</span>
        </span>
        <span className="flex items-center gap-2 text-[13px] text-muted-foreground tabular-nums">
          {c.wall_ms && c.status !== 'timeout' ? `${c.wall_ms} ms` : ''}
          <ChevronDown className="size-4 transition-transform group-data-[state=open]:rotate-180" />
        </span>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="grid gap-2 border-t p-3 text-[13px]">
          {c.input !== null ? <div><p className="mb-1 font-medium text-muted-foreground">Input</p><pre className="io-block">{c.input}</pre></div> : null}
          {c.expected !== null ? <div><p className="mb-1 font-medium text-muted-foreground">Expected</p><pre className="io-block">{c.expected}</pre></div> : null}
          {c.stdout !== null ? <div><p className="mb-1 font-medium text-muted-foreground">Your output</p><pre className="io-block">{c.stdout || '(no output)'}</pre></div> : null}
          {c.stderr ? <div><p className="mb-1 font-medium text-muted-foreground">Errors</p><pre className="io-block">{c.stderr}</pre></div> : null}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

function HiddenSummary({ cases }: { cases: Case[] }) {
  const hidden = cases.map((c, index) => ({ c, index })).filter(({ c }) => !c.public);
  if (!hidden.length) return null;
  const failed = hidden.filter(({ c }) => c.status !== 'passed');
  const slowest = Math.max(...hidden.map(({ c }) => c.wall_ms || 0));
  return (
    <Collapsible defaultOpen={failed.length > 0} className="rounded-[4px] border">
      <CollapsibleTrigger className="group flex min-h-12 w-full items-center justify-between gap-3 px-3 py-2 text-[15px]">
        <span className="flex items-center gap-2.5">
          <CaseMark ok={!failed.length} />
          Hidden tests
        </span>
        <span className="flex items-center gap-2 text-[13px] text-muted-foreground tabular-nums">
          {hidden.length - failed.length} of {hidden.length} passed{slowest ? `, slowest ${slowest} ms` : ''}
          <ChevronDown className="size-4 transition-transform group-data-[state=open]:rotate-180" />
        </span>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="grid gap-1 border-t p-3 text-[13px]">
          {failed.length ? (
            failed.map(({ c, index }) => (
              <div key={index}>
                <p className="flex justify-between gap-2"><span>Hidden test {index + 1}</span><span className="font-medium">{CASE_LABEL[c.status] ?? c.status}</span></p>
                {c.stderr ? <pre className="io-block mt-1">{c.stderr}</pre> : null}
              </div>
            ))
          ) : (
            <p className="text-muted-foreground">All passed.</p>
          )}
          <p className="mt-1 text-muted-foreground">Hidden tests check edge cases and performance; their data stays private.</p>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

/** Every public case in detail, then one summary row for the hidden ones. */
export default function CaseResults({ cases }: { cases: Case[] }) {
  return (
    <>
      {cases.map((c, i) => (c.public ? <CaseDetail key={i} c={c} index={i} /> : null))}
      <HiddenSummary cases={cases} />
    </>
  );
}
