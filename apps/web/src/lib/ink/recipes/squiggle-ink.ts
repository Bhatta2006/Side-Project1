import { defineRecipe } from '@/lib/ink/recipes'
import { markRevealId, revealMark } from '@/lib/ink/recipes/mark-reveal-ink'
import { markPen, STRUCTURAL_DRY, type MarkPen, type MarkWeight } from '@/lib/ink/recipes/text-marks-ink'
import { squiggleLines } from '@/lib/ink/shapes'
import type { Line, Pt } from '@/lib/ink/types'

export type SquiggleKind = 'wavy' | 'zigzag' | 'loops' | 'scallops' | 'dashes' | 'dots'

export interface SquiggleParams {
  kind: SquiggleKind
  orientation: 'horizontal' | 'vertical'
  tone: MarkPen
  weight: MarkWeight
  animate?: boolean
}

export const SQUIGGLE_KINDS: readonly SquiggleKind[] = ['wavy', 'zigzag', 'loops', 'scallops', 'dashes', 'dots']

export const squiggleRecipe = defineRecipe<SquiggleParams>({
  id: 'squiggle',
  kind: 'squiggle',
  layers: ['rest'],
  pad: 8,
  draw(ink, { w, h }, p, ctx) {
    const vertical = p.orientation === 'vertical'
    const L = vertical ? h : w
    const T = vertical ? w : h
    const { pen, width } = markPen(p.tone, p.weight, 18)
    const rng = ink.next('squiggle')
    const y = T / 2
    const amp = Math.max(1.6, Math.min(T * 0.32, 5))
    const x0 = 2, x1 = L - 2
    const lines: Line[] = []
    const so = { end: 'flick' as const, wobble: 0.5, speed: 1.15, simple: L > 220 }
    const pull = (pts: Pt[], o = so) => lines.push({ pts, o })
    if (p.kind === 'wavy') {
      lines.push(...squiggleLines(rng, x0, y, x1 - x0, { h: Math.max(8, T), amp: amp / 3 }).map((l) => ({ ...l, o: { ...l.o, simple: L > 220 } })))
    } else if (p.kind === 'zigzag') {
      const pitch = Math.max(9, amp * 3.4)
      const pts: Pt[] = []
      let x = x0, up = rng.chance(0.5)
      while (x <= x1) {
        pts.push([x, y + (up ? -amp : amp) * rng.range(0.75, 1.1)])
        x += pitch * rng.range(0.85, 1.15)
        up = !up
      }
      pull(pts, { ...so, poly: true, round: 0.7 } as typeof so)
    } else if (p.kind === 'loops') {
      const pitch = Math.max(12, amp * 4.2), r = pitch * 0.42
      const pts: Pt[] = []
      const n = Math.max(6, Math.round((x1 - x0) / pitch))
      for (let i = 0; i <= n * 14; i++) {
        const s = i / 14
        const th = s * Math.PI * 2
        pts.push([x0 + ((x1 - x0) / n) * s - r * Math.sin(th) * 0.9 + rng.gauss(0, 0.05), y - r * 0.55 * Math.cos(th) * (1 + 0.05 * Math.sin(s * 2.3))])
      }
      pull(pts)
    } else if (p.kind === 'scallops') {
      const pitch = Math.max(16, amp * 5.2)
      const n = Math.max(3, Math.round((x1 - x0) / pitch))
      const pts: Pt[] = []
      for (let i = 0; i < n; i++) {
        const a = x0 + ((x1 - x0) / n) * i, b = x0 + ((x1 - x0) / n) * (i + 1)
        for (let k = i ? 1 : 0; k <= 8; k++) {
          const t = k / 8
          pts.push([a + (b - a) * t + rng.gauss(0, 0.15), y + amp * 1.0 - Math.sin(Math.PI * t) * amp * 2.1 * rng.range(0.92, 1.06)])
        }
      }
      pull(pts)
    } else if (p.kind === 'dashes') {
      let x = x0 + rng.range(0, 4)
      while (x < x1 - 4) {
        const len = rng.range(6, 11)
        lines.push({ pts: [[x, y + rng.gauss(0, 0.5)], [Math.min(x1, x + len), y + rng.gauss(0, 0.6)]], o: { start: 'soft', end: 'soft', wobble: 0.4, simple: true } })
        x += len + rng.range(5, 9)
      }
    } else {
      let x = x0 + 3
      while (x < x1) {
        const r = rng.range(0.9, 1.5) * (p.weight === 'brush' ? 1.5 : 1)
        lines.push({ pts: [[x, y + rng.gauss(0, 0.5)], [x + r * 0.6, y + rng.gauss(0, 0.5) + 0.4]], o: { start: 'pool', end: 'pool', wobble: 0.2, simple: true, width: 1.7 } })
        x += rng.range(9, 13)
      }
    }
    ink.layer('rest', () => {
      const draw = () => {
        if (p.animate) revealMark(ink, { id: markRevealId(ctx.seed, 's'), lines, pen, box: { w: L, h: T }, pad: 10, width, opts: { dry: STRUCTURAL_DRY }, revealWidth: Math.max(6, T * 0.8) })
        else ink.lines(lines, pen, { width, dry: STRUCTURAL_DRY })
      }
      if (vertical) ink.group({ transform: `translate(${w} 0) rotate(90)` }, draw)
      else draw()
    })
  },
})
