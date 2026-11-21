// Run: node --experimental-strip-types --test apps/web/tests/math.test.mjs
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { displayMath, pieces } from '../src/lib/math.ts';

const maths = text => pieces(text).filter(p => p.kind === 'math').map(p => p.tex);

test('subscripts inside maths are kept whole, not read as emphasis', () => {
  const tex = String.raw`\sigma_{\text{origin} = \text{'JFK'} \land \text{available\_seats} > 0}(\text{Flights})`;
  assert.deepEqual(maths(`For example $$${tex}$$ here`), [tex]);
  assert.deepEqual(maths(String.raw`where $\text{condition}$ is true and $k$ columns`), [String.raw`\text{condition}`, 'k']);
});

test('prices are text, not maths', () => {
  assert.deepEqual(maths('It costs $5 and $10, or $5-$10.'), []);
  assert.deepEqual(maths(String.raw`Escaped \$x\$ stays text.`), []);
});

test('code spans win over maths', () => {
  const parts = pieces('Run `echo $HOME$` then $x^2$.');
  assert.deepEqual(parts.map(p => p.kind), ['text', 'code', 'text', 'math', 'text']);
});

test('\( \) and \[ \] delimiters', () => {
  const parts = pieces(String.raw`inline \(a+b\) and display \[c^2\]`).filter(p => p.kind === 'math');
  assert.deepEqual(parts.map(p => [p.tex, p.display]), [['a+b', false], ['c^2', true]]);
});

test('a display formula standing alone, on one line or several', () => {
  assert.equal(displayMath(String.raw`$$\pi_{A1, A2}(R)$$`), String.raw`\pi_{A1, A2}(R)`);
  assert.equal(displayMath('$$\na = b\n$$.'), 'a = b');
  assert.equal(displayMath('$$a$$ and more text'), null);
});
