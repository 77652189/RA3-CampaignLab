"""Engine unit test: a whole-team order to a team nobody has used yet (E3).

Bench 2026-11-04: an order to a team with nobody on it yet is not kept for a unit put on it afterwards (early); a unit
put on the team and the order in the same script go together (fresh); a team never used reads neither destroyed nor
having units, with its one member it has units, and once that member is deleted it reads destroyed (ghost). So
TEAM_DESTROYED of a team that never had anyone stays false. Three guardians stand on the player's default team in the west field, `far` 600 north of them
(the team bench's leg, land all the way); each team below is a fresh one (Mission.crew), used only as written:
  early (tank 1): MOVE_TEAM_TO at 1 s, tank 1 put on the team at 3 s, no order after -- does tank 1 ever go?
  fresh (tank 2): tank 2 put on the team and the team ordered in one script at 1 s (what Mission.order writes) --
    tank 2 goes;
  ghost: TEAM_DESTROYED and TEAM_HAS_UNITS read every frame; tank 3 put on it at GHOST_AT s and deleted 4 s later --
    what the two read never used, with a member, and emptied.
"""
from maps import island
from parts import Mission, Script, Test, counted, square

GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
GHOST_AT, RUN = 6.0, 40.0
FAR = 'Test Far Area'


def mission():
    m = Mission(name='CampTeamE', map=island, facts={})
    for k, dy in enumerate((-60, 0, 60), 1):
        m.put(GUARDIAN, 'west field', dy, -300, name=f'UNIT - CNV Fresh Tank {k}', role=f'tank {k}', angle=0.0)
    m.waypoint('far', 'CNV Fresh Far', 'west field', 0, 300)
    for key in ('Early', 'Fresh', 'Ghost'):
        m.crew(key)
    return m


def fresh(m):
    t = Test()
    early, fresh_, ghost = (m.teams[key] for key in ('Early', 'Fresh', 'Ghost'))
    tank = {k: m.role(f'tank {k}').name for k in (1, 2, 3)}
    t.areas[FAR] = square(*m.point('far'), 60.0)
    t.scripts += [
        Script('Test - start', [], [('SET_MILLISECOND_TIMER', 'Test Order', 1.0), ('SET_MILLISECOND_TIMER', 'Test Join', 3.0),
                                    ('SET_MILLISECOND_TIMER', 'Test Ghost', GHOST_AT)]),
        Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
               [('MOVE_TEAM_TO', early, m.mark('far')),
                ('UNIT_SET_TEAM', tank[2], fresh_), ('MOVE_TEAM_TO', fresh_, m.mark('far'))]),
        Script('Test - join', [('TIMER_EXPIRED', 'Test Join')], [('UNIT_SET_TEAM', tank[1], early)]),
        Script('Test - ghost', [('TIMER_EXPIRED', 'Test Ghost')], [('UNIT_SET_TEAM', tank[3], ghost),
                                                                   ('SET_MILLISECOND_TIMER', 'Test Ghost Out', 4.0)]),
        Script('Test - ghost out', [('TIMER_EXPIRED', 'Test Ghost Out')], [('NAMED_DELETE', tank[3])])]
    counted('CNV_Fresh_Early', '早令车到终点', t, named=tank[1], area=FAR)
    counted('CNV_Fresh_Fresh', '同令车到终点', t, named=tank[2], area=FAR)
    for counter, label, cond in (('CNV_Fresh_Gone', '空队算全灭', 'TEAM_DESTROYED'),
                                 ('CNV_Fresh_Has', '空队有人', 'TEAM_HAS_UNITS')):
        t.counters.append((counter, label))
        t.scripts += [Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False),
                      Script(f'Test - {counter}', [(cond, ghost)], [('SET_COUNTER', counter, 1)], once=False)]
    t.expect += [('早令车到终点', 0, '==', 0), ('同令车到终点', 0, 'ever==', 1),
                 ('空队有人', 0, '==', 0, GHOST_AT - 1), ('空队算全灭', 0, '==', 0, GHOST_AT + 3),
                 ('空队有人', GHOST_AT, '==', 1, GHOST_AT + 3),
                 ('空队有人', GHOST_AT + 5, '==', 0), ('空队算全灭', GHOST_AT + 5, '==', 1)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=len(t.counters)))]
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_team': mission}
CHECKS = {'engine_team': {'fresh': fresh}}
