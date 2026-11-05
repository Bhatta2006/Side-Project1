const { chromium } = require('playwright');
(async () => {
  const [out, label, text, wait] = process.argv.slice(2);
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
  const page = browser.contexts()[0].pages()[0];
  const t0 = Date.now();
  await page.getByText(text, { exact: true }).first().click();
  await page.waitForTimeout(Number(wait || 15000));
  await page.screenshot({ path: `${out}/${label}.png` });
  console.log('url:', page.url(), '| waited ms:', Date.now() - t0);
  console.log((await page.locator('body').innerText()).slice(0, 1500).replace(/\n+/g, ' | '));
  const btns = await page.locator('button:visible').evaluateAll(els => els.map(e => e.innerText.trim() || e.getAttribute('aria-label') || '').filter(t => t && t.length < 60));
  console.log('buttons:', JSON.stringify([...new Set(btns)].slice(-20)));
  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
