import { Ink, type InkResult } from '@/lib/ink/builder'
import { badgeSkeleton, paintSkeleton, textPath } from '@/lib/ink/art-draw'
import { smoothClosed, TIERS } from '@/lib/ink/geom'
import type { PaintKey } from '@/lib/ink/paint'
import { clamp } from '@/lib/ink/rng'
import type { ArtDef, BadgeGen, Part } from '@/lib/ink/art/types'
import type { Pt, Tier } from '@/lib/ink/types'

export const sealVariantList = ['scallop', 'starburst', 'rosette', 'medal', 'shield', 'plate', 'ticket', 'tag', 'ring', 'wax'] as const
export type SealVariant = (typeof sealVariantList)[number]
export const sealMarkList = ['check', 'star'] as const
export type SealMark = (typeof sealMarkList)[number]

export type SealTone = Exclude<PaintKey, 'current'>

export interface SealParams {
  variant: SealVariant
  text?: string
  sub?: string
  mark?: SealMark
  tone?: SealTone
  ribbon?: SealTone
  ring?: string
  deco?: BadgeGen['deco']
  textColor?: SealTone
}

const r1 = (v: number) => Math.round(v * 10) / 10
const PI2 = Math.PI * 2

function scalloped(cx: number, cy: number, r0: number, peak: number, bumps: number, rot = 0): string {
  let d = ''
  const pt = (a: number, r: number): [number, number] => [cx + Math.cos(a) * r, cy + Math.sin(a) * r]
  for (let i = 0; i < bumps; i++) {
    const a0 = rot + (i / bumps) * PI2, a1 = rot + ((i + 1) / bumps) * PI2
    const v = pt(a0, r0 + (i % 3) * 0.12), c = pt((a0 + a1) / 2, peak + ((i * 7) % 5) * 0.08), e = pt(a1, r0 + (((i + 1) % bumps) % 3) * 0.12)
    if (i === 0) d += `M${r1(v[0])} ${r1(v[1])}`
    d += ` Q${r1(c[0])} ${r1(c[1])} ${r1(e[0])} ${r1(e[1])}`
  }
  return d + ' Z'
}

const checkPath = (cx: number, cy: number, s: number) => `M${r1(cx - 0.42 * s)} ${r1(cy + 0.04 * s)} L${r1(cx - 0.1 * s)} ${r1(cy + 0.36 * s)} L${r1(cx + 0.5 * s)} ${r1(cy - 0.38 * s)}`

const starPath = (cx: number, cy: number, ro: number) => {
  let d = ''
  for (let i = 0; i < 10; i++) {
    const a = ((-90 + i * 36) * Math.PI) / 180
    const r = i % 2 ? ro * 0.44 : ro
    d += `${i ? ' L' : 'M'}${r1(cx + Math.cos(a) * r)} ${r1(cy + Math.sin(a) * r)}`
  }
  return d + ' Z'
}

function withMark(parts: readonly Part[], mark: SealMark, small: boolean, tiny: boolean): Part[] {
  const out: Part[] = []
  for (let i = 0; i < parts.length; i++) {
    const p = parts[i]
    if (tiny && p[0] === 'c' && p[1] === 'photo') {
      const next = parts[i + 1]
      if (next && next[0] === 's' && next[1] === p[2]) i++
      continue
    }
    if (p[0] !== 't') {
      out.push(p)
      continue
    }
    const [, , x, y, em] = p
    const cy = y - 0.745 * em * 0.5
    const s = em * (tiny ? 1.5 : 1.05)
    if (mark === 'check') out.push(['s', checkPath(x, cy, s), tiny ? 2.6 : small ? 1.9 : 1.75, { start: 'pool', end: 'flick' }])
    else out.push(['f', 'lemon', starPath(x, cy, s * 0.5)], ['s', starPath(x, cy, s * 0.52), small ? 1.1 : 0.9])
  }
  return out
}

function recolour(parts: readonly Part[], ribbon: SealTone | undefined): Part[] {
  if (!ribbon || ribbon === 'tomato') return [...parts]
  let seen = 0
  return parts.map((p, i) => {
    if (p[0] === 'f' && p[1] === 'tomato' && i < 2 && seen++ < 2) return ['f', ribbon, p[2], p[3]] as Part
    return p
  })
}

function badgeDef(p: SealParams, px: number): ArtDef {
  const shape = p.variant as NonNullable<BadgeGen['shape']>
  const base = badgeSkeleton(p.text || 'A', { shape, color: p.tone ?? 'bubblegum', sub: p.variant === 'ticket' ? undefined : p.sub, deco: p.deco, textColor: p.textColor })
  let parts = [...base.parts]
  let small = [...(base.small ?? base.parts)]
  if (p.mark) {
    parts = withMark(parts, p.mark, false, false)
    small = withMark(small, p.mark, true, px < 40)
  } else if (!p.text) {
    parts = parts.filter((q) => q[0] !== 't')
    small = small.filter((q) => q[0] !== 't')
  }
  if (p.variant === 'rosette' || p.variant === 'medal') {
    parts = recolour(parts, p.ribbon)
    small = recolour(small, p.ribbon)
  }
  return { ...base, parts, small }
}

function ringDef(p: SealParams): { def: ArtDef; centre: { x: number; y: number } } {
  const tone = p.tone ?? 'sky'
  const outer = scalloped(32, 32, 27.2, 30.4, 20, 0.12)
  const bandOut = 'O 32 32 24.2 24.4'
  const bandIn = 'O 32 32 16.4 16.6'
  const parts = (small: boolean): Part[] => {
    const out: Part[] = [['f', tone, outer], ['s', outer, small ? 1.15 : 1.05], ['c', 'photo', bandOut, 0.5], ['s', bandOut, 0.5], ['f', 'paper', 'O 32 32 15.8', 0.4], ['s', bandIn, small ? 0.8 : 0.6]]
    const text = (p.text ?? '').toUpperCase()
    const cy = 32
    if (p.mark === 'check') out.push(['s', checkPath(32, cy, 13), small ? 1.7 : 1.5, { start: 'pool', end: 'flick' }])
    else if (p.mark === 'star') out.push(['f', 'lemon', starPath(32, cy, 8)], ['s', starPath(32, cy, 8.3), 0.8])
    else if (text) {
      const em = clamp(28 / (text.length * 0.6), 5, small ? 11 : 12)
      out.push(['t', text, 32, r1(cy + 0.745 * em * 0.5), r1(em), p.textColor ?? 'ink', 'hand'])
    }
    return out
  }
  return { def: { grid: 64, nibK: 0.05, parts: parts(false), small: parts(true), kind: 'sticker' }, centre: { x: 32, y: 32 } }
}

function ringLetters(ink: Ink, text: string, size: number, k: number, colour: PaintKey): void {
  const src = Array.from(text.toUpperCase().trim())
  if (!src.length) return
  const unit = [...src, ' ', '•', ' ']
  const per = unit.length
  const repeats = Math.max(1, Math.round(22 / per))
  const seq: string[] = []
  for (let i = 0; i < repeats; i++) seq.push(...unit)
  const rng = ink.rng.fork('ring')
  const em = 4.3 * k
  const cap = 0.68 * em
  const mid = 20.3 * k
  const c = size / 2
  seq.forEach((ch, i) => {
    if (ch === ' ') return
    const ang = -90 + ((i + 0.5) / seq.length) * 360
    const A = (ang * Math.PI) / 180
    const rr = mid - cap / 2
    const t = textPath(ch, c + Math.cos(A) * rr, c + Math.sin(A) * rr, em, rng.fork(`c${i}`), { font: 'type', rot: ang + 90, jitter: 0.12 })
    ink.flat('text', t.d, colour, 1, { bbox: t.bbox })
  })
}

function waxOutline(cx: number, cy: number, R: number, rng: { range(a: number, b: number): number }): Pt[] {
  const p1 = rng.range(0, PI2), p2 = rng.range(0, PI2), p3 = rng.range(0, PI2)
  const tab = rng.range(0.9, 1.5)
  const pts: Pt[] = []
  const N = 44
  for (let i = 0; i < N; i++) {
    const a = (i / N) * PI2
    const dA = Math.atan2(Math.sin(a - tab), Math.cos(a - tab))
    const drip = 0.16 * Math.exp(-(dA * dA) / 0.05)
    const r = R * (1 + 0.05 * Math.sin(3 * a + p1) + 0.03 * Math.sin(7 * a + p2) + 0.018 * Math.sin(11 * a + p3) + drip)
    pts.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r])
  }
  return pts
}

function waxSeal(ink: Ink, size: number, p: SealParams): void {
  const rng = ink.next('wax')
  const c = size / 2
  const R = size * 0.4
  const tone = p.tone ?? 'red'
  const outline = waxOutline(c, c, R, rng)
  const d = smoothClosed(outline, TIERS[ink.tier])
  const bbox: [number, number, number, number] = [c - R * 1.2, c - R * 1.2, c + R * 1.2, c + R * 1.2]
  ink.flat('under', d, tone, 1, { bbox })
  ink.flat('under', d, 'ink', 0.1, { bbox })
  const inner = (rr: number, dx = 0, dy = 0): Pt[] => Array.from({ length: 40 }, (_, i) => [c + dx + Math.cos((i / 40) * PI2) * rr * (1 + 0.012 * Math.sin(i * 1.7)), c + dy + Math.sin((i / 40) * PI2) * rr * (1 + 0.012 * Math.cos(i * 1.3))] as Pt)
  ink.poly('under', inner(R * 0.93, -R * 0.04, -R * 0.05), tone, 1)
  ink.poly('under', inner(R * 0.93, -R * 0.04, -R * 0.05), 'photo', 0.12)
  ink.poly('marker', inner(R * 0.5, -R * 0.32, -R * 0.36), 'photo', 0.3)
  const rIn = R * 0.62
  ink.poly('under', inner(rIn), 'ink', 0.22)
  ink.poly('under', inner(rIn * 0.96, R * 0.012, R * 0.012), tone, 1)
  ink.stroke(inner(rIn).concat([inner(rIn)[0]]), 'ink.fine', { poly: true, alpha: 0.55, width: 0.9 })
  ink.stroke(inner(rIn * 1.02, -R * 0.02, -R * 0.02).slice(28).concat(inner(rIn * 1.02, -R * 0.02, -R * 0.02).slice(0, 8)), 'ink.fine', { poly: true, color: 'photo', alpha: 0.55, width: 0.9 })
  const word = (p.text ?? '').toUpperCase().slice(0, 2)
  if (p.mark === 'check') {
    const pts: Pt[] = [[c - R * 0.3, c + R * 0.02], [c - R * 0.07, c + R * 0.24], [c + R * 0.34, c - R * 0.26]]
    ink.stroke(pts.map(([x, y]) => [x + 0.9, y + 0.9] as Pt), 'ink.brush', { poly: true, alpha: 0.6, width: 1.15, start: 'soft', end: 'flick' })
    ink.stroke(pts, 'ink.brush', { poly: true, color: 'photo', alpha: 0.6, width: 1.05, start: 'soft', end: 'flick' })
  } else if (word) {
    const em = R * (word.length > 1 ? 0.62 : 0.9)
    const base = c + 0.745 * em * 0.5
    const t = textPath(word, c + 0.9, base + 0.9, em, rng.fork('t'), { font: 'hand', jitter: 0.5 })
    const t2 = textPath(word, c, base, em, rng.fork('t'), { font: 'hand', jitter: 0.5 })
    ink.flat('text', t.d, 'ink', 0.6, { bbox: t.bbox })
    ink.flat('text', t2.d, 'photo', 0.55, { bbox: t2.bbox })
  } else {
    const s = starPath(c, c, R * 0.34)
    ink.flat('text', s, 'ink', 0.45)
    ink.flat('text', s, 'photo', 0.4)
  }
  ink.stroke(outline.concat([outline[0]]), 'ink.fine', { poly: true, alpha: 0.8, width: 0.95 })
  ink.stroke([[c - R * 0.72, c - R * 0.42], [c - R * 0.55, c - R * 0.66], [c - R * 0.3, c - R * 0.82]], 'ink.fine', { poly: true, color: 'photo', alpha: 0.85, width: 1.2 })
}

export function sealArt(p: SealParams, size: number, seed: string, tier: Tier = 'lo'): InkResult {
  const px = Math.max(16, Math.round(size))
  const ink = new Ink(`seal:${seed}:${p.variant}`, { tier })
  if (p.variant === 'wax') {
    waxSeal(ink, px, p)
    return ink.toSvg({ w: px, h: px, pad: Math.ceil(px * 0.12) })
  }
  if (p.variant === 'ring') {
    const { def } = ringDef(p)
    const r = paintSkeleton(ink, def, px, { kind: 'sticker', tone: 'doodle' })
    if (p.ring && px >= 72) ringLetters(ink, p.ring, px, px / 64, 'ink')
    return ink.toSvg({ w: r.w, h: r.h, pad: Math.ceil(px * 0.06) })
  }
  const r = paintSkeleton(ink, badgeDef(p, px), px, { kind: 'sticker', tone: 'doodle' })
  return ink.toSvg({ w: r.w, h: r.h, pad: Math.ceil(px * 0.06) })
}

