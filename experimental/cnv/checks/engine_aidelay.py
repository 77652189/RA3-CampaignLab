"""MaximumDelay-only pair on the successful aimicspon Hunt team.

Prediction before bench: zero permits both warriors to charge together; long
still permits the first charge, then samples a RUSH_ATTACK cooldown in 0..999s.
Thus long is expected to have no simultaneous pair in the automatic window,
but that is a sampled prediction, NOT a deterministic lower-bound guarantee.
Both builds keep MinimumDelay=0, no team delay, the same update/health/targets.
The old aimicmed all-zero run is not a successful delay control.
Only the automatic window is measured; remove the inherited manual warrior.
"""
from missions import aimicro_bench as am
from checks import engine_aimicro as ac


def mission(maximum):
    m = am.built('CampAD' + ('Long' if maximum else 'Zero'), tactic='Hunt', foes=True, spow=True)
    filename, xml, asset = m.assets[0]
    tag = (f'<SpecificSpecialPowerDelay PowerType="RUSH_ATTACK" '
           f'MinimumDelay="0s" MaximumDelay="{maximum}s"/>')
    xml = xml.replace('  </AIMicroManagerData>', '    ' + tag + '\n  </AIMicroManagerData>')
    assert tag in xml
    m.assets[0] = filename, xml, asset
    m.facts['specific maximum'] = maximum
    return m


def check(m):
    t = ac.probe_built(m, 'aimicspon')
    t.scripts = [s for s in t.scripts if s.name not in ('Test - control make', 'Test - control press')]
    t.expect = [('造出', 14, 'ever>=', 2, 50), ('曾冲', 14, 'ever>=', 1, 50)]
    t.expect += [('冲', 14, '<=', 1, 50)] if m.facts['specific maximum'] else [('冲', 14, 'ever>=', 2, 50)]
    t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=4))]
    return t


MISSION = {'aidelay0': lambda: mission(0), 'aidelay999': lambda: mission(999)}
CHECKS = {b: {'a': check} for b in MISSION}
