'use client';

/** Thin client for the v2 learner API. Writes carry the session's CSRF token. */

export class ApiError extends Error {
  constructor(public status: number, public code: string) {
    super(code);
  }
}

let csrf = '';
export function setCsrf(token: string) {
  csrf = token;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (method !== 'GET') headers['X-CSRF-Token'] = csrf;
  const response = await fetch(`/api/v1${path}`, {
    method,
    headers,
    credentials: 'same-origin',
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && path !== '/me' && !path.startsWith('/auth')) toLogin();
    const code = data?.error?.code ?? 'request_failed';
    // Any locked feature, from any page, opens the paywall (components/paywall.tsx).
    if (response.status === 402 || code === 'chat_week_limit') openPaywall(code);
    throw new ApiError(response.status, code);
  }
  return data as T;
}

export const PAYWALL_EVENT = 'socrat:paywall';
export function openPaywall(reason: string) {
  if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent(PAYWALL_EVENT, { detail: reason }));
}

const PUBLIC = /^\/(login|privacy|terms|attribution|passport)?(\/|$)/;

function toLogin() {
  if (typeof window === 'undefined' || PUBLIC.test(window.location.pathname)) return;
  const next = window.location.pathname + window.location.search;
  window.location.assign(`/login?next=${encodeURIComponent(next)}`);
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body: unknown = {}) => request<T>('POST', path, body),
  put: <T>(path: string, body: unknown) => request<T>('PUT', path, body),
  patch: <T>(path: string, body: unknown) => request<T>('PATCH', path, body),
  del: <T>(path: string) => request<T>('DELETE', path),
};

export type StreamEvent = { event: string; data: Record<string, unknown> };

/** POST that answers with Server-Sent Events; yields each parsed event. */
export async function* stream(path: string, body: unknown, signal?: AbortSignal): AsyncGenerator<StreamEvent> {
  const response = await fetch(`/api/v1${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, Accept: 'text/event-stream' },
    credentials: 'same-origin',
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok || !response.body) {
    const data = await response.json().catch(() => ({}));
    const code = data?.error?.code ?? 'request_failed';
    if (response.status === 402 || code === 'chat_week_limit') openPaywall(code);
    throw new ApiError(response.status, code);
  }
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let split;
    while ((split = buffer.indexOf('\n\n')) >= 0) {
      const chunk = buffer.slice(0, split);
      buffer = buffer.slice(split + 2);
      let event = 'message';
      let data = '';
      for (const line of chunk.split('\n')) {
        if (line.startsWith('event: ')) event = line.slice(7);
        else if (line.startsWith('data: ')) data += line.slice(6);
      }
      if (data) yield { event, data: JSON.parse(data) };
    }
  }
}

const MESSAGES: Record<string, string> = {
  too_many_open_requests: 'You already have a few plans waiting. Start or finish one first.',
  request_blocked: "Socrat can't help with that request.",
  invalid_choice: 'One of those choices is not valid. Pick one option per group.',
  outline_not_ready: 'Your plan is still being prepared.',
  minimum_age: 'Socrat is for learners aged 13 and over.',
  profile_incomplete: 'Finish your profile first.',
  content_unavailable: 'Course content is not built yet. Run python scripts/content/build.py.',
  assistant_daily_limit: "You've reached today's assistant limit. It resets within 24 hours.",
  ai_budget_reached: "Soc has used today's AI allowance. Curated hints still work, and the allowance resets tomorrow.",
  ai_disabled: 'AI features are paused for maintenance. Curated hints still work.',
  ai_rate_limited: 'That was a lot of requests in a minute. Wait a moment and try again.',
  execution_lease_expired: 'That run took too long to report back. Run it again.',
  execution_token_invalid: 'That run could not be matched to your submission. Run it again.',
  execution_unavailable: 'Code execution is turned off on this server.',
  runtime_offline: 'No code runner for this language is online right now. Try again shortly.',
  daily_run_quota: "You've used today's run allowance. It resets tomorrow.",
  too_many_pending_runs: 'Wait for your earlier runs to finish first.',
  empty_source: 'Write some code first.',
  custom_input_too_large: 'That custom input is too large.',
  csrf_rejected: 'Your session token expired. Reload the page.',
  language_not_offered: 'That course is not offered in this language.',
  placement_in_progress: 'Finish the placement check first.',
  already_enrolled: 'Finish your current course first. Continue it from Today.',
  validation_failed: 'Some details are not valid. Check the form and try again.',
  authentication_required: 'Your session ended. Sign in again.',
  invalid_credentials: 'That email and password do not match. Check them, or use Forgot password.',
  email_code_invalid: 'That code is wrong or has expired. Check it, or send a new one.',
  too_many_attempts: 'Too many attempts. Wait a while, then try again.',
  email_unavailable: 'We could not send the email right now. Please try again in a few minutes.',
  codeforces_handle_not_found: "Codeforces doesn't know that handle. Check the spelling.",
  codeforces_invalid_handle: 'Handles are 3–24 letters, digits, dots, dashes or underscores.',
  codeforces_unavailable: "Codeforces isn't answering right now. Try again in a minute.",
  not_linked: 'Link a Codeforces handle first.',
  concept_locked: 'This topic unlocks when you pass the checkpoint before it.',
  concept_preparing: 'This lesson is still being prepared. Keep going with the topics before it.',
  course_exists: 'A course with that id already exists. Pick another id.',
  generation_in_progress: 'The agents are still working on this course. Wait for them to finish.',
  unknown_reuse_concept: 'One of the concepts to build on does not exist. Use full ids like zero:loops.',
  outline_published: 'This course is already published; its outline can no longer change here.',
  outline_invalid: 'The outline no longer fits the catalog. Edit it, then publish again.',
  publish_outline_first: 'Publish the outline before writing lessons.',
  concept_not_planned: 'Only planned concepts can be written; this one is already live or unknown.',
  budget_reached: 'This course has spent its budget. Raise the budget first, then resume.',
  concept_not_live: 'Only a live concept can be withdrawn or given exercises.',
  module_not_live: 'Every concept in this module must be live before it gets a project.',
  answer_length: 'Write between 10 words and the limit shown.',
  answer_attempts: "You have used today's three graded tries here. Come back tomorrow.",
  grading_unavailable: 'Grading is unavailable right now. Your answer was not counted; try again shortly.',
  milestone_locked: 'Finish the earlier milestone first.',
  checklist_incomplete: 'Tick every checklist item your work covers before submitting.',
  link_unreachable: 'That link is not a public https page we can open. Check it, or leave it out.',
  topic_not_completed: 'Complete the required topic lessons before opening this question.',
  independent_work_in_progress: 'Finish your independent assessment or timed work before opening learning help.',
  playground_generation_unavailable: 'Your lesson could not be generated right now. Your request is still here; try again.',
  playground_generation_invalid: 'The generated lesson could not be validated. Your request is still here; try again.',
  playground_generation_timeout: 'Generation took too long. Your request is still here; try again.',
  playground_ai_budget_reached: 'Socrat has reached today’s AI capacity for visuals. Your request is still here; try again tomorrow.',
  playground_ai_disabled: 'AI visuals are paused for maintenance. Your request is still here; please try again later.',
  playground_generation_interrupted: 'The server restarted while building your visual. Your request is still here; try again.',
  playground_unavailable: 'The visual playground is unavailable right now. Please try again later.',
  playground_checker_unavailable: 'The visual could not be checked right now. Your request is still here; try again.',
  playground_review_unavailable: 'The explanation could not be reviewed right now. Your request is still here; try again.',
  playground_sandbox_unavailable: 'The visual preview is unavailable right now. Please try again later.',
  playground_request_in_progress: 'Your visual is still being created. Wait for it to finish before starting another.',
  playground_busy: 'The visual playground is busy right now. Your request is still here; try again shortly.',
  playground_daily_limit: 'You have reached today’s visual-generation limit. Your saved visuals are still available.',
  playground_idempotency_conflict: 'This request could not be resumed. Please generate it again.',
  playground_artifact_reported: 'This visual was reported and removed. Generate a new one.',
  playground_frame_expired: 'This preview link expired. Reopen the visual from your saved explorations.',
  upgrade_required: 'This is part of the Founding Member plan. See the plans to unlock it.',
  pro_required: 'Company questions are part of the Pro plan. See the plans to unlock them.',
  chat_week_limit: "You've used this week's free messages with Soc. They reset on Monday, or upgrade for daily messages.",
  chat_day_limit: "You've used today's messages with Soc. They reset at midnight, or move up a plan for more.",
  playground_day_limit: "You've used today's visual generations. They reset at midnight, or move up a plan for more.",
  already_subscribed: 'You already have a paid plan. Manage it in Settings.',
  billing_unavailable: 'Payments are not available right now. Please try again later.',
  billing_provider_error: 'The payment provider did not answer. Nothing was charged. Please try again.',
  payment_signature_invalid: 'We could not confirm that payment. If you were charged, contact support and it will be sorted out.',
  not_found: "We couldn't find that. The link may be old, or it may belong to a different course than the one you are on.",
  no_active_enrollment: 'Choose a course first.',
  sprint_unavailable: 'Finish a concept check on a topic with practice problems first — sprints use topics you have studied.',
  assessment_done: "You've already finished this week's assessment. A new one opens next week.",
  try_turns_used: "That's the end of the free preview. Create an account to keep going with Soc.",
  try_rate_limited: 'The preview is busy from your network. Try again in a little while, or sign up to keep going.',
  company_not_covered: "That company's questions don't use skills in your course. Pick another company or course.",
  assessment_unavailable: 'Study at least two topics this week to unlock your weekly assessment.',
};

export function explain(error: unknown): string {
  if (error instanceof ApiError) return MESSAGES[error.code] ?? `Something went wrong (${error.code}).`;
  return 'Could not reach Socrat. Check your connection and try again.';
}
