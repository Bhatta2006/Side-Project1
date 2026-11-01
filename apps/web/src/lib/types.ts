export type Language = 'python' | 'cpp' | 'java';
export type Band = 'not_started' | 'needs_practice' | 'developing' | 'likely_known' | 'strong';
export type Pace = 'support' | 'steady' | 'fast';

/** How a course is practised and evidenced; code is the default for programming courses. */
export interface CourseShape {
  studio: 'code' | 'workbench' | 'lab' | 'reading';
  loop: string;
  evidence: string[];
  tools: string[];
  name: string;
}

export interface Enrollment {
  id: string;
  course: string;
  language: Language;
  status: 'placement' | 'active';
  minutes_per_day: number;
  weekdays: number[];
  goal: Record<string, string | number>;
  level: string;
  /** Only sent for accounts the studios are enabled for; absent means a programming course. */
  shape?: CourseShape | null;
}

export interface Profile {
  id: string;
  admin: boolean;
  display_name: string | null;
  birth_year: number | null;
  timezone: string | null;
  csrf_token: string;
  onboarded: boolean;
  tour_seen: boolean;
  enrollment: Enrollment | null;
}

export type PlanId = 'free' | 'plus' | 'pro';
export interface BillingStatus {
  enabled: boolean;
  plan: PlanId;
  usage: Record<'chat' | 'playground', { limit: number; used: number; window: 'day' | 'week' }>;
  free_concepts: string[] | null;
  renews_at: number | null;
  cancel_at_period_end: boolean;
  prices: Record<'plus' | 'pro', Record<'month' | 'year', Record<'INR' | 'USD', number>>>;
}

export interface Features {
  dev_login: boolean;
  oidc_login: boolean;
  email_login?: boolean;
  ai_provider: 'anthropic' | 'openai' | 'offline';
  code_execution: boolean;
  execution_backend: string;
  demo_mode: boolean;
  /** WhatsApp community invite for beta learners; null hides it. */
  community_url?: string | null;
  try_tutor?: boolean;
  adaptive_quiz?: boolean;
}

export interface Course {
  id: string;
  title: string;
  tagline: string;
  description: string;
  languages: Language[];
  levels: { id: string; label: string; description: string }[];
  modules: { id: string; title: string; summary: string; concepts: number }[];
  concept_count: number;
  problem_count: number;
}

export interface PlacementQuestion {
  done: boolean;
  asked: number;
  max_questions?: number;
  question?: {
    id: string;
    topic: string;
    prompt: string;
    kind: string;
    code: string | null;
    options: string[];
  };
}

export interface PlacementSummary {
  asked: number;
  correct: number;
  known_concepts: string[];
  starting_concept: string | null;
}

export type ActivityKind =
  | 'lesson'
  | 'quiz'
  | 'problem'
  | 'checkpoint'
  | 'review'
  | 'remedial'
  | 'probe'
  | 'testout'
  | 'moduletest'
  | 'example'
  | 'explain'
  | 'checkin'
  | 'stretch'
  | 'transfer';

export interface Activity {
  id: string;
  kind: ActivityKind;
  concept: string;
  title: string;
  minutes?: number;
  reason?: string;
  /** Which adaptation put this here (see ReasonChip). */
  code?: ReasonCode;
  status?: 'done' | 'pending';
}

export type ReasonCode =
  | 'path' | 'assumed_confirm' | 'failed_check_refresh' | 'stuck_support' | 'review_due'
  | 'checkpoint' | 'checkpoint_retry' | 'chosen_testout' | 'probe' | 'approved_refresh' | 'stretch' | 'transfer';

/** A concept check or review served by the adaptive engine. */
export interface AdaptiveSession {
  id: string;
  engine: 'adaptive';
  mode: string;
  concepts: string[];
  served: number;
  max_items: number;
  finished: boolean;
  stop_reason: 'max_items' | 'ceiling' | 'stable' | 'exhausted' | 'needs_lesson' | 'strikes' | null;
  score?: number | null;
  passed?: boolean | null;
  /** Test-out: the hardest band on offer and unaided corrects there. */
  hard_band?: number | null;
  hard_correct?: number | null;
  hard_needed?: number | null;
  /** Test-out answered well but the bank was too small to prove it: a transfer check decides. */
  needs_transfer?: boolean | null;
  /** Once finished: each answer's band, result and seconds. */
  results?: { band: number; correct: boolean; seconds: number }[] | null;
  current: {
    item: string;
    concept: string;
    pattern: string;
    format: string;
    band: number;
    prompt: string;
    code: string | null;
    options: string[];
    /** Why this difficulty was chosen (engine ladder rule). */
    reason?: string | null;
    hints_used: number;
    hints_available: number;
    micro_lesson: { pattern: string; concept: string } | null;
  } | null;
}

export interface AdaptiveAnswer {
  /** 'recorded': a test-out, graded only at the end. */
  outcome: 'correct' | 'wrong' | 'skipped' | 'recorded';
  answer: number | null;
  explanation: string | null;
  misconception: string | null;
  session: AdaptiveSession;
}

export interface Revision {
  pace: Pace;
  reasons: string[];
  projected_finish: string;
  remaining_minutes: number;
  at: number;
  /** What this revision added to or removed from your queue. */
  changes?: { added?: string[]; removed?: string[] };
}

export type PathStyle = 'thorough' | 'balanced' | 'fast_track' | 'goal_focused';

/** A roadmap change Socrat suggests. Nothing changes until the learner accepts it. */
export interface Proposal {
  id: string;
  kind: string;
  title: string;
  reason: string;
  payload: Record<string, unknown>;
  group: string;
  source: 'planner' | 'tutor' | 'review' | 'company_sprint';
  status: 'pending' | 'accepted' | 'declined' | 'expired' | 'superseded';
  created_at: number;
  decided_at: number | null;
}

export interface ProposalsView {
  pending: Proposal[];
  recent: Proposal[];
  overrides: {
    defer?: string[];
    skip?: string[];
    priority?: string[];
    stretch?: boolean;
    feel?: Record<string, 'easy' | 'hard'>;
  };
  style: PathStyle;
}

export interface Forecast {
  planned_finish: string;
  realistic_finish: string;
  adherence: number;
  weekly_minutes: number;
  target_date: string | null;
  on_track: boolean | null;
}

export interface Milestone {
  week: number;
  ends: string;
  concepts: { concept: string; title: string }[];
  outcome: string;
}

export interface Nudge {
  kind: string;
  severity: 'low' | 'medium' | 'high';
  title: string;
  body: string;
  href: string;
}

export interface PathOption {
  style: PathStyle;
  label: string;
  description: string;
  current: boolean;
  remaining_minutes: number;
  finish: string;
  concepts: number;
  optional: number;
}

export interface PathOptions {
  current: PathStyle;
  focus: 'foundations' | 'interview' | 'contest';
  options: PathOption[];
}

export interface WeeklyReview {
  week_start: string;
  week_end: string;
  minutes: { done: number; planned: number };
  study_days: number;
  evidence: number;
  wins: string[];
  improved: string[];
  slipping: { concept: string; title: string; href: string }[];
  stuck: { concept: string; title: string; summary: string; href: string }[];
  forecast: Forecast;
  next_milestone: Milestone | null;
  proposals: Proposal[];
  seen: boolean;
}

export interface Streak {
  current: number;
  longest: number;
  studied_today: boolean;
  /** Streak freezes banked by meeting a full week's goal; each covers one missed day. */
  freezes: number;
  /** Recent days a freeze covered (ISO dates). */
  frozen: string[];
  week_minutes: number;
  week_goal: number;
}

export interface ProgressNumbers {
  total: number;
  finished: number;
  /** Skills placed as known without evidence; not part of `finished` until confirmed. */
  assumed: number;
  /** Check passed (learned) and proven again after a gap (mastered); together = finished. */
  learned?: number;
  mastered?: number;
  percent: number;
  /** Every skill on the path is learned or mastered. */
  complete?: boolean;
}

export interface Today {
  greeting: string;
  course: { id: string; title: string };
  language: Language;
  date: string;
  study_day: boolean;
  streak: Streak;
  days_away: number;
  minutes: { done: number; goal: number; reached?: boolean };
  done: Activity[];
  next: Activity | null;
  /** The module the learner is working in (where the next step is). */
  current_module?: string | null;
  queue: Activity[];
  pace: Pace;
  pace_reason: string;
  latest_update: Revision | null;
  reviews_due: number;
  progress: ProgressNumbers;
  projected_finish: string;
  forecast: Forecast;
  checkin: { message: string; first: Activity | null } | null;
  nudges: Nudge[];
  proposals: Proposal[];
  milestone: Milestone | null;
}

export interface RoadmapItem {
  reason_codes: ReasonCode[];
  lesson_done: boolean;
  quiz_done: boolean;
  review_due: boolean;
  /** Qualified ids of the concepts this one builds on; may include ones outside the enrolled roadmap. */
  requires: string[];
  /** Transfer check: verified, due (take it), pending (solve the problem), wait (cooling down). */
  transfer?: 'verified' | 'due' | 'pending' | 'wait' | null;
  roadmap_resources: { title: string; url: string; source: string; language: string | null }[];
  concept: string;
  title: string;
  module: string;
  status:
    | 'mastered'
    | 'assumed'
    | 'practiced'
    | 'in_progress'
    | 'upcoming'
    | 'locked'
    | 'preparing'
    | 'optional'
    | 'skipped';
  locked_by?: string;
  mastery: number;
  confidence: number;
  minutes: number;
  relevance: number;
  priority: boolean;
  deferred: boolean;
  /** Why this concept sits where it does, or how it is being taught right now. */
  why?: string;
}

export interface PlanView {
  pace: Pace;
  pace_reason: string;
  projected_finish: string;
  remaining_minutes: number;
  target_date: string | null;
  on_track: boolean | null;
  current_concept: string | null;
  /** The module the next step is in. */
  current_module?: string | null;
  modules: {
    id: string;
    title: string;
    summary: string;
    course: string;
    bridge: boolean;
    concepts: RoadmapItem[];
    locked_by: LockInfo | null;
  }[];
  days: { date: string; items: Activity[]; minutes: number }[];
  reasons: string[];
  revisions: Revision[];
  progress: ProgressNumbers;
  style: PathStyle;
  focus: 'foundations' | 'interview' | 'contest';
  forecast: Forecast;
  milestones: Milestone[];
  proposals: ProposalsView;
  weekly_review_ready: boolean;
}

export interface Achievement {
  id: string;
  title: string;
  description: string;
  goal: number;
  value: number;
  earned: boolean;
  earned_at: number | null;
}

export interface ProgressView {
  modules: {
    id: string;
    title: string;
    concepts: {
      id: string;
      title: string;
      band: Band;
      mastery: number;
      confidence: number;
      evidence: number;
      next_review: number | null;
      /** Roadmap status: practiced = every step done and the check passed. */
      status?: RoadmapItem['status'];
      independent?: number;
      assisted?: number;
    }[];
  }[];
  progress: ProgressNumbers;
  streak: Streak;
  achievements: Achievement[];
  heatmap: { day: string; minutes: number; activities: number }[];
  week: { minutes: number; goal: number };
  solves: { independent_solves: number; assisted_solves: number };
  total_minutes: number;
  revisions: Revision[];
  recent: { concept: string; kind: string; score: number; assisted: boolean; at: number }[];
  pace: Pace;
  projected_finish: string;
}

export interface Resource {
  title: string;
  url: string;
  kind: 'article' | 'video' | 'docs' | 'course' | 'book' | 'interactive' | 'visualizer';
  source: string;
  minutes: number;
  level: 'intro' | 'core' | 'deep';
  languages: Language[];
  /** Among the few picked for this learner right now. */
  picked?: boolean;
  opened?: boolean;
  helpful?: boolean | null;
}

export type Platform = 'Socrat' | 'LeetCode' | 'CSES' | 'Codeforces';
export type PracticeStatus = 'todo' | 'attempted' | 'solved';

export interface ExternalProblem {
  id: string;
  title: string;
  /** Opened on click only; never rendered as text. Socrat problems use an in-app path. */
  url: string;
  platform: Platform | string;
  difficulty: 'easy' | 'medium' | 'hard';
  rating?: number | null;
  concepts: string[];
  companies: number;
  striver: boolean;
}

export interface LibraryProblem extends ExternalProblem {
  status: PracticeStatus | null;
  bookmarked: boolean;
  concept: { id: string; title: string; band: Band } | null;
}

export interface Level {
  rating: number;
  name: string;
  next_name: string | null;
  next_rating: number | null;
  progress: number;
}

export interface RecommendedProblem extends ExternalProblem {
  kind: 'review' | 'practice' | 'current' | 'stretch' | 'start' | 'upsolve';
  reason: string;
  concept: { id: string; title: string; band: Band };
  status: PracticeStatus | null;
}

export interface CodeforcesAccount {
  handle: string;
  rating: number | null;
  max_rating: number | null;
  rank: string;
  solved: number;
  attempted: number;
  weak_tags: string[];
  synced_at: number | null;
  sync_error: string;
}

export interface Recommendations {
  level: Level;
  problems: RecommendedProblem[];
  topics: { id: string; title: string; summary: string; reason: string; kind: string; band: Band; minutes: number }[];
  solved_external: number;
  codeforces: CodeforcesAccount | null;
}

export interface CompanyProblem extends ExternalProblem {
  frequency: number;
  window: 'thirty-days' | 'three-months' | 'six-months' | 'more-than-six-months' | 'all';
  concept: { id: string; title: string; band: Band } | null;
}

/** A rubric grade from the AI grader: points per criterion, logged with the evidence. */
export interface Grade {
  score: number;
  criteria: { criterion: string; points: number; max: number; note: string }[];
  feedback: string;
  model: string;
  copied: boolean;
}

export interface WrittenPrompt {
  id: string;
  prompt: string;
  max_words: number;
  rubric: { criterion: string; points: number }[];
  last: { answer: string; grade: Grade; model_answer: string } | null;
}

export interface ProjectMilestone {
  id: string;
  title: string;
  checklist: string[];
  done: boolean;
  available: boolean;
  last: { work: string; link: string; grade: Grade } | null;
}

export interface ProjectView {
  id: string;
  title: string;
  summary: string;
  skills: string[];
  constraints: string[];
  concepts: { id: string; title: string }[];
  rubric: { criterion: string; weight: number; full_marks: string }[];
  self_review: string[];
  milestones: ProjectMilestone[];
  preparing: boolean;
  ai_generated: boolean;
  attribution: string;
}

export interface ConceptView {
  prompts?: WrittenPrompt[];
  exercises: { number: number; title: string; url: string; language: string; guidance: string }[];
  id: string;
  course: string;
  title: string;
  summary: string;
  module: string;
  lesson: string;
  ai_generated: boolean;
  attribution: string;
  key_points: string[];
  pitfalls: string[];
  resources: Resource[];
  practice_links: { title: string; url: string; platform: string; difficulty: 'easy' | 'medium' | 'hard' }[];
  more_practice: LibraryProblem[];
  implementations: { title: string; url: string }[];
  handbook: { chapter: string; title: string; page: number; url: string; source: string }[];
  problems: { id: string; title: string; difficulty: string; solved: boolean }[];
  prerequisites: { id: string; title: string; band: Band }[];
  band: Band;
  lesson_done: boolean;
  quiz_done: boolean;
  locked: LockInfo | null;
  language: Language;
}

export interface QuizQuestion {
  id: string;
  concept: string;
  concept_title: string;
  kind: string;
  prompt: string;
  code: string | null;
  options: string[];
  difficulty: number;
  answered: boolean;
  choice: number | null;
  correct?: boolean;
  answer?: number;
  explanation?: string;
}

export interface QuizSession {
  id: string;
  activity_id: string;
  questions: QuizQuestion[];
  completed: boolean;
  score: number | null;
  feedback: 'immediate' | 'at_end';
  gate?: Gate;
  /** Test-outs: whether the learner proved it and skipped ahead. */
  testout?: { passed: boolean; score: number | null };
}

/** A checkpoint that unlocks the next module: an adaptive staircase graded at the end. */
export interface Gate {
  max_items: number;
  max_strikes: number;
  strikes: number;
  levels: number[];
  level: number;
  hard_level: number;
  hard_needed: number;
  hard_correct: number;
  pass_score: number;
  score: number | null;
  passed: boolean | null;
  retry_at: number | null;
  attempts: number;
  module: string;
  unlocks: string | null;
}

export interface LockInfo {
  gate: string;
  module: string;
  /** The checkpoint is passed; a transfer check still holds the module shut. */
  needs_transfer?: boolean;
  /** The transfer check to take now, if one is open. */
  transfer?: string | null;
}

export type TransferView =
  | { concept: string; title: string; state: 'unavailable' | 'verified' }
  | { concept: string; title: string; state: 'wait'; retry_at: number }
  | { concept: string; title: string; state: 'solve'; problem: string }
  | {
      concept: string;
      title: string;
      state: 'classify';
      problem: { id: string; statement: string; input_format: string; output_format: string; constraints: string[]; examples: { input: string; output: string; explanation?: string }[] };
      choices: { id: string; title: string }[];
    };

export interface TransferResult {
  correct: boolean;
  state: 'solve' | 'wait';
  problem?: string;
  retry_at?: number;
  answer?: string;
}

export interface Case {
  status: string;
  wall_ms: number;
  public: boolean;
  input: string | null;
  expected: string | null;
  stdout: string | null;
  stderr: string | null;
}

export interface Submission {
  id: string;
  problem_id: string;
  language: Language;
  mode: 'run' | 'submit';
  status: 'queued' | 'running' | 'done' | string;
  verdict: string;
  passed: number;
  total: number;
  cases: Case[];
  assistance: number;
  created_at: number;
  finished_at: number | null;
  /** Present while a browser-run job waits for this browser to run it. */
  browser?: BrowserTask | null;
}

export interface BrowserTask {
  token: string;
  language: Language;
  time_limit_ms: number;
  expires_at: number;
  tests: { index: number; input: string }[];
}

export interface ProblemView {
  id: string;
  locked: LockInfo | null;
  title: string;
  difficulty: string;
  concept: { id: string; title: string };
  statement: string;
  input_format: string;
  output_format: string;
  constraints: string[];
  examples: { input: string; output: string; explanation?: string }[];
  language: Language;
  starter: string;
  draft: string | null;
  solved: boolean;
  history: {
    id: string;
    mode: string;
    verdict: string;
    status: string;
    passed: number;
    total: number;
    at: number;
  }[];
  hint_count: number;
}

export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  level?: number | null;
  rating?: number | null;
}

export interface AssessmentStatus {
  /** 'upcoming': enough study this week, and the exam opens on Sunday. */
  state: 'locked' | 'upcoming' | 'available' | 'in_progress' | 'done';
  week: string;
  id: string | null;
  topics: string[];
  questions?: number;
  time_limit_minutes?: number;
  needed: number;
  /** Local date (YYYY-MM-DD) of the next exam day. */
  opens_on?: string;
  ready?: boolean;
}

export interface AssessmentReport {
  correct: number;
  questions: number;
  coding_solved: number;
  coding_total: number;
  minutes: number;
  previous_score: number | null;
  topics: { id: string; title: string; correct: number; total: number; before: number; after: number; band: Band }[];
  strengths: string[];
  focus: { id: string; title: string }[];
}

export interface AssessmentView {
  id: string;
  week: string;
  timed: boolean;
  started_at: number;
  deadline: number | null;
  seconds_left: number | null;
  /** Server clock at the response, so the countdown does not trust the device clock. */
  server_now?: number;
  finished: boolean;
  score: number | null;
  topics: { id: string; title: string; reason: 'studied' | 'review' }[];
  questions: QuizQuestion[];
  coding: { id: string; title: string; difficulty: string; concept: string; solved: boolean }[];
  report: AssessmentReport | null;
}

export interface SprintView {
  id: string;
  started_at: number;
  deadline: number;
  seconds_left: number | null;
  finished: boolean;
  solved: number;
  problems: { id: string; title: string; difficulty: string; concept: string; solved_after: number | null }[];
}

export interface Contest {
  id: number;
  name: string;
  start: number;
  duration_minutes: number;
  url: string;
}

/** How Socrat models the learner: one profile per concept plus a single practice level. */
export interface LearnerProfile {
  level: { rating: number; library: number; quiz: number | null; codeforces: number | null };
  review_scale: number;
  adherence: number;
  concepts: {
    concept: string;
    title: string;
    band: Band;
    mastery: number;
    trend: number | null;
    speed: number | null;
    hint_dependence: number;
    attempts: number;
    misconceptions: Record<string, number>;
    stuck: { summary: string; severity: number; failure_mode: string } | null;
  }[];
}

/** Public Skill Passport: verified evidence only, computed live. */
export interface PassportView {
  name: string;
  member_since: string;
  course: string | null;
  language: Language | null;
  mastered: { id: string; title: string; evidence: number; transfer_verified: boolean }[];
  practising: { id: string; title: string; evidence: number }[];
  counts: {
    unaided_solves: number;
    judged_solves: number;
    assisted_solves: number;
    checks_passed: number;
    transfer_verified: number;
    checkpoints: number;
    weekly_assessments: number;
    longest_streak: number;
  };
  badges: { id: string; title: string; description: string; earned_at: number | null }[];
  generated_at: number;
}

export interface PassportSettings {
  public: boolean;
  slug: string | null;
  path: string | null;
  updated_at: number | null;
  preview: PassportView;
}

export interface CompanySprintWeek {
  number: number;
  starts: string;
  ends: string;
  review: boolean;
  concepts: { id: string; title: string; band: Band; done: boolean }[];
  questions: (ExternalProblem & { solved: boolean })[];
  locked_questions: number;
}

export interface CompanySprintView {
  id: string;
  company: { slug: string; name: string };
  role: string;
  role_label: string;
  title: string;
  weeks_total: number;
  started_on: string;
  ends_on: string;
  current_week: number;
  finished: boolean;
  progress: number;
  on_track: boolean;
  counts: { concepts: number; concepts_done: number; questions: number; questions_solved: number; already_known: number };
  weeks: CompanySprintWeek[];
  proposal: Proposal | null;
}

export interface CompanySprintOverview {
  current: CompanySprintView | null;
  companies: { slug: string; name: string; questions: number }[];
  roles: { id: string; label: string }[];
  weeks: number[];
  /** Company sprints need Pro. */
  locked?: boolean;
}

export interface TryProblem {
  id: string;
  title: string;
  statement: string;
  input_format: string;
  output_format: string;
  constraints: string[];
  examples: { input: string; output: string; explanation: string }[];
  starter: string;
  time_limit_ms: number;
  tests: { index: number; input: string; expected: string; public: boolean }[];
  max_turns: number;
}
