import type { ActivityKind, CourseFeatures } from './types';

/** Activity ids look like `lesson:zero:variables-and-types`; URLs use path segments. */
export function activityHref(id: string): string {
  const [kind, ...rest] = id.split(':');
  if (kind === 'lesson') return `/learn/${rest.join('/')}`;
  if (kind === 'problem') return `/problems/${rest.join('/')}`;
  if (kind === 'transfer') return `/transfer/${rest.join('/')}`;
  // Support steps live on the concept's lesson page, which shows the step on top.
  if (SUPPORT_STEPS.includes(kind)) return `/learn/${rest.join('/')}?step=${kind}`;
  if (kind === 'quiz') return `/quiz/${rest.join('/')}`; // concept checks: /quiz/zero/programs-and-output
  return `/quiz/${kind}/${rest.join('/')}`;
}

/** Kinds that appear as the first URL segment under /quiz; anything else is a concept check. */
export const QUIZ_KINDS = ['checkpoint', 'review', 'remedial', 'probe', 'testout', 'moduletest'];

/** Activities that open on the lesson page and that the learner marks done themselves. */
export const SUPPORT_STEPS = ['example', 'explain', 'checkin', 'stretch'];

export function conceptHref(qualified: string): string {
  return `/learn/${qualified.split(':').join('/')}`;
}

export function joinSegments(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value.map(decodeURIComponent).join(':') : decodeURIComponent(value ?? '');
}

/**
 * Canonical names, used in navigation, titles, breadcrumbs, search and buttons. Routes keep
 * their paths; only labels and grouping changed in the redesign.
 */
export const NAME = {
  today: 'Today',
  skills: 'Skills',
  practice: 'Practice',
  playground: 'Playground',
  evidence: 'Evidence',
  settings: 'Settings',
  problems: 'Problems',
  practiceSets: 'Practice sets',
  companies: 'Company questions',
  sprint: 'Focus sprint',
  companySprint: 'Company sprint',
  passport: 'Skill Passport',
  assessment: 'Weekly assessment',
} as const;

export type NavKey = 'today' | 'skills' | 'practice' | 'playground' | 'evidence' | 'settings';

/** Six destinations. Each lists the routes that live under it, for the active state. */
export const NAV: { key: NavKey; href: string; label: string; owns: string[] }[] = [
  { key: 'today', href: '/today', label: NAME.today, owns: ['/today'] },
  { key: 'skills', href: '/plan', label: NAME.skills, owns: ['/plan', '/graph', '/learn', '/quiz', '/transfer'] },
  { key: 'practice', href: '/library', label: NAME.practice, owns: ['/library', '/companies', '/company-sprint', '/sprint', '/problems', '/studio'] },
  { key: 'playground', href: '/playground', label: NAME.playground, owns: ['/playground'] },
  { key: 'evidence', href: '/progress', label: NAME.evidence, owns: ['/progress', '/assessments'] },
  { key: 'settings', href: '/settings', label: NAME.settings, owns: ['/settings'] },
];

/**
 * The six destinations, the same for every course. Practice always opens the one Practice page
 * (practice sets written for the course, then whatever extras it has); a course with its own
 * studio (Workbench, Lab, Notebook) gives the slot its name.
 */
export function navItems(shape?: { studio: string; name: string } | null, _features?: CourseFeatures | null): typeof NAV {
  const label = shape && shape.studio !== 'code' ? shape.name : NAME.practice;
  return NAV.map(item => (item.key === 'practice' ? { ...item, href: '/studio', label } : item));
}

/**
 * Practice is the same page for every course. Practice sets (questions written for the course)
 * come first everywhere; a programming course adds its problem library and sprints, and DSA
 * its company questions. Each segment is a real route.
 */
export const PRACTICE_SEGMENTS: { href: string; label: string; needs: keyof CourseFeatures }[] = [
  { href: '/studio', label: NAME.practiceSets, needs: 'drills' },
  { href: '/library', label: NAME.problems, needs: 'library' },
  { href: '/companies', label: NAME.companies, needs: 'companies' },
  { href: '/company-sprint', label: NAME.companySprint, needs: 'companies' },
  { href: '/sprint', label: NAME.sprint, needs: 'library' },
];

/** Routes that belong to one kind of course; another course is sent to its own Practice. */
export const COURSE_ROUTES: { root: string; needs: keyof CourseFeatures }[] = [
  { root: '/library', needs: 'library' },
  { root: '/sprint', needs: 'library' },
  { root: '/companies', needs: 'companies' },
  { root: '/company-sprint', needs: 'companies' },
  { root: '/problems', needs: 'code' },
];

export function navFor(pathname: string): NavKey | null {
  return NAV.find(item => item.owns.some(root => pathname === root || pathname.startsWith(`${root}/`)))?.key ?? null;
}

export const KIND_LABEL: Record<ActivityKind, string> = {
  lesson: 'Lesson',
  quiz: 'Concept check',
  problem: 'Practice',
  checkpoint: 'Checkpoint',
  review: 'Review',
  remedial: 'Refresher',
  probe: 'Foundations check',
  testout: 'Test-out',
  moduletest: 'Module test-out',
  example: 'Worked example',
  explain: 'Another explanation',
  checkin: 'Talk it through',
  stretch: 'Stretch',
  transfer: 'Transfer check',
};

export const STYLE_LABEL = {
  thorough: 'Thorough',
  balanced: 'Balanced',
  fast_track: 'Fast track',
  goal_focused: 'Goal focused',
} as const;

export const LANGUAGE_LABEL = { python: 'Python', cpp: 'C++', java: 'Java' } as const;

export const BAND_LABEL = {
  not_started: 'Not started',
  needs_practice: 'Still building',
  developing: 'Developing',
  likely_known: 'Likely known',
  strong: 'Strong',
} as const;

export const PACE_LABEL = { support: 'Extra support', steady: 'Steady', fast: 'Fast track' } as const;

export function formatDate(iso: string, options: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' }) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, options);
}

export function formatStamp(seconds: number) {
  return new Date(seconds * 1000).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}

export function hours(minutes: number) {
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `${h} h ${m} min` : `${h} h`;
}
