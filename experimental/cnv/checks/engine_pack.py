"""Engine unit test: a construction yard packing back into its MCV -- ReplaceSelfSpecialAbility on
SpecialPower_PackReplaceSelf (TargetType NONE, no PackTime, ReplaceOptions DISABLE_DURING_REPLACE
DISABLE_NEW_OBJECT_DURING_UNPACK, NewObjectUnpackTime the yard's local unpack time). engine_unpack measured the other
way (an MCV / an egg deploying at a point); the three yards are the rest of the module's templates but the miner and
the surveyor.

On the Niagara map the player's yard (named) in the west field, a waypoint 400 east of it. At 1 s the yard's pack
button, NAMED_USE_COMMANDBUTTON_ABILITY(yard, Command_Pack...MCV); the first frame the player owns the MCV, and again
GO_AGAIN s after the press, MOVE_NAMED_UNIT_TO(the yard's name, there) -- the name is the MCV's if it passes on.
Counters, frames added from the press on (four lines):
  帧数    frames since the press
  车帧    +1 a frame the player owns the yard's template, +1000 a frame he owns the MCV's
  名字帧  +1 a frame the yard's name is not destroyed
  走帧    +1 a frame the MCV stands within 40 of where the yard stood, +1000 a frame it stands within 100 of there

Predictions from the data: the MCV 6 frames after the press (the deploy on the spot, engine_build a) or at once (no
PackTime); the name passes on (engine_unpack); the first order lost while the MCV unpacks (NewObjectUnpackTime 2 s,
DISABLE_NEW_OBJECT_DURING_UNPACK), the second (GO_AGAIN 4 s) taken.

Bench 11-11 (round 159), 帧数 车帧 名字帧 走帧 at the last reading:
  a CampPackAGo_mcp_1111_043158: 473 473000 473 353050 -- the MCV owned from the press frame (no yard frame at all),
    the name passed on, out of the 40 square at frame 50, within 100 of there from frame 121.
  s CampPackSGo_mcp_1111_043431: 483 483000 483 355051 -- out at 51, there at 128.
  j CampPackJGo_mcp_1111_043652: 720 720000 720 570054 -- out at 54, there at 150.
  So: the yard is its MCV at once (not the deploy's 6 frames, no PackTime), the order given that frame is kept and
  the MCV drives ~20 frames later than NewObjectUnpackTime (2 s = 30) alone would let it: fitted 30 + 14 standing
  (simunits.PACK_EXTRA_FRAMES, INFERRED). Simulator (tests/test_simbench.py
  test_a_yard_packs_into_its_mcv_at_once_and_the_mcv_stands_before_it_drives): a 676 676001 676 547054 at 46 s --
  out at 54, there at 129; the press frame still counts the yard once.
"""
import resources
from maps import niagara
from parts import Mission, Script, Test, square

KINDS = {'a': ('AlliedConstructionYard', 'AlliedMCV', 'Command_PackAlliedMCV'),
         's': ('SovietConstructionYard', 'SovietMCV', 'Command_PackSovietMCV'),
         'j': ('JapanConstructionYard', 'JapanMCV', 'Command_PackJapanMCV')}
VARIANTS = tuple(KINDS)
AT, THERE = ('west field', -200.0, 0.0), ('west field', 200.0, 0.0)
NAME = 'UNIT - CNV Pack'
RUN, GO_AGAIN = 30.0, 4.0


def mission(variant='a'):
    yard, mcv, _ = KINDS[variant]
    m = Mission(name=f'CampPack{variant.upper()}', map=resources.measured(niagara), units=[], facts={'variant': VARIANTS.index(variant)})
    m.spawns |= {mcv}
    m.put(yard, AT[0], *AT[1:], angle=0.0, role='yard', name=NAME)
    m.waypoint('there', 'Test Pack There', *THERE)
    return m


def frames(m):
    t = Test()
    yard, mcv, button = KINDS[VARIANTS[m.facts['variant']]]
    p1 = m.player('p1')
    t.areas['Test Home'] = square(*m.site(*AT), 40.0)
    t.areas['Test There'] = square(*m.point('there'), 100.0)
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0),
                                                 ('SET_MILLISECOND_TIMER', 'Test Again', 1.0 + GO_AGAIN)]))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')],
                            [('NAMED_USE_COMMANDBUTTON_ABILITY', NAME, button), ('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)
    owns_mcv = ('PLAYER_HAS_OBJECT_COMPARISON', p1, 3, 1, mcv)
    move = ('MOVE_NAMED_UNIT_TO', NAME, m.mark('there'))
    t.scripts.append(Script('Test - move first', [going, owns_mcv], [move]))
    t.scripts.append(Script('Test - move again', [going, ('TIMER_EXPIRED', 'Test Again')], [move]))

    def per_frame(counter, label, rows):
        t.counters.append((counter, label))
        t.scripts += [Script(f'Test - {counter} {k}', [going, cond], [('INCREMENT_COUNTER', step, counter)],
                             once=False) for k, (cond, step) in enumerate(rows)]

    per_frame('CNV_Pack_Frames', '帧数', [(going, 1)])
    per_frame('CNV_Pack_Own', '车帧', [(('PLAYER_HAS_OBJECT_COMPARISON', p1, 3, 1, yard), 1), (owns_mcv, 1000)])
    per_frame('CNV_Pack_Name', '名字帧', [(('NAMED_NOT_DESTROYED', NAME), 1)])
    per_frame('CNV_Pack_Walk', '走帧', [(('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, mcv,
                                          'Test Home'), 1),
                                        (('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, mcv,
                                          'Test There'), 1000)])
    t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=0.5, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {f'engine_pack_{v}': (lambda v=v: mission(v)) for v in VARIANTS}
CHECKS = {f'engine_pack_{v}': {'go': frames} for v in VARIANTS}      # mod CampPackAGo: 15 characters at most
