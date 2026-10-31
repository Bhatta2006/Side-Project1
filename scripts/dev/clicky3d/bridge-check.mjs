// Drives a compiled film through the host bridge (play, pause, rate, step) in a sandboxed iframe.
import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';
const [htmlFile, cspFile] = process.argv.slice(2);
const html = readFileSync(htmlFile, 'utf8'), csp = readFileSync(cspFile, 'utf8');
const b = await chromium.launch({ channel: 'msedge' });
const page = await b.newPage();
await page.route('**/*', route => {
  const url = route.request().url();
  if (url === 'http://host.test/') return route.fulfill({ contentType: 'text/html', body: '<iframe sandbox="allow-scripts" src="http://visual.test/" width="1000" height="900"></iframe><script>window.states=[];addEventListener("message",e=>{if(e.data&&e.data.type==="state")window.states.push(e.data)});window.say=d=>document.querySelector("iframe").contentWindow.postMessage({...d,channel:"chan"},"*");</script>' });
  if (url === 'http://visual.test/') return route.fulfill({ contentType: 'text/html', headers: { 'Content-Security-Policy': csp.replace(/frame-ancestors [^;]+/, 'frame-ancestors http://host.test') }, body: html });
  return route.abort();
});
await page.goto('http://host.test/');
const last = () => page.evaluate(() => window.states[window.states.length - 1]);
await page.waitForFunction(() => window.states.length > 0, null, { timeout: 15000 });
const log = [];
log.push(['loaded', await last()]);
await page.evaluate(() => say({ type: 'pause' })); await page.waitForTimeout(300);
log.push(['after pause', await last()]);
await page.evaluate(() => say({ type: 'step', index: 4 })); await page.waitForTimeout(300);
log.push(['after step 4', await last()]);
await page.evaluate(() => { say({ type: 'rate', value: 2 }); say({ type: 'play' }); }); await page.waitForTimeout(300);
log.push(['after rate+play', await last()]);
for (const [what, s] of log) console.log(what.padEnd(16), JSON.stringify({ timed: s.timed, playing: s.playing, current: s.current, count: s.count }));
await b.close();
