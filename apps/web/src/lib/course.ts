import { useSession } from '@/lib/session';
import type { CourseFeatures, CourseShape } from '@/lib/types';
import { featuresFor } from '@/lib/course-features';

export { featuresFor, practiceHref } from '@/lib/course-features';

/** No course yet (onboarding): nothing course-specific is offered. */
const NONE: CourseFeatures = { code: false, library: false, companies: false, codeforces: false, drills: false };

export function useCourse(): { course: string | null; shape: CourseShape | null; features: CourseFeatures; ready: boolean } {
  const { profile, loading } = useSession();
  const enrollment = profile?.enrollment ?? null;
  if (!enrollment) return { course: null, shape: null, features: NONE, ready: !loading };
  return {
    course: enrollment.course,
    shape: enrollment.shape ?? null,
    features: featuresFor(enrollment.course, enrollment.shape, enrollment.features),
    ready: true,
  };
}
