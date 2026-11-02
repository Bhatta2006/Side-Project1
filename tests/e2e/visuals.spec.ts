import { expect, test } from '@playwright/test';

// Lesson visuals render through approved components only. The gallery shows one of each wired
// renderer; the simulation talks to the real server (computed by the harness, not the browser).
test('simulation, timeline and code task work in a real browser', async ({ page }, testInfo) => {
  // Through the web origin, so the session cookie belongs to the page.
  const login = await page.request.post('/api/v1/auth/dev-login', {
    data: { subject: `visuals-${testInfo.project.name}`, display_name: 'Visuals' },
    headers: { Origin: 'http://localhost:3000' },
  });
  expect(login.ok()).toBeTruthy();
  await page.goto('/dev-gallery');
  // A first sign-in shows the plans once; it hides the page from assistive tech until dismissed.
  const later = page.getByRole('button', { name: 'Maybe later' });
  await later.click({ timeout: 8_000 }).catch(() => undefined);
  const visuals = page.getByTestId('lesson-visuals');

  // Simulation: 10 V across 5 ohm is 2 A, computed by the server; moving a slider recomputes it.
  await expect(visuals.getByRole('cell', { name: '2 A' })).toBeVisible({ timeout: 20_000 });
  await visuals.getByLabel(/resistance/i).press('End'); // the slider's top value, so less current
  await expect(visuals.getByRole('cell', { name: '2 A', exact: true })).toBeHidden({ timeout: 20_000 });

  // Timeline: tapping a step places a marker and the text list follows.
  const kick = visuals.getByRole('button', { name: 'Kick, beat 1' });
  await kick.click();
  await expect(kick).toHaveAttribute('aria-pressed', 'true');
  await expect(visuals.getByText(/Kick: 1/)).toBeVisible();

  // Code task: free practice says it is not judged.
  await expect(visuals.getByText(/not judged/)).toBeVisible();
});

// Lite mode holds a simulation behind its text version until the learner asks for it.
test('lite mode shows the text version first and loads the visual on request', async ({ page }, testInfo) => {
  const login = await page.request.post('/api/v1/auth/dev-login', {
    data: { subject: `lite-${testInfo.project.name}`, display_name: 'Lite' },
    headers: { Origin: 'http://localhost:3000' },
  });
  expect(login.ok()).toBeTruthy();
  await page.addInitScript(() => localStorage.setItem('socrat:data-use', 'lite'));
  await page.goto('/dev-gallery');
  await page.getByRole('button', { name: 'Maybe later' }).click({ timeout: 8_000 }).catch(() => undefined);
  const visuals = page.getByTestId('lesson-visuals');

  const load = visuals.getByRole('button', { name: 'Load the interactive visual' });
  await expect(load.first()).toBeVisible({ timeout: 20_000 });
  await expect(visuals.getByText(/Lite mode: showing the text version/).first()).toBeVisible();
  await expect(visuals.getByRole('cell', { name: '2 A' })).toHaveCount(0);
  // Light renderers are not held.
  await expect(visuals.getByRole('button', { name: 'Kick, beat 1' })).toBeVisible();

  await load.first().click();
  await expect(visuals.getByRole('cell', { name: '2 A' })).toBeVisible({ timeout: 20_000 });
});

// Other languages' strings load only when chosen. A Hindi learner still gets Hindi settings,
// including the data-use choice (offered because the e2e server turns lite mode on).
test('a Hindi learner sees Hindi settings and the data-use choice', async ({ page }, testInfo) => {
  const origin = 'http://localhost:3000';
  const login = await page.request.post('/api/v1/auth/dev-login', {
    data: { subject: `hindi-${testInfo.project.name}-${Date.now()}`, display_name: 'Hindi' },
    headers: { Origin: origin },
  });
  expect(login.ok()).toBeTruthy();
  const profile = await (await page.request.get('/api/v1/me')).json();
  const headers = { Origin: origin, 'X-CSRF-Token': profile.csrf_token };
  await page.request.patch('/api/v1/me', { headers, data: { birth_year: 2000, timezone: 'UTC', locale: 'hi' } });
  const enrolled = await page.request.post('/api/v1/enrollments', {
    headers,
    data: { course: 'zero', language: 'python', level: 'brand-new', minutes_per_day: 30, weekdays: [0, 1, 2, 3, 4] },
  });
  expect(enrolled.ok()).toBeTruthy();
  await page.goto('/settings');
  await page.getByRole('button', { name: 'Maybe later' }).click({ timeout: 8_000 }).catch(() => undefined);
  await expect(page.getByText('डेटा उपयोग')).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('html')).toHaveAttribute('lang', 'hi');

  const lite = page.getByRole('button', { name: 'लाइट' });
  await lite.click();
  await expect(lite).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByText('अभी लाइट मोड चालू है।')).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem('socrat:data-use'))).toBe('lite');
});
