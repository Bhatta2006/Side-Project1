// Screenshots a compiled explainer page: node scripts/dev/clicky3d/page.mjs <page.html> <out.png>
import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';
const [file, out] = process.argv.slice(2);
const b = await chromium.launch({ channel: 'msedge', args: ['--use-angle=d3d11','--ignore-gpu-blocklist'] });
const p = await b.newPage({ viewport: { width: 900, height: 1000 }, deviceScaleFactor: 1.5 });
p.on('pageerror', e => console.log('pageerror', e.message));
await p.goto(pathToFileURL(file).href); await p.waitForTimeout(+(process.argv[4] || 2500));
await p.screenshot({ path: out, fullPage: true }); await b.close();
