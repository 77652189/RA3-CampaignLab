"""Engine probe: does a POWERED defence building fire while its owner is short of power, and how soon does it change
when the power is cut or comes back (missions/powerdef_bench.py)?

s1 owns a SovietBaseDefenseAdvanced (EnergyProduction -75, KindOf +POWERED; SageXML Soviet/Structures line 64-66; weapon
AttackRange 350, Damage 450) and, per variant, a SovietPowerPlant (EnergyProduction +100, line 52). Six player tanks
(NO_ATTACK) stand 175 north of it. Variants: on (plant, supply 100 >= 75), off (no plant), cut (plant, deleted by
NAMED_DELETE at 10 s), back (no plant, one made at 10 s at its waypoint on the s1 team).
Counters: 帧数 (frames from the start), 坦克 (player tanks left, of 6), 首损 (frames counted while all 6 stand: the
frame of the first loss), 事后 (frames since the 10 s event; cut / back).
RESULTS (bench 2026-11-07; script frames run ~15 a second; 帧数 is the frame, one tank lost per shot: damage 450):
  on    CampPdOnFrames_mcp_1107_153616: first loss at frame 111 (首损 111), then one tank per ~125 frames (坦克
        6 -> 5 at 帧数 117, 4 at 238, 3 at 374, 2 at 496, 1 at 616): fires.
  off   CampPdOffFrames_mcp_1107_153902: 坦克 6 and 首损 = 帧数 for all 728 frames: never fires with supply 0 < 75.
  cut   CampPdCutFrames_mcp_1107_154116: first loss 111 as in on; the plant deleted at 帧数 ~150 (事后 starts); 坦克 stays
        5 to 帧数 692 (on's next loss was due ~236, 86 frames after the cut): it stops within a shot interval
        (the 1 s rows cannot say closer).
  back  CampPdBkFrames_mcp_1107_154336: plant made at 帧数 ~150 (事后 starts); first loss at 帧数 475 (事后 ~325, ~22 s
        later; on fired 111 frames after the start), then 坦克 5 -> 4 at 603, -> 3 at 724 (~130 frames apart): it fires
        again after power returns, but only after a delay (the plant's own construction / the coil's power-up is not
        separated here).
  Reading: a POWERED defence with its owner short of power does not fire; cutting the supply stops it within a shot
  interval; restoring it starts it again after about 325 frames (the first shot; not the exact power-up time).
"""
from parts import Script, Test, counted

VARIANTS = ('on', 'off', 'cut', 'back')           # the mission's (missions/powerdef_bench.py), in its order
PLANT = 'SovietPowerPlant'
EVENT, RUN = 10.0, 45.0


def frames(m):
    t = Test()
    v = VARIANTS[m.facts['variant']]
    N_TANKS = m.facts['tanks']
    p1 = m.player('p1')
    start = [('MAP_REVEAL_ALL_PERM', p1)] + [('UNIT_CHANGE_OBJECT_STATUS', m.role(f'tank {k}').name, 'NO_ATTACK', 1)
                                             for k in range(N_TANKS)]
    if v in ('cut', 'back'):
        start.append(('SET_MILLISECOND_TIMER', 'Test Event', EVENT))
    t.scripts.append(Script('Test - start', [], start))
    if v == 'cut':
        t.scripts.append(Script('Test - event', [('TIMER_EXPIRED', 'Test Event')],
                                [('NAMED_DELETE', m.role('plant').name), ('SET_FLAG', 'Test Event Done', 1)]))
    if v == 'back':
        t.scripts.append(Script('Test - event', [('TIMER_EXPIRED', 'Test Event')],
                                [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'UNIT - CNV Pd Plant2', PLANT, m.team('s1'),
                                  m.mark('plant')), ('SET_FLAG', 'Test Event Done', 1)]))
    t.counters.append(('CNV_Pd_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [], [('INCREMENT_COUNTER', 1, 'CNV_Pd_Frames')], once=False))
    counted('CNV_Pd_Tanks', '坦克', t, template='AlliedAntiVehicleVehicleTech1', most=N_TANKS + 1)
    t.counters.append(('CNV_Pd_First', '首损'))
    t.scripts.append(Script('Test - first', [('COUNTER', 'CNV_Pd_Tanks', 2, N_TANKS)],
                            [('INCREMENT_COUNTER', 1, 'CNV_Pd_First')], once=False))
    t.counters.append(('CNV_Pd_After', '事后'))
    t.scripts.append(Script('Test - after', [('FLAG', 'Test Event Done', 1)],
                            [('INCREMENT_COUNTER', 1, 'CNV_Pd_After')], once=False))
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {f'powerdef_{v}': {'frames': frames} for v in VARIANTS}
