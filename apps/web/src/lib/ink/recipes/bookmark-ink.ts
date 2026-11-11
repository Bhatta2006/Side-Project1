import { defineRecipe } from '@/lib/ink/recipes'
import { num, pathTag, tok } from '@/lib/ink/recipes/paper-set-ink'
import type { Accent } from '@/lib/ink/paper/props'
import { wash } from '@/lib/ink/fills'
import { densify } from '@/lib/ink/geom'
import type { Rng } from '@/lib/ink/rng'
import type { Pt } from '@/lib/ink/types'

export interface BookmarkParams {
  tone: Accent
  mode: 'toggle' | 'static'
  disabled: boolean
}

export const NOTCH = 0.55

export function ribbonPoly(w: number, h: number): Pt[] {
  const n = Math.min(h * 0.4, w * NOTCH)
  return [[0, 0], [w, 0], [w, h], [w / 2, h - n], [0, h]]
}

const ribbonD = (w: number, h: number, r: Rng) => {
  const p = densify([...ribbonPoly(w, h), ribbonPoly(w, h)[0]], 6).slice(0, -1)
  return `M${num(p[0][0])} ${num(p[0][1])}` + p.slice(1).map((q) => `L${num(q[0] + r.gauss(0, 0.22))} ${num(q[1] + r.gauss(0, 0.22))}`).join('') + 'z'
}

export const bookmarkRecipe = defineRecipe<BookmarkParams>({
  id: 'bookmark-ribbon',
  kind: 'bookmark',
  layers: ['rest', 'checked', 'disabled', 'hover'],
  pad: 6,
  draw(ink, { w, h }, { tone, mode, disabled }, ctx) {
    const d = ribbonD(w, h, ink.next('edge'))
    const ribbon = () => {
      const r = ink.next('cloth')
      const id = `ll-bm${ink.seed.toString(36)}`
      let s = `<clipPath id="${id}c"><path d="${d}"/></clipPath>`
      s += pathTag(d, { fill: tok(tone) })
      let g = ''
      for (let x = 2.2; x < w - 1; x += 2.3) g += `M${num(x + r.gauss(0, 0.08))} 0V${num(h)}`
      s += `<g clip-path="url(#${id}c)">`
      s += pathTag(g, { stroke: tok('ink'), sw: 0.7, op: 0.1 })
      s += pathTag(`M0 0H${num(w * 0.34)}V${num(h)}H0z`, { fill: tok('photo'), op: 0.22 })
      s += pathTag(`M${num(w * 0.7)} 0H${num(w)}V${num(h)}H${num(w * 0.7)}z`, { fill: tok('ink'), op: 0.13 })
      s += pathTag(`M0 ${num(h)}L${num(w / 2)} ${num(h - Math.min(h * 0.4, w * NOTCH))}L${num(w)} ${num(h)}V${num(h + 4)}H0z`, { fill: tok('ink'), op: 0.16 })
      s += `</g>`
      s += pathTag(`M2.6 1.5V${num(h - 3)}M${num(w - 2.6)} 1.5V${num(h - 3)}`, { stroke: tok('photo'), sw: 0.8, op: 0.6, extra: `stroke-dasharray="${num(r.range(2, 2.6))} ${num(r.range(1.5, 2.1))}"` })
      s += pathTag(d, { stroke: tok('ink'), sw: 0.7, op: 0.36 })
      return s
    }
    const ghost = (alpha: number) => {
      ink.raw(pathTag(d, { fill: tok('paper-shade'), op: alpha }) + pathTag(d, { stroke: tok('pencil'), sw: 1.1, op: 0.85, extra: 'stroke-dasharray="3.6 3.2"' }), 'under')
    }
    if (disabled) {
      ink.layer('disabled', () => ghost(0.3))
      return
    }
    if (mode === 'static') {
      ink.layer('rest', () => ink.raw(ribbon(), 'under'))
      return
    }
    ink.layer('rest', () => ghost(0.45))
    ink.layer('checked', () => ink.raw(ribbon(), 'under'))
    if (!ctx.calm) ink.layer('hover', () => wash(ink, ribbonPoly(w, h), tone, { alpha: 0.52, inset: 1.2 }))
  },
})
