// Run: node --experimental-strip-types --test apps/web/tests/pages.test.mjs
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { isCheckPage, minutes, splitPages, words } from '../src/lib/pages.ts';

const LESSON = [
  'A short opening line.',
  '',
  '## What a fraction is',
  'The bottom number counts equal parts.',
  '',
  '### Worked example',
  'Cut a pizza into 8.',
  '',
  '## Comparing',
  '```python',
  '## not a heading inside code',
  'print(1)',
  '```',
  'Same bottom: compare the tops.',
  '',
  '## Check yourself',
  '1. Which is bigger?',
  '<details>1/3</details>',
].join('\n');

test('each ## section is a page and the opening joins the first', () => {
  const pages = splitPages(LESSON);
  assert.deepEqual(pages.map(p => p.title), ['What a fraction is', 'Comparing', 'Check yourself']);
  assert.match(pages[0].body, /^A short opening line\./);
  assert.match(pages[0].body, /### Worked example/); // callouts stay on their page
  assert.match(pages[1].body, /## not a heading inside code/);
});

test('the closing questions are a check page', () => {
  const pages = splitPages(LESSON);
  assert.equal(isCheckPage(pages[2]), true);
  assert.equal(isCheckPage(pages[0]), false);
});

test('a lesson without sections is one page', () => {
  assert.deepEqual(splitPages('Just text.'), [{ title: '', body: 'Just text.' }]);
});

test('reading time counts teaching words only', () => {
  const [, comparing, check] = splitPages(LESSON);
  assert.equal(words(comparing), 5);
  assert.equal(words(check), 4);
  assert.equal(minutes(splitPages(LESSON)), 1);
});
