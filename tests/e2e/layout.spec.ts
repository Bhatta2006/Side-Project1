import { expect, test, type Page } from '@playwright/test';

/** No route may scroll sideways at 320, 390, 768 or 1440 px (reflow, not shrink). */
const ROUTES = [
  '/today', '/plan', '/assessments', '/playground', '/progress', '/settings',
  '/learn/basics/values', '/quiz/basics/values', '/problems/double-it',
];

async function enrolled(page: Page) {
  const origin = 'http://localhost:3000';
  expect((await page.request.post('/api/v1/auth/dev-login', { headers: { Origin: origin }, data: { subject: `layout-${Date.now()}-${Math.random().toString(36).slice(2)}`, display_name: 'Learner' } })).ok()).toBe(true);
  const profile = await (await page.request.get('/api/v1/me')).json();
  const headers = { Origin: origin, 'X-CSRF-Token': profile.csrf_token };
  await page.request.patch('/api/v1/me', { headers, data: { birth_year: 2000, timezone: 'UTC' } });
  await page.request.post('/api/v1/enrollments', { headers, data: { course: 'basics', language: 'python', level: 'brand-new', minutes_per_day: 30, weekdays: [0, 1, 2, 3, 4] } });
}

test('no page-level horizontal overflow at four widths', async ({ page }, info) => {
  test.skip(info.project.name !== 'desktop', 'widths are set explicitly');
  test.setTimeout(240_000);
  await enrolled(page);
  const found: string[] = [];
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 800 });
    for (const path of ['/', ...ROUTES]) {
      if (path === '/') continue; // signed-in visitors are redirected away from the landing page
      await page.goto(path);
      await page.waitForLoadState('networkidle');
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      if (overflow > 0) found.push(`${width}px ${path}: ${overflow}px wider than the viewport`);
    }
  }
  expect(found, found.join('\n')).toEqual([]);
});
