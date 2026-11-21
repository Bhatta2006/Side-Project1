/**
 * Where maths sits in a line of lesson text: `$...$` and `\(...\)` inline, `$$...$$` and
 * `\[...\]` display. A lone `$` follows pandoc's rule so prices stay text: the opening `$` has
 * a non-space on its right, the closing one a non-space on its left and no digit after it
 * ("$5 and $10" is not maths). Code spans win over maths, so `` `$x$` `` stays code.
 */
export type Piece = { kind: 'text' | 'code'; text: string } | { kind: 'math'; tex: string; display: boolean };

export const MATH_OR_CODE = /(`[^`]+`)|(?<!\\)\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)|(?<![\\$])\$(?=[^\s$])((?:\\\$|[^$\n])*?[^\s\\])\$(?![\d$])/g;

export function pieces(text: string): Piece[] {
  const out: Piece[] = [];
  let last = 0;
  for (const m of text.matchAll(MATH_OR_CODE)) {
    if (m.index > last) out.push({ kind: 'text', text: text.slice(last, m.index) });
    if (m[1]) out.push({ kind: 'code', text: m[1].slice(1, -1) });
    else out.push({ kind: 'math', tex: (m[2] ?? m[3] ?? m[4] ?? m[5]).trim(), display: Boolean(m[2] ?? m[3]) });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ kind: 'text', text: text.slice(last) });
  return out;
}

/** A display formula standing alone (`$$...$$` or `\[...\]`, an optional full stop after), else null. */
export function displayMath(block: string): string | null {
  const m = block.trim().match(/^(?:\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\])\s*[.,]?$/);
  return m ? (m[1] ?? m[2]).trim() : null;
}
