"""Engine unit test: CREATE_REINFORCEMENT_TEAM(team, waypoint) -- retail's most used action the simulator lacked (753
uses, docs/engine/inventory.md). In RA3 a reinforcement team is a team template in the map's Teams: not a singleton,
teamMaxInstances, seven unit lines teamUnitType / teamUnitMinCount / teamUnitMaxCount (no transport, no origin: no
retail team has one, work/logs/a137_teamkeys.log). Mission.reinforcement writes one (mapxml.add_team).

On the Niagara map the player's template R (teamMaxInstances 1): A = AlliedAntiInfantryInfantry min 2 max 3, B =
AlliedAntiVehicleVehicleTech1 min 1 max 2, made at the spawn waypoint (west field) at 1 s:
  two    again at 3 s, at 5 s MOVE_TEAM_TO the team to the goal waypoint (500 east)
  old    at 1.5 s MOVE_TEAM_TO goal (the first instance only exists), again at 14 s (the first one stands at the goal),
         at 16 s MOVE_TEAM_TO the far waypoint (500 north of the spawn): the old instance goes (到达A falls) or the new
         one (出生A falls)
Counters: 兵A (how many the player owns), 出生A (A in the square of half-side 250 round the spawn), 到达A (A in the
square of half-side 200 round the goal), two: 兵B (owned), old: 远处A (A within 200 of the far waypoint).

Bench 11-10 (round 137):
  two   CampReinfTwoGo_mcp_1110_013013 (counters then 兵A 兵B 出生A 到达A): s1 3 2 3 0 | s2-s8 6 4 6 0 | s9 6 4 4 0 | s10-s26 6 4 3 3 -- a line makes its
        MAX count (3 A, 2 B, not min 2 / 1); the second call past teamMaxInstances 1 makes a second instance all the
        same (6 / 4); the order by the team's name moves ONE instance's three, the other three stay.
  old   CampReinfOldGo_mcp_1110_013618: s1-s4 3 3 0 0 | s5 3 2 0 0 | s6 3 0 1 0 | s7-s12 3 0 3 0 | s13-s17 6 3 3 0 |
        s18-s19 6 3 2 0 | s20 6 4 0 0 | s21 6 5 0 0 | s22 6 4 0 0 | s23 6 3 0 0 | s24 6 3 0 2 | s25-s46 6 3 0 3 -- the
        first instance walks to the goal; made again, the order by the name takes the OLD instance (the goal empties,
        it walks back past the spawn to far), the new three stay at the spawn. (An earlier layout -- second call at 3 s,
        far north of the goal, CampReinfOldGo_mcp_1110_013308 -- could not tell the two apart.)
Simulator (sim.Sim.reinforce, tests/test_simbench.py test_reinforcement_teams_as_the_bench): two ends 6 3 3 4, old
s1 3 3 0 0, s9 3 0 3 0, s14 6 3 3 0, s26 6 3 0 3 -- the same counts, 1-2 s later on the bench's labels.
"""
from maps import niagara
from parts import Mission, Script, Test, counted, square

A, B = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleVehicleTech1'
UNITS = [(A, 2, 3), (B, 1, 2)]
SPAWN, GOAL, FAR = ('west field', 0.0, 0.0), ('west field', 500.0, 0.0), ('west field', 0.0, 500.0)
RUN = {'two': 30.0, 'old': 45.0}
AGAIN, GO = {'two': 3.0, 'old': 14.0}, {'two': 5.0, 'old': 16.0}
VARIANTS = ('two', 'old')


def mission(variant='two'):
    m = Mission(name=f'CampReinf{variant.title()}', map=niagara, units=[], facts={'variant': VARIANTS.index(variant)})
    m.reinforcement('Reinf', UNITS, 'p1', instances=1)
    m.waypoint('spawn', 'Test Reinf Spawn', *SPAWN)
    m.waypoint('goal', 'Test Reinf Goal', *GOAL)
    m.waypoint('far', 'Test Reinf Far', *FAR)
    return m


def frames(m):
    t = Test()
    v = VARIANTS[m.facts['variant']]
    p1, team = m.player('p1'), m.teams['RReinf']
    t.areas['Test Spawn'] = square(*m.point('spawn'), 250.0)
    t.areas['Test Goal'] = square(*m.point('goal'), 200.0)
    t.areas['Test Far'] = square(*m.point('far'), 200.0)
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1),
                                                 ('SET_MILLISECOND_TIMER', 'Test Make', 1.0),
                                                 ('SET_MILLISECOND_TIMER', 'Test First', 1.5),
                                                 ('SET_MILLISECOND_TIMER', 'Test Again', AGAIN[v]),
                                                 ('SET_MILLISECOND_TIMER', 'Test Go', GO[v])]))
    make = [('CREATE_REINFORCEMENT_TEAM', team, m.mark('spawn'))]
    t.scripts.append(Script('Test - make', [('TIMER_EXPIRED', 'Test Make')], make))
    t.scripts.append(Script('Test - again', [('TIMER_EXPIRED', 'Test Again')], make))
    if v == 'old':
        t.scripts.append(Script('Test - first', [('TIMER_EXPIRED', 'Test First')],
                                [('MOVE_TEAM_TO', team, m.mark('goal'))]))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')],
                            [('MOVE_TEAM_TO', team, m.mark('goal' if v == 'two' else 'far'))]))
    counted('CNV_Reinf_A', '兵A', t, template=A)
    counted('CNV_Reinf_SA', '出生A', t, template=A, area='Test Spawn')
    counted('CNV_Reinf_GA', '到达A', t, template=A, area='Test Goal')
    if v == 'two':
        counted('CNV_Reinf_B', '兵B', t, template=B)
    else:
        counted('CNV_Reinf_FA', '远处A', t, template=A, area='Test Far')
    t.bench = [('bench_watch', dict(seconds=RUN[v], every=1, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {f'engine_reinf_{v}': (lambda v=v: mission(v)) for v in VARIANTS}
CHECKS = {f'engine_reinf_{v}': {'go': frames} for v in VARIANTS}      # mod CampReinfTwoGo: 15 characters at most
