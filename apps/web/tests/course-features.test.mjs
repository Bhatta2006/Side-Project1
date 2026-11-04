// Run: npm run test:web-unit
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { featuresFor, practiceHref } from '../src/lib/course-features.ts';
import { navItems } from '../src/lib/routes.ts';

const reading = { studio: 'reading', loop: 'read-reflect', evidence: ['quiz'], tools: [], name: 'Notebook' };
const code = { studio: 'code', loop: 'solve', evidence: ['tests'], tools: ['editor'], name: 'Practice' };

test('company questions belong to DSA alone', () => {
  assert.equal(featuresFor('dsa', code).companies, true);
  assert.equal(featuresFor('cp', code).companies, false);
  assert.equal(featuresFor('zero', code).companies, false);
  assert.equal(featuresFor('kids-math', reading).companies, false);
});

test('a non-code course has no editor, library or Codeforces, and practises with its own sets', () => {
  const math = featuresFor('kids-math', reading);
  assert.deepEqual(math, { code: false, library: false, companies: false, codeforces: false, drills: true });
  assert.equal(practiceHref(math), '/studio');
  const practice = navItems(reading, math).find(item => item.key === 'practice');
  assert.equal(practice.href, '/studio');
  assert.equal(practice.label, 'Notebook');
});

test('the programming courses keep the problem library', () => {
  const dsa = featuresFor('dsa', code);
  assert.equal(practiceHref(dsa), '/library');
  assert.equal(navItems(code, dsa).find(item => item.key === 'practice').href, '/library');
  // A generated code course has no library: it practises with its own sets under the usual name.
  const rust = featuresFor('rust-web', code);
  assert.equal(rust.library, false);
  assert.deepEqual(navItems(code, rust).find(item => item.key === 'practice'), { ...navItems(code, dsa).find(i => i.key === 'practice'), href: '/studio' });
});

test('the API answer wins when it is sent', () => {
  const sent = { code: false, library: false, companies: false, codeforces: false, drills: true };
  assert.equal(featuresFor('dsa', code, sent), sent);
});
