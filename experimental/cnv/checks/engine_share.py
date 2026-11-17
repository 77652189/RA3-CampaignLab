"""Retail-campaign leftovers, one bench (round 222): PLAYER_TOGGLE_RESOURCE_SHARING on mining income (111 uses; a01
both players of the co-op pair) and the conditions NAMED_SELECTED (50) / TYPE_SELECTED (38), with the selection set by
SELECT_OBJECT(player, object) / DESELECT(). Mission on engine_mining's pad (maps/probe_range.py 'probe refinery': the
refinery's own collector alone, the placed one deleted at the start -- engine_mining a: 250 a load, the first at frame
239, then every 269 frames).

  all  money: Player_1 (the refinery's owner), Soviet_5 and Soviet_6 friends of the player both ways, money 0 at the
       start; sharing on for Player_1 and Soviet_5 at the start, Soviet_6 on at 24 s, Soviet_5 off at 42 s.
       So the first load is split with one sharer, the second with two, the third with one again (Soviet_6).
       selection: the player's 'pick' (a Guardian on 'power 1') and Soviet_4's 'foe' (a Hammer on 'low gun'), both
       NO_ATTACK; SELECT_OBJECT(Player_1, pick) at 3 s, (Player_1, refinery) at 6 s, DESELECT at 9 s,
       (Player_1, foe) at 12 s, DESELECT at 15 s, (Player_1, pick) at 18 s, NAMED_KILL(pick) at 21 s.
       甲钱 / 乙钱 / 丙钱 = Player_1's / Soviet_5's / Soviet_6's money
       选 (every frame) = 1 NAMED_SELECTED(pick) 2 NAMED_SELECTED(refinery) 4 TYPE_SELECTED(Guardian)
         8 TYPE_SELECTED(AlliedRefinery) 16 NAMED_SELECTED(foe) 32 TYPE_SELECTED(Hammer)
  [program (work/re d115_script_semantics.md 19): money coming in to a sharing player is split among k sharing allies
   + itself, floor(amount / (k + 1)) each. Predicted: load 1 125 / 125 / 0; load 2 (k = 2) about 83 each (the
   rounding per deposit tells whether the earner keeps the same share or the rest); load 3 125 to Player_1 and
   Soviet_6, Soviet_5 unchanged. Selection predicted: 5 (3-6 s), 10 (6-9 s: SELECT_OBJECT replaces), 0, 16 + 32 or 0
   (an enemy's selectable?), 0, 5, 0 after the kill.]
  BENCH 11-14 (round 222, run_queue, CampShareAll_mcp_1114_052045) PASS: 甲钱 / 乙钱 / 丙钱 / 选 s1 0 0 0 0 | s2-s4
    0 0 0 1 | s5-s10 0 0 0 2 | s11-s13 0 0 0 16 | s14 4 4 0 16 | s15 64 64 0 16 | s16 125 125 0 16 | s17-s23 125 125 0 1
    | s24-s31 125 125 0 0 | s32 141 133 8 0 | s33 201 163 38 | s34-s49 249 188 63 | s50 277 188 91 | s51 341 188 155 |
    s52-s67 374 188 188. Against the prediction: the earner keeps the rest, not one share (two sharers: 124 / 63 / 63
    a load -- each Friend 8 // 3 = 2 of a deposit of 8, the earner 4); SELECT_OBJECT replaces (2 alone at s5), an
    enemy's object is selected too (16); DESELECT changes nothing (2 to s10, 16 to s16); TYPE_SELECTED never true
    (no 4 / 8 / 32); the killed pick still selected ~3 s (1 to s23). Simulator: sim.Sim.earn, SELECT_OBJECT,
    NAMED_SELECTED / TYPE_SELECTED (tests/test_simbench.py test_share_all_as_the_bench).
"""
from checks import engine_mining as mining
from parts import Script, Test, status
import checks.engine_scripts8 as s8

TANK, FOE = 'AlliedAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech1'
FRIEND = (2, 0.0, 'Friend')
RUN = 66.0


def _n(part):
    return f'UNIT - CNV Share {part}'


def mission():
    m = mining.mission()
    m.name = 'CampShare'
    m.put(TANK, 'power 1', role='pick', name=_n('Pick'))
    m.put(FOE, 'low gun', role='foe', side='s4', name=_n('Foe'))
    return m


def all_(m):
    t = Test()
    p1, s5, s6 = m.player('p1'), m.player('s5'), m.player('s6')
    pick, foe, refinery = _n('Pick'), _n('Foe'), m.role('refinery').name
    na = status('NO_ATTACK')
    t.scripts.append(Script('Test - Share start', [], [
        ('MAP_REVEAL_ALL_PERM', p1), ('NAMED_DELETE', m.role('miner').name),
        *[('PLAYER_RELATES_PLAYER', a, b, FRIEND) for a, b in ((p1, s5), (s5, p1), (p1, s6), (s6, p1))],
        *[('PLAYER_SET_MONEY', p, 0) for p in (p1, s5, s6)],
        ('PLAYER_TOGGLE_RESOURCE_SHARING', p1, 1), ('PLAYER_TOGGLE_RESOURCE_SHARING', s5, 1),
        ('UNIT_CHANGE_OBJECT_STATUS', pick, na, 1), ('UNIT_CHANGE_OBJECT_STATUS', foe, na, 1)]))
    for key, secs, acts in (
            ('sel1', 3.0, [('SELECT_OBJECT', p1, pick)]),
            ('sel2', 6.0, [('SELECT_OBJECT', p1, refinery)]),
            ('desel1', 9.0, [('DESELECT',)]),
            ('sel3', 12.0, [('SELECT_OBJECT', p1, foe)]),
            ('desel2', 15.0, [('DESELECT',)]),
            ('sel4', 18.0, [('SELECT_OBJECT', p1, pick)]),
            ('kill', 21.0, [('NAMED_KILL', pick)]),
            ('share6', 24.0, [('PLAYER_TOGGLE_RESOURCE_SHARING', s6, 1)]),
            ('unshare5', 42.0, [('PLAYER_TOGGLE_RESOURCE_SHARING', s5, 0)])):
        s8.at(t, key, secs, acts)
    for counter, label, player in (('CNV_Shr_M1', '甲钱', p1), ('CNV_Shr_M5', '乙钱', s5), ('CNV_Shr_M6', '丙钱', s6)):
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter}', [], [('SET_PLAYER_MONEY_TO_COUNTER', player, counter)],
                                once=False))
    s8.total(t, 'CNV_Shr_Sel', '选', [
        (1, ('NAMED_SELECTED', pick)), (2, ('NAMED_SELECTED', refinery)),
        (4, ('TYPE_SELECTED', TANK)), (8, ('TYPE_SELECTED', mining.REFINERY)),
        (16, ('NAMED_SELECTED', foe)), (32, ('TYPE_SELECTED', FOE))])
    t.expect = [('甲钱', 0, 'ever>=', 1, RUN)]
    s8.watch(t, RUN)
    return t


MISSION = {'engine_share': mission}
CHECKS = {'engine_share': {'all': all_}}
