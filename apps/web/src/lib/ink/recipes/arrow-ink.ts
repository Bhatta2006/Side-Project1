import { defineRecipe } from '@/lib/ink/recipes'
import { markRevealId, revealMark } from '@/lib/ink/recipes/mark-reveal-ink'
import { markPen, STRUCTURAL_DRY, type MarkPen, type MarkWeight } from '@/lib/ink/recipes/text-marks-ink'
import { arrowLines } from '@/lib/ink/shapes'

export type ArrowDirection = 'right' | 'left' | 'up' | 'down' | 'up-right' | 'up-left' | 'down-right' | 'down-left'
export type ArrowCurve = 'straight' | 'curved' | 'curl'
export type ArrowHead = 'v' | 'two' | 'open' | 'solid' | 'none'

export interface ArrowParams {
  direction: ArrowDirection
  curve: ArrowCurve
  head: ArrowHead
  tone: MarkPen
  weight: MarkWeight
  bend: 'up' | 'down'
  mirror: boolean
  dx?: number
  dy?: number
  animate?: boolean
}

const FLIP: Record<ArrowDirection, ArrowDirection> = {
  right: 'left', left: 'right', up: 'up', down: 'down', 'up-right': 'up-left', 'up-left': 'up-right', 'down-right': 'down-left', 'down-left': 'down-right',
}

const UNIT: Record<ArrowDirection, [number, number]> = {
  right: [1, 0], left: [-1, 0], up: [0, -1], down: [0, 1], 'up-right': [1, -1], 'up-left': [-1, -1], 'down-right': [1, 1], 'down-left': [-1, 1],
}

export function arrowReach(p: Pick<ArrowParams, 'dx' | 'dy'>): number {
  return p.dx === undefined || p.dy === undefined ? 14 : Math.ceil(Math.hypot(p.dx, p.dy)) + 18
}

export const arrowRecipe = defineRecipe<ArrowParams>({
  id: 'arrow',
  kind: 'arrow',
  layers: ['rest'],
  pad: (_b, p) => arrowReach(p),
  draw(ink, { w, h }, p, ctx) {
    const brush = p.weight === 'brush'
    const mp = markPen(p.tone, brush ? 'regular' : p.weight, 18)
    const pen = mp.pen
    const width = brush ? mp.width * 1.3 : mp.width
    const aimed = p.dx !== undefined && p.dy !== undefined
    const dir = p.mirror && ctx.dir === 'rtl' ? FLIP[p.direction] : p.direction
    let x1: number, y1: number, x2: number, y2: number
    if (aimed) {
      x1 = w / 2
      y1 = h / 2
      x2 = x1 + (p.dx as number)
      y2 = y1 + (p.dy as number)
    } else {
      const m = Math.min(4, Math.min(w, h) * 0.12)
      const [ux, uy] = UNIT[dir]
      const cx = w / 2, cy = h / 2
      x1 = ux === 0 ? cx : ux > 0 ? m : w - m
      x2 = ux === 0 ? cx : ux > 0 ? w - m : m
      y1 = uy === 0 ? cy : uy > 0 ? m : h - m
      y2 = uy === 0 ? cy : uy < 0 ? m : h - m
      if (uy === 0) y1 += Math.min(3, h * 0.08)
    }
    const len = Math.hypot(x2 - x1, y2 - y1)
    const dx = x2 - x1, dy = y2 - y1
    const up = p.bend === 'up' ? -1 : 1
    const side = dx !== 0 ? Math.sign(dx) * up : -Math.sign(dy) * up
    const bow = p.curve === 'straight' ? undefined : side * (p.curve === 'curved' ? 0.2 : 0.06)
    const lines = arrowLines(ink.next('arrow'), x1, y1, x2, y2, { head: p.head, curl: p.curve === 'curl', curve: bow, headLen: Math.min(14, Math.max(7, len * 0.22)) })
    ink.layer('rest', () => {
      if (p.animate) revealMark(ink, { id: markRevealId(ctx.seed, 'a'), lines, pen, box: { w, h }, pad: arrowReach(p) + 6, width, opts: { dry: STRUCTURAL_DRY }, revealWidth: 5 })
      else ink.lines(lines, pen, { width, dry: STRUCTURAL_DRY })
    })
  },
})
