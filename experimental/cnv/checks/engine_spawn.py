"""Engine unit test: spawned and slaved objects (ADR 0019 layer 2, batch 4; docs/engine/spawn.md) -- the Allied war
factory's repair drones (SpawnBehavior: 3 at once, a dead one replaced 10 s later, all killed with the factory;
the drones' SlavedUpdate leash 200, their AttachUpdate flies to a hurt allied vehicle within 200).

On the range probe map (maps/probe_range.py, flat), three of the player's war factories, three power plants so none
is short of power (KillSpawnsOnDisabled):

  kill     'base gun'    NAMED_KILL at KILL: do its drones die with it?
  delete   'high gun'    NAMED_DELETE at KILL: are its drones taken away?
  keep     'order gun'   the control; a hurt Guardian ('near', NEAR north of it, 20 %) and another ('far', FAR
                         east, 20 %): which do its drones fly to? At ZAP everything of the player's within ZAP_R
                         of near is killed (UNIT_KILL_ALL_IN_AREA): near and the drone mending it. When is it
                         replaced?

Counters (the bench reads all four):
  无人机总数  the player's AlliedWarFactoryRepairDrone count
  厂旁     drones within AROUND of the keep factory (ones), the kill one (tens), the delete one (hundreds); 4 = 4+
  车旁     drones within 60 of near (ones), of far (tens)
  近车血量  near's health % (mended from 20 by an attached drone, 0 once zapped)
All drone counts by KindOf DRONE (see spawn_test: a template count does not see them).

Read (测, 2026-11-05, run CampSpawnSpawn_mcp_1105_052200, PASS; the bench's seconds ~1 s ahead of the timers):
  总数 9, 厂旁 333 from s1; s11 both doomed factories' drones gone together (9 -> 3, 333 -> 3); 车旁 1 from s1
  (3 at s2), 0 from s12; 近车 20 -> 58 by s10 (~5.5 %/s), 0 at s11. The zap killed near but not its drone (total
  stayed 3): the replace delay was not measured. docs/engine/spawn.md.
"""
from maps import probe_range
from parts import Script, Test, counted, kindof, square

FACTORY, DRONE = 'AlliedWarFactory', 'AlliedWarFactoryRepairDrone'
POWER, GUARDIAN = 'AlliedPowerPlant', 'AlliedAntiVehicleVehicleTech1'
SITES = {'kill': 'base gun', 'delete': 'high gun', 'keep': 'order gun'}
NEAR, FAR = 170.0, 380.0         # from the keep factory's centre (its footprint radius 60; the leash 200)
AROUND, ZAP_R = 300.0, 45.0
ZAP, KILL, RUN = 12.0, 12.0, 40.0


def mission():
    from parts import Mission
    m = Mission(name='CampSpawn', map=probe_range, units=[], facts={})
    for part, site in SITES.items():
        m.put(FACTORY, site, side='p1', role=f'{part} factory', name=f'UNIT - CNV Spawn {part.title()}')
    for k in (1, 2, 3):
        m.put(POWER, f'power {k}', side='p1', role=f'power {k}', name=f'UNIT - CNV Spawn Power {k}')
    m.put(GUARDIAN, SITES['keep'], 0, NEAR, side='p1', role='near', name='UNIT - CNV Spawn Near')
    m.put(GUARDIAN, SITES['keep'], FAR, 0, side='p1', role='far', name='UNIT - CNV Spawn Far')
    m.spawns.add(DRONE)                         # the factories make them: the counters may name the template
    return m


def spawn_test(m):
    t = Test()
    for part, site in SITES.items():
        t.areas[f'Test {part.title()}'] = square(*m.site(site), AROUND)
    t.areas['Test Near'] = square(*m.site(SITES['keep'], 0, NEAR), 60)
    t.areas['Test Far'] = square(*m.site(SITES['keep'], FAR, 0), 60)
    t.areas['Test Zap'] = square(*m.site(SITES['keep'], 0, NEAR), ZAP_R)
    p1 = m.player('p1')
    n = lambda part: m.role(part).name          # noqa: E731
    t.scripts.append(Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', p1), ('UNIT_SET_HEALTH', n('near'), 20.0), ('UNIT_SET_HEALTH', n('far'), 20.0),
        ('SET_MILLISECOND_TIMER', 'Test Zap', ZAP), ('SET_MILLISECOND_TIMER', 'Test Kill', KILL)]))
    t.scripts.append(Script('Test - zap', [('TIMER_EXPIRED', 'Test Zap')],
                            [('UNIT_KILL_ALL_IN_AREA', p1, 'Test Zap')]))
    t.scripts.append(Script('Test - kill', [('TIMER_EXPIRED', 'Test Kill')],
                            [('NAMED_KILL', n('kill factory')), ('NAMED_DELETE', n('delete factory'))]))
    # the drones are counted by KindOf DRONE (only the player has any): bench 11-05 run 051912, a template count
    # (SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER, PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA) read 0 throughout
    # while the drones flew about the keep factory
    drone = kindof('DRONE')
    t.areas['Test All'] = square(2500.0, 2500.0, 2700.0)
    counted('CNV_Spawn_All', '无人机总数', t, kind=drone, area='Test All', player=p1, most=12)

    def digits(counter, label, rows):
        """counter = sum over (area, step) of step x min(drones in the area, 4)"""
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        for area, step in rows:
            for k in (1, 2, 3, 4):
                t.scripts.append(Script(f'Test - {counter} {area} {k}', [
                    ('PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA', p1, 3, k, drone, area)],
                    [('INCREMENT_COUNTER', step, counter)], once=False))

    digits('CNV_Spawn_By', '厂旁', [('Test Keep', 1), ('Test Kill', 10), ('Test Delete', 100)])
    digits('CNV_Spawn_Car', '车旁', [('Test Near', 1), ('Test Far', 10)])
    counted('CNV_Spawn_Near', '近车血量', t, health=n('near'))
    # judged loosely (the bench's seconds run ~1 s ahead of the timers): 9 drones early; the killed and the deleted
    # factory's drones gone soon after KILL (厂旁 below 10); the keep factory has 3 again by the end
    t.expect = [('无人机总数', 0, 'ever>=', 9, ZAP - 2), ('厂旁', KILL + 8, '<', 10), ('厂旁', RUN - 2, '>=', 3)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=4))]
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_spawn': mission}
CHECKS = {'engine_spawn': {'spawn': spawn_test}}
