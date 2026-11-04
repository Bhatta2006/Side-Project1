'use client';

import { useEffect, useId, useMemo, useState } from 'react';
import { api, explain } from '@/lib/api';

interface ParamInfo { name: string; unit: string; low: number; high: number; default: number }
interface ModelInfo { id: string; title: string; params: ParamInfo[]; outputs: { name: string; unit: string }[] }
interface Run {
  title: string;
  outputs: Record<string, { value: number; unit: string }>;
  trace: [number, number][];
}

let catalogue: Promise<ModelInfo[]> | null = null;
function models(): Promise<ModelInfo[]> {
  catalogue ??= api.get<{ items: ModelInfo[] }>('/engine/simulations').then(r => r.items).catch(e => { catalogue = null; throw e; });
  return catalogue;
}

const label = (name: string) => name.replaceAll('_', ' ');

/** A line through the experiment's trace. Drawn from numbers the server computed; the table below is the accessible form. */
function Trace({ trace }: { trace: [number, number][] }) {
  if (trace.length < 2) return null;
  const xs = trace.map(p => p[0]);
  const ys = trace.map(p => p[1]);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const sx = (x: number) => 8 + ((x - x0) / (x1 - x0 || 1)) * 304;
  const sy = (y: number) => 112 - ((y - y0) / (y1 - y0 || 1)) * 104;
  const points = trace.map(([x, y]) => `${sx(x).toFixed(1)},${sy(y).toFixed(1)}`).join(' ');
  return (
    <svg viewBox="0 0 320 120" className="h-32 w-full rounded-lg border bg-background" aria-hidden="true">
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" className="text-primary" />
    </svg>
  );
}

/**
 * A vetted experiment computed by the server's harness. The browser never computes the physics:
 * it sends the slider values, the server checks them against the experiment's ranges and returns
 * the quantities with units. A failure shows the lesson's own fallback text (via the host).
 */
export function Simulation({ params }: { params: { model: string; inputs?: Record<string, number> } }) {
  const id = useId();
  const [info, setInfo] = useState<ModelInfo | null>(null);
  const [values, setValues] = useState<Record<string, number>>({});
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let live = true;
    models().then(all => {
      const found = all.find(m => m.id === params.model);
      if (!live) return;
      if (!found) { setError('This experiment is not available.'); return; }
      setInfo(found);
      setValues(Object.fromEntries(found.params.map(p => [p.name, params.inputs?.[p.name] ?? p.default])));
    }).catch(e => live && setError(explain(e)));
    return () => { live = false; };
  }, [params.model, params.inputs]);

  const key = useMemo(() => JSON.stringify(values), [values]);
  useEffect(() => {
    if (!info) return;
    let live = true;
    const timer = setTimeout(() => {
      api.post<Run>('/engine/simulate', { model: info.id, inputs: values })
        .then(r => { if (live) { setRun(r); setError(''); } })
        .catch(e => live && setError(explain(e)));
    }, 150);
    return () => { live = false; clearTimeout(timer); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [info, key]);

  if (error && !info) throw new Error(error); // the host's guard shows the lesson's fallback text
  if (!info) return <p className="text-sm text-muted-foreground">Loading experiment…</p>;
  return (
    <div className="grid gap-4 text-sm">
      <p className="font-medium">{info.title}</p>
      <div className="grid gap-3 sm:grid-cols-2">
        {info.params.map(p => (
          <div key={p.name} className="grid gap-1">
            <label htmlFor={`${id}-${p.name}`} className="flex justify-between gap-2">
              <span className="capitalize">{label(p.name)}</span>
              <span className="tabular-nums text-muted-foreground">{values[p.name]} {p.unit}</span>
            </label>
            <input
              id={`${id}-${p.name}`}
              type="range"
              min={p.low}
              max={p.high}
              step={(p.high - p.low) / 200}
              value={values[p.name] ?? p.default}
              onChange={e => setValues(v => ({ ...v, [p.name]: Number(e.target.value) }))}
            />
          </div>
        ))}
      </div>
      {error ? <p role="alert" className="text-destructive">{error}</p> : null}
      {run ? (
        <>
          <Trace trace={run.trace} />
          <table className="w-full text-left">
            <caption className="sr-only">Results computed by Socrat for these settings</caption>
            <thead><tr><th className="pb-1 font-medium">Result</th><th className="pb-1 font-medium">Value</th></tr></thead>
            <tbody>
              {Object.entries(run.outputs).map(([name, o]) => (
                <tr key={name} className="border-t">
                  <td className="py-1 capitalize">{label(name)}</td>
                  <td className="py-1 tabular-nums">{o.value} {o.unit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : null}
    </div>
  );
}
