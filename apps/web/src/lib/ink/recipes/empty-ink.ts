import { edgeBand, wash } from '@/lib/ink/fills'
import { roundRectPoly, seg } from '@/lib/ink/geom'
import { defineRecipe } from '@/lib/ink/recipes'
import { box, dashedBox } from '@/lib/ink/shapes'
import type { Line } from '@/lib/ink/types'

export const emptyFrameRecipe = defineRecipe<Record<string, never>>({
  id: 'empty-frame',
  kind: 'frame',
  layers: ['rest'],
  pad: 8,
  draw(ink, { w, h }, _p, ctx) {
    ink.layer('rest', () => {
      const r = Math.min(12, Math.min(w, h) / 4)
      dashedBox(ink, 1, 1, w - 2, h - 2, { r, pen: ctx.calm ? 'pencil.fine' : 'pencil', dash: 9, gap: 6.5 })
      if (ctx.calm) return
      const t = 7
      const ticks: Line[] = [
        { pts: seg(-2, r + 2, -2, r + 2 - t, 0, 2), o: { start: 'soft', end: 'flick', simple: true } },
        { pts: seg(r + 2, -2, r + 2 - t, -2, 0, 2), o: { start: 'soft', end: 'flick', simple: true } },
        { pts: seg(w + 2, h - r - 2, w + 2, h - r - 2 + t, 0, 2), o: { start: 'soft', end: 'flick', simple: true } },
        { pts: seg(w - r - 2, h + 2, w - r - 2 + t, h + 2, 0, 2), o: { start: 'soft', end: 'flick', simple: true } },
      ]
      ink.lines(ticks, 'pencil.fine', { alpha: 0.7 })
    })
  },
})

export const emptyMediaRecipe = defineRecipe<Record<string, never>>({
  id: 'empty-media',
  kind: 'tile',
  layers: ['rest'],
  pad: 8,
  draw(ink, { w, h }, _p, ctx) {
    const body = roundRectPoly(1.5, 1.5, w - 3, h - 3, 6)
    ink.layer('rest', () => {
      ink.poly('under', body, 'slip', 0.98)
      wash(ink, body, 'hi', { alpha: ctx.calm ? 0.25 : 0.35 })
      box(ink, 0, 0, w, h, { pen: ctx.calm ? 'pencil.fine' : 'ink.fine', corner: 6 })
      if (!ctx.calm) {
        edgeBand(ink, 0, 0, w, h, 'b', { thick: 4 })
        edgeBand(ink, 0, 0, w, h, 'r', { thick: 4 })
      }
    })
  },
})
