/* Clicky3D geometry: the 16 part recipes, built into typed arrays the renderer draws.
   Plain arrays in, interleaved buffers out; meshes are cached by canonical recipe. */
const Clicky3DGeometry = (() => {
  'use strict';

  const TAU = Math.PI * 2;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const num = (v, d) => (typeof v === 'number' && isFinite(v) ? v : d);
  const pos = (v, d) => Math.max(1e-4, num(v, d));
  const vec3 = v => (Array.isArray(v) && v.length >= 3 && v.every(n => typeof n === 'number' && isFinite(n)) ? [v[0], v[1], v[2]] : null);

  function mesh() {
    return { p: [], n: [], uv: [], i: [] };
  }
  function vert(m, x, y, z, nx, ny, nz, u, v) {
    const at = m.p.length / 3;
    m.p.push(x, y, z);
    m.n.push(nx, ny, nz);
    m.uv.push(u || 0, v || 0);
    return at;
  }
  // Every primitive returns flat arrays; the renderer uploads them once per recipe.
  function finish(m) {
    return {
      positions: new Float32Array(m.p),
      normals: new Float32Array(m.n),
      uvs: new Float32Array(m.uv),
      indices: new Uint32Array(m.i),
    };
  }

  // ------------------------------------------------------------------ box
  function boxFace(m, o, u, v, n) {
    const a = vert(m, o[0], o[1], o[2], n[0], n[1], n[2], 0, 0);
    const b = vert(m, o[0] + u[0], o[1] + u[1], o[2] + u[2], n[0], n[1], n[2], 1, 0);
    const c = vert(m, o[0] + v[0], o[1] + v[1], o[2] + v[2], n[0], n[1], n[2], 0, 1);
    const d = vert(m, o[0] + u[0] + v[0], o[1] + u[1] + v[1], o[2] + u[2] + v[2], n[0], n[1], n[2], 1, 1);
    m.i.push(a, b, c, c, b, d);
  }
  function boxData(w, h, d) {
    const m = mesh(), x = w / 2, y = h / 2, z = d / 2;
    boxFace(m, [-x, -y, z], [w, 0, 0], [0, h, 0], [0, 0, 1]);
    boxFace(m, [x, -y, -z], [0, 0, -d], [0, h, 0], [1, 0, 0]);
    boxFace(m, [-x, -y, -z], [0, 0, d], [0, h, 0], [-1, 0, 0]);
    boxFace(m, [-x, y, z], [w, 0, 0], [0, 0, -d], [0, 1, 0]);
    boxFace(m, [-x, -y, -z], [w, 0, 0], [0, 0, d], [0, -1, 0]);
    boxFace(m, [-x, -y, -z], [w, 0, 0], [0, h, 0], [0, 0, -1]);
    return m;
  }
  // A segmented, indexed cube — the base RoundedBoxGeometry remaps. seg 7 gives the shipped 1,764.
  function boxGrid(w, h, d, seg) {
    const m = mesh(), x = w / 2, y = h / 2, z = d / 2;
    for (let iy = 0; iy <= seg; iy++) {
      for (let ix = 0; ix <= seg; ix++) {
        vert(m, -x + (w * ix) / seg, -y + (h * iy) / seg, z, 0, 0, 1, ix / seg, iy / seg);
      }
    }
    for (let iy = 0; iy <= seg; iy++) {
      for (let ix = 0; ix <= seg; ix++) {
        vert(m, x, -y + (h * iy) / seg, z - (d * ix) / seg, 1, 0, 0, ix / seg, iy / seg);
      }
    }
    for (let iy = 0; iy <= seg; iy++) {
      for (let ix = 0; ix <= seg; ix++) {
        vert(m, -x, -y + (h * iy) / seg, -z + (d * ix) / seg, -1, 0, 0, ix / seg, iy / seg);
      }
    }
    for (let iy = 0; iy <= seg; iy++) {
      for (let ix = 0; ix <= seg; ix++) {
        vert(m, -x + (w * ix) / seg, y, z - (d * iy) / seg, 0, 1, 0, ix / seg, iy / seg);
      }
    }
    for (let iy = 0; iy <= seg; iy++) {
      for (let ix = 0; ix <= seg; ix++) {
        vert(m, -x + (w * ix) / seg, -y, -z + (d * iy) / seg, 0, -1, 0, ix / seg, iy / seg);
      }
    }
    for (let iy = 0; iy <= seg; iy++) {
      for (let ix = 0; ix <= seg; ix++) {
        vert(m, -x + (w * ix) / seg, -y + (h * iy) / seg, -z, 0, 0, -1, ix / seg, iy / seg);
      }
    }
    const row = seg + 1, face = row * row;
    for (let f = 0; f < 6; f++) {
      const base = f * face;
      // Winding follows the face normal baked into the grid, not a per-face guess.
      const intended = [m.n[base * 3], m.n[base * 3 + 1], m.n[base * 3 + 2]];
      const tri = (k) => [m.p[k * 3], m.p[k * 3 + 1], m.p[k * 3 + 2]];
      const A = tri(base), B = tri(base + 1), C = tri(base + row);
      const e1 = [B[0] - A[0], B[1] - A[1], B[2] - A[2]];
      const e2 = [C[0] - A[0], C[1] - A[1], C[2] - A[2]];
      const geo = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
      const forward = geo[0] * intended[0] + geo[1] * intended[1] + geo[2] * intended[2] >= 0;
      for (let iy = 0; iy < seg; iy++) {
        for (let ix = 0; ix < seg; ix++) {
          const a = base + iy * row + ix, b = a + 1, c = a + row, d = c + 1;
          if (forward) m.i.push(a, b, c, c, b, d);
          else m.i.push(a, c, b, b, c, d);
        }
      }
    }
    return m;
  }
  function roundedBoxData(w, h, d, radius) {
    const r = clamp(num(radius, 0.04), 0.0005, 0.45 * Math.min(w, h, d));
    const seg = 7;
    const grid = boxGrid(w, h, d, seg);
    const bx = w / 2 - r, by = h / 2 - r, bz = d / 2 - r;
    const out = mesh();
    // BoxGeometry is indexed; rounded boxes are expanded so no vertex is shared.
    for (let k = 0; k < grid.i.length; k++) {
      const at = grid.i[k] * 3;
      const px = grid.p[at], py = grid.p[at + 1], pz = grid.p[at + 2];
      const qx = clamp(px, -bx, bx), qy = clamp(py, -by, by), qz = clamp(pz, -bz, bz);
      let nx = px - qx, ny = py - qy, nz = pz - qz;
      const l = Math.hypot(nx, ny, nz) || 1;
      nx /= l; ny /= l; nz /= l;
      out.p.push(qx + nx * r, qy + ny * r, qz + nz * r);
      out.n.push(nx, ny, nz);
      out.uv.push(0, 0);
      out.i.push(k);
    }
    return out;
  }
  function box(recipe) {
    const size = vec3(recipe.size);
    const w = pos(size ? size[0] : recipe.w, 1), h = pos(size ? size[1] : recipe.h, 1), d = pos(size ? size[2] : recipe.d, 1);
    const bevel = num(recipe.bevel, num(recipe.r, 0));
    return bevel > 0.0005 ? roundedBoxData(w, h, d, bevel) : boxData(w, h, d);
  }

  // ------------------------------------------------------------------ lathe family
  function latheData(points, seg, thetaStart, thetaLength) {
    const m = mesh(), n = points.length;
    const start = num(thetaStart, 0), len = num(thetaLength, TAU);
    for (let j = 0; j < n; j++) {
      const [px, py] = points[j];
      const prev = points[Math.max(0, j - 1)], next = points[Math.min(n - 1, j + 1)];
      let dx = next[0] - prev[0], dy = next[1] - prev[1];
      const l = Math.hypot(dx, dy) || 1;
      dx /= l; dy /= l;
      for (let i = 0; i <= seg; i++) {
        const a = start + (len * i) / seg, s = Math.sin(a), c = Math.cos(a);
        vert(m, px * s, py, px * c, dy * s, -dx, dy * c, i / seg, j / (n - 1 || 1));
      }
    }
    for (let j = 0; j < n - 1; j++) {
      for (let i = 0; i < seg; i++) {
        const a = j * (seg + 1) + i, b = a + seg + 1, c = a + 1, d = b + 1;
        m.i.push(a, c, b, b, c, d);
      }
    }
    return m;
  }
  function lathe(recipe) {
    let points = (recipe.profile || recipe.points || []).filter(p => Array.isArray(p) && p.length >= 2 && isFinite(p[0]) && isFinite(p[1])).map(p => [+p[0], +p[1]]);
    if (points.length < 2) points = [[0.4, -0.5], [0.5, -0.25], [0.5, 0.25], [0.4, 0.5]];
    return latheData(points, clamp(Math.round(num(recipe.seg, 64)), 3, 128), 0, TAU);
  }
  function cylinderProfile(r, top, h, bevel) {
    const hh = h / 2, rt = top === undefined ? r : num(top, r);
    if (bevel <= 0.0005) return [[0, -hh], [r, -hh], [rt, hh], [0, hh]];
    const b = Math.min(bevel, Math.min(r, hh) * 0.45);
    const pts = [[0, -hh], [r - b, -hh]];
    for (let i = 0; i <= 4; i++) {
      const t = i / 4, u = 1 - t;
      pts.push([r - b + b * Math.sin((t * Math.PI) / 2), -hh + b - b * Math.cos((t * Math.PI) / 2)]);
    }
    if (rt > 0.0005) {
      pts.push([rt, hh - b]);
      for (let i = 0; i <= 4; i++) {
        const t = i / 4;
        pts.push([rt - b + b * Math.cos((t * Math.PI) / 2), hh - b + b * Math.sin((t * Math.PI) / 2)]);
      }
      pts.push([0, hh]);
    } else {
      pts.push([0, hh]);
    }
    return pts;
  }
  function cylinder(recipe) {
    const r = pos(recipe.r, 0.5), h = pos(recipe.h, 1);
    const seg = clamp(Math.round(num(recipe.seg, 48)), 3, 128);
    const open = !!recipe.open;
    const bevel = open ? 0 : Math.max(0, num(recipe.bevel, 0));
    const top = recipe.top === undefined ? r : num(recipe.top, r);
    if (bevel > 0.0005) {
      let profile = cylinderProfile(r, top, h, bevel);
      if (top < 0.0005) profile = [[0, -h / 2], [r, -h / 2], [0, h / 2]];
      return latheData(profile, seg, 0, TAU);
    }
    const m = mesh(), hh = h / 2, slope = (r - top) / h;
    for (let iy = 0; iy <= 1; iy++) {
      const y = iy === 0 ? hh : -hh, rad = iy === 0 ? top : r;
      for (let i = 0; i <= seg; i++) {
        const a = (TAU * i) / seg, s = Math.sin(a), c = Math.cos(a);
        vert(m, rad * s, y, rad * c, s, slope, c, i / seg, 1 - iy);
      }
    }
    const row = seg + 1;
    for (let i = 0; i < seg; i++) {
      const a = i, b = i + 1, c = i + row, d = c + 1;
      m.i.push(a, b, c, b, d, c);
    }
    if (!open) {
      const cap = (y, rad, up) => {
        const center = vert(m, 0, y, 0, 0, up, 0, 0.5, 0.5);
        const first = m.p.length / 3;
        for (let i = 0; i <= seg; i++) {
          const a = (TAU * i) / seg, s = Math.sin(a), c = Math.cos(a);
          vert(m, rad * s, y, rad * c, 0, up, 0, 0.5 + 0.5 * s, 0.5 + 0.5 * c);
        }
        for (let i = 0; i < seg; i++) {
          if (up > 0) m.i.push(center, first + i, first + i + 1);
          else m.i.push(center, first + i + 1, first + i);
        }
      };
      if (top > 0.0001) cap(hh, top, 1);
      cap(-hh, r, -1);
    }
    return m;
  }
  function cone(recipe) {
    const r = pos(recipe.r, 0.5), h = pos(recipe.h, 1), seg = clamp(Math.round(num(recipe.seg, 48)), 3, 128);
    return cylinder(Object.assign({}, recipe, { r, h, seg, top: 0 }));
  }
  function tube(recipe) {
    const r = pos(recipe.r, 0.5), inner = pos(recipe.inner, r * 0.8), h = pos(recipe.h, 1);
    const seg = clamp(Math.round(num(recipe.seg, 48)), 8, 128);
    const m = mesh(), hh = h / 2;
    for (let iy = 0; iy <= 1; iy++) {
      const y = iy === 0 ? hh : -hh;
      for (let i = 0; i <= seg; i++) {
        const a = (TAU * i) / seg, s = Math.sin(a), c = Math.cos(a);
        vert(m, r * s, y, r * c, s, 0, c, i / seg, 1 - iy);
      }
      for (let i = 0; i <= seg; i++) {
        const a = (TAU * i) / seg, s = Math.sin(a), c = Math.cos(a);
        vert(m, inner * s, y, inner * c, -s, 0, -c, i / seg, 1 - iy);
      }
    }
    const row = seg + 1;
    for (let i = 0; i < seg; i++) {
      const oa = i, ob = i + 1, oc = i + row, od = oc + 1;
      m.i.push(oa, ob, oc, ob, od, oc);
      const ia = oa + 2 * row, ib = ob + 2 * row, ic = oc + 2 * row, id = od + 2 * row;
      m.i.push(ia, ic, ib, ib, ic, id);
    }
    // rims
    for (const y of [hh, -hh]) {
      const ring = y === hh ? 0 : row;
      for (let i = 0; i < seg; i++) {
        const oa = ring + i, ob = ring + i + 1, ia = oa + row, ib = ob + row;
        if (y === hh) m.i.push(oa, ia, ob, ob, ia, ib);
        else m.i.push(oa, ob, ia, ob, ib, ia);
      }
    }
    return m;
  }
  function sphereData(r, seg, rings, dome) {
    const m = mesh();
    const phiMax = dome ? Math.PI / 2 : Math.PI;
    for (let iy = 0; iy <= rings; iy++) {
      const v = iy / rings, phi = v * phiMax, sp = Math.sin(phi), cp = Math.cos(phi);
      for (let ix = 0; ix <= seg; ix++) {
        const u = ix / seg, theta = u * TAU, x = -r * Math.cos(theta) * sp, y = r * cp, z = r * Math.sin(theta) * sp;
        vert(m, x, y, z, x / r, y / r, z / r, u, 1 - v);
      }
    }
    const row = seg + 1;
    for (let iy = 0; iy < rings; iy++) {
      for (let ix = 0; ix < seg; ix++) {
        const a = iy * row + ix, b = a + row, c = a + 1, d = b + 1;
        m.i.push(a, c, b, b, c, d);
      }
    }
    return m;
  }
  function sphere(recipe) {
    const r = pos(recipe.r, 0.5), seg = clamp(Math.round(num(recipe.seg, 48)), 8, 128);
    const rings = clamp(Math.round((2 / 3) * seg), 6, 96);
    return sphereData(r, seg, rings, !!recipe.dome);
  }
  function torus(recipe) {
    const R = pos(recipe.r, 1), r = pos(recipe.tube, R * 0.2);
    const m = mesh(), radial = 24, tubular = 72;
    for (let j = 0; j <= radial; j++) {
      const v = (TAU * j) / radial, sv = Math.sin(v), cv = Math.cos(v);
      for (let i = 0; i <= tubular; i++) {
        const u = (TAU * i) / tubular, su = Math.sin(u), cu = Math.cos(u);
        const x = (R + r * cv) * cu, z = (R + r * cv) * su, y = r * sv;
        vert(m, x, y, z, cv * cu, sv, cv * su, i / tubular, j / radial);
      }
    }
    const row = tubular + 1;
    for (let j = 0; j < radial; j++) {
      for (let i = 0; i < tubular; i++) {
        const a = j * row + i, b = a + row, c = a + 1, d = b + 1;
        m.i.push(a, c, b, b, c, d);
      }
    }
    return m;
  }
  function capsule(recipe) {
    const r = pos(recipe.r, 0.3), h = pos(recipe.h, 1);
    const cap = 8, radial = 24, pts = [];
    for (let i = 0; i <= cap; i++) {
      const a = -Math.PI / 2 + (Math.PI / 2) * (i / cap);
      pts.push([Math.cos(a) * r, -h / 2 + Math.sin(a) * r]);
    }
    for (let i = 0; i <= cap; i++) {
      const a = (Math.PI / 2) * (i / cap);
      pts.push([Math.cos(a) * r, h / 2 + Math.sin(a) * r]);
    }
    return latheData(pts, radial, 0, TAU);
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
  function tubeAlong(points, radius, segments, radial, closed) {
    const m = mesh();
    const pts = [];
    for (let i = 0; i <= segments; i++) pts.push(catmull(points, i / segments));
    let normal = null;
    for (let i = 0; i <= segments; i++) {
      const prev = pts[Math.max(0, i - 1)], next = pts[Math.min(segments, i + 1)];
      let tx = next[0] - prev[0], ty = next[1] - prev[1], tz = next[2] - prev[2];
      const tl = Math.hypot(tx, ty, tz) || 1; tx /= tl; ty /= tl; tz /= tl;
      if (!normal) {
        const helper = Math.abs(ty) > 0.9 ? [1, 0, 0] : [0, 1, 0];
        normal = [helper[1] * tz - helper[2] * ty, helper[2] * tx - helper[0] * tz, helper[0] * ty - helper[1] * tx];
        const nl = Math.hypot(...normal) || 1; normal = normal.map(v => v / nl);
      } else {
        const d = normal[0] * tx + normal[1] * ty + normal[2] * tz;
        normal = [normal[0] - tx * d, normal[1] - ty * d, normal[2] - tz * d];
        const nl = Math.hypot(...normal) || 1; normal = normal.map(v => v / nl);
      }
      const binormal = [ty * normal[2] - tz * normal[1], tz * normal[0] - tx * normal[2], tx * normal[1] - ty * normal[0]];
      for (let j = 0; j <= radial; j++) {
        const a = (TAU * j) / radial, s = Math.sin(a), c = Math.cos(a);
        const nx = normal[0] * c + binormal[0] * s, ny = normal[1] * c + binormal[1] * s, nz = normal[2] * c + binormal[2] * s;
        vert(m, pts[i][0] + nx * radius, pts[i][1] + ny * radius, pts[i][2] + nz * radius, nx, ny, nz, i / segments, j / radial);
      }
    }
    const row = radial + 1;
    for (let i = 0; i < segments; i++) {
      for (let j = 0; j < radial; j++) {
        const a = i * row + j, b = a + row, c = a + 1, d = b + 1;
        m.i.push(a, c, b, b, c, d);
      }
    }
    return m;
  }
  function pipe(recipe) {
    let points = (recipe.points || []).filter(p => Array.isArray(p) && p.length >= 3).map(p => [+p[0], +p[1], +p[2]]);
    if (points.length < 2) points = [[-0.8, 0, 0], [0, 0.35, 0], [0.8, 0, 0]];
    const radius = pos(recipe.r, 0.1), radial = clamp(Math.round(num(recipe.seg, 16)), 4, 32);
    const segments = clamp(points.length * 24, 24, 2400);
    return tubeAlong(points, radius, segments, radial);
  }
  function spring(recipe) {
    const r = pos(recipe.r, 0.5), h = pos(recipe.h, 2), coils = Math.max(1, num(recipe.coils, 8)), wire = pos(recipe.wire, 0.06);
    const points = [];
    const turns = Math.round(coils * 32);
    for (let i = 0; i <= turns; i++) {
      const t = i / turns, a = t * TAU * coils;
      points.push([r * Math.cos(a), -h / 2 + h * t, r * Math.sin(a)]);
    }
    const segments = clamp(Math.round(coils * 40), 16, 2400);
    return tubeAlong(points, wire, segments, 10);
  }
  function arrow(recipe) {
    let points = (recipe.points || []).filter(p => Array.isArray(p) && p.length >= 2).map(p => [num(p[0], 0), num(p[1], 0), num(p[2], 0)]);
    if (points.length < 2) points = [[-0.8, 0, 0], [0.8, 0, 0]];
    const r = pos(recipe.r, 0.04);
    const shaftEnd = points[points.length - 1];
    const before = points[points.length - 2];
    const head = num(recipe.head, r * 5), headR = num(recipe.headR, r * 2.6);
    // Pull the shaft back by the head so the cone caps it cleanly.
    const dx = shaftEnd[0] - before[0], dy = shaftEnd[1] - before[1], dz = shaftEnd[2] - before[2];
    const dl = Math.hypot(dx, dy, dz) || 1;
    const neck = [shaftEnd[0] - (dx / dl) * head, shaftEnd[1] - (dy / dl) * head, shaftEnd[2] - (dz / dl) * head];
    const body = tubeAlong(points.slice(0, -1).concat([neck]), r, clamp(Math.round(points.length * 16), 16, 400), 12);
    const cone = cylinder({ r: headR, top: 0, h: head, seg: 16 });
    // Move the head cone onto the tip, oriented along the last segment.
    turn(cone, [dx / dl, dy / dl, dz / dl]);
    translate(cone, shaftEnd[0] - (dx / dl) * (head / 2), shaftEnd[1] - (dy / dl) * (head / 2), shaftEnd[2] - (dz / dl) * (head / 2));
    return merge([body, cone]);
  }

  // ------------------------------------------------------------------ extrude
  function signedArea(pts) {
    let a = 0;
    for (let i = 0; i < pts.length; i++) { const p = pts[i], q = pts[(i + 1) % pts.length]; a += p[0] * q[1] - q[0] * p[1]; }
    return a / 2;
  }
  function pointInTriangle(p, a, b, c) {
    const d1 = (p[0] - b[0]) * (a[1] - b[1]) - (a[0] - b[0]) * (p[1] - b[1]);
    const d2 = (p[0] - c[0]) * (b[1] - c[1]) - (b[0] - c[0]) * (p[1] - c[1]);
    const d3 = (p[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (p[1] - a[1]);
    return !((d1 < 0 || d2 < 0 || d3 < 0) && (d1 > 0 || d2 > 0 || d3 > 0));
  }
  function triangulate(points) {
    const pts = points.map(p => [p[0], p[1]]);
    if (signedArea(pts) < 0) pts.reverse();
    const indices = [], n = pts.length;
    if (n < 3) return indices;
    const remaining = pts.map((_, i) => i);
    let guard = 0;
    while (remaining.length > 3 && guard++ < n * n) {
      let cut = false;
      for (let k = 0; k < remaining.length; k++) {
        const ia = remaining[(k + remaining.length - 1) % remaining.length], ib = remaining[k], ic = remaining[(k + 1) % remaining.length];
        const a = pts[ia], b = pts[ib], c = pts[ic];
        if ((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) <= 1e-12) continue;
        if (remaining.some(i => i !== ia && i !== ib && i !== ic && pointInTriangle(pts[i], a, b, c))) continue;
        indices.push(ia, ib, ic);
        remaining.splice(k, 1);
        cut = true;
        break;
      }
      if (!cut) break;
    }
    if (remaining.length === 3) indices.push(remaining[0], remaining[1], remaining[2]);
    return indices;
  }
  function extrudePolygon(points, depth, center) {
    const m = mesh(), z0 = center ? -depth / 2 : 0, z1 = center ? depth / 2 : depth;
    const tri = triangulate(points);
    for (let k = 0; k < tri.length; k += 3) {
      const a = points[tri[k]], b = points[tri[k + 1]], c = points[tri[k + 2]];
      const up = vert(m, a[0], a[1], z1, 0, 0, 1, 0, 0);
      vert(m, b[0], b[1], z1, 0, 0, 1, 1, 0);
      vert(m, c[0], c[1], z1, 0, 0, 1, 1, 1);
      m.i.push(up, up + 1, up + 2);
      const down = vert(m, a[0], a[1], z0, 0, 0, -1, 0, 0);
      vert(m, c[0], c[1], z0, 0, 0, -1, 1, 0);
      vert(m, b[0], b[1], z0, 0, 0, -1, 1, 1);
      m.i.push(down, down + 1, down + 2);
    }
    const n = points.length;
    for (let i = 0; i < n; i++) {
      const a = points[i], b = points[(i + 1) % n];
      const dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1;
      const nx = dy / l, ny = -dx / l;
      const p0 = vert(m, a[0], a[1], z0, nx, ny, 0, 0, 0);
      vert(m, b[0], b[1], z0, nx, ny, 0, 1, 0);
      vert(m, b[0], b[1], z1, nx, ny, 0, 1, 1);
      vert(m, a[0], a[1], z1, nx, ny, 0, 0, 1);
      m.i.push(p0, p0 + 1, p0 + 2, p0, p0 + 2, p0 + 3);
    }
    return m;
  }
  function svgPoints(d, unit) {
    const tokens = String(d).match(/[a-zA-Z]|-?\d*\.?\d+(?:e[-+]?\d+)?/g) || [];
    const out = [];
    let i = 0, x = 0, y = 0, sx = 0, sy = 0, cmd = '';
    const read = () => parseFloat(tokens[i++]);
    const push = (px, py) => out.push([px * unit, -py * unit]);
    const curve = (kind, args) => {
      // Sample every curve into short straight segments; the kernel's curveSegments is 12.
      const step = 12;
      for (let s = 1; s <= step; s++) { /* points are appended below with a quadratic/cubic formula */ }
      return step;
    };
    while (i < tokens.length) {
      if (/[a-zA-Z]/.test(tokens[i])) cmd = tokens[i++];
      const rel = cmd === cmd.toLowerCase();
      switch (cmd.toUpperCase()) {
        case 'M': {
          const nx = read(), ny = read();
          x = rel ? x + nx : nx; y = rel ? y + ny : ny; sx = x; sy = y;
          push(x, y); cmd = rel ? 'l' : 'L'; break;
        }
        case 'L': {
          const nx = read(), ny = read();
          x = rel ? x + nx : nx; y = rel ? y + ny : ny; push(x, y); break;
        }
        case 'H': { const nx = read(); x = rel ? x + nx : nx; push(x, y); break; }
        case 'V': { const ny = read(); y = rel ? y + ny : ny; push(x, y); break; }
        case 'C': {
          const c1x = read(), c1y = read(), c2x = read(), c2y = read(), nx = read(), ny = read();
          const ax = rel ? x + c1x : c1x, ay = rel ? y + c1y : c1y, bx = rel ? x + c2x : c2x, by = rel ? y + c2y : c2y;
          const ex = rel ? x + nx : nx, ey = rel ? y + ny : ny;
          const step = curve('C');
          for (let s = 1; s <= step; s++) {
            const t = s / step, u = 1 - t;
            push(u * u * u * x + 3 * u * u * t * ax + 3 * u * t * t * bx + t * t * t * ex, u * u * u * y + 3 * u * u * t * ay + 3 * u * t * t * by + t * t * t * ey);
          }
          x = ex; y = ey; break;
        }
        case 'S': {
          const c2x = read(), c2y = read(), nx = read(), ny = read();
          const bx = rel ? x + c2x : c2x, by = rel ? y + c2y : c2y, ex = rel ? x + nx : nx, ey = rel ? y + ny : ny;
          const step = curve('S');
          for (let s = 1; s <= step; s++) {
            const t = s / step, u = 1 - t;
            push(u * u * u * x + 3 * u * u * t * x + 3 * u * t * t * bx + t * t * t * ex, u * u * u * y + 3 * u * u * t * y + 3 * u * t * t * by + t * t * t * ey);
          }
          x = ex; y = ey; break;
        }
        case 'Q': {
          const cx = read(), cy = read(), nx = read(), ny = read();
          const ax = rel ? x + cx : cx, ay = rel ? y + cy : cy, ex = rel ? x + nx : nx, ey = rel ? y + ny : ny;
          for (let s = 1; s <= 12; s++) { const t = s / 12, u = 1 - t; push(u * u * x + 2 * u * t * ax + t * t * ex, u * u * y + 2 * u * t * ay + t * t * ey); }
          x = ex; y = ey; break;
        }
        case 'T': {
          const nx = read(), ny = read();
          const ex = rel ? x + nx : nx, ey = rel ? y + ny : ny;
          for (let s = 1; s <= 12; s++) { const t = s / 12, u = 1 - t; push(u * u * x + 2 * u * t * x + t * t * ex, u * u * y + 2 * u * t * y + t * t * ey); }
          x = ex; y = ey; break;
        }
        case 'A': {
          // Large-arc flags are not needed for the straight-ish outlines used here: approximate with a line.
          read(); read(); read(); read(); read();
          const nx = read(), ny = read();
          x = rel ? x + nx : nx; y = rel ? y + ny : ny; push(x, y); break;
        }
        case 'Z': { x = sx; y = sy; break; }
        default: { i++; break; }
      }
    }
    return out;
  }
  function extrude(recipe) {
    let points = [];
    if (typeof recipe.d === 'string' && recipe.d.trim()) points = svgPoints(recipe.d, num(recipe.unit, 0.01));
    else if (Array.isArray(recipe.shape)) points = recipe.shape.filter(p => Array.isArray(p) && p.length >= 2).map(p => [+p[0], +p[1]]);
    else if (Array.isArray(recipe.points)) points = recipe.points.filter(p => Array.isArray(p) && p.length >= 2).map(p => [+p[0], +p[1]]);
    if (points.length < 3) points = [[-0.3, -0.3], [0.3, -0.3], [0, 0.3]];
    return extrudePolygon(points, pos(recipe.depth, 0.3), true);
  }
  function gear(recipe) {
    const R = pos(recipe.r, 1), w = pos(recipe.w, 0.3), teeth = clamp(Math.round(num(recipe.teeth, 16)), 6, 200);
    const tooth = num(recipe.tooth, 0.14) * R, root = R - tooth / 2, tip = R + tooth / 2;
    const pts = [], step = TAU / teeth;
    for (let i = 0; i < teeth; i++) {
      const a = i * step;
      pts.push([Math.cos(a + step * 0.02) * root, Math.sin(a + step * 0.02) * root]);
      pts.push([Math.cos(a + step * 0.28) * tip, Math.sin(a + step * 0.28) * tip]);
      pts.push([Math.cos(a + step * 0.62) * tip, Math.sin(a + step * 0.62) * tip]);
      pts.push([Math.cos(a + step * 0.92) * root, Math.sin(a + step * 0.92) * root]);
    }
    return extrudePolygon(pts, w, true);
  }

  // ------------------------------------------------------------------ surface grid
  function surface(recipe) {
    const rows = recipe.grid || recipe.rows || [];
    const m = mesh();
    const R = rows.length, C = R ? rows[0].length : 0;
    if (R < 2 || C < 2) {
      const w = 1, d = 1;
      const a = vert(m, -w / 2, 0, -d / 2, 0, 1, 0, 0, 0);
      vert(m, w / 2, 0, -d / 2, 0, 1, 0, 1, 0);
      vert(m, -w / 2, 0, d / 2, 0, 1, 0, 0, 1);
      vert(m, w / 2, 0, d / 2, 0, 1, 0, 1, 1);
      m.i.push(a, a + 2, a + 1, a + 1, a + 2, a + 3);
      return m;
    }
    const at = (r, c) => [num(rows[r][c][0], 0), num(rows[r][c][1], 0), num(rows[r][c][2], 0)];
    for (let r = 0; r < R; r++) {
      for (let c = 0; c < C; c++) {
        const p = at(r, c), l = at(r, Math.max(0, c - 1)), rr = at(r, Math.min(C - 1, c + 1));
        const u = at(Math.max(0, r - 1), c), d = at(Math.min(R - 1, r + 1), c);
        const du = [rr[0] - l[0], rr[1] - l[1], rr[2] - l[2]], dv = [d[0] - u[0], d[1] - u[1], d[2] - u[2]];
        let nx = dv[1] * du[2] - dv[2] * du[1], ny = dv[2] * du[0] - dv[0] * du[2], nz = dv[0] * du[1] - dv[1] * du[0];
        const nl = Math.hypot(nx, ny, nz) || 1; nx /= nl; ny /= nl; nz /= nl;
        vert(m, p[0], p[1], p[2], nx, ny, nz, c / (C - 1), r / (R - 1));
      }
    }
    for (let r = 0; r < R - 1; r++) {
      for (let c = 0; c < C - 1; c++) {
        const a = r * C + c, b = a + 1, d = a + C, e = d + 1;
        m.i.push(a, d, b, b, d, e);
      }
    }
    return m;
  }

  // ------------------------------------------------------------------ polyhedra
  function polyhedron(recipe) {
    const faces = Math.round(num(recipe.faces, 20)), detail = clamp(Math.round(num(recipe.detail, 0)), 0, 3), r = pos(recipe.r, 0.5);
    let verts, tris;
    if (faces === 4) {
      verts = [[1, 1, 1], [-1, -1, 1], [-1, 1, -1], [1, -1, -1]];
      tris = [[0, 1, 2], [0, 3, 1], [0, 2, 3], [1, 3, 2]];
    } else if (faces === 8) {
      verts = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]];
      tris = [[0, 2, 4], [0, 4, 3], [0, 3, 5], [0, 5, 2], [1, 4, 2], [1, 3, 4], [1, 5, 3], [1, 2, 5]];
    } else {
      const t = (1 + Math.sqrt(5)) / 2;
      verts = [[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]];
      tris = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]];
    }
    let work = tris.map(t => t.map(i => verts[i]));
    for (let d = 0; d < detail; d++) {
      const next = [];
      for (const [a, b, c] of work) {
        const ab = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2];
        const bc = [(b[0] + c[0]) / 2, (b[1] + c[1]) / 2, (b[2] + c[2]) / 2];
        const ca = [(c[0] + a[0]) / 2, (c[1] + a[1]) / 2, (c[2] + a[2]) / 2];
        next.push([a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]);
      }
      work = next;
    }
    const m = mesh();
    for (const [a, b, c] of work) {
      const na = normalize(a), nb = normalize(b), nc = normalize(c);
      const pa = vert(m, na[0] * r, na[1] * r, na[2] * r, na[0], na[1], na[2], 0, 0);
      vert(m, nb[0] * r, nb[1] * r, nb[2] * r, nb[0], nb[1], nb[2], 1, 0);
      vert(m, nc[0] * r, nc[1] * r, nc[2] * r, nc[0], nc[1], nc[2], 1, 1);
      m.i.push(pa, pa + 1, pa + 2);
    }
    return m;
  }
  const normalize = v => { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; };

  // ------------------------------------------------------------------ metaballs (surface nets)
  function blob(recipe) {
    const balls = (recipe.balls || []).map(b => Array.isArray(b) ? { at: b.slice(0, 3), r: num(b[3], 0.5) } : b).filter(b => b && b.at);
    const sticks = (recipe.sticks || []).map(s => Array.isArray(s) ? { from: s[0], to: s[1], r: num(s[2], 0.2) } : s).filter(s => s && s.from && s.to);
    if (!balls.length && !sticks.length) {
      const r = pos(recipe.r, 0.5), lump = num(recipe.lumps, 0.12);
      return sphereData(r * (1 + lump), 24, 16, false);
    }
    const all = [];
    for (const b of balls) all.push({ p: b.at, r: pos(b.r, 0.5) });
    for (const s of sticks) all.push({ p: s.from, r: pos(s.r, 0.2) }, { p: s.to, r: pos(s.r, 0.2) });
    const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
    for (const s of all) for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], s.p[k] - s.r); hi[k] = Math.max(hi[k], s.p[k] + s.r); }
    const mid = [0, 1, 2].map(k => (lo[k] + hi[k]) / 2);
    const extent = Math.max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], 1e-3);
    const step = extent / 40;
    const dims = [0, 1, 2].map(k => Math.max(2, Math.ceil((hi[k] - lo[k]) / step) + 1));
    const field = new Float32Array(dims[0] * dims[1] * dims[2]);
    const at = (i, j, k) => i + dims[0] * (j + dims[1] * k);
    const dist = (x, y, z) => {
      let best = 1e9;
      for (const b of balls) {
        const dx = x - b.at[0], dy = y - b.at[1], dz = z - b.at[2];
        best = Math.min(best, Math.hypot(dx, dy, dz) - pos(b.r, 0.5));
      }
      for (const s of sticks) {
        const ax = s.from[0], ay = s.from[1], az = s.from[2];
        const bx = s.to[0] - ax, by = s.to[1] - ay, bz = s.to[2] - az;
        const px = x - ax, py = y - ay, pz = z - az;
        const l2 = bx * bx + by * by + bz * bz || 1;
        const t = clamp((px * bx + py * by + pz * bz) / l2, 0, 1);
        best = Math.min(best, Math.hypot(px - bx * t, py - by * t, pz - bz * t) - pos(s.r, 0.2));
      }
      return best;
    };
    for (let k = 0; k < dims[2]; k++) for (let j = 0; j < dims[1]; j++) for (let i = 0; i < dims[0]; i++) {
      field[at(i, j, k)] = dist(lo[0] + i * step, lo[1] + j * step, lo[2] + k * step);
    }
    // Marching tetrahedra: six tetrahedra per cell, one or two triangles each. It is the
    // simplest watertight polygoniser and has no ambiguous cube cases.
    const corners = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [0, 0, 1], [1, 0, 1], [0, 1, 1], [1, 1, 1]];
    const tets = [[0, 5, 1, 6], [0, 1, 2, 6], [0, 2, 3, 6], [0, 3, 7, 6], [0, 7, 4, 6], [0, 4, 5, 6]];
    const m = mesh();
    const point = (i, j, k) => [lo[0] + i * step, lo[1] + j * step, lo[2] + k * step];
    const lerpPoint = (a, b, va, vb) => {
      const t = va / (va - vb);
      return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
    };
    const addTri = (a, b, c) => {
      const e = step * 0.35;
      const cx = (a[0] + b[0] + c[0]) / 3, cy = (a[1] + b[1] + c[1]) / 3, cz = (a[2] + b[2] + c[2]) / 3;
      let nx = (b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1]);
      let ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]);
      let nz = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
      const gx = dist(cx + e, cy, cz) - dist(cx - e, cy, cz);
      const gy = dist(cx, cy + e, cz) - dist(cx, cy - e, cz);
      const gz = dist(cx, cy, cz + e) - dist(cx, cy, cz - e);
      if (nx * gx + ny * gy + nz * gz < 0) { const swap = b; b = c; c = swap; nx = -nx; ny = -ny; nz = -nz; }
      const nl = Math.hypot(nx, ny, nz) || 1;
      const base = m.p.length / 3;
      for (const p of [a, b, c]) vert(m, p[0], p[1], p[2], nx / nl, ny / nl, nz / nl, 0, 0);
      m.i.push(base, base + 1, base + 2);
    };
    for (let k = 0; k < dims[2] - 1; k++) for (let j = 0; j < dims[1] - 1; j++) for (let i = 0; i < dims[0] - 1; i++) {
      const wp = corners.map(c => point(i + c[0], j + c[1], k + c[2]));
      const wv = corners.map(c => field[at(i + c[0], j + c[1], k + c[2])]);
      if (wv.every(v => v >= 0) || wv.every(v => v < 0)) continue;
      for (const tet of tets) {
        const inside = [], outside = [];
        for (const c of tet) (wv[c] < 0 ? inside : outside).push(c);
        if (!inside.length || !outside.length) continue;
        if (inside.length === 1) {
          const a = inside[0];
          addTri(lerpPoint(wp[a], wp[outside[0]], wv[a], wv[outside[0]]), lerpPoint(wp[a], wp[outside[1]], wv[a], wv[outside[1]]), lerpPoint(wp[a], wp[outside[2]], wv[a], wv[outside[2]]));
        } else if (inside.length === 3) {
          const a = outside[0];
          addTri(lerpPoint(wp[a], wp[inside[0]], wv[a], wv[inside[0]]), lerpPoint(wp[a], wp[inside[1]], wv[a], wv[inside[1]]), lerpPoint(wp[a], wp[inside[2]], wv[a], wv[inside[2]]));
        } else {
          const [a, b] = inside, [c, d] = outside;
          const ab_c = lerpPoint(wp[a], wp[c], wv[a], wv[c]);
          const ab_d = lerpPoint(wp[a], wp[d], wv[a], wv[d]);
          const ba_c = lerpPoint(wp[b], wp[c], wv[b], wv[c]);
          const ba_d = lerpPoint(wp[b], wp[d], wv[b], wv[d]);
          addTri(ab_c, ab_d, ba_d);
          addTri(ab_c, ba_d, ba_c);
        }
      }
    }
    return m;
  }

  // ------------------------------------------------------------------ transforms
  function translate(m, x, y, z) {
    for (let i = 0; i < m.p.length; i += 3) { m.p[i] += x; m.p[i + 1] += y; m.p[i + 2] += z; }
  }
  function rotate(m, axis, angle) {
    const c = Math.cos(angle), s = Math.sin(angle);
    for (let i = 0; i < m.p.length; i += 3) {
      const x = m.p[i], y = m.p[i + 1], z = m.p[i + 2];
      let nx = x, ny = y, nz = z;
      if (axis === 'x') { ny = y * c - z * s; nz = y * s + z * c; }
      else if (axis === 'y') { nx = x * c + z * s; nz = -x * s + z * c; }
      else { nx = x * c - y * s; ny = x * s + y * c; }
      m.p[i] = nx; m.p[i + 1] = ny; m.p[i + 2] = nz;
      const a = m.n[i], b = m.n[i + 1], d = m.n[i + 2];
      if (axis === 'x') { m.n[i + 1] = b * c - d * s; m.n[i + 2] = b * s + d * c; }
      else if (axis === 'y') { m.n[i] = a * c + d * s; m.n[i + 2] = -a * s + d * c; }
      else { m.n[i] = a * c - b * s; m.n[i + 1] = a * s + b * c; }
    }
  }
  function turn(m, dir) {
    // Rotate +Y onto dir (axis-angle).
    const d = normalize(dir), from = [0, 1, 0];
    const dot = clamp(from[0] * d[0] + from[1] * d[1] + from[2] * d[2], -1, 1);
    if (dot > 0.99999) return m;
    if (dot < -0.99999) return rotate(m, 'z', Math.PI);
    const axis = normalize([from[1] * d[2] - from[2] * d[1], from[2] * d[0] - from[0] * d[2], from[0] * d[1] - from[1] * d[0]]);
    const a = Math.acos(dot), c = Math.cos(a), s = Math.sin(a), t = 1 - c;
    const [x, y, z] = axis;
    const R = [t * x * x + c, t * x * y - s * z, t * x * z + s * y, t * x * y + s * z, t * y * y + c, t * y * z - s * x, t * x * z - s * y, t * y * z + s * x, t * z * z + c];
    for (let i = 0; i < m.p.length; i += 3) {
      const px = m.p[i], py = m.p[i + 1], pz = m.p[i + 2];
      m.p[i] = R[0] * px + R[1] * py + R[2] * pz;
      m.p[i + 1] = R[3] * px + R[4] * py + R[5] * pz;
      m.p[i + 2] = R[6] * px + R[7] * py + R[8] * pz;
      const nx = m.n[i], ny = m.n[i + 1], nz = m.n[i + 2];
      m.n[i] = R[0] * nx + R[1] * ny + R[2] * nz;
      m.n[i + 1] = R[3] * nx + R[4] * ny + R[5] * nz;
      m.n[i + 2] = R[6] * nx + R[7] * ny + R[8] * nz;
    }
    return m;
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

  // ------------------------------------------------------------------ the kernel
  const SHAPES = {
    box,
    cyl: cylinder,
    cylinder,
    cone,
    tube,
    arrow,
    lathe,
    sphere,
    torus,
    capsule,
    pipe,
    spring,
    gear,
    extrude,
    blob,
    poly: polyhedron,
    surface,
  };

  const KINDS = Object.keys(SHAPES);

  function axisVector(axis) {
    if (typeof axis === 'string') {
      const m = /^\s*([+-]?)\s*([xyz])\s*$/i.exec(axis);
      if (!m) return null;
      const v = m[2].toLowerCase() === 'x' ? [1, 0, 0] : m[2].toLowerCase() === 'z' ? [0, 0, 1] : [0, 1, 0];
      return [v[0] * (m[1] === '-' ? -1 : 1), v[1] * (m[1] === '-' ? -1 : 1), v[2] * (m[1] === '-' ? -1 : 1)];
    }
    const v = vec3(axis);
    return v && Math.hypot(v[0], v[1], v[2]) > 1e-6 ? normalize(v) : null;
  }
  function stretchMesh(m, sx, sy, sz) {
    for (let i = 0; i < m.p.length; i += 3) { m.p[i] *= sx; m.p[i + 1] *= sy; m.p[i + 2] *= sz; }
    // Normals transform by the inverse transpose; for a diagonal scale that is 1/s.
    for (let i = 0; i < m.n.length; i += 3) {
      let nx = m.n[i] / (sx || 1), ny = m.n[i + 1] / (sy || 1), nz = m.n[i + 2] / (sz || 1);
      const l = Math.hypot(nx, ny, nz) || 1;
      m.n[i] = nx / l; m.n[i + 1] = ny / l; m.n[i + 2] = nz / l;
    }
  }

  function build(kind, recipe) {
    const make = SHAPES[kind];
    if (!make) throw new Error('Clicky3D: unknown part "' + kind + '"');
    recipe = recipe || {};
    const m = make(recipe);
    const axis = axisVector(recipe.axis);
    if (axis && !(axis[0] === 0 && Math.abs(axis[1]) === 1 && axis[2] === 0)) turn(m, axis);
    if (Array.isArray(recipe.stretch) && recipe.stretch.length >= 3) stretchMesh(m, num(recipe.stretch[0], 1), num(recipe.stretch[1], 1), num(recipe.stretch[2], 1));
    const geometry = finish(m);
    // Framing samples: the axis extremes plus an even spread, at most 600.
    const count = geometry.positions.length / 3;
    let samples;
    if (count <= 600) samples = geometry.positions;
    else {
      const picks = [];
      for (let i = 0; i < 600 - 6; i++) picks.push(Math.floor((i / (600 - 6)) * count));
      const extreme = (axis, sign) => {
        let best = 0, value = sign > 0 ? -Infinity : Infinity;
        for (let i = 0; i < count; i++) {
          const v = geometry.positions[i * 3 + axis];
          if (sign > 0 ? v > value : v < value) { value = v; best = i; }
        }
        return best;
      };
      for (let a = 0; a < 3; a++) picks.push(extreme(a, 1), extreme(a, -1));
      samples = new Float32Array(picks.length * 3);
      picks.forEach((i, k) => {
        samples[k * 3] = geometry.positions[i * 3];
        samples[k * 3 + 1] = geometry.positions[i * 3 + 1];
        samples[k * 3 + 2] = geometry.positions[i * 3 + 2];
      });
    }
    geometry.samples = samples;
    return geometry;
  }

  return { kinds: KINDS, build, box, cyl: cylinder, cone, tube, sphere, torus, capsule, lathe, pipe, spring, gear, extrude, blob, poly: polyhedron, surface };
})();
