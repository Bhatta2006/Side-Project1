import { expect, type Page } from '@playwright/test';

const ORIGIN = 'http://localhost:3000';

/** A fresh adult learner, signed in through the API, enrolled straight into a fixture course
 * (``basics`` or ``algo``). Lesson 0 onboarding has its own spec; other specs start here. */
export async function enrolled(
  page: Page,
  subject: string,
  course: 'basics' | 'algo' = 'basics',
  level = 'brand-new',
  extra: Record<string, unknown> = {},
) {
  const login = await page.request.post('/api/v1/auth/dev-login', {
    data: { subject, display_name: 'Ada' },
    headers: { Origin: ORIGIN },
  });
  expect(login.ok()).toBeTruthy();
  const profile = await (await page.request.get('/api/v1/me')).json();
  const headers = { Origin: ORIGIN, 'X-CSRF-Token': profile.csrf_token };
  await page.request.patch('/api/v1/me', { headers, data: { birth_year: 2000, timezone: 'UTC' } });
  const made = await page.request.post('/api/v1/enrollments', {
    headers,
    data: { course, language: 'python', level, minutes_per_day: 45, weekdays: [0, 1, 2, 3, 4, 5, 6], ...extra },
  });
  expect(made.ok(), await made.text()).toBeTruthy();
  return headers;
}

/** The plans dialog a first visit shows makes the rest of the page aria-hidden until closed. */
export async function dismissPlans(page: Page) {
  await page.getByRole('button', { name: 'Maybe later' }).click({ timeout: 8_000 }).catch(() => undefined);
}

/** Enrol the learner already signed in on ``page`` (as the UI login leaves them). */
export async function enrollSignedIn(page: Page, course: 'basics' | 'algo' = 'basics', level = 'brand-new') {
  const profile = await (await page.request.get('/api/v1/me')).json();
  const headers = { Origin: ORIGIN, 'X-CSRF-Token': profile.csrf_token };
  await page.request.patch('/api/v1/me', { headers, data: { birth_year: 2001, timezone: 'UTC', display_name: 'Ada' } });
  const made = await page.request.post('/api/v1/enrollments', {
    headers,
    data: { course, language: 'python', level, minutes_per_day: 45, weekdays: [0, 1, 2, 3, 4, 5, 6] },
  });
  expect(made.ok(), await made.text()).toBeTruthy();
  return headers;
}
