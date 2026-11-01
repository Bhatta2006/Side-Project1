// Proves the answer checker works inside real Pyodide with the vendored SymPy wheel: the same
// steps as public/runner/check.worker.js, run in Node. Needs `npm run runtimes` first.
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const web = join(dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(readFileSync(join(web, 'public', 'runtimes', 'manifest.json'), 'utf8'));
const base = join(web, 'public', manifest.pyodide.replace(/^\//, ''));
const started = performance.now();

const { loadPyodide } = await import(pathToFileURL(join(base, 'pyodide.mjs')).href);
const py = await loadPyodide({ indexURL: base + '/' });
await py.loadPackage('sympy');
py.FS.mkdirTree('/home/pyodide');
py.FS.writeFile('/home/pyodide/socrat_checks.py', readFileSync(join(web, 'public', 'runtimes', 'checks', 'engine.py'), 'utf8'));
py.runPython('import sys; sys.path.insert(0, "/home/pyodide")');
const run = py.pyimport('socrat_checks').run;
const ready = Math.round(performance.now() - started);

const cases = [
  [{ op: 'equivalent', expected: '(x+1)^2', given: 'x^2+2x+1' }, 'correct'],
  [{ op: 'equivalent', expected: 'x^2', given: '-x^2' }, 'incorrect', 'sign'],
  [{ op: 'equivalent', expected: 'x', given: "__import__('os')" }, 'unreadable'],
  [{ op: 'equivalent', expected: 'x', given: '9^9^9^9' }, 'unreadable'],
  [{ op: 'equation', expected: 'x=3', given: '2x+1=7' }, 'correct'],
  [{ op: 'steps', lines: ['2x+3=7', '2x=10', 'x=5'] }, 'incorrect'],
  [{ op: 'numeric', expected: 1, given: '3.6 km/h', unit: 'm/s' }, 'correct'],
  [{ op: 'numeric', expected: 9.8, given: '9.8', unit: 'm/s^2' }, 'incorrect', 'missing_units'],
];
let failed = 0;
for (const [request, verdict, hint = ''] of cases) {
  const result = JSON.parse(run(JSON.stringify(request)));
  const ok = result.verdict === verdict && result.hint === hint;
  if (!ok) failed += 1;
  console.log(ok ? 'ok  ' : 'FAIL', request.op, JSON.stringify(request).slice(0, 70), '->', result.verdict, result.hint);
}
console.log(`pyodide + sympy ready in ${ready} ms; ${cases.length - failed}/${cases.length} checks as expected`);
process.exit(failed ? 1 : 0);
