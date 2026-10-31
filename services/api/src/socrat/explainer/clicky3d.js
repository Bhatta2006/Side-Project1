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

  const KINDS = ['box', 'cyl', 'cone', 'tube', 'arrow', 'lathe', 'sphere', 'torus', 'capsule', 'pipe', 'spring', 'gear', 'extrude', 'blob', 'poly', 'surface'];
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
    return new Float32Array([A / det, B / det, C / det, (c * h - b * i) / det, (a * i - c * g) / det, (b * g - a * h) / det, (b * f - c * e) / det, (c * d - a * f) / det, (a * e - b * d) / det]);
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

  function labelTone(tone, colours) {
    colours = colours || theme();
    return tone === 'pen' ? colours.pen : tone === 'primary' ? colours.primary : tone === 'muted' ? colours.muted : (colours.dark ? '#ECEBE5' : DEFAULT_INK);
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
      const height = Math.max(240, Math.min(600, Math.round(width * 0.66)));
      if (width === state.width && height === state.height && renderer) return;
      state.width = width;
      state.height = height;
      state.dpr = Math.min(2, Math.max(1, window.devicePixelRatio || 1));
      wrap.style.height = height + 'px';
      leaders.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
      if (renderer) renderer.setSize(width, height, state.dpr);
      if (state.scene.parts) render(performance.now());
    }

    function sceneParts(scene) {
      const list = Array.isArray(scene.parts) ? scene.parts.filter(part => part && !part.hidden) : [];
      const now = performance.now();
      const tracks = new Map();
      const parts = list.map((part, index) => {
        const id = String(part.id || 'part' + index);
        const at = vec3(part.at || part.pos, [0, 0, 0]);
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
        return { spec: part, id, track, index };
      });
      state.tracks = tracks;
      return parts;
    }

    function displayOf(part, now) {
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
      return parts.map(part => {
        const spec = part.spec;
        const display = displayOf(part, now);
        const mirror = vec3(spec.mirror, [1, 1, 1]);
        const scale = [display.scale[0] * mirror[0], display.scale[1] * mirror[1], display.scale[2] * mirror[2]];
        const model = trs(display.at, display.rot, scale);
        const matrix = normalMatrix(model);
        const material = MATERIALS[String(spec.mat || spec.material || 'paint')] || MATERIALS.paint;
        const colour = linearOf(resolveColour(spec.color, material.color));
        const opacity = clamp(num(spec.opacity, 1), 0, 1);
        const glass = !!material.glass || !!spec.glass;
        const cut = cutPlane(spec.cut);
        const bands = bandData(spec);
        const glow = material.glow || spec.glow ? Math.max(0, num(spec.glow, 0.9)) : 0;
        const doubleSided = !!spec.double || !!cut;
        part.model = model;
        return {
          id: part.index + 1,
          part,
          geometry: geometryOf(spec.kind, spec.recipe),
          model,
          normal: matrix,
          flip: scale[0] * scale[1] * scale[2] < 0,
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
    }

    function cutPlane(cut) {
      if (cut === true) return new Float32Array([0, 0, 1, 0]);
      if (Array.isArray(cut) && cut.length >= 3) {
        const n = vec3(cut, [0, 0, 1]);
        const length = Math.hypot(n[0], n[1], n[2]) || 1;
        return new Float32Array([n[0] / length, n[1] / length, n[2] / length, num(cut[3], 0)]);
      }
      if (cut && typeof cut === 'object') {
        const n = vec3(cut.normal || cut.axis, [0, 0, 1]);
        const length = Math.hypot(n[0], n[1], n[2]) || 1;
        return new Float32Array([n[0] / length, n[1] / length, n[2] / length, num(cut.offset, num(cut.at, 0))]);
      }
      return new Float32Array(4);
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
      for (const item of state.labels) { item.node.remove(); item.path.remove(); item.dot.remove(); }
      state.labels = [];
      const colours = theme();
      const labels = Array.isArray(scene.labels) ? scene.labels.filter(l => l && l.text) : [];
      labels.forEach((spec, index) => {
        const part = state.lastParts && state.lastParts.find(p => p.id === String(spec.part));
        const local = vec3(spec.anchor, [0, 0, 0]);
        const fixed = !part && Array.isArray(spec.at) ? vec3(spec.at, [0, 0, 0]) : null;
        if (!part && !fixed) return;
        const node = document.createElement('div');
        node.textContent = String(spec.text);
        const tone = labelTone(spec.tone, colours);
        node.style.cssText = 'position:absolute;left:0;top:0;transform:translate3d(-1000px,-1000px,0);font:600 13px/1.25 ui-sans-serif,system-ui,sans-serif;letter-spacing:-0.01em;color:' + tone + ';background:color-mix(in srgb,' + colours.paper + ' 84%,transparent);border:1px solid color-mix(in srgb,' + tone + ' 18%,transparent);border-radius:800px;padding:3px 9px;white-space:nowrap;box-shadow:0 1px 2px color-mix(in srgb,' + colours.ink + ' 8%,transparent)';
        layer.appendChild(node);
        const width = node.offsetWidth, height = node.offsetHeight;
        const path = document.createElementNS(NS, 'path');
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke', tone);
        path.setAttribute('stroke-width', '1.4');
        path.setAttribute('stroke-linecap', 'round');
        path.setAttribute('opacity', '0.72');
        leaders.appendChild(path);
        const dot = document.createElementNS(NS, 'circle');
        dot.setAttribute('r', '2.4');
        dot.setAttribute('fill', tone);
        dot.setAttribute('opacity', '0.9');
        leaders.appendChild(dot);
        const dx = num(spec.dx, index % 2 === 0 ? 92 : -92);
        const dy = num(spec.dy, -68 - Math.floor(index / 2) * 34);
        state.labels.push({ spec, node, path, dot, part, local, fixed, dx, dy, width, height });
      });
    }

    function positionLabels(camera, width, height) {
      const placed = [];
      for (const item of state.labels) {
        const anchor = item.part ? apply(item.part.model, item.local) : item.fixed;
        const p = anchor ? project(camera.eye, camera.target, camera.fov, width / height, anchor) : null;
        if (!p) { item.node.style.display = 'none'; item.path.style.display = 'none'; item.dot.style.display = 'none'; continue; }
        item.node.style.display = '';
        item.path.style.display = '';
        item.dot.style.display = '';
        const anchorX = p.x * width, anchorY = p.y * height;
        const minX = item.width / 2 + 8, maxX = Math.max(minX, width - item.width / 2 - 8);
        const minY = item.height / 2 + 8, maxY = Math.max(minY, height - item.height / 2 - 8);
        const x = clamp(anchorX + item.dx, minX, maxX);
        let y = clamp(anchorY + item.dy, minY, maxY);
        // Keep pills from stacking on each other: push the later one away from its anchor, then back.
        const away = item.dy < 0 ? -1 : 1;
        for (let tries = 0; tries < 6; tries++) {
          const hit = placed.find(q => Math.min(x + item.width / 2, q.right) - Math.max(x - item.width / 2, q.left) > 2 && Math.min(y + item.height / 2, q.bottom) - Math.max(y - item.height / 2, q.top) > 2);
          if (!hit) break;
          const up = away < 0 ? hit.top - 7 - item.height / 2 : hit.bottom + 7 + item.height / 2;
          const down = away < 0 ? hit.bottom + 7 + item.height / 2 : hit.top - 7 - item.height / 2;
          const target = up >= minY && up <= maxY ? up : down;
          const next = clamp(target, minY, maxY);
          if (Math.abs(next - y) < 1) {
            y = clamp(y + away * (item.height + 8), minY, maxY);
            break;
          }
          y = next;
        }
        placed.push({ left: x - item.width / 2, right: x + item.width / 2, top: y - item.height / 2, bottom: y + item.height / 2 });
        item.node.style.transform = 'translate3d(' + (x - item.width / 2).toFixed(1) + 'px,' + (y - item.height / 2).toFixed(1) + 'px,0)';
        const kneeX = anchorX + (x - anchorX) * 0.58;
        item.path.setAttribute('d', 'M' + anchorX.toFixed(1) + ' ' + anchorY.toFixed(1) + 'L' + kneeX.toFixed(1) + ' ' + anchorY.toFixed(1) + 'L' + x.toFixed(1) + ' ' + y.toFixed(1));
        item.dot.setAttribute('cx', anchorX.toFixed(1));
        item.dot.setAttribute('cy', anchorY.toFixed(1));
      }
    }

    function render(now) {
      if (!renderer || !state.width) return;
      const scene = state.scene || {};
      const parts = state.lastParts;
      if (!parts) return;
      const width = state.width, height = state.height, aspect = width / height;
      const cameraSpec = scene.camera || {};
      const yawBase = num(cameraSpec.yaw, -20) * DEG;
      const spin = state.reduced ? 0 : num(cameraSpec.spin, 0.3);
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
      let min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
      for (const part of parts) {
        const display = displayOf(part, now);
        const mirror = vec3(part.spec.mirror, [1, 1, 1]);
        const model = trs(display.at, display.rot, [display.scale[0] * mirror[0], display.scale[1] * mirror[1], display.scale[2] * mirror[2]]);
        const geometry = geometryOf(part.spec.kind, part.spec.recipe);
        const stride = Math.max(1, Math.floor(geometry.samples.length / 600));
        for (let i = 0; i < geometry.samples.length; i += 3 * stride) {
          const p = apply(model, [geometry.samples[i], geometry.samples[i + 1], geometry.samples[i + 2]]);
          for (let k = 0; k < 3; k++) { if (p[k] < min[k]) min[k] = p[k]; if (p[k] > max[k]) max[k] = p[k]; }
          samples.push(p);
        }
      }
      if (!samples.length) { min = [-0.5, 0, -0.5]; max = [0.5, 1, 0.5]; }
      const fittedCenter = [(min[0] + max[0]) / 2, (min[1] + max[1]) / 2, (min[2] + max[2]) / 2];
      const center = vec3(cameraSpec.target, fittedCenter);
      const extent = Math.max(0.2, Math.max(max[0] - min[0], max[1] - min[1], max[2] - min[2]) / 2);
      const targetDistance = fitDistance(samples, center, yawBase + view.yaw, tilt, fov, aspect)
        * clamp(num(cameraSpec.distance, 1.1), 0.55, 3) * view.zoom;
      state.wantedDistance = targetDistance;
      if (!state.distance) state.distance = targetDistance;
      state.distance += (targetDistance - state.distance) * (state.reduced ? 1 : 0.18);
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
          width: num(scene.ink && scene.ink.width, 0.9),
          seamWidth: num(scene.ink && scene.ink.seamWidth, 0.6),
          strength: num(scene.ink && scene.ink.strength, 1),
          shade: num(scene.ink && scene.ink.shade, 0.6),
          color: rgbOf(scene.ink && scene.ink.color) || ink,
          a: 1,
        },
        camera,
      });
      positionLabels(camera, width, height);
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
      return problems.slice(0, 5);
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
      dispose() {
        const index = boards.indexOf(board);
        if (index >= 0) boards.splice(index, 1);
        if (state.raf) cancelAnimationFrame(state.raf);
        if (observer) observer.disconnect();
        if (themeObserver) themeObserver.disconnect();
        removeEventListener('resize', resize);
        for (const item of state.labels) { item.node.remove(); item.path.remove(); item.dot.remove(); }
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

  return { mount, audit, materials: Object.keys(MATERIALS), kinds: KINDS };
})();
