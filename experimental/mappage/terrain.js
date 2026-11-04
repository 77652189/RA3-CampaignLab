// The map page's terrain preview: the mirror of terrain_edit.py (what a brush stroke does) and of the engine line's
// terrain_rules.py (slope, the impassable bit, apply_edit, flat_enough). Every number comes in P (terrain_edit.params);
// tests/test_mappage_terrain.py runs this file under node on the same strokes as Python and wants the same heights and
// bits. A ground G = {e: Float64Array (ours, row j * w + i), bits: Uint8Array (field 0), w, h, b}.
const TERRAIN = (() => {
  // Python's round(): half to even (terrain_rules.flat_enough and platmap.level_enough use it)
  function pyRound(v) {
    const f = Math.floor(v), d = v - f;
    if (d > 0.5) return f + 1;
    if (d < 0.5) return f;
    return f % 2 === 0 ? f : f + 1;
  }
  function copy(G) { return { e: Float64Array.from(G.e), bits: Uint8Array.from(G.bits), w: G.w, h: G.h, b: G.b }; }

  // terrain_rules.slope at one cell: the largest rise to its four neighbours, edges padded
  function slopeAt(e, w, h, i, j) {
    const c = e[j * w + i];
    const l = e[j * w + Math.max(0, i - 1)], r = e[j * w + Math.min(w - 1, i + 1)];
    const u = e[Math.max(0, j - 1) * w + i], d = e[Math.min(h - 1, j + 1) * w + i];
    return Math.max(Math.abs(r - c), Math.abs(l - c), Math.abs(d - c), Math.abs(u - c));
  }
  // terrain_rules.impassable_bits at one cell
  function impassableAt(G, P, i, j) {
    return slopeAt(G.e, G.w, G.h, i, j) > P.steep && G.e[j * G.w + i] > P.waterline;
  }
  // terrain_rules.apply_edit: field 0 recomputed over the changed cells and P.ring (4-neighbour) rings round them
  function applyEdit(G, P, changed) {
    const { w, h } = G;
    let reg = Uint8Array.from(changed);
    for (let k = 0; k < P.ring; k++) {
      const n = Uint8Array.from(reg);
      for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
        if (!reg[j * w + i]) continue;
        if (i > 0) n[j * w + i - 1] = 1; if (i < w - 1) n[j * w + i + 1] = 1;
        if (j > 0) n[(j - 1) * w + i] = 1; if (j < h - 1) n[(j + 1) * w + i] = 1;
      }
      reg = n;
    }
    for (let q = 0; q < w * h; q++) if (reg[q]) G.bits[q] = impassableAt(G, P, q % w, Math.floor(q / w)) ? 1 : 0;
  }

  // terrain_edit._window: the cells round a dab, with their distance
  function each(G, P, x, y, r, fn) {
    const c = P.cell;
    const i0 = Math.max(0, Math.floor((x - r) / c) + G.b), i1 = Math.min(G.w - 1, Math.ceil((x + r) / c) + G.b);
    const j0 = Math.max(0, Math.floor((y - r) / c) + G.b), j1 = Math.min(G.h - 1, Math.ceil((y + r) / c) + G.b);
    for (let j = j0; j <= j1; j++) {
      const dy = (j - G.b) * c - y;
      for (let i = i0; i <= i1; i++) {
        const dx = (i - G.b) * c - x;
        fn(j * G.w + i, Math.sqrt(dx * dx + dy * dy));
      }
    }
  }

  // a stroke's dabs as stored: flat [x0, y0, x1, y1, ...] (the page's store takes no array of arrays), or pairs
  function dabPairs(d) {
    if (d.length && Array.isArray(d[0])) return d;
    const o = []; for (let k = 0; k + 1 < d.length; k += 2) o.push([d[k], d[k + 1]]); return o;
  }
  // terrain_edit.apply_stroke: in place; returns the changed-height mask (Uint8Array), or null for a paint stroke
  function applyStroke(G, P, st) {
    const r = +st.r, s = +(st.s || 0);
    if (st.op === "block" || st.op === "unblock") {
      const on = st.op === "block" ? 1 : 0;
      for (const [x, y] of dabPairs(st.dabs)) each(G, P, +x, +y, r, (q, d) => { if (d <= r) G.bits[q] = on; });
      return null;
    }
    const e0 = Float64Array.from(G.e), e = G.e;
    for (const [x, y] of dabPairs(st.dabs)) each(G, P, +x, +y, r, (q, d) => {
      if (!(d < r)) return;
      const amt = s * (1.0 - d / r);
      if (st.op === "raise") e[q] = e[q] + amt;
      else if (st.op === "lower") e[q] = e[q] - amt;
      else { const want = +st.height - e[q]; e[q] = e[q] + Math.max(-amt, Math.min(amt, want)); }
    });
    const changed = new Uint8Array(e.length);
    for (let q = 0; q < e.length; q++) {
      const raw = Math.min(P.raw_max, Math.max(0, Math.floor(e[q] * P.raw_per_ours + 0.5)));
      e[q] = raw / P.raw_per_ours;
      if (e[q] !== e0[q]) changed[q] = 1;
    }
    applyEdit(G, P, changed);
    return changed;
  }
  function applyProposals(G, P, proposals) {
    const out = copy(G);
    for (const p of proposals) for (const st of p.strokes || []) applyStroke(out, P, st);
    return out;
  }

  // terrain_rules.flat_enough at a world point, picked the way platmap.level_enough does
  function flatEnough(G, P, x, y, side) {
    const i = pyRound(x / P.cell) + G.b, j = pyRound(y / P.cell) + G.b;
    const half = Math.max(1, Math.trunc(pyRound(side / P.cell / 2)));
    let lo = Infinity, hi = -Infinity;
    for (let jj = Math.max(0, j - half); jj <= Math.min(G.h - 1, j + half); jj++)
      for (let ii = Math.max(0, i - half); ii <= Math.min(G.w - 1, i + half); ii++) {
        const v = G.e[jj * G.w + ii]; if (v < lo) lo = v; if (v > hi) hi = v;
      }
    return (hi - lo) * P.world_per_ours <= P.build_variation;
  }
  function flatSites(G, P, sites) {
    const out = {};
    for (const s of sites) {
      if (s.build) out[`${s.k}|build`] = flatEnough(G, P, s.x, s.y, s.build);
      if (s.cast) out[`${s.k}|cast`] = flatEnough(G, P, s.x, s.y, 2 * s.cast);
    }
    return out;
  }

  // the stored ground the page is handed: raw elevations (u16 LE) and field 0 (bits, rows, little-endian per byte)
  function decode(T) {
    const bin = (s) => { const a = atob(s), u = new Uint8Array(a.length); for (let k = 0; k < a.length; k++) u[k] = a.charCodeAt(k); return u; };
    const raw = bin(T.elev), packed = bin(T.bits), n = T.w * T.h, rb = Math.ceil(T.w / 8);
    const e = new Float64Array(n), bits = new Uint8Array(n);
    const dv = new DataView(raw.buffer);
    for (let q = 0; q < n; q++) e[q] = dv.getUint16(2 * q, true) / T.raw_per_ours;
    for (let j = 0; j < T.h; j++) for (let i = 0; i < T.w; i++) bits[j * T.w + i] = (packed[j * rb + (i >> 3)] >> (i & 7)) & 1;
    return { e, bits, w: T.w, h: T.h, b: T.b };
  }

  return { pyRound, copy, slopeAt, impassableAt, applyEdit, applyStroke, applyProposals, flatEnough, flatSites, decode };
})();
if (typeof module !== "undefined") module.exports = TERRAIN;
