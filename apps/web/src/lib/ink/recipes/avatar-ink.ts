import { blobFill, wash } from '@/lib/ink/fills'
import { ellipsePoly } from '@/lib/ink/geom'
import { defineRecipe } from '@/lib/ink/recipes'
import { clamp, hashSeed } from '@/lib/ink/rng'
import { dashedBox, loop } from '@/lib/ink/shapes'
import type { PaintKey } from '@/lib/ink/paint'
import type { PenName } from '@/lib/ink/types'

export const AVATAR_TONES = ['tomato', 'tangerine', 'lemon', 'grass', 'teal', 'sky', 'grape', 'bubblegum'] as const
export type AvatarTone = (typeof AVATAR_TONES)[number]

export function avatarTone(name: string): AvatarTone {
  const h = hashSeed(name.trim().toLowerCase())
  return AVATAR_TONES[Math.imul(h ^ (h >>> 15), 0x2c1b3c6d) >>> 29]
}

export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean)
  if (!words.length) return ''
  const first = Array.from(words[0])[0] ?? ""
  const last = words.length > 1 ? (Array.from(words[words.length - 1])[0] ?? "") : ""
  return (first + last).toUpperCase()
}

export type AvatarRing = 'ink' | 'you' | 'marker'

const RING_PEN: Record<AvatarRing, PenName> = { ink: 'ink.fine', you: 'blue.fine', marker: 'terracotta' }

export const avatarRingRecipe = defineRecipe<{ ring: AvatarRing }>({
  id: 'avatar-ring',
  kind: 'avatar',
  layers: ['rest'],
  pad: 8,
  draw(ink, { w, h }, { ring }, ctx) {
    const cx = w / 2, cy = h / 2
    const s = Math.min(w, h)
    ink.layer('rest', () => {
      if (ring === 'marker') {
        loop(ink, cx, cy, w / 2 + 1, h / 2 + 1, { pen: 'terracotta', turns: 1.06, opts: { width: clamp(s / 60, 0.28, 0.5), alpha: 0.8 } })
        return
      }
      loop(ink, cx, cy, w / 2 + 1.6, h / 2 + 1.6, { pen: ctx.calm ? 'pencil.fine' : RING_PEN[ring], turns: ctx.calm ? 1.02 : 1.09, opts: { width: clamp(s / 34, 0.85, 1.35) } })
    })
  },
})

export const avatarFallbackRecipe = defineRecipe<{ tone: AvatarTone }>({
  id: 'avatar-fallback',
  kind: 'disc',
  layers: ['rest'],
  pad: 6,
  draw(ink, { w, h }, { tone }, ctx) {
    const cx = w / 2, cy = h / 2
    const body = ellipsePoly(cx, cy, w / 2 - 0.5, h / 2 - 0.5, 28)
    ink.layer('rest', () => {
      ink.poly('under', body, 'slip', 0.95)
      const key = tone as PaintKey
      if (ctx.calm) wash(ink, body, key, { alpha: 0.5 })
      else ink.part('fill', () => blobFill(ink, body, key, { alpha: 0.62, mis: clamp(Math.min(w, h) * 0.07, 0.8, 2.4) }))
    })
  },
})

export type AvatarStatus = 'online' | 'away' | 'busy' | 'offline' | 'marker'
const STATUS_KEY: Record<AvatarStatus, PaintKey> = { online: 'grass', away: 'tangerine', busy: 'tomato', offline: 'pencil-mark', marker: 'marker' }

export const avatarBadgeRecipe = defineRecipe<{ status: AvatarStatus }>({
  id: 'avatar-badge',
  kind: 'dot',
  layers: ['rest'],
  pad: 4,
  draw(ink, { w, h }, { status }, ctx) {
    const cx = w / 2, cy = h / 2
    ink.layer('rest', () => {
      ink.poly('under', ellipsePoly(cx, cy, w / 2 + 0.5, h / 2 + 0.5, 16), 'slip', 0.95)
      blobFill(ink, ellipsePoly(cx, cy, w / 2 - 0.4, h / 2 - 0.4, 16), STATUS_KEY[status], { alpha: status === 'offline' ? 0.55 : 0.92, mis: ctx.calm ? false : 0.5, rough: 0.4 })
      if (!ctx.calm) loop(ink, cx, cy, w / 2 + 0.2, h / 2 + 0.2, { pen: 'ink.fine', turns: 1.1, opts: { width: 0.85 } })
    })
  },
})

export const avatarCountRecipe = defineRecipe<Record<string, never>>({
  id: 'avatar-count',
  kind: 'disc',
  layers: ['rest'],
  pad: 6,
  draw(ink, { w, h }, _p, ctx) {
    const body = ellipsePoly(w / 2, h / 2, w / 2 - 1, h / 2 - 1, 28)
    ink.layer('rest', () => {
      ink.poly('under', body, 'slip', 0.95)
      wash(ink, body, 'paper-shade', { alpha: 0.9 })
      dashedBox(ink, 0.5, 0.5, w - 1, h - 1, { r: Math.min(w, h) / 2, pen: ctx.calm ? 'pencil.fine' : 'pencil', dash: Math.max(4, Math.min(w, h) * 0.2) })
    })
  },
})
