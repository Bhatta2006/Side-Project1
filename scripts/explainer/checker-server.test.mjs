import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn, execFileSync } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';

const python = path.resolve('.venv', process.platform==='win32' ? 'Scripts/python.exe' : 'bin/python');
const fixture = readFileSync('services/api/tests/fixtures/visual.html', 'utf8');
const payload = html => execFileSync(python, ['-c', "import sys,json;from socrat.explainer.artifact import validate,compile_document;d=validate(sys.stdin.read());h,c=compile_document(d.html,'qa','http://host.socrat.invalid');print(json.dumps(dict(html=h,csp=c,scripts=d.scripts)))"], { input:html,env:{...process.env,PYTHONPATH:path.resolve('services/api/src')},encoding:'utf8' });

test('isolated checker authenticates and validates visuals on one warm browser', { timeout: 90000 }, async () => {
  const secret = randomBytes(32).toString('hex');
  const server = spawn(process.execPath, ['scripts/explainer/checker-server.mjs'], { env: { ...process.env, PORT: '0', SOCRAT_EXPLAINER_CHECKER_SECRET: secret }, stdio: ['ignore','pipe','pipe'] });
  try {
    const port = await new Promise((resolve,reject) => {
      const timer = setTimeout(() => reject(Error('Checker startup timed out')), 5000);
      server.stdout.once('data', chunk => { clearTimeout(timer);resolve(JSON.parse(chunk).port); });
      server.once('error', reject);
    });
    const origin = `http://127.0.0.1:${port}`;
    assert.equal((await fetch(origin+'/health')).status, 200); // waits for the browser launch
    assert.equal((await fetch(origin+'/check',{method:'POST',body:'{}'})).status, 403);
    const check = async html => {
      const response = await fetch(origin+'/check',{method:'POST',headers:{Authorization:'Bearer '+secret,'Content-Type':'application/json'},body:payload(html),signal:AbortSignal.timeout(30000)});
      assert.equal(response.status,200);
      return response.json();
    };
    const first = await check(fixture);
    assert.equal(first.ok,true,first.reason);
    assert.equal(first.step_count,4);
    // A visual that never yields is the visual's fault, not the checker's, and the browser recovers.
    const runaway = await check(fixture.replace('let index=0;', 'let index=0;let spin=1;while(spin>0){spin++}'));
    assert.equal(runaway.ok,false);
    assert.ok(!runaway.infrastructure, runaway.reason);
    const started = Date.now();
    const again = await check(fixture);
    assert.equal(again.ok,true,again.reason);
    assert.ok(Date.now()-started < 8000, 'a warm check does not pay for a browser launch');
  } finally { server.kill(); }
});
