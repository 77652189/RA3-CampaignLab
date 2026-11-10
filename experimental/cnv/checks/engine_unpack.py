"""Engine unit test: NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT(unit, Command_UnPack..., waypoint) with the waypoint
AWAY from the unit -- retail's 264 uses are mostly deploys at a point (MCVs 47, Japanese eggs ~90, the Allied miner 9):
every one a ReplaceSelfSpecialAbility on SpecialPower_UnpackReplaceSelf (StartAbilityRange 2, object geometry,
ReplacementTemplate, PackTime 2-3 s). engine_build a measured the deploy on the spot (the yard 6 frames after the
order, the MCV's name and health passed on); here the unit stands 400 west of the point.

On the Niagara map the player's unit (named) in the west field, the waypoint 400 east of it, ordered at 1 s:
  mcv  AlliedMCV -> AlliedConstructionYard (Command_UnPackAlliedMCV)
  egg  JapanBaseDefenseEgg -> JapanBaseDefense (Command_UnPackJapanBaseDefenseEgg)
Counters, frames added from the order on (four lines):
  帧数    frames since the order
  车帧    +1 a frame the player owns the unit's template, +1000 a frame one stands within 100 of the waypoint
  场帧    +1 a frame the replacement stands within 100 of the waypoint, +1000 a frame the player owns one anywhere
  名字帧  +1 a frame the unit's name is not destroyed (passed on: counts on after the replacement)

Bench 11-10 (round 138), last reading s41 (帧数 车帧 场帧 名字帧):
  mcv  CampUnpackMcvGo_mcp_1110_022434: 631 31121 510510 631 -- the MCV drives there (within 100 of the point from
       frame 90), is gone at frame 121, the yard stands on the point from frame 121 (owned and in the area alike),
       the name passes on (名字帧 = 帧数).
  egg  CampUnpackEggGo_mcp_1110_022725: 634 29112 522 634 -- the same: within 100 from frame 83, the defense on the
       point from frame 112, the name passes on; but PLAYER_HAS_OBJECT_COMPARISON(JapanBaseDefense) never held
       (场帧's thousands 0) while the area count did -- not looked into (still unfolding: not counted as owned?).
Simulator (sim: NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT with SpecialPower_UnpackReplaceSelf, REPLACE_FRAMES 6;
tests/test_simbench.py test_mcv_deploys_at_a_far_waypoint_as_the_bench): mcv 586 44128 458458 586 (the yard from
frame 128). egg 586 39108 478478 586 (round 139: the defense from frame 108; the egg came into the unit table once
simunits.resolve read EditorSorting / KindOf up its chain from BaseEgg -- its own LocomotorSet writes Speed 60;
test_nanocore_deploys_at_a_far_waypoint_as_the_bench). The bench's owned count of the defense (场帧's thousands 0)
is not modelled: the sim counts it owned.
"""
from maps import niagara
from parts import Mission, Script, Test, square

KINDS = {'mcv': ('AlliedMCV', 'AlliedConstructionYard', 'Command_UnPackAlliedMCV'),
         'egg': ('JapanBaseDefenseEgg', 'JapanBaseDefense', 'Command_UnPackJapanBaseDefenseEgg')}
VARIANTS = tuple(KINDS)
AT, THERE = ('west field', -200.0, 0.0), ('west field', 200.0, 0.0)
NAME = 'UNIT - CNV Unpack'
RUN = 40.0


def mission(variant='mcv'):
    unit, yard, _ = KINDS[variant]
    m = Mission(name=f'CampUnpack{variant.title()}', map=niagara, units=[],
                facts={'variant': VARIANTS.index(variant)})
    m.spawns |= {yard}
    m.put(unit, AT[0], *AT[1:], angle=0.0, role='unit', name=NAME)
    m.waypoint('there', 'Test Unpack There', *THERE)
    return m


def frames(m):
    t = Test()
    unit, yard, button = KINDS[VARIANTS[m.facts['variant']]]
    p1 = m.player('p1')
    t.areas['Test There'] = square(*m.point('there'), 100.0)
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')],
                            [('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', NAME, button, m.mark('there')),
                             ('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)

    def per_frame(counter, label, rows):
        t.counters.append((counter, label))
        t.scripts += [Script(f'Test - {counter} {k}', [going, cond], [('INCREMENT_COUNTER', step, counter)],
                             once=False) for k, (cond, step) in enumerate(rows)]

    per_frame('CNV_Unpack_Frames', '帧数', [(going, 1)])
    per_frame('CNV_Unpack_Unit', '车帧', [(('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, unit,
                                            'Test There'), 1000),
                                          (('PLAYER_HAS_OBJECT_COMPARISON', p1, 3, 1, unit), 1)])
    per_frame('CNV_Unpack_Yard', '场帧', [(('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, yard,
                                            'Test There'), 1),
                                          (('PLAYER_HAS_OBJECT_COMPARISON', p1, 3, 1, yard), 1000)])
    per_frame('CNV_Unpack_Name', '名字帧', [(('NAMED_NOT_DESTROYED', NAME), 1)])
    t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {f'engine_unpack_{v}': (lambda v=v: mission(v)) for v in VARIANTS}
CHECKS = {f'engine_unpack_{v}': {'go': frames} for v in VARIANTS}      # mod CampUnpackMcvGo: 15 characters at most
