"""Every map built with the platform generator (experimental/campaign/platmap.py) passes its design lint without the
game: ramps gentle enough, the sites meant for building flat, ore and tech buildings on flat dry ground, every bridge
from bank to bank of one level over water (docs/story/map-language.md 6). Bench 2026-10-23: a gate mid-ramp got no
ice built and a bridge end on a raised plaza -- both now caught here in a second."""
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / 'experimental' / 'cnv' / 'maps'
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
sys.path.insert(0, str(ROOT / 'experimental' / 'campaign'))
import platmap  # noqa: E402


def platform_maps():
    assert MAPS.is_dir(), f'扫描目标不存在，测试会静默通过：{MAPS}'
    out = []
    for p in sorted(MAPS.glob('*.py')):
        if p.stem.startswith('_'):
            continue
        mod = importlib.import_module(f'maps.{p.stem}')
        if hasattr(mod, 'LAYOUT'):
            out.append(mod)
    assert out, 'no map uses the platform generator'
    return out


def test_platform_maps_pass_their_lint():
    for mod in platform_maps():
        problems = platmap.lint(mod.LAYOUT, mod.SITES, getattr(mod, 'OBJECTS', []), getattr(mod, 'SCENERY', []))
        assert not problems, f'{mod.__name__}: ' + '; '.join(problems)


def test_island_scenery_keeps_off_and_counts_as_nothing():
    """The noise island (no layout) dresses its coasts only: its scenery clear of every site on its own heights, and
    none of it a STRUCTURE (CampKinds counts that kind over the whole island, every player's)."""
    import platprops
    isl = importlib.import_module('maps.island')
    assert isl.SCENERY
    assert platprops.lint(None, isl.SITES, [], isl.SCENERY, ground=isl.ground()) == []
    assert not {o.template for o in isl.SCENERY} & platprops.STRUCTURE


def test_scenery_lint_catches_a_prop_on_the_way():
    from parts import Obj
    fest = importlib.import_module('maps.festival')
    on_road = [Obj('HB_Tree03', 3000.0, fest.ROAD_Y, side='civ', site='map'),
               Obj('TH_Fish_Market02', fest.SITES['inside 1'].x, fest.SITES['inside 1'].y, side='civ', site='map')]
    problems = platmap.lint(fest.LAYOUT, fest.SITES, fest.OBJECTS, on_road)
    assert len(problems) == 2 and all(p.startswith('scenery ') for p in problems), problems


def test_every_landmark_placed_by_hand_is_in_the_scenery():
    """A landmark is placed by hand where the map wants it (a torii before the shrine, a lookout over the falls):
    each one is in SCENERY where its list puts it, and place(must=True) raises for one that may not stand there
    rather than dropping it unseen (2026-10-26: six were dropped by the keep-off margins, none in the built map)."""
    import platprops
    for name in ('festival', 'niagara'):
        mod = importlib.import_module(f'maps.{name}')
        have = {(o.template, o.x, o.y) for o in mod.SCENERY}
        missing = [(t, x, y) for t, x, y, _ in mod.LANDMARKS if (t, float(x), float(y)) not in have]
        assert not missing, f'{name}: {missing}'
    fest = importlib.import_module('maps.festival')
    on_plaza = [('TH_PHpagoda_01', fest.SITES['plaza 3'].x, fest.SITES['plaza 3'].y, 0.0)]
    try:
        platprops.place(on_plaza, fest.LAYOUT, fest.SITES, fest.OBJECTS, must=True)
    except ValueError as e:
        assert 'TH_PHpagoda_01' in str(e)
    else:
        raise AssertionError('a landmark on a plaza was dropped, not refused')


def test_place_keeps_wide_footprints_apart():
    """The thinning looks as far as the widest footprint reaches: two houses of radius ~77 130 apart overlap,
    though their 100-wide grid cells are two apart."""
    import platprops
    wide = max(platprops.CATALOG, key=platprops.radius)
    r = platprops.radius(wide)
    assert r > 60
    x, y, d = 1099.0, 1000.0, 1.6 * r
    assert int((x + d) // 100) - int(x // 100) >= 2
    ground = platprops.Ground(None, e=__import__('numpy').full((platmap.CONTAINER[1], platmap.CONTAINER[0]), 300.0))
    out = platprops.place([(wide, x, y, 0.0), (wide, x + d, y, 0.0)], None, ground=ground)
    assert len(out) == 1, out


def test_every_refinery_by_its_ore():
    """Every build's refineries (the map's, the mission's, any side) stand by an ore node, as retail (~180; user
    2026-10-27: ore and its refinery belong together)."""
    import build
    import parts
    bad = []
    for n, (_, checks) in build.MISSIONS.items():
        m, t, _ = build.resolve(n, '')
        bad += [f'{n}: {p}' for p in platmap.ore_lint(list(getattr(m.map, 'OBJECTS', [])) + parts.merged(m, t).objects)]
    assert not bad, '\n'.join(bad)
    from parts import Obj
    far = [Obj('OreNode', 0, 0), Obj('AlliedRefinery', 300, 0)]
    assert platmap.ore_lint(far) and not platmap.ore_lint([far[0], Obj('AlliedRefinery', 180, 0)])


def test_nothing_a_build_places_stands_on_scenery():
    """Every build's objects and waypoints (missions, their checks, the benches) keep clear of its map's scenery:
    a unit is not made inside a tree or a house, a waypoint is not inside a rock."""
    import build
    import parts
    import platprops
    bad = []
    names = [(n, c) for n, (_, checks) in build.MISSIONS.items() for c in [''] + list(checks)]
    for n, c in names + [(p, '') for p in build.PAIRS]:
        m, t, _ = build.resolve(n, c)
        scenery = getattr(m.map, 'SCENERY', [])
        if not scenery:
            continue
        mm = parts.merged(m, t)
        grid = {}
        for o in scenery:
            grid.setdefault((int(o.x // 200), int(o.y // 200)), []).append(o)
        points = [(o.template, o.x, o.y) for o in mm.objects] + [(w, x, y) for w, (x, y) in mm.waypoints.items()]
        for what, x, y in points:
            for i in range(int(x // 200) - 1, int(x // 200) + 2):
                for j in range(int(y // 200) - 1, int(y // 200) + 2):
                    for o in grid.get((i, j), ()):
                        if ((o.x - x) ** 2 + (o.y - y) ** 2) ** 0.5 < platprops.radius(o.template) + 20:
                            bad.append(f'{n} {c}: {what} at ({x:.0f}, {y:.0f}) on {o.template} ({o.x:.0f}, {o.y:.0f})')
    assert not bad, '\n'.join(sorted(set(bad))[:20])


def test_lint_catches_what_the_bench_caught():
    """The two bench failures of 2026-10-23, put back: a building site on a ramp, a bridge end on a plaza."""
    from parts import Obj, Site
    fest = importlib.import_module('maps.festival')
    x, y = fest.SITES['gate 1'].x, fest.SITES['gate 1'].y
    mid_ramp = {'mid ramp': Site(x, fest.ROAD_Y + (fest.RAMP_FOOT + fest.RAMP_LEN / 2), 0.0, '', build=160.0)}
    assert any('mid ramp' in p for p in platmap.lint(fest.LAYOUT, mid_ramp))
    ends = [Obj('HB_Bridge_02', b[0], b[1], side='neutral', flags=f, site='map')
            for b, f in (((x, fest.SITES['plaza 1'].y), 16), ((3890, 3150), 32))]
    assert any('one level' in p or 'dry ground' in p for p in platmap.lint(fest.LAYOUT, {}, ends))
