"""Tech minimum-distance contrast: oil/barracks/tank/home at s40.

The oil uses the host's plant counter. Predicted zero/control: 4/0/0/0;
2000: 0/0/0/4. Counters establish movement, not live candidate distance.
Original evidence: work/re/c_mindist_report.md.
Two-oil contrast: minimum 0 selects near oil (4/0/0/4), 350 stays home
(0/0/4/4), contradicting the model's far-oil prediction. Qualification and
fallback remain gaps; see work/re/c_mindist_pair_report.md.
"""
from checks.engine_aitargetpick import a
from parts import Script, Test, counted, square


def pair(m):
    """Read both neutral oil destinations and survival, at s40.

    Prediction: minimum 0 -> near/far/home/total 4/0/0/4;
    minimum 350 -> 0/4/0/4. See work/re/c_mindist_pair_report.md.
    Observed: 0 -> 4/0/0/4; 350 -> 0/0/4/4 (original prediction FAIL).
    No claim about exact boundary, far qualification or fallback order.
    """
    t = Test()
    t.scripts.append(Script('Minimum pair reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.scripts.append(Script('Minimum pair keep', [],
        [('UNIT_SET_HEALTH', m.role(role).name, 100.0) for role in ('plant', 'barracks', 'tank')], once=False))
    tank, = m.cnv_units
    for role, label, key in (('plant', '近油井', 'near'), ('barracks', '远油井', 'far')):
        obj = m.find(m.role(role).name)
        area = 'Minimum pair ' + key
        t.areas[area] = square(obj.x, obj.y, 340)
        counted('CMP_' + key, label, t, template=tank, player=m.player('s1'), area=area)
        t.expect.append((label, 40, '==', m.facts['expect ' + key + ' oil'], 41))
    x, y = m.site('east base')
    t.areas['Minimum pair home'] = [(x-300, y-400), (x+300, y-400), (x+300, y+450), (x-300, y+450)]
    counted('CMP_home', '在家', t, template=tank, player=m.player('s1'), area='Minimum pair home')
    counted('CMP_total', '总数', t, template=tank, player=m.player('s1'))
    t.expect += [('在家', 40, '==', 0, 41), ('总数', 40, '==', 4, 41)]
    t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=4))]
    return t

CHECKS = {build: {'a': a} for build in ('aimind0', 'aimindhi', 'aimindctl')}
CHECKS.update({build: {'a': pair} for build in ('aimindpair0', 'aimindpair350')})
