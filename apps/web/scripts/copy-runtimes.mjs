// Copies the in-browser code runtimes (Pyodide, YoWASP Clang, the WASI shim) from
// node_modules into public/runtimes/<name>-<version>/ so they are served from our own origin,
// cached as immutable files, and work under the strict CSP. Run before `next dev` and
// `next build`; the copies are not committed (see .gitignore).
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const web = join(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(join(web, 'package.json'));
const out = join(web, 'public', 'runtimes');

// Some packages do not export package.json, so look the directory up the resolution paths.
function packageDir(name) {
  for (const base of require.resolve.paths(name) ?? []) {
    if (existsSync(join(base, name, 'package.json'))) return join(base, name);
  }
  throw new Error(`${name} is not installed; run npm ci`);
}

const runtimes = {
  pyodide: { pkg: 'pyodide', dir: '', files: ['pyodide.mjs', 'pyodide.asm.mjs', 'pyodide.asm.wasm', 'python_stdlib.zip', 'pyodide-lock.json'] },
  clang: { pkg: '@yowasp/clang', dir: 'gen', files: null },
  wasi: { pkg: '@bjorn3/browser_wasi_shim', dir: 'dist', files: null },
};

const manifest = {};
for (const [key, { pkg, dir, files }] of Object.entries(runtimes)) {
  const root = packageDir(pkg);
  const { version } = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'));
  const name = `${key}-${version}`;
  const from = join(root, dir);
  const to = join(out, name);
  mkdirSync(to, { recursive: true });
  for (const file of files ?? readdirSync(from).filter(f => /\.(js|mjs|wasm|tar)$/.test(f))) {
    const source = join(from, file);
    const target = join(to, file);
    if (existsSync(target) && statSync(target).size === statSync(source).size) continue;
    copyFileSync(source, target);
  }
  manifest[key] = `/runtimes/${name}`;
}
// The answer checker: SymPy (and mpmath) built by Pyodide, kept in vendor/ because they are not
// in the npm package. Each wheel must match the hash in Pyodide's own lock file.
const pyodideDir = join(out, manifest.pyodide.split('/').pop());
const lock = JSON.parse(readFileSync(join(pyodideDir, 'pyodide-lock.json'), 'utf8')).packages;
for (const name of ['sympy', 'mpmath']) {
  const { file_name: file, sha256 } = lock[name];
  const bytes = readFileSync(join(web, 'vendor', 'pyodide-wheels', file));
  if (createHash('sha256').update(bytes).digest('hex') !== sha256) {
    throw new Error(`vendor/pyodide-wheels/${file} does not match pyodide-lock.json; re-download it from the Pyodide CDN`);
  }
  writeFileSync(join(pyodideDir, file), bytes);
}
// The checker itself is plain Python shared with the API tests, so one file serves both.
const checks = join(out, 'checks');
mkdirSync(checks, { recursive: true });
copyFileSync(join(web, '..', '..', 'services', 'api', 'src', 'socrat', 'checks', 'engine.py'), join(checks, 'engine.py'));
manifest.checks = '/runtimes/checks';
writeFileSync(join(out, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
console.log('runtimes ready:', Object.values(manifest).join(', '));
