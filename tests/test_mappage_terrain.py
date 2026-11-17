"""The map page's terrain editor (ADR 0017): terrain_edit.py says what a brush stroke does, terrain.js (the page's live
preview) must give the same heights, impassable bits and flat-enough verdicts -- checked by running terrain.js under node
on the strokes Python ran -- and --apply-preview / --pull read terrain proposals back for the level line."""
import importlib.util
import json
import re
import shutil
import subprocess

import numpy as np
import pytest

from test_mappage import ROOT, _a4, mappage

te = mappage.terrain_edit
JS = ROOT / 'experimental' / 'mappage' / 'terrain.js'
NODE = shutil.which('node')
_spec = importlib.util.spec_from_file_location('terrain_rules', ROOT / 'experimental' / 'campaign' / 'terrain_rules.py')
tr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tr)


def _ground():
    """A small map: a low plain, a plateau with a cliff, a ramp, a sea corner; field 0 as the writers set it, plus one
    painted cell the slope does not give."""
    h, w, b = 64, 72, 6
    e = np.full((h, w), 340.0)
    e[30:, 40:] = 455.0                                       # plateau, cliff along its edges
    e[:12, :14] = 200.0                                       # sea corner (below the waterline)
    for k in range(10):                                       # a ramp up the plateau
        e[20 + k, 50:56] = 340.0 + 11.5 * (k + 1)
    e = np.floor(e * 16 + 0.5) / 16
    bits = tr.impassable_bits(e, 285.7)
    bits[8, 30] = True
    return te.Ground(e, bits, b, 285.7)


STROKES = [
    {'kind': 'terrain', 'strokes': [
        {'op': 'raise', 'r': 80, 's': 3.3, 'dabs': [100, 100, 120, 110, 140, 130]},
        {'op': 'lower', 'r': 45, 's': 7.25, 'dabs': [[380, 300], [395, 300]]},
    ]},
    {'kind': 'terrain', 'strokes': [
        {'op': 'flatten', 'r': 120, 's': 20, 'height': 340.0, 'dabs': [400, 240, 430, 260]},   # into the cliff
        {'op': 'block', 'r': 30, 'dabs': [-20, 20, 200, 20]},
        {'op': 'unblock', 'r': 25, 'dabs': [240, 20, 460, 250]},
        {'op': 'raise', 'r': 300, 's': 9000, 'dabs': [-40, -40]},                              # clipped at the edges
        {'op': 'lower', 'r': 55, 's': 400, 'dabs': [80, 520]},                                # down to raw 0
        {'op': 'lower', 'r': 35, 's': 30, 'dabs': [650, 400, 650, 560]},                      # the right and top edges
        {'op': 'lower', 'r': 25, 's': 100, 'dabs': [620, 300]},                # its ring alone reaches the right edge
    ]},
]
SITES = [{'k': 'a', 'x': 105.0, 'y': 115.0, 'build': 160.0, 'cast': 52.0},
         {'k': 'b', 'x': 400.0, 'y': 250.0, 'build': 50.0, 'cast': 0.0},
         {'k': 'c', 'x': 250.0, 'y': 145.0, 'build': 0.0, 'cast': 25.0},
         # 50 across: Python's round(2.5) = 2 cells each way stays off the cliff 3 cells east; a half-up 3 would not
         {'k': 'd', 'x': 310.0, 'y': 270.0, 'build': 50.0, 'cast': 0.0}]

NODE_SCRIPT = r"""
const T = require(process.argv[2]);
const inp = JSON.parse(require('fs').readFileSync(process.argv[3], 'utf8'));
const P = inp.P;
const G = { e: Float64Array.from(inp.e), bits: Uint8Array.from(inp.bits), w: P.w, h: P.h, b: P.b };
const steps = [];
let cur = G;
for (const p of inp.proposals) { cur = T.applyProposals(cur, P, [p]); steps.push({ e: Array.from(cur.e), bits: Array.from(cur.bits), flat: T.flatSites(cur, P, inp.sites) }); }
const dec = T.decode(Object.assign({}, P, inp.enc));
const rounds = inp.rounds.map(T.pyRound);
process.stdout.write(JSON.stringify({ steps, dec: { e: Array.from(dec.e), bits: Array.from(dec.bits) }, rounds }));
"""


def _flat(g, sites):
    o = {}
    for s in sites:
        i, j = g.cell_of(s['x'], s['y'])
        if s['build']:
            o[f'{s["k"]}|build'] = bool(tr.flat_enough(g.e, i, j, s['build']))
        if s['cast']:
            o[f'{s["k"]}|cast'] = bool(tr.flat_enough(g.e, i, j, 2 * s['cast']))
    return o


@pytest.mark.skipif(NODE is None, reason='node not installed')
def test_page_preview_equals_python(tmp_path):
    g0 = _ground()
    P = te.params(g0)
    rounds = [0.5, 1.5, 2.5, -0.5, -1.5, 2.4999, 7.5, 104 / 20, 50 / 20]
    inp = {'P': P, 'e': g0.e.ravel().tolist(), 'bits': g0.bits.ravel().astype(int).tolist(), 'proposals': STROKES,
           'sites': SITES, 'enc': te.encode(g0), 'rounds': rounds}
    f = tmp_path / 'in.json'
    f.write_text(json.dumps(inp), encoding='utf-8')
    js = tmp_path / 'run.js'
    js.write_text(NODE_SCRIPT, encoding='utf-8')
    out = json.loads(subprocess.run([NODE, str(js), str(JS), str(f)], capture_output=True, text=True, check=True).stdout)

    assert out['rounds'] == [round(v) for v in rounds]
    assert np.array_equal(np.array(out['dec']['e']).reshape(g0.e.shape), g0.e)
    assert np.array_equal(np.array(out['dec']['bits'], dtype=bool).reshape(g0.e.shape), g0.bits)
    g = g0
    for p, step in zip(STROKES, out['steps']):
        g, _ = te.apply_proposals(g, [p])
        assert np.array_equal(np.array(step['e']).reshape(g.e.shape), g.e), 'heights differ'
        assert np.array_equal(np.array(step['bits'], dtype=bool).reshape(g.e.shape), g.bits), 'field 0 differs'
        assert step['flat'] == _flat(g, SITES)
    # the strokes did what they say, so the comparison is not of two no-ops
    assert (g.e != g0.e).sum() > 500 and (g.bits != g0.bits).sum() > 20
    assert g.e.max() == 65535 / 16 and g.e.min() == 0.0
    assert len({v for v in out['steps'][0]['flat'].values()}) == 2 or len({v for v in out['steps'][1]['flat'].values()}) == 2


def test_stroke_rules_are_terrain_rules():
    """Field 0 after a height stroke is terrain_rules.apply_edit over the moved cells; a paint stroke keeps the heights;
    painted cells away from a later height stroke stay painted; the page gets terrain_rules' own numbers."""
    g = _ground()
    painted = g.copy()
    te.apply_stroke(painted, {'op': 'block', 'r': 15, 'dabs': [300, 0]})
    assert np.array_equal(painted.e, g.e) and painted.bits[6, 36]
    after = painted.copy()
    moved = te.apply_stroke(after, {'op': 'raise', 'r': 60, 's': 15, 'dabs': [100, 300]})
    assert moved.any()
    assert np.array_equal(after.bits, tr.apply_edit(after.e, painted.bits, moved, 285.7))
    assert after.bits[6, 36], 'a painted cell outside the edit stays'
    assert np.array_equal(after.e, np.floor(after.e * 16 + .5) / 16), 'heights stored as the map stores them'
    P = te.params(g)
    assert (P['steep'], P['build_variation'], P['world_per_ours'], P['raw_per_ours']) == \
           (tr.STEEP, tr.BUILD_VARIATION, tr.WORLD_PER_OURS, tr.RAW_PER_OURS)
    src = JS.read_text(encoding='utf-8')
    assert not re.search(r'(?<![\w.])(9|3|0\.625|25\.6|16|285\.7)(?![\w.])', src.split('function decode')[0].replace('i & 7', '')), \
        'terrain.js must take the rules\' numbers from P, not type them'


def _terrain_doc(site, op='raise', **kw):
    st = dict({'op': op, 'r': 120, 's': 40, 'dabs': [site.x, site.y]}, **kw)
    return {'kind': 'terrain', 'strokes': [st], 'why': '试一下', 'level': 'a4', 'at': '2026-11-04T12:00'}


def test_apply_preview_reports_a_cast_point_made_steep(tmp_path):
    """A hill raised on a cast site: the preview says that site is no longer flat and the contract goes red on it;
    --pull names the brushes and the site they cover."""
    m = _a4()
    k = next(n for n, s in m.map.SITES.items() if s.cast)
    s = m.map.SITES[k]
    d = tmp_path / 'proposals'
    d.mkdir()
    (d / 't1.json').write_text(json.dumps(_terrain_doc(s), ensure_ascii=False), encoding='utf-8')
    out = mappage.apply_preview('a4', str(tmp_path))
    assert '1 条地形提议' in out and f'{k} 的施法点不再平' in out
    assert re.search(rf'新红 .*{k}', out), out
    pulled = mappage.pull('a4', str(tmp_path))
    assert '[t1] 地形 1 笔（抬高 1）' in pulled and k in pulled and '试一下' in pulled


def test_lint_on_restores_platmap():
    import contract
    import platmap
    before = (platmap.heights, platmap.walkable, dict(contract._DESIGN))
    with te.lint_on(_ground()):
        assert platmap.heights is not before[0]
    assert (platmap.heights, platmap.walkable, dict(contract._DESIGN)) == before
