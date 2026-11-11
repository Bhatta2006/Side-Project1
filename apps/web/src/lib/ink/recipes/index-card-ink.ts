import { defineRecipe } from '@/lib/ink/recipes'
import { holePunch, mirrorX, num, pathTag, stackSvg, tok } from '@/lib/ink/recipes/paper-set-ink'
import type { Accent } from '@/lib/ink/paper/props'

export interface IndexCardParams {
  hole: boolean
  flag: Accent | 'none'
  stack: number
}

export const INDEX_CARD = { holeFromFoot: 19, holeR: 6.2, flagAt: 58, flagH: 42, flagOut: 15, flagOver: 9 } as const

export const indexCardRecipe = defineRecipe<IndexCardParams>({
  id: 'index-card-decor',
  kind: 'index-card',
  layers: ['rest'],
  pad: 26,
  draw(ink, { w, h }, { hole, flag, stack }, ctx) {
    const id = `ll-ic${ink.seed.toString(36)}`
    ink.layer('rest', () => {
      const r = ink.next('card')
      let s = stackSvg(w, h, stack, r, id, ['card', 'slip'])
      let inner = ''
      if (hole) inner += holePunch(`${id}h`, w / 2 + r.gauss(0, 0.6), h - INDEX_CARD.holeFromFoot + r.gauss(0, 0.5), INDEX_CARD.holeR, r.range(-20, 20))
      if (flag !== 'none') {
        const { flagAt: y, flagH: fh, flagOut: out, flagOver: over } = INDEX_CARD
        const x0 = w - over
        const x1 = w + out
        const body = `M${num(x0)} ${num(y)}H${num(x1 - 3)}L${num(x1)} ${num(y + fh / 2)}L${num(x1 - 3)} ${num(y + fh)}H${num(x0)}z`
        inner += pathTag(body, { fill: tok('ink'), op: 0.18, transform: 'translate(.8 2)' })
        inner += pathTag(body, { fill: tok(flag), op: 0.92 })
        inner += pathTag(`M${num(x0)} ${num(y)}H${num(w)}V${num(y + fh)}H${num(x0)}z`, { fill: tok('photo'), op: 0.18 })
        inner += pathTag(`M${num(w)} ${num(y)}V${num(y + fh)}`, { stroke: tok('ink'), sw: 0.6, op: 0.28 })
        inner += pathTag(`M${num(x0 + 1)} ${num(y + 1)}H${num(x1 - 3)}`, { stroke: tok('photo'), sw: 0.9, op: 0.75 })
        inner += pathTag(body, { stroke: tok('ink'), sw: 0.6, op: 0.28 })
      }
      s += ctx.dir === 'rtl' ? mirrorX(w, inner) : inner
      ink.raw(s, 'top')
      ink.grow([-26, -26, w + 26, h + 26])
    })
  },
})
