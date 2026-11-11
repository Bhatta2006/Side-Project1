import { wash } from '@/lib/ink/fills'
import { roundRectPoly } from '@/lib/ink/geom'
import { clamp } from '@/lib/ink/rng'
import { box } from '@/lib/ink/shapes'
import { defineRecipe } from '@/lib/ink/recipes'

export const fieldChoiceRecipe = defineRecipe<Record<string, never>>({
  id: 'field-choice',
  kind: 'card',
  layers: ['rest', 'hover', 'checked'],
  pad: 12,
  draw(ink, { w, h }, _p, ctx) {
    const r = clamp(Math.min(w, h) * 0.06, 2, 4)
    const body = roundRectPoly(1.5, 1.5, w - 3, h - 3, r)
    const wide = w > 360
    ink.layer('rest', () => {
      ink.poly('under', body, 'slip', 0.7)
      if (ctx.calm) box(ink, 0, 0, w, h, { pen: 'pencil.fine', corner: r })
      else box(ink, 0, 0, w, h, { pen: 'pencil', corner: r, opts: { width: 1.1, simple: wide } })
    })
    ink.layer('hover', () => {
      box(ink, 0.8, 0.8, w - 1.6, h - 1.6, { pen: ctx.calm ? 'pencil.fine' : 'ink.fine', corner: r, loose: 0.7, opts: { alpha: 0.75, simple: wide } })
    })
    ink.layer('checked', () => {
      ink.part('fill', () => wash(ink, body, 'hi', { alpha: 0.5 }))
      box(ink, 0, 0, w, h, { pen: ctx.calm ? 'pencil.fine' : 'ink', corner: r, opts: { width: 1.05, simple: wide } })
    })
  },
})
