import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/auth/status', route => route.fulfill({ json: { profile: null } }));
  await page.route('**/api/v1/features', route => route.fulfill({ json: {} }));
  await page.route('**/api/v1/courses', route => route.fulfill({ json: { items: [{ id: 'zero', title: 'Programming from Zero', concept_count: 18, problem_count: 25 }] } }));
});

test('landing hero, paths, questions and navigation work on desktop and phone', async ({ page }, info) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Quick question before we start: what do you want to be able to do?');
  await expect(page.getByRole('link', { name: 'Get started', exact: true }).first()).toHaveAttribute('href', '/login');
  await expect(page.locator('.path-count')).toHaveText('18 skills · 25 judged problems');
  // How it works introduces the status system with shapes and labels.
  for (const label of ['Read', 'Check passed', 'Mastered']) await expect(page.getByText(label, { exact: true }).first()).toBeVisible();
  await expect(page.getByRole('radiogroup', { name: 'Your goal' })).toBeVisible();
  await page.getByText('Can I start without knowing how to code?', { exact: true }).click();
  await expect(page.locator('.landing-question', { hasText: 'Can I start without knowing how to code?' })).toHaveAttribute('open', '');
  await expect(page.getByRole('link', { name: /Get started with/ })).toHaveCount(3);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  // The nav floats as a pill just below the top edge.
  const nav = await page.locator('.landing-nav').boundingBox();
  expect(nav?.y).toBe(0);
  expect(nav?.height).toBeLessThan(100);
  if (info.project.name === 'mobile') {
    await page.getByRole('button', { name: 'Open navigation' }).click();
    await expect(page.getByRole('navigation', { name: 'Mobile site' })).toBeVisible();
    await page.getByRole('button', { name: 'Close navigation' }).press('Escape');
    await expect(page.getByRole('navigation', { name: 'Mobile site' })).toHaveCount(0);
  }
  const audit = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(audit.violations).toEqual([]);
  await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' });
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]);
});

test('landing is flat: inline SVG illustration, no canvas or WebGL, nav stays put on scroll', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('canvas')).toHaveCount(0);
  const hero = page.locator('section[aria-labelledby="hero-title"] svg[aria-hidden="true"]');
  await expect(hero.first()).toBeVisible();
  // The navigation wrapper remains fixed at the viewport top while scrolling.
  const navY = async () => (await page.locator('.landing-nav').boundingBox())?.y;
  await expect.poll(navY).toBe(0);
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await expect.poll(navY).toBe(0);
});

test('landing remains usable without the course API', async ({ page }) => {
  await page.route('**/api/v1/courses', route => route.fulfill({ status: 503, json: { error: { code: 'unavailable' } } }));
  await page.goto('/');
  await expect(page.getByRole('link', { name: /Get started with/ })).toHaveCount(3);
  await expect(page.locator('.path-count')).toHaveCount(0);
  await page.getByRole('link', { name: 'Get started', exact: true }).nth(1).click();
  await expect(page).toHaveURL(/\/login$/);
});
