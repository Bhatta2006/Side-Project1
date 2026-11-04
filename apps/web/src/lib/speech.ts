/**
 * Read a lesson aloud with the browser's own speech synthesis: no key, nothing uploaded,
 * nothing stored. Long utterances stop silently in some browsers (Chrome cuts them after
 * about 15 seconds), so the text is spoken in sentence-sized chunks.
 */

/** Sentence-sized pieces of at most `max` characters, in order, never empty. */
export function speakableChunks(text: string, max = 220): string[] {
  const clean = text.replace(/\s+/g, ' ').trim();
  if (!clean) return [];
  const sentences = clean.match(/[^.!?]+[.!?]+["')\]]*\s*|[^.!?]+$/g) ?? [clean];
  const out: string[] = [];
  let current = '';
  const push = (piece: string) => {
    if (piece.trim()) out.push(piece.trim());
  };
  for (const sentence of sentences) {
    if (sentence.length > max) {
      push(current);
      current = '';
      // A very long sentence is split at commas, then at spaces.
      let rest = sentence;
      while (rest.length > max) {
        const window = rest.slice(0, max);
        const cut = Math.max(window.lastIndexOf(', '), window.lastIndexOf(' '));
        const at = cut > max / 3 ? cut + 1 : max;
        push(rest.slice(0, at));
        rest = rest.slice(at);
      }
      current = rest;
    } else if ((current + sentence).length > max) {
      push(current);
      current = sentence;
    } else {
      current += sentence;
    }
  }
  push(current);
  return out;
}

/**
 * The words of a rendered lesson worth hearing: code listings, the self-check answers
 * (inside <details>), and anything marked aria-hidden are left out.
 */
export function lessonText(root: HTMLElement): string {
  const copy = root.cloneNode(true) as HTMLElement;
  copy.querySelectorAll('pre, details, [aria-hidden="true"], script, style, button').forEach(n => n.remove());
  return copy.innerText || copy.textContent || '';
}

export function canSpeak(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window && typeof SpeechSynthesisUtterance !== 'undefined';
}
