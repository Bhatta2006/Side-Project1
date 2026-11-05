const { chromium } = require('playwright');
(async () => {
  const out = process.argv[2];
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
  const page = browser.contexts()[0].pages()[0];
  await page.locator('input[type=email]').fill('<email>');
  await page.getByRole('button', { name: /send code/i }).click();
  await page.waitForTimeout(4000);
  await page.screenshot({ path: out + '/04-code-sent.png' });
  const text = (await page.locator('body').innerText()).slice(0, 600);
  console.log(text.replace(/\n+/g, ' | '));
  const inputs = await page.locator('input').evaluateAll(els => els.map(e => ({ type: e.type, inputmode: e.inputMode, maxlength: e.maxLength, autocomplete: e.autocomplete })));
  console.log('inputs:', JSON.stringify(inputs));
  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
