"""CannotAttackTargetReaction measured lifecycle, replayed by test_ai_cannot_reaction.

SDK predicts Ignore continues, Disband releases, TreatLikeSuccess uses RAMPAGE.
Counters only validate the scene and its game clock. Team lifecycle/aims must
be read from CNVTeams, not inferred from no damage. See work/re/c_cannot_report.md.

MEASURED 2026-11-13, one three-build round: all scene checks PASS.
Ignore: two members from carrier frame 21, air tactical target from 51,
retained through frame 1771. Disband: target at 51, zero members at 95,
two again at 97, repeated clearing/recruitment. TreatLikeSuccess/RAMPAGE:
air target at 51, ground yard target at 92, enemy micro state 6 at 500.
All three keep two living Guardians and zero air-target damage. Carrier
frames are not map-counter frames. Exact dispatch timing, ReturnHomeAndDisband
and other tactics remain gaps; consumer boundaries are in work/re/e122_cannot.md.
"""
from model import Script, Test, counted, square


def probe(m):
    t = Test()
    t.counters += [('CNV_CA_Frame', '帧数'), ('CNV_CA_Hurt', '空靶受伤')]
    t.scripts += [Script('Cannot - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                  Script('Cannot - frame', [], [('INCREMENT_COUNTER', 1, 'CNV_CA_Frame')], once=False),
                  Script('Cannot - hurt', [('UNIT_HEALTH', m.role('air target').name, 0, 100)],
                         [('SET_COUNTER', 'CNV_CA_Hurt', 1)])]
    counted('CNV_CA_Own', '坦克数', t, template=m.cnv_units[0], player=m.player('s1'))
    t.areas['CNV Cannot Home'] = square(*m.site('east base'), 450)
    counted('CNV_CA_Home', '在家', t, template=m.cnv_units[0], player=m.player('s1'), area='CNV Cannot Home')
    t.expect = [('帧数', 1, 'ever>=', 900, 125), ('坦克数', 1, '==', 2, 125),
                ('空靶受伤', 1, '==', 0, 125)]
    t.bench = [('bench_watch', dict(seconds=127, every=3, sheet=False, lines=4))]
    return t


CHECKS = {name: {'r': probe} for name in ('aicantig', 'aicantdi', 'aicantsu')}
