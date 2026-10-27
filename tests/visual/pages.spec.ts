import { expect, test, type Locator, type Page } from '@playwright/test';

/**
 * Visual regression for the pages learners see most. Content that changes by itself
 * (dates, greetings, daily-rotating picks, streak counters) is masked so only design
 * changes fail the comparison.
 */

test.use({ reducedMotion: 'reduce' });

async function settle(page: Page) {
  await page.waitForLoadState('networkidle');
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => document.getAnimations().every(a => a.playState !== 'running'), null, { timeout: 10_000 }).catch(() => undefined);
}

async function shoot(page: Page, name: string, mask: Locator[] = []) {
  await settle(page);
  await expect(page).toHaveScreenshot(`${name}.png`, { fullPage: true, mask: [page.locator('[data-visual-mask]'), ...mask] });
}

async function newLearner(page: Page) {
  await page.goto('/login');
  await page.getByLabel('Your name').fill(`visual-${test.info().project.name}-${Date.now()}`);
  await page.getByRole('button', { name: 'Log in' }).click();
  await page.getByLabel('What should we call you?').fill('Ada');
  await page.getByLabel('Year you were born').selectOption('2001');
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('button', { name: /Programming from Zero/ }).click();
  await page.getByRole('button', { name: /never written code/ }).click();
  await page.getByRole('button', { name: 'Python', exact: true }).click();
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('button', { name: 'Create my plan' }).click();
  await expect(page).toHaveURL(/\/today$/);
}

test('landing page', async ({ page }) => {
  // Keep the marketing composition independent of live catalog counts and dev banners.
  await page.route('**/api/v1/auth/status', route => route.fulfill({ json: { profile: null } }));
  await page.route('**/api/v1/features', route => route.fulfill({ json: {} }));
  await page.route('**/api/v1/courses', route => route.fulfill({ json: { items: [] } }));
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await shoot(page, 'landing');
});

test('public pages', async ({ page }) => {
  await page.route('**/api/v1/auth/status', route => route.fulfill({ json: { profile: null } }));
  await page.route('**/api/v1/features', route => route.fulfill({ json: { dev_login: true, oidc_login: true } }));
  await page.goto('/login');
  await expect(page.getByLabel('Your name')).toBeVisible();
  await shoot(page, 'login');
});

/** Recommendations rotate daily; give them fixed titles so heights stay the same. */
async function freezePicks(page: Page) {
  await page.route('**/api/v1/library/recommendations**', async route => {
    const response = await route.fetch();
    const body = await response.json();
    body.problems = (body.problems ?? []).map((p: Record<string, unknown>, i: number) => ({
      ...p, id: `visual-${i}`, title: `Practice problem ${i + 1}`, reason: 'Matched to your level.',
      platform: 'LeetCode', difficulty: 'easy', rating: 1000, solved: false,
    }));
    await route.fulfill({ response, json: body });
  });
}

test('learner pages', async ({ page }) => {
  test.setTimeout(180_000);
  await freezePicks(page);
  await newLearner(page);
  // Today keeps one section open at a time: check the picks, then open Progress for the shot.
  await page.getByRole('tab', { name: /^Practice/ }).click();
  await expect(page.getByRole('heading', { name: 'Practice picked for you' })).toBeVisible();
  await page.getByRole('tab', { name: /^Progress/ }).click();
  const header = page.locator('header').filter({ has: page.getByRole('heading', { level: 1 }) });
  const chrome: Locator[] = [];

  const card = (name: string | RegExp) => page.getByRole('heading', { name }).locator('xpath=ancestor::*[@data-slot="card"][1]');
  // Weekday letters and projected dates change on their own.
  await shoot(page, 'today', [...chrome, header, card(/-day streak/), card('Course progress')]);

  await page.goto('/plan');
  await expect(page.getByRole('heading', { name: 'Modules' })).toBeVisible();
  await shoot(page, 'plan', [...chrome, header, page.locator('[aria-labelledby="schedule-heading"]'), page.locator('[aria-labelledby="why-heading"]')]);

  await page.goto('/progress');
  await expect(page.getByRole('heading', { name: 'Mastery by module' })).toBeVisible();
  await page.getByRole('tab', { name: /^Activity/ }).click();
  await shoot(page, 'progress', [...chrome, header, page.locator('[aria-labelledby="activity-heading"]')]);

  await page.goto('/learn/zero/programs-and-output');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await shoot(page, 'lesson', chrome);

  await page.goto('/problems/greeting');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await expect(page.locator('.cm-editor')).toBeVisible();
  await shoot(page, 'problem', chrome);
});
