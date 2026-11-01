// Dev only: open a compiled film page straight from disk and report whether it plays.
//   node scripts/dev/clicky3d/open-check.mjs <page.html> <out.png>
import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';

const [file, out] = process.argv.slice(2);
const browser = await chromium.launch({ channel: 'msedge', args: ['--use-angle=d3d11', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1100, height: 1000 } });
const errors = [];
page.on('pageerror', e => errors.push(e.message));
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
await page.goto(pathToFileURL(file).href);
await page.waitForTimeout(2500);
const state = await page.evaluate(() => ({
  player: !!window.__explainer, chapters: window.__explainer ? window.__explainer.stepCount : 0,
  canvas: !!document.querySelector('canvas'), explode: !!document.querySelector('button[aria-label="Explode into parts"]'),
}));
console.log(JSON.stringify(state), errors.length ? 'errors: ' + errors.join(' | ').slice(0, 400) : 'no errors');
await page.screenshot({ path: out });
await browser.close();
