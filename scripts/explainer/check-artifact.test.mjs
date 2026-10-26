import test from 'node:test';
import assert from 'node:assert/strict';
import { inspectScripts } from './check-artifact.mjs';

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

test('allows locally declared names that shadow reserved globals, never free references', () => {
  for (const script of [
    'function merge(parent){return parent.left}', 'const parent=[0];parent[0]=1;',
    'for(let i=0,top=3;i<top;i++){}', 'const {parent,top}=node;use(parent,top)',
    'tree.forEach(([parent,...rest])=>draw(parent,rest))', 'try{}catch(self){self.message}',
    'function heap(){let parent=0;return ()=>parent+1}',
  ]) inspectScripts([script]);
  for (const script of [
    'function f(parent){} parent.postMessage(1,"*")', '{let parent=1} top.document',
    'function f(){const x=1} self.alert(1)', 'const o={parent}',
  ]) assert.throws(() => inspectScripts([script]), undefined, script);
});
