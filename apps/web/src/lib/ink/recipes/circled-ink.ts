import { defineRecipe } from '@/lib/ink/recipes'
import { markRevealId, revealMark } from '@/lib/ink/recipes/mark-reveal-ink'
import { markPen, type LineParams, type MarkPen, type MarkWeight } from '@/lib/ink/recipes/text-marks-ink'
import { boxLines, bracketLines, loopLines } from '@/lib/ink/shapes'
import type { Line } from '@/lib/ink/types'

export type CircledShape = 'circle' | 'box' | 'brackets'

export interface CircledParams extends LineParams {
  shape: CircledShape
  tone: MarkPen
  weight: MarkWeight
  bleed?: number
}

export const BLEED_DEFAULT = 2
export const BLEED_MAX = 16
export const ONE_LINE_POWER = 2.5

export const bleedOf = (p: Pick<CircledParams, 'bleed'>): number => {
  const b = p.bleed
  return typeof b === 'number' && Number.isFinite(b) ? Math.round(Math.min(BLEED_MAX, Math.max(0, b)) * 2) / 2 : BLEED_DEFAULT
}

export function circledReach(w: number, h: number, p: Pick<LineParams, 'fs'> & Pick<CircledParams, 'bleed'>): number {
  return Math.ceil(Math.max(14, w * 0.15 + p.fs * 0.7, h * 0.4 + p.fs * 0.5)) + Math.max(0, bleedOf(p) - BLEED_DEFAULT)
}

export function loopRadii(tw: number, th: number, p: Pick<LineParams, 'fs' | 'ch'> & Pick<CircledParams, 'bleed'>, h: number): [number, number] {
  const b = bleedOf(p)
  if (h > p.ch * 1.5) return [tw * 1.08 + p.fs * 0.34 + (b - BLEED_DEFAULT), th * 1.32 + p.fs * 0.34 + (b - BLEED_DEFAULT)]
  return [tw * 1.06 + p.fs * 0.17 + b, th * 1.18 + p.fs * 0.08 + b]
}

export function squareUp(lines: Line[], cx: number, cy: number, rx: number, ry: number, n: number): Line[] {
  return lines.map((l) => ({
    ...l,
    pts: l.pts.map(([x, y]) => {
      const u = (x - cx) / rx, v = (y - cy) / ry
      const r = Math.hypot(u, v)
      if (r < 1e-6) return [x, y] as [number, number]
      const k = (Math.abs(u / r) ** n + Math.abs(v / r) ** n) ** (-1 / n)
      return [cx + u * k * rx, cy + v * k * ry] as [number, number]
    }),
  }))
}

export const circledRecipe = defineRecipe<CircledParams>({
  id: 'circled',
  kind: 'circled',
  layers: ['rest'],
  pad: (b, p) => circledReach(b.w, b.h, p),
  draw(ink, { w, h }, p, ctx) {
    const { pen, width } = markPen(p.tone, p.weight, p.fs)
    const top = p.base - p.cap
    const bot = h - (p.ch - p.base - p.desc)
    const cx = w / 2, cy = (top + bot) / 2
    const tw = w / 2, th = (bot - top) / 2
    const rng = ink.next('circled')
    let lines: Line[]
    if (p.shape === 'box') {
      const b = bleedOf(p)
      const px = p.fs * 0.32 + b, py = p.fs * 0.22 + b * 0.75
      lines = boxLines(rng, -px, top - py, w + 2 * px, bot - top + 2 * py, { corner: 3 })
    } else if (p.shape === 'brackets') {
      const off = p.fs * 0.3 + bleedOf(p) - BLEED_DEFAULT
      const hh = bot - top + p.fs * 0.5 + (bleedOf(p) - BLEED_DEFAULT)
      const y = top - p.fs * 0.25 - (bleedOf(p) - BLEED_DEFAULT) / 2
      lines = [...bracketLines(rng, -off, y, hh, { kind: 'square', dir: 1 }), ...bracketLines(rng.fork('r'), w + off, y, hh, { kind: 'square', dir: -1 })]
    } else {
      const [rx, ry] = loopRadii(tw, th, p, h)
      if (h <= p.ch * 1.5) {
        lines = squareUp(loopLines(rng, cx, cy, rx, ry, { drift: rng.fork('d').range(0.01, 0.05) }), cx, cy, rx, ry, ONE_LINE_POWER)
      } else lines = loopLines(rng, cx, cy, rx, ry)
    }
    ink.layer('rest', () => {
      if (p.animate) {
        revealMark(ink, { id: markRevealId(ctx.seed, 'c'), lines, pen, box: { w, h }, pad: circledReach(w, h, p) + 6, width, revealWidth: 5 + p.fs * 0.15 })
      } else ink.lines(lines, pen, { width })
    })
  },
})
