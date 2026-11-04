// Run: npm run test:web-unit
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { featuresFor, practiceHref } from '../src/lib/course-features.ts';
import { PRACTICE_SEGMENTS, navItems } from '../src/lib/routes.ts';

const reading = { studio: 'reading', loop: 'read-reflect', evidence: ['quiz'], tools: [], name: 'Math Quest' };
const code = { studio: 'code', loop: 'solve', evidence: ['tests'], tools: ['editor'], name: 'Practice' };
const tabs = features => PRACTICE_SEGMENTS.filter(s => features[s.needs]).map(s => s.label);

test('every course practises on the same page, with questions written for it', () => {
  for (const [course, shape] of [['kids-math', reading], ['dsa', code], ['zero', code], ['rust-web', code]]) {
    const features = featuresFor(course, shape);
    assert.equal(features.drills, true, course);
    assert.equal(practiceHref(features), '/studio');
    assert.equal(navItems(shape, features).find(item => item.key === 'practice').href, '/studio');
  }
  assert.equal(navItems(reading).find(item => item.key === 'practice').label, 'Math Quest');
});

test('only the extras a course has: company questions in DSA alone', () => {
  assert.deepEqual(tabs(featuresFor('kids-math', reading)), ['Practice sets']);
  assert.deepEqual(tabs(featuresFor('zero', code)), ['Practice sets', 'Problems', 'Focus sprint']);
  assert.deepEqual(tabs(featuresFor('cp', code)), ['Practice sets', 'Problems', 'Focus sprint']);
  assert.deepEqual(tabs(featuresFor('dsa', code)), ['Practice sets', 'Problems', 'Company questions', 'Company sprint', 'Focus sprint']);
  const math = featuresFor('kids-math', reading);
  assert.equal(math.code || math.library || math.companies || math.codeforces, false);
});

test('the API answer wins when it is sent', () => {
  const sent = { code: false, library: false, companies: false, codeforces: false, drills: true };
  assert.equal(featuresFor('dsa', code, sent), sent);
});
