// Types one message into the creation chat, waits, then reports the visible state.
const { chromium } = require('playwright');
(async () => {
  const [out, label, text, wait] = process.argv.slice(2);
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
  const page = browser.contexts()[0].pages()[0];
  const t0 = Date.now();
  if (text) {
    const box = page.locator('textarea').last();
    await box.fill(text);
    await box.press('Enter');
  }
  await page.waitForTimeout(Number(wait || 20000));
  await page.screenshot({ path: `${out}/${label}.png`, fullPage: true });
  console.log('url:', page.url(), '| waited ms:', Date.now() - t0);
  const main = await page.locator('main').first().innerText().catch(() => page.locator('body').innerText());
  console.log(main.slice(-1800).replace(/\n+/g, ' | '));
  const btns = await page.locator('button').evaluateAll(els => els.map(e => e.innerText.trim()).filter(t => t && t.length < 60));
  console.log('buttons:', JSON.stringify([...new Set(btns)].slice(-25)));
  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
