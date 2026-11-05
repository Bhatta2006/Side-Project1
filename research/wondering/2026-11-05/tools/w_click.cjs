const { chromium } = require('playwright');
(async () => {
  const [out, label, name, wait] = process.argv.slice(2);
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
  const page = browser.contexts()[0].pages()[0];
  const t0 = Date.now();
  const target = name.startsWith('i:') ? new RegExp(name.slice(2).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i') : name;
  await page.getByRole('button', { name: target, exact: !name.startsWith('i:') }).last().click();
  await page.waitForTimeout(Number(wait || 20000));
  await page.screenshot({ path: `${out}/${label}.png`, fullPage: true });
  console.log('url:', page.url(), '| waited ms:', Date.now() - t0);
  const main = await page.locator('main').first().innerText().catch(() => page.locator('body').innerText());
  console.log(main.slice(-1600).replace(/\n+/g, ' | '));
  const btns = await page.locator('button').evaluateAll(els => els.map(e => e.innerText.trim()).filter(t => t && t.length < 60));
  console.log('buttons:', JSON.stringify([...new Set(btns)].slice(-25)));
  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
