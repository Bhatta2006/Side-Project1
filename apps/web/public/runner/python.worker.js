// Runs Python solutions with Pyodide. One interpreter per worker; every test gets a fresh
// __main__ namespace and its own stdin. The page terminates the worker on a timeout.
import { report } from './common.js';

let runner = null;

const PRELUDE = `
import sys, io, traceback
# Solutions run on the learner's own machine; keep them away from the browser APIs.
for _name in ("js", "pyodide", "pyodide_js", "pyodide.ffi", "pyodide.http"):
    sys.modules[_name] = None

def __socrat_run(src, data):
    out, err = io.StringIO(), io.StringIO()
    saved = sys.stdin, sys.stdout, sys.stderr
    sys.stdin = io.TextIOWrapper(io.BytesIO(data.encode()), encoding="utf-8")
    sys.stdout, sys.stderr = out, err
    status = "executed"
    try:
        code = compile(src, "solution.py", "exec")
    except SyntaxError as e:
        # A typo is not a crash: report it as a syntax error with only the learner's line.
        sys.stdin, sys.stdout, sys.stderr = saved
        return "compile_error", "", "".join(traceback.format_exception_only(type(e), e))
    try:
        exec(code, {"__name__": "__main__"})
    except SystemExit as e:
        if e.code not in (None, 0):
            status = "runtime_error"
    except BaseException as e:
        # Skip this harness frame so the traceback starts in solution.py.
        traceback.print_exception(type(e), e, e.__traceback__.tb_next)
        status = "runtime_error"
    finally:
        sys.stdin, sys.stdout, sys.stderr = saved
        sys.setrecursionlimit(1000)
    return status, out.getvalue(), err.getvalue()
`;

async function load(base) {
  if (runner) return runner;
  const { loadPyodide } = await import(`${base}/pyodide.mjs`);
  const py = await loadPyodide({ indexURL: `${base}/`, stdout: () => {}, stderr: () => {} });
  py.runPython(PRELUDE);
  runner = { py, run: py.globals.get('__socrat_run') };
  return runner;
}

self.onmessage = async ({ data }) => {
  try {
    const { run } = await load(data.base);
    if (data.type === 'warm') return void self.postMessage({ type: 'ready' });
    self.postMessage({ type: 'ready' });
    for (const test of data.tests) {
      self.postMessage({ type: 'start', index: test.index });
      const started = performance.now();
      const result = run(data.source, test.input);
      const [status, stdout, stderr] = result.toJs();
      result.destroy();
      self.postMessage(await report(test.index, status, stdout, stderr, started));
    }
    self.postMessage({ type: 'done' });
  } catch (error) {
    self.postMessage({ type: 'failed', message: String(error?.message || error) });
  }
};
