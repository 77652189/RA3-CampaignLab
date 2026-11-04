"""The editable map page (experimental/mappage, ADR 0017): its rules are the --show contract, problems land on the map,
--pull turns the page's proposals into a list naming sites."""
import dataclasses
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('mappage', ROOT / 'experimental' / 'mappage' / 'mappage.py')
mappage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mappage)


def _a4():
    m, _, _ = mappage.build.resolve('a4', '')
    return mappage.parts.merged(m, None)


def test_page_rules_are_the_show_contract():
    """The page's verdict is the very line `build.py a4 --show` prints."""
    show = mappage.build.show('a4')
    line = next(x for x in show.splitlines() if x.startswith('contract: '))
    r = mappage.rules(_a4())
    assert line.split('\n')[0] == f'contract: {r["show"]}'
    drawn = [p['text'] for rule in r['rules'] for p in rule['problems']]
    assert sorted(drawn) == sorted(r['total'])


def test_a_broken_cast_point_is_drawn_at_its_site():
    """A spell mark moved off its cast site fails cast_points_clear, and the page puts the problem where the stray mark stands."""
    m = _a4()
    wp, site = next(iter(m.spells.items()))
    m.waypoints = dict(m.waypoints, **{wp: (m.waypoints[wp][0] + 50, m.waypoints[wp][1])})
    cast = next(rule for rule in mappage.rules(m)['rules'] if rule['fn'] == 'cast_points_clear')
    assert cast['problems'], 'the moved mark should fail'
    assert site in cast['problems'][0]['text']
    assert cast['problems'][0]['at'] == m.waypoints[wp]          # drawn where the stray mark stands


def test_every_a4_site_has_a_chinese_name():
    """The page shows each site as 中文名 + code name; the names live beside the map module (maps/<map>_names.py)."""
    sites = _a4().map.SITES
    names = mappage.site_names(_a4().map)
    assert sorted(k for k in sites if not names.get(k)) == [], 'add these to the map\'s _names.py'
    assert sorted(set(names) - set(sites)) == [], 'names for sites the map no longer has'


def test_locate_reads_coordinates_and_sites():
    sites = {'gate 1': mappage.parts.Site(100.0, 200.0)}
    m = dataclasses.make_dataclass('M', [('spells', dict)])({})
    assert mappage.locate('OreNode at (12, -3.5): not made', m, sites) == (12.0, -3.5)
    assert mappage.locate('site gate 1: 3 cells of its cast circle', m, sites) == (100.0, 200.0)
    assert mappage.locate('no place here', m, sites) is None


def test_pull_lists_a_dragged_site_and_a_note(tmp_path):
    s = _a4().map.SITES
    k = next(n for n, v in s.items() if v.r < 1000 and n != 'start')
    docs = {'documents': [
        {'id': 'p1', 'data': {'kind': 'move', 'site': k, 'from': [s[k].x, s[k].y], 'to': [s[k].x + 150, s[k].y],
                              'why': '往东挪一点', 'at': '2026-11-04T10:00'}},
        {'id': 'p2', 'data': {'kind': 'note', 'at_xy': [s['start'].x + 10, s['start'].y], 'why': '这里太空',
                              'at': '2026-11-04T10:01'}}]}
    f = tmp_path / 'p.json'
    f.write_text(json.dumps(docs, ensure_ascii=False), encoding='utf-8')
    out = mappage.pull('a4', str(f))
    assert '2 条' in out
    assert f'挪地点 {k!r}' in out and '挪了 150' in out and '往东挪一点' in out
    assert "地点 'start'" in out and '这里太空' in out


def test_pull_reads_the_artifactdata_folder(tmp_path):
    """ArtifactData list with out_dir writes <out_dir>/proposals/<id>.json, the body only; other levels are skipped."""
    d = tmp_path / 'proposals'
    d.mkdir()
    (d / 'n1.json').write_text(json.dumps({'kind': 'block', 'points': [[100, 2400], [100, 2600]], 'why': '堵西口',
                                           'level': 'a4', 'at': 'b'}, ensure_ascii=False), encoding='utf-8')
    (d / 'n2.json').write_text(json.dumps({'kind': 'note', 'at_xy': [0, 0], 'level': 'a5', 'at': 'a'}), encoding='utf-8')
    out = mappage.pull('a4', str(tmp_path))
    assert '1 条' in out and '[n1] 画挡路线：2 个点，长 200' in out and '堵西口' in out
