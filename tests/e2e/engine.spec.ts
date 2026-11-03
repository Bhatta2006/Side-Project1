import { expect, test } from '@playwright/test';

// A learner can say how sure they are before checking a quiz answer; it is optional and feeds
// confidence calibration (master prompt 8.1), never the score.
test('quiz answers can carry an optional confidence', async ({ page }, testInfo) => {
  const origin = 'http://localhost:3000';
  const login = await page.request.post('/api/v1/auth/dev-login', {
    data: { subject: `sure-${testInfo.project.name}-${Date.now()}`, display_name: 'Sure' },
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
  await page.request.post('/api/v1/activities/lesson:zero:programs-and-output/complete', { headers });

  await page.emulateMedia({ reducedMotion: 'reduce' }); // stable layout, as the other suites do
  await page.goto('/quiz/quiz/zero/programs-and-output');
  await page.getByRole('button', { name: 'Maybe later' }).click({ timeout: 8_000 }).catch(() => undefined);
  const sure = page.getByRole('group', { name: /How sure are you/ });
  await expect(sure).toHaveCount(0); // only after an option is chosen
  await page.getByRole('radio').first().click();
  await expect(sure).toBeVisible();
  // The emulated phone draws a 20px classic scrollbar (real phones overlay it), which shifts
  // Playwright's click point onto the neighbouring pill near the fixed bottom nav. A hit test at
  // rest finds the right button, so dispatch the click instead of moving a mouse.
  await sure.getByRole('button', { name: 'Certain' }).dispatchEvent('click');
  await expect(sure.getByRole('button', { name: 'Certain' })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: 'Check answer' }).dispatchEvent('click');
  await expect(page.getByText(/^(Correct|Incorrect)$/).first()).toBeVisible({ timeout: 20_000 });

  const calibration = await (await page.request.get('/api/v1/progress/calibration')).json();
  expect(calibration.calibration.rated).toBe(1);
  expect(calibration.calibration.confidence).toBe(1);
});
