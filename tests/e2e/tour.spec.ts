import { expect, test, type Page } from '@playwright/test';

// This file needs a browser that has never seen the tour.
test.use({ storageState: { cookies: [], origins: [] } });

async function enrolled(page: Page) {
  const origin = 'http://localhost:3000';
  expect((await page.request.post('/api/v1/auth/dev-login', { headers: { Origin: origin }, data: { subject: `tour-${Date.now()}-${Math.random().toString(36).slice(2)}`, display_name: 'Learner' } })).ok()).toBe(true);
  const profile = await (await page.request.get('/api/v1/me')).json();
  const headers = { Origin: origin, 'X-CSRF-Token': profile.csrf_token };
  await page.request.patch('/api/v1/me', { headers, data: { birth_year: 2000, timezone: 'UTC' } });
  await page.request.post('/api/v1/enrollments', { headers, data: { course: 'basics', language: 'python', level: 'brand-new', minutes_per_day: 30, weekdays: [0, 1, 2, 3, 4] } });
}

test('a new learner gets the tour once, and can replay it from Settings', async ({ page }) => {
  await enrolled(page);
  await page.goto('/today');
  await page.getByRole('button', { name: 'Maybe later' }).click({ timeout: 8_000 }).catch(() => undefined);

  const tour = page.getByRole('dialog', { name: 'Welcome to Socrat' });
  await expect(tour).toBeVisible();
  await page.getByRole('button', { name: 'Show me' }).click();
  for (const title of ['Today', 'Ask Soc, your tutor', 'Skills', 'Practice', 'Playground', 'Evidence', 'Settings']) {
    await expect(page.getByRole('dialog', { name: title })).toBeVisible();
    await page.getByRole('button', { name: 'Next' }).click();
  }
  await expect(page.getByRole('dialog', { name: 'You are all set' })).toBeVisible();
  await page.getByRole('button', { name: 'Start learning' }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect.poll(async () => (await (await page.request.get('/api/v1/me')).json()).tour_seen).toBe(true);

  // The account remembers it, even in a browser that has not seen it.
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await page.waitForTimeout(1_000);
  await expect(page.getByRole('dialog')).toHaveCount(0);

  await page.goto('/settings');
  // Replay is a window event the shell's tour listens for once hydrated: retry until it lands.
  await expect(async () => {
    await page.getByRole('button', { name: 'Replay tour' }).click();
    await expect(page.getByRole('dialog', { name: 'Welcome to Socrat' })).toBeVisible({ timeout: 5_000 });
  }).toPass({ timeout: 30_000 });
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
});
