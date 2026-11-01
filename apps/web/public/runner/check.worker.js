// Checks learners' math and physics answers with SymPy in Pyodide. One interpreter per worker,
// loaded on the first request. The checker (engine.py) is plain Python shared with the API tests;
// it only reads text, and the page terminates this worker if a check runs too long.
let checker = null;

async function load(base, checks) {
  if (checker) return checker;
  const { loadPyodide } = await import(`${base}/pyodide.mjs`);
  const py = await loadPyodide({ indexURL: `${base}/`, stdout: () => {}, stderr: () => {} });
  await py.loadPackage('sympy'); // brings mpmath; both are served from our own origin
  const source = await (await fetch(`${checks}/engine.py`)).text();
  py.FS.writeFile('/home/pyodide/socrat_checks.py', source);
  py.runPython('import sys; sys.path.insert(0, "/home/pyodide")');
  checker = py.pyimport('socrat_checks').run;
  return checker;
}

self.onmessage = async ({ data }) => {
  try {
    const run = await load(data.base, data.checks);
    if (data.type === 'warm') return self.postMessage({ type: 'ready' });
    const result = JSON.parse(run(JSON.stringify(data.request)));
    self.postMessage({ type: 'result', id: data.id, result });
  } catch (error) {
    self.postMessage({ type: 'failed', id: data.id, message: String(error?.message || error) });
  }
};
