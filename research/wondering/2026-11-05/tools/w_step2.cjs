const { chromium } = require('playwright');
(async () => {
  const out = process.argv[2];
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
  const page = browser.contexts()[0].pages()[0];
  await page.getByText('SIGN IN', { exact: true }).first().click();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: out + '/02-signin.png' });
  const email = page.getByText(/Continue with email/i).first();
  console.log('email option visible:', await email.isVisible().catch(() => false));
  if (await email.isVisible().catch(() => false)) {
    await email.click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: out + '/03-email-form.png' });
    const inputs = await page.locator('input').evaluateAll(els => els.map(e => ({ type: e.type, name: e.name, placeholder: e.placeholder, visible: !!(e.offsetWidth || e.offsetHeight) })));
    console.log('inputs:', JSON.stringify(inputs));
  }
  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
