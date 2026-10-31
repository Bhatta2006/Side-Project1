import http from 'node:http';
import { timingSafeEqual } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { chromium } from 'playwright';
import { contextOptions, launchOptions, run } from './check-artifact.mjs';

// The secret may be mounted as a file (SOCRAT_EXPLAINER_CHECKER_SECRET_FILE) so it never sits in the environment.
const secretFile = process.env.SOCRAT_EXPLAINER_CHECKER_SECRET_FILE;
const token = (secretFile ? readFileSync(secretFile, 'utf8').trim() : process.env.SOCRAT_EXPLAINER_CHECKER_SECRET || '');
if (token.length < 32) throw Error('Configure a strong checker secret');
// Matches the API's default of four simultaneous generations; each check is one browser context.
const LIMIT = Number(process.env.SOCRAT_EXPLAINER_CHECKER_CONCURRENCY || 4);
const BUDGET_MS = 15_000;
const CLOSE_MS = 3_000;

// One warm browser for every check: launching Chromium per check cost seconds of the time budget
// and blamed slow starts on the visual. Each check gets its own fresh context.
let browser = null;
function warm() {
  if (!browser) {
    const launching = browser = chromium.launch(launchOptions());
    const forget = () => { if (browser === launching) browser = null; };
    launching.then(launched => launched.on('disconnected', forget), forget);
  }
  return browser;
}

async function check(input) {
  let current, context;
  try {
    current = await warm();
    context = await current.newContext(contextOptions);
  } catch (error) {
    return { ok: false, infrastructure: true, reason: 'Browser checker unavailable', detail: String(error.message).slice(0, 600) };
  }
  let timer;
  const work = run(context, input);
  work.catch(() => undefined); // still settles after a timeout, when its context is closed
  try {
    return await Promise.race([work, new Promise(resolve => { timer = setTimeout(() => resolve({ ok: false, reason: 'Visual exceeded the browser time budget' }), BUDGET_MS); })]);
  } catch (error) {
    // A browser that died mid-check (a crash, or another check's restart) is not the visual's fault.
    if (!current.isConnected()) return { ok: false, infrastructure: true, reason: 'Browser check did not complete' };
    return { ok: false, reason: String(error.message).slice(0, 1200) };
  } finally {
    clearTimeout(timer);
    const closed = await Promise.race([context.close().then(() => true, () => true), new Promise(resolve => setTimeout(() => resolve(false), CLOSE_MS))]);
    // A renderer that will not die (a runaway script) takes the browser with it; the next check relaunches.
    if (!closed) current.close().catch(() => undefined);
  }
}

let running = 0;
const server = http.createServer(async (request, response) => {
  const reply = (status, data) => { response.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }); response.end(JSON.stringify(data)); };
  if (request.url === '/health' && request.method === 'GET') {
    // Healthy only when the browser can actually launch.
    try { await warm(); return reply(200, { ok: true }); } catch { return reply(503, { ok: false }); }
  }
  const supplied = Buffer.from((request.headers.authorization || '').replace(/^Bearer /, ''));
  const expected = Buffer.from(token);
  if (request.url !== '/check' || request.method !== 'POST' || supplied.length !== expected.length || !timingSafeEqual(supplied, expected)) return reply(403, { error: 'forbidden' });
  if (running >= LIMIT) return reply(429, { error: 'busy' });
  running++;
  try {
    let raw = '';
    for await (const chunk of request) { raw += chunk; if (raw.length > 700_000) return reply(413, { error: 'too_large' }); }
    let input;
    try { input = JSON.parse(raw); } catch { return reply(400, { error: 'invalid_request' }); }
    reply(200, await check(input));
  } finally { running--; }
});
server.listen(Number(process.env.PORT || 8010), '0.0.0.0', () => {
  warm().catch(error => console.error(JSON.stringify({ browser: 'launch_failed', detail: String(error.message).slice(0, 600) })));
  console.log(JSON.stringify({ port: server.address().port }));
});
