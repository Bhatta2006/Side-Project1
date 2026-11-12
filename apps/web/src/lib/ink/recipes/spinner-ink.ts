import { Ink } from '@/lib/ink/builder'
import type { InkResult } from '@/lib/ink/builder'
import { TAU } from '@/lib/ink/geom'
import { clamp } from '@/lib/ink/rng'
import { reveal, revealId } from '@/lib/ink/recipes/draw-on-ink'
import { spiralLines } from '@/lib/ink/shapes'
import type { Line, Pt, Tier } from '@/lib/ink/types'

export const spinnerVariantList = ['scribble', 'loops', 'write'] as const
export type SpinnerVariant = (typeof spinnerVariantList)[number]
export type SpinnerShape = 'spiral' | 'loops'

export interface SpinnerMarkOpts {
  shape?: SpinnerShape
  w?: number
  h?: number
  tier?: Tier
  calm?: boolean
}

function loopLines(rng: ReturnType<Ink['next']>, w: number, h: number, loops: number): Line[] {
  const R = h * 0.4
  const total = loops * TAU
  const k = Math.min(R * 0.75, (w - 2 * R) / total)
  const n = Math.max(30, loops * 16)
  const ph = rng.range(-0.3, 0.3)
  const pts: Pt[] = []
  for (let i = 0; i <= n; i++) {
    const th = (i / n) * total
    pts.push([R + k * th - R * 0.9 * Math.sin(th + ph), h / 2 - R * Math.cos(th + ph) * (1 + 0.04 * Math.sin(th * 0.7)) + rng.gauss(0, 0.06)])
  }
  return [{ pts, o: { start: 'soft', end: 'flick', wobble: 0.5, speed: 1 } }]
}

export function spinnerMark(seed: string, px: number, o: SpinnerMarkOpts = {}): InkResult {
  const shape = o.shape ?? 'spiral'
  const w = shape === 'spiral' ? px : (o.w ?? px)
  const h = shape === 'spiral' ? px : (o.h ?? px * 0.3)
  const ink = new Ink(seed, { tier: o.tier, calm: o.calm })
  const rng = ink.next('spinner')
  const id = revealId(`${seed}|spinner`, 'sp')
  const width = clamp(px / 20, 0.9, 1.45)
  const lines =
    shape === 'spiral'
      ? spiralLines(rng, w / 2, h / 2, w * 0.4, { turns: px < 20 ? 1.85 : px < 40 ? 2.1 : 2.6, steps: px < 20 ? 22 : 34, shrink: 0.86 })
      : loopLines(rng, w, h, Math.max(3, Math.round(w / (h * 1.5))))
  ink.layer('rest', () =>
    reveal(ink, {
      id,
      lines,
      pen: 'ink',
      box: { w, h },
      width,
      revealWidth: Math.max(3.4, Math.min(w, h) * 0.34),
    })
  )
  ink.grow([-1, -1, w + 1, h + 1])
  return recolour(ink.toSvg({ w, h, pad: 3 }))
}

function recolour(res: InkResult): InkResult {
  const swap = (s: string) => s.replaceAll('var(--ll-ink)', 'currentColor')
  return { ...res, svg: swap(res.svg), parts: Object.fromEntries(Object.entries(res.parts).map(([k, v]) => [k, swap(v ?? '')])) }
}
