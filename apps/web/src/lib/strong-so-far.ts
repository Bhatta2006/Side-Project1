/**
 * The mastery estimate (band) can say "strong" before the evidence has shown the skill without
 * help, lasting, or in a new setting (evidence stage below "demonstrated", master prompt 9.2 and
 * 9.3). The lesson page must not call that "Mastered": it says "Strong so far" until the
 * evidence supports more. Without evidence data the band alone decides, as before.
 */
export function strongSoFar(concept: { band: string; evidence?: { stage: string } | null }): boolean {
  return concept.band === 'strong' && concept.evidence != null && concept.evidence.stage !== 'demonstrated';
}
