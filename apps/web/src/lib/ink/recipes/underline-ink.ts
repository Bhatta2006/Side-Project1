import { underline } from '@/lib/ink/shapes'
import { defineRecipe } from '@/lib/ink/recipes'
import { markPen, overshoot, type LineParams, type MarkPen, type MarkWeight } from '@/lib/ink/recipes/text-marks-ink'
import type { Pt } from '@/lib/ink/types'

export type UnderlineKind = 'single' | 'double' | 'wavy' | 'scribble'

export interface UnderlineParams extends LineParams {
  kind: UnderlineKind
  tone: MarkPen
  weight: MarkWeight
}

export const underlineRecipe = defineRecipe<UnderlineParams>({
  id: 'underline',
  kind: 'underline',
  layers: ['rest'],
  pad: 10,
  draw(ink, { w }, p) {
    const o = overshoot(p.fs)
    const x0 = p.first ? -o * 0.5 : 0
    const x1 = p.last ? w + o : w
    const y = p.base + p.desc * 0.55 + p.fs * 0.1
    const { pen, width } = markPen(p.tone, p.weight, p.fs)
    ink.layer('rest', () => {
      if (p.kind === 'scribble') {
        const rng = ink.next('ul-scrib')
        const pts: Pt[] = []
        const swing = Math.max(2.2, p.fs * 0.16)
        let x = x0
        let up = rng.chance(0.5)
        while (x < x1) {
          pts.push([x, y + (up ? -1 : 1) * swing * rng.range(0.6, 1.1) - swing * 0.2 - ((x - x0) / (x1 - x0)) * 1.2])
          x += Math.max(3.4, p.fs * 0.27) * rng.range(0.75, 1.3)
          up = !up
        }
        ink.lines([{ pts, o: { poly: true, round: 1.6, end: 'flick', speed: 1.3, wobble: 0.6 } }], pen, { width: 0.85 * width })
        return
      }
      underline(ink, x0, y, x1 - x0, { kind: p.kind, pen, opts: { width } })
    })
  },
})
