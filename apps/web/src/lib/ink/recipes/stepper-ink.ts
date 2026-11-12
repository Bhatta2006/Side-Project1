import { wash } from '@/lib/ink/fills'
import { roundRectPoly } from '@/lib/ink/geom'
import { Ink } from '@/lib/ink/builder'
import { defineRecipe } from '@/lib/ink/recipes'
import { clamp } from '@/lib/ink/rng'
import { box, dashedBox, focusRing, squiggle, tallyLines, underline, RULER } from '@/lib/ink/shapes'

export interface StepperParams {
  disabled?: boolean
  invalid?: boolean
  plain?: boolean
}

function tick(ink: Ink, x: number, h: number, alpha: number, pen: 'pencil.fine' | 'red.fine' = 'pencil.fine'): void {
  ink.stroke([[x, 6], [x, h - 6]], pen, { ...RULER, alpha, simple: true })
}

export const stepperRecipe = defineRecipe<StepperParams>({
  id: 'stepper',
  kind: 'field',
  layers: ['rest', 'hover', 'focus', 'invalid', 'disabled'],
  lazy: ['focus', 'hover'],
  pad: 12,
  draw(ink, { w, h }, { disabled, invalid, plain }, ctx) {
    const r = clamp(Math.min(w, h) * 0.08, 2, 4)
    const body = roundRectPoly(1.5, 1.5, w - 3, h - 3, r)
    const roomy = !plain && w >= h * 2.4
    if (disabled) {
      if (ctx.lazyOnly) return
      ink.layer('disabled', () => {
        wash(ink, body, 'paper-shade', { alpha: 0.9, material: 'wash' })
        dashedBox(ink, 0, 0, w, h, { r, pen: 'pencil', opts: { color: 'pencil-mark' } })
        if (roomy) {
          tick(ink, h, h, 0.5)
          tick(ink, w - h, h, 0.5)
        }
      })
      return
    }
    ctx.lazy('focus', (f) => focusRing(f, 0, 0, w, h, { r }))
    ctx.lazy('hover', (hv) => box(hv, 0.6, 0.6, w - 1.2, h - 1.2, { pen: invalid ? 'red.fine' : 'ink.fine', corner: r, loose: 0.7, opts: { alpha: invalid ? 0.7 : 0.75 } }))
    if (ctx.lazyOnly) return
    if (invalid) {
      ink.layer('invalid', () => {
        ink.poly('under', body, 'slip', 0.7)
        box(ink, 0, 0, w, h, { pen: ctx.calm ? 'red.fine' : 'red', corner: r, opts: { width: ctx.calm ? 1.1 : 1.25 } })
        if (!ctx.calm) squiggle(ink, 6, h + 5, clamp(w - 40, 24, 90), { pen: 'redfelt.fine', h: 7, amp: 0.8 })
        if (roomy) {
          tick(ink, h, h, 0.7, 'red.fine')
          tick(ink, w - h, h, 0.7, 'red.fine')
        }
      })
      return
    }
    ink.layer('rest', () => {
      ink.poly('under', body, 'slip', 0.7)
      if (ctx.calm) box(ink, 0, 0, w, h, { pen: 'pencil.fine', corner: r })
      else box(ink, 0, 0, w, h, { pen: 'pencil', corner: r, opts: { width: 1.15 } })
      if (roomy) {
        tick(ink, h, h, 0.8)
        tick(ink, w - h, h, 0.8)
        if (!ctx.calm) {
          const len = clamp(w - 2 * h - 22, 16, 56)
          underline(ink, w / 2 - len / 2, h - 6.4, len, { pen: 'blue.fine', kind: 'single', opts: { alpha: 0.45, simple: true } })
        }
      }
    })
  },
})

export interface StepperTallyParams {
  count: number
}

export const TALLY_H = 16
export function tallyWidth(count: number, gh = TALLY_H): number {
  const groups = Math.ceil(Math.max(0, count) / 5)
  return Math.max(4, Math.round(groups * (1.05 * gh + 6) - 6 + 4))
}

export const stepperTallyRecipe = defineRecipe<StepperTallyParams>({
  id: 'stepper-tally',
  kind: 'tally',
  layers: ['rest'],
  pad: 6,
  draw(ink, { h }, { count }) {
    const gh = Math.min(TALLY_H, h - 2)
    const t = tallyLines(ink.next('tally'), 2, (h - gh) / 2, Math.max(0, Math.min(count, 60)), gh)
    ink.layer('rest', () => ink.lines(t.lines, 'ink.fine', { alpha: 0.9, simple: true }))
  },
})
