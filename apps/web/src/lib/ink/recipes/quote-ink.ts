import { pen as penSpec } from '@/lib/ink/pens'
import { defineRecipe } from '@/lib/ink/recipes'
import { markRevealId, revealMark } from '@/lib/ink/recipes/mark-reveal-ink'
import { markPen, type MarkPen, type MarkWeight } from '@/lib/ink/recipes/text-marks-ink'
import type { Rng } from '@/lib/ink/rng'
import type { Line, PenName, PenSpec, Pt } from '@/lib/ink/types'
import { RULER } from '@/lib/ink/shapes'

export interface QuoteParams {
  tone: MarkPen
  weight: MarkWeight
  size: number
  rule: boolean
  animate?: boolean
}

function mark(rng: Rng, x: number, y: number, s: number, opening: boolean): Line {
  const j = () => rng.gauss(0, s * 0.012)
  const lean = rng.gauss(0, 0.04)
  const bend = (t: number) => Math.sin(t * Math.PI) * s * 0.09
  const pts: Pt[] = []
  const n = 12
  for (let i = 0; i <= n; i++) {
    const t = i / n
    const px = opening ? 0.66 - 0.54 * t - lean * t : 0.62 - 0.4 * t - lean * t
    const py = opening ? 0.06 + 0.8 * t : 0.14 + 0.78 * t
    pts.push([x + s * px + (opening ? -bend(t) : bend(t) * 0.5) + j(), y + s * py + j()])
  }
  return { pts, o: opening ? { start: 'soft', end: 'pool', wobble: 0.4, speed: 0.8 } : { start: 'pool', end: 'flick', wobble: 0.4, speed: 0.9 } }
}

export const quoteRecipe = defineRecipe<QuoteParams>({
  id: 'quote',
  kind: 'quote',
  layers: ['rest'],
  pad: 14,
  draw(ink, { w, h }, p, ctx) {
    const s = p.size
    const c = s * 0.72
    const pen: PenName | PenSpec = p.tone === 'marker' ? penSpec('ink.brush', { color: 'marker', alpha: 0.88 }) : markPen(p.tone, 'brush', 18).pen
    const rng = ink.next('quote')
    const lines: Line[] = [
      mark(rng.fork('o1'), 2, 2, s, true),
      mark(rng.fork('o2'), 2 + s * 0.46, 2, s, true),
      mark(rng.fork('c1'), w - c * 1.05, h - c * 1.0, c, false),
      mark(rng.fork('c2'), w - c * 1.05 + c * 0.46, h - c * 1.0, c, false),
    ]
    if (ctx.dir === 'rtl') for (const l of lines) l.pts = l.pts.map(([x, y]): Pt => [w - x, y])
    const width = (s / 30) * 0.95 * (p.weight === 'fine' ? 0.7 : p.weight === 'brush' ? 1.25 : 1)
    ink.layer('rest', () => {
      if (p.animate) revealMark(ink, { id: markRevealId(ctx.seed, 'q'), lines, pen, box: { w, h }, pad: 20, width, revealWidth: s * 0.3 })
      else ink.lines(lines, pen, { width })
      if (p.rule) {
        const x = ctx.dir === 'rtl' ? w - 3 : 3
        ink.lines([{ pts: [[x, s + 10], [x, h - c - 4]], o: RULER }], 'pencil', { width: 1.1 })
      }
    })
  },
})
