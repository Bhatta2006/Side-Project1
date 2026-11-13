import { useId, type CSSProperties } from 'react';
import { cn } from '@/lib/utils';
import { SocStone } from './soc-pebble';

/**
 * Soc, the tutor: the waitlist mascot. A cartoon stone bust of Socrates, light speckled stone with a
 * soft, curly beard, a thick ink line around the dome and the pedestal, standing on a stack of blue,
 * red and yellow books. Vector throughout, so it stays crisp at any size and in both themes.
 *
 * `mood` changes the brows, eyes and mouth (and adds a small prop: a question mark, sparkles, z's).
 * `look` turns his gaze, from -1 to 1 on each axis, for pointer-following on the landing page.
 */
export type SocMood =
  | 'neutral'
  | 'worried'
  | 'curious'
  | 'thinking'
  | 'happy'
  | 'proud'
  | 'surprised'
  | 'confused'
  | 'sleepy'
  | 'wink'
  | 'angry';

type Look = { x: number; y: number };

const INK = '#111111';
const EDGE = '#8C8B86';

// Side hair and beard curls, back to front. Upper rows are drawn last so they sit in front.
const HAIR: [number, number, number][] = [
  [57, 136, 13], [52, 119, 13], [50, 102, 13], [53, 86, 12], [62, 72, 11],
  [177, 139, 13], [182, 122, 13], [183, 105, 13], [180, 89, 12], [172, 75, 11],
];
const BEARD: [number, number, number][] = [
  [98, 183, 11], [118, 184, 11],
  [84, 173, 13], [106, 176, 13], [128, 175, 13], [147, 169, 12],
  [70, 159, 14], [92, 163, 14], [114, 164, 14], [136, 162, 14], [157, 156, 13],
  [60, 143, 13], [80, 147, 14], [102, 149, 14], [124, 149, 14], [146, 146, 14], [166, 141, 13],
  [65, 127, 13], [86, 132, 13], [108, 135, 12], [130, 133, 13], [150, 130, 13], [167, 124, 12],
  [66, 110, 12], [161, 112, 12],
];

function Curl({ cx, cy, r, fill }: { cx: number; cy: number; r: number; fill: string }) {
  return (
    <g>
      <circle cx={cx} cy={cy} r={r} fill={fill} stroke={EDGE} strokeWidth="0.9" strokeOpacity="0.75" />
      <path d={`M${cx - r * 0.55} ${cy + r * 0.35}a${r * 0.7} ${r * 0.7} 0 0 0 ${r * 1.1} ${-r * 0.1}`} fill="none" stroke={EDGE} strokeWidth="0.8" strokeOpacity="0.45" strokeLinecap="round" />
    </g>
  );
}

type Brow = [number, number, number, number, number]; // x1 y1 x2 y2 bend (negative arches up)
const BROWS: Record<SocMood, [Brow, Brow]> = {
  worried: [[80, 54, 103, 53, -1], [127, 59, 150, 66, -5]],
  neutral: [[80, 56, 103, 54, -2], [127, 55, 150, 58, -2]],
  curious: [[80, 57, 103, 56, -1], [127, 49, 150, 52, -5]],
  thinking: [[80, 58, 103, 59, 1], [127, 52, 150, 49, -3]],
  happy: [[80, 52, 103, 49, -3], [127, 49, 150, 52, -3]],
  proud: [[80, 51, 103, 48, -3], [127, 48, 150, 51, -3]],
  surprised: [[80, 46, 103, 44, -4], [127, 44, 150, 46, -4]],
  confused: [[80, 50, 103, 55, -1], [127, 60, 150, 55, -1]],
  sleepy: [[80, 60, 103, 60, 0], [127, 60, 150, 60, 0]],
  wink: [[80, 55, 103, 53, -2], [127, 58, 150, 61, 1]],
  // Both brows slammed down toward the nose.
  angry: [[80, 50, 104, 60, 2], [126, 62, 150, 52, 2]],
};

function Brows({ mood }: { mood: SocMood }) {
  return (
    <>
      {BROWS[mood].map(([x1, y1, x2, y2, bend], i) => (
        <path key={i} d={`M${x1} ${y1}Q${(x1 + x2) / 2} ${(y1 + y2) / 2 + bend} ${x2} ${y2}`} fill="none" stroke={INK} strokeWidth="7" strokeLinecap="round" />
      ))}
    </>
  );
}

type EyeKind = 'open' | 'big' | 'smile' | 'closed';

function Eye({ cx, cy, kind }: { cx: number; cy: number; kind: EyeKind }) {
  if (kind === 'smile') return <path d={`M${cx - 7} ${cy + 2}q7 -9 14 0`} fill="none" stroke={INK} strokeWidth="4" strokeLinecap="round" />;
  if (kind === 'closed') return <path d={`M${cx - 7} ${cy}q7 5 14 0`} fill="none" stroke={INK} strokeWidth="4" strokeLinecap="round" />;
  const big = kind === 'big';
  return (
    <g>
      <ellipse cx={cx} cy={cy} rx={big ? 7 : 5.8} ry={big ? 9.5 : 7.8} fill={INK} />
      <circle cx={cx + 2} cy={cy - 2.8} r={big ? 2.4 : 1.9} fill="#fff" />
    </g>
  );
}

function Eyes({ mood }: { mood: SocMood }) {
  const [l, r]: [EyeKind, EyeKind] =
    mood === 'happy' || mood === 'proud' ? ['smile', 'smile']
      : mood === 'sleepy' ? ['closed', 'closed']
        : mood === 'surprised' ? ['big', 'big']
          : mood === 'wink' ? ['open', 'smile']
            : ['open', 'open'];
  // Thinking glances up and away; curious leans in.
  const shift = mood === 'thinking' ? 'translate(3 -3)' : mood === 'curious' ? 'translate(2 0)' : undefined;
  return (
    <g transform={shift}>
      <g className={l === 'open' || l === 'big' ? 'soc-eyes' : undefined}>
        <Eye cx={91} cy={81} kind={l} />
        <Eye cx={134} cy={85} kind={r} />
      </g>
    </g>
  );
}

function Mouth({ mood }: { mood: SocMood }) {
  switch (mood) {
    case 'worried':
      // The waitlist face: a small open trapezoid with the upper teeth showing.
      return (
        <g>
          <path d="M102.5 114.5l17-1.5l-2.5 10.5h-12z" fill={INK} stroke={INK} strokeWidth="1.6" strokeLinejoin="round" />
          <path d="M104 115.2l14-1.2l-0.6 2.6l-12.8 1.1z" fill="#D9D8D3" />
        </g>
      );
    case 'happy':
    case 'proud':
      return (
        <g>
          <path d="M99 114q12 1 24-1q-2 13-12 13t-12-12z" fill={INK} stroke={INK} strokeWidth="1.4" strokeLinejoin="round" />
          <path d="M104 121.5q7 3.5 14 0" fill="none" stroke="#E46A6A" strokeWidth="3" strokeLinecap="round" />
        </g>
      );
    case 'surprised':
      return <ellipse cx="111" cy="120" rx="6" ry="7.5" fill={INK} />;
    case 'curious':
      return <ellipse cx="112" cy="119" rx="4.2" ry="4.6" fill={INK} />;
    case 'thinking':
      return <path d="M103 120q6-1 16-4" fill="none" stroke={INK} strokeWidth="3.2" strokeLinecap="round" />;
    case 'confused':
      return <path d="M101 119q4-4 7 0t7 0t7 0" fill="none" stroke={INK} strokeWidth="3" strokeLinecap="round" />;
    case 'sleepy':
      return <ellipse cx="111" cy="119" rx="3.6" ry="2.6" fill={INK} />;
    case 'wink':
      return <path d="M101 116q11 9 21-1" fill="none" stroke={INK} strokeWidth="3.2" strokeLinecap="round" />;
    case 'angry':
      return <path d="M101 121q10-7 20 0" fill="none" stroke={INK} strokeWidth="3.4" strokeLinecap="round" />;
    default:
      return <path d="M101 116q10 7 20 0" fill="none" stroke={INK} strokeWidth="3.2" strokeLinecap="round" />;
  }
}

/** Small props that carry the mood beyond the face, in pen red, highlighter or ink. */
function Extras({ mood }: { mood: SocMood }) {
  if (mood === 'curious' || mood === 'confused') {
    return <text x="190" y="50" fontSize="40" fill="var(--pen)" style={{ fontFamily: 'var(--font-hand)' }} transform="rotate(12 198 40)">?</text>;
  }
  if (mood === 'thinking') {
    return (
      <g fill="#fff" stroke={INK} strokeWidth="2.5">
        <circle cx="186" cy="48" r="4" /><circle cx="198" cy="34" r="6" /><circle cx="214" cy="16" r="9" />
      </g>
    );
  }
  if (mood === 'proud' || mood === 'happy') {
    const star = (x: number, y: number, s: number) => (
      <path d={`M${x} ${y - s}Q${x + s * 0.18} ${y - s * 0.18} ${x + s} ${y}Q${x + s * 0.18} ${y + s * 0.18} ${x} ${y + s}Q${x - s * 0.18} ${y + s * 0.18} ${x - s} ${y}Q${x - s * 0.18} ${y - s * 0.18} ${x} ${y - s}Z`} fill="var(--highlight)" stroke={INK} strokeWidth="2" strokeLinejoin="round" />
    );
    return <g>{star(198, 40, 12)}{star(36, 52, 8)}{mood === 'proud' ? star(214, 80, 6) : null}</g>;
  }
  if (mood === 'sleepy') {
    return (
      <g fill="var(--pen)" style={{ fontFamily: 'var(--font-hand)' }}>
        <text x="184" y="56" fontSize="22">z</text>
        <text x="198" y="38" fontSize="30">z</text>
      </g>
    );
  }
  if (mood === 'angry') {
    // A cartoon anger mark by the temple, in pen red.
    return (
      <g stroke="var(--pen)" strokeWidth="4" strokeLinecap="round" fill="none" transform="translate(186 30)">
        <path d="M0 8q8 0 8-8" /><path d="M14 0q0 8 8 8" /><path d="M22 14q-8 0-8 8" /><path d="M8 22q0-8-8-8" />
      </g>
    );
  }
  if (mood === 'surprised') {
    return <g stroke="var(--pen)" strokeWidth="3" strokeLinecap="round"><path d="M34 44l10 10" /><path d="M26 66h13" /><path d="M200 44l-10 10" /><path d="M208 66h-13" /></g>;
  }
  return null;
}

/** One book: chunky, angled ends, black sides, a pale page block. */
function Book({ x, y, w, h, color, chamfer = 10 }: { x: number; y: number; w: number; h: number; color: string; chamfer?: number }) {
  const body = `${x},${y} ${x + w - chamfer},${y} ${x + w},${y + chamfer * 0.6} ${x + w},${y + h} ${x + chamfer * 0.9},${y + h} ${x},${y + h - chamfer * 0.7}`;
  return (
    <g strokeLinejoin="round">
      <polygon points={body} transform="translate(3 3)" fill={INK} />
      <polygon points={body} fill={color} stroke={INK} strokeWidth="2" />
      <rect x={x + chamfer + 8} y={y + h * 0.3} width={w - chamfer - 14} height={h * 0.5} fill="#E3E3E1" stroke={INK} strokeWidth="1.2" />
    </g>
  );
}

function Books() {
  return (
    <g>
      <Book x={6} y={262} w={218} h={42} color="#E2D766" chamfer={14} />
      <Book x={20} y={250} w={190} h={30} color="#E8141C" />
      <Book x={10} y={226} w={206} h={34} color="#0B2FE4" chamfer={14} />
    </g>
  );
}

/** The original stone bust on books, kept so the old Soc is one line away. */
export function SocBust({
  mood = 'neutral',
  books = false,
  look,
  idle = false,
  size,
  className,
  style,
  title,
}: {
  mood?: SocMood;
  books?: boolean;
  look?: Look;
  idle?: boolean;
  /** Width in px. Height follows the figure's proportions. */
  size?: number;
  className?: string;
  style?: CSSProperties;
  /** An accessible name. Without one the figure is decorative. */
  title?: string;
}) {
  const id = useId().replace(/[:«»]/g, '');
  const texture = !size || size >= 96;
  const lx = Math.max(-1, Math.min(1, look?.x ?? 0));
  const ly = Math.max(-1, Math.min(1, look?.y ?? 0));
  // Small avatars drop the pedestal and crop to the head, so the face stays legible.
  const bust = books || !size || size >= 72;
  const box = books ? '0 6 234 306' : bust ? '0 6 234 236' : '34 14 170 178';
  const [, , bw, bh] = box.split(' ').map(Number);
  const curl = `url(#curl-${id})`;
  const stone = `url(#stone-${id})`;
  // Heavier ink as the figure shrinks, so the outline holds at avatar sizes.
  const outline = size && size < 72 ? 4.5 : 2.8;
  return (
    <svg
      viewBox={box}
      width={size}
      height={size ? (size * bh) / bw : undefined}
      className={cn('block select-none', className)}
      style={style}
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      focusable="false"
    >
      <defs>
        <radialGradient id={`curl-${id}`} cx="38%" cy="32%" r="70%">
          <stop offset="0" stopColor="#E4E3DF" />
          <stop offset="0.6" stopColor="#CFCECA" />
          <stop offset="1" stopColor="#ADACA7" />
        </radialGradient>
        <radialGradient id={`dome-${id}`} cx="42%" cy="30%" r="75%">
          <stop offset="0" stopColor="#DCDBD7" />
          <stop offset="0.75" stopColor="#CDCCC8" />
          <stop offset="1" stopColor="#B9B8B3" />
        </radialGradient>
        <radialGradient id={`base-${id}`} cx="45%" cy="30%" r="80%">
          <stop offset="0" stopColor="#D6D5D1" />
          <stop offset="0.8" stopColor="#C6C5C1" />
          <stop offset="1" stopColor="#ABAAA5" />
        </radialGradient>
        {texture ? (
          <filter id={`stone-${id}`} x="0" y="0" width="100%" height="100%">
            <feTurbulence type="fractalNoise" baseFrequency="1.2" numOctaves="2" seed="11" result="noise" />
            <feColorMatrix in="noise" type="matrix" values="0 0 0 0 0.45  0 0 0 0 0.45  0 0 0 0 0.43  0 0 0 -3.2 1.45" result="speck" />
            <feComposite in="speck" in2="SourceGraphic" operator="in" result="specks" />
            <feBlend in="SourceGraphic" in2="specks" mode="multiply" />
          </filter>
        ) : null}
      </defs>
      {books ? <Books /> : null}
      <g className={idle ? 'soc-idle' : undefined}>
        <g className="soc-head" style={{ transform: `rotate(${lx * 2.5}deg)`, transformOrigin: '114px 205px' }}>
          <g filter={texture ? stone : undefined}>
            {bust ? (
              <>
                <ellipse cx="114" cy="204" rx="83" ry="32" fill={`url(#base-${id})`} stroke={INK} strokeWidth={outline} />
                <path d="M44 214q70 28 142 0" fill="none" stroke="#A9A8A3" strokeWidth="3" strokeLinecap="round" opacity="0.7" />
              </>
            ) : null}
            <ellipse cx="117" cy="98" rx="63" ry="76" fill={`url(#dome-${id})`} stroke={INK} strokeWidth={outline} />
            {/* A shadowed mass behind the curls, so the gaps between them read as deep crevices */}
            <g fill="#9E9D98">
              {[...HAIR, ...BEARD].map(([cx, cy, r]) => <circle key={`s${cx}-${cy}`} cx={cx + 1} cy={cy + 1.5} r={r * 0.92} />)}
            </g>
            {HAIR.map(([cx, cy, r]) => <Curl key={`h${cx}-${cy}`} cx={cx} cy={cy} r={r} fill={curl} />)}
            {BEARD.map(([cx, cy, r]) => <Curl key={`b${cx}-${cy}`} cx={cx} cy={cy} r={r} fill={curl} />)}
          </g>
          <g className="soc-look" style={{ transform: `translate(${lx * 4}px, ${ly * 3}px)` }}>
            <Mouth mood={mood} />
            {/* Moustache: two soft curls sweeping out from under the nose */}
            <g filter={texture ? stone : undefined}>
              <ellipse cx="97" cy="108" rx="17" ry="7" transform="rotate(-10 97 108)" fill={curl} stroke={EDGE} strokeWidth="1" />
              <ellipse cx="128" cy="110" rx="17" ry="7" transform="rotate(12 128 110)" fill={curl} stroke={EDGE} strokeWidth="1" />
              <circle cx="113" cy="96" r="10.5" fill={curl} stroke={EDGE} strokeWidth="1.1" />
            </g>
            <Eyes mood={mood} />
            <Brows mood={mood} />
          </g>
        </g>
        <Extras mood={mood} />
      </g>
    </svg>
  );
}

/**
 * Soc as drawn across the app: the round granite pebble (Socrates trained as a stonemason).
 * Same props as before, so every caller keeps working: `books` sets him on a notebook page,
 * `look` turns his eyes, small sizes crop to the stone.
 */
export function SocFigure(props: {
  mood?: SocMood;
  books?: boolean;
  look?: Look;
  idle?: boolean;
  /** No motion at all (see SocStone). */
  still?: boolean;
  /** Width in px. Height follows the figure's proportions. */
  size?: number;
  className?: string;
  style?: CSSProperties;
  /** An accessible name. Without one the figure is decorative. */
  title?: string;
}) {
  return <SocStone {...props} />;
}
