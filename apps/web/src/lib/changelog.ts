/**
 * The public change log (/changelog): who reported bugs or asked for features that were then
 * fixed or built. Each person gets one line: how many of their reports shipped, and the single
 * most important one. The individual reports are deliberately not listed.
 *
 * To credit someone, add them here (or raise their count), spelled the way they want to be
 * credited, and bump UPDATED.
 */
export interface Contributor {
  name: string;
  /** How many of this person's reports were fixed or built. */
  reports: number;
  /** The one that mattered most, as a short plain phrase. */
  major: string;
}

/** ISO date of the last change to this list. */
export const UPDATED = '2026-11-14';

export const CONTRIBUTORS: Contributor[] = [
  { name: 'Abhay J Kashyap', reports: 7, major: 'Pages that lagged on slower phones and laptops now run smoothly' },
];
