// Model code is parsed as data, then executed only in a fresh sandboxed browser frame.
import acorn from 'next/dist/compiled/acorn/acorn.js';
import { chromium } from 'playwright';

const reserved = new Set(['eval','Function','AsyncFunction','GeneratorFunction','fetch','XMLHttpRequest','WebSocket','EventSource','Worker','SharedWorker','ServiceWorker','navigator','location','parent','top','opener','frames','globalThis','self','localStorage','sessionStorage','indexedDB','caches','Reflect','Proxy','WebAssembly','Atomics','SharedArrayBuffer','alert','prompt','confirm']);
const forbiddenProperties = new Set(['constructor','__proto__','prototype','cookie','defaultView','location','domain','write','writeln','open','postMessage','sendBeacon','registerProtocolHandler','serviceWorker','contentWindow','contentDocument']);
const windowProperties = new Set(['__explainer','getComputedStyle','matchMedia','innerWidth','innerHeight','devicePixelRatio','addEventListener','removeEventListener','requestAnimationFrame','cancelAnimationFrame','setTimeout','clearTimeout','setInterval','clearInterval']);

const patternNames = pattern => !pattern ? [] :
  pattern.type === 'Identifier' ? [pattern.name] :
  pattern.type === 'ObjectPattern' ? pattern.properties.flatMap(p => patternNames(p.type === 'RestElement' ? p.argument : p.value)) :
  pattern.type === 'ArrayPattern' ? pattern.elements.flatMap(patternNames) :
  pattern.type === 'AssignmentPattern' ? patternNames(pattern.left) :
  pattern.type === 'RestElement' ? patternNames(pattern.argument) : [];
const declarationNames = statement =>
  statement?.type === 'VariableDeclaration' ? statement.declarations.flatMap(d => patternNames(d.id)) :
  ['FunctionDeclaration','ClassDeclaration'].includes(statement?.type) ? [statement.id.name] : [];
// Names a scope node binds for its own subtree, so a local `parent` is not the browser's parent.
// ponytail: a `var` nested in an inner block only counts inside that block; a false rejection, never a false pass.
function declared(node) {
  switch (node.type) {
    case 'Program': case 'BlockStatement': case 'StaticBlock': return node.body.flatMap(declarationNames);
    case 'SwitchStatement': return node.cases.flatMap(c => c.consequent.flatMap(declarationNames));
    case 'FunctionDeclaration': case 'FunctionExpression': case 'ArrowFunctionExpression':
      return [...node.params.flatMap(patternNames), ...(node.type === 'FunctionExpression' && node.id ? [node.id.name] : [])];
    case 'ClassExpression': return node.id ? [node.id.name] : [];
    case 'ForStatement': return declarationNames(node.init);
    case 'ForInStatement': case 'ForOfStatement': return declarationNames(node.left);
    case 'CatchClause': return patternNames(node.param);
    default: return null;
  }
}

export function inspectScripts(scripts) {
  for (const script of scripts) {
    let root;
    try { root = acorn.parse(script, { ecmaVersion: 'latest', sourceType: 'script' }); }
    catch (error) { throw Error(`JavaScript syntax error at script line ${error.loc?.line}: ${script.split('\n')[(error.loc?.line || 1)-1].trim().slice(0,140)}`); }
    const pending = [[root, null, '', new Set()]];
    while (pending.length) {
      let [node, parent, key, bound] = pending.pop();
      const names = declared(node);
      if (names?.length) bound = new Set([...bound, ...names]);
      if (!node || typeof node !== 'object') continue;
      if (['ImportExpression','ImportDeclaration','WithStatement'].includes(node.type)) throw Error('Use local JavaScript without imports or with statements');
      const propertyName = node.type === 'MemberExpression' ? (node.computed ? node.property.value : node.property.name) : null;
      if (forbiddenProperties.has(propertyName)) throw Error('Forbidden browser capability: ' + propertyName);
      if (node.type === 'MemberExpression' && node.object.name === 'window' && !windowProperties.has(propertyName)) throw Error('Unsupported window capability: ' + (propertyName || 'dynamic property'));
      if (node.type === 'Identifier' && reserved.has(node.name) && !bound.has(node.name)) {
        const isKey = (parent?.type === 'MemberExpression' && key === 'property' && !parent.computed) || (parent?.type === 'Property' && key === 'key' && !parent.computed && !parent.shorthand);
        if (!isKey) throw Error('Reserved browser capability: ' + node.name + '; use another name for local variables');
      }
      if (node.type === 'WhileStatement' && node.test.type === 'Literal' && node.test.value) throw Error('Unbounded loops are forbidden');
      if (node.type === 'ForStatement' && !node.test) throw Error('Unbounded loops are forbidden');
      if (node.type === 'CallExpression' && ['setTimeout','setInterval'].includes(node.callee.name) && ['Literal','TemplateLiteral'].includes(node.arguments[0]?.type)) throw Error('Timers must take functions');
      for (const [name, value] of Object.entries(node)) {
        if (Array.isArray(value)) {
          for (const child of value) if (child?.type) pending.push([child, node, name, bound]);
        } else if (value?.type) pending.push([value, node, name, bound]);
      }
    }
  }
}

export const launchOptions = () => ({
  channel: process.env.SOCRAT_EXPLAINER_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined),
  // A container's default seccomp profile blocks the user namespaces Chromium's sandbox needs; the
  // checker container (no egress, non-root, no-new-privileges) sets SOCRAT_EXPLAINER_NO_SANDBOX=1.
  chromiumSandbox: process.platform !== 'win32' && process.env.SOCRAT_EXPLAINER_NO_SANDBOX !== '1',
  args: ['--site-per-process'],
});
export const contextOptions = { viewport: { width: 1000, height: 900 }, reducedMotion: 'reduce', serviceWorkers: 'block' };

async function main() {
  let raw = '';
  for await (const chunk of process.stdin) { raw += chunk; if (raw.length > 700_000) throw Error('Document too large'); }
  const input = JSON.parse(raw);
  const browser = await chromium.launch(launchOptions());
  try {
    return await run(await browser.newContext(contextOptions), input);
  } finally {
    // Closing can take several seconds (Edge on Windows: ~6 s) while the verdict is already known.
    // The caller waits for this process to exit under an 18 s budget, so a slow close used to fail
    // visuals that had passed. Give it a moment, then exit; Playwright kills the browser on exit.
    await Promise.race([browser.close().catch(() => undefined), new Promise(resolve => setTimeout(resolve, CLOSE_GRACE_MS))]);
  }
}

/** Check one visual in a fresh browser context. The caller owns (and closes) the context. */
export async function run(context, input) {
  inspectScripts(input.scripts);
  const page = await context.newPage();
  page.setDefaultTimeout(4000);
  page.setDefaultNavigationTimeout(10000);
  const errors = [], blocked = [];
  page.on('pageerror', error => errors.push(String(error.message).slice(0,180)));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text().slice(0,180)); });
  const host = 'http://host.socrat.invalid/', visual = 'http://visual.socrat.invalid/';
  await context.route('**/*', route => {
    const url = route.request().url();
    if (url === host) return route.fulfill({ contentType: 'text/html', body: `<html lang="en"><head><title>Visual check</title></head><body><main><iframe title="Visual explanation" sandbox="allow-scripts" src="${visual}" width="1000" height="900"></iframe></main></body></html>` });
    if (url === visual) return route.fulfill({ contentType: 'text/html', headers: { 'Content-Security-Policy': input.csp.replace(/frame-ancestors [^;]+/, 'frame-ancestors ' + host.slice(0,-1)), 'Origin-Agent-Cluster': '?1' }, body: input.html });
    blocked.push('external request'); return route.abort();
  });
  // Created before goto(), so it must not reject unhandled while goto is still running (a cold
  // browser start made it time out and crash the checker with no output).
  const frameReady = page.waitForEvent('framenavigated', { predicate: f => f.url() === visual, timeout: 12000 });
  frameReady.catch(() => undefined);
  await page.goto(host);
  const frame = await frameReady;
  if (!frame) throw Error('Visual did not load');
  try { await frame.waitForFunction(() => document.readyState === 'complete' && window.__explainer); }
  catch { throw Error(errors[0] || 'Initialize window.__explainer and a working initial visual immediately on load'); }
  // A script that threw while drawing is the real cause of any follow-on 'blank' or 'missing' finding.
  const initial = await frame.evaluate(() => {
    const api = window.__explainer, region = document.querySelector('#visual');
    if (!region || region.getBoundingClientRect().height < 120 || region.getBoundingClientRect().width < 100) throw Error('Visual canvas is blank or too small');
    if (typeof api.step !== 'function' || typeof api.reset !== 'function' || typeof api.describe !== 'function') throw Error('Missing step/reset/describe controls');
    const count = Number(api.stepCount), text = String(api.describe());
    if (!Number.isInteger(count) || count < 1 || count > 2000) throw Error('Initial stepCount must be from 1 to 2000; initialize a complete visual using your own example before exposing the interface');
    if (!Number.isInteger(api.currentStep) || api.currentStep < 0 || api.currentStep >= count) throw Error('Expose get currentStep() returning the actual selected zero-based step, including after input edits');
    if (!text.trim()) throw Error('describe() must explain the current initial state before any user interaction');
    // innerText keeps row and cell breaks (textContent runs table cells together into one word);
    // it skips closed <details>, so open them first.
    const section = document.querySelector('#transcript');
    section?.querySelectorAll('details').forEach(details => { details.open = true; });
    const transcript = section?.innerText.trim() || '';
    if (transcript.length < 100 || transcript.length > 30000) throw Error('Include a complete teaching explanation in section id=transcript');
    const controls = [...document.querySelectorAll('input,select,button')];
    if (!controls.length) throw Error('Include controls for learner input or experimentation');
    for (const control of controls) {
      const labelled = control.getAttribute('aria-label') || control.getAttribute('aria-labelledby') || control.labels?.length || (control.tagName === 'BUTTON' && control.textContent.trim());
      if (!labelled) throw Error('Label every control');
    }
    const drawn = region.querySelector('svg path,svg rect,svg circle,svg text,canvas') || region.children.length > 1;
    if (!drawn) throw Error('Include a real visual, not just explanatory text');
    return { count, current: api.currentStep, text, title: document.title, transcript };
  }).catch(error => { throw errors.length ? Error('Visual script error: ' + errors[0]) : error; });
  const snapshot = () => frame.evaluate(() => {
    const region=document.querySelector('#visual');
    return region.innerHTML+[...region.querySelectorAll('canvas')].map(c=>c.toDataURL()).join('');
  });
  const observe = () => frame.evaluate(() => ({ step:window.__explainer.currentStep, description:String(window.__explainer.describe()).slice(0,6000), visible_text:document.body.innerText.slice(0,4000) }));
  // The host's drawing kit audits the layout: overlapping or cut-off text in any observed state fails.
  const layout = async () => {
    const problems = await frame.evaluate(() => (typeof Sketch === 'undefined' ? [] : Sketch.audit()));
    if (problems.length) throw Error('Layout problem (shorten the text or use fewer items): ' + problems.slice(0, 3).join('; '));
  };
  const observations = [await observe()];
  await layout();
  if (initial.count > 1) {
    const firstVisual = await snapshot();
    for (const index of new Set([0,1,Math.floor(initial.count/2),initial.count-1])) {
      if (index === initial.current) continue;
      await frame.evaluate(i => window.__explainer.step(i), index);
      if (await frame.evaluate(() => window.__explainer.currentStep) !== index) throw Error('currentStep must report the index selected by step(index)');
      await page.waitForTimeout(80);
      const next = await frame.evaluate(() => String(window.__explainer.describe()));
      observations.push(await observe());
      await layout();
      if (!next.trim() || next === initial.text || await snapshot() === firstVisual) throw Error('Stepping must change both the visual and its state explanation');
    }
  } else {
    const fields = frame.locator('input:not([type=hidden]),textarea,select');
    const inputControl = (await fields.count() ? fields : frame.locator('button')).first();
    const before = await frame.evaluate(() => document.querySelector('#visual').innerHTML + window.__explainer.describe() + document.body.textContent);
    await inputControl.evaluate(element => {
      if (element.tagName === 'BUTTON') element.click();
      else {
        if (element.tagName === 'SELECT') element.value = element.options[(element.selectedIndex+1)%element.options.length].value;
        else if (['checkbox','radio'].includes(element.type)) element.checked = !element.checked;
        else if (['range','number'].includes(element.type)) { const step=Number(element.step)||1,next=Number(element.value)+step; element.value=String(element.max && next>Number(element.max) ? Number(element.value)-step : next); }
        else { const number=element.value.match(/-?\d+(?:\.\d+)?/); element.value=number ? element.value.replace(number[0],String(Number(number[0])+1)) : element.value+'a'; }
        element.dispatchEvent(new Event('input',{bubbles:true}));element.dispatchEvent(new Event('change',{bubbles:true}));
      }
    });
    const state = () => frame.evaluate(() => document.querySelector('#visual').innerHTML + window.__explainer.describe() + document.body.textContent);
    let after = await state();
    // Many apps apply an edited input with a button ("Search", "Run"); press the first one.
    if (before === after && await fields.count() && await frame.locator('button').count()) {
      await frame.locator('button').first().evaluate(button => button.click());
      after = await state();
    }
    observations.push(await observe());
    await layout();
    if (before === after) throw Error('Input controls must change the visual or its explanation');
  }
  await frame.evaluate(() => window.__explainer.reset());
  if (errors.length || blocked.length) throw Error(errors.length ? 'Visual script error: '+errors[0] : 'Visual attempted external access');
  const count = await frame.evaluate(() => Number(window.__explainer.stepCount));
  return { ok: true, step_count: count, title: initial.title, transcript: initial.transcript, observations, checks: ['script-syntax','capability-policy','sandbox-load','nonblank-canvas','labelled-controls','working-interaction','layout','reset'] };
}

const CLOSE_GRACE_MS = 500;

if (process.argv[1]?.endsWith('check-artifact.mjs')) {
  main()
    .catch(error => { const infrastructure = String(error.message).includes('browserType.launch'); return { ok: false, infrastructure, reason: infrastructure ? 'Browser checker unavailable' : String(error.message).slice(0,300), ...(infrastructure ? { detail: String(error.message).slice(0,600) } : {}) }; })
    .then(result => process.stdout.write(JSON.stringify(result), () => process.exit(result.ok ? 0 : 1)));
}
