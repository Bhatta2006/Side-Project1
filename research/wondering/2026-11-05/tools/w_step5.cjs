const { chromium } = require('playwright');
(async () => {
  const out = process.argv[2];
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
  const page = browser.contexts()[0].pages()[0];
  await page.getByText('Create', { exact: true }).first().click();
  await page.waitForTimeout(3000);
  await page.screenshot({ path: out + '/06-create.png' });
  console.log('url:', page.url());
  console.log((await page.locator('main, body').first().innerText()).slice(0, 1200).replace(/\n+/g, ' | '));
  const inputs = await page.locator('input, textarea').evaluateAll(els => els.map(e => ({ tag: e.tagName, type: e.type, placeholder: e.placeholder })));
  console.log('inputs:', JSON.stringify(inputs));
  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
