import type { CourseFeatures, CourseShape } from './types';

/**
 * What the learner's course offers. Every page asks this instead of assuming a programming
 * course: a children's math course has no code editor and no language choice; its Practice is
 * a set of questions written for it. A code editor follows the course's own shape (a code
 * studio), never a course id: every course is generated for the learner.
 */
export function featuresFor(course: string | null | undefined, shape?: CourseShape | null, sent?: CourseFeatures): CourseFeatures {
  if (sent) return sent;
  return {
    code: !shape || shape.studio === 'code',
    drills: !!course,
  };
}

/** Where the Practice slot opens: the same page for every course. */
export function practiceHref(_features?: CourseFeatures): string {
  return '/studio';
}
