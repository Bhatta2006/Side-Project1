const { chromium } = require('playwright');
(async () => {
  const out = process.argv[2];
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
  const page = browser.contexts()[0].pages()[0];
  await page.locator('input[autocomplete=one-time-code]').fill(process.argv[3]);
  await page.getByRole('button', { name: /verify and continue/i }).click();
  await page.waitForTimeout(6000);
  await page.screenshot({ path: out + '/05-after-login.png' });
  console.log('url:', page.url());
  console.log((await page.locator('body').innerText()).slice(0, 700).replace(/\n+/g, ' | '));
  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
