import { expect, test, type Page } from '@playwright/test';
import { RIGHT } from './helpers/answer-keys';
import { enrollSignedIn, grantPlus, readToEnd } from './helpers/learner';
import type { AdaptiveSession, AdaptiveAnswer } from '../../apps/web/src/lib/types';

test.describe.configure({ timeout: 90000 });

/** One learner's first session through the v2 web app, on desktop and mobile. */

async function signIn(page: Page, name: string) {
  await page.goto('/login');
  await page.getByLabel('Your name').fill(name);
  await page.locator('form', { has: page.getByLabel('Your name') }).getByRole('button', { name: 'Log in' }).click();
  await expect(page).toHaveURL(/\/start$/);
}

/** Lesson 0 needs a model (it has its own spec); here the learner is enrolled straight into a
 * fixture course (services/api/tests/content_fixture.py) and lands where the app sends them. */
async function onboard(page: Page, course: 'basics' | 'algo', level: string) {
  await enrollSignedIn(page, course, level);
  await page.goto(level === 'brand-new' ? '/today' : '/placement');
  await page.getByRole('button', { name: 'Maybe later' }).click({ timeout: 8_000 }).catch(() => undefined);
}

test('a beginner reads a lesson, passes its check and sees progress', async ({ page }, info) => {
  await signIn(page, `beginner-${info.project.name}-${Date.now()}`);
  await onboard(page, 'basics', 'brand-new');

  await expect(page).toHaveURL(/\/today$/);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Ada');
  await expect(page.getByRole('heading', { name: 'Values' })).toBeVisible();
  await page.getByRole('link', { name: 'Start lesson' }).click();

  await expect(page).toHaveURL(/\/learn\/basics\/values$/);
  // Only the learner's language variant of a code sample is ever shown.
  await expect(page.locator('pre[data-lang="cpp"], pre[data-lang="java"]')).toHaveCount(0);
  await readToEnd(page);
  const started = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/adaptive-quiz/sessions'));
  await page.getByRole('link', { name: 'Take concept check' }).click();

  await expect(page).toHaveURL(/\/quiz\/basics\/values$/);
  let session = await (await started).json() as AdaptiveSession;
  while (!session.finished) {
    const question = session.current!;
    expect(question.item).toBeTruthy();
    await page.getByRole('radio', { name: RIGHT, exact: true }).click();
    const answered = page.waitForResponse(r => r.request().method() === 'POST' && /\/adaptive-quiz\/sessions\/[^/]+\/answer$/.test(r.url()));
    await page.getByRole('button', { name: 'Check answer' }).click();
    const result = await (await answered).json() as AdaptiveAnswer;
    expect(result.outcome).toBe('correct');
    session = result.session;
    await expect(page.getByRole('status').filter({ hasText: 'Correct' })).toBeVisible();
    await page.getByRole('button', { name: /Next question|See results/ }).click();
  }
  expect(session.passed).toBe(true);
  await expect(page.getByText(/of \d+ correct/)).toBeVisible();
  await page.getByRole('link', { name: 'Continue' }).click();

  await expect(page).toHaveURL(/\/today$/);
  await expect(page.getByText('Values check', { exact: true }).first()).toBeVisible();
  await page.goto('/progress');
  await expect(page.getByRole('heading', { name: 'Mastery by module' })).toBeVisible();
  await page.goto('/plan');
  await expect(page.getByRole('heading', { name: 'Modules' })).toBeVisible();
});

test('placement adapts, then practice and the Socratic tutor work', async ({ page }, info) => {
  test.setTimeout(180_000); // the tutor may call a live model
  await signIn(page, `placed-${info.project.name}-${Date.now()}`);
  await onboard(page, 'basics', 'some');

  await expect(page).toHaveURL(/\/placement$/);
  const ready = page.getByRole('heading', { name: 'Your plan is ready' });
  const counter = page.getByText(/^Question \d+ of at most \d+$/);
  for (let asked = 0; asked < 25; asked++) {
    await expect(counter.or(ready)).toBeVisible();
    if (await ready.isVisible()) break;
    const before = await counter.textContent();
    await page.getByRole('button', { name: 'Not sure yet' }).click();
    await expect(ready.or(counter.filter({ hasNotText: before ?? '' }))).toBeVisible();
  }
  await page.getByRole('link', { name: 'See your plan' }).click();
  await expect(page).toHaveURL(/\/today$/);

  await page.goto('/problems/sum-loop');
  await expect(page.getByRole('heading', { name: 'Sum Loop' })).toBeVisible();
  await expect(page.getByTestId('code-editor')).toBeVisible();
  await expect(page.getByText('Draft saved')).toBeVisible();

  await page.getByRole('button', { name: 'Ask Soc' }).click();
  const tutor = page.getByRole('dialog', { name: 'Ask Soc' });
  await expect(tutor).toBeVisible();
  await tutor.getByRole('button', { name: 'Give me a hint' }).click();
  // A live model (when one is configured) takes longer than the curated offline reply.
  await expect(tutor.locator('.chat-bubble-assistant').last()).toHaveText(/\w/, { timeout: 90_000 });
  // The walkthrough is not offered after one hint; it appears only once real help has been given.
  await expect(tutor.getByRole('button', { name: 'Give me a hint' })).toBeEnabled({ timeout: 90_000 });
  await expect(tutor.getByRole('button', { name: 'Show solution' })).toHaveCount(0);
  await page.keyboard.press('Escape');
  await expect(tutor).toBeHidden();

  await page.goto('/settings');
  await page.getByRole('button', { name: '20 min' }).click();
  await page.getByRole('button', { name: 'Save changes' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Saved' })).toBeVisible();
  await page.goto('/plan');
  await page.getByText('Why did my plan change?').click();
  await expect(page.getByText(/You updated your plan: 20 min per study day/).first()).toBeVisible();
});

test('later modules are locked behind a checkpoint that gets harder', async ({ page }, info) => {
  await signIn(page, `gate-${info.project.name}-${Date.now()}`);
  await onboard(page, 'basics', 'brand-new');
  await expect(page).toHaveURL(/\/today$/);

  await page.goto('/plan');
  const go = page.getByRole('link', { name: 'Go to checkpoint' }).first();
  await expect(go).toBeVisible();
  await go.click();
  await expect(page).toHaveURL(/\/quiz\/checkpoint\//);
  await expect(page.getByRole('img', { name: /Difficulty level \d of \d/ })).toBeVisible();
  for (let i = 0; i < 12; i++) {
    const results = page.getByRole('heading', { name: /unlocked|Not yet/ });
    if (await results.isVisible()) break;
    const counter = page.getByText(/^\d+ \/ up to \d+$/);
    const before = await counter.textContent();
    await page.getByRole('radio').first().click();
    await page.getByRole('button', { name: 'Check answer' }).click();
    await expect(results.or(counter.filter({ hasNotText: before ?? '' }))).toBeVisible();
  }
  await expect(page.getByRole('heading', { name: /unlocked|Not yet/ })).toBeVisible();
});

test('a weekly assessment is built from what the learner studied', async ({ page }, info) => {
  test.setTimeout(120_000);
  await signIn(page, `weekly-${info.project.name}-${Date.now()}`);
  await onboard(page, 'basics', 'brand-new');
  await expect(page).toHaveURL(/\/today$/);

  // Weekly assessments are a Founding Member feature: Free sees the offer, a paid plan the exam.
  await page.goto('/assessments');
  await expect(page.getByRole('button', { name: 'Unlock weekly assessments' })).toBeVisible();
  await grantPlus(page);
  await page.reload();
  await expect(page.getByText(/unlocks as you study/)).toBeVisible();
  for (const concept of ['values', 'text']) {
    await page.goto(`/learn/basics/${concept}`);
    await readToEnd(page);
    await expect(page.getByRole('heading', { name: 'Lesson read' })).toBeVisible();
  }

  await page.goto('/assessments');
  await page.getByRole('button', { name: /^Start the \d+-minute exam/ }).click();
  const save = page.getByRole('button', { name: 'Save answer' });
  for (let i = 0; i < 15 && (await save.isVisible()); i++) {
    await page.getByRole('radio').first().click();
    await save.click();
    // Wait for the saved answer to register before touching the next question.
    await expect(page.getByText(new RegExp(`\\. ${i + 1} answered`))).toBeVisible();
  }
  await page.getByRole('button', { name: 'Submit assessment' }).click();
  await page.getByRole('button', { name: 'Submit', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'By topic' })).toBeVisible();
  await expect(page.getByText('Values').first()).toBeVisible();
});
