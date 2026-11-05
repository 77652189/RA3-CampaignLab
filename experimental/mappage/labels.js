// The map page's site-name layout: where each label goes so that no two shown labels overlap (and none covers another
// site's dot or runs off the map). Pure geometry on boxes, no DOM -- the page measures the labels (getBBox) at the
// current zoom and hands their sizes in; tests/test_mappage_labels.py runs this file under node and checks the result.
//
// place(items, bounds, o) -> [{shown, x, y, w, h, short, leader}] in the same order as items
//   items   [{x, y, w, h, ws?}]: the site's dot centre (map units, y down as in the svg), its label's box size and,
//           optionally, the width of its short form (the Chinese name alone), tried only when the full one finds no spot
//   bounds  [x0, y0, x1, y1]: the map; a label must lie inside
//   o       {dot, gap, rings, step}: dot radius, gap between dot and label, how many rings further out to try (with a
//           leader line back to the dot) and how far apart the rings are -- all map units
// A label first tries the eight spots next to its dot (right first, as the page always drew it), then the same eight
// further out, ring by ring, with a leader line; a leader may not cross a placed label, and a later label may not cross
// a placed leader. Crowded sites are placed first, so they get the near spots. A label with no free spot is not shown
// (the page shows it on hover).
const Labels = (() => {
  const hit = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
  // does the segment p->q cross box b (Liang-Barsky)
  function segHit(p, q, b) {
    let t0 = 0, t1 = 1;
    const dx = q[0] - p[0], dy = q[1] - p[1];
    for (const [pp, qq] of [[-dx, p[0] - b.x], [dx, b.x + b.w - p[0]], [-dy, p[1] - b.y], [dy, b.y + b.h - p[1]]]) {
      if (pp === 0) { if (qq < 0) return false; continue; }
      const r = qq / pp;
      if (pp < 0) { if (r > t1) return false; if (r > t0) t0 = r; }
      else { if (r < t0) return false; if (r < t1) t1 = r; }
    }
    return t0 < t1;
  }
  // the point on box b nearest to (x, y)
  const near = (b, x, y) => [Math.max(b.x, Math.min(x, b.x + b.w)), Math.max(b.y, Math.min(y, b.y + b.h))];

  function spots(it, d) {
    const { x, y, w, h } = it, e = d * 0.71;
    return [[x + d, y - h / 2], [x - d - w, y - h / 2], [x + e, y - e - h], [x + e, y + e], [x - e - w, y - e - h],
      [x - e - w, y + e], [x - w / 2, y - d - h], [x - w / 2, y + d]];
  }

  function place(items, bounds, o) {
    const [X0, Y0, X1, Y1] = bounds;
    const dots = items.map((it) => ({ x: it.x - o.dot, y: it.y - o.dot, w: 2 * o.dot, h: 2 * o.dot }));
    const reach = (it) => it.w + o.dot + o.gap;
    const crowd = items.map((it, i) => items.reduce((n, q, j) => n + (j !== i && Math.abs(q.x - it.x) < reach(it) + q.w &&
      Math.abs(q.y - it.y) < 3 * it.h ? 1 : 0), 0));
    const order = items.map((_, i) => i).sort((a, b) => crowd[b] - crowd[a] || a - b);
    const out = items.map((it) => ({ shown: false, x: 0, y: 0, w: it.w, h: it.h, short: false, leader: null }));
    const boxes = [], leaders = [];
    for (const i of order) {
      const it = items[i];
      let got = null;
      const widths = it.ws && it.ws < it.w ? [it.w, it.ws] : [it.w];
      for (let ring = 0; ring <= o.rings && !got; ring++) for (const w of widths) {
        if (got) break;
        for (const [bx, by] of spots({ x: it.x, y: it.y, w, h: it.h }, o.dot + o.gap + ring * o.step)) {
          const b = { x: bx, y: by, w, h: it.h };
          if (b.x < X0 || b.y < Y0 || b.x + b.w > X1 || b.y + b.h > Y1) continue;
          if (boxes.some((q) => hit(q, b)) || dots.some((q, j) => j !== i && hit(q, b))) continue;
          if (leaders.some(([p, q]) => segHit(p, q, b))) continue;
          let lead = null;
          if (ring > 0) {
            const q = near(b, it.x, it.y), L = Math.hypot(q[0] - it.x, q[1] - it.y) || 1;
            const p = [it.x + (q[0] - it.x) * o.dot / L, it.y + (q[1] - it.y) * o.dot / L];
            if (boxes.some((bb) => segHit(p, q, bb))) continue;
            lead = [p, q];
          }
          got = { b, lead };
          break;
        }
      }
      if (!got) continue;
      Object.assign(out[i], { shown: true, x: got.b.x, y: got.b.y, w: got.b.w, short: got.b.w < it.w, leader: got.lead });
      boxes.push(got.b);
      if (got.lead) leaders.push(got.lead);
    }
    return out;
  }

  // the page's numbers at k map units per screen pixel: the dot (drawn r 26 + stroke) or 3 px, a 3 px gap, six rings 10 px apart
  const opts = (k) => ({ dot: Math.max(32, 3 * k), gap: 3 * k, rings: 6, step: 10 * k });

  return { place, opts, hit, segHit };
})();
if (typeof module !== "undefined") module.exports = Labels;
