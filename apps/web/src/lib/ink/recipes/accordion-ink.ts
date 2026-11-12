import { highlight } from '@/lib/ink/fills'
import { defineRecipe } from '@/lib/ink/recipes'
import { focusRing, line } from '@/lib/ink/shapes'

export const accordionRuleRecipe = defineRecipe<Record<string, never>>({
  id: 'accordion-rule',
  kind: 'rule',
  layers: ['rest'],
  pad: 8,
  draw(ink, { w, h }, _p, ctx) {
    const y = h / 2
    const x0 = Math.min(6, w * 0.03)
    ink.layer('rest', () => {
      if (ctx.calm) line(ink, x0, y, w - x0, y, { pen: 'pencil.fine', opts: { alpha: 0.7, wobble: 0.2 } })
      else line(ink, x0, y, w - x0, y, { pen: 'pencil' })
    })
  },
})

export const accordionTriggerRecipe = defineRecipe<{ disabled?: boolean }>({
  id: 'accordion-trigger',
  kind: 'row',
  layers: ['hover', 'focus'],
  lazy: ['hover', 'focus'],
  pad: 12,
  draw(_ink, { w, h }, { disabled }, ctx) {
    if (disabled) return
    ctx.lazy('hover', (s) => {
      const inset = Math.min(4, w * 0.02)
      s.part('swipe', () => highlight(s, inset, h * 0.2, w - inset * 2 - 6, h * 0.6, { k: 1 }), 'hl')
    })
    ctx.lazy('focus', (f) => focusRing(f, 0, 0, w, h, { r: 4 }))
  },
})
