import { bandFill, blobFill, wash } from '@/lib/ink/fills'
import { ellipsePoly, roundRectPoly } from '@/lib/ink/geom'
import { defineRecipe } from '@/lib/ink/recipes'
import { box, line, loop } from '@/lib/ink/shapes'
import type { PaintKey } from '@/lib/ink/paint'
import type { PenName } from '@/lib/ink/types'

export type AlertTone = 'default' | 'destructive' | 'info' | 'success' | 'warning' | 'note'

export interface AlertParams {
  tone: AlertTone
}

const PEN: Record<AlertTone, PenName> = { default: 'ink', destructive: 'redfelt', info: 'blue', success: 'greenfelt', warning: 'ink', note: 'ink' }
const HAIR: Record<AlertTone, PenName> = { default: 'pencil.fine', destructive: 'red.fine', info: 'bluepencil.fine', success: 'green.fine', warning: 'pencil.fine', note: 'pencil.fine' }

const MARK: Record<AlertTone, PaintKey> = { default: 'pencil-mark', destructive: 'red', info: 'sky', success: 'grass', warning: 'tangerine', note: 'pencil-mark' }

export const alertRecipe = defineRecipe<AlertParams>({
  id: 'alert',
  kind: 'alert',
  layers: ['rest'],
  pad: 12,
  draw(ink, { w, h }, { tone }, ctx) {
    if (tone === 'note') return
    const r = 3
    const body = roundRectPoly(1.5, 1.5, w - 3, h - 3, r)
    const calm = ctx.calm
    const rtl = ctx.dir === 'rtl'
    const X = (x: number): number => (rtl ? w - x : x)
    const wide = w > 360
    ink.layer('rest', () => {
      ink.poly('under', body, 'slip', 0.94)
      if (tone === 'warning') ink.part('fill', () => bandFill(ink, body, 'hi', { alpha: calm ? 0.4 : 0.6, passes: 1, ends: 'flag' }))
      if (calm) {
        if (tone !== 'default' && tone !== 'warning') line(ink, X(6.5), 4, X(6.5), h - 4, { pen: HAIR[tone], opts: { alpha: 0.9 } })
      } else if (tone === 'destructive') {
        wash(ink, body, 'red', { alpha: 0.04 })
        ink.part('fill', () => bandFill(ink, roundRectPoly(rtl ? w - 11 : 3, 3.5, 8, h - 7, 2), 'red', { alpha: 0.9, passes: 1, ends: 'square', W: 5 }))
      } else if (tone === 'info') {
        line(ink, X(5.2), 5, X(5.6), h - 5, { pen: 'bluepencil' })
        line(ink, X(10), 5.5, X(10.4), h - 6, { pen: 'bluepencil', opts: { alpha: 0.75 } })
      } else if (tone === 'success') {
        ink.part('fill', () => bandFill(ink, roundRectPoly(rtl ? w - 11 : 3, 3.5, 8, h - 7, 2), 'grass', { alpha: 0.7, passes: 1, ends: 'square', W: 5 }))
      }
      if (!calm) {
        const px = 16
        const py = ctx.density === 'compact' ? 10 : 12
        const cx = X(px + 8), cy = py + 10
        ink.part('icon-mark', () => {
          const off = blobFill(ink, ellipsePoly(cx, cy, 11.5, 11.5, 20), MARK[tone], { alpha: tone === 'default' ? 0.3 : 0.32, mis: 1.6 })
          loop(ink, cx, cy, 12.5, 12.5, { pen: tone === 'default' ? 'pencil.fine' : HAIR[tone], turns: 1.08 })
          return off
        })
      }
      if (calm) box(ink, 0, 0, w, h, { pen: HAIR[tone], corner: r })
      else box(ink, 0, 0, w, h, { pen: PEN[tone], corner: r, opts: wide ? { simple: true } : undefined })
    })
  },
})
