"""RepairUpdate: player-toggled building repair, not engineer or drone healing.

Retail has one declaration, Includes/GenericBuildingRepair.xml, with schema
defaults (10 HP/s, toggleable, not repairable when dead, 50% rebuild cost).
Two Allied power plants (1000 HP, cost 800) start at 50%, with 5000 credits.
Attempt to toggle only the first (sidebar wrench; SDK default C also tried).
PREDICT: selected plant gains 1 percentage point/s to 100; control stays 50.
Cost hypothesis: 200 credits for 500 HP (50% of build cost per full HP bar).
Four counters: repairing HP, untouched HP, credits, frames spent below 100%.
No enemy, AI, engineer, repair drone or economy producer is present.

Bench 2026-11-10: BOTH attempts FAIL, HP 50/50 and credits 5000 throughout
s1-s102. First attempt used C and had an invalid frame comparison (now fixed).
Second used the wrench, counted 626 below-full frames at s40 and 1566 at s102,
but still only selected the plant. Activation failure remains unexplained.
Do not turn this into a PASS by changing expected HP to 50: repair is unmeasured.
Hypotheses and next discriminating run: work/re/handoff-e.md (stop after two).
"""
from maps import probe_range
from parts import Mission, Script, Test, counted


def mission():
    m = Mission(name='CampRepair', map=probe_range, units=[])
    for role, site in (('repair', 'base gun'), ('control', 'high gun')):
        m.put('AlliedPowerPlant', site, name='Repair ' + role, role=role)
    return m


def check(m):
    t = Test()
    player = m.player('p1')
    t.scripts = [Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', player), ('PLAYER_SET_MONEY', player, 5000),
        *[('UNIT_SET_HEALTH', m.role(role).name, 50.0) for role in ('repair', 'control')]])]
    for role in ('repair', 'control'):
        counted('Repair ' + role + ' HP', role + ' HP', t, health=m.role(role).name)
    t.counters += [('Repair money', '资金'), ('Repair frames', '未满帧')]
    t.scripts += [Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', player, 'Repair money')], once=False),
                  Script('Test - frames', [('COUNTER', 'Repair repair HP', 0, 100)],
                         [('INCREMENT_COUNTER', 1, 'Repair frames')], once=False)]
    t.expect = [('repair HP', 90, '==', 100, 100), ('control HP', 1, '==', 50, 100),
                ('资金', 90, '==', 4800, 100)]
    target = m.find(m.role('repair').name)
    watch = dict(every=1, sheet=False, lines=4)
    t.bench = [('bench_watch', dict(watch, seconds=2)),
               ('bench_camera', dict(x=target.x, y=target.y, look=False)),
               ('bench_click', dict(x=1088, y=222, world=False, look=False)),
               ('bench_click', dict(x=target.x, y=target.y, look=False)),
               ('bench_watch', dict(watch, seconds=62))]
    return t


MISSION = {'engine_repair': mission}
CHECKS = {'engine_repair': {'a': check}}
