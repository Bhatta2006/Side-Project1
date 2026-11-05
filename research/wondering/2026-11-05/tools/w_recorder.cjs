// Records Wondering's backend traffic: timing, path, status and value-free shapes.
// Never records headers (so no tokens). Full bodies only for generation/content reads, to scratch.
const { chromium } = require('playwright');
const fs = require('fs');
const dir = process.argv[2];
const log = fs.createWriteStream(dir + '/net.jsonl', { flags: 'a' });
const FULL = /functions\/v1\/(generate|course-creation-chat|check-understanding|lesson-progress|trigger|learning-sources|search-learning)|rest\/v1\/(lesson_sessions|practices|course_nodes|lesson_plans|lesson_practice_generations|projects)/;
const SKIP = /auth\/v1|token|posthog|sentry/i;
function shape(v, d = 0) {
  if (d > 6) return '…';
  if (Array.isArray(v)) return v.length ? [`len=${v.length}`, shape(v[0], d + 1)] : [];
  if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).slice(0, 40).map(([k, x]) => [k, shape(x, d + 1)]));
  if (typeof v === 'string') return `str(${v.length})`;
  return typeof v;
}
let n = 0;
(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
  const ctx = browser.contexts()[0];
  const watch = page => {
    const started = new Map();
    page.on('request', r => started.set(r, Date.now()));
    page.on('requestfinished', async r => {
      const url = r.url();
      if (!/supabase\.co|wondering\.app\/api/.test(url) || SKIP.test(url)) return;
      const t0 = started.get(r) || Date.now();
      const res = await r.response().catch(() => null);
      const u = new URL(url);
      const entry = { t: new Date(t0).toISOString(), ms: Date.now() - t0, method: r.method(), path: u.pathname, query: u.search.slice(0, 300), status: res ? res.status() : null };
      try { const b = r.postData(); if (b) { try { entry.req = shape(JSON.parse(b)); } catch { entry.req = `text(${b.length})`; } } } catch {}
      if (res) {
        const ct = res.headers()['content-type'] || '';
        entry.ct = ct.split(';')[0];
        try {
          const body = await res.text();
          entry.bytes = body.length;
          if (ct.includes('json')) { try { entry.res = shape(JSON.parse(body)); } catch {} }
          else if (ct.includes('event-stream')) {
            entry.events = [...new Set((body.match(/"type"\s*:\s*"([a-z_]+)"/g) || []).map(s => s.split('"')[3]))];
          }
          if (FULL.test(url)) { const f = `${dir}/raw/${String(++n).padStart(3, '0')}-${u.pathname.split('/').pop()}.${ct.includes('json') ? 'json' : 'txt'}`; fs.writeFileSync(f, body); entry.raw = f.split('/').pop(); }
        } catch {}
      }
      log.write(JSON.stringify(entry) + '\n');
    });
  };
  ctx.pages().forEach(watch);
  ctx.on('page', watch);
  console.log('recording');
  setInterval(() => {}, 1 << 30);
})().catch(e => { console.error(e.message); process.exit(1); });
