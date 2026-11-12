import { Ink } from '@/lib/ink/builder'
import { blobFill } from '@/lib/ink/fills'
import { ellipsePoly, polyPath, roundRectPoly } from '@/lib/ink/geom'
import type { PaintKey } from '@/lib/ink/paint'
import { clamp, makeRng, type Rng } from '@/lib/ink/rng'
import { box } from '@/lib/ink/shapes'
import type { Pt } from '@/lib/ink/types'

export const CONFETTI_KINDS = ['strip', 'dot', 'star', 'triangle', 'curl', 'scrap'] as const
export type ConfettiKind = (typeof CONFETTI_KINDS)[number]
export const CONFETTI_COLORS = ['tomato', 'tangerine', 'lemon', 'grass', 'teal', 'sky', 'grape', 'bubblegum'] as const satisfies readonly PaintKey[]
export type ConfettiColor = (typeof CONFETTI_COLORS)[number]

export interface ConfettiPiece {
  svg: string
  w: number
  h: number
}

const cache = new Map<string, ConfettiPiece>()

const outline = (ink: Ink, x: number, y: number, w: number, h: number, corner = 1) =>
  box(ink, x, y, w, h, { pen: 'ink.fine', corner, opts: { width: 0.55, alpha: 0.6 } })

export function confettiPiece(kind: ConfettiKind, color: PaintKey, variant = 0): ConfettiPiece {
  const key = `${kind}|${color}|${variant}`
  const hit = cache.get(key)
  if (hit) return hit
  const ink = new Ink(`confetti|${key}`, { grain: false })
  const fill = (poly: Pt[], alpha = 0.95, mis = 0.55) => blobFill(ink, poly, color, { alpha, mis, rough: 0.35, material: 'top' })
  let w = 16, h = 16
  const printed = (pts: Pt[]) => {
    ink.flat('top', polyPath(pts.map((p): Pt => [p[0] + 0.55, p[1] + 0.4]), 10), color, 0.95)
    ink.flat('top', polyPath(pts, 10), 'ink', 0.6, { stroke: 'ink', sw: 0.6 })
  }
  ink.layer('rest', () => {
    switch (kind) {
      case 'strip': {
        w = 9; h = 17
        fill(roundRectPoly(1.5, 1.5, 6, 14, 0.8))
        ink.flat('top', 'M4.5 2.5V14.5H7.5V2.5Z', 'ink', 0.13)
        outline(ink, 1.5, 1.5, 6, 14)
        break
      }
      case 'dot': {
        w = 14; h = 14
        fill(ellipsePoly(7, 7, 4.8, 4.6, 14))
        ink.flat('top', 'M9.6 5.2a1.5 1.5 0 1 1-.01 0Z', 'photo', 0.55)
        break
      }
      case 'star': {
        w = 20; h = 20
        const r = makeRng(`star${variant}`)
        const pts: Pt[] = []
        for (let i = 0; i < 10; i++) {
          const a = -Math.PI / 2 + (i * Math.PI) / 5 + r.gauss(0, 0.04)
          const rad = (i % 2 ? 4.4 : 8.8) * (1 + r.gauss(0, 0.05))
          pts.push([10 + Math.cos(a) * rad, 10.4 + Math.sin(a) * rad])
        }
        printed(pts)
        break
      }
      case 'triangle': {
        w = 16; h = 15
        printed([[8, 1.4], [14.8, 13.4], [1.3, 13]])
        break
      }
      case 'curl': {
        w = 26; h = 14
        const pts: Pt[] = []
        for (let i = 0; i <= 14; i++) pts.push([2 + i * 1.65, 7 + Math.sin(i * 0.9 + variant) * 4.2])
        ink.stroke(pts, 'ink', { color, width: 1.35, wobble: 0.3, start: 'soft', end: 'soft' })
        break
      }
      case 'scrap': {
        w = 16; h = 16
        const r: Rng = makeRng(`scrap${variant}`)
        const pts: Pt[] = []
        const n = 6 + (variant % 2)
        for (let i = 0; i < n; i++) {
          const a = (i / n) * Math.PI * 2 + r.gauss(0, 0.2)
          const rad = 4.6 + r() * 3.4
          pts.push([8 + Math.cos(a) * rad, 8 + Math.sin(a) * rad])
        }
        fill(pts, 0.95, 0.6)
        break
      }
    }
  })
  const res = ink.toSvg({ w, h, pad: 1 })
  const out: ConfettiPiece = { svg: res.svg, w, h }
  cache.set(key, out)
  return out
}

export interface FlightOptions {
  count: number
  spread: number
  angle: number
  velocity: number
  gravity: number
  drift: number
  duration: number
  seed: number
}

export interface Flight {
  kind: ConfettiKind
  color: ConfettiColor
  variant: number
  frames: Array<{ x: number; y: number; rot: number; flip: number; opacity: number }>
  scale: number
}

export const STEP_MS = 50

export function simulate(o: FlightOptions, kinds: readonly ConfettiKind[] = CONFETTI_KINDS, colors: readonly ConfettiColor[] = CONFETTI_COLORS): Flight[] {
  const rng = makeRng(`flight|${o.seed}`)
  const dt = STEP_MS / 1000
  const steps = Math.max(2, Math.round(o.duration / STEP_MS))
  const out: Flight[] = []
  for (let i = 0; i < o.count; i++) {
    const r = rng.fork(i)
    const a = ((o.angle + (r() - 0.5) * o.spread) * Math.PI) / 180
    const speed = o.velocity * (0.35 + 0.65 * Math.sqrt(r()))
    let vx = Math.cos(a) * speed, vy = -Math.sin(a) * speed
    const drag = 2.6 + r() * 1.2
    const sway = 10 + r() * 22, swayW = 3.5 + r() * 3, swayP = r() * 6.28
    const spin = (r() - 0.5) * 900, flipW = 4 + r() * 6, flipP = r() * 6.28
    let x = 0, y = 0
    const frames: Flight['frames'] = []
    for (let s = 0; s <= steps; s++) {
      const t = s * dt
      const p = s / steps
      frames.push({
        x: x + Math.sin(t * swayW + swayP) * sway * clamp(t * 1.5, 0, 1),
        y,
        rot: spin * t * Math.exp(-t * 0.6),
        flip: Math.cos(flipP + flipW * t),
        opacity: p < 0.72 ? 1 : Math.max(0, 1 - (p - 0.72) / 0.28),
      })
      vx += (o.drift - drag * vx) * dt
      vy += (o.gravity - drag * vy) * dt
      x += vx * dt
      y += vy * dt
    }
    out.push({ kind: kinds[Math.floor(r() * kinds.length)], color: colors[Math.floor(r() * colors.length)], variant: Math.floor(r() * 3), frames, scale: 0.85 + r() * 0.5 })
  }
  return out
}
