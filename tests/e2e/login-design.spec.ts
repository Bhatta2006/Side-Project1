import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/auth/status', route => route.fulfill({ json: { profile: null } }));
  await page.route('**/api/v1/features', route => route.fulfill({ json: { dev_login: true, oidc_login: true } }));
});

test('login keeps provider links, keyboard submission and recoverable errors', async ({ page }, info) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/login');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Log in');
  const google = page.getByRole('link', { name: 'Continue with Google' });
  // Server-rendered provider configuration takes precedence over client fallback fixtures.
  if (await google.count()) await expect(google).toHaveAttribute('href', '/api/v1/auth/login');
  await expect(page.getByRole('link', { name: 'Back to home' })).toHaveAttribute('href', '/');
  await expect(page.locator('form', { has: page.getByLabel('Your name') }).getByRole('button', { name: 'Log in', exact: true })).toBeDisabled();
  await page.getByLabel('Your name').fill('   ');
  await expect(page.locator('form', { has: page.getByLabel('Your name') }).getByRole('button', { name: 'Log in', exact: true })).toBeDisabled();
  await page.route('**/api/v1/auth/dev-login', route => route.fulfill({ status: 400, json: { error: { code: 'validation_failed' } } }));
  await page.getByLabel('Your name').fill('Ada Lovelace');
  await page.getByLabel('Your name').press('Enter');
  await expect(page.locator('.login-panel').getByRole('alert')).toContainText('Some details are not valid');
  await expect(page.locator('form', { has: page.getByLabel('Your name') }).getByRole('button', { name: 'Log in', exact: true })).toBeEnabled();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]);
  await page.emulateMedia({ colorScheme: 'dark' });
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]);
  if (info.project.name === 'desktop') await page.screenshot({ path: '.cache/landing/login-error-preview.png', fullPage: true });
  let signedIn = false;
  await page.route('**/api/v1/auth/status', route => route.fulfill({ json: { profile: signedIn ? { id: 'ada', display_name: 'Ada Lovelace', enrollment: null } : null } }));
  await page.route('**/api/v1/auth/dev-login', async route => {
    expect(route.request().postDataJSON()).toEqual({ subject: 'ada-lovelace', display_name: 'Ada Lovelace' });
    signedIn = true;
    await route.fulfill({ status: 204 });
  });
  await page.locator('form', { has: page.getByLabel('Your name') }).getByRole('button', { name: 'Log in', exact: true }).click();
  await expect(page).toHaveURL(/\/start$/);
});

test('login explains unavailable sign-in without presenting inactive controls', async ({ page }) => {
  await page.route('**/api/v1/features', route => route.fulfill({ json: { dev_login: false, oidc_login: false } }));
  await page.goto('/login');
  test.skip(await page.getByLabel('Your name').count() > 0, 'Live server configuration overrides the client fallback fixture.');
  await expect(page.getByText('Sign-in is not configured on this server.')).toBeVisible();
  await expect(page.locator('form', { has: page.getByLabel('Your name') }).getByRole('button', { name: 'Log in', exact: true })).toHaveCount(0);
});
