"""Engine unit tests: can a scripted group move at its slowest member's pace (docs/engine/pathing.md 5; user
2026-11-04 "成群移动按最低速度前进在技术上可行吗？"). engine_paths group showed a whole-team move does not wait: an IFV
(speed 120) at s7, an engineer (40) at s25. On the probe map's pace lanes (maps/probe_range.py: open ground, 1 500
west to east, leg points at 500 and 1 000), an IFV and an engineer each:

  pace   the IFV is our copy with an upgrade whose SPEED modifier is 33% (120 -> 40), granted at s0; one team move
  legs   retail IFV; the pair is moved leg by leg: on to the next leg point only when both stand inside this one
  guard  retail IFV on a team of its own told to guard the engineer (TEAM_GUARD_OBJECT); the engineer alone is moved

Counters (every frame): 1 the IFV at the goal, 10 the engineer at the goal; and per lane 100 while the IFV is more
than 300 ahead of the engineer -- read as: the IFV inside the goal's or the second leg's strip while the engineer is
still west of the first leg's (approximately: strips 300 wide across the lane).

Read (测, 2026-11-04, docs/engine/pathing.md 5): pace 11 at s33 (both at once, never ahead); legs 1 from s25, 11 at
s33 (the IFV waits at each leg point, 8 s early on the last leg); guard 10 at s33 (the IFV never reached the goal).
"""
import os

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, square

IFV = 'AlliedAntiAirVehicleTech1'
ENGINEER = 'AlliedEngineer'
PACED = 'CNV_PacedIfv'
PACE = 0.33                                     # the engineer's 40 over the IFV's 120
RUN = 60.0
LABEL = {'pace': '限速', 'legs': '分段', 'guard': '护卫'}


def paced_ifv(id=PACED, speed=PACE):
    """Retail's IFV under our id with one OBJECT upgrade whose attribute modifier sets SPEED to `speed` of its own."""
    up, mod = f'Upgrade_{id}_Pace', f'AttributeModifier_{id}_Pace'
    x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', f'{IFV}.xml'), encoding='utf-8').read()
    for old, new in ((f'id="{IFV}"', f'id="{id}"'), (f'EditorName="{IFV}"', f'EditorName="{id}"'),
                     ('<Behaviors>', f'''<Behaviors>
			<AttributeModifierUpgrade id="ModuleTag_CNV_Pace" AttributeModifier="{mod}">
				<TriggeredBy>{up}</TriggeredBy>
			</AttributeModifierUpgrade>'''),
                     ('</AssetDeclaration>', f'''	<UpgradeTemplate id="{up}" Type="OBJECT"/>
	<AttributeModifier id="{mod}" Category="NONE">
		<Modifier Type="SPEED" Value="{round(speed * 100)}%"/>
	</AttributeModifier>
</AssetDeclaration>''')):
        assert x.count(old) == 1, (old[:40], x.count(old))
        x = x.replace(old, new, 1)
    return Unit(id, x, link=[f'UpgradeTemplate:{up}', f'AttributeModifier:{mod}'], names={'pace': up},
                what=f'探针：原版多功能步兵车，升级后速度 x{speed:g}', params=dict(speed=speed))


def _key(s):
    return s.title().replace(' ', '')


def mission():
    m = Mission(name='CampPace', map=probe_range, units=[paced_ifv()], facts={})
    for lane in probe_range.PACE:
        m.put(PACED if lane == 'pace' else IFV, f'{lane} start', 0, 40.0, role=f'{lane} ifv',
              name=f'UNIT - CNV Pace {_key(lane)} Ifv')
        m.put(ENGINEER, f'{lane} start', 0, -40.0, role=f'{lane} engineer', name=f'UNIT - CNV Pace {_key(lane)} Engineer')
    return m


def pace(m):
    t = Test()
    ifv = {lane: m.role(f'{lane} ifv').name for lane in probe_range.PACE}
    eng = {lane: m.role(f'{lane} engineer').name for lane in probe_range.PACE}

    def wp(lane, where):
        n = f'Test Pace {_key(lane)} {_key(where)}'
        t.waypoints[n] = m.site(f'{lane} {where}')
        return n

    def area(lane, where, half=100.0):
        n = f'Test Pace {_key(lane)} {_key(where)} Area'
        t.areas[n] = square(*m.site(f'{lane} {where}'), half)
        return n

    paced = next(u for u in m.units if u.id == PACED).names['pace']
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('NAMED_RECEIVE_UPGRADE', paced, ifv['pace'])]
    start += m.order('move', [ifv['pace'], eng['pace']], wp('pace', 'goal'), crew='PacePace')
    start += m.order('move', [ifv['legs'], eng['legs']], wp('legs', 'leg 1'), crew='PaceLegs')
    guards = m.crew('PaceGuardIfv')
    start += [('UNIT_SET_TEAM', ifv['guard'], guards), ('TEAM_GUARD_OBJECT', guards, eng['guard'])]
    start += m.order('move', [eng['guard']], wp('guard', 'goal'), crew='PaceGuardEng')
    t.scripts.append(Script('Test - go', [], start))
    for k, nxt in ((1, 'leg 2'), (2, 'goal')):
        here = area('legs', f'leg {k}', 120.0)
        t.scripts.append(Script(f'Test - legs {k} gathered',
                                [('NAMED_INSIDE_AREA', ifv['legs'], here), ('NAMED_INSIDE_AREA', eng['legs'], here)],
                                m.order('move', [ifv['legs'], eng['legs']], wp('legs', nxt), crew='PaceLegs')))
    for lane in probe_range.PACE:
        counter = f'CNV_Pace_{_key(lane)}'
        t.counters.append((counter, LABEL[lane]))
        goal = area(lane, 'goal', 120.0)
        # strips: the IFV east of the second leg point - 150, the engineer west of the first + 150 -> > 300 apart
        lx, ly = m.site(f'{lane} leg 2')
        fx, _ = m.site(f'{lane} leg 1')
        far, back = f'Test Pace {_key(lane)} Far', f'Test Pace {_key(lane)} Back'
        t.areas[far] = [(lx - 150, ly - 200), (lx + 800, ly - 200), (lx + 800, ly + 200), (lx - 150, ly + 200)]
        t.areas[back] = [(fx - 800, ly - 200), (fx - 350, ly - 200), (fx - 350, ly + 200), (fx - 800, ly + 200)]
        t.scripts += [Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False),
                      Script(f'Test - {counter} ifv', [('NAMED_INSIDE_AREA', ifv[lane], goal)],
                             [('INCREMENT_COUNTER', 1, counter)], once=False),
                      Script(f'Test - {counter} engineer', [('NAMED_INSIDE_AREA', eng[lane], goal)],
                             [('INCREMENT_COUNTER', 10, counter)], once=False),
                      Script(f'Test - {counter} ahead', [('NAMED_INSIDE_AREA', ifv[lane], far),
                                                         ('NAMED_INSIDE_AREA', eng[lane], back)],
                             [('INCREMENT_COUNTER', 100, counter)], once=False)]
    t.expect = []
    t.bench = [('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=3))]
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_pace': mission}
CHECKS = {'engine_pace': {'pace': pace}}
