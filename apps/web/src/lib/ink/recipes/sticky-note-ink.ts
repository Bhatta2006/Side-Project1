import { box } from '@/lib/ink/shapes'
import { checkLines } from '@/lib/ink/shapes'
import { defineRecipe } from '@/lib/ink/recipes'
import { reveal, revealId } from '@/lib/ink/recipes/draw-on-ink'
import { MIRROR } from '@/lib/ink/recipes/paper-set-ink'

export const STICKY_BOX = { size: 17, inset: 11, top: 10 } as const

export const stickyNoteRecipe = defineRecipe<Record<string, never>>({
  id: 'sticky-note-decor',
  kind: 'sticky',
  layers: ['rest', 'checked'],
  pad: 6,
  draw(ink, { w, h }, _p, ctx) {
    const s = STICKY_BOX.size
    const x = w - STICKY_BOX.inset - s
    const y = STICKY_BOX.top
    const mirror = ctx.dir === 'rtl'
    const inMirror = (fn: () => void) => (mirror ? ink.group({ transform: MIRROR(w) }, fn) : fn())
    ink.layer('rest', () => inMirror(() => box(ink, x, y, s, s, { pen: 'ink.fine', corner: 2.5, opts: { alpha: 0.6 } })))
    ink.layer('checked', () =>
      inMirror(() => reveal(ink, { id: revealId(ctx.seed, 't'), lines: checkLines(ink.next('tick'), x + 2, y, s + 1), pen: 'greenfelt', box: { w, h }, revealWidth: 7, width: 1.15 })),
    )
  },
})
