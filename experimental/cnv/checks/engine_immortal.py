"""Engine probe: damage floor and explicit removal of a retail dummy body.

BENCHED 2026-11-09 (engine line C round 14; the readings are at the end of this docstring). The prediction below held on
everything but one thing: after the delete the health counter stays 1, it is not written 0 (a dead object's counter freezes).
Retail CPDummyTarget is placeable (EditorName / EditorSorting SYSTEM), immobile,
selectable with a health bar, NoArmor and MaxHealth=100. Unlike BaseRock it is
not UNATTACKABLE; its invisible in-game model does not affect named script reads.
Source data: work/downloads/ra3sdk_v3/sdk3/XMLFiles/Civilian/Props/CPDummyTarget.xml.

Two lanes (check variants, the same object and damage in each):
  a: Test Go at 1 s applies NAMED_DAMAGE 200 (= twice retail MaxHealth).
     Read health through a counter throughout the next 10 s; bench_watch every 0.5 s.
  b: as a, then NAMED_KILL at Go+10 s, NAMED_DELETE at Go+11 s.
     The gone counter becomes 1 when NAMED_DESTROYED observes the deletion.

PREDICTED readings (health / gone): before Go 100 / 0; after the hit 1 / 0
at every half-second observation for 10 s. In b, KILL leaves 1 / 0; after
DELETE the gone counter is 1 and health is 0: the reader runs later in that
same frame and writes 0 for a dead object; subsequent reads retain that 0.
Only the gone counter establishes removal. Run a for 12 s, b for 14 s.

Rule, not a fit: the Generals reference body's internalChangeHealth clamps
changes to leave at least 1 HP, so 100 - 200 becomes 1 HP = 1 percent.
ScriptActions::doNamedKill calls Object::kill (MaxHealth unresistable damage),
which is clamped too. doNamedDelete calls GameLogic::destroyObject directly;
it bypasses health changes. RA3 behavior remains a prediction pending line C.

Bench 2026-11-09 (the ImmortalBody module of CPDummyTarget; lanes a, b, c = the kill alone, no delete, 14 s):
  a: health 1 (percent), gone 0, from the hit at 1 s to the end (s1-s13) -- the 200 hit leaves 1 %, the dummy lives on.
  c: the same 1 / 0 through s15 after the NAMED_KILL at 11 s -- a script kill does not remove it either (floor of 1).
  b: 1 / 0 to s10, then 1 / 1 from s11 (the bench clock labels run about a second behind the mission's): the delete
     removes it; the health counter keeps 1 beside gone 1 (it froze), the predicted 0 was wrong.
"""
from maps import niagara
from parts import Mission, Script, Test

TEMPLATE = 'CPDummyTarget'
UNIT = 'UNIT - CNV Immortal Dummy'
MAX_HEALTH = 100                 # retail CPDummyTarget.xml, not a probe override
GO, OBSERVE = 1.0, 10.0


def mission():
    m = Mission(name='CampImmortal', map=niagara, units=[], facts={})
    m.put(TEMPLATE, 'west field', -120.0, 260.0, side='p1', role='dummy', name=UNIT)
    return m


def build_test(m, which='a'):
    t = Test()
    t.counters = [('CNV_Immortal_Health', '血量'), ('CNV_Immortal_Gone', '消失')]
    t.scripts.append(Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        ('SET_MILLISECOND_TIMER', 'Test Go', GO)]))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], [
        ('NAMED_DAMAGE', UNIT, 2 * MAX_HEALTH),
        ('SET_MILLISECOND_TIMER', 'Test Kill', OBSERVE)]))
    if which in 'bc':                   # c: the kill alone, no delete (bench 11-09 b: gone at s11.1, before the delete)
        t.scripts.append(Script('Test - kill', [('TIMER_EXPIRED', 'Test Kill')], [
            ('NAMED_KILL', UNIT)] + ([('SET_MILLISECOND_TIMER', 'Test Delete', 1.0)] if which == 'b' else [])))
    if which == 'b':
        t.scripts.append(Script('Test - delete', [('TIMER_EXPIRED', 'Test Delete')], [('NAMED_DELETE', UNIT)]))
    t.scripts += [
        Script('Test - health', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', UNIT,
                                     'CNV_Immortal_Health')], once=False),
        Script('Test - gone', [('NAMED_DESTROYED', UNIT)], [('SET_COUNTER', 'CNV_Immortal_Gone', 1)])]
    run = 12.0 if which == 'a' else 14.0
    t.expect = [('血量', 0, 'ever<=', 1, run)]
    if which == 'b':
        t.expect.append(('消失', 0, 'ever>=', 1, run))
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=run))]
    return t


MISSION = {'engine_immortal': mission}
CHECKS = {'engine_immortal': {w: (lambda m, w=w: build_test(m, w)) for w in 'abc'}}
