import { expect, test } from '@playwright/test';

// Today loads "How Socrat is adapting to you" on demand (it is outside the first-load budget);
// it must still appear with the rest of the page.
test('Today shows the adapting card after it loads on demand', async ({ page }, testInfo) => {
  const origin = 'http://localhost:3000';
  const login = await page.request.post('/api/v1/auth/dev-login', {
    data: { subject: `today-${testInfo.project.name}-${Date.now()}`, display_name: 'Today' },
    headers: { Origin: origin },
  });
  expect(login.ok()).toBeTruthy();
  const profile = await (await page.request.get('/api/v1/me')).json();
  const headers = { Origin: origin, 'X-CSRF-Token': profile.csrf_token };
  await page.request.patch('/api/v1/me', { headers, data: { birth_year: 2000, timezone: 'UTC' } });
  const enrolled = await page.request.post('/api/v1/enrollments', {
    headers,
    data: { course: 'zero', language: 'python', level: 'brand-new', minutes_per_day: 30, weekdays: [0, 1, 2, 3, 4, 5, 6] },
  });
  expect(enrolled.ok()).toBeTruthy();
  await page.goto('/today');
  await page.getByRole('button', { name: 'Maybe later' }).click({ timeout: 8_000 }).catch(() => undefined);
  await expect(page.getByRole('heading', { name: 'How Socrat is adapting to you' })).toBeVisible({ timeout: 20_000 });
});
