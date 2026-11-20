import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

/** WCAG 2.1 A/AA checks on every main page, light and dark. Serious or critical issues fail. */
const PAGES = [
  '/today', '/plan', '/assessments', '/progress', '/settings',
  '/learn/zero/programs-and-output', '/problems/double-it', '/quiz/zero/programs-and-output',
  '/quiz/checkpoint/zero/first-steps',
];

async function audit(page: Page, label: string, found: string[]) {
  // Fades still run under reduced motion; measure contrast on the settled page.
  await page.waitForFunction(() => document.getAnimations().every(a => a.playState !== 'running'), null, { timeout: 10_000 }).catch(() => undefined);
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .exclude('.cm-editor') // CodeMirror manages its own ARIA; covered by its own tests
    .analyze();
  for (const v of results.violations) {
    if (v.impact !== 'serious' && v.impact !== 'critical') continue;
    const nodes = v.nodes.slice(0, 4).map(n => `${n.target.join(' ')} | ${(n.failureSummary ?? '').split('\n').slice(1, 2).join('').trim()}`);
    found.push([`${label} :: ${v.id} (${v.impact}): ${v.help}`, ...nodes.map(n => `    ${n}`)].join('\n'));
  }
}

for (const scheme of ['light', 'dark'] as const) {
  test(`accessibility · ${scheme}`, async ({ page }, info) => {
    test.skip(info.project.name !== 'desktop', 'one viewport is enough for rule checks');
    test.setTimeout(240_000);
    const found: string[] = [];
    await page.emulateMedia({ colorScheme: scheme, reducedMotion: 'reduce' });
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await audit(page, `${scheme} /`, found);
    await page.goto('/login');
    await audit(page, `${scheme} /login`, found);
    await page.getByLabel('Your name').fill(`a11y ${scheme} ${Date.now()}`);
    await page.getByRole('button', { name: 'Log in' }).click();
    await expect(page.getByLabel('What should we call you?')).toBeVisible();
    await audit(page, `${scheme} /start`, found);
    await page.getByLabel('What should we call you?').fill('Ada');
    await page.getByLabel('Year you were born').selectOption('2001');
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.getByRole('button', { name: /Programming from Zero/ }).click();
    await page.getByRole('button', { name: /never written code/ }).click();
    await page.getByRole('button', { name: 'Python', exact: true }).click();
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.getByRole('button', { name: 'Create my plan' }).click();
    await expect(page).toHaveURL(/\/today$/);
    for (const path of PAGES) {
      await page.goto(path);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(400);
      await audit(page, `${scheme} ${path}`, found);
    }
    expect(found.length, `${found.length} serious accessibility issues\n${found.join('\n')}`).toBe(0);
  });
}
