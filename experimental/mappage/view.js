// The map page's zoom and pan: which part of the map the svg shows (its viewBox), as pure arithmetic so
// tests/test_mappage_labels.py can run it under node. A view is {x, y, w} in svg units (y down); its height is
// w * H / W, the map's own aspect, so the picture is never stretched.
const View = (() => {
  const MAX_ZOOM = 12;                       // at most 1/12 of the map across
  const full = (W, H) => ({ x: 0, y: 0, w: W });
  const height = (v, W, H) => v.w * H / W;
  // inside the map, between the whole map and MAX_ZOOM
  function clamp(v, W, H) {
    const w = Math.min(W, Math.max(W / MAX_ZOOM, v.w)), h = w * H / W;
    return { x: Math.min(W - w, Math.max(0, v.x)), y: Math.min(H - h, Math.max(0, v.y)), w };
  }
  // zoom by f (> 1 = closer) keeping the map point (px, py) where it is on the screen
  function zoomAt(v, W, H, f, px, py) {
    const w = Math.min(W, Math.max(W / MAX_ZOOM, v.w / f)), s = w / v.w;
    return clamp({ x: px - (px - v.x) * s, y: py - (py - v.y) * s, w }, W, H);
  }
  // move by (dx, dy) svg units
  const panBy = (v, W, H, dx, dy) => clamp({ x: v.x + dx, y: v.y + dy, w: v.w }, W, H);
  // a two-finger gesture: started on view v0 with fingers a0, b0 (screen px), now at a1, b1; rect = svg's screen box
  function pinch(v0, W, H, rect, a0, b0, a1, b1) {
    const d0 = Math.hypot(b0[0] - a0[0], b0[1] - a0[1]) || 1, d1 = Math.hypot(b1[0] - a1[0], b1[1] - a1[1]) || 1;
    const m0 = [(a0[0] + b0[0]) / 2, (a0[1] + b0[1]) / 2], m1 = [(a1[0] + b1[0]) / 2, (a1[1] + b1[1]) / 2];
    const k0 = v0.w / rect.width;
    const px = v0.x + (m0[0] - rect.left) * k0, py = v0.y + (m0[1] - rect.top) * k0;   // map point under the start midpoint
    const w = Math.min(W, Math.max(W / MAX_ZOOM, v0.w * d0 / d1)), k1 = w / rect.width;
    return clamp({ x: px - (m1[0] - rect.left) * k1, y: py - (m1[1] - rect.top) * k1, w }, W, H);
  }
  return { MAX_ZOOM, full, height, clamp, zoomAt, panBy, pinch };
})();
if (typeof module !== "undefined") module.exports = View;
