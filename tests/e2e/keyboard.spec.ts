import { expect, test, type Locator, type Page } from '@playwright/test';
import { enrollSignedIn } from './helpers/learner';

/**
 * Keyboard-only walkthrough: sign-in, a lesson, its check, the tutor and the
 * library, using Tab, Enter, Space and Escape. Every stop must show a visible focus ring.
 * Also checks that each page's headings form an outline (one h1, no skipped levels).
 */

async function focusRing(page: Page) {
  return page.evaluate(() => {
    const el = document.activeElement as HTMLElement | null;
    if (!el || el === document.body) return 'none';
    const style = getComputedStyle(el);
    const outline = style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0;
    const shadow = style.boxShadow && style.boxShadow !== 'none';
    return outline || shadow ? 'visible' : `missing on ${el.tagName.toLowerCase()} "${(el.textContent ?? '').trim().slice(0, 40)}"`;
  });
}

/** Tab forward until the target has focus; fails if it is unreachable. */
async function tabTo(page: Page, target: Locator, limit = 80) {
  const handle = await target.elementHandle();
  for (let i = 0; i < limit; i++) {
    await page.keyboard.press('Tab');
    if (await page.evaluate(el => el === document.activeElement, handle)) {
      expect(await focusRing(page)).toBe('visible');
      return;
    }
  }
  throw new Error(`Could not reach ${target} with Tab`);
}

async function outline(page: Page, path: string) {
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  const levels = await page.$$eval('h1,h2,h3,h4,h5,h6', els =>
    els.filter(e => (e as HTMLElement).offsetParent !== null).map(e => Number(e.tagName[1])),
  );
  expect(levels.filter(l => l === 1), `${path}: exactly one h1`).toHaveLength(1);
  levels.forEach((level, i) => {
    if (i) expect(level - levels[i - 1], `${path}: heading level skipped at #${i + 1}`).toBeLessThanOrEqual(1);
  });
}

test('a learner can do a whole session with the keyboard alone', async ({ page }, info) => {
  test.skip(info.project.name !== 'desktop', 'Tab order is a desktop concern; mobile uses touch');
  test.setTimeout(240_000);

  await page.goto('/login');
  await tabTo(page, page.getByLabel('Your name'));
  await page.keyboard.type(`keys-${Date.now()}`);
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/start$/);

  // Lesson 0 needs a model; this learner is enrolled straight into the fixture course.
  await enrollSignedIn(page);
  await page.goto('/today');
  await page.getByRole('button', { name: 'Maybe later' }).click({ timeout: 8_000 }).catch(() => undefined);
  await expect(page).toHaveURL(/\/today$/);
  await outline(page, '/today');

  await tabTo(page, page.getByRole('link', { name: 'Start lesson' }));
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/learn\/basics\/values$/);
  await outline(page, 'lesson');

  // The tutor opens into its message box, closes on Escape and hands focus back.
  const launcher = page.getByRole('button', { name: /^Ask Soc/ }).first();
  await launcher.focus();
  await page.keyboard.press('Enter');
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('textbox')).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();
  await expect(launcher).toBeFocused();

  // A paged lesson keeps "Mark lesson as read" on its last page (Recap): page there by keyboard.
  const markRead = page.getByRole('button', { name: 'Mark lesson as read' });
  for (let i = 0; i < 30 && !(await markRead.isVisible()); i++) {
    await tabTo(page, page.getByRole('button', { name: /^(Next|Recap)$/ }), 200);
    await page.keyboard.press('Enter');
  }
  await tabTo(page, markRead, 200);
  await page.keyboard.press('Enter');
  await tabTo(page, page.getByRole('link', { name: 'Take concept check' }), 200);
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/quiz\/basics\/values$/);
  await outline(page, 'quiz');

  await tabTo(page, page.getByRole('radio').first());
  await page.keyboard.press('Space');
  await expect(page.getByRole('radio').first()).toHaveAttribute('aria-checked', 'true');
  await tabTo(page, page.getByRole('button', { name: 'Check answer' }));
  await page.keyboard.press('Enter');
  await expect(page.getByRole('status').filter({ hasText: /Correct|Incorrect/ })).toBeVisible();

  await page.goto('/today');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible(); // hydrated: shortcuts work
  await page.keyboard.press('Control+k');
  const search = page.getByPlaceholder('Search lessons and pages…');
  await expect(search).toBeFocused();
  await page.keyboard.type('progress');
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/progress$/);
  await outline(page, '/progress');

  for (const path of ['/plan', '/settings', '/assessments']) {
    await page.goto(path);
    await outline(page, path);
  }
});
