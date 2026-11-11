import { defineMascot, type ArtDef, type ArtColour, type Part } from '@/lib/ink/art/types'
import { BODY_K, dot, L, pose, xf, type Acc, type Xf } from '@/lib/ink/art/mascots/body'

const f1 = (v: number): string => String(Math.round(v * 10) / 10)
type P = readonly [number, number]
const C = (colour: ArtColour, d: string, w?: number): Part => (w === undefined ? ['c', colour, d] : ['c', colour, d, w])
const F = (colour: ArtColour, d: string): Part => ['f', colour, d]

function cloudPath(cx: number, cy: number, rx: number, ry: number, bumps: number, a0 = 140, open = 0.03): string {
  const out: string[] = []
  const span = 360 * (1 - open)
  const pt = (deg: number, k: number): P => [cx + Math.cos((deg * Math.PI) / 180) * rx * k, cy + Math.sin((deg * Math.PI) / 180) * ry * k]
  const p0 = pt(a0, 1)
  out.push(`M ${f1(p0[0])} ${f1(p0[1])}`)
  for (let i = 1; i <= bumps; i++) {
    const a = a0 + (span * i) / bumps
    const m = a0 + (span * (i - 0.5)) / bumps
    const wob = 1 + 0.06 * Math.sin(i * 2.3)
    const c = pt(m, 1.42 * wob)
    const e = pt(a, 1 + 0.03 * Math.cos(i * 1.7))
    out.push(`Q ${f1(c[0])} ${f1(c[1])} ${f1(e[0])} ${f1(e[1])}`)
  }
  return out.join(' ')
}

function puddlePath(cx: number, cy: number, rx: number, ry: number, phase = 0): string {
  const pts: string[] = []
  for (let i = 0; i < 20; i++) {
    const a = (i / 20) * Math.PI * 2
    const r = 1 + 0.16 * Math.sin(3 * a + phase) + 0.09 * Math.sin(5 * a + phase * 1.7)
    pts.push(`${i ? 'L' : 'M'} ${f1(cx + Math.cos(a) * rx * r)} ${f1(cy + Math.sin(a) * ry * r)}`)
  }
  return pts.join(' ')
}

function loopsPath(x0: number, y0: number, w: number, amp: number, loops: number, rise: number, hx = amp * 0.36, frac = 1): string {
  const n = Math.max(6, Math.round(loops * 18 * frac))
  const pts: string[] = []
  for (let i = 0; i <= n; i++) {
    const t = (i / n) * frac
    const a = t * loops * Math.PI * 2
    const loop = Math.floor((a - 0.001) / (Math.PI * 2))
    const grow = (0.5 + 0.5 * t) * (1 + 0.22 * Math.sin(loop * 2.1 + 0.6))
    const x = x0 + t * w + Math.sin(a) * hx * grow * (1 + 0.18 * Math.sin(3.1 * a))
    const y = y0 - t * rise - Math.cos(a) * amp * grow * (1 + 0.12 * Math.sin(2.3 * a)) + amp * grow
    pts.push(`${i ? 'L' : 'M'} ${f1(x)} ${f1(y)}`)
  }
  return pts.join(' ')
}

function dashRun(x0: number, y0: number, x1: number, y1: number, lens: readonly number[], gap: number): string {
  const L = Math.hypot(x1 - x0, y1 - y0)
  const ux = (x1 - x0) / L, uy = (y1 - y0) / L
  const out: string[] = []
  let s = 0.4
  for (let i = 0; s < L - 1; i++) {
    const d = Math.min(lens[i % lens.length], L - s)
    out.push(`M ${f1(x0 + ux * s)} ${f1(y0 + uy * s + Math.sin(i * 2.1) * 0.18)} L ${f1(x0 + ux * (s + d))} ${f1(y0 + uy * (s + d) + Math.cos(i * 1.7) * 0.18)}`)
    s += d + gap + (i % 3) * 0.35
  }
  return out.join(' ')
}

function octagon(cx: number, cy: number, R: number, rot = 22.5): string {
  const out: string[] = []
  for (let i = 0; i < 8; i++) {
    const a = ((rot + i * 45) * Math.PI) / 180
    const wob = 1 + 0.03 * Math.sin(i * 2.9)
    out.push(`${i ? 'L' : 'M'} ${f1(cx + Math.cos(a) * R * wob)} ${f1(cy + Math.sin(a) * R * wob)}`)
  }
  return `${out.join(' ')} Z`
}

export function questionMark(x: number, y: number, k = 1, rot = 0, colour: 'ink' | 'grape' | 'tangerine' = 'ink'): readonly Part[] {
  const hook = 'M0 5.4 Q0.2 0.6 4.6 0.4 Q9.6 0.6 9.2 5.4 Q8.8 8.4 5.6 10 Q4.2 11 4.4 13.4'
  const t = { cx: 4.6, cy: 8, k, rot, dx: x - 4.6, dy: y - 8 }
  return xf([C(colour, `${hook} M3.9 17.2 L5.9 17.9`, colour === 'ink' ? 0.8 : 0.95)], t)
}

export const thoughtCloud: Acc = {
  m: [F('photo', cloudPath(49.8, 11.6, 8.2, 5.2, 5)), C('pencil', `${cloudPath(49.8, 11.6, 8.2, 5.2, 5)} O 43.4 21.8 1.8 1.5`, 0.45), L('M45.8 12 L46.5 12.1 M49.6 12.2 L50.3 12.3 M53.6 11.8 L54.3 11.9', 1.1)],
  s: [F('photo', cloudPath(49.8, 11.6, 8.4, 5.4, 5)), C('pencil', `${cloudPath(49.8, 11.6, 8.4, 5.4, 5)} O 43.4 21.8 2 1.7`, 0.8), L('M45.8 12 L46.6 12.1 M49.6 12.2 L50.4 12.3 M53.6 11.8 L54.4 11.9', 1.3)],
  u: [C('pencil', 'M41.6 24.6 L43 24.7 M46 17.4 L47.6 17.5 M52.2 9.6 L54.2 9.7', 1.7)],
}

const SWISH = [
  'M50.2 21.8 Q55 27.4 50.2 33.6 M56 16.6 Q61 27 56.2 37.6',
  'M49 21.2 Q53.8 26.8 49 33 M54.6 15.8 Q59.8 26.4 54.8 37',
  'M51.4 22.6 Q56.2 28 51.4 34.4 M57 17.8 Q61 27.4 57.2 38.4',
]
export const waveMarks = (frame: 0 | 1 | 2): Acc => ({
  m: [C('sky', SWISH[frame], 0.75)],
  s: [C('sky', SWISH[frame], 1)],
  u: [C('sky', SWISH[frame].split(' M')[0], 1.6)],
})

export const zzz: Acc = {
  m: [C('ink-you', 'M47.6 27.2 L52.4 27.2 L47.6 32.2 L52.4 32.2 M50.6 15.6 L56.6 15.6 L50.6 22.4 L56.6 22.4', 0.5), C('ink-you', 'M52.4 3.6 L60 3.6 L52.4 12.6 L60 12.6', 0.58)],
  s: [C('ink-you', 'M50.4 15.4 L56.8 15.4 L50.4 22.6 L56.8 22.6', 0.75), C('ink-you', 'M52.2 3.4 L60.2 3.4 L52.2 12.8 L60.2 12.8', 0.82)],
  u: [C('ink-you', 'M49.4 13.2 L56.6 13.2 L49.4 22 L56.6 22', 1.1)],
}

const DROP = 'M10.8 20.4 Q6 27.2 7.2 30.8 Q9.2 34.2 12.8 31.8 Q14.6 28.2 10.8 20.4 Z'
export const sweatDrop: Acc = {
  m: [F('sky', DROP), L(`${DROP} M33.8 6.2 L31.8 3.6 M39.2 4.4 L39.8 3.2 M44.6 7.2 L47.6 5.8`, 0.75)],
  s: [F('sky', DROP), L(`${DROP} M33.8 6.2 L31.6 3.6 M44.6 7.2 L47.8 5.8`, 0.95)],
  u: [C('sky', 'M10.4 21 Q6.4 27 8.8 30.8', 1.7)],
}

export const confetti = (frame: 0 | 1): Acc => {
  const fall: Xf = { dy: frame * 2.4 }
  return {
    m: xf([C('tomato', 'M7.2 18.2 L11 16.6 M6 27.4 L9.4 25.6 M16.6 6.4 L18.8 9.6 M55 16.8 L55.2 23 M51.8 20 L58.4 19.8', 1.1), C('sky', 'M52.4 12.2 L56.2 13.8 M10 4.6 L10.2 10.8 M6.8 7.8 L13.4 7.6 M47.4 5.6 L49.6 8.6 M44 8.2 L41.8 11.4', 1.1)], fall),
    s: xf([C('tomato', 'M7.2 18.2 L11 16.6 M16.6 6.4 L18.8 9.6 M55 16.8 L55.2 23 M51.8 20 L58.4 19.8', 1.3), C('sky', 'M52.4 12.2 L56.2 13.8 M10 4.6 L10.2 10.8 M6.8 7.8 L13.4 7.6', 1.3)], fall),
    u: xf([C('tomato', 'M6.2 9.2 L12.2 8.8 M53 10 L56.6 11.2', 1.6)], fall),
  }
}
export const confettiHi: readonly Part[] = [C('lemon', 'M13 15 L13.2 20.4 M10.4 17.6 L16 17.4 M50.6 27.4 L50.8 32.6 M48 30 L53.4 29.8', 0.8), C('grass', 'M9 32 L12.4 30.4 M56.6 6 L58.2 9', 0.95)]

export const questions: Acc = {
  m: [...questionMark(50.4, 14.4, 1.12, 9), ...questionMark(9.2, 22, 0.82, -12)],
  s: [...questionMark(50.4, 14.4, 1.16, 9).map((p): Part => (p[0] === 'c' ? ['c', p[1], p[2], (p[3] ?? 1) * 1.35] : p)), ...questionMark(9.2, 22, 0.88, -12)],
  u: [...questionMark(50.4, 14.4, 1.2, 9).map((p): Part => (p[0] === 'c' ? ['c', p[1], p[2], (p[3] ?? 1) * 1.6] : p))],
}

const HANDLE = 'M50.6 50.2 L53.4 48 L59.4 55.8 L56.4 58.4 Z'
export const magnifier: Acc = {
  m: [F('tangerine', HANDLE), L(`O 44.6 43.4 9 ${HANDLE}`, 1), L('O 42.4 42.4 4.6', 0.8), dot(43, 42.6, 2.2)],
  s: [F('tangerine', HANDLE), L(`O 44.6 43.4 9 ${HANDLE}`, 1.3), dot(42.8, 42.6, 2.9)],
  u: [F('tangerine', HANDLE), L('O 44.6 43.4 9', 1.6)],
}

export const stopSign: Acc = {
  m: [F('tomato', octagon(51.4, 12.8, 8.2)), L(octagon(51.4, 12.8, 8.2), 0.8), C('photo', 'M46.4 13 L56.4 12.6', 1.2)],
  s: [F('tomato', octagon(51.4, 12.8, 8.2)), L(octagon(51.4, 12.8, 8.2), 1), C('photo', 'M46.2 13 L56.6 12.6', 1.5)],
  u: [F('tomato', octagon(51.4, 12.8, 8)), L(octagon(51.4, 12.8, 8), 1.2)],
}

const PLUG = 'M53.2 60.2 L59.8 60 L60 66.8 L53.4 67 Z'
export const cableCut: Acc = {
  m: [F('tangerine', PLUG), L(`M50.6 47.8 Q57.4 48.4 57 54.6 Q56.6 57.8 56.6 60.2 ${PLUG} M53 62 L50 62 M53.2 65.2 L50.2 65.2`, 0.85), C('tangerine', 'M52.6 43.6 L54.8 40.4 M55.8 46.6 L59.6 45.2 M50.6 42.6 L51 39.4', 0.85)],
  s: [F('tangerine', PLUG), L(`M50.6 47.8 Q57.4 48.4 57 54.6 Q56.6 57.8 56.6 60.2 ${PLUG} M53 62 L50 62 M53.2 65.2 L50.2 65.2`, 1), C('tangerine', 'M52.6 43.6 L54.8 40.4 M55.8 46.6 L59.6 45.2', 1.1)],
  u: [C('tangerine', 'M52.6 45 L55 41.6 M55.8 48 L59.8 46.6', 1.6)],
}

const BOX = 'M44.8 48.8 L59.6 47.2 L60 65.2 L45.2 66.8 Z'
export const parcel: Acc = {
  m: [F('kraft', BOX), L('M44.6 49 L59.8 47 L60.2 65.4 L45 67 Z M52.4 48 L52.8 66 M45 57.4 L60 56', 0.8)],
  s: [F('kraft', BOX), L('M44.6 49 L59.8 47 L60.2 65.4 L45 67 Z M52.4 48 L52.8 66 M45 57.4 L60 56', 1)],
  u: [F('kraft', BOX), L('M44.6 49 L59.8 47 L60.2 65.4 L45 67 Z', 1.2)],
}

const ARROW = 'M46.6 31 Q53 29.4 58.6 31.8 M53.6 26 L59.2 31.8 L53.4 36.6'
export const arrow: Acc = {
  m: [C('tangerine', ARROW, 0.7)],
  s: [C('tangerine', ARROW, 1)],
  u: [C('tangerine', ARROW, 1.7)],
}

const box = (lens: readonly number[]): string =>
  [dashRun(46.4, 5.2, 60.2, 5.6, lens, 1.7), dashRun(60.2, 5.6, 60, 21.4, lens, 1.7), dashRun(60, 21.4, 46.2, 21, lens, 1.7), dashRun(46.2, 21, 46.4, 5.2, lens, 1.7)].join(' ')
export const dashedFrame: Acc = {
  m: [L(box([3.6, 2.6]), 0.62)],
  s: [L(box([4.2, 3]), 0.9)],
  u: [L('M47.2 6.2 L52.2 5.8 M55.2 6.1 L60.4 6.3 L60.2 11.4 M60.2 14.6 L60 20.2 M55.4 21.3 L47.3 20.8', 1.2)],
}

export const scribble = (x: number, y: number, frac = 1): Acc => ({
  m: [C('pencil', loopsPath(x, y, 59 - x, 5.2, 4, -6, 2, frac), 0.5)],
  s: [C('pencil', loopsPath(x, y, 59 - x, 5.2, 3, -6, 2.1, frac), 0.8)],
  u: [C('pencil', loopsPath(x, y, 59 - x, 5.4, 2, -6, 2.1, frac), 1.5)],
})

function fan(cx: number, cy: number, angles: readonly number[], r0: number, r1: number, jit = 0): string {
  return angles
    .map((a, i) => {
      const t = (a * Math.PI) / 180
      const ra = r0 + Math.sin(i * 2.7) * jit, rb = r1 + Math.cos(i * 1.9) * jit
      return `M ${f1(cx + Math.sin(t) * ra)} ${f1(cy - Math.cos(t) * ra)} L ${f1(cx + Math.sin(t) * rb)} ${f1(cy - Math.cos(t) * rb)}`
    })
    .join(' ')
}

export const propDefs = defineMascot({
  'thought-cloud': {
    grid: [64, 72],
    shade: false,
    nibK: 0.03,
    tags: ['thought', 'thinking', 'hmm', 'idea'],
    parts: [
      ['f', 'paper-shade', cloudPath(33, 26, 23, 14.6, 7, 150)],
      ['c', 'pencil', cloudPath(33, 26, 23, 14.6, 7, 150), 0.7],
      ['c', 'pencil', 'O 15.6 50.4 4.6 3.8 O 8.4 61.6 2.5', 0.65],
      ['d', 23.6, 26.4, 2],
      ['d', 33, 26.8, 2],
      ['d', 42.6, 26, 2],
    ],
    small: [
      ['c', 'pencil', cloudPath(33, 26, 22.6, 14.6, 6, 150), 1.25],
      ['c', 'pencil', 'O 15.6 50.4 5 4.2 O 8.6 62 2.8', 1.15],
      ['d', 23.6, 26.6, 2.6],
      ['d', 33, 27, 2.6],
      ['d', 42.6, 26.2, 2.6],
    ],
  },
  'question-mark': {
    grid: [64, 72],
    nibK: 0.034,
    tags: ['question', 'unknown', 'huh', 'help'],
    parts: [...questionMark(27, 38, 3.1, -8), ...questionMark(50.4, 21, 1.5, 16, 'grape'), ['c', 'tangerine', 'M45.6 52 L49 50.4 M52.4 56.4 L56 56', 0.8]],
    small: [...questionMark(28, 36, 3.2, -6).map((p): Part => (p[0] === 'c' ? ['c', p[1], p[2], (p[3] ?? 1) * 1.35] : p)), ...questionMark(51.4, 21, 1.5, 16, 'grape')],
  },
  zzz: {
    grid: [64, 72],
    nibK: 0.034,
    tags: ['sleep', 'quiet', 'idle', 'snooze'],
    parts: [
      ['c', 'ink-you', 'M8.6 58.4 L15.2 58 L8.2 65.6 L15.8 65.2', 0.85],
      ['c', 'ink-you', 'M21.6 40.6 L31.6 40 L21 51.6 L32.2 51', 0.95],
      ['c', 'ink-you', 'M36.2 12.8 L52.4 12 L35.6 30.8 L53.4 30', 1.05],
    ],
    small: [
      ['c', 'ink-you', 'M8.6 58.4 L15.6 58 L8.2 66 L16 65.4', 1.15],
      ['c', 'ink-you', 'M22 40.4 L32.4 39.8 L21.4 52 L33 51.4', 1.2],
      ['c', 'ink-you', 'M36.2 12.6 L53 11.8 L35.6 31.4 L54 30.6', 1.3],
    ],
  },
  'sweat-drop': {
    grid: [64, 72],
    shade: false,
    nibK: 0.03,
    tags: ['worry', 'nervous', 'hot', 'oops'],
    parts: [
      ['f', 'sky', 'M33 10.8 Q17.6 33.4 19.4 45.4 Q22 58.6 33.4 57.6 Q45.8 55.4 44.6 43.6 Q43.8 31.6 33.6 12.4 Z'],
      ['c', 'ink-you', 'M33.4 9.6 Q18.4 31.6 19.2 44.8 Q22 59.4 34 58.6 Q46.8 56.2 45.4 43.2 Q44.4 32 35.4 15.6', 0.45],
      ['c', 'photo', 'M24 46.6 Q23.6 41.4 26 37.4', 1],
      ['c', 'sky', 'M50 26.4 L56 21.4 M52.4 44.4 L59 45.2 M11.6 26.8 L7.6 22.4', 0.9],
    ],
    small: [
      ['f', 'sky', 'M33 9.4 Q16.6 33.4 18.4 46 Q21.4 60 33.4 58.8 Q46.8 56.4 45.6 44 Q44.8 31.8 33.8 11.2 Z'],
      ['c', 'ink-you', 'M33.6 8.4 Q17.4 31.6 18.2 45.6 Q21.4 60.6 33.6 59.8 Q47.6 57.2 46.2 43.8 Q45.2 31 36 14.4', 0.6],
      ['c', 'photo', 'M23.4 47 Q23 41.4 25.8 37', 1.2],
      ['c', 'sky', 'M50.6 26.4 L56.4 21.4 M52.8 45 L59 45.8', 1.1],
    ],
  },
  'ink-blot': {
    grid: [64, 72],
    shade: false,
    nibK: 0.03,
    tags: ['spill', 'error', 'mess', 'oops'],
    parts: [
      ['f', 'ink', `${puddlePath(31, 41.6, 17.4, 7.4, 0.4)} ${puddlePath(14.6, 44.4, 8.4, 5.4, 2)} ${puddlePath(47.4, 38.6, 10, 5.6, 3.3)}`],
      ['c', 'photo', 'M21.6 40.4 Q24.6 37.4 29.6 37', 0.9],
      ['d', 55.6, 28.4, 2.6],
      ['d', 8.4, 54, 2],
      ['d', 46, 60.4, 1.7],
    ],
    small: [
      ['f', 'ink', `${puddlePath(31, 41.6, 17.8, 7.8, 0.4)} ${puddlePath(14.6, 44.4, 8.8, 5.6, 2)} ${puddlePath(47.4, 38.6, 10.4, 5.8, 3.3)}`],
      ['c', 'photo', 'M21.6 40.4 Q24.6 37.4 29.6 37', 1.1],
      ['d', 55.6, 28.4, 3],
      ['d', 8.4, 54, 2.4],
    ],
  },
  'lead-shards': {
    grid: [64, 72],
    nibK: 0.03,
    tags: ['broken', 'snapped', 'error'],
    parts: [
      ['f', 'ink', 'M9.6 47.6 L30.6 27 L36.4 32 L28.2 41.6 L15.4 53.6 Z M38.6 21.4 L57.6 33.6 L51.6 44 L43.6 40.6 Z'],
      ['s', 'M9 47.4 L30.8 26.6 L36.8 32.2 L28 41.8 L15.6 54 Z M38.4 21 L58 33.8 L51.8 44.4 L43.4 41 Z', 0.6],
      ['c', 'pencil', 'M12.6 24 L21.2 30.6 M20.6 16.4 L26.2 24.4 M38 52 L43.2 61 M47.4 51.6 L54 58', 0.8],
    ],
    small: [
      ['f', 'ink', 'M9.6 47.6 L30.6 27 L37 32.4 L28.2 41.6 L15.4 53.6 Z M38.6 21 L58 33.6 L51.6 44.6 L43.4 40.8 Z'],
      ['c', 'pencil', 'M12.6 24 L21.2 30.6 M20.6 16.4 L26.2 24.4 M38 52 L43.2 61', 1.1],
    ],
  },
  'confetti-burst': {
    grid: [64, 72],
    nibK: 0.03,
    tags: ['party', 'success', 'celebrate', 'done'],
    parts: [
      ['f', 'tomato', 'M11.4 24.4 L18 22 L20.4 28.6 L13.8 31 Z'],
      ['f', 'sky', 'M44.6 10.4 L51.4 12 L49.8 18.8 L43 17.2 Z'],
      ['c', 'lemon', fan(32, 62, [-58, 24], 20, 27, 1.2), 1],
      ['c', 'grass', fan(32, 62, [-16], 36, 43, 1.2), 1],
      ['c', 'grape', fan(32, 62, [-28, 12], 44, 50, 1.2), 1],
      ['c', 'tangerine', fan(32, 62, [40], 30, 36, 1.2), 1],
    ],
    small: [
      ['f', 'tomato', 'M10.4 24.4 L18.6 21.8 L21.2 29.6 L13 32 Z'],
      ['f', 'sky', 'M44 9.6 L52 11.6 L50 19.6 L42 17.6 Z'],
      ['c', 'lemon', fan(32, 62, [-58, 24], 20, 28, 1), 1.3],
      ['c', 'grass', fan(32, 62, [-16], 36, 44, 1), 1.3],
      ['c', 'grape', fan(32, 62, [-28, 12], 44, 51, 1), 1.3],
      ['c', 'tangerine', fan(32, 62, [40], 30, 37, 1), 1.3],
    ],
  },
  magnifier: {
    grid: [64, 72],
    nibK: 0.03,
    tags: ['search', 'find', 'zoom', 'look'],
    parts: [
      ['f', 'sky~', 'O 26.4 27.6 18'],
      ['f', 'tangerine', 'M39.4 40.6 L46.6 36 L58.6 56.6 L52 61.2 Z'],
      ['c', 'pencil', 'O 26.4 27.6 19', 1],
      ['s', 'M39.8 40.2 L46.6 35.8 L59 56.4 L52.2 61.4 Z', 0.75],
      ['c', 'photo', 'M14.2 18.4 Q17.6 12.6 24 11', 1],
      ['s', 'O 26.6 28.6 9.4 7.4', 0.9],
      ['d', 26.8, 28.6, 5],
    ],
    small: [
      ['f', 'tangerine', 'M39.4 40.6 L46.6 36 L58.6 56.6 L52 61.2 Z'],
      ['c', 'pencil', 'O 26.4 27.6 19', 1.2],
      ['s', 'M39.8 40.2 L46.6 35.8 L59 56.4 L52.2 61.4 Z O 26.6 28.6 9.4 7.4', 0.9],
      ['d', 26.8, 28.6, 5.4],
    ],
  },
  'dashed-frame': {
    grid: [64, 72],
    nibK: 0.03,
    tags: ['placeholder', 'empty', 'no data', 'drop zone', 'skeleton'],
    parts: [
      ['c', 'pencil', `${dashRun(6, 10, 6.2, 62, [4.6, 3, 5.4], 1.8)} ${dashRun(6, 10, 58.6, 10.6, [4.2, 5, 3.2], 1.7)} ${dashRun(58.6, 10.6, 58.8, 46, [4.6, 3.2], 1.8)} ${dashRun(6.2, 62, 34, 62.4, [4.2, 3.4], 1.7)}`, 0.6],
      ['c', 'pencil', 'M14 20 L14.4 52 L50.4 52.4', 0.55],
      ['c', 'pencil-mark', `${dashRun(20, 52, 20.2, 40, [3, 2], 1.4)} ${dashRun(30.8, 52, 31, 29, [3.2, 2.2], 1.4)} ${dashRun(41.6, 52, 41.8, 35, [3, 2], 1.4)}`, 0.55],
      ['c', 'sky', 'M4.4 6.8 L7.2 10.4 M59.6 6.8 L57.6 10.4 M4.6 64.2 L7 61.4', 0.7],
    ],
    small: [
      ['c', 'pencil', `${dashRun(6, 10, 6.2, 62, [5, 3.4], 2)} ${dashRun(6, 10, 58.6, 10.6, [5, 3.6], 2)} ${dashRun(58.6, 10.6, 58.8, 46, [5, 3.4], 2)}`, 1],
      ['c', 'pencil', 'M14 20 L14.4 52 L50.4 52.4', 0.9],
      ['c', 'pencil-mark', `${dashRun(25, 52, 25.2, 36, [4, 3], 1.4)} ${dashRun(38, 52, 38.2, 28, [4, 3], 1.4)}`, 0.9],
    ],
  },
  'cable-cut': {
    grid: [64, 72],
    nibK: 0.03,
    tags: ['offline', 'disconnected', 'unplugged', 'network'],
    parts: [
      ['c', 'pencil-mark', 'M23 52.6 Q34 64 42 52 Q50 38.4 47.4 30', 1],
      ['f', 'pencil-mark', 'M6.4 44.6 L21.4 43.4 L22.8 60.4 L7.6 61.6 Z'],
      ['s', 'M6 44.4 L21.6 43 L23.2 60.6 L7.4 62 Z M21.4 47 L27.4 46.4 M21.8 56.8 L27.8 56.2', 0.8],
      ['c', 'pencil-mark', 'M47.4 30 L46.6 24.4 M48.8 29.6 L50.2 24', 0.8],
      ['c', 'tangerine', 'M44 16.4 L41.4 11.4 M51 14.6 L53.4 9.4 M56.4 22.6 L59.6 20.8', 0.9],
    ],
    small: [
      ['c', 'pencil-mark', 'M23 52.6 Q34 64 42 52 Q50 38.4 47.4 30', 1.2],
      ['f', 'pencil-mark', 'M6.4 44.6 L21.4 43.4 L22.8 60.4 L7.6 61.6 Z'],
      ['s', 'M6 44.4 L21.6 43 L23.2 60.6 L7.4 62 Z M21.4 47 L27.4 46.4 M21.8 56.8 L27.8 56.2', 1.1],
      ['c', 'tangerine', 'M44 16.4 L41.4 11.4 M51 14.6 L53.4 9.4 M56.4 22.6 L59.6 20.8', 1.2],
    ],
  },
  'sheet-box': {
    grid: [64, 72],
    nibK: 0.03,
    tags: ['upload', 'file', 'paper', 'carry'],
    parts: [
      ['f', 'kraft', 'M8.2 42.2 L54.4 41.2 L56.2 66.3 L10.4 67.7 Z'],
      ['s', 'M7.4 42.2 L54.4 40.6 L56.4 66.2 L9.6 68 Z M8 42.2 L26 50 L31.4 41.6', 0.9],
      ['f', 'sticky-blue', 'M12 8 L45 6 L47.4 46 L14.6 48.4 Z'],
      ['s', 'M11.4 8.4 L37.4 6.4 L47.4 6 L48 47 L14.4 49 Z', 0.9],
      ['c', 'pencil', 'M17 18 L41 16.6 M17.6 26.4 L42 25 M18.4 34.6 L42.6 33.2', 0.5],
      ['c', 'pencil-mark', 'M37.6 6.4 Q38.4 12.4 43.6 13.4 L47.6 13.2', 0.65],
    ],
    small: [
      ['f', 'kraft', 'M8.2 42.2 L54.4 41.2 L56.2 66.3 L10.4 67.7 Z'],
      ['s', 'M7.4 42.2 L54.4 40.6 L56.4 66.2 L9.6 68 Z', 1.15],
      ['f', 'sticky-blue', 'M12 8 L45 6 L47.4 46 L14.6 48.4 Z'],
      ['s', 'M11.4 8.4 L37.4 6.4 L47.4 6 L48 47 L14.4 49 Z', 1.15],
      ['c', 'pencil', 'M17.2 20.4 L41.4 18.8 M18.2 30.6 L42.2 29.2', 0.9],
    ],
  },
  'stop-tick': {
    grid: [64, 72],
    shade: false,
    nibK: 0.03,
    tags: ['no', 'blocked', 'denied', 'forbidden'],
    parts: [
      ['c', 'red', 'O 32.4 36.4 22', 1],
      ['c', 'red', 'M16.6 52.2 L48.6 20.4', 1.05],
      ['c', 'red', 'M11.6 30 Q13 24 16.4 20', 0.7],
    ],
    small: [
      ['c', 'red', 'O 32.4 36.4 23', 1.3],
      ['c', 'red', 'M16.2 52.6 L48.8 20', 1.35],
    ],
  },
  shavings: {
    grid: [64, 72],
    nibK: 0.03,
    tags: ['sharpen', 'wood', 'curl', 'mess'],
    parts: [
      ['c', 'kraft', 'M28 27 Q10 27 9.6 18.4 Q11 11.4 19 13 Q23 17.4 18 20 M56.4 46.4 Q38 46.4 38 38 Q39.4 32 46.4 33.4 Q50 37.4 45.6 39.6 M30 64 Q12 64 12 56.4 Q13.4 50.6 20 52 Q23.6 56 19.6 58', 1.5],
      ['c', 'pencil', 'M28 28.4 Q8 28.6 8 18.2 Q9.6 9.8 19.6 11.6 Q24.4 16.6 18.6 21.4 M56.6 47.8 Q36.4 48 36.4 37.8 Q38 30.4 46.8 32 Q51.4 37.2 46 40.6 M30.2 65.4 Q10.4 65.4 10.4 56.2 Q12 48.8 20.4 50.4 Q25 55.6 20 59.2', 0.5],
      ['c', 'kraft', 'M52 16.4 Q57 16.6 56.4 21.4 M46 62 Q50.6 61.4 51.4 65.6', 1.5],
    ],
    small: [
      ['c', 'kraft', 'M28 27 Q10 27 9.6 18.4 Q11 11.4 19 13 Q23 17.4 18 20 M56.4 46.4 Q38 46.4 38 38 Q39.4 32 46.4 33.4 Q50 37.4 45.6 39.6', 1.5],
      ['c', 'pencil', 'M28 28.4 Q8 28.6 8 18.2 Q9.6 9.8 19.6 11.6 Q24.4 16.6 18.6 21.4 M56.6 47.8 Q36.4 48 36.4 37.8 Q38 30.4 46.8 32 Q51.4 37.2 46 40.6', 0.9],
    ],
  },
  scribble: {
    grid: [64, 72],
    nibK: 0.03,
    tags: ['loading', 'draw', 'busy', 'progress', 'writing'],
    parts: [['c', 'pencil', loopsPath(6, 44, 48, 9.4, 6, 20, 4.8), 0.75]],
    small: [['c', 'pencil', loopsPath(7, 44, 46, 10.4, 4, 18, 5.8), 1.2]],
  },
})

const tipAt = (rot: number, dx: number): P => {
  const a = (rot * Math.PI) / 180
  return [32.4 + 63.2 * BODY_K * Math.sin(a) + dx, 67.4 - 63.2 * BODY_K * Math.cos(a)]
}

export function writeDef(frame: 0 | 1 | 2): ArtDef {
  const rot = [11, 13, 15][frame]
  const dx = [-9.4, -8.6, -7.8][frame]
  const t = tipAt(rot, dx)
  return pose({ face: { eyes: 'squint', mouth: 'tongue' }, turn: { rot, dx }, acc: scribble(t[0] + 1.8, t[1] + 2.4, [0.42, 0.72, 1][frame]), tags: ['busy', 'loading', 'progress', 'typing', 'draw'] })
}

export function waveDef(frame: 0 | 1 | 2): ArtDef {
  return pose({ face: { eyes: 'dot', look: [1.2, -0.6], mouth: 'grin' }, turn: { rot: [-7, -9.5, -5.5][frame] }, acc: waveMarks(frame), tags: ['hello', 'welcome', 'greet', 'hi'] })
}

export function celebrateDef(frame: 0 | 1): ArtDef {
  const turn: Xf = frame === 0 ? { k: 0.93, dy: -2.6, rot: 3 } : { sx: 1.04, sy: 0.95, rot: -1 }
  return pose({ face: { eyes: 'happy', mouth: 'grin' }, turn, acc: confetti(frame), hi: xf(confettiHi, { dy: frame * 2.4 }), tags: ['success', 'done', 'yay', 'hooray', 'all done'] })
}

export const frames = defineMascot({
  'write-1': writeDef(0),
  'write-2': writeDef(1),
  'write-3': writeDef(2),
  'wave-1': waveDef(0),
  'wave-2': waveDef(1),
  'wave-3': waveDef(2),
  'celebrate-1': celebrateDef(0),
  'celebrate-2': celebrateDef(1),
})
