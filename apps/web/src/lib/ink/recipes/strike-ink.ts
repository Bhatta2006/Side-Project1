import { seg } from '@/lib/ink/geom'
import { defineRecipe } from '@/lib/ink/recipes'
import { markPen, overshoot, type LineParams, type MarkPen, type MarkWeight } from '@/lib/ink/recipes/text-marks-ink'
import { strike } from '@/lib/ink/shapes'
import type { Line } from '@/lib/ink/types'

export type StrikeKind = 'single' | 'double' | 'cross'

export interface StrikeParams extends LineParams {
  kind: StrikeKind
  tone: MarkPen
  weight: MarkWeight
}

export const strikeRecipe = defineRecipe<StrikeParams>({
  id: 'strike',
  kind: 'strike',
  layers: ['rest'],
  pad: 12,
  draw(ink, { w, h }, p) {
    const o = overshoot(p.fs)
    const { pen, width } = markPen(p.tone, p.weight, p.fs, { pencil: true })
    ink.layer('rest', () => {
      if (p.kind === 'cross') {
        const rng = ink.next('cross')
        const top = p.base - p.cap - 1
        const bot = h - (p.ch - p.base - p.desc) + 1
        const l = -o * 0.8, r = w + o * 0.8
        const j = () => rng.gauss(0, 0.9)
        const n = Math.max(6, Math.ceil(w / 14))
        const lines: Line[] = [
          { pts: seg(l + j(), top + j(), r + j(), bot + j(), rng.gauss(0, 1.2), n), o: { end: 'flick', wobble: 0.5, speed: 1.2 } },
          { pts: seg(r + j() - 2, top + j(), l + j() + 3, bot + j(), rng.gauss(0, 1.2), n), o: { end: 'flick', start: 'soft', wobble: 0.5, speed: 1.2 } },
        ]
        ink.lines(lines, pen, { width })
        return
      }
      strike(ink, -o * 0.4, p.base - p.xh * 0.55, w + o * 0.9, { pen, double: p.kind === 'double', opts: { width } })
    })
  },
})
