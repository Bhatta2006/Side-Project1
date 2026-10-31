// Dev harness: renders Clicky3D scenes and films without the LLM. Usage:
//   node scripts/dev/clicky3d/harness.mjs <scene.js|film.json> <out.png> [--debug N] [--wait ms] [--yaw deg] [--t s] [--step k] [--dark]
// scene.js is a script that defines `const SCENE = {...}` (or a function scene(t)).
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { chromium } from 'playwright';

const here = dirname(fileURLToPath(import.meta.url));
const kitDir = resolve(here, '../../../services/api/src/socrat/explainer');
const args = process.argv.slice(2);
const flag = (name, d) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : d; };
const [sceneFile, out] = args;
const stage = ['clicky3d-geometry.js', 'clicky3d-render.js', 'clicky3d.js'].map(f => readFileSync(join(kitDir, f), 'utf8'));
const width = +flag('--width', 1100), height = +flag('--height', 760);
// Same tokens and fonts the compiler injects: the app's palette (light or --dark) and Geist.
const repo = resolve(here, '../../..');
const css = readFileSync(join(repo, 'apps/web/src/app/globals.css'), 'utf8');
const dark = args.includes('--dark');
const block = css.match(new RegExp('^' + (dark ? String.raw`\.dark` : ':root') + String.raw`\s*\{([\s\S]*?)^\}`, 'm'));
const card = (block ? block[1] : '').match(/--card:\s*([^;]+);/);
const font = (family, file, weight) => `@font-face{font-family:"${family}";src:url(data:font/woff2;base64,${readFileSync(join(repo, 'apps/web/src/fonts', file)).toString('base64')}) format("woff2");font-weight:${weight};font-display:block}`;
const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
${font('Geist', 'geist-wght.woff2', '100 900')}
:root{${block ? block[1] : ''};color-scheme:${dark ? 'dark' : 'light'};--sans:"Geist",ui-sans-serif,system-ui,sans-serif;--background:${card ? card[1] : '#FFFFFF'}}
html,body{margin:0;background:var(--card);color:var(--foreground);font-family:var(--sans)}#board{width:${width}px}</style>
${stage.map(s => `<script>${s}</script>`).join('')}</head><body><div id="board"></div>
<script>${sceneFile.endsWith('.json') ? `
// Films: seek to --t seconds (or the settled state of chapter --step) and hold still.
const player = Clicky3D.film('#board', ${readFileSync(sceneFile, 'utf8')}, {autoplay:false});
window.__player = player;
if (${flag('--step', 'null')} !== null) player.step(${flag('--step', 'null')}); else player.seek(${flag('--t', 0)});
// Explore: --explode takes it apart; --inspect <label id> opens that part's card.
if (${args.includes('--explode')}) player.explode(true);
if (${JSON.stringify(flag('--inspect', ''))}) player.inspect(${JSON.stringify(flag('--inspect', ''))});
` : `${readFileSync(sceneFile, 'utf8')}
const board = Clicky3D.mount('#board', {desc:'harness'});
window.__board = board;
const sc = typeof SCENE === 'function' ? SCENE() : SCENE;
if (${flag('--debug', 0)}) sc.debug = ${flag('--debug', 0)};
if (${flag('--yaw', 'null')} !== null) sc.camera = Object.assign({}, sc.camera, {yaw:${flag('--yaw', 'null')}});
sc.camera = Object.assign({spin:0}, sc.camera, {spin:0});
board.draw(sc);
`}
</script></body></html>`;
const dir = mkdtempSync(join(tmpdir(), 'c3d-'));
const file = join(dir, 'h.html');
writeFileSync(file, html);
const browser = await chromium.launch({ channel: 'msedge', args: ['--use-angle=d3d11', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: width + 40, height: height + 40 }, deviceScaleFactor: +flag('--dpr', 1.5) });
page.on('pageerror', e => console.log('pageerror:', e.message));
page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log('console:', m.text()); });
await page.goto(pathToFileURL(file).href);
await page.waitForTimeout(+flag('--wait', 1200));
if (args.includes('--measure')) console.log(await page.evaluate(() => [...(document.querySelector('.clicky3d-film') || document.body).children, ...(document.querySelector('.clicky3d-film') || document.body).firstElementChild.querySelectorAll('*')].slice(0, 12).map(el => { const r = el.getBoundingClientRect(); return el.tagName + ' ' + r.top.toFixed(1) + '..' + r.bottom.toFixed(1); }).join(' | ')));
await page.locator('#board').screenshot({ path: out });
await browser.close();
console.log('wrote', out);
