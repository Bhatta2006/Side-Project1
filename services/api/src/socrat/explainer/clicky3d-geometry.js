/* Clicky3D geometry: part recipes built into typed arrays the renderer draws.
   Plain data in, indexed meshes out; the scene kit caches them by canonical recipe.
   Conventions: Y is up, revolved kinds turn about Y, every closed part is wound outward. */
const Clicky3DGeometry = (() => {
  'use strict';

  const TAU = Math.PI * 2;
  const DEG = Math.PI / 180;
  const MAX_VERTICES = 160000;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const num = (v, d) => (typeof v === 'number' && isFinite(v) ? v : d);
  const pos = (v, d) => Math.max(1e-4, num(v, d));
  const vec3 = v => (Array.isArray(v) && v.length >= 3 && v.slice(0, 3).every(n => typeof n === 'number' && isFinite(n)) ? [v[0], v[1], v[2]] : null);
  const pts2 = list => (Array.isArray(list) ? list : []).filter(p => Array.isArray(p) && p.length >= 2 && isFinite(p[0]) && isFinite(p[1])).map(p => [+p[0], +p[1]]);
  const pts3 = list => (Array.isArray(list) ? list : []).filter(p => Array.isArray(p) && p.length >= 3 && p.slice(0, 3).every(isFinite)).map(p => [+p[0], +p[1], +p[2]]);
  const normalize = v => { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; };
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
  const crossV = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];

  // ------------------------------------------------------------------ mesh basics
  function mesh() { return { p: [], n: [], uv: [], i: [] }; }
  function vert(m, x, y, z, nx, ny, nz, u, v) {
    const at = m.p.length / 3;
    m.p.push(x, y, z);
    m.n.push(nx, ny, nz);
    m.uv.push(u || 0, v || 0);
    return at;
  }
  function finish(m) {
    return { positions: new Float32Array(m.p), normals: new Float32Array(m.n), uvs: new Float32Array(m.uv), indices: new Uint32Array(m.i) };
  }
  function merge(parts) {
    const out = mesh();
    for (const m of parts) {
      const base = out.p.length / 3;
      for (let i = 0; i < m.p.length; i++) out.p.push(m.p[i]);
      for (let i = 0; i < m.n.length; i++) out.n.push(m.n[i]);
      for (let i = 0; i < m.uv.length; i++) out.uv.push(m.uv[i]);
      for (let i = 0; i < m.i.length; i++) out.i.push(base + m.i[i]);
    }
    return out;
  }
  function transform(m, R, t) {
    // R is a row-major 3x3 rotation, t a translation. Normals take R as well.
    for (let i = 0; i < m.p.length; i += 3) {
      const x = m.p[i], y = m.p[i + 1], z = m.p[i + 2];
      m.p[i] = R[0] * x + R[1] * y + R[2] * z + (t ? t[0] : 0);
      m.p[i + 1] = R[3] * x + R[4] * y + R[5] * z + (t ? t[1] : 0);
      m.p[i + 2] = R[6] * x + R[7] * y + R[8] * z + (t ? t[2] : 0);
      const a = m.n[i], b = m.n[i + 1], c = m.n[i + 2];
      m.n[i] = R[0] * a + R[1] * b + R[2] * c;
      m.n[i + 1] = R[3] * a + R[4] * b + R[5] * c;
      m.n[i + 2] = R[6] * a + R[7] * b + R[8] * c;
    }
    return m;
  }
  function axisAngle(axis, angle) {
    const [x, y, z] = normalize(axis), c = Math.cos(angle), s = Math.sin(angle), t = 1 - c;
    return [t * x * x + c, t * x * y - s * z, t * x * z + s * y, t * x * y + s * z, t * y * y + c, t * y * z - s * x, t * x * z - s * y, t * y * z + s * x, t * z * z + c];
  }
  function translate(m, x, y, z) { return transform(m, [1, 0, 0, 0, 1, 0, 0, 0, 1], [x, y, z]); }
  // Rotate +Y onto dir.
  function turn(m, dir) {
    const d = normalize(dir);
    if (d[1] > 0.99999) return m;
    if (d[1] < -0.99999) return transform(m, axisAngle([1, 0, 0], Math.PI));
    return transform(m, axisAngle(crossV([0, 1, 0], d), Math.acos(clamp(d[1], -1, 1))));
  }
  function stretchMesh(m, sx, sy, sz) {
    for (let i = 0; i < m.p.length; i += 3) { m.p[i] *= sx; m.p[i + 1] *= sy; m.p[i + 2] *= sz; }
    for (let i = 0; i < m.n.length; i += 3) {
      const n = normalize([m.n[i] / (sx || 1), m.n[i + 1] / (sy || 1), m.n[i + 2] / (sz || 1)]);
      m.n[i] = n[0]; m.n[i + 1] = n[1]; m.n[i + 2] = n[2];
    }
    if (sx * sy * sz < 0) for (let i = 0; i < m.i.length; i += 3) { const t = m.i[i + 1]; m.i[i + 1] = m.i[i + 2]; m.i[i + 2] = t; }
    return m;
  }
  // Area-weighted vertex normals from the triangles (for gridded surfaces).
  function computeNormals(m) {
    const n = new Float64Array(m.p.length);
    for (let k = 0; k < m.i.length; k += 3) {
      const a = m.i[k] * 3, b = m.i[k + 1] * 3, c = m.i[k + 2] * 3;
      const e1 = [m.p[b] - m.p[a], m.p[b + 1] - m.p[a + 1], m.p[b + 2] - m.p[a + 2]];
      const e2 = [m.p[c] - m.p[a], m.p[c + 1] - m.p[a + 1], m.p[c + 2] - m.p[a + 2]];
      const f = crossV(e1, e2);
      for (const v of [a, b, c]) { n[v] += f[0]; n[v + 1] += f[1]; n[v + 2] += f[2]; }
    }
    for (let i = 0; i < n.length; i += 3) {
      const v = normalize([n[i], n[i + 1], n[i + 2]]);
      m.n[i] = v[0]; m.n[i + 1] = v[1]; m.n[i + 2] = v[2];
    }
    return m;
  }
  // A closed mesh with negative signed volume is wound inward: flip it.
  function orientOutward(m, keepNormals) {
    let volume = 0;
    for (let k = 0; k < m.i.length; k += 3) {
      const a = m.i[k] * 3, b = m.i[k + 1] * 3, c = m.i[k + 2] * 3;
      volume += m.p[a] * (m.p[b + 1] * m.p[c + 2] - m.p[b + 2] * m.p[c + 1])
        - m.p[a + 1] * (m.p[b] * m.p[c + 2] - m.p[b + 2] * m.p[c])
        + m.p[a + 2] * (m.p[b] * m.p[c + 1] - m.p[b + 1] * m.p[c]);
    }
    if (volume < 0) {
      for (let i = 0; i < m.i.length; i += 3) { const t = m.i[i + 1]; m.i[i + 1] = m.i[i + 2]; m.i[i + 2] = t; }
      if (!keepNormals) for (let i = 0; i < m.n.length; i++) m.n[i] = -m.n[i];
    }
    return m;
  }
  // rows x cols grid of points; wrapCols closes each row into a loop. Normals from the faces.
  function gridMesh(rows, wrapCols) {
    const m = mesh(), R = rows.length, C = rows[0].length;
    const cols = wrapCols ? C + 1 : C;
    for (let r = 0; r < R; r++) for (let c = 0; c < cols; c++) {
      const p = rows[r][c % C];
      vert(m, p[0], p[1], p[2], 0, 1, 0, c / (cols - 1), r / (R - 1 || 1));
    }
    for (let r = 0; r < R - 1; r++) for (let c = 0; c < cols - 1; c++) {
      const a = r * cols + c, b = a + 1, d = a + cols, e = d + 1;
      m.i.push(a, d, b, b, d, e);
    }
    computeNormals(m);
    if (wrapCols) {
      // The seam column is duplicated for UVs; give both copies the same averaged normal.
      for (let r = 0; r < R; r++) {
        const a = (r * cols) * 3, b = (r * cols + C) * 3;
        const v = normalize([m.n[a] + m.n[b], m.n[a + 1] + m.n[b + 1], m.n[a + 2] + m.n[b + 2]]);
        m.n[a] = m.n[b] = v[0]; m.n[a + 1] = m.n[b + 1] = v[1]; m.n[a + 2] = m.n[b + 2] = v[2];
      }
    }
    return m;
  }
  // A flat fan closing one loop of a gridMesh: the first row's cap keeps the loop's winding and
  // the last row's cap reverses it, which matches the grid. orientOutward then fixes both at once.
  function capLoop(loop, reverse) {
    const m = mesh();
    const c = loop.reduce((s, p) => [s[0] + p[0] / loop.length, s[1] + p[1] / loop.length, s[2] + p[2] / loop.length], [0, 0, 0]);
    let nrm = [0, 0, 0];
    for (let i = 0; i < loop.length; i++) {
      const f = crossV(sub(loop[i], c), sub(loop[(i + 1) % loop.length], c));
      nrm = [nrm[0] + f[0], nrm[1] + f[1], nrm[2] + f[2]];
    }
    nrm = normalize(nrm);
    if (reverse) nrm = nrm.map(v => -v);
    const center = vert(m, c[0], c[1], c[2], nrm[0], nrm[1], nrm[2], 0.5, 0.5);
    for (const p of loop) vert(m, p[0], p[1], p[2], nrm[0], nrm[1], nrm[2], 0, 0);
    for (let i = 0; i < loop.length; i++) {
      const a = center + 1 + i, b = center + 1 + ((i + 1) % loop.length);
      if (reverse) m.i.push(center, b, a); else m.i.push(center, a, b);
    }
    return m;
  }

  // ------------------------------------------------------------------ 2D profiles
  // Round every sharp corner of a (r, y) or (x, y) polyline with a short Bézier fillet.
  function fillet(points, radius, closed, steps, keep) {
    if (!(radius > 0) || points.length < 3) return points.slice();
    steps = steps || 4;
    const out = [], n = points.length;
    for (let i = 0; i < n; i++) {
      const p = points[i];
      const hasPrev = closed || i > 0, hasNext = closed || i < n - 1;
      if (!hasPrev || !hasNext || (keep && keep(p, i))) { out.push(p); continue; }
      const a = points[(i - 1 + n) % n], b = points[(i + 1) % n];
      const l1 = Math.hypot(p[0] - a[0], p[1] - a[1]), l2 = Math.hypot(b[0] - p[0], b[1] - p[1]);
      if (l1 < 1e-9 || l2 < 1e-9) { out.push(p); continue; }
      const u1 = [(p[0] - a[0]) / l1, (p[1] - a[1]) / l1], u2 = [(b[0] - p[0]) / l2, (b[1] - p[1]) / l2];
      const bend = Math.acos(clamp(u1[0] * u2[0] + u1[1] * u2[1], -1, 1));
      if (bend < 0.2) { out.push(p); continue; }
      const d = Math.min(radius * Math.tan(bend / 2), l1 * 0.45, l2 * 0.45);
      const s = [p[0] - u1[0] * d, p[1] - u1[1] * d], e = [p[0] + u2[0] * d, p[1] + u2[1] * d];
      for (let k = 0; k <= steps; k++) {
        const t = k / steps, q = 1 - t;
        out.push([q * q * s[0] + 2 * q * t * p[0] + t * t * e[0], q * q * s[1] + 2 * q * t * p[1] + t * t * e[1]]);
      }
    }
    return out;
  }
  function signedArea(pts) {
    let a = 0;
    for (let i = 0; i < pts.length; i++) { const p = pts[i], q = pts[(i + 1) % pts.length]; a += p[0] * q[1] - q[0] * p[1]; }
    return a / 2;
  }
  function circle(cx, cy, r, count) {
    const out = [];
    for (let i = 0; i < count; i++) { const a = (TAU * i) / count; out.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]); }
    return out;
  }
  function roundedRect(w, h, corner, steps) {
    const c = clamp(corner, 0, Math.min(w, h) / 2 - 1e-4), x = w / 2, y = h / 2, out = [];
    if (c <= 1e-4) return [[-x, -y], [x, -y], [x, y], [-x, y]];
    const corners = [[x - c, -y + c, -90], [x - c, y - c, 0], [-x + c, y - c, 90], [-x + c, -y + c, 180]];
    for (const [cx, cy, start] of corners) for (let k = 0; k <= steps; k++) {
      const a = (start + (90 * k) / steps) * DEG;
      out.push([cx + Math.cos(a) * c, cy + Math.sin(a) * c]);
    }
    return out;
  }
  // Offset a loop to its left by dist (inward for a CCW outline), mitred and clamped.
  function offsetLoop(loop, dist) {
    if (!dist) return loop.map(p => p.slice());
    const n = loop.length, out = [];
    for (let i = 0; i < n; i++) {
      const a = loop[(i - 1 + n) % n], p = loop[i], b = loop[(i + 1) % n];
      const e1 = normalize([p[0] - a[0], p[1] - a[1], 0]), e2 = normalize([b[0] - p[0], b[1] - p[1], 0]);
      const n1 = [-e1[1], e1[0]], n2 = [-e2[1], e2[0]];
      let mx = n1[0] + n2[0], my = n1[1] + n2[1];
      const ml = Math.hypot(mx, my);
      if (ml < 1e-6) { mx = n1[0]; my = n1[1]; } else { mx /= ml; my /= ml; }
      const cos = Math.max(0.35, mx * n1[0] + my * n1[1]);
      out.push([p[0] + (mx * dist) / cos, p[1] + (my * dist) / cos]);
    }
    return out;
  }
  // Earcut (after Mapbox's algorithm, without the z-order hash): holes are bridged into the
  // outer ring by a ray cast to the nearest visible vertex, then ears are clipped, with local
  // self-intersections cured and a split as the last resort. Returns the points and indices.
  function earcut(outer, holes) {
    const flat = [], holeStarts = [];
    for (const p of outer) flat.push(p);
    for (const h of holes) { holeStarts.push(flat.length); for (const p of h) flat.push(p); }
    const node = (i, x, y) => ({ i, x, y, prev: null, next: null, steiner: false });
    const area = (p, q, r) => (q.y - p.y) * (r.x - q.x) - (q.x - p.x) * (r.y - q.y);
    const equals = (a, b) => a.x === b.x && a.y === b.y;
    const insert = (i, last) => {
      const n = node(i, flat[i][0], flat[i][1]);
      if (!last) { n.prev = n; n.next = n; } else { n.next = last.next; n.prev = last; last.next.prev = n; last.next = n; }
      return n;
    };
    const remove = n => { n.next.prev = n.prev; n.prev.next = n.next; };
    const ringArea = (start, end) => {
      let sum = 0;
      for (let i = start, j = end - 1; i < end; j = i++) sum += (flat[j][0] - flat[i][0]) * (flat[i][1] + flat[j][1]);
      return sum;
    };
    const linked = (start, end, clockwise) => {
      let last = null;
      if (clockwise === (ringArea(start, end) > 0)) for (let i = start; i < end; i++) last = insert(i, last);
      else for (let i = end - 1; i >= start; i--) last = insert(i, last);
      if (last && equals(last, last.next)) { remove(last); last = last.next; }
      return last;
    };
    const filter = (start, end) => {
      if (!start) return start;
      if (!end) end = start;
      let p = start, again;
      do {
        again = false;
        if (!p.steiner && (equals(p, p.next) || area(p.prev, p, p.next) === 0)) {
          remove(p); p = end = p.prev;
          if (p === p.next) break;
          again = true;
        } else p = p.next;
      } while (again || p !== end);
      return end;
    };
    const inTri = (ax, ay, bx, by, cx, cy, px, py) => (cx - px) * (ay - py) >= (ax - px) * (cy - py) && (ax - px) * (by - py) >= (bx - px) * (ay - py) && (bx - px) * (cy - py) >= (cx - px) * (by - py);
    const isEar = ear => {
      const a = ear.prev, b = ear, c = ear.next;
      if (area(a, b, c) >= 0) return false;
      let p = c.next;
      while (p !== a) {
        if (inTri(a.x, a.y, b.x, b.y, c.x, c.y, p.x, p.y) && area(p.prev, p, p.next) >= 0) return false;
        p = p.next;
      }
      return true;
    };
    const sign = v => (v > 0 ? 1 : v < 0 ? -1 : 0);
    const onSeg = (p, q, r) => q.x <= Math.max(p.x, r.x) && q.x >= Math.min(p.x, r.x) && q.y <= Math.max(p.y, r.y) && q.y >= Math.min(p.y, r.y);
    const intersects = (p1, q1, p2, q2) => {
      const o1 = sign(area(p1, q1, p2)), o2 = sign(area(p1, q1, q2)), o3 = sign(area(p2, q2, p1)), o4 = sign(area(p2, q2, q1));
      if (o1 !== o2 && o3 !== o4) return true;
      return (o1 === 0 && onSeg(p1, p2, q1)) || (o2 === 0 && onSeg(p1, q2, q1)) || (o3 === 0 && onSeg(p2, p1, q2)) || (o4 === 0 && onSeg(p2, q1, q2));
    };
    const locallyInside = (a, b) => (area(a.prev, a, a.next) < 0 ? area(a, b, a.next) >= 0 && area(a, a.prev, b) >= 0 : area(a, b, a.prev) < 0 || area(a, a.next, b) < 0);
    const middleInside = (a, b) => {
      let p = a, inside = false;
      const px = (a.x + b.x) / 2, py = (a.y + b.y) / 2;
      do {
        if (((p.y > py) !== (p.next.y > py)) && p.next.y !== p.y && px < ((p.next.x - p.x) * (py - p.y)) / (p.next.y - p.y) + p.x) inside = !inside;
        p = p.next;
      } while (p !== a);
      return inside;
    };
    const intersectsPolygon = (a, b) => {
      let p = a;
      do {
        if (p.i !== a.i && p.next.i !== a.i && p.i !== b.i && p.next.i !== b.i && intersects(p, p.next, a, b)) return true;
        p = p.next;
      } while (p !== a);
      return false;
    };
    const isValidDiagonal = (a, b) => a.next.i !== b.i && a.prev.i !== b.i && !intersectsPolygon(a, b)
      && ((locallyInside(a, b) && locallyInside(b, a) && middleInside(a, b) && (area(a.prev, a, b.prev) || area(a, b.prev, b)))
        || (equals(a, b) && area(a.prev, a, a.next) > 0 && area(b.prev, b, b.next) > 0));
    const split = (a, b) => {
      const a2 = node(a.i, a.x, a.y), b2 = node(b.i, b.x, b.y), an = a.next, bp = b.prev;
      a.next = b; b.prev = a; a2.next = an; an.prev = a2; b2.next = a2; a2.prev = b2; bp.next = b2; b2.prev = bp;
      return b2;
    };
    const out = [];
    const cure = start => {
      let p = start;
      do {
        const a = p.prev, b = p.next.next;
        if (!equals(a, b) && intersects(a, p, p.next, b) && locallyInside(a, b) && locallyInside(b, a)) {
          out.push(a.i, p.i, b.i);
          remove(p); remove(p.next);
          p = start = b;
        }
        p = p.next;
      } while (p !== start);
      return filter(p);
    };
    let budget = 200000;
    const clip = (ear, pass) => {
      if (!ear) return;
      let stop = ear;
      while (ear.prev !== ear.next && budget-- > 0) {
        const prev = ear.prev, next = ear.next;
        if (isEar(ear)) { out.push(prev.i, ear.i, next.i); remove(ear); ear = next.next; stop = next.next; continue; }
        ear = next;
        if (ear === stop) {
          if (!pass) clip(filter(ear), 1);
          else if (pass === 1) clip(cure(filter(ear)), 2);
          else splitClip(ear);
          break;
        }
      }
    };
    const splitClip = start => {
      let a = start;
      do {
        let b = a.next.next;
        while (b !== a.prev) {
          if (a.i !== b.i && isValidDiagonal(a, b)) {
            let c = split(a, b);
            a = filter(a, a.next); c = filter(c, c.next);
            clip(a, 0); clip(c, 0);
            return;
          }
          b = b.next;
        }
        a = a.next;
      } while (a !== start);
    };
    const findBridge = (hole, outerNode) => {
      let p = outerNode, qx = -Infinity, m = null;
      const hx = hole.x, hy = hole.y;
      do {
        if (hy <= p.y && hy >= p.next.y && p.next.y !== p.y) {
          const x = p.x + ((hy - p.y) * (p.next.x - p.x)) / (p.next.y - p.y);
          if (x <= hx && x > qx) { qx = x; m = p.x < p.next.x ? p : p.next; if (x === hx) return m; }
        }
        p = p.next;
      } while (p !== outerNode);
      if (!m) return null;
      const stop = m, mx = m.x, my = m.y;
      let tanMin = Infinity;
      p = m;
      do {
        if (hx >= p.x && p.x >= mx && hx !== p.x && inTri(hy < my ? hx : qx, hy, mx, my, hy < my ? qx : hx, hy, p.x, p.y)) {
          const tan = Math.abs(hy - p.y) / (hx - p.x);
          if (locallyInside(p, hole) && (tan < tanMin || (tan === tanMin && (p.x > m.x || (p.x === m.x && area(m.prev, m, p.prev) < 0 && area(p.next, m, m.next) < 0))))) { m = p; tanMin = tan; }
        }
        p = p.next;
      } while (p !== stop);
      return m;
    };
    let outerNode = linked(0, outer.length, true);
    if (!outerNode || outerNode.next === outerNode.prev) return { points: flat, indices: [] };
    if (holeStarts.length) {
      const queue = [];
      holeStarts.forEach((start, k) => {
        const end = k < holeStarts.length - 1 ? holeStarts[k + 1] : flat.length;
        const list = linked(start, end, false);
        if (!list) return;
        if (list === list.next) list.steiner = true;
        let left = list, p = list;
        do { if (p.x < left.x || (p.x === left.x && p.y < left.y)) left = p; p = p.next; } while (p !== list);
        queue.push(left);
      });
      queue.sort((a, b) => a.x - b.x);
      for (const hole of queue) {
        const bridge = findBridge(hole, outerNode);
        if (!bridge) continue;
        const bridgeReverse = split(bridge, hole);
        filter(bridgeReverse, bridgeReverse.next);
        outerNode = filter(bridge, bridge.next);
      }
    }
    clip(outerNode, 0);
    // Triangles come out counter-clockwise for a y-up outline, which is what the caps expect.
    return { points: flat, indices: out };
  }

  // ------------------------------------------------------------------ revolve
  // Spin a (radius, y) profile about Y. Corners sharper than ~35° keep hard normals;
  // gentler joints share one averaged normal. Walk the profile with the material on the left.
  function revolve(profile, seg, closed, sharp) {
    sharp = sharp === undefined ? 0.6 : sharp;
    const pts = profile.filter((p, i) => i === 0 || Math.hypot(p[0] - profile[i - 1][0], p[1] - profile[i - 1][1]) > 1e-7);
    if (closed && pts.length > 2 && Math.hypot(pts[0][0] - pts[pts.length - 1][0], pts[0][1] - pts[pts.length - 1][1]) < 1e-7) pts.pop();
    const n = pts.length;
    const segCount = closed ? n : n - 1;
    const segN = [];
    let total = 0;
    const lengths = [];
    for (let k = 0; k < segCount; k++) {
      const a = pts[k], b = pts[(k + 1) % n];
      const dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1;
      segN.push([dy / l, -dx / l]);
      lengths.push(total);
      total += l;
    }
    const jointNormal = (k, side) => {
      // Normal at point k, as seen from segment `side` (k-1 or k).
      const own = segN[side];
      const other = side === k ? (closed || k > 0 ? segN[(k - 1 + segCount) % segCount] : null) : (closed || k < n - 1 ? segN[k % segCount] : null);
      if (!other || (!closed && (k === 0 || k === n - 1))) return own;
      if (Math.acos(clamp(own[0] * other[0] + own[1] * other[1], -1, 1)) > sharp) return own;
      const v = [own[0] + other[0], own[1] + other[1]], l = Math.hypot(v[0], v[1]) || 1;
      return [v[0] / l, v[1] / l];
    };
    const m = mesh(), row = seg + 1;
    for (let k = 0; k < segCount; k++) {
      const ka = k, kb = (k + 1) % n;
      const ends = [[pts[ka], jointNormal(ka, k), lengths[k]], [pts[kb], jointNormal(kb, k), lengths[k] + Math.hypot(pts[kb][0] - pts[ka][0], pts[kb][1] - pts[ka][1])]];
      const base = m.p.length / 3;
      for (const [p, nrm, along] of ends) {
        for (let i = 0; i <= seg; i++) {
          const a = (TAU * i) / seg, s = Math.sin(a), c = Math.cos(a);
          vert(m, p[0] * s, p[1], p[0] * c, nrm[0] * s, nrm[1], nrm[0] * c, i / seg, 1 - along / (total || 1));
        }
      }
      for (let i = 0; i < seg; i++) {
        const a = base + i, c = a + 1, b = base + row + i, d = b + 1;
        m.i.push(a, c, b, b, c, d);
      }
    }
    return m;
  }
  // Offset an open (r, y) profile inward to give it a wall: the revolved part becomes a shell.
  function withWall(profile, wall) {
    const n = profile.length, inner = [];
    for (let i = 0; i < n; i++) {
      const a = profile[Math.max(0, i - 1)], b = profile[Math.min(n - 1, i + 1)];
      const dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1;
      inner.push([Math.max(0, profile[i][0] - (dy / l) * wall), profile[i][1] + (dx / l) * wall]);
    }
    return profile.concat(inner.reverse());
  }

  // ------------------------------------------------------------------ box
  function boxFace(m, o, u, v, n) {
    const a = vert(m, o[0], o[1], o[2], n[0], n[1], n[2], 0, 0);
    vert(m, o[0] + u[0], o[1] + u[1], o[2] + u[2], n[0], n[1], n[2], 1, 0);
    vert(m, o[0] + v[0], o[1] + v[1], o[2] + v[2], n[0], n[1], n[2], 0, 1);
    vert(m, o[0] + u[0] + v[0], o[1] + u[1] + v[1], o[2] + u[2] + v[2], n[0], n[1], n[2], 1, 1);
    m.i.push(a, a + 1, a + 2, a + 2, a + 1, a + 3);
  }
  function boxData(w, h, d) {
    const m = mesh(), x = w / 2, y = h / 2, z = d / 2;
    boxFace(m, [-x, -y, z], [w, 0, 0], [0, h, 0], [0, 0, 1]);
    boxFace(m, [x, -y, -z], [-w, 0, 0], [0, h, 0], [0, 0, -1]);
    boxFace(m, [x, -y, z], [0, 0, -d], [0, h, 0], [1, 0, 0]);
    boxFace(m, [-x, -y, -z], [0, 0, d], [0, h, 0], [-1, 0, 0]);
    boxFace(m, [-x, y, z], [w, 0, 0], [0, 0, -d], [0, 1, 0]);
    boxFace(m, [-x, -y, -z], [w, 0, 0], [0, 0, d], [0, -1, 0]);
    return m;
  }
  // A rounded box: an indexed 8×8 grid per face pushed onto the rounded hull. Shared edges
  // between faces are welded so the rounding shades as one surface.
  function roundedBoxData(w, h, d, radius) {
    const r = clamp(radius, 0.0005, 0.45 * Math.min(w, h, d));
    const seg = 8, bx = w / 2 - r, by = h / 2 - r, bz = d / 2 - r;
    const m = mesh(), index = new Map();
    // Grid lines bunch near the edges so the rounding gets most of the vertices.
    const spread = t => { const s = t * 2 - 1; return Math.sign(s) * Math.pow(Math.abs(s), 0.55); };
    const faces = [
      [[0, 0, 1], [1, 0, 0], [0, 1, 0]], [[0, 0, -1], [-1, 0, 0], [0, 1, 0]],
      [[1, 0, 0], [0, 0, -1], [0, 1, 0]], [[-1, 0, 0], [0, 0, 1], [0, 1, 0]],
      [[0, 1, 0], [1, 0, 0], [0, 0, -1]], [[0, -1, 0], [1, 0, 0], [0, 0, 1]],
    ];
    for (const [nrm, u, v] of faces) {
      const ids = [];
      for (let iy = 0; iy <= seg; iy++) for (let ix = 0; ix <= seg; ix++) {
        const su = spread(ix / seg), sv = spread(iy / seg);
        const px = nrm[0] * w / 2 + u[0] * su * w / 2 + v[0] * sv * w / 2;
        const py = nrm[1] * h / 2 + u[1] * su * h / 2 + v[1] * sv * h / 2;
        const pz = nrm[2] * d / 2 + u[2] * su * d / 2 + v[2] * sv * d / 2;
        const qx = clamp(px, -bx, bx), qy = clamp(py, -by, by), qz = clamp(pz, -bz, bz);
        const l = Math.hypot(px - qx, py - qy, pz - qz) || 1;
        const nx = (px - qx) / l, ny = (py - qy) / l, nz = (pz - qz) / l;
        const x = qx + nx * r, y = qy + ny * r, z = qz + nz * r;
        const key = Math.round(x * 1e5) + ',' + Math.round(y * 1e5) + ',' + Math.round(z * 1e5);
        let id = index.get(key);
        if (id === undefined) { id = vert(m, x, y, z, nx, ny, nz, ix / seg, iy / seg); index.set(key, id); }
        ids.push(id);
      }
      const row = seg + 1;
      for (let iy = 0; iy < seg; iy++) for (let ix = 0; ix < seg; ix++) {
        const a = ids[iy * row + ix], b = ids[iy * row + ix + 1], c = ids[(iy + 1) * row + ix], e = ids[(iy + 1) * row + ix + 1];
        m.i.push(a, b, c, c, b, e);
      }
    }
    return m;
  }
  function box(recipe) {
    const size = vec3(recipe.size);
    const w = pos(size ? size[0] : recipe.w, 1), h = pos(size ? size[1] : recipe.h, 1), d = pos(size ? size[2] : recipe.d, 1);
    const bevel = num(recipe.bevel, num(recipe.r, 0));
    return bevel > 0.0005 ? roundedBoxData(w, h, d, bevel) : boxData(w, h, d);
  }

  // ------------------------------------------------------------------ revolved kinds
  const segOf = (recipe, d, lo) => clamp(Math.round(num(recipe.seg, d)), lo || 3, 128);
  const onAxis = p => p[0] < 1e-6;
  function cylinder(recipe) {
    const r = pos(recipe.r, 0.5), h = pos(recipe.h, 1), hh = h / 2, seg = segOf(recipe, 48);
    const top = Math.max(0, num(recipe.top, r));
    if (recipe.open) return revolve([[r, -hh], [top, hh]], seg, false);
    const bevel = Math.max(0, num(recipe.bevel, 0));
    let profile = top > 1e-6 ? [[0, -hh], [r, -hh], [top, hh], [0, hh]] : [[0, -hh], [r, -hh], [0, hh]];
    if (bevel > 0.0005) profile = fillet(profile, Math.min(bevel, Math.min(r, hh) * 0.45), false, 5, onAxis);
    return revolve(profile, seg, false);
  }
  function cone(recipe) { return cylinder(Object.assign({}, recipe, { top: num(recipe.top, 0) })); }
  function tube(recipe) {
    const r = pos(recipe.r, 0.5), inner = clamp(num(recipe.inner, r * 0.8), 1e-4, r - 1e-4), h = pos(recipe.h, 1), hh = h / 2;
    let profile = [[inner, -hh], [r, -hh], [r, hh], [inner, hh]];
    const bevel = Math.max(0, num(recipe.bevel, 0));
    if (bevel > 0.0005) profile = fillet(profile, Math.min(bevel, (r - inner) * 0.45, hh * 0.45), true, 4);
    return revolve(profile, segOf(recipe, 48, 8), true);
  }
  function lathe(recipe) {
    let points = pts2(recipe.profile || recipe.points);
    if (points.length < 2) points = [[0.4, -0.5], [0.5, -0.25], [0.5, 0.25], [0.4, 0.5]];
    const wall = num(recipe.wall, 0);
    const bevel = Math.max(0, num(recipe.bevel, 0));
    if (wall > 0) {
      let closed = withWall(points, wall);
      if (bevel > 0.0005) closed = fillet(closed, bevel, true, 3);
      return revolve(closed, segOf(recipe, 64, 8), true);
    }
    if (bevel > 0.0005) points = fillet(points, bevel, false, 4, onAxis);
    return revolve(points, segOf(recipe, 64, 8), false, num(recipe.smooth, 0.6));
  }
  function capsule(recipe) {
    const r = pos(recipe.r, 0.3), h = pos(recipe.h, 1), pts = [];
    for (let i = 0; i <= 10; i++) { const a = -Math.PI / 2 + (Math.PI / 2) * (i / 10); pts.push([Math.cos(a) * r, -h / 2 + Math.sin(a) * r]); }
    for (let i = 0; i <= 10; i++) { const a = (Math.PI / 2) * (i / 10); pts.push([Math.cos(a) * r, h / 2 + Math.sin(a) * r]); }
    pts[0][0] = 0; pts[pts.length - 1][0] = 0;
    return revolve(pts, segOf(recipe, 32, 8), false, 1.2);
  }
  function sphereData(r, seg, rings, dome) {
    const m = mesh(), phiMax = dome ? Math.PI / 2 : Math.PI;
    for (let iy = 0; iy <= rings; iy++) {
      const v = iy / rings, phi = v * phiMax, sp = Math.sin(phi), cp = Math.cos(phi);
      for (let ix = 0; ix <= seg; ix++) {
        const theta = (ix / seg) * TAU, x = r * Math.sin(theta) * sp, y = r * cp, z = r * Math.cos(theta) * sp;
        vert(m, x, y, z, x / r, y / r, z / r, ix / seg, 1 - v);
      }
    }
    const row = seg + 1;
    for (let iy = 0; iy < rings; iy++) for (let ix = 0; ix < seg; ix++) {
      const a = iy * row + ix, b = a + row, c = a + 1, d = b + 1;
      m.i.push(a, b, c, c, b, d);
    }
    if (dome) {
      const base = m.p.length / 3, center = vert(m, 0, 0, 0, 0, -1, 0, 0.5, 0.5);
      for (let ix = 0; ix <= seg; ix++) { const t = (ix / seg) * TAU; vert(m, r * Math.sin(t), 0, r * Math.cos(t), 0, -1, 0, 0, 0); }
      for (let ix = 0; ix < seg; ix++) m.i.push(center, base + 2 + ix, base + 1 + ix);
    }
    return m;
  }
  function sphere(recipe) {
    const r = pos(recipe.r, 0.5), seg = segOf(recipe, 48, 8);
    return sphereData(r, seg, clamp(Math.round(seg * 0.67), 6, 96), !!recipe.dome);
  }
  function torus(recipe) {
    const R = pos(recipe.r, 1), r = pos(recipe.tube, R * 0.2), arc = clamp(num(recipe.arc, 360), 1, 360) * DEG, start = num(recipe.start, 0) * DEG;
    const m = mesh(), radial = 24, tubular = clamp(Math.round(72 * arc / TAU), 6, 96);
    for (let j = 0; j <= radial; j++) {
      const v = (TAU * j) / radial, sv = Math.sin(v), cv = Math.cos(v);
      for (let i = 0; i <= tubular; i++) {
        const u = start + (arc * i) / tubular, su = Math.sin(u), cu = Math.cos(u);
        vert(m, (R + r * cv) * cu, r * sv, (R + r * cv) * su, cv * cu, sv, cv * su, i / tubular, j / radial);
      }
    }
    const row = tubular + 1;
    for (let j = 0; j < radial; j++) for (let i = 0; i < tubular; i++) {
      const a = j * row + i, b = a + row, c = a + 1, d = b + 1;
      m.i.push(a, b, c, c, b, d);
    }
    // Wound outward by construction (a→b→c crosses +y × +z = +x at the outer equator).
    if (arc >= TAU - 1e-6) return m;
    // An arc gets flat end caps, each facing away along the sweep.
    const ring = i => { const out = []; for (let j = 0; j < radial; j++) { const k = (j * row + i) * 3; out.push([m.p[k], m.p[k + 1], m.p[k + 2]]); } return out; };
    const facing = (loop, dir) => {
      const cap = capLoop(loop, false);
      if (cap.n[0] * dir[0] + cap.n[1] * dir[1] + cap.n[2] * dir[2] < 0) {
        for (let k = 0; k < cap.i.length; k += 3) { const t = cap.i[k + 1]; cap.i[k + 1] = cap.i[k + 2]; cap.i[k + 2] = t; }
        for (let k = 0; k < cap.n.length; k++) cap.n[k] = -cap.n[k];
      }
      return cap;
    };
    const end = start + arc;
    return merge([m, facing(ring(0), [Math.sin(start), 0, -Math.cos(start)]), facing(ring(tubular), [-Math.sin(end), 0, Math.cos(end)])]);
  }

  // ------------------------------------------------------------------ sweeps
  function catmull(points, t) {
    if (points.length < 3) {
      const a = points[0], b = points[points.length - 1];
      return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
    }
    const scaled = t * (points.length - 1), i = Math.min(points.length - 2, Math.floor(scaled)), f = scaled - i;
    const p0 = points[Math.max(0, i - 1)], p1 = points[i], p2 = points[i + 1], p3 = points[Math.min(points.length - 1, i + 2)];
    const f2 = f * f, f3 = f2 * f;
    return [0, 1, 2].map(k => 0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * f + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * f2 + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * f3));
  }
  function tubeAlong(points, radius, segments, radial, caps, smooth) {
    const pts = [];
    if (smooth === false) {
      // Straight runs with mitred corners: hydraulic lines, wires, frames.
      for (let i = 0; i < points.length - 1; i++) for (let s = 0; s < 4; s++) {
        const t = s / 4, a = points[i], b = points[i + 1];
        pts.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]);
      }
      pts.push(points[points.length - 1]);
    } else {
      for (let i = 0; i <= segments; i++) pts.push(catmull(points, i / segments));
    }
    const rings = [];
    let normal = null;
    const N = pts.length - 1;
    for (let i = 0; i <= N; i++) {
      const prev = pts[Math.max(0, i - 1)], next = pts[Math.min(N, i + 1)];
      const t = normalize(sub(next, prev));
      if (!normal) {
        const helper = Math.abs(t[1]) > 0.9 ? [1, 0, 0] : [0, 1, 0];
        normal = normalize(crossV(helper, t));
      } else {
        const d = normal[0] * t[0] + normal[1] * t[1] + normal[2] * t[2];
        normal = normalize([normal[0] - t[0] * d, normal[1] - t[1] * d, normal[2] - t[2] * d]);
      }
      const binormal = crossV(t, normal);
      const ring = [];
      for (let j = 0; j < radial; j++) {
        const a = (TAU * j) / radial, s = Math.sin(a), c = Math.cos(a);
        ring.push([pts[i][0] + (normal[0] * c + binormal[0] * s) * radius, pts[i][1] + (normal[1] * c + binormal[1] * s) * radius, pts[i][2] + (normal[2] * c + binormal[2] * s) * radius]);
      }
      rings.push(ring);
    }
    const parts = [gridMesh(rings, true)];
    if (caps !== false) {
      parts.push(capLoop(rings[0], false), capLoop(rings[N], true));
    }
    return orientOutward(merge(parts));
  }
  function pipe(recipe) {
    let points = pts3(recipe.points);
    if (points.length < 2) points = [[-0.8, 0, 0], [0, 0.35, 0], [0.8, 0, 0]];
    const radius = pos(recipe.r, 0.1), radial = clamp(Math.round(num(recipe.seg, 16)), 4, 32);
    const segments = clamp(points.length * 24, 24, 2400);
    return tubeAlong(points, radius, segments, radial, true, recipe.smooth !== false);
  }
  function spring(recipe) {
    const r = pos(recipe.r, 0.5), h = pos(recipe.h, 2), coils = Math.max(1, num(recipe.coils, 8)), wire = pos(recipe.wire, 0.06);
    const points = [], turns = Math.round(coils * 32);
    for (let i = 0; i <= turns; i++) {
      const t = i / turns, a = t * TAU * coils;
      points.push([r * Math.cos(a), -h / 2 + h * t, r * Math.sin(a)]);
    }
    return tubeAlong(points, wire, clamp(Math.round(coils * 40), 16, 2400), 12, true);
  }
  function arrow(recipe) {
    let points = (recipe.points || []).filter(p => Array.isArray(p) && p.length >= 2).map(p => [num(p[0], 0), num(p[1], 0), num(p[2], 0)]);
    if (points.length < 2) points = [[-0.8, 0, 0], [0.8, 0, 0]];
    const r = pos(recipe.r, 0.04), tip = points[points.length - 1], before = points[points.length - 2];
    const head = num(recipe.head, r * 5), headR = num(recipe.headR, r * 2.6);
    const dir = normalize(sub(tip, before));
    const neck = [tip[0] - dir[0] * head, tip[1] - dir[1] * head, tip[2] - dir[2] * head];
    const body = tubeAlong(points.slice(0, -1).concat([neck]), r, clamp(Math.round(points.length * 16), 16, 400), 12, true);
    const point = revolve([[0, -head / 2], [headR, -head / 2], [0, head / 2]], 20, false);
    turn(point, dir);
    translate(point, tip[0] - dir[0] * (head / 2), tip[1] - dir[1] * (head / 2), tip[2] - dir[2] * (head / 2));
    return merge([body, point]);
  }

  // ------------------------------------------------------------------ extrude family
  // Extrude an outline (and holes) along Z, centred, with an optional rounded bevel.
  function extrudeShape(outline, holes, depth, bevel, smoothAngle) {
    let outer = outline.slice();
    if (signedArea(outer) < 0) outer.reverse();
    const inner = holes.filter(h => h.length >= 3).map(h => (signedArea(h) > 0 ? h.slice().reverse() : h.slice()));
    const loops = [outer].concat(inner);
    const hz = depth / 2;
    const b = clamp(bevel || 0, 0, hz * 0.9);
    const steps = b > 0 ? 3 : 0;
    // Rings from back to front: [inward offset, z, normal weight on side, normal z].
    const rings = [];
    if (b > 0) {
      for (let k = 0; k <= steps; k++) { const t = (Math.PI / 2) * (1 - k / steps); rings.push([b * (1 - Math.cos(t)), -hz + b - b * Math.sin(t), Math.cos(t), -Math.sin(t)]); }
      for (let k = 0; k <= steps; k++) { const t = (Math.PI / 2) * (k / steps); rings.push([b * (1 - Math.cos(t)), hz - b + b * Math.sin(t), Math.cos(t), Math.sin(t)]); }
    } else {
      rings.push([0, -hz, 1, 0], [0, hz, 1, 0]);
    }
    const m = mesh();
    const sharp = num(smoothAngle, 32) * DEG;
    for (const loop of loops) {
      const n = loop.length;
      const offsets = rings.map(r => offsetLoop(loop, r[0]));
      const edgeN = [];
      for (let i = 0; i < n; i++) {
        const a = loop[i], c = loop[(i + 1) % n], dx = c[0] - a[0], dy = c[1] - a[1], l = Math.hypot(dx, dy) || 1;
        edgeN.push([dy / l, -dx / l]);
      }
      const sideN = (i, edge) => {
        const own = edgeN[edge], other = edgeN[edge === i ? (i - 1 + n) % n : (i + 1) % n];
        if (Math.acos(clamp(own[0] * other[0] + own[1] * other[1], -1, 1)) > sharp) return own;
        const v = [own[0] + other[0], own[1] + other[1]], l = Math.hypot(v[0], v[1]) || 1;
        return [v[0] / l, v[1] / l];
      };
      for (let i = 0; i < n; i++) {
        const j = (i + 1) % n, ni = sideN(i, i), nj = sideN(j, i);
        const base = m.p.length / 3;
        rings.forEach((r, k) => {
          const pi = offsets[k][i], pj = offsets[k][j];
          vert(m, pi[0], pi[1], r[1], ni[0] * r[2], ni[1] * r[2], r[3], i / n, k / (rings.length - 1));
          vert(m, pj[0], pj[1], r[1], nj[0] * r[2], nj[1] * r[2], r[3], j / n, k / (rings.length - 1));
        });
        for (let k = 0; k < rings.length - 1; k++) {
          const a = base + k * 2, c = a + 1, d = a + 2, e = a + 3;
          m.i.push(a, c, e, a, e, d);
        }
      }
    }
    // Caps on the fully inset outline.
    const cap = earcut(offsetLoop(outer, b), inner.map(h => offsetLoop(h, b)));
    const poly = cap.points, tri = cap.indices;
    for (const [z, sign] of [[hz, 1], [-hz, -1]]) {
      const base = m.p.length / 3;
      for (const p of poly) vert(m, p[0], p[1], z, 0, 0, sign, p[0], p[1]);
      for (let k = 0; k < tri.length; k += 3) {
        if (sign > 0) m.i.push(base + tri[k], base + tri[k + 1], base + tri[k + 2]);
        else m.i.push(base + tri[k], base + tri[k + 2], base + tri[k + 1]);
      }
    }
    return m;
  }
  function holeLoops(list, unit) {
    return (Array.isArray(list) ? list : []).map(h => {
      if (Array.isArray(h) && h.length === 3 && h.every(v => typeof v === 'number')) return circle(h[0], h[1], Math.abs(h[2]), 24);
      if (h && typeof h === 'object' && !Array.isArray(h) && Array.isArray(h.at)) return circle(num(h.at[0], 0), num(h.at[1], 0), pos(h.r, 0.05), 24);
      if (typeof h === 'string') return svgPoints(h, unit);
      return pts2(h);
    }).filter(h => h.length >= 3);
  }
  function svgPoints(d, unit) {
    const tokens = String(d).match(/[a-zA-Z]|-?\d*\.?\d+(?:e[-+]?\d+)?/g) || [];
    const out = [];
    let i = 0, x = 0, y = 0, sx = 0, sy = 0, cmd = '', lastC = null;
    const read = () => parseFloat(tokens[i++]);
    const push = (px, py) => out.push([px * unit, -py * unit]);
    while (i < tokens.length) {
      if (/[a-zA-Z]/.test(tokens[i])) cmd = tokens[i++];
      const rel = cmd === cmd.toLowerCase();
      const C = cmd.toUpperCase();
      if (C === 'M') { const nx = read(), ny = read(); x = rel ? x + nx : nx; y = rel ? y + ny : ny; sx = x; sy = y; push(x, y); cmd = rel ? 'l' : 'L'; lastC = null; }
      else if (C === 'L') { const nx = read(), ny = read(); x = rel ? x + nx : nx; y = rel ? y + ny : ny; push(x, y); lastC = null; }
      else if (C === 'H') { const nx = read(); x = rel ? x + nx : nx; push(x, y); lastC = null; }
      else if (C === 'V') { const ny = read(); y = rel ? y + ny : ny; push(x, y); lastC = null; }
      else if (C === 'C' || C === 'S') {
        let ax, ay;
        if (C === 'C') { const c1x = read(), c1y = read(); ax = rel ? x + c1x : c1x; ay = rel ? y + c1y : c1y; }
        else { ax = lastC ? 2 * x - lastC[0] : x; ay = lastC ? 2 * y - lastC[1] : y; }
        const c2x = read(), c2y = read(), nx = read(), ny = read();
        const bx = rel ? x + c2x : c2x, by = rel ? y + c2y : c2y, ex = rel ? x + nx : nx, ey = rel ? y + ny : ny;
        for (let s = 1; s <= 12; s++) {
          const t = s / 12, u = 1 - t;
          push(u * u * u * x + 3 * u * u * t * ax + 3 * u * t * t * bx + t * t * t * ex, u * u * u * y + 3 * u * u * t * ay + 3 * u * t * t * by + t * t * t * ey);
        }
        lastC = [bx, by]; x = ex; y = ey;
      } else if (C === 'Q' || C === 'T') {
        let ax, ay;
        if (C === 'Q') { const cx = read(), cy = read(); ax = rel ? x + cx : cx; ay = rel ? y + cy : cy; }
        else { ax = lastC ? 2 * x - lastC[0] : x; ay = lastC ? 2 * y - lastC[1] : y; }
        const nx = read(), ny = read(), ex = rel ? x + nx : nx, ey = rel ? y + ny : ny;
        for (let s = 1; s <= 12; s++) { const t = s / 12, u = 1 - t; push(u * u * x + 2 * u * t * ax + t * t * ex, u * u * y + 2 * u * t * ay + t * t * ey); }
        lastC = [ax, ay]; x = ex; y = ey;
      } else if (C === 'A') {
        // Elliptical arc, sampled through its centre parameterisation.
        let rx = Math.abs(read()), ry = Math.abs(read());
        const phi = read() * DEG, large = read() ? 1 : 0, sweep = read() ? 1 : 0, nx = read(), ny = read();
        const ex = rel ? x + nx : nx, ey = rel ? y + ny : ny;
        if (!rx || !ry) { x = ex; y = ey; push(x, y); continue; }
        const cp = Math.cos(phi), sp = Math.sin(phi);
        const dx = (x - ex) / 2, dy = (y - ey) / 2, x1 = cp * dx + sp * dy, y1 = -sp * dx + cp * dy;
        const lam = (x1 * x1) / (rx * rx) + (y1 * y1) / (ry * ry);
        if (lam > 1) { rx *= Math.sqrt(lam); ry *= Math.sqrt(lam); }
        const sign = large === sweep ? -1 : 1;
        const co = sign * Math.sqrt(Math.max(0, (rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1) / (rx * rx * y1 * y1 + ry * ry * x1 * x1)));
        const cx1 = (co * rx * y1) / ry, cy1 = (-co * ry * x1) / rx;
        const cx = cp * cx1 - sp * cy1 + (x + ex) / 2, cy = sp * cx1 + cp * cy1 + (y + ey) / 2;
        const ang = (ux, uy, vx, vy) => Math.atan2(ux * vy - uy * vx, ux * vx + uy * vy);
        const t1 = ang(1, 0, (x1 - cx1) / rx, (y1 - cy1) / ry);
        let dt = ang((x1 - cx1) / rx, (y1 - cy1) / ry, (-x1 - cx1) / rx, (-y1 - cy1) / ry);
        if (!sweep && dt > 0) dt -= TAU; else if (sweep && dt < 0) dt += TAU;
        const steps = Math.max(4, Math.ceil(Math.abs(dt) / (TAU / 32)));
        for (let s = 1; s <= steps; s++) {
          const t = t1 + (dt * s) / steps;
          push(cx + rx * Math.cos(t) * cp - ry * Math.sin(t) * sp, cy + rx * Math.cos(t) * sp + ry * Math.sin(t) * cp);
        }
        x = ex; y = ey; lastC = null;
      } else if (C === 'Z') { x = sx; y = sy; lastC = null; }
      else i++;
    }
    // Drop a closing duplicate of the first point.
    if (out.length > 2 && Math.hypot(out[0][0] - out[out.length - 1][0], out[0][1] - out[out.length - 1][1]) < 1e-9) out.pop();
    return out;
  }
  function extrude(recipe) {
    const unit = num(recipe.unit, 0.01);
    let points = [];
    if (Array.isArray(recipe.rect)) points = roundedRect(pos(recipe.rect[0], 1), pos(recipe.rect[1], 1), num(recipe.corner, 0), 6);
    else if (typeof recipe.d === 'string' && recipe.d.trim()) points = svgPoints(recipe.d, unit);
    else points = pts2(recipe.shape || recipe.points);
    if (points.length < 3) points = [[-0.3, -0.3], [0.3, -0.3], [0, 0.3]];
    return extrudeShape(points, holeLoops(recipe.holes, unit), pos(recipe.depth, 0.3), Math.max(0, num(recipe.bevel, 0)), recipe.smooth);
  }
  // A flat board in XZ (thickness along Y): PCBs, plates, panels, lids, cards.
  function plate(recipe) {
    const size = vec3(recipe.size);
    const w = pos(size ? size[0] : recipe.w, 1), h = pos(size ? size[1] : recipe.h, 0.05), d = pos(size ? size[2] : recipe.d, 0.7);
    const outline = roundedRect(w, d, num(recipe.corner, Math.min(w, d) * 0.04), 6);
    const holes = holeLoops(recipe.holes, 1).map(loop => loop.map(p => [p[0], -p[1]]));
    const m = extrudeShape(outline, holes, h, Math.max(0, num(recipe.bevel, h * 0.18)));
    // Extruded along Z with Y as depth; lay it flat so thickness runs along Y.
    return transform(m, axisAngle([1, 0, 0], -Math.PI / 2));
  }
  function gear(recipe) {
    const R = pos(recipe.r, 1), w = pos(recipe.w, 0.3), teeth = clamp(Math.round(num(recipe.teeth, 16)), 6, 200);
    const tooth = num(recipe.tooth, 0.14) * R, root = R - tooth / 2, tip = R + tooth / 2;
    const pts = [], step = TAU / teeth;
    for (let i = 0; i < teeth; i++) {
      const a = i * step;
      // A flank that bulges like an involute: root, two flank points, tip land, mirrored.
      const flank = [[0.0, root], [0.12, root + tooth * 0.35], [0.2, root + tooth * 0.78], [0.27, tip], [0.47, tip], [0.54, root + tooth * 0.78], [0.62, root + tooth * 0.35], [0.74, root]];
      for (const [f, rad] of flank) pts.push([Math.cos(a + step * f) * rad, Math.sin(a + step * f) * rad]);
    }
    const holes = [];
    const hole = num(recipe.hole, 0);
    if (hole > 0) holes.push(circle(0, 0, Math.min(hole, root * 0.9), 32).reverse());
    return extrudeShape(pts, holes, w, num(recipe.bevel, Math.min(w * 0.12, tooth * 0.15)), 50);
  }

  // ------------------------------------------------------------------ aero & machine parts
  // Symmetric NACA 00xx half-thickness at x in [0, 1].
  const nacaThickness = (x, t) => 5 * t * (0.2969 * Math.sqrt(x) - 0.126 * x - 0.3516 * x * x + 0.2843 * x * x * x - 0.1036 * x * x * x * x);
  function airfoilLoop(chord, thick, camber, count) {
    // Cosine spacing bunches points at the leading edge. Loop: upper TE→LE, lower LE→TE.
    const loop = [], p = 0.4;
    const line = x => (x < p ? (camber / (p * p)) * (2 * p * x - x * x) : (camber / ((1 - p) * (1 - p))) * (1 - 2 * p + 2 * p * x - x * x));
    for (let k = count; k >= 0; k--) { const x = 0.5 * (1 - Math.cos((Math.PI * k) / count)); loop.push([x * chord, (line(x) + nacaThickness(x, thick)) * chord]); }
    for (let k = 1; k < count; k++) { const x = 0.5 * (1 - Math.cos((Math.PI * k) / count)); loop.push([x * chord, (line(x) - nacaThickness(x, thick)) * chord]); }
    return loop;
  }
  // Fans, compressors, turbines, propellers: a hub with N twisted airfoil blades about Y.
  function rotor(recipe) {
    const r = pos(recipe.r, 0.5), hub = clamp(num(recipe.hub, r * 0.3), 0.01, r * 0.95);
    const count = clamp(Math.round(num(recipe.blades, 12)), 1, 96);
    const chord = pos(recipe.chord, Math.min(0.6 * (TAU * (hub + r) / 2) / count * 1.6, (r - hub) * 0.8));
    const thick = clamp(num(recipe.thick, 0.1), 0.02, 0.4);
    const pitch = num(recipe.pitch, 40) * DEG, twist = num(recipe.twist, 25) * DEG;
    const taper = clamp(num(recipe.taper, 0.75), 0.1, 2), sweep = num(recipe.sweep, 0) * DEG;
    const camber = clamp(num(recipe.camber, 0.04), 0, 0.1);
    const hubH = pos(recipe.h, chord * 1.3);
    const stations = 9, loopN = 9;
    const section = airfoilLoop(1, thick, camber, loopN);
    const parts = [];
    for (let b = 0; b < count; b++) {
      const phi = (TAU * b) / count;
      const R = [Math.sin(phi), 0, Math.cos(phi)], T = [Math.cos(phi), 0, -Math.sin(phi)], A = [0, 1, 0];
      const rows = [];
      for (let s = 0; s <= stations; s++) {
        const f = s / stations, rho = hub * 0.92 + (r - hub * 0.92) * f;
        const c = chord * (1 + (taper - 1) * f);
        const beta = pitch + twist * (1 - f) - twist / 2;
        const cd = [T[0] * Math.cos(beta) + A[0] * Math.sin(beta), T[1] * Math.cos(beta) + A[1] * Math.sin(beta), T[2] * Math.cos(beta) + A[2] * Math.sin(beta)];
        const td = [-T[0] * Math.sin(beta) + A[0] * Math.cos(beta), -T[1] * Math.sin(beta) + A[1] * Math.cos(beta), -T[2] * Math.sin(beta) + A[2] * Math.cos(beta)];
        const back = Math.tan(sweep) * (rho - hub);
        rows.push(section.map(([u, v]) => {
          const uu = (u - 0.35) * c + back, vv = v * c;
          return [R[0] * rho + cd[0] * uu + td[0] * vv, R[1] * rho + cd[1] * uu + td[1] * vv, R[2] * rho + cd[2] * uu + td[2] * vv];
        }));
      }
      parts.push(orientOutward(merge([gridMesh(rows, true), capLoop(rows[0], false), capLoop(rows[rows.length - 1], true)])));
    }
    if (recipe.hubless !== true) {
      let profile = [[0, -hubH / 2], [hub, -hubH / 2], [hub, hubH / 2], [0, hubH / 2]];
      if (recipe.spinner) {
        const len = num(recipe.spinner === true ? hub * 1.6 : recipe.spinner, hub * 1.6);
        profile = [[0, -hubH / 2], [hub, -hubH / 2], [hub, hubH / 2]];
        for (let k = 1; k <= 8; k++) { const t = k / 8; profile.push([hub * Math.cos(t * Math.PI / 2), hubH / 2 + len * Math.sin(t * Math.PI / 2)]); }
      }
      parts.push(revolve(fillet(profile, hub * 0.08, false, 3, onAxis), 40, false));
    }
    return merge(parts);
  }
  // A wing panel: root at x=0, span along +X, chord along -Z (leading edge toward +Z), thickness Y.
  function airfoil(recipe) {
    const chord = pos(recipe.chord, 1), span = pos(recipe.span, 2), thick = clamp(num(recipe.thick, 0.12), 0.02, 0.4);
    const camber = clamp(num(recipe.camber, 0.02), 0, 0.1), taper = clamp(num(recipe.taper, 0.6), 0.05, 2);
    const sweep = num(recipe.sweep, 15) * DEG, dihedral = num(recipe.dihedral, 0) * DEG, twist = num(recipe.twist, 0) * DEG;
    const stations = 12, section = airfoilLoop(1, thick, camber, 14), rows = [];
    for (let s = 0; s <= stations; s++) {
      const f = s / stations, x = span * f, c = chord * (1 + (taper - 1) * f), a = twist * f;
      const le = -Math.tan(sweep) * x, y0 = Math.tan(dihedral) * x;
      rows.push(section.map(([u, v]) => {
        const zz = -u * c, yy = v * c;
        return [x, y0 + yy * Math.cos(a) - zz * Math.sin(a), le + zz * Math.cos(a) + yy * Math.sin(a) + chord * 0.3];
      }));
    }
    return orientOutward(merge([gridMesh(rows, true), capLoop(rows[0], false), capLoop(rows[stations], true)]));
  }
  // Superellipse sections along Z: car bodies, fuselages, hulls, bottles on their side, fish, bones.
  // sections: [[z, width, height, roundness (2 ellipse … 8 boxy), yOffset], ...]
  function loft(recipe) {
    let sections = (Array.isArray(recipe.sections) ? recipe.sections : []).filter(s => Array.isArray(s) && s.length >= 3 && s.slice(0, 3).every(isFinite));
    if (sections.length < 2) sections = [[-0.8, 0.2, 0.2, 2], [-0.4, 0.6, 0.5, 3], [0.4, 0.6, 0.5, 3], [0.8, 0.3, 0.3, 2]];
    sections = sections.map(s => [+s[0], Math.max(0, +s[1]), Math.max(0, +s[2]), clamp(num(s[3], 2.5), 1.2, 12), num(s[4], 0), num(s[5], 0)]).sort((a, b) => a[0] - b[0]);
    const around = clamp(Math.round(num(recipe.seg, 40)), 8, 96), sub = clamp(Math.round(num(recipe.smooth, 4)), 1, 8);
    // Catmull-Rom between sections so the body flows instead of kinking at each section.
    const sample = t => catmull(sections.map(s => [s[0], s[1], s[2]]), t).concat(catmull(sections.map(s => [s[3], s[4], s[5]]), t));
    const rows = [], total = (sections.length - 1) * sub;
    for (let k = 0; k <= total; k++) {
      const [z, w, h, e, dy, dx] = sample(k / total), loop = [];
      for (let j = 0; j < around; j++) {
        const a = (TAU * j) / around, c = Math.cos(a), s = Math.sin(a);
        const px = (Math.max(w, 1e-4) / 2) * Math.sign(c) * Math.pow(Math.abs(c), 2 / e);
        const py = (Math.max(h, 1e-4) / 2) * Math.sign(s) * Math.pow(Math.abs(s), 2 / e);
        loop.push([px + dx, py + dy, z]);
      }
      rows.push(loop);
    }
    return orientOutward(merge([gridMesh(rows, true), capLoop(rows[0], false), capLoop(rows[total], true)]));
  }
  // Tyre about Y: r is the outer radius, inner the bead seat, w the width.
  function tire(recipe) {
    const r = pos(recipe.r, 0.5), w = pos(recipe.w, r * 0.5), inner = clamp(num(recipe.inner, r * 0.62), 0.01, r * 0.98), hw = w / 2;
    const profile = fillet([[inner, -hw * 0.85], [r - (r - inner) * 0.05, -hw], [r, -hw * 0.6], [r, hw * 0.6], [r - (r - inner) * 0.05, hw], [inner, hw * 0.85]], Math.min(hw, r - inner) * 0.45, true, 5);
    const body = revolve(profile, segOf(recipe, 56, 12), true, 0.9);
    const grooves = Math.round(num(recipe.tread, 0));
    if (grooves <= 0) return body;
    // Tread blocks: shallow boxes around the crown.
    const blocks = [];
    for (let i = 0; i < grooves; i++) {
      const a = (TAU * i) / grooves;
      const blk = roundedBoxData((TAU * r / grooves) * 0.55, w * 0.82, (r - inner) * 0.12, (r - inner) * 0.04);
      transform(blk, axisAngle([0, 1, 0], a), [Math.sin(a) * r, 0, Math.cos(a) * r]);
      blocks.push(blk);
    }
    return merge([body].concat(blocks));
  }
  // Wheel rim about Y: a barrel, a hub, and spokes.
  function rim(recipe) {
    const r = pos(recipe.r, 0.32), w = pos(recipe.w, r * 0.7), hw = w / 2, hub = clamp(num(recipe.hub, r * 0.22), 0.01, r * 0.8);
    const spokes = clamp(Math.round(num(recipe.spokes, 5)), 0, 40), seg = segOf(recipe, 48, 12);
    const lip = r * 0.06;
    const barrel = revolve(fillet([[r - lip, -hw], [r + lip * 0.4, -hw], [r + lip * 0.4, -hw + lip], [r, -hw + lip * 1.5], [r, hw - lip * 1.5], [r + lip * 0.4, hw - lip], [r + lip * 0.4, hw], [r - lip, hw]], lip * 0.4, true, 2), seg, true);
    const hubPart = revolve(fillet([[0, -hw * 0.5], [hub, -hw * 0.5], [hub, hw * 0.55], [hub * 0.4, hw * 0.7], [0, hw * 0.7]], hub * 0.2, false, 3, onAxis), 32, false);
    const parts = [barrel, hubPart];
    const sw = Math.max(0.01, num(recipe.spokeWidth, r * 0.16)), st = num(recipe.spokeThick, w * 0.18);
    for (let i = 0; i < spokes; i++) {
      const a = (TAU * i) / spokes, len = r - lip - hub * 0.8;
      const s = roundedBoxData(sw, st, len, Math.min(sw, st) * 0.35);
      translate(s, 0, hw * 0.45, hub * 0.8 + len / 2);
      transform(s, axisAngle([0, 1, 0], a));
      parts.push(s);
    }
    return merge(parts);
  }

  // ------------------------------------------------------------------ surface grid
  function surface(recipe) {
    const rows = recipe.grid || recipe.rows || [];
    const R = rows.length, C = R && Array.isArray(rows[0]) ? rows[0].length : 0;
    if (R < 2 || C < 2) return transform(boxData(1, 0.001, 1), [1, 0, 0, 0, 1, 0, 0, 0, 1]);
    const grid = [];
    for (let r = 0; r < R; r++) {
      const row = [];
      for (let c = 0; c < C; c++) { const p = rows[r][c] || [0, 0, 0]; row.push([num(p[0], 0), num(p[1], 0), num(p[2], 0)]); }
      grid.push(row);
    }
    return gridMesh(grid, false);
  }

  // ------------------------------------------------------------------ polyhedra
  function polyhedron(recipe) {
    const faces = Math.round(num(recipe.faces, 20)), detail = clamp(Math.round(num(recipe.detail, 0)), 0, 3), r = pos(recipe.r, 0.5);
    let verts, tris;
    if (faces === 4) { verts = [[1, 1, 1], [-1, -1, 1], [-1, 1, -1], [1, -1, -1]]; tris = [[0, 1, 2], [0, 3, 1], [0, 2, 3], [1, 3, 2]]; }
    else if (faces === 6) return boxData(r * 1.15, r * 1.15, r * 1.15);
    else if (faces === 8) {
      verts = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]];
      tris = [[0, 2, 4], [0, 4, 3], [0, 3, 5], [0, 5, 2], [1, 4, 2], [1, 3, 4], [1, 5, 3], [1, 2, 5]];
    } else {
      const t = (1 + Math.sqrt(5)) / 2;
      verts = [[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]];
      tris = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]];
    }
    let work = tris.map(t => t.map(i => normalize(verts[i])));
    for (let d = 0; d < detail; d++) {
      const next = [];
      for (const [a, b, c] of work) {
        const ab = normalize([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2]);
        const bc = normalize([(b[0] + c[0]) / 2, (b[1] + c[1]) / 2, (b[2] + c[2]) / 2]);
        const ca = normalize([(c[0] + a[0]) / 2, (c[1] + a[1]) / 2, (c[2] + a[2]) / 2]);
        next.push([a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]);
      }
      work = next;
    }
    // Faceted: each face keeps its own flat normal, which is what a crystal or die looks like.
    const m = mesh();
    for (const [a, b, c] of work) {
      const f = normalize(crossV(sub(b, a), sub(c, a)));
      const base = m.p.length / 3;
      for (const p of [a, b, c]) vert(m, p[0] * r, p[1] * r, p[2] * r, f[0], f[1], f[2], 0, 0);
      m.i.push(base, base + 1, base + 2);
    }
    return orientOutward(m);
  }

  // ------------------------------------------------------------------ metaballs
  function blob(recipe) {
    const balls = (recipe.balls || []).map(b => (Array.isArray(b) ? { at: b.slice(0, 3), r: num(b[3], 0.5) } : b)).filter(b => b && vec3(b.at));
    const sticks = (recipe.sticks || []).map(s => (Array.isArray(s) ? { from: s[0], to: s[1], r: num(s[2], 0.2), r2: num(s[3], num(s[2], 0.2)) } : s)).filter(s => s && vec3(s.from) && vec3(s.to));
    if (!balls.length && !sticks.length) return sphereData(pos(recipe.r, 0.5), 40, 26, false);
    const k = Math.max(0, num(recipe.blend, 0.12));
    // Polynomial smooth-min: neighbouring balls fuse into one organic surface.
    const smin = (a, b) => { if (k <= 0) return Math.min(a, b); const h = clamp(0.5 + (0.5 * (b - a)) / k, 0, 1); return b + (a - b) * h - k * h * (1 - h); };
    const dist = (x, y, z) => {
      let best = 1e9;
      for (const b of balls) best = smin(best, Math.hypot(x - b.at[0], y - b.at[1], z - b.at[2]) - pos(b.r, 0.5));
      for (const s of sticks) {
        const bx = s.to[0] - s.from[0], by = s.to[1] - s.from[1], bz = s.to[2] - s.from[2];
        const px = x - s.from[0], py = y - s.from[1], pz = z - s.from[2];
        const t = clamp((px * bx + py * by + pz * bz) / (bx * bx + by * by + bz * bz || 1), 0, 1);
        best = smin(best, Math.hypot(px - bx * t, py - by * t, pz - bz * t) - (pos(s.r, 0.2) + (pos(s.r2, s.r) - pos(s.r, 0.2)) * t));
      }
      return best;
    };
    const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
    const grow = (p, r) => { for (let i = 0; i < 3; i++) { lo[i] = Math.min(lo[i], p[i] - r - k); hi[i] = Math.max(hi[i], p[i] + r + k); } };
    balls.forEach(b => grow(b.at, b.r));
    sticks.forEach(s => { grow(s.from, Math.max(s.r, s.r2 || 0)); grow(s.to, Math.max(s.r, s.r2 || 0)); });
    // Resolution follows the smallest feature, capped by the vertex budget (the fix §3.4 asks for).
    const smallest = Math.min(...balls.map(b => b.r), ...sticks.map(s => Math.min(s.r, s.r2 || s.r)));
    const extent = Math.max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], 1e-3);
    const step = Math.max(extent / 48, Math.min(smallest / 4, extent / 28));
    const dims = [0, 1, 2].map(i => Math.max(2, Math.ceil((hi[i] - lo[i]) / step) + 2));
    const at = (i, j, kk) => i + dims[0] * (j + dims[1] * kk);
    const field = new Float32Array(dims[0] * dims[1] * dims[2]);
    for (let kk = 0; kk < dims[2]; kk++) for (let j = 0; j < dims[1]; j++) for (let i = 0; i < dims[0]; i++) field[at(i, j, kk)] = dist(lo[0] + i * step, lo[1] + j * step, lo[2] + kk * step);
    // Surface nets: one vertex per crossing cell, quads across each sign-changing edge.
    const m = mesh(), cellVert = new Int32Array(dims[0] * dims[1] * dims[2]).fill(-1);
    const corners = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [0, 0, 1], [1, 0, 1], [0, 1, 1], [1, 1, 1]];
    const edges = [[0, 1], [2, 3], [4, 5], [6, 7], [0, 2], [1, 3], [4, 6], [5, 7], [0, 4], [1, 5], [2, 6], [3, 7]];
    const e = step * 0.5;
    for (let kk = 0; kk < dims[2] - 1; kk++) for (let j = 0; j < dims[1] - 1; j++) for (let i = 0; i < dims[0] - 1; i++) {
      const v = corners.map(c => field[at(i + c[0], j + c[1], kk + c[2])]);
      let inside = 0;
      for (const f of v) if (f < 0) inside++;
      if (inside === 0 || inside === 8) continue;
      let sx = 0, sy = 0, sz = 0, count = 0;
      for (const [a, b] of edges) {
        if ((v[a] < 0) === (v[b] < 0)) continue;
        const t = v[a] / (v[a] - v[b]);
        sx += corners[a][0] + (corners[b][0] - corners[a][0]) * t;
        sy += corners[a][1] + (corners[b][1] - corners[a][1]) * t;
        sz += corners[a][2] + (corners[b][2] - corners[a][2]) * t;
        count++;
      }
      const x = lo[0] + (i + sx / count) * step, y = lo[1] + (j + sy / count) * step, z = lo[2] + (kk + sz / count) * step;
      const g = normalize([dist(x + e, y, z) - dist(x - e, y, z), dist(x, y + e, z) - dist(x, y - e, z), dist(x, y, z + e) - dist(x, y, z - e)]);
      cellVert[at(i, j, kk)] = vert(m, x, y, z, g[0], g[1], g[2], 0, (y - lo[1]) / (hi[1] - lo[1] || 1));
    }
    const quad = (a, b, c, d, flip) => {
      if (a < 0 || b < 0 || c < 0 || d < 0) return;
      if (flip) m.i.push(a, c, b, a, d, c); else m.i.push(a, b, c, a, c, d);
    };
    for (let kk = 1; kk < dims[2] - 1; kk++) for (let j = 1; j < dims[1] - 1; j++) for (let i = 1; i < dims[0] - 1; i++) {
      const here = field[at(i, j, kk)] < 0;
      // Edge along +x from (i,j,k): the four cells sharing it.
      if (here !== (field[at(i + 1, j, kk)] < 0)) quad(cellVert[at(i, j - 1, kk - 1)], cellVert[at(i, j, kk - 1)], cellVert[at(i, j, kk)], cellVert[at(i, j - 1, kk)], !here);
      if (here !== (field[at(i, j + 1, kk)] < 0)) quad(cellVert[at(i - 1, j, kk - 1)], cellVert[at(i - 1, j, kk)], cellVert[at(i, j, kk)], cellVert[at(i, j, kk - 1)], !here);
      if (here !== (field[at(i, j, kk + 1)] < 0)) quad(cellVert[at(i - 1, j - 1, kk)], cellVert[at(i, j - 1, kk)], cellVert[at(i, j, kk)], cellVert[at(i - 1, j, kk)], !here);
    }
    return orientOutward(m, true);
  }

  // ------------------------------------------------------------------ the kernel
  const SHAPES = {
    box, cyl: cylinder, cylinder, cone, tube, arrow, lathe, sphere, torus, capsule, pipe, spring, gear, extrude, blob,
    poly: polyhedron, surface, plate, rotor, airfoil, loft, tire, rim,
  };
  const KINDS = Object.keys(SHAPES);

  function axisVector(axis) {
    if (typeof axis === 'string') {
      const m = /^\s*([+-]?)\s*([xyz])\s*$/i.exec(axis);
      if (!m) return null;
      const s = m[1] === '-' ? -1 : 1, k = m[2].toLowerCase();
      return k === 'x' ? [s, 0, 0] : k === 'z' ? [0, 0, s] : [0, s, 0];
    }
    const v = vec3(axis);
    return v && Math.hypot(v[0], v[1], v[2]) > 1e-6 ? normalize(v) : null;
  }

  function build(kind, recipe) {
    const make = SHAPES[kind];
    if (!make) throw new Error('Clicky3D: unknown part "' + kind + '"');
    recipe = recipe || {};
    const m = make(recipe);
    if (m.p.length / 3 > MAX_VERTICES) throw new Error('Clicky3D: part too detailed (' + m.p.length / 3 + ' vertices)');
    const axis = axisVector(recipe.axis);
    if (axis && !(axis[1] === 1)) turn(m, axis);
    if (Array.isArray(recipe.stretch) && recipe.stretch.length >= 3) stretchMesh(m, num(recipe.stretch[0], 1), num(recipe.stretch[1], 1), num(recipe.stretch[2], 1));
    const geometry = finish(m);
    // Framing samples: the axis extremes plus an even spread, at most 600.
    const count = geometry.positions.length / 3;
    let samples;
    if (count <= 600) samples = geometry.positions;
    else {
      const picks = [];
      for (let i = 0; i < 594; i++) picks.push(Math.floor((i / 594) * count));
      for (let a = 0; a < 3; a++) {
        let hiI = 0, loI = 0;
        for (let i = 0; i < count; i++) {
          if (geometry.positions[i * 3 + a] > geometry.positions[hiI * 3 + a]) hiI = i;
          if (geometry.positions[i * 3 + a] < geometry.positions[loI * 3 + a]) loI = i;
        }
        picks.push(hiI, loI);
      }
      samples = new Float32Array(picks.length * 3);
      picks.forEach((i, k) => { samples[k * 3] = geometry.positions[i * 3]; samples[k * 3 + 1] = geometry.positions[i * 3 + 1]; samples[k * 3 + 2] = geometry.positions[i * 3 + 2]; });
    }
    geometry.samples = samples;
    return geometry;
  }

  return { kinds: KINDS, build, svgPoints, roundedRect };
})();
