"""SPN closure: four native disguise lanes, Friend/Neutral for both hosts.

PREDICT 1111 in every lane: both native power filters accept these relations.
Each lane independently latches its 10 UNRES hit; no scripted disguise bit.
Spy Friend/Neutral and transport Friend/Neutral share one map and four counters.
Relation overrides use the previously measured script interface. Copied native
hosts retain their weapon and consumer; only the marker and unique IDs change.
Identity, acquisition, cancellation and precise unpack timing remain gaps.
Evidence and the six-weapon closure table: work/re/c_spnclosure_report.md.
MEASURED 2026-11-13: one game, retry=0, PASS in 125.8s; s1-4 all1100,
s5 1111/1111/1110/1110, s6-15 all1111. The transport transition remains
unmodeled; the settled relation boundary does not validate copied identity.
"""
from copy import deepcopy

from checks import engine_spndisguise as spy, engine_spntrans as transport
from model import Script


def mission():
    m = spy.mission()
    tr = transport.mission()
    m.name = 'CampSPNRel'
    # Keep the existing four published pads; replace each caster with an intact
    # native positive, never a removed-nugget or scripted-condition control.
    m.units = []
    m.objects = []
    for i, lane in enumerate(spy.CASES):
        source = spy.mission() if i < 2 else tr
        prefix = 'SPD' if i < 2 else 'SPT'
        unit = source.units[0]
        unit = deepcopy(unit)
        original = unit.id
        unit.id = original.replace('Base', lane.title())
        unit.xml = unit.xml.replace(original, unit.id)
        for link in unit.link:
            old = link.split(':', 1)[1]
            unit.xml = unit.xml.replace(old, old.replace('Base', lane.title()))
        unit.link = [x.replace('Base', lane.title()) for x in unit.link]
        m.units.append(unit)
        m.put(unit.id, lane+' gun', side='p1', angle=1.5708,
              name='SPD '+lane+' caster')
        victim = next(o.template for o in source.objects if o.name == prefix+' base victim')
        side = 's2' if i % 2 == 0 else 's3'
        crew = m.crew('SPNFriend' if side == 's2' else 'SPNNeutral', side=side)
        m.put(victim, lane+' gun', 0, 250, side=side,
              angle=4.7124, name='SPD '+lane+' victim', props={'originalOwner': crew})
    return m


def check(m):
    t = spy.check(m)
    for s in t.scripts:
        s.do = [a for a in s.do if a[0] != 'UNIT_SET_MODELCONDITION_GENERIC']
    relations = []
    for side, relation in [('s2', 'Friend'), ('s3', 'Neutral')]:
        team = m.teams['SPNFriend' if side == 's2' else 'SPNNeutral']
        relations += [('PLAYER_SET_OVERRIDE_RELATION_TO_TEAM', m.player('p1'), team, relation),
                      ('TEAM_SET_OVERRIDE_RELATION_TO_PLAYER', team, m.player('p1'), relation)]
    t.scripts.insert(0, Script('Test - relation setup', [], relations))
    t.expect = [(label, 12, '==', 1111, 14) for _, label in t.counters]
    return t


MISSION = {'engine_spnrelations': mission}
CHECKS = {'engine_spnrelations': {'a': check}}
