'use client';
// Soc as a pebble (Socrates trained as a stonemason). The black finishes give the stone real
// texture (shadowed side, sheen, pits, flecks, a quartz vein) so it reads as a stone, not a blob;
// the drawn finishes use Looseleaf's ink outline, ink-dot eyes and Socrates' brows.
import * as React from 'react';

import { cn } from '@/lib/utils';
import { watchFigure } from '@/lib/soc-blink';
import { useEnsureInkDefs } from '@/lib/ink/react';
import { drawMascot } from '@/lib/ink/art/mascot-draw';
import { memo } from '@/lib/ink/art-draw';
import { spline, xf, type P } from '@/lib/ink/art/mascots/body';
import type { ArtColour, ArtDef, Part } from '@/lib/ink/art/types';
import type { SocMood } from './soc';

export type PebbleShape = 'river' | 'round' | 'skimmer' | 'tall' | 'chipped' | 'lumpy';
export type PebbleFinish = 'plain' | 'basalt' | 'granite' | 'quartz' | 'drawn' | 'brows';
export type PebbleProp = 'none' | 'page' | 'laurel';
export type PebbleMood = 'idle' | 'think' | 'happy' | 'ask';

const r1 = (v: number) => Math.round(v * 10) / 10;
const TAU = Math.PI * 2;

/** Deterministic random numbers, so a pebble's speckles never change between renders. */
function rng(seed: string) {
  let h = 1779033703;
  for (let i = 0; i < seed.length; i++) h = Math.imul(h ^ seed.charCodeAt(i), 3432918353);
  return () => {
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return ((h ^= h >>> 16) >>> 0) / 4294967296;
  };
}

interface ShapeSpec {
  name: string;
  /** The outline, and the ellipse it roughly fills (for placing texture safely inside). */
  d: string;
  cx: number; cy: number; rx: number; ry: number;
  eyes: [number, number];
  tilt: number;
}

function lumpy(cx: number, cy: number, r: number, sy: number, wobble: readonly number[], rot: number): string {
  const n = wobble.length;
  const pts: P[] = wobble.map((w, i) => {
    const a = (rot * Math.PI) / 180 + (i / n) * TAU;
    return [r1(cx + Math.cos(a) * r * w), r1(cy + Math.sin(a) * r * w * sy)];
  });
  return spline(pts, { closed: true, z: true });
}

const SHAPES: Record<PebbleShape, ShapeSpec> = {
  river: { name: 'River', d: lumpy(32, 40, 19.5, 0.86, [1, 0.96, 1.04, 0.98, 1.03, 0.95, 1.02, 0.99, 1.05, 0.97], 10), cx: 32, cy: 40, rx: 19.5, ry: 16.8, eyes: [30.4, 37], tilt: -6 },
  round: { name: 'Round', d: lumpy(32, 40, 18.4, 0.97, [1, 0.98, 1.02, 0.99, 1.01, 0.97, 1.02, 1], 0), cx: 32, cy: 40, rx: 18.4, ry: 17.8, eyes: [31, 37.4], tilt: 4 },
  skimmer: { name: 'Skimmer', d: lumpy(32, 44, 23, 0.6, [1, 0.97, 1.03, 0.99, 1.02, 0.96, 1.01, 1], 6), cx: 32, cy: 44, rx: 23, ry: 13.8, eyes: [30, 42], tilt: -4 },
  tall: { name: 'Tall', d: lumpy(32, 39, 16.4, 1.28, [1, 0.97, 1.03, 0.99, 1.02, 0.96, 1.01, 1], -80), cx: 32, cy: 39, rx: 16.4, ry: 21, eyes: [31, 33.4], tilt: 6 },
  chipped: {
    name: 'Chipped',
    d: spline([[14, 44], [17, 30], [28, 22.4], [41, 23.6], [50, 32], [51, 45], [44, 56], [30, 59], [18, 54.4]], { closed: true, corners: [1, 3, 5, 7], z: true }),
    cx: 32.4, cy: 40.6, rx: 17.6, ry: 17, eyes: [30.6, 37.6], tilt: -3,
  },
  lumpy: { name: 'Lumpy', d: lumpy(32, 40, 19.4, 0.9, [1.08, 0.9, 1.05, 0.86, 1.1, 0.92, 1, 0.88], 20), cx: 32, cy: 40, rx: 17.4, ry: 15.6, eyes: [30.6, 37], tilt: 5 },
};

/** A crescent hugging the ellipse between two angles: the shadowed side or the sheen. */
function crescent(s: ShapeSpec, a0: number, a1: number, scale: number, thick: number, dx: number, dy: number): string {
  const pts: string[] = [];
  const N = 18;
  for (let i = 0; i <= N; i++) {
    const a = ((a0 + ((a1 - a0) * i) / N) * Math.PI) / 180;
    pts.push(`${r1(s.cx + Math.cos(a) * s.rx * scale)} ${r1(s.cy + Math.sin(a) * s.ry * scale)}`);
  }
  for (let i = N; i >= 0; i--) {
    const a = ((a0 + ((a1 - a0) * i) / N) * Math.PI) / 180;
    const taper = Math.sin((i / N) * Math.PI);
    const k = scale - thick * taper;
    pts.push(`${r1(s.cx + dx * taper + Math.cos(a) * s.rx * k)} ${r1(s.cy + dy * taper + Math.sin(a) * s.ry * k)}`);
  }
  return `M${pts[0]} L${pts.slice(1).join(' ')} Z`;
}

/** Random points inside the shape's ellipse, kept clear of the eyes. */
function scatter(s: ShapeSpec, n: number, seed: string, rMin: number, rMax: number, inset = 0.82): Array<[number, number, number]> {
  const rand = rng(seed);
  const out: Array<[number, number, number]> = [];
  let guard = 0;
  while (out.length < n && guard++ < n * 20) {
    const a = rand() * TAU, d = Math.sqrt(rand()) * inset;
    const x = s.cx + Math.cos(a) * s.rx * d, y = s.cy + Math.sin(a) * s.ry * d;
    if (Math.hypot(x - s.eyes[0], (y - s.eyes[1]) * 1.3) < 7.4) continue;
    out.push([r1(x), r1(y), r1(rMin + rand() * (rMax - rMin))]);
  }
  return out;
}
const flecks = (pts: Array<[number, number, number]>, c: ArtColour): Part => ['f', c, pts.map(([x, y, r]) => `O ${x} ${y} ${r}`).join(' ')];

/** A quartz vein: a lens-shaped white band across the stone, tapering to nothing at both ends. */
function vein(s: ShapeSpec): string {
  const top: string[] = [], bot: string[] = [];
  const N = 16;
  const ax = s.cx - s.rx * 0.05, ay = s.cy + s.ry * 0.86, bx = s.cx + s.rx * 0.84, by = s.cy - s.ry * 0.12;
  const len = Math.hypot(bx - ax, by - ay), nx = -(by - ay) / len, ny = (bx - ax) / len;
  for (let i = 0; i <= N; i++) {
    const t = i / N, x = ax + (bx - ax) * t, y = ay + (by - ay) * t;
    const wave = Math.sin(t * Math.PI * 2) * 0.7;
    const w = Math.sin(t * Math.PI) * 1.2;
    top.push(`${r1(x + nx * (wave - w))} ${r1(y + ny * (wave - w))}`);
    bot.unshift(`${r1(x + nx * (wave + w))} ${r1(y + ny * (wave + w))}`);
  }
  return `M${top[0]} L${[...top.slice(1), ...bot].join(' ')} Z`;
}

function eyes(s: ShapeSpec, mood: PebbleMood, light: boolean): Part[] {
  const [x, y] = s.eyes, gap = 6.6, k = 1.25;
  const look = mood === 'think' ? [-1.2, -1.4] : [0, 0];
  const lx = x - gap / 2 + look[0], rx = x + gap / 2 + look[0], ey = y + look[1];
  const c: ArtColour = light ? 'paper' : 'ink';
  if (mood === 'happy') {
    const arc = (cx: number) => `M${r1(cx - 2.6 * k)} ${r1(ey + 1 * k)} Q${r1(cx)} ${r1(ey - 3.2 * k)} ${r1(cx + 2.6 * k)} ${r1(ey + 1 * k)}`;
    return [['c', c, `${arc(lx)} ${arc(rx)}`, 0.55 * k]];
  }
  const big = mood === 'ask' ? 1.25 : 1;
  const ex = light ? 1.9 : 1.6, ey2 = light ? 2.6 : 2.1;
  const o = (cx: number, b: number) => {
    const a = ex * k * b, bb = ey2 * k * b;
    return `M${r1(cx + a)} ${r1(ey)} C${r1(cx + a)} ${r1(ey + bb * 0.55)} ${r1(cx + a * 0.55)} ${r1(ey + bb)} ${r1(cx)} ${r1(ey + bb)} C${r1(cx - a * 0.55)} ${r1(ey + bb)} ${r1(cx - a)} ${r1(ey + bb * 0.55)} ${r1(cx - a)} ${r1(ey)} C${r1(cx - a)} ${r1(ey - bb * 0.55)} ${r1(cx - a * 0.55)} ${r1(ey - bb)} ${r1(cx)} ${r1(ey - bb)} C${r1(cx + a * 0.55)} ${r1(ey - bb)} ${r1(cx + a)} ${r1(ey - bb * 0.55)} ${r1(cx + a)} ${r1(ey)} Z`;
  };
  return [['f', c, `${o(lx, 1)} ${o(rx, big)}`]];
}

function brows(s: ShapeSpec, mood: PebbleMood): Part {
  const [x, y] = s.eyes, l = r1(x - 4), r = r1(x + 4), b = r1(y - 7.4);
  const d =
    mood === 'think' ? `M${l - 3.4} ${b + 0.8} L${l + 2.6} ${b + 1.4} M${r - 2.8} ${b - 0.6} Q${r} ${b - 2.8} ${r + 3.4} ${b - 0.4}`
      : mood === 'ask' ? `M${l - 3.2} ${b - 0.2} Q${l} ${b - 2.6} ${l + 3} ${b - 0.6} M${r - 3} ${b - 0.6} Q${r} ${b - 2.6} ${r + 3.2} ${b - 0.2}`
        : `M${l - 3.2} ${b + 0.8} Q${l} ${b - 1} ${l + 3} ${b + 0.2} M${r - 3} ${b + 0.2} Q${r} ${b - 1} ${r + 3.2} ${b + 0.8}`;
  return ['c', 'ink', d, 0.8];
}

const star = (x: number, y: number, s: number): Part[] => {
  const d = `M${x} ${y - s} Q${x + s * 0.2} ${y - s * 0.2} ${x + s} ${y} Q${x + s * 0.2} ${y + s * 0.2} ${x} ${y + s} Q${x - s * 0.2} ${y + s * 0.2} ${x - s} ${y} Q${x - s * 0.2} ${y - s * 0.2} ${x} ${y - s} Z`;
  return [['f', 'lemon', d], ['s', d, 0.7]];
};
function extra(mood: PebbleMood, x: number, y: number): Part[] {
  if (mood === 'happy') return [...star(x, y, 4.2), ...star(x - 5, y + 9, 2.4)];
  if (mood === 'ask') return [['t', '?', x - 3, y + 6, 14, 'red', 'hand']];
  if (mood === 'think') return ([[x - 4, y + 10, 1.2], [x - 1.5, y + 5.5, 1.8], [x + 2.5, y, 2.6]] as const).flatMap(([cx, cy, r]): Part[] => [['f', 'paper', `O ${cx} ${cy} ${r}`], ['s', `O ${cx} ${cy} ${r}`, 0.6]]);
  return [];
}

/** A small ruled notebook page for the pebble to sit on, kept below it so no line crosses the stone. */
function page(s: ShapeSpec): Part[] {
  const top = Math.min(66, s.cy + s.ry * 1.14 + 1);
  const d = `M6 ${top + 0.6} L58 ${top - 0.4} L59 71 L5 71 Z`;
  return [
    // 'slip', not 'paper': the engine merges same-colour fills into the layer where the colour first
    // appears, so a 'paper' page drawn first would pull Soc's white eyes and hands under the stone.
    ['f', 'slip', d], ['s', d, 0.8],
    ['c', 'rule-blue', `M8 ${r1(top + 4)} L56 ${r1(top + 3.4)} M7.6 ${r1(top + 7.2)} L56.6 ${r1(top + 6.6)}`, 0.35],
    ['c', 'rule-red', `M12 ${r1(top + 0.6)} L11.8 71`, 0.35],
  ];
}

/** A laurel sprig tucked against the top right of the stone. */
function laurel(s: ShapeSpec): Part[] {
  const bx = s.cx + s.rx * 0.57, by = s.cy - s.ry * 0.98;
  const p = (x: number, y: number) => `${r1(bx + x)} ${r1(by + y)}`;
  const leaf = (x: number, y: number, ang: number): Part[] => {
    const a = (ang * Math.PI) / 180, c = Math.cos(a), sn = Math.sin(a);
    const q = (u: number, v: number) => p(x + u * c - v * sn, y + u * sn + v * c);
    const d = `M${q(0, 0)} Q${q(2.4, -1.8)} ${q(5.4, 0)} Q${q(2.4, 1.8)} ${q(0, 0)} Z`;
    return [['f', 'grass', d], ['s', d, 0.55]];
  };
  return [
    ['s', `M${p(-2, 3)} Q${p(4, -2)} ${p(11, -9)}`, 0.7],
    ...leaf(1, 0.6, -110), ...leaf(1.6, 0, 10), ...leaf(5.4, -3, -120), ...leaf(5.8, -3.4, 0), ...leaf(9.4, -7, -110),
  ];
}

export function pebbleArt(shape: PebbleShape, finish: PebbleFinish, mood: PebbleMood = 'idle', prop: PebbleProp = 'none'): ArtDef {
  const s = SHAPES[shape];
  const parts: Part[] = [];
  if (prop === 'page') parts.push(...page(s));
  const stoneAt = parts.length;
  const black = finish === 'plain' || finish === 'basalt' || finish === 'granite' || finish === 'quartz';
  if (black) {
    const base: ArtColour = finish === 'basalt' || finish === 'quartz' ? 'ink-soft' : 'ink';
    parts.push(['f', base, s.d]);
    if (finish !== 'plain') {
      if (base === 'ink-soft') parts.push(['f', 'ink', crescent(s, -15, 135, 0.97, 0.3, -2.4, -2.6)]);
      parts.push(['f', 'pencil-mark', crescent(s, 200, 250, 0.8, 0.09, 0.6, 0.6)]);
    }
    if (finish === 'basalt') parts.push(flecks(scatter(s, 22, `${shape}-pits`, 0.22, 0.5), 'ink'), flecks(scatter(s, 10, `${shape}-glint`, 0.18, 0.32), 'pencil-mark'));
    if (finish === 'granite') parts.push(flecks(scatter(s, 40, `${shape}-fleck`, 0.2, 0.5), 'pencil-mark'), flecks(scatter(s, 14, `${shape}-mica`, 0.18, 0.34), 'paper'));
    if (finish === 'quartz') parts.push(['f', 'paper', vein(s)], flecks(scatter(s, 12, `${shape}-pits`, 0.2, 0.42), 'ink'));
    parts.push(...eyes(s, mood, true));
  } else {
    parts.push(['f', 'pencil-mark', s.d]);
    parts.push(['f', 'paper~', crescent(s, 195, 255, 0.84, 0.12, 0.8, 0.8)]);
    parts.push(flecks(scatter(s, 14, `${shape}-speck`, 0.22, 0.45), 'ink-soft'));
    parts.push(['s', s.d, 1]);
    if (finish === 'brows') {
      const cx = s.cx + s.rx * 0.46, cy = s.cy - s.ry * 0.52;
      parts.push(['c', 'ink', `M${r1(cx)} ${r1(cy)} L${r1(cx - 1.6)} ${r1(cy + 2.6)} L${r1(cx + 0.4)} ${r1(cy + 4.2)} L${r1(cx - 1)} ${r1(cy + 6.8)}`, 0.4]);
      parts.push(brows(s, mood));
    }
    parts.push(...eyes(s, mood, false));
  }
  const stone = xf(parts.splice(stoneAt), { cx: s.cx, cy: s.cy, k: 1.14 });
  parts.push(...stone);
  if (prop === 'laurel') parts.push(...laurel(s));
  parts.push(...extra(mood, 56, 10));
  return { grid: [64, 72], nibK: 0.05, shade: false, parts, tilt: s.tilt, tags: ['pebble', shape, finish] };
}

export const PEBBLE_SHAPES: Record<PebbleShape, string> = Object.fromEntries(Object.entries(SHAPES).map(([k, v]) => [k, v.name])) as Record<PebbleShape, string>;
export const PEBBLE_KEYS = Object.keys(SHAPES) as PebbleShape[];
export const PEBBLE_FINISHES: Record<PebbleFinish, string> = {
  plain: 'Plain black', basalt: 'Basalt', granite: 'Granite', quartz: 'Quartz vein', drawn: 'Drawn stone', brows: 'Drawn + brows',
};
export const PEBBLE_PROPS: Record<PebbleProp, string> = { none: 'No prop', page: 'On a page', laurel: 'Laurel sprig' };
export const PEBBLE_MOODS: PebbleMood[] = ['idle', 'think', 'happy', 'ask'];

function hash(text: string): string {
  let h = 0;
  for (let i = 0; i < text.length; i++) h = (Math.imul(31, h) + text.charCodeAt(i)) | 0;
  return (h >>> 0).toString(36);
}

export function SocPebble({
  shape = 'river',
  finish = 'basalt',
  mood = 'idle',
  prop = 'none',
  size = 120,
  label,
  className,
  ...props
}: Omit<React.ComponentProps<'svg'>, 'children' | 'viewBox'> & {
  shape?: PebbleShape;
  finish?: PebbleFinish;
  mood?: PebbleMood;
  prop?: PebbleProp;
  size?: number;
  label?: string;
}) {
  useEnsureInkDefs();
  const uid = React.useId().replace(/[^a-zA-Z0-9]/g, '');
  const px = Math.max(16, Math.round(size));
  const art = pebbleArt(shape, finish, mood, prop);
  // The drawing itself is in the key, so an edited drawing is never served from a stale cache.
  const res = memo(`soc-pebble|${hash(JSON.stringify(art.parts))}|${px}|${uid}`, () => drawMascot(art, px, `${shape}-${finish}`, { idPrefix: `sp-${uid}` }), 200);
  return (
    <svg
      data-slot="soc-pebble"
      aria-hidden={label ? undefined : true}
      role={label ? 'img' : undefined}
      aria-label={label}
      focusable="false"
      viewBox={`0 0 ${res.w} ${res.h}`}
      width={res.w}
      height={res.h}
      className={cn('pointer-events-none shrink-0 overflow-visible ll-drop-sticker', className)}
      dangerouslySetInnerHTML={{ __html: res.svg }}
      {...props}
    />
  );
}

// ---------------------------------------------------------------------------------------------
// Soc: the round granite pebble, chosen as the mascot. Every mood SocFigure knows, eyes that can
// follow the pointer (in small steps, each drawing cached), a notebook page in place of the books,
// and a tight crop for avatars so the face stays readable at 24px.

type Gaze = { x: number; y: number };

function ovalPath(cx: number, cy: number, a: number, b: number): string {
  const c = 0.5523;
  return `M${r1(cx + a)} ${r1(cy)} C${r1(cx + a)} ${r1(cy + b * c)} ${r1(cx + a * c)} ${r1(cy + b)} ${r1(cx)} ${r1(cy + b)} C${r1(cx - a * c)} ${r1(cy + b)} ${r1(cx - a)} ${r1(cy + b * c)} ${r1(cx - a)} ${r1(cy)} C${r1(cx - a)} ${r1(cy - b * c)} ${r1(cx - a * c)} ${r1(cy - b)} ${r1(cx)} ${r1(cy - b)} C${r1(cx + a * c)} ${r1(cy - b)} ${r1(cx + a)} ${r1(cy - b * c)} ${r1(cx + a)} ${r1(cy)} Z`;
}

/** White eyes (and, for the strong moods, white brows) on the dark stone. */
function stoneFace(s: ShapeSpec, mood: SocMood, gaze: Gaze): Part[] {
  const think = mood === 'thinking' ? [-1.4, -1.6] : [0, 0];
  const x = s.eyes[0] + gaze.x * 1.8 + think[0], y = s.eyes[1] + gaze.y * 1.4 + think[1];
  const lx = r1(x - 3.3), rx = r1(x + 3.3), A = 2.4, B = 3.25;
  const eye = (cx: number, k = 1, dy = 0, sy = 1) => ovalPath(cx, y + dy, A * k, B * k * sy);
  const up = (cx: number) => `M${r1(cx - 3)} ${r1(y + 1.2)} Q${r1(cx)} ${r1(y - 3.8)} ${r1(cx + 3)} ${r1(y + 1.2)}`;
  const down = (cx: number) => `M${r1(cx - 3)} ${r1(y - 0.4)} Q${r1(cx)} ${r1(y + 3.4)} ${r1(cx + 3)} ${r1(y - 0.4)}`;
  const W = (d: string): Part => ['f', 'paper', d];
  const line = (d: string, w = 0.7): Part => ['c', 'paper', d, w];
  const brow = (x1: number, y1: number, x2: number, y2: number) => `M${r1(x1)} ${r1(y1)} L${r1(x2)} ${r1(y2)}`;
  switch (mood) {
    case 'happy':
    case 'proud':
      return [line(`${up(lx)} ${up(rx)}`)];
    case 'sleepy':
      return [line(`${down(lx)} ${down(rx)}`)];
    case 'wink':
      return [W(eye(lx)), line(up(rx))];
    case 'curious':
      return [W(`${eye(lx)} ${eye(rx, 1.22)}`)];
    case 'surprised':
      return [W(`${eye(lx, 1.32)} ${eye(rx, 1.32)}`), line(`${brow(lx - 2.6, y - 7.4, lx + 2.4, y - 8.2)} ${brow(rx - 2.4, y - 8.2, rx + 2.6, y - 7.4)}`, 0.55)];
    case 'confused':
      return [W(`${eye(lx, 0.8, 0.8)} ${eye(rx, 1.12)}`), line(`M${r1(rx - 2.8)} ${r1(y - 6.6)} Q${r1(rx - 1)} ${r1(y - 8.4)} ${r1(rx + 0.6)} ${r1(y - 6.8)} Q${r1(rx + 2)} ${r1(y - 5.6)} ${r1(rx + 3)} ${r1(y - 7)}`, 0.55)];
    case 'worried':
      return [W(`${eye(lx)} ${eye(rx)}`), line(`${brow(lx - 2.8, y - 5.4, lx + 2.4, y - 7.4)} ${brow(rx - 2.4, y - 7.4, rx + 2.8, y - 5.4)}`, 0.55)];
    case 'angry':
      return [W(`${eye(lx, 1, 0.4, 0.8)} ${eye(rx, 1, 0.4, 0.8)}`), line(`${brow(lx - 2.8, y - 7.2, lx + 2.6, y - 4.6)} ${brow(rx - 2.6, y - 4.6, rx + 2.8, y - 7.2)}`, 0.6)];
    default:
      return [W(`${eye(lx)} ${eye(rx)}`)];
  }
}

/** The small prop beside the stone that carries the mood past the face. */
function stoneExtra(mood: SocMood): Part[] {
  const x = 55, y = 10;
  switch (mood) {
    case 'happy': return [...star(x, y, 4.2), ...star(x - 5, y + 9, 2.4)];
    case 'proud': return [...star(x, y, 4.6), ...star(x - 5.4, y + 9.4, 2.6), ...star(8.6, 22, 3)];
    case 'thinking': return extra('think', x, y);
    case 'curious':
    case 'confused': return [['t', '?', x - 3, y + 6, 14, 'red', 'hand']];
    case 'sleepy': return [['t', 'z', x - 6, y + 9, 8, 'red', 'hand'], ['t', 'z', x - 1, y + 3, 11, 'red', 'hand']];
    case 'surprised': return [['c', 'red', `M${x - 6} ${y + 6} L${x - 3} ${y + 9} M${x - 1} ${y + 2} L${x - 1} ${y + 6.4} M${x + 3} ${y + 7} L${x + 6} ${y + 5}`, 0.6]];
    case 'worried': {
      const d = 'M50 20 Q47.6 24.4 47.8 26.2 Q48.2 28.6 50.4 28.6 Q52.6 28.4 52.6 26 Q52.4 24 50 20 Z';
      return [['f', 'sky', d], ['s', d, 0.6]];
    }
    case 'angry': return [['c', 'red', `M${x - 4} ${y + 2} Q${x - 1} ${y + 2} ${x - 1} ${y - 1} M${x + 2} ${y - 1} Q${x + 2} ${y + 2} ${x + 5} ${y + 2} M${x + 5} ${y + 5} Q${x + 2} ${y + 5} ${x + 2} ${y + 8} M${x - 1} ${y + 8} Q${x - 1} ${y + 5} ${x - 4} ${y + 5}`, 0.6]];
    default: return [];
  }
}

/**
 * Soc's hands: small white cartoon hands that float at the stone, no arms. Drawn in the final
 * 64x72 grid (after the stone is grown). Each pose is written once; `flip` mirrors it across the
 * stone's centre line, so a steeple or a shrug is one hand and its mirror.
 */
export type HandPose = 'none' | 'steeple' | 'wave' | 'chin' | 'shrug' | 'thumbs';
export const HAND_POSES: readonly HandPose[] = ['steeple', 'wave', 'chin', 'shrug', 'thumbs'];

const flip = (d: string) => d.replace(/(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)/g, (_, x: string, y: string) => `${r1(64 - Number(x))} ${y}`);
const hand = (d: string, lines = ''): Part[] => [['f', 'paper', d], ['s', d, 0.8], ...(lines ? [['s', lines, 0.5] as Part] : [])];
const both = (d: string, lines: string): Part[] => [...hand(d, lines), ...hand(flip(d), flip(lines))];

/** How much each pose grows, and the point it grows from (where the hand meets the stone). */
const HAND_SCALE: Partial<Record<HandPose, [number, number, number]>> = { steeple: [32, 60.6, 1.2], wave: [11, 37, 1.05], chin: [41, 59.4, 1.3], thumbs: [52, 48, 1.3] };

function hands(pose: HandPose): Part[] {
  const sc = HAND_SCALE[pose];
  const parts = handParts(pose);
  return sc ? xf(parts, { cx: sc[0], cy: sc[1], k: sc[2] }) : parts;
}

function handParts(pose: HandPose): Part[] {
  switch (pose) {
    case 'steeple': {
      // Fingertips meet under the eyes, thumbs meet below them, the stone shows through the tent.
      const d = 'M23.6 60.4 Q22.4 55.6 24.6 53 L30.4 46.6 Q31.9 45.4 32.2 47.2 L32.1 48.2 Q31.4 50.8 29.6 53.6 Q29.6 55.4 31.4 56.2 Q32.4 57.2 31.4 58.2 Q29.8 59.6 28 60.6 Z';
      return both(d, 'M25.8 54.8 L30.6 49.2 M26.6 57 L30.2 53');
    }
    case 'wave': {
      // A chunky open hand: thumb out, four short rounded fingers, drawn in its own box then placed.
      const d = 'M5 21 Q3.4 17.6 3.6 14 L1.2 11.6 Q0 10.4 1 9.6 Q2 9 3 10 L5 12 L5.2 5 Q5.4 3.4 6.9 3.4 Q8.4 3.4 8.4 5 L8.4 11 L8.6 4.2 Q8.8 2.4 10.4 2.4 Q12 2.4 12 4.2 L11.8 11 L12.2 5.2 Q12.6 3.6 14 3.8 Q15.4 4 15.2 5.6 L14.6 11.6 L15.2 8 Q15.8 6.8 17 7.2 Q18 7.6 17.6 9 L16.4 14 Q16.4 18 14 21 Q9.5 23 5 21 Z';
      return [...xf(hand(d, 'M7.4 16.6 Q9.8 17.8 12.6 16.4'), { dx: 1.5, dy: 15.5, k: 1 }), ['c', 'red', 'M2.6 17.6 Q2.6 15.2 4.6 13.8 M0.8 22.4 Q0.4 20.2 1.4 18.6', 0.6]];
    }
    case 'chin': {
      // A fist under the face, one finger up: hmm.
      const d = 'M37.6 53 Q37 58.6 41.4 59.2 Q45.6 59.4 46 55.4 Q46.2 52 43.6 51.6 L42 51.6 L41.6 46.8 Q41.4 45.6 40.4 45.8 Q39.4 46 39.6 47.2 L39.8 51.8 Q38 52 37.6 53 Z';
      return hand(d, 'M41.8 54.2 Q43.6 53.8 45.6 54.6 M41.6 56.6 Q43.4 56.4 45.4 57');
    }
    case 'shrug': {
      const d = 'M15 47.6 L13 47.2 Q12.6 44.4 11.4 44.6 Q10.2 44.8 10.6 47 L8 46.6 Q5.6 46.4 5.6 48.2 Q5.8 49.8 8.2 50.2 L12.4 51.6 Q14.8 52.4 15.6 50.4 Z';
      return both(d, 'M6.6 48.4 L11 49');
    }
    case 'thumbs': {
      const d = 'M51 42 Q50.6 47.6 54 48.2 Q58.4 48.6 58.8 45.2 Q59 42 56.6 41.6 L55.4 41.4 L55.6 37.6 Q55.4 36 54 36.2 Q52.8 36.6 53 38.2 L53.2 41.4 Q51.4 41.4 51 42 Z';
      return hand(d, 'M54.2 43.6 L58.4 43.8 M54 45.8 L58.2 46');
    }
    default:
      return [];
  }
}

/** The pose each mood reaches for when Soc has room for hands. */
const MOOD_HANDS: Partial<Record<SocMood, HandPose>> = {
  neutral: 'steeple',
  curious: 'steeple',
  thinking: 'chin',
  happy: 'wave',
  proud: 'thumbs',
  wink: 'thumbs',
  confused: 'shrug',
};

/** Moods whose eyes are open, so a blink frame means something (happy, proud, sleepy already squint). */
const BLINKS: ReadonlySet<SocMood> = new Set<SocMood>(['neutral', 'curious', 'thinking', 'surprised', 'confused', 'worried', 'angry', 'wink']);

/**
 * The face with its open eyes shut: the same brows and marks, eyes as short closed curves.
 * Wink keeps its already-closed eye and shuts the open one.
 */
function closedFace(s: ShapeSpec, mood: SocMood, gaze: Gaze): Part[] {
  const open = stoneFace(s, mood, gaze).filter(p => !(p[0] === 'f' && p[1] === 'paper'));
  const think = mood === 'thinking' ? [-1.4, -1.6] : [0, 0];
  const x = s.eyes[0] + gaze.x * 1.8 + think[0], y = s.eyes[1] + gaze.y * 1.4 + think[1];
  const shut = (cx: number) => `M${r1(cx - 2.6)} ${r1(y + 0.2)} Q${r1(cx)} ${r1(y + 1.6)} ${r1(cx + 2.6)} ${r1(y + 0.2)}`;
  const eyes = mood === 'wink' ? shut(x - 3.3) : `${shut(x - 3.3)} ${shut(x + 3.3)}`;
  return [...open, ['c', 'paper', eyes, 0.7]];
}

/** The second drawing of a gesture: where the hands and the mood's props move to on the beat. */
function beatHands(pose: HandPose, parts: Part[]): Part[] {
  switch (pose) {
    case 'wave': return xf(parts, { cx: 12, cy: 46, rot: -18 });
    case 'thumbs': return xf(parts, { cx: 54, cy: 46, rot: -10, dy: -1.6 });
    case 'chin': return xf(parts, { cx: 41, cy: 58, rot: 7 });
    case 'shrug': return xf(parts, { dy: -2.2 });
    case 'steeple': return xf(parts, { cx: 32, cy: 58, k: 1.04, dy: -0.6 });
    default: return parts;
  }
}

function beatExtra(mood: SocMood, parts: Part[]): Part[] {
  if (!parts.length) return parts;
  switch (mood) {
    case 'happy':
    case 'proud': return xf(parts, { cx: 52, cy: 14, k: 1.22, rot: 12 });
    case 'sleepy':
    case 'thinking': return xf(parts, { dy: -2.4, dx: 0.8 });
    case 'worried': return xf(parts, { dy: 2.6 });
    case 'curious':
    case 'confused': return xf(parts, { cx: 52, cy: 12, rot: 14 });
    default: return xf(parts, { cx: 55, cy: 12, k: 1.18 });
  }
}

/** Which drawing of Soc: the resting one, the blink, or the gesture's second beat. */
type Frame = 'base' | 'blink' | 'beat';

export function socStoneArt(
  mood: SocMood = 'neutral',
  o: { gaze?: Gaze; page?: boolean; crop?: boolean; hands?: HandPose; frame?: Frame } = {},
): ArtDef {
  const s = SHAPES.round;
  const gaze = o.gaze ?? { x: 0, y: 0 };
  const frame = o.frame ?? 'base';
  const stone: Part[] = [
    ['f', 'ink', s.d],
    ['f', 'pencil-mark', crescent(s, 200, 250, 0.8, 0.09, 0.6, 0.6)],
    flecks(scatter(s, 40, 'round-fleck', 0.2, 0.5), 'pencil-mark'),
    flecks(scatter(s, 14, 'round-mica', 0.18, 0.34), 'paper'),
  ];
  // The face is drawn last, so a blink frame is the same drawing up to the eyes and lines up exactly.
  const face = xf(frame === 'blink' ? closedFace(s, mood, gaze) : stoneFace(s, mood, gaze), { cx: s.cx, cy: s.cy, k: 1.14 });
  const grown = xf(stone, { cx: s.cx, cy: s.cy, k: 1.14 });
  const pose = o.hands ?? 'none';
  if (o.crop) {
    // The stone alone, centred in a square: what an avatar needs.
    const own = pose === 'steeple' || pose === 'chin' ? hands(pose) : [];
    return { grid: [48, 48], nibK: 0.05, shade: false, parts: xf([...grown, ...own, ...face], { dx: -8, dy: -16, k: 1 }), tilt: s.tilt, tags: ['soc'] };
  }
  const handParts = frame === 'beat' ? beatHands(pose, hands(pose)) : hands(pose);
  const extraParts = frame === 'beat' ? beatExtra(mood, stoneExtra(mood)) : stoneExtra(mood);
  const parts: Part[] = [...(o.page ? page(s) : []), ...grown, ...handParts, ...extraParts, ...face];
  return { grid: [64, 72], nibK: 0.05, shade: false, parts, tilt: s.tilt, tags: ['soc'] };
}

/** Soc as drawn everywhere in the app. `size` is the width in px; without it the figure fills its box. */
export function SocStone({
  mood = 'neutral',
  look,
  books = false,
  idle = false,
  hands: handsProp,
  size,
  className,
  style,
  title,
}: {
  mood?: SocMood;
  look?: Gaze;
  books?: boolean;
  idle?: boolean;
  /** A hand pose, or false for none. By default the mood picks one when Soc is 56px or larger. */
  hands?: HandPose | false;
  size?: number;
  className?: string;
  style?: React.CSSProperties;
  title?: string;
}) {
  useEnsureInkDefs();
  const uid = React.useId().replace(/[^a-zA-Z0-9]/g, '');
  // Up to 120px with no page, Soc is an avatar: the stone alone, filling its box.
  const crop = !books && size !== undefined && size <= 120;
  // Pointer-following moves the eyes in half steps, so at most 25 drawings per mood are cached.
  const q = (v: number | undefined) => Math.round(Math.max(-1, Math.min(1, v ?? 0)) * 2) / 2;
  const gaze = { x: q(look?.x), y: q(look?.y) };
  const pose = handsProp === false ? 'none' : (handsProp ?? (size === undefined || size >= 56 ? MOOD_HANDS[mood] : undefined) ?? 'none');
  const width = size ?? 220;
  // Tiny avatars stay still; from 32px he blinks, and with room for hands or props he gestures.
  const blinks = width >= 32 && BLINKS.has(mood);
  const gestures = !crop && (pose !== 'none' || stoneExtra(mood).length > 0);
  const draw = (frame: Frame) => {
    const art = socStoneArt(mood, { gaze, page: books, crop, hands: pose, frame });
    const [gw, gh] = art.grid as readonly [number, number];
    const px = Math.max(16, Math.round((width * gh) / gw));
    // Every frame shares one seed, so the lines they have in common are drawn identically.
    return memo(`soc-stone|${hash(JSON.stringify(art.parts))}|${px}|${uid}`, () => drawMascot(art, px, 'soc', { idPrefix: `ss-${uid}` }), 300);
  };
  // 0 to 1, steady for this Soc: offsets its blink and gesture so a page of Socs is not in step.
  const shift = ([...uid].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 997, 7) % 100) / 100;
  const figure = React.useRef<HTMLSpanElement>(null);
  // His blink, and (when idle with hands to move) his repeated gesture: see lib/soc-blink.ts.
  const beats = Boolean(idle && gestures);
  React.useEffect(() => (figure.current && (blinks || beats) ? watchFigure(figure.current, shift, { blinks, beats }) : undefined), [blinks, beats, shift, mood]);
  const base = draw('base');
  const blink = blinks ? draw('blink') : null;
  const beat = gestures ? draw('beat') : null;
  const frame = (res: { w: number; h: number; svg: string }, kind: Frame) => (
    <svg
      data-frame={kind}
      viewBox={`0 0 ${res.w} ${res.h}`}
      className={kind === 'base' ? 'soc-frame block h-auto w-full overflow-visible' : 'soc-frame pointer-events-none absolute inset-0 h-full w-full overflow-visible'}
      aria-hidden="true"
      focusable="false"
      dangerouslySetInnerHTML={{ __html: res.svg }}
    />
  );
  return (
    <span
      // A new mood remounts the figure, so its reaction plays once.
      key={mood}
      ref={figure}
      data-slot="soc"
      data-mood={mood}
      data-pose={pose}
      data-gestures={gestures ? '' : undefined}
      className={cn('soc relative block shrink-0 select-none ll-drop-sticker', idle && 'soc-idle', className)}
      style={{ width: size, '--soc-shift': shift, ...style } as React.CSSProperties}
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      {frame(base, 'base')}
      {beat ? frame(beat, 'beat') : null}
      {blink ? frame(blink, 'blink') : null}
    </span>
  );
}
