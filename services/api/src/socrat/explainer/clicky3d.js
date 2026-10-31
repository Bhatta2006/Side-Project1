/* Clicky3D: the host's 3D product-render kit for generated visuals. The model describes parts,
   materials, camera and labels as data; this kit builds the meshes, fits the camera and draws the
   studio render. Trusted host code: injected before the generated scripts by compile_document. */
const Clicky3D = (() => {
  'use strict';

  const DEG = Math.PI / 180, TAU = Math.PI * 2;
  const clamp = (value, lo, hi) => Math.max(lo, Math.min(hi, value));
  const num = (value, fallback) => (typeof value === 'number' && isFinite(value) ? value : fallback);
  const vec3 = (value, fallback) => (Array.isArray(value) && value.length >= 3 && value.slice(0, 3).every(n => typeof n === 'number' && isFinite(n)) ? [value[0], value[1], value[2]] : fallback);

  // The 24 documented material names. Colors are only a default; a part's own color wins.
  const MATERIALS = {
    steel:      { color: '#B9C1CB', rough: 0.28, metal: 1.00, coat: 0.00, sheen: 0.00 },
    alu:        { color: '#C9CED6', rough: 0.32, metal: 1.00, coat: 0.00, sheen: 0.00 },
    aluminum:   { color: '#C9CED6', rough: 0.32, metal: 1.00, coat: 0.00, sheen: 0.00 },
    aluminium:  { color: '#C9CED6', rough: 0.32, metal: 1.00, coat: 0.00, sheen: 0.00 },
    titanium:   { color: '#A8AFB8', rough: 0.26, metal: 1.00, coat: 0.00, sheen: 0.00 },
    chrome:     { color: '#E6E9EE', rough: 0.08, metal: 1.00, coat: 0.00, sheen: 0.00 },
    brass:      { color: '#C9A25A', rough: 0.24, metal: 1.00, coat: 0.00, sheen: 0.00 },
    copper:     { color: '#C97A50', rough: 0.28, metal: 1.00, coat: 0.00, sheen: 0.00 },
    gold:       { color: '#E0B84F', rough: 0.22, metal: 1.00, coat: 0.00, sheen: 0.00 },
    iron:       { color: '#6E737B', rough: 0.50, metal: 1.00, coat: 0.00, sheen: 0.00 },
    black:      { color: '#23252B', rough: 0.42, metal: 0.25, coat: 0.18, sheen: 0.00 },
    rubber:     { color: '#2B2D33', rough: 0.82, metal: 0.00, coat: 0.00, sheen: 0.10 },
    glass:      { color: '#DCEAF2', rough: 0.05, metal: 0.00, coat: 0.00, sheen: 0.00, glass: true },
    water:      { color: '#7FB6D9', rough: 0.04, metal: 0.00, coat: 0.00, sheen: 0.00, glass: true },
    wood:       { color: '#B98A5B', rough: 0.56, metal: 0.00, coat: 0.00, sheen: 0.00 },
    ceramic:    { color: '#F0EBE0', rough: 0.28, metal: 0.00, coat: 0.26, sheen: 0.00 },
    paper:      { color: '#FAF5EA', rough: 0.72, metal: 0.00, coat: 0.00, sheen: 0.00 },
    gloss:      { color: '#E8E4DA', rough: 0.10, metal: 0.00, coat: 0.80, sheen: 0.00 },
    paint:      { color: '#C6CDD6', rough: 0.42, metal: 0.00, coat: 0.00, sheen: 0.00 },
    plastic:    { color: '#C6CDD6', rough: 0.30, metal: 0.00, coat: 0.40, sheen: 0.15 },
    soft:       { color: '#D8D2C6', rough: 0.86, metal: 0.00, coat: 0.00, sheen: 0.35 },
    matte:      { color: '#C6CDD6', rough: 0.90, metal: 0.00, coat: 0.00, sheen: 0.00 },
    metal:      { color: '#B9C1CB', rough: 0.30, metal: 1.00, coat: 0.00, sheen: 0.00 },
    glow:       { color: '#FFD479', rough: 0.50, metal: 0.00, coat: 0.00, sheen: 0.00, glow: true },
  };

  const KINDS = Clicky3DGeometry.kinds.filter(kind => kind !== 'cylinder');
  const DEFAULT_PAPER = '#FAF5EA';
  const DEFAULT_INK = '#15171C';

  // ------------------------------------------------------------------ colour
  // A 1×1 canvas normalises any CSS colour the model writes (#abc, rgb(), a name).
  const probe = document.createElement('canvas').getContext('2d');
  function rgbOf(value) {
    if (Array.isArray(value) && value.length >= 3) return value.slice(0, 3).map(v => clamp(num(v, 0), 0, 1));
    if (typeof value !== 'string' || !value.trim()) return null;
    probe.fillStyle = '#010203';
    probe.fillStyle = value;
    const text = String(probe.fillStyle);
    if (text[0] === '#') {
      const hex = text.length === 4 ? text.replace(/[0-9a-f]/gi, c => c + c) : text;
      return [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255);
    }
    const match = /rgba?\(([^)]+)\)/i.exec(text);
    if (!match) return null;
    const parts = match[1].split(',').map(v => parseFloat(v));
    return parts.slice(0, 3).map(v => clamp(v / 255, 0, 1));
  }
  function linearOf(value) {
    const rgb = rgbOf(value);
    if (!rgb) return [0.5, 0.5, 0.5];
    return rgb.map(v => (v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)));
  }
  const cssVar = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  function resolveColour(value, fallback) {
    if (typeof value === 'string') {
      const variable = /^var\((--[\w-]+)\)$/.exec(value.trim());
      if (variable) return cssVar(variable[1]) || fallback;
    }
    return value || fallback;
  }
  function luminance(value) {
    const rgb = rgbOf(value);
    return rgb ? rgb[0] * 0.2126 + rgb[1] * 0.7152 + rgb[2] * 0.0722 : 1;
  }
  function theme() {
    const style = getComputedStyle(document.documentElement);
    const background = style.getPropertyValue('--background').trim() || '#F6F5F0';
    const dark = luminance(background) < 0.35;
    const card = style.getPropertyValue('--card').trim() || (dark ? '#1A1B21' : '#FFFFFF');
    return {
      dark,
      paper: dark ? card : DEFAULT_PAPER,
      ink: dark ? (style.getPropertyValue('--foreground').trim() || '#ECEBE5') : DEFAULT_INK,
      pen: style.getPropertyValue('--pen').trim() || (dark ? '#FF7D72' : '#CC2A24'),
      primary: style.getPropertyValue('--primary').trim() || (dark ? '#4A63FF' : '#2340E8'),
      muted: style.getPropertyValue('--muted-foreground').trim() || (dark ? '#A4A39C' : '#5D5C57'),
    };
  }

  // ------------------------------------------------------------------ math
  const { m4, mul, perspective, lookAt, norm, cross, dot } = Clicky3DRender.math;

  function trs(at, rot, scale) {
    const cx = Math.cos(rot[0]), sx = Math.sin(rot[0]);
    const cy = Math.cos(rot[1]), sy = Math.sin(rot[1]);
    const cz = Math.cos(rot[2]), sz = Math.sin(rot[2]);
    // Ry * Rx * Rz, then a non-uniform scale.
    const r00 = cy * cz + sy * sx * sz, r01 = -cy * sz + sy * sx * cz, r02 = sy * cx;
    const r10 = cx * sz, r11 = cx * cz, r12 = -sx;
    const r20 = -sy * cz + cy * sx * sz, r21 = sy * sz + cy * sx * cz, r22 = cy * cx;
    const m = m4();
    m[0] = r00 * scale[0]; m[1] = r10 * scale[0]; m[2] = r20 * scale[0];
    m[4] = r01 * scale[1]; m[5] = r11 * scale[1]; m[6] = r21 * scale[1];
    m[8] = r02 * scale[2]; m[9] = r12 * scale[2]; m[10] = r22 * scale[2];
    m[12] = at[0]; m[13] = at[1]; m[14] = at[2]; m[15] = 1;
    return m;
  }
  function normalMatrix(m) {
    const a = m[0], b = m[4], c = m[8], d = m[1], e = m[5], f = m[9], g = m[2], h = m[6], i = m[10];
    const A = e * i - f * h, B = f * g - d * i, C = d * h - e * g;
    const det = a * A + b * B + c * C || 1;
    // Inverse-transpose = cofactor matrix / det, written column-major for uniformMatrix3fv.
    const C10 = c * h - b * i, C11 = a * i - c * g, C12 = b * g - a * h;
    const C20 = b * f - c * e, C21 = c * d - a * f, C22 = a * e - b * d;
    return new Float32Array([A / det, C10 / det, C20 / det, B / det, C11 / det, C21 / det, C / det, C12 / det, C22 / det]);
  }
  function apply(m, point) {
    const x = point[0], y = point[1], z = point[2];
    return [m[0] * x + m[4] * y + m[8] * z + m[12], m[1] * x + m[5] * y + m[9] * z + m[13], m[2] * x + m[6] * y + m[10] * z + m[14]];
  }
  function rotatePoint(rot, point) {
    const cx = Math.cos(rot[0]), sx = Math.sin(rot[0]);
    const cy = Math.cos(rot[1]), sy = Math.sin(rot[1]);
    const cz = Math.cos(rot[2]), sz = Math.sin(rot[2]);
    const x = point[0], y = point[1], z = point[2];
    // Rz, then Rx, then Ry (the inverse composition of trs).
    const x1 = x * cz - y * sz, y1 = x * sz + y * cz, z1 = z;
    const y2 = y1 * cx - z1 * sx, z2 = y1 * sx + z1 * cx;
    return [x1 * cy + z2 * sy, y2, -x1 * sy + z2 * cy];
  }

  // ------------------------------------------------------------------ geometry cache
  const geometryCache = new Map();
  function canonical(value) {
    if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
    if (value && typeof value === 'object') {
      return '{' + Object.keys(value).sort().filter(key => value[key] !== undefined && typeof value[key] !== 'function').map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
    }
    if (typeof value === 'number') return isFinite(value) ? String(Math.round(value * 10000) / 10000) : '0';
    return JSON.stringify(value);
  }
  function geometryOf(kind, recipe) {
    kind = String(kind || 'box');
    if (!Clicky3DGeometry.kinds.includes(kind)) kind = 'box';
    const key = kind + '|' + canonical(recipe || {});
    let geometry = geometryCache.get(key);
    if (!geometry) {
      try {
        geometry = Clicky3DGeometry.build(kind, recipe || {});
      } catch (error) {
        geometry = Clicky3DGeometry.build('box', {});
      }
      geometryCache.set(key, geometry);
    }
    return geometry;
  }

  function fitDistance(points, center, yaw, tilt, fov, aspect) {
    const dir = [Math.sin(yaw) * Math.cos(tilt), Math.sin(tilt), Math.cos(yaw) * Math.cos(tilt)];
    const forward = [-dir[0], -dir[1], -dir[2]];
    const right = norm(cross(forward, [0, 1, 0]));
    const up = cross(right, forward);
    const tanHalf = Math.tan((fov * DEG) / 2);
    let distance = 0;
    for (const p of points) {
      const x = p[0] - center[0], y = p[1] - center[1], z = p[2] - center[2];
      const across = Math.abs(dot([x, y, z], right)) / Math.max(1e-4, tanHalf * aspect);
      const upward = Math.abs(dot([x, y, z], up)) / Math.max(1e-4, tanHalf);
      const depth = dot([x, y, z], forward);
      distance = Math.max(distance, across - depth, upward - depth);
    }
    return Math.max(1.2, distance);
  }

  const project = (() => {
    let cache = null;
    return (eye, target, fov, aspect, point) => {
      if (!cache || cache.eye !== eye || cache.target !== target || cache.fov !== fov || cache.aspect !== aspect) {
        const view = lookAt(eye, target, [0, 1, 0]);
        cache = { eye, target, fov, aspect, vp: mul(perspective(fov, aspect, 0.1, 200), view) };
      }
      const vp = cache.vp;
      const w = vp[3] * point[0] + vp[7] * point[1] + vp[11] * point[2] + vp[15];
      if (!isFinite(w) || w <= 1e-5) return null;
      const x = (vp[0] * point[0] + vp[4] * point[1] + vp[8] * point[2] + vp[12]) / w;
      const y = (vp[1] * point[0] + vp[5] * point[1] + vp[9] * point[2] + vp[13]) / w;
      return { x: (x * 0.5 + 0.5), y: (1 - (y * 0.5 + 0.5)) };
    };
  })();

  const smooth = t => t * t * (3 - 2 * t);
  const same = (a, b) => Math.abs(a[0] - b[0]) < 1e-4 && Math.abs(a[1] - b[1]) < 1e-4 && Math.abs(a[2] - b[2]) < 1e-4;
  const lerp3 = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

  // ------------------------------------------------------------------ labels
  const NS = 'http://www.w3.org/2000/svg';
  // Every mounted board: the host's browser checker audits 3D label layout the way it audits Sketch.
  const boards = [];
  function audit() {
    return boards.flatMap(board => board.audit());
  }

  // Callouts speak Socrat's language: a card-surface tag in Geist, a hairline border, and a number
  // badge in the app's primary blue. The tone only recolours the badge: primary (default), pen
  // for the part that matters most, muted for context.
  function toneOf(tone) {
    if (tone === 'pen') return { fill: 'var(--chart-5,#D3302A)', text: '#FFFFFF' };
    if (tone === 'muted') return { fill: 'var(--muted,#EEECE5)', text: 'var(--muted-foreground,#5D5C57)' };
    return { fill: 'var(--primary,#2340E8)', text: 'var(--primary-foreground,#FFFFFF)' };
  }

  // ------------------------------------------------------------------ mount
  function mount(host, options) {
    host = typeof host === 'string' ? document.querySelector(host) : host;
    if (!host) throw new Error('Clicky3D: host element not found');
    options = options || {};

    const wrap = document.createElement('div');
    wrap.className = 'clicky3d';
    wrap.style.cssText = 'position:relative;width:100%;height:100%;min-height:240px;overflow:hidden;border-radius:14px;isolation:isolate;background:' + theme().paper;
    const canvas = document.createElement('canvas');
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', String(options.desc || '3D visual'));
    canvas.style.cssText = 'display:block;width:100%;height:100%';
    const leaders = document.createElementNS(NS, 'svg');
    leaders.setAttribute('aria-hidden', 'true');
    leaders.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible;z-index:2';
    const layer = document.createElement('div');
    layer.style.cssText = 'position:absolute;inset:0;pointer-events:none;z-index:3';
    wrap.append(canvas, leaders, layer);
    host.appendChild(wrap);

    let renderer = null;
    let failure = '';
    try {
      renderer = Clicky3DRender.create(canvas);
    } catch (error) {
      failure = String(error && error.message ? error.message : error);
      const note = document.createElement('p');
      note.textContent = 'This device cannot draw the 3D view.';
      note.style.cssText = 'position:absolute;inset:0;display:grid;place-items:center;margin:0;color:#5D5C57;font:14px/1.4 ui-sans-serif,system-ui,sans-serif';
      wrap.appendChild(note);
    }

    const state = {
      scene: { parts: [], labels: [] },
      tracks: new Map(),
      labels: [],
      width: 0,
      height: 0,
      dpr: 1,
      mounted: performance.now(),
      distance: 0,
      center: [0, 0.5, 0],
      extent: 1,
      raf: 0,
      reduced: !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches),
    };

    // ---------------------------------------------------------------- interaction
    // The reader orbits the scene, not the camera rig: drag swings yaw and tilt, wheel or
    // pinch changes the framing, and the turntable waits until they let go.
    const view = { yaw: 0, tilt: 0, zoom: 1 };
    const drag = { id: null, x: 0, y: 0, yaw: 0, tilt: 0, last: 0, vYaw: 0 };
    let spinAngle = 0;
    let spinResumeAt = 0;
    let fling = 0;
    let lastRender = 0;
    const ROTATE = 0.0085;
    const TILT_STEP = 0.0065;
    const MIN_TILT = -0.12;
    const MAX_TILT = 1.28;
    const MIN_ZOOM = 0.62;
    const MAX_ZOOM = 2.6;

    canvas.style.cursor = 'grab';
    canvas.style.touchAction = 'none';
    canvas.title = 'Drag to rotate, scroll to zoom';
    wrap.tabIndex = 0;
    wrap.setAttribute('role', 'group');
    wrap.setAttribute('aria-label', String(options.desc || '3D visual')
      + '. Drag to rotate, scroll to zoom, arrow keys to turn.');

    const hint = document.createElement('div');
    hint.textContent = 'Drag to rotate · scroll to zoom';
    hint.style.cssText = 'position:absolute;right:10px;bottom:10px;z-index:4;pointer-events:none;'
      + 'font:500 11px/1 ui-sans-serif,system-ui,sans-serif;letter-spacing:.02em;'
      + 'color:color-mix(in srgb,' + theme().ink + ' 62%,transparent);'
      + 'background:color-mix(in srgb,' + theme().paper + ' 82%,transparent);'
      + 'border-radius:999px;padding:5px 8px;opacity:.9;transition:opacity .4s ease';
    wrap.appendChild(hint);
    function dismissHint() {
      if (!hint.isConnected) return;
      hint.style.opacity = '0';
      setTimeout(() => hint.remove(), 450);
    }
    setTimeout(dismissHint, 7000);

    function beginDrag(event) {
      if (drag.id !== null) return;
      if (event.pointerType === 'mouse' && event.button !== 0) return;
      drag.id = event.pointerId;
      drag.x = event.clientX;
      drag.y = event.clientY;
      drag.yaw = view.yaw;
      drag.tilt = view.tilt;
      drag.last = performance.now();
      drag.vYaw = 0;
      fling = 0;
      spinResumeAt = Infinity;
      canvas.style.cursor = 'grabbing';
      if (canvas.setPointerCapture) canvas.setPointerCapture(event.pointerId);
      dismissHint();
      event.preventDefault();
    }

    function moveDrag(event) {
      if (event.pointerId !== drag.id) return;
      const now = performance.now();
      const dt = Math.max(8, now - drag.last) / 1000;
      const nextYaw = drag.yaw - (event.clientX - drag.x) * ROTATE;
      const nextTilt = clamp(drag.tilt + (event.clientY - drag.y) * TILT_STEP, MIN_TILT, MAX_TILT);
      drag.vYaw = (nextYaw - view.yaw) / dt;
      view.yaw = nextYaw;
      view.tilt = nextTilt;
      drag.last = now;
      render(now);
      event.preventDefault();
    }

    function endDrag(event) {
      if (event.pointerId !== drag.id) return;
      drag.id = null;
      canvas.style.cursor = 'grab';
      const now = performance.now();
      const still = now - drag.last > 90;
      fling = state.reduced || still ? 0 : clamp(drag.vYaw, -4.5, 4.5);
      if (Math.abs(fling) < 0.12) fling = 0;
      spinResumeAt = now + 2400;
      if (canvas.hasPointerCapture && canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
      schedule();
    }

    function zoomBy(factor) {
      view.zoom = clamp(view.zoom * factor, MIN_ZOOM, MAX_ZOOM);
      spinResumeAt = performance.now() + 2400;
      render(performance.now());
    }

    function resetView() {
      view.yaw = 0;
      view.tilt = 0;
      view.zoom = 1;
      spinAngle = 0;
      fling = 0;
      drag.vYaw = 0;
      spinResumeAt = performance.now() + 1200;
      render(performance.now());
    }

    canvas.addEventListener('pointerdown', beginDrag);
    canvas.addEventListener('pointermove', moveDrag);
    canvas.addEventListener('pointerup', endDrag);
    canvas.addEventListener('pointercancel', endDrag);
    canvas.addEventListener('lostpointercapture', event => { if (event.pointerId === drag.id) endDrag(event); });
    canvas.addEventListener('wheel', event => {
      event.preventDefault();
      const delta = clamp(event.deltaY, -240, 240);
      zoomBy(Math.exp(delta * 0.0016));
    }, { passive: false });
    canvas.addEventListener('dblclick', event => { event.preventDefault(); resetView(); });
    wrap.addEventListener('keydown', event => {
      const step = (event.shiftKey ? 24 : 8) * DEG;
      if (event.key === 'ArrowLeft') view.yaw -= step;
      else if (event.key === 'ArrowRight') view.yaw += step;
      else if (event.key === 'ArrowUp') view.tilt = clamp(view.tilt + step, MIN_TILT, MAX_TILT);
      else if (event.key === 'ArrowDown') view.tilt = clamp(view.tilt - step, MIN_TILT, MAX_TILT);
      else if (event.key === '+' || event.key === '=') { event.preventDefault(); zoomBy(0.88); return; }
      else if (event.key === '-' || event.key === '_') { event.preventDefault(); zoomBy(1 / 0.88); return; }
      else if (event.key === '0' || event.key === 'Home') { event.preventDefault(); resetView(); return; }
      else return;
      event.preventDefault();
      spinResumeAt = performance.now() + 2400;
      render(performance.now());
    });

    function resize() {
      const width = Math.max(200, Math.round(wrap.clientWidth || host.clientWidth || 640));
      // `fill`: the host sets the height (a film's stage); otherwise the board sizes itself.
      const fill = options.fill && host.clientHeight > 0;
      const height = fill ? Math.max(240, Math.round(host.clientHeight)) : Math.max(240, Math.min(600, Math.round(width * 0.66)));
      if (width === state.width && height === state.height && renderer) return;
      state.width = width;
      state.height = height;
      state.dpr = Math.min(2, Math.max(1, window.devicePixelRatio || 1));
      wrap.style.height = fill ? '100%' : height + 'px';
      leaders.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
      if (renderer) renderer.setSize(width, height, state.dpr);
      if (state.scene.parts) render(performance.now());
    }

    // Attachments: a part with `on` is placed by the kit, flush against a face of another part
    // that shares its parent (or centred inside it), from both meshes' real extents. Authors give
    // the main body coordinates and attach the rest, so nothing floats.
    function placeParts(specs) {
      const byId = new Map(), placed = new Map();
      for (const spec of specs) if (spec && typeof spec === 'object' && spec.id !== undefined) byId.set(String(spec.id), spec);
      const boxOf = (spec, at) => {
        const geometry = geometryOf(spec.kind, spec.recipe);
        const raw = spec.scale === undefined ? 1 : spec.scale;
        const scale = Array.isArray(raw) ? vec3(raw, [1, 1, 1]) : [num(raw, 1), num(raw, 1), num(raw, 1)];
        const m = trs(at, vec3(spec.rot || spec.rotate, [0, 0, 0]).map(v => v * DEG), scale);
        const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
        const stride = Math.max(1, Math.floor(geometry.samples.length / 900));
        for (let i = 0; i < geometry.samples.length; i += 3 * stride) {
          const q = apply(m, [geometry.samples[i], geometry.samples[i + 1], geometry.samples[i + 2]]);
          for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], q[k]); hi[k] = Math.max(hi[k], q[k]); }
        }
        if (!isFinite(lo[0])) return { lo: at.slice(), hi: at.slice() };
        return { lo, hi };
      };
      const place = (spec, depth) => {
        const id = String(spec.id);
        if (placed.has(id)) return placed.get(id);
        placed.set(id, vec3(spec.at || spec.pos, [0, 0, 0]));
        const on = spec.on;
        const target = on && typeof on === 'object' ? byId.get(String(on.part)) : null;
        if (target && target !== spec && depth < 24 && String(target.kind) !== 'group' && String(target.parent || '') === String(spec.parent || '')) {
          const T = boxOf(target, place(target, depth + 1)), S = boxOf(spec, [0, 0, 0]);
          const face = String(on.face || '+y').toLowerCase();
          const inside = face === 'inside';
          const k = 'xyz'.indexOf(face.replace(/[^xyz]/g, '')), sign = face[0] === '-' ? -1 : 1;
          const align = vec3(on.align, [0, 0, 0]), offset = vec3(on.offset, [0, 0, 0]), inset = clamp(num(on.inset, 0), -1, 1);
          const at = [0, 1, 2].map(j => (T.lo[j] + T.hi[j]) / 2 + clamp(align[j], -1, 1) * (T.hi[j] - T.lo[j]) / 2 - (S.lo[j] + S.hi[j]) / 2);
          if (!inside && k >= 0) {
            const size = S.hi[k] - S.lo[k];
            at[k] = sign > 0 ? T.hi[k] - S.lo[k] - inset * size : T.lo[k] - S.hi[k] + inset * size;
          }
          placed.set(id, [at[0] + offset[0], at[1] + offset[1], at[2] + offset[2]]);
        }
        return placed.get(id);
      };
      for (const spec of byId.values()) place(spec, 0);
      seat(byId, placed, boxOf);
      return placed;
    }

    // Seating: an assembled object is one piece. Within every parent, each child (a part, or a
    // group with everything inside it) is boxed; any cluster left floating apart from the main
    // body (the largest by volume) slides straight toward its nearest neighbour until it touches.
    // The deepest groups are seated first, so a sub-assembly is whole before it is placed, and an
    // author's rough coordinates still give a coherent model.
    function seat(byId, placed, boxOf) {
      const children = new Map();
      for (const spec of byId.values()) {
        if (spec.hidden) continue;
        const key = String(spec.parent || '');
        if (!children.has(key)) children.set(key, []);
        children.get(key).push(spec);
      }
      const matrixOf = spec => {
        const raw = spec.scale === undefined ? 1 : spec.scale;
        const scale = Array.isArray(raw) ? vec3(raw, [1, 1, 1]) : [num(raw, 1), num(raw, 1), num(raw, 1)];
        return trs(placed.get(String(spec.id)), vec3(spec.rot || spec.rotate, [0, 0, 0]).map(v => v * DEG), scale);
      };
      // A child's box in its parent's frame: its own mesh plus its whole subtree.
      const outerBox = (spec, depth) => {
        let lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
        const grow = q => { for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], q[k]); hi[k] = Math.max(hi[k], q[k]); } };
        if (String(spec.kind) !== 'group') {
          const own = boxOf(spec, placed.get(String(spec.id)));
          if (own.hi[0] > own.lo[0] || own.hi[1] > own.lo[1] || own.hi[2] > own.lo[2]) { grow(own.lo); grow(own.hi); }
        }
        if (depth < 12) {
          const m = matrixOf(spec);
          for (const child of children.get(String(spec.id)) || []) {
            const box = outerBox(child, depth + 1);
            if (!box) continue;
            for (let c = 0; c < 8; c++) grow(apply(m, [c & 1 ? box.hi[0] : box.lo[0], c & 2 ? box.hi[1] : box.lo[1], c & 4 ? box.hi[2] : box.lo[2]]));
          }
        }
        return isFinite(lo[0]) ? { lo, hi } : null;
      };
      const depthOf = key => { let d = 0; for (let id = key; id && byId.has(id) && d < 24; id = String(byId.get(id).parent || '')) d++; return d; };
      const volume = b => Math.max(1e-6, (b.hi[0] - b.lo[0]) * (b.hi[1] - b.lo[1]) * (b.hi[2] - b.lo[2]));
      const separation = (A, B) => [0, 1, 2].map(k => (A.lo[k] - B.hi[k] > 0 ? A.lo[k] - B.hi[k] : B.lo[k] - A.hi[k] > 0 ? -(B.lo[k] - A.hi[k]) : 0));
      const families = [...children.keys()].sort((x, y) => depthOf(y) - depthOf(x));
      for (const key of families) {
        const boxes = [];
        for (const spec of children.get(key)) { const box = outerBox(spec, 0); if (box) boxes.push({ spec, lo: box.lo, hi: box.hi }); }
        if (boxes.length < 2) continue;
        const lo = [0, 1, 2].map(k => Math.min(...boxes.map(b => b.lo[k]))), hi = [0, 1, 2].map(k => Math.max(...boxes.map(b => b.hi[k])));
        const gap = Math.max(0.005, Math.hypot(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]) * 0.01);
        for (let round = 0; round < boxes.length; round++) {
          const root = boxes.map((_, i) => i);
          const find = i => (root[i] === i ? i : (root[i] = find(root[i])));
          for (let a = 0; a < boxes.length; a++) for (let b = a + 1; b < boxes.length; b++) {
            if (separation(boxes[a], boxes[b]).every(v => Math.abs(v) <= gap)) root[find(a)] = find(b);
          }
          const sizes = new Map();
          boxes.forEach((b, i) => sizes.set(find(i), (sizes.get(find(i)) || 0) + volume(b)));
          if (sizes.size < 2) break;
          const main = [...sizes.entries()].sort((x, y) => y[1] - x[1])[0][0];
          let best = null;
          boxes.forEach((A, i) => {
            if (find(i) === main) return;
            boxes.forEach((B, j) => {
              if (find(j) !== main) return;
              const g = separation(A, B), d = Math.hypot(g[0], g[1], g[2]);
              if (!best || d < best.d) best = { d, g, cluster: find(i) };
            });
          });
          if (!best) break;
          // Move only along the separated axes, a hair past touching so the seam closes.
          const move = best.g.map(v => (v > 0 ? -(v + gap * 0.5) : v < 0 ? -v + gap * 0.5 : 0));
          boxes.forEach((b, i) => {
            if (find(i) !== best.cluster) return;
            const id = String(b.spec.id), at = placed.get(id);
            placed.set(id, [at[0] + move[0], at[1] + move[1], at[2] + move[2]]);
            for (let k = 0; k < 3; k++) { b.lo[k] += move[k]; b.hi[k] += move[k]; }
          });
        }
      }
    }

    function sceneParts(scene) {
      const specs = Array.isArray(scene.parts) ? scene.parts : [];
      const placed = placeParts(specs);
      const list = expandParts(specs);
      const now = performance.now();
      const tracks = new Map();
      const parts = list.map(({ spec: part, id, base, array, copy }, index) => {
        const at = placed.has(base) ? placed.get(base).slice() : vec3(part.at || part.pos, [0, 0, 0]);
        const rotation = vec3(part.rot || part.rotate, [0, 0, 0]).map(v => v * DEG);
        const raw = part.scale === undefined ? 1 : part.scale;
        const scale = (Array.isArray(raw) ? vec3(raw, [1, 1, 1]) : [num(raw, 1), num(raw, 1), num(raw, 1)]).map(v => (Math.abs(v) < 1e-4 ? 1e-4 : v));
        const target = { at, rot: rotation, scale };
        let track = state.tracks.get(id);
        if (!track) {
          track = { current: { at: at.slice(), rot: rotation.slice(), scale: scale.slice() }, from: null, target, start: now, born: now };
        } else if (!same(track.target.at, at) || !same(track.target.rot, rotation) || !same(track.target.scale, scale)) {
          track.from = { at: track.current.at.slice(), rot: track.current.rot.slice(), scale: track.current.scale.slice() };
          track.target = target;
          track.start = now;
        }
        tracks.set(id, track);
        return { spec: part, id, base, array, copy, track, index, group: String(part.kind || '') === 'group' };
      });
      state.tracks = tracks;
      return parts;
    }

    // Copies, radial arrays and mirrors expand into plain parts that share one cached mesh.
    // A copy's id is "<id>.<k>"; labels and parents can name either the copy or the base id.
    function expandParts(list) {
      const out = [];
      list.forEach((part, index) => {
        if (!part || typeof part !== 'object' || part.hidden) return;
        const id = String(part.id || 'part' + index);
        const arrays = [];
        const around = part.around;
        if (around && typeof around === 'object') {
          const count = clamp(Math.round(num(around.count, 6)), 1, 400);
          const angle = num(around.angle, 360);
          const step = Math.abs(angle) >= 359.999 ? angle / count : count > 1 ? angle / (count - 1) : 0;
          const axis = axisOf(around.axis);
          const center = vec3(around.center || around.at, [0, 0, 0]);
          const start = num(around.start, 0);
          for (let k = 0; k < count; k++) arrays.push(aroundMatrix(axis, (start + k * step) * DEG, center));
        } else if (part.copies !== undefined) {
          const count = clamp(Math.round(num(part.copies, 1)), 1, 400);
          const step = vec3(part.step, [0, 0, 0]);
          const turnStep = vec3(part.turn, [0, 0, 0]).map(v => v * DEG);
          for (let k = 0; k < count; k++) arrays.push(trs([step[0] * k, step[1] * k, step[2] * k], [turnStep[0] * k, turnStep[1] * k, turnStep[2] * k], [1, 1, 1]));
        }
        if (!arrays.length) out.push({ spec: part, id, base: id, array: null, copy: -1 });
        else arrays.forEach((matrix, k) => out.push({ spec: part, id: id + '.' + k, base: id, array: matrix, copy: k }));
      });
      return out.slice(0, 1200);
    }
    function axisOf(axis) {
      if (typeof axis === 'string') {
        const key = axis.replace(/[^xyz]/gi, '').toLowerCase();
        const sign = /^\s*-/.test(axis) ? -1 : 1;
        return key === 'x' ? [sign, 0, 0] : key === 'z' ? [0, 0, sign] : [0, sign, 0];
      }
      return norm(vec3(axis, [0, 1, 0]));
    }
    function aroundMatrix(axis, angle, center) {
      const [x, y, z] = norm(axis), c = Math.cos(angle), s = Math.sin(angle), t = 1 - c;
      const m = m4();
      m[0] = t * x * x + c; m[1] = t * x * y + s * z; m[2] = t * x * z - s * y;
      m[4] = t * x * y - s * z; m[5] = t * y * y + c; m[6] = t * y * z + s * x;
      m[8] = t * x * z + s * y; m[9] = t * y * z - s * x; m[10] = t * z * z + c;
      // Rotate about the line through `center`: p' = R (p - c) + c.
      m[12] = center[0] - (m[0] * center[0] + m[4] * center[1] + m[8] * center[2]);
      m[13] = center[1] - (m[1] * center[0] + m[5] * center[1] + m[9] * center[2]);
      m[14] = center[2] - (m[2] * center[0] + m[6] * center[1] + m[10] * center[2]);
      m[15] = 1;
      return m;
    }
    function mirrorOf(value) {
      if (typeof value === 'string') return ['x', 'y', 'z'].map(k => (value.toLowerCase().includes(k) ? -1 : 1));
      return vec3(value, [1, 1, 1]).map(v => (v < 0 ? -1 : 1));
    }
    const det3 = m => m[0] * (m[5] * m[10] - m[9] * m[6]) - m[4] * (m[1] * m[10] - m[9] * m[2]) + m[8] * (m[1] * m[6] - m[5] * m[2]);

    // World matrices for this frame: array placement, the part's own (eased) transform, then
    // its parent's world matrix. Groups are pivots with no mesh; moving one moves its children.
    function computeWorld(parts, now) {
      const byId = new Map(), byBase = new Map();
      for (const part of parts) {
        byId.set(part.id, part);
        if (!byBase.has(part.base)) byBase.set(part.base, part);
        const display = displayOf(part, now);
        const mirror = mirrorOf(part.spec.mirror);
        const scaled = [display.scale[0] * mirror[0], display.scale[1] * mirror[1], display.scale[2] * mirror[2]];
        // A film's continuous motion (spin, slide, swing) acts in the part's own frame, between
        // its rotation and its scale, so children of a spinning group spin with it.
        const motion = state.frame && state.frame.motion ? state.frame.motion(part) : null;
        const local = motion ? mul(trs(display.at, display.rot, [1, 1, 1]), mul(motion, trs([0, 0, 0], [0, 0, 0], scaled))) : trs(display.at, display.rot, scaled);
        part.display = display;
        part.local = part.array ? mul(part.array, local) : local;
        part.world = null;
      }
      const resolve = (part, depth) => {
        if (part.world) return part.world;
        const key = part.spec.parent === undefined ? '' : String(part.spec.parent);
        // A copy's child follows the matching copy of an arrayed parent when one exists.
        const parent = key && depth < 24 ? (part.copy >= 0 && byId.get(key + '.' + part.copy)) || byId.get(key) || byBase.get(key) : null;
        part.world = parent && parent !== part ? mul(resolve(parent, depth + 1), part.local) : part.local;
        part.parentPart = parent && parent !== part ? parent : null;
        part.root = parent && parent !== part ? parent.root : part;
        return part.world;
      };
      for (const part of parts) resolve(part, 0);
      for (const part of parts) part.model = part.world;
    }

    function displayOf(part, now) {
      if (state.frame) {
        const target = part.track.target;
        const pose = state.frame.pose ? state.frame.pose(part) : null;
        let at = pose && pose.at ? pose.at : target.at;
        const rot = pose && pose.rot ? pose.rot : target.rot;
        const scale = pose && pose.scale ? pose.scale : target.scale;
        const explode = state.frame.explode || 0;
        if (explode) {
          // Exploded view: the part's own explode vector, or 60% further out from its parent.
          const away = vec3(part.spec.explode, [target.at[0] * 0.6, target.at[1] * 0.6, target.at[2] * 0.6]);
          at = [at[0] + away[0] * explode, at[1] + away[1] * explode, at[2] + away[2] * explode];
        }
        part.track.current = { at: at.slice(), rot: rot.slice(), scale: scale.slice() };
        part.track.from = null;
        return { at, rot, scale };
      }
      const track = part.track;
      const target = track.target;
      if (track.from && (state.reduced || now - track.start >= 440)) track.from = null;
      const t = track.from ? smooth(clamp((now - track.start) / 440, 0, 1)) : 1;
      const from = track.from || track.current;
      const at = lerp3(from.at, target.at, t);
      const rot = lerp3(from.rot, target.rot, t);
      const scale = lerp3(from.scale, target.scale, t);
      const grow = state.reduced ? 1 : 0.72 + 0.28 * smooth(clamp((now - track.born) / 520, 0, 1));
      let pulse = 0;
      if (!state.reduced && part.spec.pulse) pulse = (typeof part.spec.pulse === 'number' ? clamp(part.spec.pulse, 0, 0.3) : 0.035) * Math.sin((now - state.mounted) / 1000 * TAU * 0.55 + part.index * 1.7);
      const display = { at, rot, scale: scale.map(v => v * grow * (1 + pulse)) };
      track.current = { at: at.slice(), rot: rot.slice(), scale: scale.slice() };
      return display;
    }

    function buildObjects(parts, now, eye) {
      const frame = state.frame;
      const objects = parts.filter(part => !part.group && (!frame || !frame.opacity || frame.opacity(part) > 0.02)).map(part => {
        const spec = part.spec;
        const display = part.display;
        const model = part.model;
        const matrix = normalMatrix(model);
        const material = MATERIALS[String(spec.mat || spec.material || 'paint')] || MATERIALS.paint;
        const colour = linearOf(resolveColour(spec.color, material.color));
        const opacity = clamp(num(spec.opacity, 1), 0, 1) * (frame && frame.opacity ? frame.opacity(part) : 1);
        const glass = !!material.glass || !!spec.glass;
        const cut = cutPlane(spec.cut, part);
        const bands = bandData(spec);
        const glow = material.glow || spec.glow ? Math.max(0, num(spec.glow, 0.9)) : 0;
        const doubleSided = !!spec.double || !!cut;
        return {
          id: part.index + 1,
          part,
          geometry: geometryOf(spec.kind, spec.recipe),
          model,
          normal: matrix,
          flip: det3(model) < 0,
          base: [colour[0], colour[1], colour[2], 1],
          emissive: glow ? [colour[0] * glow, colour[1] * glow, colour[2] * glow, 1] : [0, 0, 0, 0],
          surface: [clamp(num(spec.rough, material.rough), 0.04, 1), clamp(num(spec.metal, material.metal), 0, 1), opacity, bands.count],
          coat: [glass ? 0 : clamp(num(spec.coat, material.coat), 0, 1), 0.06, clamp(num(spec.sheen, material.sheen), 0, 1), glass ? 1 : 0],
          flags: [0, spec.flat ? 1 : 0, doubleSided ? 1 : 0, 0],
          cut,
          bandData: bands.data,
          doubleSided,
          transparent: glass || opacity < 0.999,
          depth: Math.hypot(model[12] - eye[0], model[13] - eye[1], model[14] - eye[2]),
          display,
        };
      });
      if (frame && frame.flows) for (const item of frame.flows(parts)) objects.push(flowObject(item, eye));
      return objects;
    }

    // One particle of a flow: a small lit bead, tinted along the path (cold to hot, say).
    function flowObject(item, eye) {
      const colour = linearOf(resolveColour(item.color, '#7FA8FF'));
      const glow = item.glow;
      const model = item.model;
      return {
        id: 0,
        part: null,
        geometry: geometryOf('capsule', { r: 1, h: 2, seg: 12 }),
        model,
        normal: normalMatrix(model),
        flip: false,
        base: [colour[0], colour[1], colour[2], 1],
        emissive: glow ? [colour[0] * glow, colour[1] * glow, colour[2] * glow, 1] : [0, 0, 0, 0],
        surface: [0.35, 0, item.alpha, 0],
        coat: [0.3, 0.06, 0, 0],
        flags: [0, 0, 0, 0],
        cut: new Float32Array(4),
        bandData: new Float32Array(64),
        doubleSided: false,
        noInk: true,
        transparent: item.alpha < 0.999,
        depth: Math.hypot(model[12] - eye[0], model[13] - eye[1], model[14] - eye[2]),
        display: null,
      };
    }

    // A cut plane is a world-space normal through a point: `cut.at` if given, otherwise the
    // origin of the part's top-level assembly, so every shell of one machine shares the cut.
    function cutPlane(cut, part) {
      if (!cut) return new Float32Array(4);
      let normal = [0, 0, 1], offset = 0, at = null;
      if (Array.isArray(cut) && cut.length >= 3) { normal = vec3(cut, normal); offset = num(cut[3], 0); }
      else if (typeof cut === 'string') normal = axisOf(cut);
      else if (typeof cut === 'object') { normal = vec3(cut.normal || cut.axis, normal); offset = num(cut.offset, 0); at = vec3(cut.at, null); }
      normal = norm(normal);
      const root = part && part.root ? part.root.world : null;
      const origin = at || (root ? [root[12], root[13], root[14]] : [0, 0, 0]);
      if (state.frame && typeof state.frame.cut === 'number') offset += (1 - clamp(state.frame.cut, 0, 1)) * state.extent * 0.85;
      return new Float32Array([normal[0], normal[1], normal[2], dot(normal, origin) + offset]);
    }

    function bandData(spec) {
      let colours = null, count = 0;
      if (Array.isArray(spec.bands)) { colours = spec.bands; count = colours.length; }
      else if (spec.bands !== undefined) {
        count = Math.round(num(spec.bands, 0));
        colours = Array.isArray(spec.bandColors) ? spec.bandColors : Array.isArray(spec.bandColours) ? spec.bandColours : null;
      }
      if (spec.bandColors || spec.bandColours) {
        colours = spec.bandColors || spec.bandColours;
        if (!count) count = colours.length;
      }
      if (!count) return { count: 0, data: new Float32Array(64) };
      if (!colours) colours = ['#FFFFFF', '#EDE8DE'];
      count = clamp(count, 0, 16);
      const data = new Float32Array(64);
      for (let i = 0; i < count; i++) {
        const c = linearOf(resolveColour(colours[i % colours.length], '#FFFFFF'));
        data[i * 4] = c[0]; data[i * 4 + 1] = c[1]; data[i * 4 + 2] = c[2]; data[i * 4 + 3] = 1;
      }
      return { count, data };
    }

    function drawLabels(scene) {
      for (const item of state.labels) { item.node.remove(); item.path.remove(); item.halo.remove(); item.dot.remove(); }
      state.labels = [];
      const colours = theme();
      const labels = Array.isArray(scene.labels) ? scene.labels.filter(l => l && l.text) : [];
      const numbered = !!scene.numbered;
      labels.forEach((spec, index) => {
        const key = spec.part === undefined ? '' : String(spec.part);
        const part = key && state.lastParts ? state.lastParts.find(p => p.id === key) || state.lastParts.find(p => p.base === key) : null;
        const local = vec3(spec.anchor, [0, 0, 0]);
        const fixed = !part && Array.isArray(spec.at) ? vec3(spec.at, [0, 0, 0]) : null;
        if (!part && !fixed) return;
        const tone = toneOf(spec.tone);
        const node = document.createElement('div');
        const number = spec.n !== undefined ? String(spec.n) : numbered ? String(index + 1) : '';
        node.style.cssText = 'position:absolute;left:0;top:0;transform:translate3d(-1000px,-1000px,0);display:flex;align-items:center;gap:8px;'
          + 'font:500 13.5px/1.25 var(--sans,"Geist",ui-sans-serif,system-ui,sans-serif);letter-spacing:-.005em;color:var(--foreground,#15161E);white-space:nowrap;'
          + 'background:var(--card,#FFFFFF);border:1px solid var(--border-strong,var(--border,#CFCCC2));border-radius:8px;'
          + 'padding:' + (number ? '5px 11px 5px 6px' : '5px 11px') + ';box-shadow:0 1px 2px rgba(21,22,30,.06),0 6px 16px -8px rgba(21,22,30,.18);'
          + 'transition:opacity .25s ease,border-color .25s ease';
        if (number) {
          const badge = document.createElement('span');
          badge.textContent = number;
          badge.style.cssText = 'display:inline-grid;place-items:center;min-width:20px;height:20px;padding:0 5px;border-radius:999px;'
            + 'font:600 11.5px/1 var(--sans,"Geist",ui-sans-serif,sans-serif);font-variant-numeric:tabular-nums;background:' + tone.fill + ';color:' + tone.text;
          node.appendChild(badge);
        }
        const body = document.createElement('span');
        body.style.cssText = 'display:grid;gap:1px';
        const title = document.createElement('span');
        title.textContent = String(spec.text);
        body.appendChild(title);
        if (spec.note) {
          const note = document.createElement('span');
          note.textContent = String(spec.note);
          note.style.cssText = 'font-weight:400;font-size:12px;color:var(--muted-foreground,#5D5C57);white-space:normal;max-width:220px';
          body.appendChild(note);
        }
        node.appendChild(body);
        // With an onLabel handler (a film's part explorer) each callout is a button that opens
        // the part's detail.
        if (typeof options.onLabel === 'function') {
          node.setAttribute('role', 'button');
          node.tabIndex = 0;
          node.setAttribute('aria-label', String(spec.text) + (spec.note ? ', ' + String(spec.note) : '') + '. Show details');
          node.style.cursor = 'pointer';
          node.style.pointerEvents = 'auto';
          const open = event => { event.preventDefault(); event.stopPropagation(); options.onLabel(spec); };
          node.addEventListener('click', open);
          node.addEventListener('pointerdown', event => event.stopPropagation());
          node.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') open(event); });
          node.addEventListener('pointerenter', () => { node.style.borderColor = 'var(--primary,#2340E8)'; });
          node.addEventListener('pointerleave', () => { node.style.borderColor = 'var(--border-strong,var(--border,#CFCCC2))'; });
        }
        layer.appendChild(node);
        const width = node.offsetWidth, height = node.offsetHeight;
        const path = document.createElementNS(NS, 'path');
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke', 'var(--foreground,#15161E)');
        path.setAttribute('stroke-opacity', '0.62');
        path.setAttribute('stroke-width', '1.25');
        path.setAttribute('stroke-linejoin', 'round');
        leaders.appendChild(path);
        // A hairline halo in the card colour keeps the leader legible where it crosses the model.
        const halo = path.cloneNode();
        halo.setAttribute('stroke', 'var(--card,#FFFFFF)');
        halo.setAttribute('stroke-opacity', '0.85');
        halo.setAttribute('stroke-width', '3.25');
        leaders.insertBefore(halo, path);
        const dot = document.createElementNS(NS, 'circle');
        dot.setAttribute('r', '4');
        dot.setAttribute('fill', 'var(--card,#FFFFFF)');
        dot.setAttribute('stroke', tone.fill === 'var(--muted,#EEECE5)' ? 'var(--muted-foreground,#5D5C57)' : tone.fill);
        dot.setAttribute('stroke-width', '2');
        leaders.appendChild(dot);
        const auto = spec.dx === undefined && spec.dy === undefined;
        state.labels.push({ spec, node, path, halo, dot, part, local, fixed, auto, dx: num(spec.dx, 0), dy: num(spec.dy, 0), width, height });
      });
    }

    // The selected callout (a film's open part card) wears the primary colour.
    function positionSelected() {
      const selected = state.frame && state.frame.selected;
      for (const item of state.labels) {
        const on = selected !== undefined && selected !== null && String(item.spec.id) === String(selected);
        item.node.style.boxShadow = on ? '0 0 0 2px var(--primary,#2340E8),0 6px 16px -8px rgba(21,22,30,.18)' : '0 1px 2px rgba(21,22,30,.06),0 6px 16px -8px rgba(21,22,30,.18)';
        if (item.node.tabIndex === 0) item.node.setAttribute('aria-pressed', on ? 'true' : 'false');
      }
    }

    // A film fades callouts in on their chapter; a plain scene shows them all.
    function labelVisibility(item) {
      if (!state.frame || !state.frame.labels) return 1;
      return clamp(num(state.frame.labels(item.spec), 0), 0, 1);
    }

    // Does this part belong to `key`: its id, its base id, or any ancestor's?
    function belongs(part, key) {
      for (let p = part, depth = 0; p && depth < 24; p = p.parentPart, depth++) if (p.id === key || p.base === key) return true;
      return false;
    }

    // Pills go in columns beside the model's silhouette (or rows above and below it when the
    // stage is too narrow), keep their anchor's vertical order, and never overlap each other.
    function positionLabels(camera, width, height, screen) {
      const margin = 26, edge = 8;
      const items = [];
      for (const item of state.labels) {
        const anchor = item.part ? apply(item.part.model, item.local) : item.fixed;
        const p = anchor ? project(camera.eye, camera.target, camera.fov, width / height, anchor) : null;
        const shown = labelVisibility(item);
        const hidden = !p || shown <= 0.02;
        item.node.style.opacity = String(shown);
        item.path.style.opacity = item.halo.style.opacity = item.dot.style.opacity = String(shown);
        item.node.style.display = hidden ? 'none' : 'flex';
        if (item.node.tabIndex === 0) item.node.style.pointerEvents = shown > 0.5 ? 'auto' : 'none';
        item.path.style.display = hidden ? 'none' : '';
        item.halo.style.display = hidden ? 'none' : '';
        item.side = null;
        item.dot.style.display = hidden ? 'none' : '';
        if (hidden) continue;
        item.ax = p.x * width; item.ay = p.y * height;
        items.push(item);
      }
      const box = screen || { minX: width * 0.3, maxX: width * 0.7, minY: height * 0.3, maxY: height * 0.7, cx: width / 2, cy: height / 2 };
      const widest = items.reduce((w, item) => Math.max(w, item.width), 0);
      const columns = box.minX - margin - widest >= edge || width - box.maxX - margin - widest >= edge;
      const groups = { left: [], right: [], top: [], bottom: [], free: [] };
      for (const item of items) {
        if (!item.auto) { item.x = item.ax + item.dx; item.y = item.ay + item.dy; groups.free.push(item); continue; }
        if (columns) {
          const side = item.ax < box.cx ? 'left' : 'right';
          const room = side === 'left' ? box.minX - margin - item.width >= edge : width - box.maxX - margin - item.width >= edge;
          if (room) {
            item.x = side === 'left' ? box.minX - margin - item.width / 2 : box.maxX + margin + item.width / 2;
            item.y = item.ay;
            item.side = side === 'left' ? 'right' : 'left';
            groups[side].push(item);
          } else {
            const row = item.ay < box.cy ? 'top' : 'bottom';
            item.x = item.ax;
            item.y = row === 'top' ? box.minY - margin - item.height / 2 : box.maxY + margin + item.height / 2;
            groups[row].push(item);
          }
        } else {
          const side = item.ay < box.cy ? 'top' : 'bottom';
          item.x = item.ax;
          item.y = side === 'top' ? box.minY - margin - item.height / 2 : box.maxY + margin + item.height / 2;
          groups[side].push(item);
        }
      }
      const minY = item => item.height / 2 + edge, maxY = item => height - item.height / 2 - edge;
      const minX = item => item.width / 2 + edge, maxX = item => width - item.width / 2 - edge;
      // One-dimensional packing: sort, push forward to clear the previous pill, then pull back
      // from the far edge if the stack overflowed.
      const pack = (list, axis) => {
        const lo = axis === 'y' ? minY : minX, hi = axis === 'y' ? maxY : maxX, size = axis === 'y' ? 'height' : 'width', gap = axis === 'y' ? 8 : 12;
        list.sort((a, b) => a[axis] - b[axis]);
        for (let i = 0; i < list.length; i++) {
          list[i][axis] = clamp(list[i][axis], lo(list[i]), hi(list[i]));
          if (i) list[i][axis] = Math.max(list[i][axis], list[i - 1][axis] + (list[i - 1][size] + list[i][size]) / 2 + gap);
        }
        for (let i = list.length - 1; i >= 0; i--) {
          list[i][axis] = Math.min(list[i][axis], hi(list[i]));
          if (i < list.length - 1) list[i][axis] = Math.min(list[i][axis], list[i + 1][axis] - (list[i + 1][size] + list[i][size]) / 2 - gap);
        }
      };
      pack(groups.left, 'y'); pack(groups.right, 'y'); pack(groups.top, 'x'); pack(groups.bottom, 'x');
      // A model that fills the stage leaves no row outside it: keep the row inside the stage.
      for (const item of groups.top.concat(groups.bottom)) item.y = clamp(item.y, minY(item), maxY(item));
      for (const item of groups.free) { item.x = clamp(item.x, minX(item), maxX(item)); item.y = clamp(item.y, minY(item), maxY(item)); }
      for (const item of items) {
        const left = item.x - item.width / 2, top = item.y - item.height / 2;
        item.node.style.transform = 'translate3d(' + left.toFixed(1) + 'px,' + top.toFixed(1) + 'px,0)';
        // Leaders are drafting-style: a run from the anchor to a short shoulder, then square into
        // the side of the tag that faces the anchor.
        const fromSide = item.side || (Math.abs(item.ax - item.x) / item.width > Math.abs(item.ay - item.y) / item.height
          ? (item.ax < item.x ? 'left' : 'right') : (item.ay < item.y ? 'top' : 'bottom'));
        let ex, ey, kx, ky;
        if (fromSide === 'left' || fromSide === 'right') {
          ex = fromSide === 'left' ? left : left + item.width; ey = item.y;
          kx = ex + (fromSide === 'left' ? -14 : 14); ky = ey;
        } else {
          ex = item.x; ey = fromSide === 'top' ? top : top + item.height;
          kx = ex; ky = ey + (fromSide === 'top' ? -12 : 12);
        }
        const straight = Math.abs(item.ax - kx) + Math.abs(item.ay - ky) < 6;
        item.path.setAttribute('d', 'M' + item.ax.toFixed(1) + ' ' + item.ay.toFixed(1)
          + (straight ? '' : 'L' + kx.toFixed(1) + ' ' + ky.toFixed(1)) + 'L' + ex.toFixed(1) + ' ' + ey.toFixed(1));
        item.halo.setAttribute('d', item.path.getAttribute('d'));
        item.dot.setAttribute('cx', item.ax.toFixed(1));
        item.dot.setAttribute('cy', item.ay.toFixed(1));
      }
    }

    function render(now) {
      if (!renderer || !state.width) return;
      const scene = state.scene || {};
      const parts = state.lastParts;
      if (!parts) return;
      const width = state.width, height = state.height, aspect = width / height;
      const frame = state.frame;
      // A film directs the camera; the reader's own orbit and zoom still apply on top.
      const cameraSpec = frame && frame.camera ? frame.camera : scene.camera || {};
      const yawBase = num(cameraSpec.yaw, -20) * DEG;
      const spin = state.reduced || frame ? 0 : num(cameraSpec.spin, 0.3);
      const dt = lastRender ? Math.min(0.05, Math.max(0, (now - lastRender) / 1000)) : 0;
      lastRender = now;
      if (!state.reduced) {
        if (drag.id === null && fling) {
          view.yaw += fling * dt;
          fling *= Math.exp(-4.2 * dt);
          if (Math.abs(fling) < 0.02) fling = 0;
        }
        if (drag.id === null && now >= spinResumeAt) spinAngle += spin * dt;
      }
      const yaw = yawBase + spinAngle + view.yaw;
      const tilt = clamp(num(cameraSpec.tilt, 15) * DEG + view.tilt, MIN_TILT, MAX_TILT);
      const fov = clamp(num(cameraSpec.fov, 35), 18, 60);

      // Bounds and framing come from the settled targets, so a step change does not make the
      // camera lurch while a part eases into place.
      const samples = [];
      const owners = [];
      let min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
      computeWorld(parts, now);
      for (const part of parts) {
        if (part.group) continue;
        if (frame && frame.opacity && frame.opacity(part) <= 0.02) continue;
        const model = part.model;
        const geometry = geometryOf(part.spec.kind, part.spec.recipe);
        const stride = Math.max(1, Math.floor(geometry.samples.length / 600));
        for (let i = 0; i < geometry.samples.length; i += 3 * stride) {
          const p = apply(model, [geometry.samples[i], geometry.samples[i + 1], geometry.samples[i + 2]]);
          for (let k = 0; k < 3; k++) { if (p[k] < min[k]) min[k] = p[k]; if (p[k] > max[k]) max[k] = p[k]; }
          samples.push(p);
          owners.push(part);
        }
      }
      if (!samples.length) { min = [-0.5, 0, -0.5]; max = [0.5, 1, 0.5]; }
      const fittedCenter = [(min[0] + max[0]) / 2, (min[1] + max[1]) / 2, (min[2] + max[2]) / 2];
      const extent = Math.max(0.2, Math.max(max[0] - min[0], max[1] - min[1], max[2] - min[2]) / 2);
      state.extent = extent;
      // With callouts, the model keeps to the middle of the stage so the columns have room.
      const labelled = frame ? state.labels.some(item => labelVisibility(item) > 0.02) : Array.isArray(scene.labels) && scene.labels.length > 0;
      const fitAspect = labelled ? aspect * 0.68 : aspect;
      // A target is a point, or a part id: the camera then centres and frames that part (with its
      // children). A film blends the framing of the previous and the next chapter's target.
      const framing = target => {
        let points = samples;
        if (typeof target === 'string' && target) {
          const picked = samples.filter((_, i) => belongs(owners[i], target));
          if (picked.length) points = picked;
        }
        let lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
        for (const p of points) for (let k = 0; k < 3; k++) { if (p[k] < lo[k]) lo[k] = p[k]; if (p[k] > hi[k]) hi[k] = p[k]; }
        const c = points === samples ? fittedCenter : [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2];
        const centre = Array.isArray(target) ? vec3(target, c) : c;
        // A part target keeps some of its surroundings in frame, so the close-up still has context.
        const context = points === samples ? 1 : 2;
        return { centre, distance: fitDistance(points.length ? points : [[0, 0, 0]], centre, yawBase + view.yaw, tilt, fov, fitAspect) * (labelled ? 1.06 : 1) * context };
      };
      let center, fitted;
      if (frame && frame.camera) {
        const a = framing(frame.camera.from), b = framing(frame.camera.to), e = clamp(num(frame.camera.e, 1), 0, 1);
        center = lerp3(a.centre, b.centre, e);
        fitted = a.distance + (b.distance - a.distance) * e;
      } else {
        const f = framing(cameraSpec.target);
        center = f.centre; fitted = f.distance;
      }
      state.lastSamples = samples; state.lastOwners = owners;
      const targetDistance = fitted * clamp(num(cameraSpec.distance, 1.1), 0.25, 3) * view.zoom;
      state.wantedDistance = targetDistance;
      if (!state.distance) state.distance = targetDistance;
      state.distance += (targetDistance - state.distance) * (state.reduced || frame ? 1 : 0.18);
      const distance = state.distance;
      const eye = [center[0] + Math.sin(yaw) * Math.cos(tilt) * distance, center[1] + Math.sin(tilt) * distance, center[2] + Math.cos(yaw) * Math.cos(tilt) * distance];
      const camera = { eye, target: center, fov, distance, yaw, tilt };

      const objects = buildObjects(parts, now, eye);
      state.lastObjects = objects;
      const colours = theme();
      const ink = rgbOf(colours.ink) || [0.08, 0.09, 0.11];
      state.groundY = typeof scene.ground === 'number' ? scene.ground : min[1] - extent * 0.012;
      renderer.render({
        objects,
        center,
        extent,
        groundY: state.groundY,
        ground: scene.ground !== false,
        paper: rgbOf(colours.paper) || [0.98, 0.96, 0.92],
        ink: {
          width: num(scene.ink && scene.ink.width, 1.8),
          seamWidth: num(scene.ink && scene.ink.seamWidth, 1.1),
          strength: num(scene.ink && scene.ink.strength, 0.85),
          shade: num(scene.ink && scene.ink.shade, 0.6),
          color: rgbOf(scene.ink && scene.ink.color) || ink,
          a: 1,
        },
        camera,
        debug: num(scene.debug, 0),
      });
      // The model's screen footprint, so callouts can sit just outside it.
      let screen = null;
      if (state.labels.length) {
        screen = { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity };
        // Under a film's focus, callouts clear the focused parts and may cross the ghosted rest.
        const solid = frame && frame.opacity ? samples.filter((_, i) => frame.opacity(owners[i]) > 0.5) : samples;
        const footprint = solid.length ? solid : samples;
        const step = Math.max(1, Math.floor(footprint.length / 400));
        for (let i = 0; i < footprint.length; i += step) {
          const q = project(eye, center, fov, aspect, footprint[i]);
          if (!q) continue;
          screen.minX = Math.min(screen.minX, q.x * width); screen.maxX = Math.max(screen.maxX, q.x * width);
          screen.minY = Math.min(screen.minY, q.y * height); screen.maxY = Math.max(screen.maxY, q.y * height);
        }
        if (!isFinite(screen.minX)) screen = null;
        else { screen.cx = (screen.minX + screen.maxX) / 2; screen.cy = (screen.minY + screen.maxY) / 2; }
      }
      positionLabels(camera, width, height, screen);
      wrap.style.background = colours.paper;
    }

    function needsAnimation(now) {
      if (state.reduced) return false;
      if (fling) return true;
      if (num((state.scene.camera || {}).spin, 0.3) !== 0) return true;
      if (state.wantedDistance && Math.abs(state.wantedDistance - state.distance) > 0.002) return true;
      return (state.lastParts || []).some(part => part.spec.pulse || part.track.from || now - part.track.born < 540);
    }

    function tick(now) {
      state.raf = 0;
      render(now);
      if (needsAnimation(now)) state.raf = requestAnimationFrame(tick);
    }

    function schedule() {
      if (!state.raf && !state.reduced) state.raf = requestAnimationFrame(tick);
    }

    function draw(scene) {
      state.scene = scene && typeof scene === 'object' ? scene : { parts: [] };
      state.lastParts = sceneParts(state.scene);
      drawLabels(state.scene);
      render(performance.now());
      schedule();
    }

    // The host repaints the document's tokens in place when the dashboard theme flips.
    const themeObserver = typeof MutationObserver === 'function' ? new MutationObserver(() => {
      state.reduced = !!(document.documentElement.dataset.reducedMotion === 'true'
        || (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches));
      if (!state.scene) return;
      draw(state.scene);
    }) : null;
    if (themeObserver) themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['style', 'data-theme', 'data-reduced-motion'] });

    function audit(root) {
      const problems = [];
      const stage = (root || wrap).querySelector ? (root || wrap).querySelector('.clicky3d') || wrap : wrap;
      const box = stage.getBoundingClientRect();
      const items = state.labels.map(item => ({ text: item.spec.text, r: item.node.getBoundingClientRect() })).filter(item => item.r.width > 0);
      items.forEach(item => {
        if (item.r.left < box.left - 1 || item.r.right > box.right + 1 || item.r.top < box.top - 1 || item.r.bottom > box.bottom + 1) problems.push('"' + String(item.text).slice(0, 30) + '" runs outside the 3D stage');
      });
      for (let a = 0; a < items.length; a++) for (let b = a + 1; b < items.length; b++) {
        const p = items[a].r, q = items[b].r;
        const ix = Math.min(p.right, q.right) - Math.max(p.left, q.left);
        const iy = Math.min(p.bottom, q.bottom) - Math.max(p.top, q.top);
        if (ix > 1 && iy > 1 && ix * iy > 0.12 * Math.min(p.width * p.height, q.width * q.height)) problems.push('"' + String(items[a].text).slice(0, 30) + '" overlaps "' + String(items[b].text).slice(0, 30) + '"');
      }
      problems.push(...floating());
      return problems.slice(0, 5);
    }

    // An assembled object is one connected piece: every visible part touches (or sits inside) the
    // rest. Parts drifting in space read as a broken model. Exploded views and posed parts are
    // meant to separate, so they are not checked.
    function floating() {
      const frame = state.frame;
      if (frame && (frame.explode || 0) > 0.02) return [];
      const samples = state.lastSamples || [], owners = state.lastOwners || [];
      const boxes = new Map();
      samples.forEach((p, i) => {
        const part = owners[i];
        if (frame && frame.pose && frame.pose(part)) return;
        let box = boxes.get(part);
        if (!box) boxes.set(part, box = { part, lo: p.slice(), hi: p.slice() });
        for (let k = 0; k < 3; k++) { box.lo[k] = Math.min(box.lo[k], p[k]); box.hi[k] = Math.max(box.hi[k], p[k]); }
      });
      const list = [...boxes.values()];
      if (list.length < 2) return [];
      const gap = Math.max(0.01, (state.extent || 1) * 0.04);
      const root = list.map((_, i) => i);
      const find = i => (root[i] === i ? i : (root[i] = find(root[i])));
      for (let a = 0; a < list.length; a++) for (let b = a + 1; b < list.length; b++) {
        const A = list[a], B = list[b];
        if ([0, 1, 2].every(k => A.lo[k] - gap <= B.hi[k] && B.lo[k] - gap <= A.hi[k])) root[find(a)] = find(b);
      }
      const sizes = new Map();
      const volume = box => Math.max(1e-6, (box.hi[0] - box.lo[0]) * (box.hi[1] - box.lo[1]) * (box.hi[2] - box.lo[2]));
      list.forEach((box, i) => sizes.set(find(i), (sizes.get(find(i)) || 0) + volume(box)));
      const main = [...sizes.entries()].sort((x, y) => y[1] - x[1])[0][0];
      const loose = list.filter((_, i) => find(i) !== main);
      if (!loose.length) return [];
      // Boxes in the assembly's own coordinates (the root group's position taken off), so the
      // numbers match the `at` values the author wrote.
      const rootOf = part => { let p = part; while (p.parentPart) p = p.parentPart; return p.world ? [p.world[12], p.world[13], p.world[14]] : [0, 0, 0]; };
      const origin = rootOf(loose[0].part);
      const fmt = box => '[' + [0, 1, 2].map(k => (box.lo[k] - origin[k]).toFixed(2) + '..' + (box.hi[k] - origin[k]).toFixed(2)).join(', ') + ']';
      const separation = (A, B) => [0, 1, 2].map(k => Math.max(A.lo[k] - B.hi[k], B.lo[k] - A.hi[k], 0));
      const body = list.filter((_, i) => find(i) === main);
      const seen = new Set(), notes = [];
      for (const box of loose) {
        if (seen.has(box.part.base) || notes.length >= 3) continue;
        seen.add(box.part.base);
        let best = null, bestGap = Infinity;
        for (const other of body) { const g = separation(box, other); const d = Math.hypot(g[0], g[1], g[2]); if (d < bestGap) { bestGap = d; best = { other, g }; } }
        const axis = best.g.indexOf(Math.max(...best.g));
        notes.push(box.part.base + ' ' + fmt(box) + ' is ' + best.g[axis].toFixed(2) + ' away along ' + 'xyz'[axis] + ' from ' + best.other.part.base + ' ' + fmt(best.other));
      }
      const others = [...new Set(loose.map(box => box.part.base))].filter(name => !seen.has(name));
      return ['Parts float apart from the model (boxes are x,y,z ranges in assembly coordinates): ' + notes.join('; ')
        + (others.length ? '; also loose: ' + others.slice(0, 6).join(', ') : '') + '. Move them by their `at` so they touch or sit inside their neighbours, where they really are'];
    }

    const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(() => resize()) : null;
    if (observer) observer.observe(wrap);
    addEventListener('resize', resize);
    resize();

    const board = {
      canvas,
      element: wrap,
      draw,
      resize,
      audit,
      belongs,
      // A film's frame for this instant (poses, motions, camera, callouts), or null for a plain scene.
      frame(next) { state.frame = next || null; positionSelected(); render(performance.now()); },
      get parts() { return state.lastParts || []; },
      get reduced() { return state.reduced; },
      dispose() {
        const index = boards.indexOf(board);
        if (index >= 0) boards.splice(index, 1);
        if (state.raf) cancelAnimationFrame(state.raf);
        if (observer) observer.disconnect();
        if (themeObserver) themeObserver.disconnect();
        removeEventListener('resize', resize);
        for (const item of state.labels) { item.node.remove(); item.path.remove(); item.halo.remove(); item.dot.remove(); }
        if (renderer) renderer.dispose();
        wrap.remove();
      },
      get scene() { return state.scene; },
      get renderer() { return renderer; },
      get failure() { return failure; },
    };
    boards.push(board);
    return board;
  }

  // ------------------------------------------------------------------ film
  // A film is a declarative "how it works" movie: one assembly, continuous motions and flows, and
  // chapters that are keyframes. Each chapter states only what changes (camera, poses, callouts,
  // focus, explode, cut, motion speeds); everything else carries over from the chapter before.
  // Time is a pure function: scrubbing to any instant gives the same frame as playing to it.
  const GHOST = 0.13;
  const ease = t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  const list = value => (Array.isArray(value) ? value.map(String) : typeof value === 'string' ? [value] : null);
  const clock = seconds => Math.floor(seconds / 60) + ':' + String(Math.floor(seconds % 60)).padStart(2, '0');

  function film(host, data, options) {
    host = typeof host === 'string' ? document.querySelector(host) : host;
    if (!host) throw new Error('Clicky3D.film: host element not found');
    data = data && typeof data === 'object' ? data : {};
    options = options || {};
    const labels = (Array.isArray(data.labels) ? data.labels : []).filter(l => l && l.text).map(l => Object.assign({}, l, { id: String(l.id || l.part || l.text) }));
    const motions = (Array.isArray(data.motions) ? data.motions : []).filter(m => m && m.part).map((m, i) => Object.assign({}, m, { id: String(m.id || m.part + '-' + (m.type || 'spin') + i) }));
    const flows = (Array.isArray(data.flows) ? data.flows : []).filter(f => f && Array.isArray(f.path) && f.path.length >= 2).map((f, i) => Object.assign({}, f, { id: String(f.id || 'flow' + i) }));
    const runners = motions.map(m => m.id).concat(flows.map(f => f.id));
    const hasCut = (data.parts || []).some(part => part && part.cut);

    // ---- keyframe states
    const base = data.camera || {};
    let previous = {
      camera: { yaw: num(base.yaw, -28), tilt: num(base.tilt, 16), distance: num(base.distance, 1), fov: num(base.fov, 35), target: base.target || null, orbit: num(base.orbit, 0) },
      show: labels.map(l => l.id), focus: [], hide: [], explode: 0, cut: hasCut ? 1 : 0,
      run: Object.fromEntries(runners.map(id => [id, 1])), pose: {},
    };
    const chapters = (Array.isArray(data.chapters) && data.chapters.length ? data.chapters : [{ title: data.title || 'Overview', say: data.summary || '' }]).slice(0, 16).map(chapter => {
      chapter = chapter && typeof chapter === 'object' ? chapter : {};
      const cam = chapter.camera && typeof chapter.camera === 'object' ? chapter.camera : {};
      const run = Object.assign({}, previous.run);
      if (chapter.run && typeof chapter.run === 'object') for (const key in chapter.run) run[key] = num(chapter.run[key], run[key] || 0);
      const pose = Object.assign({}, previous.pose);
      if (chapter.pose && typeof chapter.pose === 'object') for (const key in chapter.pose) pose[key] = Object.assign({}, pose[key], chapter.pose[key]);
      const state = {
        camera: {
          yaw: num(cam.yaw, previous.camera.yaw), tilt: num(cam.tilt, previous.camera.tilt),
          distance: num(cam.distance, previous.camera.distance), fov: num(cam.fov, previous.camera.fov),
          target: cam.target !== undefined ? cam.target : previous.camera.target, orbit: num(cam.orbit, 0),
        },
        show: list(chapter.show) || previous.show,
        focus: list(chapter.focus) || previous.focus,
        hide: list(chapter.hide) || previous.hide,
        explode: clamp(num(chapter.explode, previous.explode), 0, 2),
        cut: clamp(num(typeof chapter.cut === 'boolean' ? +chapter.cut : chapter.cut, previous.cut), 0, 1),
        run, pose,
      };
      const seconds = clamp(num(chapter.seconds, 6), 2, 30);
      const item = { title: String(chapter.title || ''), say: String(chapter.say || ''), seconds, blend: clamp(num(chapter.blend, Math.min(1.6, seconds * 0.35)), 0, seconds), from: previous, to: state };
      previous = state;
      return item;
    });
    chapters[0].from = chapters[0].to;
    let total = 0;
    for (const chapter of chapters) { chapter.start = total; total += chapter.seconds; }
    // Each runner's phase at each chapter start: the integral of its speed so far.
    const runEnd = (chapter, id, u) => {
      const a = num(chapter.from.run[id], 0), b = num(chapter.to.run[id], 0), T = chapter.blend;
      if (u <= 0) return 0;
      if (T > 0 && u < T) return a * u + (b - a) * u * u / (2 * T);
      return (T > 0 ? a * T + (b - a) * T / 2 : 0) + b * (u - T);
    };
    const phaseStart = chapters.map(() => ({}));
    for (const id of runners) {
      let sum = 0;
      chapters.forEach((chapter, k) => { phaseStart[k][id] = sum; sum += runEnd(chapter, id, chapter.seconds); });
    }

    // ---- DOM: stage, caption, transport, chapter list
    const root = document.createElement('div');
    root.className = 'clicky3d-film';
    root.style.cssText = 'display:grid;gap:12px;font-family:var(--sans,"Geist",ui-sans-serif,system-ui,sans-serif);color:var(--foreground,#15161E)';
    const stage = document.createElement('div');
    stage.style.cssText = 'height:clamp(340px,62vw,580px)';
    const caption = document.createElement('div');
    caption.setAttribute('aria-live', 'polite');
    caption.style.cssText = 'display:flex;gap:12px;align-items:flex-start;min-height:3.4em;padding:2px 2px 0';
    const badge = document.createElement('span');
    badge.style.cssText = 'flex:none;display:inline-grid;place-items:center;min-width:24px;height:24px;margin-top:1px;padding:0 6px;border-radius:999px;'
      + 'background:var(--primary,#2340E8);color:var(--primary-foreground,#FFFFFF);font:600 12.5px/1 var(--sans,"Geist",sans-serif);font-variant-numeric:tabular-nums';
    const words = document.createElement('div');
    const heading = document.createElement('strong');
    heading.style.cssText = 'display:block;font-size:16px;font-weight:600;letter-spacing:-.01em;line-height:1.35';
    const line = document.createElement('p');
    line.style.cssText = 'margin:2px 0 0;font-size:15px;line-height:1.5;color:var(--muted-foreground,#5D5C57)';
    words.style.cssText = 'flex:1;min-width:0';
    words.append(heading, line);
    const close = document.createElement('button');
    close.type = 'button';
    close.textContent = 'Back to the film';
    close.style.cssText = 'flex:none;display:none;align-items:center;min-height:36px;padding:0 14px;border-radius:999px;border:1px solid var(--border,#E4E2DA);background:var(--card,#FFFFFF);'
      + 'color:var(--foreground,#15161E);font:500 13.5px/1 var(--sans,"Geist",sans-serif);cursor:pointer;white-space:nowrap';
    caption.append(badge, words, close);

    const bar = document.createElement('div');
    bar.style.cssText = 'display:flex;align-items:center;gap:12px';
    const play = document.createElement('button');
    play.type = 'button';
    play.style.cssText = 'flex:none;display:inline-grid;place-items:center;width:44px;height:44px;min-height:44px;padding:0;border:0;border-radius:999px;'
      + 'background:var(--primary,#2340E8);color:var(--primary-foreground,#FFFFFF);cursor:pointer';
    const icon = document.createElementNS(NS, 'svg');
    icon.setAttribute('viewBox', '0 0 24 24'); icon.setAttribute('width', '18'); icon.setAttribute('height', '18'); icon.setAttribute('aria-hidden', 'true');
    const glyph = document.createElementNS(NS, 'path');
    glyph.setAttribute('fill', 'currentColor');
    icon.appendChild(glyph);
    play.appendChild(icon);
    const track = document.createElement('div');
    track.style.cssText = 'position:relative;flex:1;min-width:0;display:flex;align-items:center';
    const scrub = document.createElement('input');
    scrub.type = 'range'; scrub.min = '0'; scrub.max = String(Math.round(total * 100)); scrub.step = '1'; scrub.value = '0';
    scrub.setAttribute('aria-label', 'Film position');
    scrub.style.cssText = 'width:100%;min-height:44px;margin:0;accent-color:var(--primary,#2340E8);cursor:pointer';
    const ticks = document.createElement('div');
    ticks.setAttribute('aria-hidden', 'true');
    ticks.style.cssText = 'position:absolute;left:8px;right:8px;top:50%;height:0;pointer-events:none';
    chapters.slice(1).forEach(chapter => {
      const tick = document.createElement('span');
      tick.style.cssText = 'position:absolute;top:-7px;width:2px;height:14px;border-radius:2px;background:var(--card,#FFFFFF);box-shadow:0 0 0 1px var(--border-strong,#CFCCC2);left:' + (chapter.start / total * 100).toFixed(2) + '%';
      ticks.appendChild(tick);
    });
    track.append(scrub, ticks);
    const time = document.createElement('span');
    time.style.cssText = 'flex:none;font-size:13px;font-variant-numeric:tabular-nums;color:var(--muted-foreground,#5D5C57);min-width:78px;text-align:right';
    // One click takes the whole product apart (and puts it back together).
    const apartButton = document.createElement('button');
    apartButton.type = 'button';
    apartButton.setAttribute('aria-pressed', 'false');
    apartButton.style.cssText = 'flex:none;display:inline-flex;align-items:center;gap:8px;min-height:44px;padding:0 16px 0 13px;border-radius:999px;'
      + 'border:1px solid var(--border-strong,var(--border,#CFCCC2));background:var(--card,#FFFFFF);color:var(--foreground,#15161E);'
      + 'font:500 14px/1 var(--sans,"Geist",sans-serif);cursor:pointer;white-space:nowrap;transition:background .2s ease,color .2s ease,border-color .2s ease';
    const apartIcon = document.createElementNS(NS, 'svg');
    apartIcon.setAttribute('viewBox', '0 0 24 24'); apartIcon.setAttribute('width', '18'); apartIcon.setAttribute('height', '18'); apartIcon.setAttribute('aria-hidden', 'true');
    apartIcon.setAttribute('fill', 'none'); apartIcon.setAttribute('stroke', 'currentColor'); apartIcon.setAttribute('stroke-width', '1.8'); apartIcon.setAttribute('stroke-linecap', 'round'); apartIcon.setAttribute('stroke-linejoin', 'round');
    const apartGlyph = document.createElementNS(NS, 'path');
    apartIcon.appendChild(apartGlyph);
    const apartText = document.createElement('span');
    apartButton.append(apartIcon, apartText);
    bar.append(play, apartButton, track, time);

    const index = document.createElement('div');
    index.setAttribute('role', 'group');
    index.setAttribute('aria-label', 'Chapters');
    index.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px';
    const chips = chapters.map((chapter, k) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.textContent = (k + 1) + '  ' + chapter.title;
      chip.setAttribute('aria-label', 'Chapter ' + (k + 1) + ': ' + chapter.title);
      chip.style.cssText = 'min-height:36px;padding:0 14px;border-radius:999px;border:1px solid var(--border,#E4E2DA);background:var(--card,#FFFFFF);'
        + 'color:var(--muted-foreground,#5D5C57);font:500 13.5px/1 var(--sans,"Geist",sans-serif);cursor:pointer;white-space:nowrap';
      chip.addEventListener('click', () => api.step(k));
      index.appendChild(chip);
      return chip;
    });
    root.append(stage, caption, bar, index);
    host.appendChild(root);

    const board = mount(stage, { desc: options.desc || data.desc || data.title || '3D film', fill: true, onLabel: spec => api.inspect(spec.id) });
    board.draw({ parts: data.parts || [], labels, ground: data.ground, ink: data.ink, numbered: data.numbered !== false, camera: { spin: 0 } });

    // ---- evaluation
    let t = 0, playing = false, raf = 0, last = 0, shownChapter = -1, shownMode = 'film', rate = 1;
    const chapterAt = at => { let k = 0; while (k < chapters.length - 1 && at >= chapters[k + 1].start - 1e-6) k++; return k; };
    const memberOf = (part, keys) => keys.some(key => board.belongs(part, key));
    const opacityIn = (state, part) => (memberOf(part, state.hide) ? 0 : state.focus.length && !memberOf(part, state.focus) ? GHOST : 1);
    const lerp = (a, b, e) => a + (b - a) * e;

    function frameAt(at) {
      const k = chapterAt(at), chapter = chapters[k];
      const u = at - chapter.start;
      const e = board.reduced || chapter.blend <= 0 ? 1 : ease(clamp(u / chapter.blend, 0, 1));
      const A = chapter.from, B = chapter.to;
      const previousChapter = chapters[k - 1];
      // The previous chapter's slow orbit has turned the camera by the time this one begins.
      const yawA = A.camera.yaw + (previousChapter && !board.reduced ? A.camera.orbit * previousChapter.seconds : 0);
      const orbit = board.reduced ? 0 : B.camera.orbit * u;
      const phase = id => (board.reduced ? 0 : num(phaseStart[k][id], 0) + runEnd(chapter, id, u));
      const speed = id => lerp(num(A.run[id], 0), num(B.run[id], 0), e);
      return {
        chapter: k,
        explode: lerp(A.explode, B.explode, e),
        cut: hasCut ? lerp(A.cut, B.cut, e) : undefined,
        camera: {
          yaw: lerp(yawA, B.camera.yaw, e) + orbit, tilt: lerp(A.camera.tilt, B.camera.tilt, e),
          distance: lerp(A.camera.distance, B.camera.distance, e), fov: lerp(A.camera.fov, B.camera.fov, e),
          from: A.camera.target, to: B.camera.target, e,
        },
        // Callouts switch over the middle of a blend, once the thing they point at is in view.
        labels: spec => smooth(clamp((lerp(A.show.includes(spec.id) ? 1 : 0, B.show.includes(spec.id) ? 1 : 0, e) - 0.35) / 0.4, 0, 1)),
        opacity: part => lerp(opacityIn(A, part), opacityIn(B, part), e),
        pose(part) {
          const pa = A.pose[part.id] || A.pose[part.base], pb = B.pose[part.id] || B.pose[part.base];
          if (!pa && !pb) return null;
          const rest = part.track.target;
          const pick = (pose, key, fallback, scale) => {
            if (!pose || pose[key] === undefined) return fallback;
            if (key === 'scale' && typeof pose.scale === 'number') return [pose.scale, pose.scale, pose.scale];
            const v = vec3(pose[key], null);
            return v ? v.map(n => n * scale) : fallback;
          };
          return {
            at: lerp3(pick(pa, 'at', rest.at, 1), pick(pb, 'at', rest.at, 1), e),
            rot: lerp3(pick(pa, 'rot', rest.rot, DEG), pick(pb, 'rot', rest.rot, DEG), e),
            scale: lerp3(pick(pa, 'scale', rest.scale, 1), pick(pb, 'scale', rest.scale, 1), e),
          };
        },
        motion(part) {
          let matrix = null;
          for (const m of motions) {
            if (m.part !== part.id && m.part !== part.base) continue;
            const axis = axisOf(m.axis || 'y'), pivot = vec3(m.pivot, [0, 0, 0]), c = phase(m.id);
            const period = Math.max(0.05, num(m.period, 1)), wave = Math.sin(TAU * (c / period + num(m.phase, 0)));
            let step;
            if (m.type === 'slide') { const d = num(m.amount, 0.2) * wave; step = trs([axis[0] * d, axis[1] * d, axis[2] * d], [0, 0, 0], [1, 1, 1]); }
            else if (m.type === 'swing') step = aroundMatrixOf(axis, num(m.angle, 20) * DEG * wave, pivot);
            else step = aroundMatrixOf(axis, num(m.speed, 0.5) * c * TAU, pivot);
            matrix = matrix ? mul(matrix, step) : step;
          }
          return matrix;
        },
        flows(parts) {
          const beads = [];
          for (const flow of flows) {
            const shown = clamp(speed(flow.id), 0, 1);
            if (shown <= 0.02) continue;
            const owner = flow.parent ? parts.find(p => p.id === String(flow.parent) || p.base === String(flow.parent)) : null;
            const points = flow.path.map(p => vec3(p, [0, 0, 0]));
            const lengths = [0];
            for (let i = 1; i < points.length; i++) lengths.push(lengths[i - 1] + Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1], points[i][2] - points[i - 1][2]));
            const length = lengths[lengths.length - 1] || 1;
            const count = clamp(Math.round(num(flow.count, 14)), 1, 80);
            const period = Math.max(0.2, num(flow.period, 2.5));
            const colours = Array.isArray(flow.colors) && flow.colors.length ? flow.colors : [flow.color || '#6C8CFF'];
            const r = clamp(num(flow.r, 0.025), 0.005, 0.3);
            const c = phase(flow.id) / period;
            for (let i = 0; i < count; i++) {
              const s = ((i / count + c) % 1 + 1) % 1;
              const d = s * length;
              let j = 1;
              while (j < lengths.length - 1 && lengths[j] < d) j++;
              const f = (d - lengths[j - 1]) / Math.max(1e-6, lengths[j] - lengths[j - 1]);
              let p = lerp3(points[j - 1], points[j], f);
              if (owner && owner.world) p = apply(owner.world, p);
              // Beads swell in at the start of the path and shrink out at the end.
              const size = r * Math.min(1, s * 8, (1 - s) * 8) * shown;
              if (size < 0.002) continue;
              const ci = s * (colours.length - 1), c0 = Math.floor(ci), c1 = Math.min(colours.length - 1, c0 + 1);
              const colour = mixColour(colours[c0], colours[c1], ci - c0);
              // A streak: a capsule stretched along the local direction of travel.
              let a = points[j - 1], b = points[j];
              if (owner && owner.world) { a = apply(owner.world, a); b = apply(owner.world, b); }
              const along = norm([b[0] - a[0], b[1] - a[1], b[2] - a[2]]);
              const side = norm(Math.abs(along[1]) < 0.9 ? cross(along, [0, 1, 0]) : cross(along, [1, 0, 0]));
              const up = cross(side, along);
              const stretch = clamp(num(flow.stretch, 2.4), 1, 6);
              const m = m4();
              m[0] = side[0] * size; m[1] = side[1] * size; m[2] = side[2] * size;
              m[4] = along[0] * size * stretch / 2; m[5] = along[1] * size * stretch / 2; m[6] = along[2] * size * stretch / 2;
              m[8] = up[0] * size; m[9] = up[1] * size; m[10] = up[2] * size;
              m[12] = p[0]; m[13] = p[1]; m[14] = p[2]; m[15] = 1;
              beads.push({ model: m, r, color: colour, glow: num(flow.glow, 0.45), alpha: 1 });
            }
          }
          return beads;
        },
      };
    }

    // ---- explore: the exploded view and the part card sit on top of the film's frame. Opening
    // either pauses the film; playing, seeking or choosing a chapter returns to it.
    const explore = { apart: 0, apartTo: 0, focus: 0, focusTo: 0, selected: null, shown: null, view: null, raf: 0, last: 0 };
    const labelOf = id => labels.find(l => l.id === String(id)) || null;
    const numberOf = label => (label.n !== undefined ? String(label.n) : data.numbered === false ? '' : String(labels.indexOf(label) + 1));
    const targetOf = frame => (frame.camera.e >= 0.5 ? frame.camera.to : frame.camera.from);
    const aim = (from, to) => { explore.view = { from, to, k: board.reduced ? 1 : 0 }; };

    function overlay(base) {
      const x = ease(explore.apart), f = ease(explore.focus);
      if (x <= 0 && f <= 0 && !explore.view) return base;
      const label = explore.shown ? labelOf(explore.shown) : null;
      // A callout on one copy ("compressor.3") spotlights the whole part (every stage).
      const key = label && label.part !== undefined ? String(label.part).replace(/\.\d+$/, '') : null;
      const view = explore.view;
      return Object.assign({}, base, {
        explode: lerp(base.explode, Math.max(base.explode, 1), x),
        cut: base.cut === undefined ? undefined : lerp(base.cut, 0, x),
        camera: Object.assign({}, base.camera, {
          distance: lerp(base.camera.distance, Math.max(base.camera.distance, 1.05), x),
          from: view ? view.from : base.camera.from, to: view ? view.to : base.camera.to, e: view ? ease(view.k) : base.camera.e,
        }),
        // Taken apart, every part is named; an open card spotlights its own part.
        labels: spec => {
          const v = Math.max(base.labels(spec), x);
          return !label ? v : spec.id === label.id ? Math.max(v, f) : v * (1 - f);
        },
        opacity: part => {
          const o = lerp(base.opacity(part), 1, x);
          return key ? lerp(o, board.belongs(part, key) ? 1 : GHOST, f) : o;
        },
        flows: parts => (x > 0.3 || f > 0.3 ? [] : base.flows(parts)),
        selected: explore.selected,
      });
    }

    function animate(now) {
      explore.raf = 0;
      const dt = explore.last ? Math.min(0.1, (now - explore.last) / 1000) : 0;
      explore.last = now;
      const towards = (value, to, seconds) => (board.reduced ? to : value < to ? Math.min(to, value + dt / seconds) : Math.max(to, value - dt / seconds));
      explore.apart = towards(explore.apart, explore.apartTo, 1.1);
      explore.focus = towards(explore.focus, explore.focusTo, 0.6);
      if (explore.view) explore.view.k = towards(explore.view.k, 1, 0.9);
      if (explore.focus <= 0 && explore.focusTo <= 0) explore.shown = explore.selected;
      const settled = explore.apart === explore.apartTo && explore.focus === explore.focusTo && (!explore.view || explore.view.k >= 1);
      if (settled && explore.apart <= 0 && explore.focus <= 0 && !explore.selected) explore.view = null;
      show();
      if (!settled) explore.raf = requestAnimationFrame(animate);
      else explore.last = 0;
    }
    function kick() { if (!explore.raf) { explore.last = 0; explore.raf = requestAnimationFrame(animate); } }
    const currentTarget = () => (explore.view ? explore.view.to : targetOf(frameAt(t)));

    function setApart(on) {
      on = !!on;
      if (on === !!explore.apartTo && !explore.selected) return;
      if (on && playing) stop();
      const from = currentTarget();
      explore.apartTo = on ? 1 : 0;
      explore.selected = null; explore.focusTo = 0;
      aim(from, on ? null : targetOf(frameAt(t)));
      kick();
    }
    function inspect(id) {
      const label = labelOf(id);
      if (!label) return;
      if (playing) stop();
      const from = currentTarget();
      explore.selected = explore.shown = label.id;
      explore.focusTo = 1;
      aim(from, label.part !== undefined ? String(label.part).replace(/\.\d+$/, '') : null);
      kick();
    }
    function uninspect() {
      if (!explore.selected) return;
      const from = currentTarget();
      explore.selected = null; explore.focusTo = 0;
      aim(from, explore.apartTo ? null : targetOf(frameAt(t)));
      kick();
    }
    // Back to the film exactly where it was: assembled, nothing selected.
    function leave() {
      if (!explore.apartTo && !explore.selected && explore.apart <= 0 && explore.focus <= 0) return;
      const from = currentTarget();
      explore.apartTo = 0; explore.selected = null; explore.focusTo = 0;
      aim(from, targetOf(frameAt(t)));
      kick();
    }

    function show() {
      board.frame(overlay(frameAt(t)));
      const k = chapterAt(t);
      const card = explore.selected ? labelOf(explore.selected) : null;
      const mode = card ? 'part:' + card.id : explore.apartTo ? 'apart' : 'film';
      const apart = !!explore.apartTo;
      apartButton.setAttribute('aria-pressed', apart ? 'true' : 'false');
      apartButton.setAttribute('aria-label', apart ? 'Put the parts back together' : 'Explode into parts');
      apartText.textContent = apart ? 'Assemble' : 'Explode';
      apartGlyph.setAttribute('d', apart
        ? 'M4 9h5V4M20 9h-5V4M4 15h5v5M20 15h-5v5'
        : 'M9 4H4v5M15 4h5v5M9 20H4v-5M15 20h5v-5M12 9v6M9 12h6');
      apartButton.style.background = apart ? 'var(--primary,#2340E8)' : 'var(--card,#FFFFFF)';
      apartButton.style.color = apart ? 'var(--primary-foreground,#FFFFFF)' : 'var(--foreground,#15161E)';
      apartButton.style.borderColor = apart ? 'var(--primary,#2340E8)' : 'var(--border-strong,var(--border,#CFCCC2))';
      if (mode !== shownMode) {
        shownMode = mode;
        shownChapter = -1;
        close.style.display = mode === 'film' ? 'none' : 'inline-flex';
        close.textContent = card && apart ? 'All parts' : 'Back to the film';
        chips.forEach(chip => { chip.style.opacity = mode === 'film' ? '' : '0.6'; });
        if (card) {
          badge.textContent = numberOf(card) || '\u2022';
          heading.textContent = String(card.text);
          line.textContent = String(card.detail || card.note || '');
        } else if (mode === 'apart') {
          badge.textContent = String(labels.length);
          heading.textContent = 'Every part, taken apart';
          line.textContent = labels.length ? 'Select any label to see what that part is and what it does.' : 'Drag to turn the parts around.';
        }
      }
      if (mode === 'film' && k !== shownChapter) {
        shownChapter = k;
        badge.textContent = String(k + 1);
        heading.textContent = chapters[k].title;
        line.textContent = chapters[k].say;
        chips.forEach((chip, i) => {
          const on = i === k;
          chip.setAttribute('aria-current', on ? 'step' : 'false');
          chip.style.borderColor = on ? 'var(--primary,#2340E8)' : 'var(--border,#E4E2DA)';
          chip.style.color = on ? 'var(--foreground,#15161E)' : 'var(--muted-foreground,#5D5C57)';
          chip.style.fontWeight = on ? '600' : '500';
        });
      }
      scrub.value = String(Math.round(t * 100));
      time.textContent = clock(t) + ' / ' + clock(total);
      glyph.setAttribute('d', playing ? 'M7 5h3.5v14H7zM13.5 5H17v14h-3.5z' : 'M8 5.5v13l10.5-6.5z');
      play.setAttribute('aria-label', playing ? 'Pause film' : t >= total - 0.01 ? 'Replay film' : 'Play film');
    }

    function loop(now) {
      raf = 0;
      if (!playing) return;
      const dt = last ? Math.min(0.1, (now - last) / 1000) : 0;
      last = now;
      t = Math.min(total, t + dt * rate);
      if (t >= total) playing = false;
      show();
      if (playing) raf = requestAnimationFrame(loop);
    }
    function start() {
      leave();
      if (t >= total - 0.01) t = 0;
      playing = true; last = 0;
      if (!raf) raf = requestAnimationFrame(loop);
      show();
    }
    function stop() { playing = false; if (raf) cancelAnimationFrame(raf); raf = 0; show(); }
    function seek(at) { t = clamp(num(at, 0), 0, total); last = 0; show(); }

    play.addEventListener('click', () => (playing ? stop() : start()));
    apartButton.addEventListener('click', () => setApart(!explore.apartTo));
    close.addEventListener('click', () => (explore.selected && explore.apartTo ? uninspect() : leave()));
    scrub.addEventListener('input', () => { leave(); const resume = playing; if (resume) stop(); seek(Number(scrub.value) / 100); if (resume) start(); });
    root.addEventListener('keydown', event => {
      if (event.key === ' ' && event.target === board.element) { event.preventDefault(); playing ? stop() : start(); }
      if (event.key === 'Escape' && (explore.selected || explore.apartTo)) {
        event.preventDefault();
        if (explore.selected && explore.apartTo) uninspect(); else leave();
      }
    });

    const api = {
      board,
      element: root,
      get stepCount() { return chapters.length; },
      get currentStep() { return chapterAt(t); },
      get time() { return t; },
      get duration() { return total; },
      get playing() { return playing; },
      get rate() { return rate; },
      set rate(value) { rate = clamp(num(value, 1), 0.25, 4); },
      // Stepping lands on the chapter's settled state; while playing it plays in from the cut.
      step(k) {
        leave();
        const chapter = chapters[clamp(Math.round(num(k, 0)), 0, chapters.length - 1)];
        seek(playing ? chapter.start + 1e-4 : chapter.start + chapter.blend);
        if (playing && !raf) raf = requestAnimationFrame(loop);
      },
      describe() {
        const card = explore.selected ? labelOf(explore.selected) : null;
        if (card) return 'Part ' + (numberOf(card) || '') + ': ' + card.text + '. ' + (card.detail || card.note || '');
        if (explore.apartTo) return 'Exploded view: ' + labels.length + ' labelled parts. Select a label to learn about that part.';
        const k = chapterAt(t);
        return 'Chapter ' + (k + 1) + ' of ' + chapters.length + ': ' + chapters[k].title + '. ' + chapters[k].say;
      },
      reset() { stop(); leave(); seek(0); },
      // Explore: take the product apart, or open one labelled part's card.
      get exploded() { return !!explore.apartTo; },
      get selected() { return explore.selected; },
      explode(on) { setApart(on === undefined ? !explore.apartTo : !!on); },
      inspect,
      assemble: leave,
      play: start,
      pause: stop,
      seek,
    };
    seek(0);
    if (options.autoplay !== false && !board.reduced) start();
    return api;
  }

  function aroundMatrixOf(axis, angle, pivot) {
    const [x, y, z] = norm(axis), c = Math.cos(angle), s = Math.sin(angle), k = 1 - c;
    const m = m4();
    m[0] = k * x * x + c; m[1] = k * x * y + s * z; m[2] = k * x * z - s * y;
    m[4] = k * x * y - s * z; m[5] = k * y * y + c; m[6] = k * y * z + s * x;
    m[8] = k * x * z + s * y; m[9] = k * y * z - s * x; m[10] = k * z * z + c;
    m[12] = pivot[0] - (m[0] * pivot[0] + m[4] * pivot[1] + m[8] * pivot[2]);
    m[13] = pivot[1] - (m[1] * pivot[0] + m[5] * pivot[1] + m[9] * pivot[2]);
    m[14] = pivot[2] - (m[2] * pivot[0] + m[6] * pivot[1] + m[10] * pivot[2]);
    m[15] = 1;
    return m;
  }
  function mixColour(a, b, t) {
    const p = rgbOf(resolveColour(a, '#6C8CFF')) || [0.4, 0.5, 1], q = rgbOf(resolveColour(b, '#6C8CFF')) || p;
    const h = v => Math.round(clamp(v, 0, 1) * 255).toString(16).padStart(2, '0');
    return '#' + h(p[0] + (q[0] - p[0]) * t) + h(p[1] + (q[1] - p[1]) * t) + h(p[2] + (q[2] - p[2]) * t);
  }
  function axisOf(axis) {
    if (typeof axis === 'string') {
      const key = axis.replace(/[^xyz]/gi, '').toLowerCase();
      const sign = /^\s*-/.test(axis) ? -1 : 1;
      return key === 'x' ? [sign, 0, 0] : key === 'z' ? [0, 0, sign] : [0, sign, 0];
    }
    return norm(vec3(axis, [0, 1, 0]));
  }

  return { mount, film, audit, materials: Object.keys(MATERIALS), kinds: KINDS };
})();
