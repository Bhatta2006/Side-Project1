import test from 'node:test';
import assert from 'node:assert/strict';
import { closeWithin, inspectScripts } from './check-artifact.mjs';

test('allows ordinary visual computations and rejects nested browser capabilities', () => {
  inspectScripts(['const nums=[1,2];function draw(i){return nums[i]*2} window.__explainer={step:draw};']);
  inspectScripts(['const color=window.getComputedStyle(document.documentElement).getPropertyValue("--primary");']);
  inspectScripts(['class Scene { constructor(){this.index=0} step(i){this.index=i} }']);
  for (const script of [
    'function f(){fetch("/secret")}', 'const f=()=>new Function("return 1")',
    'window.parent.document', 'document.cookie', 'const x=({}).constructor',
    'import("https://example.com")', 'const x=localStorage.getItem("key")',
    'while(true){}', 'while(1){}', 'for(;;){}', 'setTimeout("alert(1)",10)',
    'document.defaultView', 'const f=()=>new Worker("x")',
    'class Scene { step(){return this.constructor} }',
  ]) assert.throws(() => inspectScripts([script]), undefined, script);
});

test('exits once the verdict is known instead of waiting for a slow browser close', { timeout: 5000 }, async () => {
  let closed = false;
  await closeWithin({ close: () => new Promise(() => {}) }, 50);
  await closeWithin({ close: async () => { closed = true; } }, 1000);
  assert.ok(closed);
  await closeWithin({ close: async () => { throw Error('already gone'); } }, 1000);
});
