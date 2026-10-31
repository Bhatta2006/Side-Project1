'use client';

import { useEffect, useRef, useState } from 'react';
import { Pause, Play, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface Run {
  outputs: Record<string, { value: number; unit: string }>;
  trace: [number, number][];
}
type Params = Record<string, number>;

const W = 400;
const H = 220;
const num = (p: Params, k: string, fallback = 0) => (Number.isFinite(p[k]) ? p[k] : fallback);

/** Linear lookup of a traced series at x (points are sorted by x). */
function at(trace: [number, number][], x: number): [number, number] {
  if (!trace.length) return [0, 0];
  if (x <= trace[0][0]) return trace[0];
  for (let i = 1; i < trace.length; i++) {
    if (x <= trace[i][0]) {
      const [x0, y0] = trace[i - 1], [x1, y1] = trace[i];
      const f = (x - x0) / (x1 - x0 || 1);
      return [x, y0 + (y1 - y0) * f];
    }
  }
  return trace[trace.length - 1];
}

/** How long one pass of the experiment lasts, in simulated seconds. */
export function durationOf(model: string, run: Run | null): number {
  if (model === 'projectile') return run?.outputs.flight_time?.value ?? 2;
  if (model === 'circuit') return 4;
  return run?.trace.length ? run.trace[run.trace.length - 1][0] : 2;
}

/** A clock that plays, pauses, loops and scrubs; time is simulated seconds. */
function useClock(duration: number, speed: number) {
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(true);
  const last = useRef<number | null>(null);
  useEffect(() => {
    if (!playing) { last.current = null; return; }
    let frame = 0;
    const tick = (now: number) => {
      if (last.current !== null) setT(prev => { const next = prev + ((now - last.current!) / 1000) * speed; return next > duration + 0.6 ? 0 : next; });
      last.current = now;
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [playing, duration, speed]);
  return { t: Math.min(t, duration), setT, playing, setPlaying };
}

const ink = 'currentColor';

function Projectile({ p, run, ghost, t }: { p: Params; run: Run | null; ghost: Run | null; t: number }) {
  const angle = (num(p, 'angle', 45) * Math.PI) / 180;
  const all = [...(run?.trace ?? []), ...(ghost?.trace ?? [])];
  const fallbackX = (num(p, 'speed', 20) ** 2 * Math.sin(2 * angle)) / num(p, 'gravity', 9.81) || 20;
  const maxX = Math.max(...all.map(q => q[0]), fallbackX, 1) * 1.08;
  const maxY = Math.max(...all.map(q => q[1]), num(p, 'height'), 1) * 1.2;
  const s = Math.min((W - 40) / maxX, (H - 50) / maxY);
  const px = (x: number) => 24 + x * s, py = (y: number) => H - 28 - y * s;
  const line = (tr: [number, number][]) => tr.map(([x, y], i) => `${i ? 'L' : 'M'}${px(x).toFixed(1)} ${py(y).toFixed(1)}`).join(' ');
  const flight = run?.outputs.flight_time?.value ?? 1;
  const ball = run ? run.trace[Math.min(run.trace.length - 1, Math.round((t / flight) * (run.trace.length - 1)))] : [0, num(p, 'height')];
  const done = run ? run.trace.slice(0, Math.round((t / flight) * (run.trace.length - 1)) + 1) : [];
  const len = Math.min(52, 14 + num(p, 'speed', 20) * 0.5);
  return (
    <>
      <line x1="8" x2={W - 8} y1={py(0)} y2={py(0)} stroke={ink} strokeOpacity="0.4" />
      {ghost ? <path d={line(ghost.trace)} fill="none" stroke={ink} strokeOpacity="0.3" strokeDasharray="4 4" /> : null}
      {run ? <path d={line(run.trace)} fill="none" stroke={ink} strokeOpacity="0.15" strokeWidth="2" /> : null}
      {done.length > 1 ? <path d={line(done)} fill="none" className="text-primary" stroke={ink} strokeWidth="2.5" /> : null}
      {!run ? <line x1={px(0)} y1={py(num(p, 'height'))} x2={px(0) + len * Math.cos(angle)} y2={py(num(p, 'height')) - len * Math.sin(angle)} stroke={ink} strokeWidth="2" strokeDasharray="5 3" /> : null}
      {run?.outputs.range ? <text x={px(run.outputs.range.value)} y={py(0) + 16} fontSize="11" textAnchor="middle" fill={ink}>{Number(run.outputs.range.value.toPrecision(3))} m</text> : null}
      <circle cx={px(ball[0])} cy={py(ball[1])} r="7" className="fill-primary" />
    </>
  );
}

function FreeFall({ p, run, t }: { p: Params; run: Run | null; t: number }) {
  const h = num(p, 'height', 20);
  const top = 22, bottom = H - 28, scale = (bottom - top) / h;
  const y = run ? at(run.trace, t)[1] : h;
  return (
    <>
      <line x1="150" x2="250" y1={bottom} y2={bottom} stroke={ink} strokeOpacity="0.5" strokeWidth="2" />
      <line x1="120" x2="120" y1={top} y2={bottom} stroke={ink} strokeOpacity="0.4" />
      {[0, 0.25, 0.5, 0.75, 1].map(f => (
        <g key={f}><line x1="114" x2="126" y1={bottom - f * h * scale} y2={bottom - f * h * scale} stroke={ink} strokeOpacity="0.4" />
          <text x="108" y={bottom - f * h * scale + 4} fontSize="10" textAnchor="end" fill={ink}>{Number((f * h).toPrecision(3))}</text></g>
      ))}
      <text x="120" y="12" fontSize="10" textAnchor="middle" fill={ink}>metres</text>
      <circle cx="200" cy={bottom - y * scale - 8} r="8" className="fill-primary" />
      {run ? <text x="270" y={bottom - y * scale - 4} fontSize="12" fill={ink}>{Number(y.toPrecision(3))} m</text> : null}
    </>
  );
}

function Pendulum({ p, run, t }: { p: Params; run: Run | null; t: number }) {
  const rod = 40 + Math.min(1, num(p, 'length', 1) / 3) * 110;
  const angle = run ? at(run.trace, t)[1] : num(p, 'amplitude', 10);
  const a = (angle * Math.PI) / 180;
  const cx = W / 2, cy = 24;
  const bx = cx + rod * Math.sin(a), by = cy + rod * Math.cos(a);
  return (
    <>
      <line x1={cx - 40} x2={cx + 40} y1={cy} y2={cy} stroke={ink} strokeWidth="3" />
      <line x1={cx} y1={cy} x2={cx} y2={cy + rod + 14} stroke={ink} strokeOpacity="0.2" strokeDasharray="3 4" />
      <line x1={cx} y1={cy} x2={bx} y2={by} stroke={ink} strokeWidth="2" />
      <circle cx={bx} cy={by} r="12" className="fill-primary" />
      <text x={cx + 8} y={cy + 30} fontSize="11" fill={ink}>{Number(angle.toFixed(1))}°</text>
    </>
  );
}

function Spring({ p, run, t }: { p: Params; run: Run | null; t: number }) {
  const amp = num(p, 'amplitude', 0.1);
  const x = run ? at(run.trace, t)[1] : amp;
  const scale = 90 / Math.max(amp, 0.001);
  const rest = 200, mass = 28 + Math.min(1, num(p, 'mass', 1) / 10) * 22;
  const left = 40, right = rest + x * scale - mass / 2;
  const coils = 12, step = (right - left) / coils;
  const zig = Array.from({ length: coils + 1 }, (_, i) => `${i ? 'L' : 'M'}${(left + i * step).toFixed(1)} ${110 + (i === 0 || i === coils ? 0 : i % 2 ? -14 : 14)}`).join(' ');
  return (
    <>
      <line x1={left} x2={left} y1="70" y2="150" stroke={ink} strokeWidth="4" />
      <line x1="40" x2={W - 20} y1="150" y2="150" stroke={ink} strokeOpacity="0.3" />
      <line x1={rest} x2={rest} y1="60" y2="160" stroke={ink} strokeOpacity="0.4" strokeDasharray="3 4" />
      <text x={rest} y="174" fontSize="10" textAnchor="middle" fill={ink}>rest</text>
      <path d={zig} fill="none" stroke={ink} strokeWidth="2" />
      <rect x={right} y={110 - mass / 2} width={mass} height={mass} rx="4" className="fill-primary" />
    </>
  );
}

function Circuit({ p, run, t }: { p: Params; run: Run | null; t: number }) {
  const current = run?.outputs.current?.value ?? num(p, 'voltage', 12) / num(p, 'resistance', 100);
  const power = run?.outputs.power?.value ?? num(p, 'voltage', 12) * current;
  const brightness = Math.min(1, power / 20);
  const [x0, y0, x1, y1] = [60, 50, 340, 170];
  const perimeter = 2 * (x1 - x0 + (y1 - y0));
  const pos = (d: number): [number, number] => {
    d = ((d % perimeter) + perimeter) % perimeter;
    const w = x1 - x0, h = y1 - y0;
    if (d < w) return [x0 + d, y0];
    if (d < w + h) return [x1, y0 + d - w];
    if (d < 2 * w + h) return [x1 - (d - w - h), y1];
    return [x0, y1 - (d - 2 * w - h)];
  };
  const dots = Array.from({ length: 24 }, (_, i) => pos((i * perimeter) / 24 + t * Math.min(260, 60 + current * 400)));
  return (
    <>
      <rect x={x0} y={y0} width={x1 - x0} height={y1 - y0} fill="none" stroke={ink} strokeOpacity="0.4" strokeWidth="2" />
      <rect x="170" y={y0 - 12} width="60" height="24" rx="4" fill="#f59e0b" fillOpacity={0.25 + 0.75 * brightness} stroke={ink} />
      <text x="200" y={y0 - 18} fontSize="11" textAnchor="middle" fill={ink}>{Number(num(p, 'resistance', 100).toPrecision(3))} Ω</text>
      <g><line x1={x0 - 14} x2={x0 + 14} y1="104" y2="104" stroke={ink} strokeWidth="3" /><line x1={x0 - 8} x2={x0 + 8} y1="116" y2="116" stroke={ink} strokeWidth="3" /></g>
      <text x={x0 + 20} y="112" fontSize="11" fill={ink}>{Number(num(p, 'voltage', 12).toPrecision(3))} V</text>
      {dots.map(([x, y], i) => <circle key={i} cx={x} cy={y} r="3" className="fill-primary" />)}
      <text x="200" y={y1 + 24} fontSize="12" textAnchor="middle" fill={ink}>{Number(current.toPrecision(3))} A flowing</text>
    </>
  );
}

/**
 * An animated picture of the experiment. Before the run it shows the setup from the parameters;
 * after, it plays the simulation's own trace, so the picture can never disagree with the numbers.
 */
export function Scene({ model, params, run, ghost, label }: { model: string; params: Params; run: Run | null; ghost?: Run | null; label: string }) {
  const [speed, setSpeed] = useState(1);
  const duration = durationOf(model, run);
  const { t, setT, playing, setPlaying } = useClock(duration, speed);
  const live = run !== null || model === 'circuit';
  useEffect(() => { setT(0); }, [run, setT]);
  const body = (() => {
    switch (model) {
      case 'projectile': return <Projectile p={params} run={run} ghost={ghost ?? null} t={t} />;
      case 'free_fall': return <FreeFall p={params} run={run} t={t} />;
      case 'pendulum': return <Pendulum p={params} run={run} t={t} />;
      case 'spring_mass': return <Spring p={params} run={run} t={t} />;
      case 'circuit': return <Circuit p={params} run={run} t={t} />;
      default: return null;
    }
  })();
  return (
    <figure className="grid gap-2">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} className="w-full max-w-lg rounded-md bg-muted text-foreground">{body}</svg>
      {live ? (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <Button size="sm" variant="outline" onClick={() => setPlaying(!playing)} aria-label={playing ? 'Pause' : 'Play'}>{playing ? <Pause /> : <Play />}</Button>
          <Button size="sm" variant="outline" onClick={() => { setT(0); setPlaying(true); }} aria-label="Replay"><RotateCcw /></Button>
          <input type="range" min={0} max={duration} step={duration / 200} value={t} aria-label="Time" className="min-w-24 flex-1"
            onChange={e => { setPlaying(false); setT(Number(e.target.value)); }} />
          <span className="tabular-nums text-muted-foreground">{t.toFixed(2)} s</span>
          <select aria-label="Speed" value={speed} onChange={e => setSpeed(Number(e.target.value))} className="rounded-md border bg-background px-1 py-0.5 text-xs">
            <option value={0.25}>0.25×</option><option value={0.5}>0.5×</option><option value={1}>1×</option><option value={2}>2×</option>
          </select>
        </div>
      ) : null}
    </figure>
  );
}
