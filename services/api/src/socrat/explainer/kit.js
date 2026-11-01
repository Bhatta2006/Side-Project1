/* Sketch: the host's layout kit for generated visuals. The model describes a scene as data (rows,
   links, pointers, focus); every coordinate is computed here, so nothing overlaps or lands in the
   wrong place. Trusted host code: injected before the generated scripts by compile_document. */
const Sketch = (() => {
  const NS = 'http://www.w3.org/2000/svg', W = 600, PAD = 20, GAP = 14, ROW_GAP = 78, HILITE_TEXT = '#15161E', chipSize = 16;
    const INK = 'var(--ink)', PEN = 'var(--pen)', MUTED = 'var(--muted-foreground)', CARD = 'var(--card)';

  function el(parent, tag, attrs, text) {
    const node = document.createElementNS(NS, tag);
    for (const key in attrs) node.setAttribute(key, String(attrs[key]));
    if (text !== undefined) node.textContent = String(text);
    parent.appendChild(node);
    return node;
  }
  const chipOf = c => (typeof c === 'object' ? c : { text: c });
  const stroke = (color, width) => `fill:none;stroke:${color};stroke-width:${width || 2.4};stroke-linecap:round;stroke-linejoin:round`;
  const fail = message => { throw new Error('Sketch: ' + message); };
  const toneColor = tone => (tone === 'pen' ? PEN : tone === 'primary' ? 'var(--primary)' : tone === 'muted' ? MUTED : INK);

  function mount(host, options = {}) {
    host = typeof host === 'string' ? document.querySelector(host) : host;
    if (!host) fail('mount() needs an element or selector');
    host.replaceChildren();
    const svg = el(host, 'svg', { viewBox: `0 0 ${W} 200`, role: 'img', 'aria-labelledby': 'sketch-desc' });
    svg.setAttribute('style', 'width:100%;height:auto;display:block');
    el(svg, 'desc', { id: 'sketch-desc' }, options.desc || 'A hand-drawn diagram; the note above it says what it shows.');
    const defs = el(svg, 'defs', {});
    const rough = el(defs, 'filter', { id: 'sketch-rough' });
    el(rough, 'feTurbulence', { type: 'fractalNoise', baseFrequency: '0.03', numOctaves: '2', seed: '3' });
    el(rough, 'feDisplacementMap', { in: 'SourceGraphic', scale: '2.2' });
    const shapes = el(svg, 'g', { filter: 'url(#sketch-rough)' });
    const labels = el(svg, 'g', {});
    const probe = el(svg, 'text', { x: -999, y: -999, 'aria-hidden': 'true' });
    const measure = (text, size) => {
      probe.setAttribute('style', `font-family:var(--hand);font-size:${size}px`);
      probe.textContent = text;
      const width = probe.getComputedTextLength ? probe.getComputedTextLength() : 0;
      probe.textContent = '';
      return width || String(text).length * size * 0.58;
    };
    const text = (x, y, value, size, color, anchor) =>
      el(labels, 'text', { x: x.toFixed(1), y: y.toFixed(1), 'text-anchor': anchor || 'middle', style: `font-family:var(--hand);font-size:${size}px;fill:${color || INK}` }, value);
    // Text is measured in the hand font; if it was still loading, lay the last scene out again.
    let last = null;
    if (document.fonts && document.fonts.status !== 'loaded') document.fonts.ready.then(() => { if (last) draw(last, { svg, shapes, labels, measure, text }); });
    return { draw: scene => { last = scene; return draw(scene, { svg, shapes, labels, measure, text }); } };
  }

  const split = id => { const [row, rest] = String(id).split('.'); return [row, rest]; };
  const bez = (p, t) => {
    const u = 1 - t;
    return { x: u ** 3 * p[0].x + 3 * u * u * t * p[1].x + 3 * u * t * t * p[2].x + t ** 3 * p[3].x, y: u ** 3 * p[0].y + 3 * u * u * t * p[1].y + 3 * u * t * t * p[2].y + t ** 3 * p[3].y };
  };
  const overlap = (a, b, pad = 0) => a.x < b.x + b.w + pad && b.x < a.x + a.w + pad && a.y < b.y + b.h + pad && b.y < a.y + a.h + pad;

  function draw(scene, ctx) {
    const { svg, shapes, labels, measure, text } = ctx;
    shapes.replaceChildren(); labels.replaceChildren();
    const rows = (scene && scene.rows) || [];
    if (!rows.length) fail('scene.rows needs at least one row');
    const links = scene.links || [], pointers = scene.pointers || [];
    const focus = [].concat(scene.focus || []);
    const rowIds = new Set(), boxes = {}, order = [], pointerLevels = new Map();

    // A same-row link between non-neighbours arcs over the row, so leave room above the first row.
    const arcs = links.some(l => { const [ra, ia] = split(l.from), [rb, ib] = split(l.to); const r = rows.find(x => x.id === ra); return r && ra === rb && Math.abs(r.items.findIndex((it, i) => String(it.id ?? i) === ia) - r.items.findIndex((it, i) => String(it.id ?? i) === ib)) > 1; });
    const gutterWidth = Math.max(0, ...rows.map(r => (r.label ? measure(r.label, 16) : 0)));
    const gutter = gutterWidth ? Math.min(120, gutterWidth + 14) : 0;
    const left = PAD + gutter, avail = W - PAD - left;
    let y = PAD + (arcs ? 44 : 0);

    rows.forEach(row => {
      if (!row.id || /[.#]/.test(row.id) || rowIds.has(row.id)) fail(`row ids must be unique and contain no "." or "#": ${row.id}`);
      rowIds.add(row.id);
      const items = row.items || [];
      if (!items.length || items.length > 40) fail(`row "${row.id}" needs 1 to 40 items`);
      const bars = row.kind === 'bars';
      const chipSize = 16;
      const chipOf = c => (typeof c === 'object' ? c : { text: c });
      const chipsWidth = it => (it.chips || []).reduce((sum, c) => sum + Math.max(28, measure(String(chipOf(c).text), chipSize) + 14) + 6, 6);
      let font = 20;
      const widthFor = f => Math.max(bars ? 44 : 52, ...items.map(it => Math.max(measure(String(it.text ?? ''), f) + 22, chipsWidth(it))));
      let w = widthFor(font), per = Math.floor((avail + GAP) / (w + GAP));
      if (per < items.length && font > 16) { font = 16; w = widthFor(font); per = Math.floor((avail + GAP) / (w + GAP)); }
      if (w > avail) fail(`an item in row "${row.id}" is too wide to fit; shorten its text`);
      per = Math.max(1, Math.min(per, items.length));
      const lineCount = Math.ceil(items.length / per);
      per = Math.ceil(items.length / lineCount);
      const hasChips = items.some(it => it.chips && it.chips.length);
      const h = bars ? 150 : hasChips ? 88 : 58;
      // Pointers on the same item share one label ("lo / hi"); they would otherwise sit on each other.
      const merged = new Map();
      pointers.filter(p => split(p.at)[0] === row.id).forEach(p => {
        const seen = merged.get(p.at);
        if (seen) seen.text += ' / ' + p.text; else merged.set(p.at, { at: p.at, text: String(p.text), tone: p.tone });
      });
      const mine = [...merged.values()];
      // Where each item's centre falls, so pointer labels can be placed before the rows are stacked.
      const centreOf = index => {
        const li = Math.floor(index / per), count = Math.min(per, items.length - li * per);
        return left + (avail - (count * w + (count - 1) * GAP)) / 2 + (index - li * per) * (w + GAP) + w / 2;
      };
      // Pointer labels on one line drop to a second level when they would touch.
      const levels = [], laneOf = Array(lineCount).fill(0);
      mine.forEach(p => {
        const idx = items.findIndex((it, i) => String(it.id ?? i) === split(p.at)[1]);
        if (idx < 0) fail(`pointer "${p.text}" points at unknown "${p.at}"`);
        const li = Math.floor(idx / per), cx = centreOf(idx), width = measure(p.text, 18) + 10;
        let level = 0;
        while ((levels[level] || []).some(o => o.li === li && Math.abs(o.cx - cx) < (o.width + width) / 2 + 6)) level++;
        (levels[level] = levels[level] || []).push({ id: `${row.id}.${split(p.at)[1]}`, li, cx, width, p });
        laneOf[li] = Math.max(laneOf[li], 50 + 30 * level);
      });
      if (levels.length) pointerLevels.set(row, levels);
      let lineY = y;
      for (let li = 0; li < lineCount; li++) {
        const slice = items.slice(li * per, (li + 1) * per);
        const total = slice.length * w + (slice.length - 1) * GAP;
        let x = left + (avail - total) / 2;
        slice.forEach((it, k) => {
          const index = li * per + k, id = `${row.id}.${it.id ?? index}`;
          if (boxes[id]) fail(`duplicate item id "${id}"`);
          boxes[id] = { id, x, y: lineY, w, h, it, row, bars, font, chips: [] };
          order.push(boxes[id]);
          x += w + GAP;
        });
        lineY += h + laneOf[li] + (li < lineCount - 1 ? 22 : 0);
      }
      y = lineY + ROW_GAP;
    });
    const height = y - ROW_GAP + PAD + 6;

    // Boxes, chips, bar fills, then item text. Everything is derived from the measured layout.
    for (const b of order) {
      const state = b.it.state || '', done = state === 'done' || state === 'dim', active = state === 'active', hit = state === 'hit';
      const color = hit ? PEN : done ? MUTED : INK, ink = active ? HILITE_TEXT : done ? MUTED : INK;
      if (b.bars) {
        const values = b.row.items.map(it => Number(it.value) || 0), max = Math.max(1, ...values), room = b.h - 62;
        const barH = Math.max(4, (room * (Number(b.it.value) || 0)) / max), base = b.y + b.h - 30, bw = Math.min(b.w - 10, 56);
        const bx = b.x + (b.w - bw) / 2;
        el(shapes, 'rect', { x: bx.toFixed(1), y: (base - barH).toFixed(1), width: bw.toFixed(1), height: barH.toFixed(1), rx: 4, style: `${stroke(color, hit ? 3.2 : 2.4)};fill:${active ? 'var(--highlight)' : CARD}` });
        el(shapes, 'line', { x1: b.x, y1: base, x2: b.x + b.w, y2: base, style: stroke(MUTED, 1.6) });
        text(b.x + b.w / 2, base - barH - 7, b.it.value, 16, ink);
        text(b.x + b.w / 2, b.y + b.h - 8, b.it.text ?? '', b.font, ink);
        continue;
      }
      el(shapes, 'rect', { x: b.x.toFixed(1), y: b.y.toFixed(1), width: b.w.toFixed(1), height: b.h, rx: 11, style: `${stroke(color, hit ? 3.2 : 2.4)};fill:${active ? 'var(--highlight)' : CARD}` });
      const chips = b.it.chips || [];
      text(b.x + b.w / 2, chips.length ? b.y + 26 : b.y + b.h / 2 + b.font * 0.34, b.it.text ?? '', b.font, ink);
      const sizes = chips.map(c => Math.max(28, measure(String(chipOf(c).text), chipSize) + 14));
      let cx = b.x + (b.w - sizes.reduce((s, n) => s + n, 0) - 6 * (chips.length - 1)) / 2;
      chips.forEach((c, n) => {
        const chip = chipOf(c), cw = sizes[n], cy = b.y + b.h - 36;
        const chipId = `${b.id}#${n}`;
        boxes[chipId] = { id: chipId, x: cx, y: cy, w: cw, h: 28 };
        const on = chip.state === 'active';
        el(shapes, 'rect', { x: cx.toFixed(1), y: cy, width: cw, height: 28, rx: 7, style: `${stroke(chip.state === 'hit' ? PEN : INK, 2)};fill:${on ? 'var(--highlight)' : CARD}` });
        text(cx + cw / 2, cy + 20, chip.text, chipSize, on ? HILITE_TEXT : INK);
        cx += cw + 6;
      });
    }
    const box = id => boxes[id] || fail(`unknown id "${id}"; use "row.item" (or "row.item#n" for a chip)`);

    // Links: a curve from the nearest edge of one item to the nearest edge of another. Several
    // links leaving one edge fan out so they never start from the same point.
    const ends = [];
    const info = links.map((l, i) => {
      const a = box(l.from), b = box(l.to);
      const ac = { x: a.x + a.w / 2, y: a.y + a.h / 2 }, bc = { x: b.x + b.w / 2, y: b.y + b.h / 2 };
      const sameRow = Math.abs(ac.y - bc.y) < Math.max(a.h, b.h) / 2;
      const near = sameRow && Math.abs(ac.x - bc.x) <= a.w + GAP + 2;
      const kind = sameRow ? (near ? 'side' : 'arc') : 'vertical';
      const down = bc.y > ac.y;
      const sides = kind === 'vertical' ? [down ? 'bottom' : 'top', down ? 'top' : 'bottom'] : kind === 'arc' ? ['top', 'top'] : [bc.x > ac.x ? 'right' : 'left', bc.x > ac.x ? 'left' : 'right'];
      ends.push({ i, end: 'from', box: a, side: sides[0], other: bc.x }, { i, end: 'to', box: b, side: sides[1], other: ac.x });
      return { l, a, b, kind, down, sides, off: [0, 0] };
    });
    const groups = {};
    ends.forEach(e => (groups[e.box.id + '|' + e.side] = groups[e.box.id + '|' + e.side] || []).push(e));
    Object.values(groups).forEach(list => {
      list.sort((p, q) => p.other - q.other);
      const step = Math.min(14, (list[0].box.w - 20) / Math.max(1, list.length - 1));
      list.forEach((e, k) => { info[e.i].off[e.end === 'from' ? 0 : 1] = (k - (list.length - 1) / 2) * step; });
    });
    const claimed = [];
    const point = (b, side, off) => (side === 'top' ? { x: b.x + b.w / 2 + off, y: b.y - 4 } : side === 'bottom' ? { x: b.x + b.w / 2 + off, y: b.y + b.h + 4 } : side === 'right' ? { x: b.x + b.w + 4, y: b.y + b.h / 2 } : { x: b.x - 4, y: b.y + b.h / 2 });
    info.forEach(({ l, a, b, kind, down, sides, off }) => {
      const p0 = point(a, sides[0], off[0]), p1 = point(b, sides[1], off[1]);
      let c1, c2;
      if (kind === 'vertical') { const c = Math.max(24, Math.abs(p1.y - p0.y) * 0.5), s = down ? 1 : -1; c1 = { x: p0.x, y: p0.y + s * c }; c2 = { x: p1.x, y: p1.y - s * c }; }
      else if (kind === 'arc') { const rise = 34; c1 = { x: p0.x, y: p0.y - rise }; c2 = { x: p1.x, y: p1.y - rise }; }
      else { c1 = { x: (p0.x * 2 + p1.x) / 3, y: p0.y - 6 }; c2 = { x: (p0.x + p1.x * 2) / 3, y: p1.y - 6 }; }
      const curve = [p0, c1, c2, p1], color = toneColor(l.tone);
      el(shapes, 'path', { d: `M${p0.x.toFixed(1)} ${p0.y.toFixed(1)}C${c1.x.toFixed(1)} ${c1.y.toFixed(1)} ${c2.x.toFixed(1)} ${c2.y.toFixed(1)} ${p1.x.toFixed(1)} ${p1.y.toFixed(1)}`, style: stroke(color) });
      const angle = Math.atan2(p1.y - c2.y, p1.x - c2.x), head = (turn) => ({ x: p1.x - 11 * Math.cos(angle + turn), y: p1.y - 11 * Math.sin(angle + turn) });
      const h1 = head(0.5), h2 = head(-0.5);
      el(shapes, 'path', { d: `M${h1.x.toFixed(1)} ${h1.y.toFixed(1)}L${p1.x.toFixed(1)} ${p1.y.toFixed(1)}L${h2.x.toFixed(1)} ${h2.y.toFixed(1)}`, style: stroke(color) });
      if (l.label === undefined || l.label === '') return;
      const lw = measure(String(l.label), 16) + 12, lh = 22;
      const blockers = Object.values(boxes).filter(o => o.h > 0);
      let spot = null;
      for (const t of [0.5, 0.42, 0.58, 0.34, 0.66, 0.26, 0.74]) {
        const pt = bez(curve, t), r = { x: pt.x - lw / 2, y: pt.y - lh / 2, w: lw, h: lh };
        if (r.x < 4 || r.x + r.w > W - 4) continue;
        if (!claimed.some(c => overlap(r, c, 2)) && !blockers.some(o => overlap(r, o, 2))) { spot = r; break; }
      }
      if (!spot) { const pt = bez(curve, 0.5); spot = { x: pt.x - lw / 2, y: pt.y - lh / 2, w: lw, h: lh }; }
      claimed.push(spot);
      el(labels, 'rect', { x: spot.x.toFixed(1), y: spot.y.toFixed(1), width: lw.toFixed(1), height: lh, rx: 6, style: `fill:${CARD};stroke:none` });
      text(spot.x + lw / 2, spot.y + 16.5, l.label, 16, color);
    });

    // Pointers: a short arrow under an item and its name (lo, mid, hi, i, head ...).
    rows.forEach(row => (pointerLevels.get(row) || []).forEach((level, n) => level.forEach(({ id, cx, p }) => {
      const b = boxes[id];
      const color = toneColor(p.tone || 'pen'), top = b.y + b.h + 5, tip = top + 18 + 30 * n;
      el(shapes, 'path', { d: `M${cx.toFixed(1)} ${(tip + 2).toFixed(1)}L${cx.toFixed(1)} ${top.toFixed(1)}`, style: stroke(color, 2.2) });
      el(shapes, 'path', { d: `M${(cx - 6).toFixed(1)} ${(top + 9).toFixed(1)}L${cx.toFixed(1)} ${top.toFixed(1)}L${(cx + 6).toFixed(1)} ${(top + 9).toFixed(1)}`, style: stroke(color, 2.2) });
      text(cx, tip + 21, p.text, 18, color);
    })));

    // Focus: a pen outline hugging an item. Only an item that exists can be circled.
    focus.forEach(id => {
      const b = box(id);
      el(shapes, 'rect', { x: (b.x - 7).toFixed(1), y: (b.y - 7).toFixed(1), width: (b.w + 14).toFixed(1), height: (b.h + 14).toFixed(1), rx: 14, style: stroke(PEN, 3) });
    });
    // Left gutter labels, centered on the row.
    rows.forEach(row => {
      if (!row.label) return;
      const first = order.find(b => b.row === row);
      text(PAD, first.y + first.h / 2 + 5, row.label, 16, MUTED, 'start');
    });
    svg.setAttribute('viewBox', `0 0 ${W} ${Math.max(140, Math.ceil(height))}`);
  }

  /* Layout audit: text that overlaps other text, or runs outside the drawing. Used by the host's
     browser check on every observed state, so a cluttered or cut-off diagram is rejected. */
  function audit(root) {
    root = root || document.querySelector('#visual');
    const problems = [];
    root.querySelectorAll('svg').forEach(svg => {
      const frame = svg.getBoundingClientRect();
      const items = [...svg.querySelectorAll('text')].filter(t => t.textContent.trim()).map(t => ({ t: t.textContent.trim(), r: t.getBoundingClientRect() })).filter(i => i.r.width > 0 && i.r.height > 0 && i.r.bottom > frame.top - 1000);
      items.forEach(i => {
        if (i.r.left < frame.left - 1 || i.r.right > frame.right + 1 || i.r.top < frame.top - 1 || i.r.bottom > frame.bottom + 1) problems.push(`"${i.t.slice(0, 30)}" runs outside the drawing`);
      });
      for (let a = 0; a < items.length; a++) for (let b = a + 1; b < items.length; b++) {
        const p = items[a].r, q = items[b].r, ix = Math.min(p.right, q.right) - Math.max(p.left, q.left), iy = Math.min(p.bottom, q.bottom) - Math.max(p.top, q.top);
        if (ix > 1 && iy > 1 && ix * iy > 0.12 * Math.min(p.width * p.height, q.width * q.height)) problems.push(`"${items[a].t.slice(0, 30)}" overlaps "${items[b].t.slice(0, 30)}"`);
      }
    });
    return problems.slice(0, 5);
  }

  return { mount, audit };
})();
