const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
  const ctx = browser.contexts()[0];
  const page = ctx.pages()[0] || await ctx.newPage();
  await page.goto('https://wondering.app/', { waitUntil: 'networkidle', timeout: 60000 });
  await page.screenshot({ path: process.argv[2] + '/01-landing.png' });
  const buttons = await page.locator('button, a[role=button], a').evaluateAll(els => els.map(e => (e.innerText || e.getAttribute('aria-label') || '').trim()).filter(t => t && t.length < 40));
  console.log('clickables:', JSON.stringify([...new Set(buttons)].slice(0, 40)));
  await browser.close(); // disconnects only; the browser keeps running
})().catch(e => { console.error(e.message); process.exit(1); });
