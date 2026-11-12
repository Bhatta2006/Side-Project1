'use client';
// Soc as one soft silhouette: a single wonky shape, two small eyes, no mouth, no props. The idea is
// a character that reads at 16px and at 300px alike. Nine shapes, four treatments, four moods,
// compared on /dev-mascots before one replaces the plain-SVG bust in soc.tsx.
import * as React from 'react';

import { cn } from '@/lib/utils';
import { useEnsureInkDefs } from '@/lib/ink/react';
import { drawMascot } from '@/lib/ink/art/mascot-draw';
import { memo } from '@/lib/ink/art-draw';
import { oval, spline, type P } from '@/lib/ink/art/mascots/body';
import type { ArtColour, ArtDef, Part } from '@/lib/ink/art/types';

export type BlobMood = 'idle' | 'think' | 'happy' | 'ask';
export type BlobShape = 'blot' | 'cloud' | 'soc' | 'cumulus' | 'pebble' | 'asterisk' | 'drop' | 'question' | 'sprout';
/** ink: dark silhouette, white eyes. flat: brand colour, no outline. colour: marker fill, ink outline. sketch: paper, pencil outline. */
export type BlobTreatment = 'ink' | 'flat' | 'colour' | 'sketch';

const r1 = (v: number) => Math.round(v * 10) / 10;

/** A lumpy closed shape through points at the given radii, evenly spaced around a centre. */
function lumpy(cx: number, cy: number, radii: readonly number[], rot = 0, sy = 1): string {
  const n = radii.length;
  const pts: P[] = radii.map((r, i) => {
    const a = ((rot + (i / n) * 360) * Math.PI) / 180;
    return [r1(cx + Math.cos(a) * r), r1(cy + Math.sin(a) * r * sy)];
  });
  return spline(pts, { closed: true, z: true });
}

/** Joins points with outward bumps (clockwise order), so an edge reads as cloud or wool. */
function scallop(pts: ReadonlyArray<readonly [number, number]>, bulge: number): string {
  let d = '';
  for (let i = 1; i < pts.length; i++) {
    const [ax, ay] = pts[i - 1], [bx, by] = pts[i];
    const len = Math.hypot(bx - ax, by - ay) || 1;
    d += ` Q${r1((ax + bx) / 2 + ((by - ay) / len) * bulge)} ${r1((ay + by) / 2 - ((bx - ax) / len) * bulge)} ${r1(bx)} ${r1(by)}`;
  }
  return d;
}

interface Spec {
  name: string;
  note: string;
  colour: ArtColour;
  /** The silhouette, plus small satellite shapes (splashes, puffs, the question dot). */
  body: string[];
  /** Detail drawn on top, in the outline colour (a leaf, a chisel facet). */
  detail?: (t: BlobTreatment) => Part[];
  eyes: { x: number; y: number; gap: number; k?: number };
  brows?: string;
  extra: [number, number];
  /** A slight lean, for attitude. */
  tilt?: number;
}

const SHAPES: Record<BlobShape, Spec> = {
  blot: {
    name: 'Ink blot', note: 'A splat of ink off the nib: the notebook’s own creature.', colour: 'ink-you',
    body: [lumpy(32, 40, [21, 17.5, 22.5, 16.5, 21.5, 18, 23, 16, 20.5, 17], -8, 1.02), 'O 55 22 2.6', 'O 9.6 58 2', 'O 51.6 63 1.5'],
    eyes: { x: 31, y: 36, gap: 6.4 }, extra: [55, 10], tilt: -6,
  },
  cloud: {
    name: 'Thought cloud', note: 'Soc as the thought itself, trailing little puffs.', colour: 'sky',
    body: [`M12 46 Q6.6 45.6 7.4 39.4 Q8 33.4 14 33.6${scallop([[14, 33.6], [17.6, 24.6], [27.4, 19.6], [37.6, 21], [45.4, 25.6], [50.6, 32.6], [56.4, 39.4], [52, 46.4]], 3.4)} Q32 49.6 12 46 Z`, 'O 17.6 56 3.4', 'O 11 63.6 2.2'],
    eyes: { x: 31, y: 35, gap: 6.6 }, extra: [56, 12], tilt: 4,
  },
  soc: {
    name: 'Soc silhouette', note: 'Bald dome, cloud beard, heavy brows: Socrates in one shape.', colour: 'kraft',
    body: [`M15.6 30 E 32 30 16.4 17.4 180 360${scallop([[48.4, 30], [51.4, 38.6], [49.4, 47.4], [43.6, 54.6], [36.4, 60.2], [28, 60.4], [20.4, 55.6], [14.8, 47.8], [12.6, 38.4], [15.6, 30]], 3.6)} Z`],
    eyes: { x: 32, y: 29.6, gap: 6.8 }, brows: 'M20.6 23.4 Q25.4 19.8 30 22.6 M34 22.6 Q38.6 19.8 43.4 23.4', extra: [56, 10], tilt: -4,
  },
  cumulus: {
    name: 'Cumulus', note: 'A tall cloud on two small feet, walking along with you.', colour: 'grape',
    body: [`M17 56${scallop([[17, 56], [13.4, 47], [14.8, 38], [19, 29.4], [25, 21.8], [32.6, 18.4], [40.6, 21.2], [46.2, 28.6], [49.8, 37.6], [50.8, 47], [47, 56]], 3.8)} Q32 59.6 17 56 Z`, 'O 26 61.6 2.8', 'O 38.4 61.6 2.8'],
    eyes: { x: 31.4, y: 36, gap: 6.6 }, extra: [56, 10], tilt: -3,
  },
  pebble: {
    name: 'Pebble', note: 'Socrates trained as a stonemason. A smooth stone, one chisel facet.', colour: 'pencil-mark',
    body: [spline([[14, 46], [16, 33], [25, 24], [37, 22.4], [47.6, 28], [52, 40], [49, 53], [38, 60], [24, 59.4], [15.4, 53.6]], { closed: true, z: true })],
    detail: () => [['c', 'paper', 'M40.4 26.6 Q46.6 30 48.6 37', 0.5]],
    eyes: { x: 29.4, y: 39, gap: 6.6 }, extra: [56, 12], tilt: -8,
  },
  asterisk: {
    name: 'Soft asterisk', note: 'The ✳ from the Socrat wordmark, gone soft and curious.', colour: 'tomato',
    body: [lumpy(32, 39, [23, 14.6, 22.4, 15.2, 23.6, 14.4, 22.6, 15, 23.2, 14.6, 22.8, 15], -90)],
    eyes: { x: 32, y: 38.6, gap: 5.6, k: 0.85 }, extra: [57, 8], tilt: 8,
  },
  drop: {
    name: 'Ink drop', note: 'One drop of ink, about to write something down.', colour: 'teal',
    body: ['M32.4 8 C35.6 19.6 50.4 29.4 50.4 44.4 C50.4 56.6 42.4 64.4 32 64.4 C21.6 64.4 13.6 56.6 13.6 44.4 C13.6 29.6 28.6 20 32.4 8 Z'],
    eyes: { x: 31.4, y: 44, gap: 6.6 }, extra: [54, 14], tilt: 6,
  },
  question: {
    name: 'Question hook', note: 'A soft question mark, eyes in the curl.', colour: 'lemon',
    body: [spline([[14.6, 25], [17.4, 13.6], [28, 6.8], [40.6, 8], [48.6, 16.6], [48, 28], [41.4, 36.4], [37.8, 43], [37.2, 49.6], [27.6, 49.6], [27.4, 42], [30.6, 34.2], [36.4, 27.6], [37.2, 21.6], [32.4, 18.6], [27, 20.4], [25.4, 26.4]], { closed: true, z: true }), 'O 32.4 60 5.4'],
    eyes: { x: 32.4, y: 12.8, gap: 5.6, k: 0.75 }, extra: [56, 30], tilt: 5,
  },
  sprout: {
    name: 'Sprouting bean', note: 'A bean with one leaf: curiosity, growing.', colour: 'sticky-green',
    body: [spline([[13.6, 44], [16.6, 30.6], [27, 25.2], [33.6, 28.6], [40.4, 25.4], [49.6, 31], [51.6, 45], [45, 58.6], [32, 62.6], [19, 58.4]], { closed: true, z: true })],
    detail: t => [
      ['s', 'M33.4 28.6 Q32.6 20 35.6 14', 1],
      ['f', t === 'ink' ? 'grass' : 'grass', 'M35.6 14 Q38.4 5.4 48.4 6.4 Q46 14.6 35.6 14 Z'],
      ['s', 'M35.6 14 Q38.4 5.4 48.4 6.4 Q46 14.6 35.6 14 Z', 0.85],
    ],
    eyes: { x: 31, y: 42, gap: 6.6 }, extra: [56, 22], tilt: -5,
  },
};

const star = (x: number, y: number, s: number): Part[] => {
  const d = `M${x} ${y - s} Q${x + s * 0.2} ${y - s * 0.2} ${x + s} ${y} Q${x + s * 0.2} ${y + s * 0.2} ${x} ${y + s} Q${x - s * 0.2} ${y + s * 0.2} ${x - s} ${y} Q${x - s * 0.2} ${y - s * 0.2} ${x} ${y - s} Z`;
  return [['f', 'lemon', d], ['s', d, 0.7]];
};

function extra(mood: BlobMood, x: number, y: number): Part[] {
  if (mood === 'happy') return [...star(x, y, 4.2), ...star(x - 5, y + 9, 2.4)];
  if (mood === 'ask') return [['t', '?', x - 3, y + 6, 14, 'red', 'hand']];
  if (mood === 'think') return ([[x - 4, y + 10, 1.2], [x - 1.5, y + 5.5, 1.8], [x + 2.5, y, 2.6]] as const).flatMap(([cx, cy, r]): Part[] => [['f', 'paper', `O ${cx} ${cy} ${r}`], ['s', `O ${cx} ${cy} ${r}`, 0.6]]);
  return [];
}

/** Eyes: small upright ovals, Soc's whole expression. White on ink, ink on everything else. */
function eyes(spec: Spec, mood: BlobMood, t: BlobTreatment): Part[] {
  const { x, y, gap } = spec.eyes, k = (spec.eyes.k ?? 1) * 1.25;
  const light = t === 'ink';
  const ink: ArtColour = light ? 'paper' : 'ink';
  const look = mood === 'think' ? [-1.2, -1.4] : [0, 0];
  const lx = x - gap / 2 + look[0], rx = x + gap / 2 + look[0], ey = y + look[1];
  if (mood === 'happy') {
    const arc = (cx: number) => `M${r1(cx - 2.6 * k)} ${r1(ey + 1 * k)} Q${r1(cx)} ${r1(ey - 3.2 * k)} ${r1(cx + 2.6 * k)} ${r1(ey + 1 * k)}`;
    return [['c', ink, `${arc(lx)} ${arc(rx)}`, 0.55 * k]];
  }
  const big = mood === 'ask' ? 1.25 : 1;
  return [['f', ink, `${oval(r1(lx), r1(ey), 1.9 * k, 2.6 * k)} ${oval(r1(rx), r1(ey), 1.9 * k * big, 2.6 * k * big)}`]];
}

export function blobArt(shape: BlobShape, mood: BlobMood = 'idle', t: BlobTreatment = 'ink'): ArtDef {
  const spec = SHAPES[shape];
  const fill: ArtColour = t === 'ink' ? 'ink' : t === 'sketch' ? 'paper' : spec.colour;
  const parts: Part[] = [];
  for (const d of spec.body) {
    parts.push(['f', fill, d]);
    if (t === 'colour' || t === 'sketch') parts.push(t === 'sketch' ? ['c', 'pencil', d, 0.55] : ['s', d, 1]);
  }
  if (t === 'sketch') parts.push(['c', 'pencil', 'M20 50 L24 46 M22 53 L27 48 M25 55 L30 50', 0.35]);
  parts.push(...(spec.detail?.(t) ?? []));
  if (spec.brows) parts.push(['c', t === 'ink' ? 'paper' : 'ink', spec.brows, 0.8]);
  parts.push(...eyes(spec, mood, t), ...extra(mood, ...spec.extra));
  return { grid: [64, 72], nibK: 0.05, shade: false, parts, tags: [shape, t], ...(spec.tilt ? { tilt: spec.tilt } : {}) };
}

export const BLOB_SHAPES = SHAPES as Readonly<Record<BlobShape, Pick<Spec, 'name' | 'note'>>>;
export const BLOB_KEYS = Object.keys(SHAPES) as BlobShape[];
export const BLOB_MOODS: BlobMood[] = ['idle', 'think', 'happy', 'ask'];
export const BLOB_TREATMENTS: BlobTreatment[] = ['ink', 'flat', 'colour', 'sketch'];

function hash(text: string): string {
  let h = 0;
  for (let i = 0; i < text.length; i++) h = (Math.imul(31, h) + text.charCodeAt(i)) | 0;
  return (h >>> 0).toString(36);
}

export function SocBlob({
  shape = 'soc',
  mood = 'idle',
  treatment = 'ink',
  size = 120,
  seed,
  label,
  className,
  ...props
}: Omit<React.ComponentProps<'svg'>, 'children' | 'viewBox'> & {
  shape?: BlobShape;
  mood?: BlobMood;
  treatment?: BlobTreatment;
  size?: number;
  seed?: string | number;
  label?: string;
}) {
  useEnsureInkDefs();
  const uid = React.useId().replace(/[^a-zA-Z0-9]/g, '');
  const px = Math.max(16, Math.round(size));
  const art = blobArt(shape, mood, treatment);
  // The drawing itself is in the key, so an edited drawing is never served from a stale cache.
  const res = memo(`soc-blob|${hash(JSON.stringify(art.parts))}|${px}|${seed ?? ''}|${uid}`, () => drawMascot(art, px, seed ?? `${shape}-${mood}`, { idPrefix: `sb-${uid}` }), 160);
  return (
    <svg
      data-slot="soc-blob"
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
