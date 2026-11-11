import type { ArtColour, ArtDef, Part } from '@/lib/ink/art/types'

const r1 = (v: number): number => Math.round(v * 10) / 10
const pt = (x: number, y: number): string => `${r1(x)} ${r1(y)}`
export type P = readonly [number, number]

const F = (colour: ArtColour, d: string, mis?: number): Part => (mis === undefined ? ['f', colour, d] : ['f', colour, d, mis])
const S = (d: string, w?: number): Part => (w === undefined ? ['s', d] : ['s', d, w])
const C = (colour: ArtColour, d: string, w?: number): Part => (w === undefined ? ['c', colour, d] : ['c', colour, d, w])
export const L = (d: string, w = 1): Part => ['c', 'ink', d, r1(Math.max(0.45, w / 1.5))]
export const dot = (x: number, y: number, r: number): Part => ['d', r1(x), r1(y), r1(r)]
export const dots = (list: ReadonlyArray<readonly [number, number, number]>): Part[] => list.map(([x, y, r]) => dot(x, y, r))

export interface Xf {
  dx?: number
  dy?: number
  rot?: number
  k?: number
  sx?: number
  sy?: number
  cx?: number
  cy?: number
}

const CMD = /^[MLlQCOEZ]$/
export const BASE: P = [32.4, 67.4]

function xfPath(d: string, t: Xf): string {
  const sx = t.sx ?? t.k ?? 1, sy = t.sy ?? t.k ?? 1
  const a = ((t.rot ?? 0) * Math.PI) / 180
  const c = Math.cos(a), s = Math.sin(a)
  const cx = t.cx ?? BASE[0], cy = t.cy ?? BASE[1], dx = t.dx ?? 0, dy = t.dy ?? 0
  const at = (x: number, y: number): string => {
    const ux = (x - cx) * sx, uy = (y - cy) * sy
    return pt(cx + ux * c - uy * s + dx, cy + ux * s + uy * c + dy)
  }
  const vec = (x: number, y: number): string => pt(x * sx * c - y * sy * s, x * sx * s + y * sy * c)
  const tok = d.match(/[MLlQCOEZ]|-?\d*\.?\d+/g) ?? []
  const out: string[] = []
  let i = 0
  while (i < tok.length) {
    const cmd = tok[i++]
    if (cmd === 'Z') {
      out.push('Z')
      continue
    }
    const n: number[] = []
    while (i < tok.length && !CMD.test(tok[i])) n.push(Number(tok[i++]))
    if (cmd === 'O') out.push(`O ${at(n[0], n[1])} ${r1(n[2] * sx)}${n[3] !== undefined ? ` ${r1(n[3] * sy)}` : ''}`)
    else if (cmd === 'E') out.push(`E ${at(n[0], n[1])} ${r1(n[2] * sx)} ${r1(n[3] * sy)} ${r1(n[4] + (t.rot ?? 0))} ${r1(n[5] + (t.rot ?? 0))}`)
    else {
      const pairs: string[] = []
      for (let j = 0; j + 1 < n.length; j += 2) pairs.push(cmd === 'l' ? vec(n[j], n[j + 1]) : at(n[j], n[j + 1]))
      out.push(`${cmd} ${pairs.join(' ')}`)
    }
  }
  return out.join(' ')
}

export function xf(parts: readonly Part[], t: Xf): Part[] {
  const sx = t.sx ?? t.k ?? 1, sy = t.sy ?? t.k ?? 1
  const a = ((t.rot ?? 0) * Math.PI) / 180
  const c = Math.cos(a), s = Math.sin(a)
  const cx = t.cx ?? BASE[0], cy = t.cy ?? BASE[1]
  const at = (x: number, y: number): [number, number] => {
    const ux = (x - cx) * sx, uy = (y - cy) * sy
    return [r1(cx + ux * c - uy * s + (t.dx ?? 0)), r1(cy + ux * s + uy * c + (t.dy ?? 0))]
  }
  return parts.map((p): Part => {
    switch (p[0]) {
      case 'f':
        return p[3] === undefined ? ['f', p[1], xfPath(p[2], t)] : ['f', p[1], xfPath(p[2], t), p[3]]
      case 's':
        return p[3] !== undefined ? ['s', xfPath(p[1], t), p[2], p[3]] : p[2] === undefined ? ['s', xfPath(p[1], t)] : ['s', xfPath(p[1], t), p[2]]
      case 'c':
        return p[4] !== undefined ? ['c', p[1], xfPath(p[2], t), p[3], p[4]] : p[3] === undefined ? ['c', p[1], xfPath(p[2], t)] : ['c', p[1], xfPath(p[2], t), p[3]]
      case 'h':
        return p[2] === undefined ? ['h', xfPath(p[1], t)] : ['h', xfPath(p[1], t), p[2]]
      case 'd': {
        const [x, y] = at(p[1], p[2])
        return p[3] === undefined ? ['d', x, y] : ['d', x, y, r1(p[3] * Math.sqrt(sx * sy))]
      }
      case 't': {
        const [x, y] = at(p[2], p[3])
        return ['t', p[1], x, y, r1(p[4] * Math.sqrt(sx * sy)), p[5], p[6]]
      }
    }
  })
}

export function spline(pts: readonly P[], o: { closed?: boolean; corners?: readonly number[]; z?: boolean } = {}): string {
  const n = pts.length
  const corner = new Set(o.corners ?? [])
  const at = (i: number): P => (o.closed ? pts[((i % n) + n) % n] : pts[Math.max(0, Math.min(n - 1, i))])
  const tan = (i: number): P => {
    const a = at(i - 1), b = at(i + 1)
    return [(b[0] - a[0]) / 6, (b[1] - a[1]) / 6]
  }
  const segs = o.closed ? n : n - 1
  let d = `M${pt(...pts[0])}`
  for (let i = 0; i < segs; i++) {
    const p1 = at(i), p2 = at(i + 1)
    let c1: P, c2: P
    if (corner.has(((i % n) + n) % n)) c1 = [p1[0] + (p2[0] - p1[0]) / 3, p1[1] + (p2[1] - p1[1]) / 3]
    else {
      const t = tan(i)
      c1 = [p1[0] + t[0], p1[1] + t[1]]
    }
    if (corner.has((((i + 1) % n) + n) % n)) c2 = [p2[0] - (p2[0] - p1[0]) / 3, p2[1] - (p2[1] - p1[1]) / 3]
    else {
      const t = tan(i + 1)
      c2 = [p2[0] - t[0], p2[1] - t[1]]
    }
    d += ` C${pt(...c1)} ${pt(...c2)} ${pt(...p2)}`
  }
  return d + (o.closed && o.z ? ' Z' : '')
}

export function oval(cx: number, cy: number, rx: number, ry: number, tilt = 0): string {
  const k = 0.5523
  const a = (tilt * Math.PI) / 180
  const c = Math.cos(a), s = Math.sin(a)
  const q = (x: number, y: number): string => pt(cx + x * c - y * s, cy + x * s + y * c)
  return `M${q(rx, 0)} C${q(rx, ry * k)} ${q(rx * k, ry)} ${q(0, ry)} C${q(-rx * k, ry)} ${q(-rx, ry * k)} ${q(-rx, 0)} C${q(-rx, -ry * k)} ${q(-rx * k, -ry)} ${q(0, -ry)} C${q(rx * k, -ry)} ${q(rx, -ry * k)} ${q(rx, 0)} Z`
}

export type Tier = 'm' | 's' | 'u'

const OUT: readonly P[] = [
  [14, 58.6], [12.8, 46], [13.2, 34], [13.8, 26.6], [21.6, 15.4], [28.4, 8.2], [32.4, 4.2], [36.4, 8.6], [43.4, 16.4], [51.2, 26.8],
  [51.8, 38], [51.6, 50], [50.6, 58.8], [46.2, 65.8], [38, 68.4], [28, 68.6], [19.4, 66.2],
]
const OUTLINE = spline(OUT, { closed: true, corners: [6], z: true })
const SCALLOP = 'M13.8 26.6 Q19.8 34.4 26.6 27.8 Q32.8 34.8 39.2 27.6 Q45.4 33.8 51.2 26.8'
const CONE = `${spline([[14.4, 26.2], [21.8, 15.8], [28.6, 8.6], [32.4, 4.8], [36.3, 9], [43.3, 16.8], [50.6, 26.4]], { corners: [3] })} Q45.4 33.6 39.2 27.4 Q32.8 34.6 26.6 27.6 Q19.8 34.2 14.4 26.2 Z`
const BARREL = 'M17.6 24.4 L47.6 24.4 L50.6 27.2 L51 42 L50.4 57 L50.2 60.2 L15.8 60.6 L14.8 58 L13.6 42 L14.6 27 Z'
const ERASER = spline([[14.6, 57.8], [50.8, 57.2], [50.3, 60.4], [46, 65.2], [38, 67.7], [28, 67.9], [20, 65.6], [15.6, 61.6]], { closed: true, corners: [0, 1], z: true })
const TIP = 'M32.4 4.8 L38.2 11.2 Q32.4 14.4 26.6 11.4 Z'
const TIP_SNAPPED = 'M29.4 8 L35.8 8.6 L38 11.2 Q32.4 14.2 26.6 11.4 Z'

const BLUSH = `${oval(19.8, 46.8, 3.7, 2.3, -4)} ${oval(45.2, 46.4, 3.7, 2.3, 3)}`

export function bodyParts(t: Tier, o: { tip?: 'graphite' | 'snapped'; blush?: boolean } = {}): Part[] {
  const tip = o.tip === 'snapped' ? TIP_SNAPPED : TIP
  const fills = [F('lemon', BARREL), F('kraft', CONE), F('pencil', tip), F('bubblegum', ERASER)]
  if (t === 'u') return [...fills, S(OUTLINE, 0.9)]
  return [...fills, ...(o.blush === false ? [] : [F('bubblegum', BLUSH)]), S(OUTLINE, t === 's' ? 1.15 : 1.05), L(SCALLOP, t === 's' ? 1 : 0.85)]
}

export const bodyHi: readonly Part[] = [C('photo', 'M18.6 32.4 Q18 38.2 18.8 42.6', 0.55), L('M14.2 58 L50.8 57.2', 0.8)]

export function peekParts(t: Tier, o: { blush?: boolean } = {}): Part[] {
  const sides = spline([[13, 47.6], [13.2, 34], [13.8, 26.6], [21.6, 15.4], [28.4, 8.2], [32.4, 4.2], [36.4, 8.6], [43.4, 16.4], [51.2, 26.8], [51.8, 38], [51.6, 47.8]], { corners: [5] })
  const strip = 'M7.6 47.2 L57.4 46 L58.4 58.6 L8.4 60.2 Z'
  const fills = [F('lemon', 'M17.6 24.4 L47.6 24.4 L50.6 27.2 L51 42 L50.6 50 L14.6 51 L13.6 42 L14.6 27 Z'), F('kraft', CONE), F('pencil', TIP), F('tangerine~', strip)]
  const lines = [S(sides, t === 'm' ? 1.05 : t === 's' ? 1.15 : 1.3), L('M7.4 47.4 L57.4 46 L58.4 58.6 L8.2 60.2 Z', 0.85)]
  if (t === 'u') return [...fills, ...lines]
  return [...fills, ...(o.blush === false ? [] : [F('bubblegum', `${oval(19.8, 42.4, 3.4, 2.1, -4)} ${oval(45.2, 42, 3.4, 2.1, 3)}`)]), ...lines, L(SCALLOP, t === 's' ? 1 : 0.85)]
}

export type EyeKind = 'dot' | 'happy' | 'closed' | 'wide' | 'squint' | 'dash' | 'x' | 'wink' | 'lens'
export type MouthKind = 'smile' | 'grin' | 'o' | 'flat' | 'frown' | 'wavy' | 'tongue' | 'yawn' | 'gritted'
export type BrowKind = 'none' | 'up' | 'worry' | 'stern' | 'shrug' | 'one'

export interface Face {
  eyes?: EyeKind
  look?: readonly [number, number]
  mouth?: MouthKind
  brows?: BrowKind
  blush?: boolean
}

const XL = 25.2, XR = 39.6, YL = 41.4, YR = 41
const DOT: Record<Tier, number> = { m: 2.7, s: 2.9, u: 2.9 }
const WID: Record<Tier, number> = { m: 1, s: 0.95, u: 1.5 }

const MICRO_EYES: Partial<Record<EyeKind, EyeKind>> = { happy: 'dot', wide: 'dot', squint: 'dot', x: 'dot', closed: 'dash' }
const MICRO_MOUTH: Partial<Record<MouthKind, MouthKind>> = { grin: 'smile', tongue: 'smile', yawn: 'o', wavy: 'flat', gritted: 'flat' }

function eyesOf(kind0: EyeKind, t: Tier, look: readonly [number, number]): Part[] {
  const xl = XL + look[0], yl = YL + look[1], xr = XR + look[0], yr = YR + look[1]
  const w = WID[t], R = DOT[t]
  const kind = t === 'u' ? (MICRO_EYES[kind0] ?? kind0) : kind0
  switch (kind) {
    case 'dot':
      return dots([[xl, yl, R], [xr, yr, R * 0.95]])
    case 'happy':
      return [L(`M${pt(xl - 3.8, yl + 1.8)} Q${pt(xl, yl - 4.4)} ${pt(xl + 3.8, yl + 1.6)} M${pt(xr - 3.6, yr + 1.6)} Q${pt(xr + 0.2, yr - 4.2)} ${pt(xr + 3.9, yr + 1.9)}`, 1.1 * w)]
    case 'closed':
      return [L(`M${pt(xl - 3.8, yl - 0.8)} Q${pt(xl, yl + 3.8)} ${pt(xl + 3.8, yl - 0.6)} M${pt(xr - 3.7, yr - 0.6)} Q${pt(xr + 0.2, yr + 3.6)} ${pt(xr + 3.8, yr - 0.9)}`, 1.1 * w)]
    case 'wide':
      return dots([[xl, yl, R * 1.34], [xr, yr, R * 1.28]])
    case 'squint':
      return [L(`M${pt(xl - 3.6, yl - 3.4)} L${pt(xl + 2.6, yl + 0.2)} L${pt(xl - 3.4, yl + 3.6)} M${pt(xr + 3.6, yr - 3.4)} L${pt(xr - 2.6, yr + 0.2)} L${pt(xr + 3.4, yr + 3.6)}`, 1.1 * w)]
    case 'dash': {
      const a = t === 'u' ? 2.4 : 3.5
      return [L(`M${pt(xl - a, yl + 0.2)} L${pt(xl + a - 0.3, yl - 0.3)} M${pt(xr - a + 0.2, yr - 0.2)} L${pt(xr + a, yr + 0.4)}`, 1.2 * w)]
    }
    case 'x':
      return [L(`M${pt(xl - 3, yl - 3)} L${pt(xl + 3, yl + 3.1)} M${pt(xl + 3, yl - 3.1)} L${pt(xl - 3, yl + 3)} M${pt(xr - 3.1, yr - 3)} L${pt(xr + 3, yr + 3)} M${pt(xr + 3, yr - 3)} L${pt(xr - 3.1, yr + 3.1)}`, 1.15 * w)]
    case 'wink':
      return [dot(xl, yl, R), L(`M${pt(xr - 3.6, yr + 1.6)} Q${pt(xr + 0.2, yr - 4.2)} ${pt(xr + 3.9, yr + 1.9)}`, 1.1 * w)]
    case 'lens':
      return [dot(xl, yl, R)]
  }
}

function mouthOf(kind0: MouthKind, t: Tier): Part[] {
  const w = WID[t]
  const kind = t === 'u' ? (MICRO_MOUTH[kind0] ?? kind0) : kind0
  switch (kind) {
    case 'smile':
      return [L('M29.4 46.4 Q32.6 50.4 36 46.2', 1 * w)]
    case 'grin':
      return [F('ink', 'M28.4 46 Q32.6 47.8 37 45.8 Q36.8 52.2 32.6 52.6 Q28.6 52 28.4 46 Z')]
    case 'o':
      return t === 'm' ? [L('O 32.8 48.8 2.2 2.8', 0.95)] : [dot(32.8, 49, t === 's' ? 2.6 : 3)]
    case 'yawn':
      return [F('ink', 'M30.6 46.6 Q32.6 46 34.8 46.8 Q35.6 50.6 32.8 51.6 Q30 50.8 30.6 46.6 Z')]
    case 'flat':
      return [L('M29 48 L36.2 47.6', 1.05 * w)]
    case 'frown':
      return [L('M29.4 50.2 Q32.8 46.2 36.2 49.6', 1 * w)]
    case 'wavy':
      return [L('M28.6 48.6 Q30.4 46.2 32.4 48.4 Q34.6 50.4 36.6 47.6', 1 * w)]
    case 'gritted':
      return [L('M28.8 47.2 L36.4 47 L36 50.4 L29.2 50.6 Z', 0.85 * w), ...(t === 'm' ? [L('M32.6 47.2 L32.8 50.5', 0.5)] : [])]
    case 'tongue':
      return [L('M29.4 46.4 Q32.6 50.4 36 46.2', 1 * w), F('tomato', 'M32.6 49.2 Q32.4 53.4 35 53.2 Q37.2 52.8 36.2 48.6 Z')]
  }
}

function browsOf(kind: BrowKind, t: Tier): Part[] {
  if (kind === 'none' || t === 'u') return []
  const w = (t === 's' ? 1.2 : 1) * 0.85
  switch (kind) {
    case 'up':
      return [L('M21.8 35 Q25.2 32.6 28.8 34.4 M36.4 34 Q39.8 31.8 43.2 33.8', w)]
    case 'worry':
      return [L('M21.6 36.4 L28.6 33.6 M36.6 33.4 L43.4 36', w)]
    case 'stern':
      return [L('M21.8 33.6 L28.8 36 M36.4 35.6 L43.4 33.2', w)]
    case 'shrug':
      return [L('M21.8 35.4 Q25.2 32 28.8 33 M36.6 33.8 L43 36', w)]
    case 'one':
      return [L('M37 35 Q40 32.8 43.2 34.6', w)]
  }
}

const FACE_XF: Record<Exclude<Tier, 'm'>, Xf> = { s: { cx: 32.4, cy: 44.4, k: 1.12, dy: 1.2 }, u: { cx: 32.4, cy: 44.4, k: 1.3, dy: 1.6 } }

export function faceParts(f: Face, t: Tier): Part[] {
  const inner = [...eyesOf(f.eyes ?? 'dot', t, f.look ?? [0, 0]), ...mouthOf(f.mouth ?? 'smile', t)]
  return [...browsOf(f.brows ?? 'none', t), ...(t === 'm' ? inner : xf(inner, FACE_XF[t]))]
}

export interface Acc {
  m: readonly Part[]
  s?: readonly Part[]
  u?: readonly Part[]
}

export interface PoseSpec {
  face: Face
  turn?: Xf
  tip?: 'graphite' | 'snapped'
  peek?: boolean
  acc?: Acc
  under?: Acc
  hi?: readonly Part[]
  tags?: readonly string[]
}

const NIB_K = 0.05

export const BODY_K = 0.9

const pick = (a: Acc | undefined, t: Tier): readonly Part[] => (a ? (t === 'm' ? a.m : t === 's' ? (a.s ?? a.m) : (a.u ?? [])) : [])

export function pose(spec: PoseSpec): ArtDef {
  const t0 = spec.turn ?? {}
  const turn: Xf = { ...t0, sx: (t0.sx ?? t0.k ?? 1) * BODY_K, sy: (t0.sy ?? t0.k ?? 1) * BODY_K, ...(spec.peek ? { dy: 8.8 } : {}) }
  const face = (t: Tier): Part[] => xf(spec.peek ? xf(faceParts(spec.face, t), { dy: -4.2, cy: 40, sy: 0.9 }) : faceParts(spec.face, t), turn)
  const at = (t: Tier): Part[] => [
    ...pick(spec.under, t),
    ...xf(spec.peek ? peekParts(t, { blush: spec.face.blush }) : bodyParts(t, { tip: spec.tip, blush: spec.face.blush }), turn),
    ...face(t),
    ...pick(spec.acc, t),
  ]
  return {
    grid: [64, 72],
    nibK: NIB_K,
    shade: false,
    ...(spec.tags ? { tags: spec.tags } : {}),
    parts: at('m'),
    small: at('s'),
    micro: at('u'),
    hi: spec.peek ? [] : [...xf(bodyHi, turn), ...(spec.hi ?? [])],
  }
}
