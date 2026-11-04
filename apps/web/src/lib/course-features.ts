import type { CourseFeatures, CourseShape } from './types';

/**
 * What the learner's course offers. Every page asks this instead of assuming a programming
 * course: a children's math course has no code editor, no language choice, no company
 * questions and no Codeforces; its Practice is a set of questions written for it.
 *
 * The API sends `features`; for an older API we derive the same answer from the course id
 * and shape (company questions belong to DSA alone).
 */
export function featuresFor(course: string | null | undefined, shape?: CourseShape | null, sent?: CourseFeatures): CourseFeatures {
  if (sent) return sent;
  const code = !shape || shape.studio === 'code';
  const library = code && !!course && ['zero', 'dsa', 'cp'].includes(course);
  return {
    code,
    library,
    companies: code && course === 'dsa',
    codeforces: code && (course === 'dsa' || course === 'cp'),
    drills: !!course && !library,
  };
}

/** Where the Practice slot opens for this course. */
export function practiceHref(features: CourseFeatures): string {
  return features.library ? '/library' : '/studio';
}
