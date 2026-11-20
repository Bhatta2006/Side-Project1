// Run: npm run test:web-unit
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { featuresFor, practiceHref } from '../src/lib/course-features.ts';
import { navItems } from '../src/lib/routes.ts';

const reading = { studio: 'reading', loop: 'read-reflect', evidence: ['quiz'], tools: [], name: 'Math Quest' };
const code = { studio: 'code', loop: 'solve', evidence: ['tests'], tools: ['editor'], name: 'Practice' };

test('every course practises on the same page, with questions written for it', () => {
  for (const [course, shape] of [['kids-math', reading], ['rust-web', code]]) {
    const features = featuresFor(course, shape);
    assert.equal(features.drills, true, course);
    assert.equal(practiceHref(features), '/studio');
    assert.equal(navItems(shape, features).find(item => item.key === 'practice').href, '/studio');
  }
  assert.equal(navItems(reading).find(item => item.key === 'practice').label, 'Math Quest');
});

test('a code editor follows the course shape, never the course id', () => {
  assert.equal(featuresFor('kids-math', reading).code, false);
  assert.equal(featuresFor('rust-web', code).code, true);
  // The same id with a different shape answers differently: nothing is keyed on a course name.
  assert.equal(featuresFor('rust-web', reading).code, false);
  assert.equal(featuresFor('kids-math', code).code, true);
});

test('the API answer wins when it is sent', () => {
  const sent = { code: false, drills: true };
  assert.equal(featuresFor('rust-web', code, sent), sent);
});
