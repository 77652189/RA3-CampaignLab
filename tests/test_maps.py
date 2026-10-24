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
        problems = platmap.lint(mod.LAYOUT, mod.SITES, getattr(mod, 'OBJECTS', []))
        assert not problems, f'{mod.__name__}: ' + '; '.join(problems)


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
