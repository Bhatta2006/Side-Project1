import { cn } from '@/lib/utils';
import { SocFigure, type SocMood } from '@/components/socrat/soc';

/**
 * Notebook doodles: ink line drawings over offset blocks of the book colours (blue, red, yellow),
 * like a risograph print that slipped a little in registration. The ink draws itself in as the
 * doodle scrolls into view (CSS scroll-driven animation; static where unsupported or with reduced
 * motion), or on load with `draw="load"`. Never contain text that must be read.
 */
export type IllustrationName = 'stack' | 'orbit' | 'welcome' | 'ladder' | 'empty' | 'bulb' | 'target' | 'plane';

const INK = 'var(--illo-line)';
const BLUE = 'var(--book-blue)';
const RED = 'var(--book-red)';
const YELLOW = 'var(--highlight)';

/** An ink stroke that draws in. */
function Ink({ d, w = 2.6, dash }: { d: string; w?: number; dash?: boolean }) {
  return <path d={d} pathLength={dash ? undefined : 1} data-ink={dash ? undefined : ''} fill="none" stroke={INK} strokeWidth={w} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={dash ? '3 7' : undefined} />;
}
/** A flat colour block, printed slightly off the ink line. */
function Fill({ d, color, dx = 5, dy = 4 }: { d: string; color: string; dx?: number; dy?: number }) {
  return <path d={d} fill={color} data-fill="" transform={`translate(${dx} ${dy})`} />;
}
function Spark({ x, y, s = 9, color = YELLOW }: { x: number; y: number; s?: number; color?: string }) {
  const d = `M${x} ${y - s}Q${x + s * 0.2} ${y - s * 0.2} ${x + s} ${y}Q${x + s * 0.2} ${y + s * 0.2} ${x} ${y + s}Q${x - s * 0.2} ${y + s * 0.2} ${x - s} ${y}Q${x - s * 0.2} ${y - s * 0.2} ${x} ${y - s}Z`;
  return <><Fill d={d} color={color} dx={2} dy={2} /><Ink d={d} w={2} /></>;
}

function Plane() {
  const wing = 'M30 122L206 52L132 186L112 142Z';
  return (
    <>
      <Ink d="M24 214c30-6 40-34 18-40s-26 26 4 30c40 6 58-30 70-56" dash />
      <Fill d={wing} color={BLUE} />
      <Ink d={wing} />
      <Ink d="M112 142L206 52" />
      <Ink d="M112 142l-4 34 24 10" w={2.2} />
      <Spark x={196} y={150} s={11} />
      <Spark x={60} y={60} s={7} color={RED} />
    </>
  );
}

function Welcome() {
  // A notebook page with a highlighted line and Soc's question mark.
  const page = 'M44 46h132a10 10 0 0 1 10 10v140a10 10 0 0 1-10 10H44Z';
  return (
    <>
      <Fill d={page} color={BLUE} dx={7} dy={6} />
      <path d={page} fill="var(--card)" />
      <Ink d={page} />
      <path d="M68 92h86" stroke={YELLOW} strokeWidth="14" strokeLinecap="round" opacity="0.9" />
      {[92, 118, 144, 170].map(y => <Ink key={y} d={`M68 ${y}h${y === 92 ? 86 : y === 170 ? 52 : 92}`} w={2} />)}
      <Ink d="M58 46v160" w={1.6} />
      <text x="188" y="72" fontSize="54" fill={RED} style={{ fontFamily: 'var(--font-hand)' }} transform="rotate(10 198 56)">?</text>
      <Spark x={30} y={194} s={8} />
    </>
  );
}

function Orbit() {
  return (
    <>
      <Ink d="M44 120c0-30 34-50 76-50s76 20 76 50-34 50-76 50-76-20-76-50Z" w={2} dash />
      <Ink d="M80 54c26-14 70 14 98 62s28 92 2 106-70-14-98-62-28-92-2-106Z" w={2} dash />
      <Fill d="M102 88c-12 0-12 8-12 16s0 14-8 16c8 2 8 8 8 16s0 16 12 16" color={YELLOW} dx={4} dy={3} />
      <Ink d="M102 88c-12 0-12 8-12 16s0 14-8 16c8 2 8 8 8 16s0 16 12 16" w={3} />
      <Ink d="M138 88c12 0 12 8 12 16s0 14 8 16c-8 2-8 8-8 16s0 16-12 16" w={3} />
      <circle cx="196" cy="120" r="11" fill={BLUE} data-fill="" />
      <circle cx="80" cy="54" r="8" fill={RED} data-fill="" />
      <circle cx="180" cy="222" r="7" fill={YELLOW} data-fill="" />
      <Ink d="M196 109a11 11 0 1 1 0 22a11 11 0 1 1 0-22" w={2} />
    </>
  );
}

function Stack() {
  const books: [number, number, number, string, number][] = [[40, 170, 150, YELLOW, -2], [56, 138, 128, RED, 2], [46, 104, 140, BLUE, -3]];
  return (
    <>
      {books.map(([x, y, w, color, r]) => {
        const d = `M${x} ${y}h${w}v30H${x}Z`;
        return (
          <g key={y} transform={`rotate(${r} ${x + w / 2} ${y + 15})`}>
            <Fill d={d} color={color} />
            <Ink d={d} />
            <Ink d={`M${x + 16} ${y + 10}h${w - 26}M${x + 16} ${y + 20}h${w - 40}`} w={1.6} />
          </g>
        );
      })}
      {/* A pencil leaning on the stack */}
      <Fill d="M186 34l20 10-36 84-20-10Z" color={YELLOW} dx={3} dy={3} />
      <Ink d="M186 34l20 10-36 84-20-10ZM150 118l-6 22 16-12" />
      <Spark x={34} y={70} s={8} color={RED} />
    </>
  );
}

function Ladder() {
  const steps: [number, number, string][] = [[34, 150, YELLOW], [92, 110, RED], [150, 70, BLUE]];
  return (
    <>
      {steps.map(([x, y, color]) => {
        const d = `M${x} ${y}h50V${206}H${x}Z`;
        return <g key={x}><Fill d={d} color={color} /><Ink d={d} /></g>;
      })}
      <Ink d="M175 70V30" />
      <Fill d="M175 30l30 9-30 9Z" color={RED} dx={2} dy={2} />
      <Ink d="M175 30l30 9-30 9" w={2.2} />
      <Ink d="M22 128c30-50 80-84 136-96" w={2} dash />
      <Ink d="M20 206h204" w={2} />
    </>
  );
}

function Empty() {
  // An open notebook, a pencil and an unanswered question.
  const left = 'M120 70c-24-12-52-14-80-8v118c28-6 56-4 80 8Z';
  const right = 'M120 70c24-12 52-14 80-8v118c-28-6-56-4-80 8Z';
  return (
    <>
      <Fill d={`${left}${right}`} color={BLUE} dx={6} dy={6} />
      <path d={`${left}${right}`} fill="var(--card)" />
      <Ink d={left} />
      <Ink d={right} />
      {[96, 116, 136, 156].map(y => <Ink key={y} d={`M54 ${y - 4}c20-3 40-2 56 4M134 ${y}c16-6 36-7 56-4`} w={1.4} />)}
      <text x="150" y="58" fontSize="46" fill={RED} style={{ fontFamily: 'var(--font-hand)' }} transform="rotate(8 160 42)">?</text>
      <Fill d="M60 210l100-30 4 12-100 30Z" color={YELLOW} dx={2} dy={2} />
      <Ink d="M60 210l100-30 4 12-100 30ZM60 210l-14 10 18 2" w={2.2} />
    </>
  );
}

function Bulb() {
  const glass = 'M120 40c-34 0-58 26-58 58 0 22 12 36 24 48 6 6 8 12 8 20h52c0-8 2-14 8-20 12-12 24-26 24-48 0-32-24-58-58-58Z';
  return (
    <>
      <Fill d={glass} color={YELLOW} />
      <Ink d={glass} />
      <Ink d="M98 182h44M102 198h36M110 212h20" />
      <Ink d="M108 150c-4-20 4-40 12-50 8 10 16 30 12 50" w={2} />
      {[[40, 60, 22, 48], [200, 60, 218, 48], [30, 110, 12, 110], [210, 110, 228, 110], [52, 160, 38, 172], [188, 160, 202, 172]].map(([x1, y1, x2, y2]) => (
        <Ink key={`${x1}${y1}`} d={`M${x1} ${y1}L${x2} ${y2}`} w={2.4} />
      ))}
      <Spark x={196} y={210} s={8} color={BLUE} />
    </>
  );
}

function Target() {
  return (
    <>
      <circle cx="118" cy="126" r="78" fill={RED} data-fill="" transform="translate(5 4)" />
      <circle cx="118" cy="126" r="78" fill="var(--card)" />
      <Ink d="M118 48a78 78 0 1 1 0 156a78 78 0 1 1 0-156" />
      <circle cx="118" cy="126" r="50" fill={YELLOW} data-fill="" transform="translate(4 3)" />
      <Ink d="M118 76a50 50 0 1 1 0 100a50 50 0 1 1 0-100" />
      <circle cx="118" cy="126" r="20" fill={BLUE} data-fill="" />
      <Ink d="M118 106a20 20 0 1 1 0 40a20 20 0 1 1 0-40" />
      <Ink d="M120 124L212 36M212 36l-22 2M212 36l-2 22M200 48l-18-2M200 48l-2 18" w={2.6} />
    </>
  );
}

const DRAW: Record<IllustrationName, () => React.ReactNode> = {
  welcome: Welcome, orbit: Orbit, stack: Stack, ladder: Ladder, empty: Empty, bulb: Bulb, target: Target, plane: Plane,
};

export function Illustration({ name, className, draw = 'scroll' }: { name: IllustrationName; className?: string; proof?: boolean; draw?: 'scroll' | 'load' | 'none' }) {
  const Drawing = DRAW[name];
  return (
    <svg viewBox="0 0 240 240" className={cn('doodle block overflow-visible', draw !== 'none' && `doodle-${draw}`, className)} aria-hidden="true" focusable="false">
      <Drawing />
    </svg>
  );
}

/**
 * Soc, the tutor: the stone bust (see soc.tsx), sized as an avatar. Decorative unless `label` is
 * given (only where it acts as a control). Inside a button or link, Soc nods when it is hovered or
 * focused (see .soc-avatar in globals.css). `mood` matches the moment: happy on a pass, thinking
 * while he waits, worried on an error.
 */
export function Soc({ size = 48, className, label, mood = 'neutral' }: { size?: number; className?: string; label?: string; mood?: SocMood }) {
  return <SocFigure size={size} mood={mood} title={label} className={cn('soc-avatar flex-none', className)} />;
}
