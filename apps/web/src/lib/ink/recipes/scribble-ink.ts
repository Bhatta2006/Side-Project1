import { defineRecipe } from '@/lib/ink/recipes'
import { markPen, overshoot, type LineParams, type MarkPen, type MarkWeight } from '@/lib/ink/recipes/text-marks-ink'
import type { Line, Pt } from '@/lib/ink/types'

export interface ScribbleParams extends LineParams {
  tone: MarkPen
  weight: MarkWeight
}

export const scribbleRecipe = defineRecipe<ScribbleParams>({
  id: 'scribble',
  kind: 'scribble',
  layers: ['rest'],
  pad: 10,
  draw(ink, { w }, p, ctx) {
    const o = overshoot(p.fs)
    const rng = ink.next('redact')
    const top = p.base - p.cap - p.fs * 0.06
    const bot = p.base + p.desc * 0.7
    const { pen, width } = markPen(p.tone, p.weight === 'regular' ? 'brush' : p.weight, p.fs)
    const x0 = -o * 0.7, x1 = w + o * 0.8
    const pitch = Math.max(2.6, p.fs * 0.2)
    ink.layer('rest', () => {
      const lines: Line[] = []
      let pts: Pt[] = []
      let x = x0
      let up = true
      let len = 0
      const lean = rng.gauss(0.22, 0.05) * (bot - top)
      while (x < x1) {
        const t = up ? top + rng.range(0, 0.18) * (bot - top) : bot - rng.range(0, 0.18) * (bot - top)
        pts.push([Math.min(x1, x + (up ? -lean / 2 : lean / 2)), t])
        x += pitch * rng.range(0.7, 1.35)
        up = !up
        len += pitch
        if (len > 160 && pts.length > 3) {
          lines.push({ pts, o: { end: 'flick', speed: 1.5, wobble: 0.5, poly: true, round: 1.4 } })
          pts = [pts[pts.length - 1]]
          len = 0
        }
      }
      if (pts.length > 1) lines.push({ pts, o: { end: 'flick', speed: 1.5, wobble: 0.5, poly: true, round: 1.4 } })
      ink.lines(lines, pen, { width: 0.7 * width })
      if (!ctx.calm) {
        const back: Pt[] = []
        const n = Math.max(4, Math.round((x1 - x0) / (pitch * 3.1)))
        for (let i = 0; i <= n; i++) back.push([x0 + ((x1 - x0) * i) / n + rng.gauss(0, 1), i % 2 ? top + 1 : bot - 1])
        ink.lines([{ pts: back, o: { end: 'flick', speed: 1.4, wobble: 0.6, poly: true, round: 1.2 } }], pen, { width: 0.6 * width })
      }
    })
  },
})
