// Live browser journey: a new visitor goes through /start (Lesson 0) with the real model, gets a
// plan, starts learning, opens the first lesson, reads it to the end and takes its check.
//
// Needs: scripts/dev/live-journey-api.ps1 on :8000 and `npm run dev` on :3000.
// Usage:  node scripts/dev/journey.mjs <out-dir> ["goal text"]
// Writes a numbered screenshot per step and journey.json (timings, every step's outcome) to out-dir.
import { chromium } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const out = process.argv[2] ?? '.cache/journey/run';
const goal = process.argv[3] ?? 'Write SQL queries to answer questions about my own data';
const BASE = process.env.JOURNEY_BASE ?? 'http://localhost:3000';
mkdirSync(out, { recursive: true });

const log = { goal, started: new Date().toISOString(), steps: [], timings: {} };
const t0 = Date.now();
let shot = 0;
const browser = await chromium.launch({ channel: process.env.PW_CHANNEL ?? 'msedge', headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const errors = [];
page.on('response', r => { if (r.url().includes('/api/') && r.status() >= 500) errors.push(`${r.status()} ${r.request().method()} ${r.url()}`); });
page.on('pageerror', e => errors.push(`pageerror ${e.message}`));

const since = () => Math.round((Date.now() - t0) / 1000);
async function snap(name) {
  const file = path.join(out, `${String(++shot).padStart(2, '0')}-${name}.png`);
  await page.screenshot({ path: file, fullPage: true }).catch(() => undefined);
  return file;
}
async function step(name, fn) {
  const start = Date.now();
  try {
    const note = await fn();
    log.steps.push({ name, ok: true, seconds: Math.round((Date.now() - start) / 1000), at: since(), note: note ?? null, shot: await snap(name) });
    console.log(`ok   ${name} (${Math.round((Date.now() - start) / 1000)} s)${note ? ` - ${note}` : ''}`);
  } catch (e) {
    log.steps.push({ name, ok: false, at: since(), error: String(e).slice(0, 600), shot: await snap(`${name}-FAILED`) });
    console.log(`FAIL ${name}: ${String(e).slice(0, 300)}`);
    throw e;
  }
}
// isVisible() does not wait; this does, up to ms.
const visible = (loc, ms = 1500) => loc.first().waitFor({ state: 'visible', timeout: ms }).then(() => true, () => false);
const button = name => page.getByRole('button', { name });

/** The welcome tour and the plans dialog open a moment after the page; close whichever appear. */
async function dismissOverlays(ms = 8000) {
  const overlay = button('Skip tour').or(button('Maybe later'));
  for (let i = 0; i < 3 && await visible(overlay, i ? 2000 : ms); i++) {
    await overlay.first().click().catch(() => undefined);
    await page.waitForTimeout(300);
  }
}

/** Answer one Lesson 0 task (win or snag): the first option, then the stuck button if needed. */
async function answerTask() {
  const options = page.getByRole('radiogroup', { name: 'Your answer' }).getByRole('radio');
  await options.first().waitFor({ timeout: 120_000 });
  await options.first().click();
  const cont = button(/^Continue/);
  const stuck = button(/stuck, show me/);
  for (let i = 0; i < 60; i++) {
    if (await visible(cont, 500)) return cont.click();
    if (await visible(stuck, 500)) { await stuck.click(); continue; }
    if (i % 4 === 3) { // a wrong first try: try the next option
      const n = await options.count();
      const free = options.nth(Math.min(n - 1, 1 + Math.floor(i / 4)));
      if (await free.isEnabled().catch(() => false)) await free.click().catch(() => undefined);
    }
    await page.waitForTimeout(1000);
  }
  throw new Error('task never offered Continue');
}

let code = 0;
try {
  await step('goal', async () => {
    await page.goto(`${BASE}/start`);
    await page.getByLabel('What you want to be able to do').fill(goal);
    await button(/^Continue/).click();
  });
  await step('mode', async () => { await page.getByRole('button', { name: /^Builder/ }).click(); });
  await step('door', async () => {
    await page.getByText('Pick your door').waitFor({ timeout: 90_000 });
    const doors = page.locator('button[aria-pressed]');
    const first = await doors.first().innerText();
    await doors.first().click();
    return `door: ${first.trim()}`;
  });
  await step('time', async () => { await page.getByRole('button', { name: /^25 min/ }).click(); });
  await step('win', async () => {
    const prompt = await page.getByRole('heading', { level: 1 }).innerText({ timeout: 120_000 }).catch(() => '');
    await answerTask();
    return prompt.slice(0, 120);
  });
  // After the warm-up: the snag task, its reveal, or straight to saving.
  const save = button(/test learner \(development\)/);
  await page.getByText('one step further').or(save).first().waitFor({ timeout: 120_000 });
  if (await visible(page.getByText('one step further'), 500)) await step('snag', answerTask);
  if (await visible(button(/Build my course from here/), 15_000)) await step('reveal', () => button(/Build my course from here/).click());
  await step('save', async () => {
    await button(/test learner \(development\)/).click({ timeout: 60_000 });
    const year = page.getByLabel('Year you were born');
    if (await visible(year, 10_000)) {
      await year.selectOption('1998');
      await button(/^Save my course/).click();
    }
  });
  await step('plan (T1)', async () => {
    await page.getByRole('button', { name: /^Start learning/ }).or(page.getByRole('group', { name: 'Where to start' })).first().waitFor({ timeout: 600_000 });
    log.timings.T1_plan_seconds = since();
    const offer = page.getByRole('group', { name: 'Where to start' });
    if (await visible(offer, 1000)) { await button('Start there').click(); return 'level_suggestion offered: took it'; }
  });
  await step('first lesson ready (T2)', async () => {
    const start = button(/^Start learning/);
    const retry = button('Try again');
    for (let i = 0; i < 900; i++) {
      if (await visible(retry, 300)) { await retry.click(); log.retriedFirstLesson = true; }
      if (await start.isEnabled({ timeout: 300 }).catch(() => false) && await visible(start, 300)) break;
      await page.waitForTimeout(1000);
    }
    log.timings.T2_first_lesson_seconds = since();
    await start.click();
  });
  await step('today', async () => {
    await page.waitForURL(/\/today/, { timeout: 60_000 });
    await dismissOverlays();
    await page.getByRole('link', { name: 'Start lesson' }).first().click({ timeout: 30_000 });
  });
  await step('lesson', async () => {
    await page.waitForURL(/\/learn\//, { timeout: 60_000 });
    await dismissOverlays();
    const title = await page.getByRole('heading', { level: 1 }).innerText().catch(() => '');
    let pages = 1;
    const mark = button('Mark lesson as read');
    while (!(await visible(mark, 800)) && pages < 40) {
      await button(/^(Next|Recap)$/).click({ timeout: 10_000 });
      pages++;
    }
    await mark.click();
    return `${title} (${pages} pages)`;
  });
  await step('concept check', async () => {
    await page.getByRole('link', { name: 'Take concept check' }).click({ timeout: 30_000 });
    await page.waitForURL(/\/quiz\//, { timeout: 60_000 });
    let answered = 0;
    for (let i = 0; i < 25; i++) {
      const radio = page.getByRole('radio').first();
      const checkBtn = button('Check answer');
      if (await visible(radio, 3000) && await visible(checkBtn, 500)) {
        await radio.click();
        await checkBtn.click();
        await page.getByRole('status').filter({ hasText: /Correct|Incorrect|Not quite|Right/ }).first().waitFor({ timeout: 30_000 }).catch(() => undefined);
        answered++;
      }
      const next = button(/^(Next question|Next|See results|Finish|Done)$/);
      if (await visible(next, 1500)) { await next.click(); continue; }
      if (!(await visible(checkBtn, 1500))) break;
    }
    return `${answered} questions answered`;
  });
  await step('today after the check', async () => {
    await page.goto(`${BASE}/today`);
    await dismissOverlays();
    await page.getByRole('heading', { level: 1 }).waitFor({ timeout: 30_000 });
  });
} catch {
  code = 1;
} finally {
  log.errors = errors;
  log.finished = new Date().toISOString();
  log.total_seconds = since();
  writeFileSync(path.join(out, 'journey.json'), JSON.stringify(log, null, 2));
  console.log(`\n${code ? 'STOPPED' : 'COMPLETE'} after ${log.total_seconds} s; T1 ${log.timings.T1_plan_seconds ?? '-'} s, T2 ${log.timings.T2_first_lesson_seconds ?? '-'} s; server errors: ${errors.length}`);
  errors.forEach(e => console.log(`  ${e}`));
  await browser.close();
  process.exit(code);
}
