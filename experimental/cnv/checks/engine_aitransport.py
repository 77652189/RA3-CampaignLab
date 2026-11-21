"""Tactic UseTransports: does a SimpleAttack team with a transport put its infantry aboard before it goes?

missions/aitransport_bench.py: Niagara without bridges, four Peacekeepers and a Riptide of s1 on the east bank, the
target plant on Goat Island. Three counters, once a second:
  车内步兵   s1's objects carrying ENCLOSED (only the Peacekeepers can be: aboard the Riptide)
  岛上步兵   s1's Peacekeepers inside Goat Island's box
  激流在岛   1 while the Riptide is inside Goat Island's box
Prediction (b221 read rule): true -> they board (车内步兵 > 0), the Peacekeepers reach the island; false -> the
Riptide crosses alone (激流在岛 1), 岛上步兵 stays 0.

RESULTS (2026-11-16, run_queue, B round 221): aitrans0 PASS, aitrans1 FAIL -- both 0 0 0 from s1 to the end (s117 /
s112); the minimap at s80 shows every s1 unit still at the east base: the team never left in either, so this pair
does not tell the flag apart (the simulator: the same, nobody moves). Not registered. Suspects: the target heuristic
or the team's start wants a ground way to the target (no target / no team), so no pair ever forms. Next: a home-box
counter, and the target reachable by the Riptide but not by the infantry in some other way.
RESULTS (2026-11-16, B round 222, the ra3ext host added, 4th counter 步兵在家): aitrans0 / aitrans1 again 0 0 0 4
to the end (CampAITrans0A_mcp_1116_131624, CampAITrans1A_mcp_1116_131448). The logs: the state's target pick finds
the island plant at f16 (the player's yard the other candidate, both ok); the SimpleAttack team is made at f17 with
0 members, dropped and made again every ~90 frames to the end; every s1 unit stays in the default team -- nobody is
recruited, it is not a team that does not move. aitransr (the Riptide alone): the same, 0 members
(CampAITransRA_mcp_1116_132232) -- the Riptide itself is turned away, not blocked by unpairable infantry.
aitransw0 / aitransw1 / aitransrw (the plant on the west bank's landing 'front' instead): the same in all three
(..._1116_133119 / 132835 / 132645). aiteamfilter's aitfamph took Riptides at a land target on the east bank (with
bridges, AllowedLocomotorTypes AMPHIBIOUS only). Not explained in two layouts: stopped (work/re handoff-b 222).
RESULTS (2026-11-16, B round 223): aitransre (the Riptide alone, no bridges, the plant back at aiteamfilter's
'east gate' on the east bank) PASS: 激流在岛 1 from s60 (CampAITransREA_mcp_1116_134740) -- the Riptide is taken and
goes. So this map (no bridges, no library, LAND AMPHIBIOUS) does not turn it away; what does is the target being
somewhere the east bank has no ground way to (the island, the west bank): the recruit turns the Riptide away there
too. A passenger is paired only when it cannot reach the target itself, and such a unit is not recruited, so no
layout of this bench forms a pair and UseTransports stays untold apart. Stopped, not registered (handoff-b 223).
RESULTS (2026-11-21, B): the recruit tries a unit that cannot reach again or'd with a member that can carry it, and
an AIR mask always passes (work/re b1121_transports.md): aitranst0 / aitranst1 put a Twinblade in for the Riptide
(激流在岛 then counts the Twinblade). The flag tells: true -> all four board s24-27, carried off from s32; false ->
the team takes all five (f153), nobody boards, the Peacekeepers drop out (f248), the Twinblade crosses alone (s49).
Readings in engine_aitransport.readings.toml, both a mismatch (the model's recruit does not pair).
"""
from parts import Script, Test, counted, square, status

ISLAND = 'CNV Trans Island'     # B222 aitransw*: the target's box (the west bank's landing), not the island
HOME = 'CNV Trans Home'
X0, X1, Y0, Y1 = 2450.0, 2750.0, 2450.0, 3350.0      # niagara.GOAT
AT, SECONDS = 75.0, 85.0


def a(m):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    if m.facts.get('player shot'):          # E 11-21 aitranstp: the player's Twinblade at its own plant
        t.scripts.append(Script('Test - shoot', [], [('NAMED_FORCE_ATTACK_NAMED', 'UNIT - CNV Twinblade',
                                                       'UNIT - CNV AI Player Target')]))
    if m.facts['target on island']:
        t.areas[ISLAND] = [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)]
    else:
        t.areas[ISLAND] = square(m.facts['target x'], m.facts['target y'], 350.0)   # 'front' / B223 'east gate'
    counted('CNV_TR_In', '车内步兵', t, status=status('ENCLOSED'), player=s1)
    if m.facts.get('air transport'):        # E 11-21: what the Twinblade does to the plant (four lines fit)
        counted('CNV_TR_Plant', '电厂血', t, health='UNIT - CNV AI Player Target')
    else:
        counted('CNV_TR_Isle', '岛上步兵', t, template='AlliedAntiInfantryInfantry', area=ISLAND, player=s1)
    counted('CNV_TR_Boat', '激流在岛', t, named='UNIT - CNV AI Riptide', area=ISLAND)
    t.areas[HOME] = square(*m.site('east base'), 450.0)          # B222: aiteamfilter's home box
    counted('CNV_TR_Home', '步兵在家', t, template='AlliedAntiInfantryInfantry', area=HOME, player=s1)
    if m.facts.get('air transport'):                              # B 11-21: what the bench read
        t.expect = [('车内步兵', 30, '==', 4 if m.facts['use transports'] else 0, 31)]
    elif not m.facts['ai infantry']:                                # aitransr: the Riptide alone
        t.expect = [('激流在岛', AT, '==', 1, AT + 1)]
    elif m.facts['use transports']:
        t.expect = [('岛上步兵', AT, '>=', 1, AT + 1)]
    else:
        t.expect = [('岛上步兵', AT, '==', 0, AT + 1), ('车内步兵', AT, '==', 0, AT + 1)]
    t.bench = [('bench_watch', dict(seconds=SECONDS, every=1, sheet=False, lines=3))]
    return t


CHECKS = {name: {'a': a} for name in ('aitrans0', 'aitrans1', 'aitransr', 'aitransw0', 'aitransw1',
                                              'aitransrw', 'aitransre', 'aitranst0', 'aitranst1', 'aitranstp')}
