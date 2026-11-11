import { wash } from '@/lib/ink/fills'
import { roundRectPoly } from '@/lib/ink/geom'
import { clamp } from '@/lib/ink/rng'
import { box } from '@/lib/ink/shapes'
import { defineRecipe } from '@/lib/ink/recipes'

export const buttonGroupTextRecipe = defineRecipe<Record<string, never>>({
  id: 'button-group-text',
  kind: 'cell',
  layers: ['rest'],
  pad: 12,
  draw(ink, { w, h }, _p, ctx) {
    const r = clamp(h * 0.09, 2.5, 4.4)
    const inset = clamp(h * 0.06, 1.6, 3)
    ink.layer('rest', () => {
      wash(ink, roundRectPoly(inset, inset, w - 2 * inset, h - 2 * inset, r), 'paper-shade', { alpha: 0.95, material: 'wash' })
      if (ctx.calm) box(ink, 0, 0, w, h, { pen: 'pencil.fine', corner: r, opts: { simple: w > 360 || undefined } })
      else box(ink, 0, 0, w, h, { pen: 'ink', corner: r, opts: w > 360 ? { simple: true } : undefined })
    })
  },
})
