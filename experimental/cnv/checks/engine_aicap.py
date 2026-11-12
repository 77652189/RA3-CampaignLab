"""SpecificUnitCap: MEDIUM cap two, HARD-only cap two, and uncapped control.

Prediction (INFERRED model rule): MEDIUM Peacekeepers reach two and never
exceed it; HARD-only and control reach at least three. Javelins remain
available in every build. Counts are living owned units, not queue entries.
All builds run on the same MEDIUM setting, so the mask alone is varied.
Evidence and scope: work/re/e_aicap_e80.md.
"""
from parts import Script, Test, counted


def a(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    for counter, label, template in (
            ('CNV_CapPk', '维和总数', 'AlliedAntiInfantryInfantry'),
            ('CNV_CapJav', '标枪总数', 'AlliedAntiVehicleInfantry')):
        m.spawns.add(template)
        counted(counter, label, t, template=template, player=m.player('s1'))
    active = m.facts['cap active']
    t.expect = [('维和总数', 70., '<=', 2, 100.)] if active else []
    t.expect += [('维和总数', 70., 'ever>=', 2 if active else 3, 100.),
                 ('标枪总数', 70., 'ever>=', 3, 100.)]
    t.bench = [('bench_watch', dict(seconds=104., every=1, sheet=False, lines=2))]
    return t


def b(m):
    """Discriminate an opening-only bypass from caps ignored after the opening.

    First aicapmed:a made three Peacekeepers by s54 despite cap two.
    Preserve that failed prediction in a; this longer run tests whether the
    same cap prevents further production once the opening finishes.
    """
    t = a(m)
    active = m.facts['cap active']
    t.expect = [('维和总数', 150., '<=', 2, 200.)] if active else []
    t.expect += [('维和总数', 150., 'ever>=', 2 if active else 4, 200.),
                 ('标枪总数', 150., 'ever>=', 4, 200.)]
    t.bench = [('bench_watch', dict(seconds=204., every=1, sheet=False, lines=2))]
    return t


CHECKS = {name: {'a': a, 'b': b} for name in ('aicapctrl', 'aicapmed', 'aicaphard')}
