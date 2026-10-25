import { expect, test, type Page } from '@playwright/test';

/**
 * Run and Submit execute in the learner's browser: Python in Pyodide, C++ in Clang compiled to
 * WebAssembly. The server receives output digests only and judges them.
 */
test.describe.configure({ mode: 'serial' });
test.setTimeout(240_000);
const ORIGIN = 'http://localhost:3000';

const GREETING_PY = 'name = input().strip()\nprint(f"Hello, {name}! Welcome to Socrat.")\n';
const GREETING_CPP = `#include <bits/stdc++.h>
using namespace std;
int main() {
  string name; getline(cin, name);
  while (!name.empty() && isspace((unsigned char)name.back())) name.pop_back();
  cout << "Hello, " << name << "! Welcome to Socrat." << endl;
}
`;

async function signUp(page: Page) {
  const subject = `runner-${Date.now()}-${Math.random().toString(16).slice(2, 6)}`;
  await page.goto('/login');
  const login = await page.request.post('/api/v1/auth/dev-login', { data: { subject, display_name: 'Runner' }, headers: { Origin: ORIGIN } });
  expect(login.ok()).toBeTruthy();
  const me = await (await page.request.get('/api/v1/me')).json();
  const headers = { Origin: ORIGIN, 'X-CSRF-Token': me.csrf_token };
  await page.request.patch('/api/v1/me', { data: { birth_year: 2001, timezone: 'Asia/Kolkata' }, headers });
  const enrolled = await page.request.post('/api/v1/enrollments', {
    data: { course: 'zero', language: 'python', level: 'brand-new', minutes_per_day: 45, weekdays: [0, 1, 2, 3, 4, 5, 6] },
    headers,
  });
  expect(enrolled.ok()).toBeTruthy();
  return headers;
}

async function runWith(page: Page, headers: Record<string, string>, language: 'python' | 'cpp', source: string, button: 'Run tests' | 'Submit solution') {
  const saved = await page.request.put('/api/v1/problems/greeting/draft', { data: { source, language }, headers });
  expect(saved.ok()).toBeTruthy();
  await page.evaluate(() => localStorage.clear());
  await page.goto('/problems/greeting');
  const select = page.getByRole('combobox').filter({ hasText: /Python|C\+\+/ }).first();
  await select.selectOption(language);
  await expect(page.locator('.cm-content')).toContainText(source.split('\n')[0].slice(0, 20));
  await page.getByRole('button', { name: button }).last().click();
  const results = page.getByRole('region', { name: 'Results' });
  await expect(results).toBeVisible({ timeout: 200_000 });
  return results;
}

test('Python: submit is judged from the browser run, failures show their reason', async ({ page }, info) => {
  test.skip(info.project.name !== 'desktop', 'one browser is enough for the runtime check');
  const headers = await signUp(page);

  let results = await runWith(page, headers, 'python', GREETING_PY, 'Submit solution');
  await expect(results).toContainText('Submission: Accepted');

  results = await runWith(page, headers, 'python', 'print("wrong")\n', 'Run tests');
  await expect(results).toContainText('Wrong answer');

  results = await runWith(page, headers, 'python', 'name = input()\nprint(1 // 0)\n', 'Run tests');
  await expect(results).toContainText('Runtime error');
  await expect(results).toContainText('ZeroDivisionError');
  await expect(results).not.toContainText('__socrat_run');

  results = await runWith(page, headers, 'python', 'print("hi"\n', 'Run tests');
  await expect(results).toContainText('Syntax error');
  await expect(results).toContainText('SyntaxError');

  results = await runWith(page, headers, 'python', 'while True:\n    pass\n', 'Run tests');
  await expect(results).toContainText('Time limit exceeded');
});

test('C++: compiles in the browser, with bits/stdc++.h, errors and time limits', async ({ page }, info) => {
  test.skip(info.project.name !== 'desktop', 'one browser is enough for the runtime check');
  const headers = await signUp(page);

  let results = await runWith(page, headers, 'cpp', GREETING_CPP, 'Submit solution');
  await expect(results).toContainText('Submission: Accepted');

  results = await runWith(page, headers, 'cpp', '#include <bits/stdc++.h>\nint main() { int x = ; }\n', 'Run tests');
  await expect(results).toContainText('Compilation error');
  await expect(results).toContainText('expected expression');

  results = await runWith(page, headers, 'cpp', '#include <cstdio>\nint depth(int n) { return n ? 1 + depth(n - 1) : 0; }\nint main() { std::printf("%d\\n", depth(1000000)); return 3; }\n', 'Run tests');
  await expect(results).toContainText('Runtime error');
  await expect(results).toContainText('exited with code 3');

  results = await runWith(page, headers, 'cpp', 'int main() { volatile long x = 0; while (true) x++; }\n', 'Run tests');
  await expect(results).toContainText('Time limit exceeded');
});

test('drafts typed in the editor survive a reload before they reach the server', async ({ page }, info) => {
  test.skip(info.project.name !== 'desktop', 'storage behaviour is the same on phones');
  await signUp(page);
  await page.goto('/problems/greeting');
  const content = page.locator('.cm-content');
  await expect(content).toBeVisible();
  // Block the autosave, type, and reload: the local copy comes back and is saved.
  await page.route('**/api/v1/problems/greeting/draft', route => route.abort());
  await content.click();
  await page.keyboard.press('Control+End');
  await page.keyboard.type('\n# kept offline');
  await page.waitForTimeout(2000);
  await page.unroute('**/api/v1/problems/greeting/draft');
  await page.reload();
  await expect(content).toContainText('# kept offline');
  await expect.poll(async () => (await (await page.request.get('/api/v1/problems/greeting')).json()).draft ?? '').toContain('# kept offline');
});
