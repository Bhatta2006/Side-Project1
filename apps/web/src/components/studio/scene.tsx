'use client';

import { useEffect, useRef, useState, type RefObject } from 'react';
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
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const ARROW = 1.4; // pixels per m/s for the launch arrow

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

interface Timing {
  /** Seconds the picture plays for. */
  duration: number;
  /** Simulated seconds per picture second (long experiments are sped up). */
  scale: number;
  /** Whether the clock reads in real simulated seconds. */
  clock: boolean;
}

/** How long one pass lasts, and how picture time maps to simulated time. */
export function timingOf(model: string, run: Run | null): Timing {
  const end = run?.trace.length ? run.trace[run.trace.length - 1][0] : 2;
  switch (model) {
    case 'projectile': return { duration: run?.outputs.flight_time?.value ?? 2, scale: 1, clock: true };
    case 'circuit': return { duration: 4, scale: 1, clock: false };
    case 'wave': return { duration: 4, scale: 1, clock: false };
    case 'refraction': return { duration: 2, scale: 1, clock: false };
    case 'heating': return { duration: 6, scale: Math.max(end, 1) / 6, clock: true };
    default: return { duration: end, scale: 1, clock: true };
  }
}

/** A clock that plays, pauses, loops and scrubs, in picture seconds. */
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
export type Aim = (angle: number, speed: number) => void;

function Projectile({ p, run, ghost, t, svg, onAim }: { p: Params; run: Run | null; ghost: Run | null; t: number; svg: RefObject<SVGSVGElement | null>; onAim?: Aim }) {
  const angle = (num(p, 'angle', 45) * Math.PI) / 180;
  const all = [...(run?.trace ?? []), ...(ghost?.trace ?? [])];
  const fallbackX = (num(p, 'speed', 20) ** 2 * Math.sin(2 * angle)) / num(p, 'gravity', 9.81) || 20;
  const maxX = Math.max(...all.map(q => q[0]), fallbackX, 1) * 1.08;
  const maxY = Math.max(...all.map(q => q[1]), num(p, 'height'), 1) * 1.2;
  const s = Math.min((W - 40) / maxX, (H - 50) / maxY);
  const px = (x: number) => 24 + x * s, py = (y: number) => H - 28 - y * s;
  const line = (tr: [number, number][]) => tr.map(([x, y], i) => `${i ? 'L' : 'M'}${px(x).toFixed(1)} ${py(y).toFixed(1)}`).join(' ');
  const flight = run?.outputs.flight_time?.value ?? 1;
  const index = run ? Math.min(run.trace.length - 1, Math.round((t / flight) * (run.trace.length - 1))) : 0;
  const ball = run ? run.trace[index] : [0, num(p, 'height')];
  const done = run ? run.trace.slice(0, index + 1) : [];
  const [lx, ly] = [px(0), py(num(p, 'height'))];
  const len = clamp(num(p, 'speed', 20) * ARROW, 14, 160);
  const [hx, hy] = [lx + len * Math.cos(angle), ly - len * Math.sin(angle)];

  function drag(e: React.PointerEvent<SVGCircleElement>) {
    const el = svg.current;
    if (!onAim || !el || !e.currentTarget.hasPointerCapture(e.pointerId)) return;
    const at = el.createSVGPoint();
    at.x = e.clientX; at.y = e.clientY;
    const m = el.getScreenCTM();
    if (!m) return;
    const q = at.matrixTransform(m.inverse());
    const [dx, dy] = [q.x - lx, ly - q.y];
    onAim(Math.round(clamp((Math.atan2(dy, Math.max(dx, 0.001)) * 180) / Math.PI, 0, 90)), Math.round(clamp(Math.hypot(dx, dy) / ARROW, 1, 100)));
  }

  return (
    <>
      <line x1="8" x2={W - 8} y1={py(0)} y2={py(0)} stroke={ink} strokeOpacity="0.4" />
      {ghost ? <path d={line(ghost.trace)} fill="none" stroke={ink} strokeOpacity="0.3" strokeDasharray="4 4" /> : null}
      {run ? <path d={line(run.trace)} fill="none" stroke={ink} strokeOpacity="0.15" strokeWidth="2" /> : null}
      {done.length > 1 ? <path d={line(done)} fill="none" className="text-primary" stroke={ink} strokeWidth="2.5" /> : null}
      {!run || onAim ? <line x1={lx} y1={ly} x2={hx} y2={hy} stroke={ink} strokeWidth="2" strokeDasharray="5 3" /> : null}
      {run?.outputs.range ? <text x={px(run.outputs.range.value)} y={py(0) + 16} fontSize="11" textAnchor="middle" fill={ink}>{Number(run.outputs.range.value.toPrecision(3))} m</text> : null}
      <circle cx={px(ball[0])} cy={py(ball[1])} r="7" className="fill-primary" />
      {run && onAim ? (
        <g>
          <circle cx={hx} cy={hy} r="9" className="cursor-grab fill-background stroke-primary" strokeWidth="2.5" style={{ touchAction: 'none' }}
            onPointerDown={e => e.currentTarget.setPointerCapture(e.pointerId)} onPointerMove={drag} role="slider" aria-label="Aim the launch" aria-valuetext={`${Math.round(num(p, 'angle'))} degrees at ${Math.round(num(p, 'speed'))} metres per second`} />
          <text x={hx + 12} y={hy - 8} fontSize="10" fill={ink}>{Math.round(num(p, 'angle'))}° · {Math.round(num(p, 'speed'))} m/s</text>
        </g>
      ) : null}
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

/** A travelling wave in slow motion: the pattern moves right while each point only moves up and down. */
function Wave({ p, t }: { p: Params; t: number }) {
  const wavelength = Math.max(num(p, 'wavelength', 1.5), 0.001);
  const amp = 14 + 66 * Math.sqrt(clamp(num(p, 'amplitude', 0.5) / 5, 0, 1));
  const span = 3, left = 20, width = W - 40, perM = width / (span * wavelength);
  const phase = t / 2; // two cycles per pass, so the wave is slow enough to follow
  const y = (x: number) => 110 - amp * Math.sin(2 * Math.PI * (x / wavelength - phase));
  const pts = Array.from({ length: 121 }, (_, i) => { const x = (i / 120) * span * wavelength; return `${i ? 'L' : 'M'}${(left + x * perM).toFixed(1)} ${y(x).toFixed(1)}`; }).join(' ');
  const dotX = span * wavelength * 0.5;
  const base = H - 36;
  return (
    <>
      <line x1={left} x2={W - 20} y1="110" y2="110" stroke={ink} strokeOpacity="0.25" />
      <path d={pts} fill="none" className="text-primary" stroke={ink} strokeWidth="2.5" />
      <line x1={left + dotX * perM} x2={left + dotX * perM} y1="110" y2={y(dotX)} stroke={ink} strokeOpacity="0.4" strokeDasharray="3 3" />
      <circle cx={left + dotX * perM} cy={y(dotX)} r="6" className="fill-primary" />
      <line x1={left} x2={left + wavelength * perM} y1={base} y2={base} stroke={ink} />
      <line x1={left} x2={left} y1={base - 5} y2={base + 5} stroke={ink} />
      <line x1={left + wavelength * perM} x2={left + wavelength * perM} y1={base - 5} y2={base + 5} stroke={ink} />
      <text x={left + (wavelength * perM) / 2} y={base + 16} fontSize="11" textAnchor="middle" fill={ink}>one wavelength = {Number(wavelength.toPrecision(3))} m</text>
      <text x={W - 24} y="16" fontSize="10" textAnchor="end" fill={ink} fillOpacity="0.7">slow motion</text>
    </>
  );
}

/** Light bending at a boundary. The refracted ray appears only once the experiment has run. */
function Refraction({ p, run, t }: { p: Params; run: Run | null; t: number }) {
  const [n1, n2] = [num(p, 'n1', 1), num(p, 'n2', 1.5)];
  const cx = W / 2, cy = 110, L = 92;
  const a1 = (num(p, 'angle_in', 30) * Math.PI) / 180;
  const out = run?.outputs.refracted_angle?.value;
  const a2 = out === undefined ? null : (out * Math.PI) / 180;
  const start = [cx - L * Math.sin(a1), cy - L * Math.cos(a1)];
  const end = a2 === null ? null : [cx + L * Math.sin(a2), cy + L * Math.cos(a2)];
  const u = (t % 2) / 2;
  const photon = u < 0.5 ? [start[0] + (cx - start[0]) * u * 2, start[1] + (cy - start[1]) * u * 2] : end ? [cx + (end[0] - cx) * (u - 0.5) * 2, cy + (end[1] - cy) * (u - 0.5) * 2] : [cx, cy];
  return (
    <>
      <rect x="0" y="0" width={W} height={cy} fill="#3b82f6" fillOpacity={0.05 + 0.1 * (n1 - 1)} />
      <rect x="0" y={cy} width={W} height={H - cy} fill="#3b82f6" fillOpacity={0.05 + 0.1 * (n2 - 1)} />
      <line x1="0" x2={W} y1={cy} y2={cy} stroke={ink} strokeOpacity="0.6" strokeWidth="2" />
      <line x1={cx} x2={cx} y1="12" y2={H - 12} stroke={ink} strokeOpacity="0.4" strokeDasharray="4 4" />
      <text x="10" y="18" fontSize="11" fill={ink}>n = {Number(n1.toPrecision(3))}</text>
      <text x="10" y={H - 10} fontSize="11" fill={ink}>n = {Number(n2.toPrecision(3))}</text>
      <line x1={start[0]} y1={start[1]} x2={cx} y2={cy} stroke="#f59e0b" strokeWidth="3" />
      <text x={cx - 70} y={cy - 12} fontSize="11" fill={ink}>{Math.round(num(p, 'angle_in', 30) * 10) / 10}°</text>
      {end ? <line x1={cx} y1={cy} x2={end[0]} y2={end[1]} stroke="#f59e0b" strokeWidth="3" /> : <text x={cx + 20} y={cy + 40} fontSize="22" fill={ink} fillOpacity="0.4">?</text>}
      {out !== undefined ? <text x={cx + 14} y={cy + 56} fontSize="11" fill={ink}>{Number(out.toPrecision(3))}°</text> : null}
      <circle cx={photon[0]} cy={photon[1]} r="5" fill="#fde68a" stroke="#f59e0b" />
    </>
  );
}

/** A beaker on a heater: the liquid warms and the thermometer climbs along the simulated curve. */
function Heating({ p, run, t }: { p: Params; run: Run | null; t: number }) {
  const start = num(p, 'start_temp', 20);
  const temp = run ? at(run.trace, t)[1] : start;
  const fraction = clamp(temp / 100, 0, 1);
  const warm = `rgb(${Math.round(60 + 190 * fraction)}, ${Math.round(130 - 60 * fraction)}, ${Math.round(220 - 170 * fraction)})`;
  const flame = 8 + 22 * clamp(num(p, 'power', 1000) / 5000, 0, 1);
  const bubbles = temp > 85 ? [0, 1, 2, 3] : [];
  return (
    <>
      <rect x="120" y="50" width="120" height="110" rx="6" fill="none" stroke={ink} strokeWidth="2.5" />
      <rect x="123" y="80" width="114" height="77" fill={warm} fillOpacity="0.85" />
      <text x="180" y="124" fontSize="13" textAnchor="middle" fill="#fff">{Number(num(p, 'mass', 1).toPrecision(3))} kg</text>
      {bubbles.map(i => <circle key={i} cx={140 + i * 25} cy={150 - ((t * 40 + i * 20) % 60)} r="3" fill="#fff" fillOpacity="0.7" />)}
      <path d={`M160 176 q ${flame / 2} -${flame * 1.6} 20 -${flame * 2} q -4 ${flame} 20 ${flame * 2}`} fill="#f59e0b" fillOpacity="0.85" transform={`translate(0 ${-flame * 0.4})`} />
      <rect x="130" y="176" width="100" height="8" rx="3" fill={ink} fillOpacity="0.5" />
      <rect x="290" y="30" width="14" height="150" rx="7" fill="none" stroke={ink} strokeWidth="2" />
      <rect x="293" y={180 - 144 * fraction} width="8" height={144 * fraction} rx="4" fill="#ef4444" />
      <circle cx="297" cy="186" r="11" fill="#ef4444" />
      <text x="316" y={180 - 144 * fraction + 4} fontSize="12" fill={ink}>{Number(temp.toFixed(1))} °C</text>
    </>
  );
}

/**
 * An animated picture of the experiment. Before the run it shows the setup from the parameters;
 * after, it plays the simulation's own trace, so the picture can never disagree with the numbers.
 * ``onAim`` makes the projectile's launch arrow draggable once it has run.
 */
export function Scene({ model, params, run, ghost, label, onAim }: { model: string; params: Params; run: Run | null; ghost?: Run | null; label: string; onAim?: Aim }) {
  const [speed, setSpeed] = useState(1);
  const svg = useRef<SVGSVGElement>(null);
  const { duration, scale, clock } = timingOf(model, run);
  const { t, setT, playing, setPlaying } = useClock(duration, speed);
  const live = run !== null || ['circuit', 'wave', 'refraction'].includes(model);
  useEffect(() => { setT(0); }, [run, setT]);
  const sim = t * scale;
  const body = (() => {
    switch (model) {
      case 'projectile': return <Projectile p={params} run={run} ghost={ghost ?? null} t={sim} svg={svg} onAim={onAim} />;
      case 'free_fall': return <FreeFall p={params} run={run} t={sim} />;
      case 'pendulum': return <Pendulum p={params} run={run} t={sim} />;
      case 'spring_mass': return <Spring p={params} run={run} t={sim} />;
      case 'circuit': return <Circuit p={params} run={run} t={sim} />;
      case 'wave': return <Wave p={params} t={sim} />;
      case 'refraction': return <Refraction p={params} run={run} t={sim} />;
      case 'heating': return <Heating p={params} run={run} t={sim} />;
      default: return null;
    }
  })();
  return (
    <figure className="grid gap-2">
      <svg ref={svg} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} className="w-full max-w-lg touch-none rounded-md bg-muted text-foreground">{body}</svg>
      {run && onAim && model === 'projectile' ? <figcaption className="text-xs text-muted-foreground">Drag the ring on the arrow to aim: angle and speed change together.</figcaption> : null}
      {live ? (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <Button size="sm" variant="outline" onClick={() => setPlaying(!playing)} aria-label={playing ? 'Pause' : 'Play'}>{playing ? <Pause /> : <Play />}</Button>
          <Button size="sm" variant="outline" onClick={() => { setT(0); setPlaying(true); }} aria-label="Replay"><RotateCcw /></Button>
          <input type="range" min={0} max={duration} step={duration / 200} value={t} aria-label="Time" className="min-w-24 flex-1"
            onChange={e => { setPlaying(false); setT(Number(e.target.value)); }} />
          {clock ? <span className="tabular-nums text-muted-foreground">{Number(sim.toPrecision(3))} s</span> : null}
          <select aria-label="Speed" value={speed} onChange={e => setSpeed(Number(e.target.value))} className="rounded-md border bg-background px-1 py-0.5 text-xs">
            <option value={0.25}>0.25×</option><option value={0.5}>0.5×</option><option value={1}>1×</option><option value={2}>2×</option>
          </select>
        </div>
      ) : null}
    </figure>
  );
}
