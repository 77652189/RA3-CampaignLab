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

Round 281 (11-21): pwr = j08's power plant egg at the waypoint; pin / mid = a07 / s07's untargeted press
NAMED_USE_COMMANDBUTTON_ABILITY(egg, Command_UnPackJapanBaseDefenseEgg), standing (pin) or 1 s into its unpack trip
(mid); 场帧's thousands then count a defense within 290 of the start (the way there) instead of owned. Bench pin
CampUnpackPinGo_mcp_1121_123012 633 633 0 633, mid CampUnpackMidGo_mcp_1121_123227 632 632 0 632: nothing unfolds,
and mid's egg stops short of the point. pwr CampUnpackPwrGo_mcp_1121_123504 632 28105 527 632: as egg (the plant from
frame 105, never counted owned). crs = the defense egg pressed at the waypoint with the power plant egg's button (the
same SpecialPower_UnpackReplaceSelf, not in its CommandSet). brk / ref / fac = a07 / j08's barracks, refinery and war
factory eggs at the waypoint, as pwr. Round 322: nvl / jpn = j04's naval MCV and s02's Japanese MCV pressed their
unpack button untargeted, standing (as pin); jpk = s02's escape, the MCV driving to the waypoint pressed the yard's
Command_PackJapanMCV at it 1 s on (not in the MCV's CommandSet). Readings: engine_unpack.readings.toml.
"""
import resources
from maps import niagara
from parts import Mission, Script, Test, square

EGG = ('JapanBaseDefenseEgg', 'JapanBaseDefense', 'Command_UnPackJapanBaseDefenseEgg')
KINDS = {'mcv': ('AlliedMCV', 'AlliedConstructionYard', 'Command_UnPackAlliedMCV'), 'egg': EGG,
         'pwr': ('JapanPowerPlantEgg', 'JapanPowerPlant', 'Command_UnPackJapanPowerPlantEgg'), 'pin': EGG, 'mid': EGG,
         'crs': EGG[:2] + ('Command_UnPackJapanPowerPlantEgg',),
         **{v: (f'Japan{k}Egg', f'Japan{k}', f'Command_UnPackJapan{k}Egg')          # a07 / j08 / s07's eggs
            for v, k in (('brk', 'Barracks'), ('ref', 'Refinery'), ('fac', 'WarFactory'))},
         'nvl': ('AlliedMCV_Naval', 'AlliedConstructionYard', 'Command_UnPackAlliedMCV'),      # j04's, untargeted
         'jpn': ('JapanMCV', 'JapanConstructionYard', 'Command_UnPackJapanMCV'),                # s02's, untargeted
         'jpk': ('JapanMCV', 'JapanConstructionYard', 'Command_PackJapanMCV')}                  # s02's, at a waypoint
PLAIN = ('pin', 'nvl', 'jpn')       # pressed untargeted, standing
VARIANTS = tuple(KINDS)
AT, THERE = ('west field', -200.0, 0.0), ('west field', 200.0, 0.0)
NAME = 'UNIT - CNV Unpack'
RUN = 40.0


def mission(variant='mcv'):
    unit, yard, _ = KINDS[variant]
    m = Mission(name=f'CampUnpack{variant.title()}', map=resources.measured(niagara), units=[],
                facts={'variant': VARIANTS.index(variant)})
    m.spawns |= {yard}
    m.put(unit, AT[0], *AT[1:], angle=0.0, role='unit', name=NAME)
    m.waypoint('there', 'Test Unpack There', *THERE)
    m.waypoint('short', 'Test Unpack Short', *AT)
    return m


def frames(m):
    t = Test()
    v = VARIANTS[m.facts['variant']]
    unit, yard, button = KINDS[v]
    p1 = m.player('p1')
    t.areas['Test There'] = square(*m.point('there'), 100.0)
    t.areas['Test Short'] = square(*m.point('short'), 290.0)    # pin / mid: west of There, the egg's way included
    press = ('NAMED_USE_COMMANDBUTTON_ABILITY', NAME, button)
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0),
                                                 ('SET_MILLISECOND_TIMER', 'Test Mid', 2.0)]))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')],
                            [press if v in PLAIN else ('MOVE_NAMED_UNIT_TO', NAME, m.mark('there')) if v == 'jpk' else
                             ('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', NAME, button, m.mark('there')),
                             ('SET_FLAG', 'Test Going', 1)]))
    if v == 'mid':      # pressed again untargeted on its way (a07 / s07's eggs when attacked)
        t.scripts.append(Script('Test - mid', [('TIMER_EXPIRED', 'Test Mid')], [press]))
    if v == 'jpk':      # s02's escape: the packed MCV on its way pressed the yard's pack button at the point
        t.scripts.append(Script('Test - mid', [('TIMER_EXPIRED', 'Test Mid')],
                                [('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', NAME, button, m.mark('there'))]))
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
                                          (('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, yard, 'Test Short')
                                           if v in PLAIN + ('mid',) else ('PLAYER_HAS_OBJECT_COMPARISON', p1, 3, 1, yard),
                                           1000)])
    per_frame('CNV_Unpack_Name', '名字帧', [(('NAMED_NOT_DESTROYED', NAME), 1)])
    t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {f'engine_unpack_{v}': (lambda v=v: mission(v)) for v in VARIANTS}
CHECKS = {f'engine_unpack_{v}': {'go': frames} for v in VARIANTS}      # mod CampUnpackMcvGo: 15 characters at most
