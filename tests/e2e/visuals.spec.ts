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
