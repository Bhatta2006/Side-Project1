/**
 * Answer checker for math and physics: symbolic equivalence, equations, derivation steps and
 * numbers with units. SymPy runs in Pyodide in a Web Worker, so answers never leave the learner's
 * machine. The page ends a check that runs too long by terminating the worker.
 */

export type CheckRequest =
  | { op: 'equivalent'; expected: string; given: string }
  | { op: 'equation'; expected: string; given: string }
  | { op: 'steps'; lines: string[]; expected?: string }
  | { op: 'numeric'; expected: number; given: string; unit?: string; rel_tol?: number; abs_tol?: number };

export interface CheckResult {
  verdict: 'correct' | 'incorrect' | 'unreadable';
  reason: string;
  /** Names a common slip: sign, constant, missing_units, wrong_units, power_of_ten. */
  hint: string;
  hint_text?: string;
  /** 1-based line of the first step that does not follow (steps checks). */
  step?: number;
  final?: boolean | null;
}

type Paths = { pyodide: string; checks: string };

const TIMEOUT_MS = 20_000;

let paths: Promise<Paths> | null = null;
function runtimes(): Promise<Paths> {
  paths ??= fetch('/runtimes/manifest.json').then(r => {
    if (!r.ok) throw new Error('The answer checker is not installed on this server.');
    return r.json() as Promise<Paths>;
  });
  paths.catch(() => { paths = null; });
  return paths;
}

let worker: Worker | null = null;
let counter = 0;

function spawn() {
  worker = new Worker('/runner/check.worker.js', { type: 'module', name: 'socrat-check' });
  return worker;
}

/** Start loading the checker in the background (SymPy is a few MB, cached after the first time). */
export async function warmChecker() {
  if (worker) return;
  try {
    const { pyodide, checks } = await runtimes();
    spawn().postMessage({ type: 'warm', base: pyodide, checks });
  } catch {
    /* warm-up is best effort */
  }
}

export async function check(request: CheckRequest, timeoutMs = TIMEOUT_MS): Promise<CheckResult> {
  const { pyodide, checks } = await runtimes();
  const active = worker ?? spawn();
  const id = ++counter;
  return new Promise<CheckResult>((resolve, reject) => {
    const stop = (error: Error) => {
      active.terminate();
      if (worker === active) worker = null;
      reject(error);
    };
    const timer = setTimeout(() => stop(new Error('Checking took too long. Try a simpler answer.')), timeoutMs);
    const onMessage = ({ data }: MessageEvent) => {
      if (data.id !== id) return;
      clearTimeout(timer);
      active.removeEventListener('message', onMessage);
      if (data.type === 'result') resolve(data.result as CheckResult);
      else reject(new Error(String(data.message)));
    };
    active.addEventListener('message', onMessage);
    active.onerror = event => { clearTimeout(timer); stop(new Error(event.message || 'The answer checker crashed.')); };
    active.postMessage({ type: 'check', id, base: pyodide, checks, request });
  });
}
