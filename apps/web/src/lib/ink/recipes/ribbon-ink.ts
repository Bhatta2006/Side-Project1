import { bandFill, blobFill, wash } from '@/lib/ink/fills'
import type { PaintKey } from '@/lib/ink/paint'
import { defineRecipe } from '@/lib/ink/recipes'
import { box, focusRing, underline, RULER } from '@/lib/ink/shapes'
import { clamp } from '@/lib/ink/rng'
import type { Pt } from '@/lib/ink/types'

export const ribbonVariantList = ['banner', 'swallow', 'flag'] as const
export type RibbonVariant = (typeof ribbonVariantList)[number]
export const ribbonSizeList = ['sm', 'default', 'lg'] as const
export type RibbonSize = (typeof ribbonSizeList)[number]
export const ribbonToneList = ['marker', 'hi', 'tangerine', 'lemon', 'grass', 'teal', 'sky', 'bubblegum', 'paper'] as const
export type RibbonTone = (typeof ribbonToneList)[number]

export const RIBBON_SIZES: Record<RibbonSize, { band: number; tail: number; drop: number; text: string; font: number }> = {
  sm: { band: 26, tail: 14, drop: 6, text: 'text-sm', font: 14 },
  default: { band: 34, tail: 20, drop: 9, text: 'text-base', font: 16 },
  lg: { band: 46, tail: 28, drop: 12, text: 'text-xl', font: 20 },
}

export const ribbonGutter = (variant: RibbonVariant): number => (variant === 'flag' ? 12 : 14)

export interface RibbonParams {
  variant: RibbonVariant
  tone: RibbonTone
  size: RibbonSize
  hoverable?: boolean
}

export const ribbonInset = (variant: RibbonVariant, size: RibbonSize): number => (variant === 'banner' ? RIBBON_SIZES[size].tail : Math.round(RIBBON_SIZES[size].band * 0.32))
export const ribbonDrop = (variant: RibbonVariant, size: RibbonSize): number => (variant === 'banner' ? RIBBON_SIZES[size].drop : 0)

const closed = (pts: Pt[]): Pt[] => [...pts, pts[0]]

export const ribbonRecipe = defineRecipe<RibbonParams>({
  id: 'ribbon',
  kind: 'ribbon',
  layers: ['rest', 'hover', 'focus'],
  lazy: ['focus'],
  pad: 12,
  draw(ink, { w, h }, { variant, tone, size, hoverable }, ctx) {
    const S = RIBBON_SIZES[size]
    const D = ribbonDrop(variant, size)
    const H = h - D
    ctx.lazy('focus', (f) => focusRing(f, 0, 0, w, h, { r: 3 }))
    if (ctx.lazyOnly) return
    const fill: PaintKey = tone
    const T = variant === 'banner' ? S.tail : ribbonInset(variant, size)
    const notch = clamp(H * 0.28, 5, 14)
    const outline = ctx.calm ? 'pencil.fine' : 'ink'
    const fine = ctx.calm ? 'pencil.fine' : 'ink.fine'

    ink.layer('rest', () => {
      if (variant === 'banner') {
        const F = clamp(D * 1.2, 6, 18)
        const left: Pt[] = [[T, D], [0.5, D], [notch, D + (H - 0.5) / 2], [0.5, h - 0.5], [T, h - 0.5]]
        const right: Pt[] = left.map(([x, y]) => [w - x, y] as Pt).reverse()
        const foldL: Pt[] = [[T, H], [T + F, H], [T, h - 0.5]]
        const foldR: Pt[] = foldL.map(([x, y]) => [w - x, y] as Pt).reverse()
        ink.part('fill', () => {
          let off = { dx: 0, dy: 0 }
          for (const piece of [left, right, foldL, foldR]) off = blobFill(ink, piece, fill, { alpha: 0.95, mis: ctx.calm ? false : undefined })
          return off
        })
        for (const tail of [left, right]) {
          wash(ink, tail, 'ink', { alpha: 0.16, inset: 0.5 })
          ink.stroke(closed(tail), fine, { poly: true, round: 1.2, simple: true })
        }
        for (const f of [foldL, foldR]) {
          wash(ink, f, 'ink', { alpha: 0.4, inset: 0.3 })
          ink.stroke(closed(f), 'ink.fine', { poly: true, round: 0.8, simple: true })
        }
      }
      const flip = (pts: Pt[]): Pt[] => (ctx.dir === 'rtl' ? pts.map(([x, y]) => [w - x, y] as Pt).reverse() : pts)
      const band: Pt[] =
        variant === 'banner'
          ? [[T, 1.5], [w - T, 1.5], [w - T, H - 1.5], [T, H - 1.5]]
          : variant === 'swallow'
            ? [[1.5, 1.5], [w - 1.5, 1.5], [w - 1.5 - notch, H / 2], [w - 1.5, H - 1.5], [1.5, H - 1.5], [1.5 + notch, H / 2]]
            : flip([[1.5, 1.5], [w - 1.5, 1.5], [w - 1.5 - notch, H / 2], [w - 1.5, H - 1.5], [1.5, H - 1.5]])
      ink.part('fill', () => bandFill(ink, band, fill, { passes: ctx.calm ? 1 : 2, ends: ctx.calm ? 'square' : undefined }))
      if (variant === 'banner') box(ink, T, 0, w - 2 * T, H, { pen: outline, corner: 2 })
      else ink.stroke(closed(band), outline, { poly: true, round: 1.4 })
    })

    if (!hoverable) return
    ink.layer('hover', () => {
      const gutter = T + ribbonGutter(variant)
      if (w - 2 * gutter > 12) underline(ink, gutter, H / 2 + S.font * 0.56, w - 2 * gutter, { kind: 'single', pen: 'ink.fine', opts: { simple: true } })
      const y = H + 3.5
      const x0 = variant === 'banner' ? T + 4 : 6
      const x1 = variant === 'banner' ? w - T - 4 : w - 8
      ink.lines([{ pts: [[x0, y], [x1, y]], o: RULER }], 'ink.fine', { width: 1.2 })
    })
  },
})
