import { wash } from '@/lib/ink/fills'
import { roundRectPoly } from '@/lib/ink/geom'
import { clamp } from '@/lib/ink/rng'
import { box, dashedBox, focusRing, line, squiggle } from '@/lib/ink/shapes'
import { defineRecipe } from '@/lib/ink/recipes'

export const inputGroupRecipe = defineRecipe<Record<string, never>>({
  id: 'input-group',
  kind: 'field',
  layers: ['rest', 'invalid', 'disabled', 'hover', 'focus'],
  lazy: ['focus', 'hover'],
  pad: 12,
  draw(ink, { w, h }, _p, ctx) {
    const r = clamp(Math.min(w, h) * 0.08, 2, 4)
    const body = roundRectPoly(1.5, 1.5, w - 3, h - 3, r)
    const rtl = ctx.dir === 'rtl'
    ctx.lazy('focus', (f) => focusRing(f, 0, 0, w, h, { r }))
    ctx.lazy('hover', (hv) => box(hv, 0.6, 0.6, w - 1.2, h - 1.2, { pen: 'ink.fine', corner: r, loose: 0.7, opts: { alpha: 0.75, simple: w > 360 } }))
    if (ctx.lazyOnly) return

    ink.layer('rest', () => {
      ink.poly('under', body, 'slip', 0.7)
      ink.group({ hideOn: 'invalid disabled' }, () => {
        if (ctx.calm) box(ink, 0, 0, w, h, { pen: 'pencil.fine', corner: r })
        else box(ink, 0, 0, w, h, { pen: 'pencil', corner: r, opts: { width: 1.15, simple: w > 360 } })
      })
    })
    ink.layer('invalid', () => {
      box(ink, 0, 0, w, h, { pen: ctx.calm ? 'red.fine' : 'red', corner: r, opts: { width: ctx.calm ? 1.1 : 1.25, simple: w > 360 } })
      const len = clamp(w - 40, 24, 110)
      if (!ctx.calm) squiggle(ink, rtl ? w - 6 - len : 6, h + 5, len, { pen: 'redfelt.fine', h: 7, amp: 0.8 })
    })
    ink.layer('disabled', () => {
      wash(ink, body, 'paper-shade', { alpha: 0.9, material: 'wash' })
      dashedBox(ink, 0, 0, w, h, { r, pen: 'pencil', opts: { color: 'pencil-mark' } })
    })
  },
})

export const inputGroupRuleRecipe = defineRecipe<{ edge: 'top' | 'bottom' }>({
  id: 'input-group-rule',
  kind: 'rule',
  layers: ['rest'],
  pad: 6,
  draw(ink, { w, h }, { edge }, ctx) {
    const y = edge === 'bottom' ? h - 1 : 1
    ink.layer('rest', () => {
      if (ctx.calm) line(ink, 1, y, w - 1, y, { pen: 'pencil.fine', opts: { alpha: 0.7, wobble: 0.2 } })
      else line(ink, 1, y, w - 1, y, { pen: 'pencil', opts: { width: 1.15, simple: w > 360 } })
    })
  },
})
