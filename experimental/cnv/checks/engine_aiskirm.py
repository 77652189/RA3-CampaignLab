"""Engine probe: when the skirmish AI's first attack team leaves its base (missions/aiskirm_bench.py: s1 AlliedBalanced
with a yard, woken at 10 s with 50000 money; the player has a yard, a war factory and a power plant on the west bank),
read for the plan simulator (simai.py: first team BalancedAttackGround = 4 Riptides + 4 dogs leaves ~157 s after the
wake; the player's 3 buildings die 232-261 s after).

  a  激流总数 / 激流在家   Riptides (AlliedAntiInfantryVehicle) s1 owns / of them inside 600 around the east base
     出门帧             frames from the wake until the first Riptide stands outside the area (stops there; never
                        out = counts the whole run). 15 frames a second.
     我方建筑           how many of the player's yard / war factory / power plant are still alive (0-3)

The units counted are the Riptides only (the team's dogs are not read: the Riptides are the first to be built and the
ones that leave with the team). Four lines a check. Once the first leaves, the other readings are the timeline.

读数
RESULTS (bench 2026-11-07; bench s; counters 激流总数 激流在家 出门帧 我方建筑; the check logs 1-s rows; PASS):
  wake: 出门帧 starts counting at ~s8.1 bench (the check's wake = timer 10 s + 30 ticks; bench s runs ~2 s ahead of
    the mission clock), 15 frames a second. Seconds below are bench s; "after wake" = minus ~8.1.
  first Riptide: 激流总数 1 at s111 (~103 s after wake), 2 at s123, 3 at s131, 4 at s142, 5 s174, 6 s185, 7 s248,
    8 s259, 9 s269, 10 s280, 11 s291, 12 s317, 13 s325 (total counts all Riptides, the AI keeps building).
  leaves: 出门帧 stops at 1992 (= 132.8 s) at s139: 激流在家 3 at s138, 1 at s139 (two out at once) = first team
    leaves ~131-133 s after the wake (sim said ~157 s: the sim is ~25 s late).
  player buildings 我方建筑: 3 until s202, 2 from s203, 1 from s221, 0 from s223 = first dies ~195 s after the wake,
    the last (all three gone) ~215 s after (sim said 232-261 s: the sim is ~35-45 s late).
  Reading: the first attack team leaves ~132 s after the wake, 20 s after the first Riptide stands (s111), and the
  player's 3 buildings are gone ~83 s after it leaves; the sim's 157 s / 232-261 s are too late.

  b  激流在家 / 警犬总数 / 警犬在家 / 出圈帧   (dogs = AlliedScoutInfantry; 出圈帧 stops at the first dog out)
RESULTS b (bench 2026-11-07; PASS; wake = ~s8.1 bench, so after-wake seconds = bench s minus 8.1):
  dogs: total 1 at s23, 2 at s26 (built before the first Riptide); 出圈帧 stops at 661 (= 44 s after wake) at s52:
    警犬在家 2 -> 1 at s52 -> 0 at s55; back 2 at s68-86; 0 again from s87 on (the whole 120-170 window). So the dogs
    scout on their own, they are NOT in the team that leaves with the Riptides.
  Riptides: 在家 1 at s111, 2 at s123, 3 at s131-138, 1 at s139, 0 at s140-141 (the two leave at s139).
  120-145 s after wake (s128-153), 激流在家/警犬总数/警犬在家: s128-130 2/2/0; s131-138 3/2/0; s139 1/2/0;
    s140-141 0/2/0; s142 1/2/0; s143-150 2/2/0; s151-153 1/2/0. Dogs stay at 0 home, so no dog leaves with them.
  145-170 s after wake (s153-178): 激流在家 1 (to s158; the 4th, built s142, left at s151), 0 (s159-173; the 2nd team
    out), 1 from s174, 2 from s185 -- these are the new builds of a's total (5th at s174, 6th at s185); no dog or
    Riptide is seen coming home (home count only rises at build seconds).
  Reading: the first team's two Riptides leave without dogs; the dogs left earlier (~44 s after wake) and are away.

  c  维和总数 / 维和在家 / 标枪总数 / 工程师总数   (Peacekeeper AlliedAntiInfantryInfantry, Javelin soldier
     AlliedAntiVehicleInfantry, AlliedEngineer; home = inside 600 around the east base; runs to ~s188)
RESULTS c (bench 2026-11-07; PASS; after-wake seconds = bench s minus 8.1; templates all exist in the SDK):
  Peacekeepers total: 1 at s43 (35 s after wake), 2 s49 (41), 3 s54 (46), 4 s133 (125), 5 s150 (142), 6 s162 (154),
    7 s168 (160), 8 s179 (171). Javelin: 1 s32 (24), 2 s37 (29), 3 s60 (52), 4 s156 (148), 5 s173 (165), 6 s185 (177).
    Engineer: 1 at s144 (136), only one in the whole run. So the barracks never stops: ~1 infantry per 5-25 s, a long
    gap 52-125 s (nothing built; 3 Peacekeepers + 3 Javelins stand home s69-132).
  Peacekeepers at home 125-145 s after wake (s133-153): 4 (s133-140), 1 at s141 (= 132.9 s after wake: THREE leave
    in the same second, the same moment the first Riptide team leaves), 0 s142-144, 3 at s145 (the 3 back or new ones:
    total stays 4, so they return), 4 at s150, 1 at s152 (3 out again). Engineer built s144 (136 s).
  Reading: the first attack team leaves ~133 s after wake with 3 Peacekeepers (plus the Riptides); the barracks'
    4th Peacekeeper (125 s) is built just before and stays or comes back.

  d  AI钱 / 塔数 / 建筑数 / 兵数   (AI钱 = s1's money each frame; 塔数 = AlliedBaseDefense + AlliedBaseDefenseAdvanced;
     建筑数 = yard + power + barracks + refinery + war factory + towers; 兵数 = Peacekeeper + Javelin + Riptide + dog.
     Mission aiskirm (50000) and aiskirmlow (15000, CampAISkLow). f = d + PLAYER_GIVE_MONEY 20000 to s1, aiskirmlow only.)
RESULTS d (bench 2026-11-07; PASS; after-wake seconds = bench s minus the first-money second: s8 for aiskirm, s9 for
  aiskirmlow; the run ends ~245 s after wake, longer than the 200 s asked):
  aiskirm d, AI钱 at 0/60/100/110/120/130/140/160/180/200 s after wake: 49996, 43050, 41063, 40810, 40790, 40389,
    39740, 38300, 35685, 33608. Per 10 s: ~1160 (0-60 s), ~500 (60-100), ~260 (100-110), ~0-20 (110-120), ~400 (120-130),
    ~650 (130-140), ~720 (140-160), ~1300 (160-180), ~1040 (180-200). No cliff at 120 s: money goes out steadily.
    Towers: first at s184 (176 s after wake), second at s204 (196 s). 建筑数 1, 2 at 11 s, 3 at 21, 4 at 41, 5 at 61,
    6 at 71, 7 at 95, 8 at 163, 10 at 176 (a tower + one more), 11 at 196. 兵数: 8 from 52 s to 114 s, 9 at 115, 10 at 129,
    11 at 145, 12 at 147, 13 at 170, ... 18 at 201, 26 at 237.
  aiskirmlow d: AI钱 at 0/60/100/110/120/130/140/160/180/200: 14966, 8089, 5989, 5700, 5670, 5405, 4830, 2400, 1183,
    800. Per 10 s: ~1150 (0-60), ~525 (60-100), ~290 (100-110), ~30 (110-120), ~265 (120-130), ~575 (130-140), ~1215
    (140-160), ~610 (160-180), ~190 (180-200). Money under 1300 from 166 s on, 85 at s234, 50 at s235 (floor). NO tower
    in the whole run (0 to s279). 建筑数 2 at 10 s, 3 at 20, 4 at 42, 5 at 61, 6 at 71, 7 at 92, 8 at 153, 9 at 162 (not
    towers). 兵数 8 from 52 s to 103, 9 at 104, 10 at 125, 12 at 147, 13 at 157, 15 at 171, 19 at 241.
RESULTS f (aiskirmlow, 20000 given at s166 = ~157 s after wake s9, not 160: the timer starts a bit early; PASS):
  AI钱 at 0/60/100/110/120/130/140/160 s after wake: 14960, 7986, 5835, 5630, 4853, 3315, 1671, ~410 (s165, just before
    the gift); the gift: 405 -> 20276 at s166. After it: 161 s 19812, 170 s 18578 (s179), 180 s 17022 (s189), 190 s
    15644 (s199), 200 s 14491 (s209), 210 s 13586 (s219), 230 s 11740 (s239). Spent after the gift: 1355 in the first 10 s,
    ~2670 in 20 s, ~4120 in 30 s (income included), ~5800 in 43 s, ~8500 in 70 s (s236).
    Before the gift this run spent faster than aiskirmlow d (money 5300 at s126 vs s142 there).
  Tower: the first at s186 (177 s after wake, ~20 s after the gift), one only. 建筑数 9 at 138 s, 10 at 177 (that tower).
    兵数 9 at 102 s, 10 at 114, 12 at 123, 13 at 133, 15 at 145, 16 at 151, 17 at 157, 18 at 162, 22 at 174, 27 at 197,
    30 at 238. The tower came at the same ~176 s as in aiskirm d (50000), so it does not look tied to the gift but to
    time plus having money then (aiskirmlow d, money ~1500 at 177 s, had none).

  e  标枪近院 / 出门帧 / 维和在家 / 标枪在家   (aiskjav only: s1 has a named Javelin soldier 'UNIT - CNV AI Jav' 100 west of
     the yard; at mission second 100 (90 s after the wake) it is teleported to OUT, 1200 straight south of the yard.
     标枪近院 = that soldier inside 300 around the yard (1/0); 出门帧 and 维和在家 as in a / c; 标枪在家 = all of s1's
     Javelin soldiers inside 600. Question: does the AI's LandDefense team still hold its soldiers 90 s after the wake?
     Runs to ~170 s of the mission. Weak expectation: the readings are complete.)
RESULTS e (bench 2026-11-08, aiskjav, CampAISkJavE; PASS (weak); bench s, which runs ~2 s ahead of the mission clock, so
  the teleport at mission 100 shows at ~s102):
  标枪近院: 1 from the start to s20, 0 s21-s32 (it walked out of 300 and back), 1 from s33 to s99 -- so NOT a constant 1
    before the teleport, it left the 300 square for ~12 s once. 0 from s102 (the teleport, out 1200 south) to s154;
    1 again at s155-s161 (inside 300 again ~53 s after the teleport); 0 from s162 on (out again, to the end).
  出门帧: counts 15 a second from s9, stops at 2004 at s158 (first Riptide out; ~19 s later than aiskirm a's s139).
  维和在家: 1 at s37, 2 at s49, 3 at s60, stays 3 to s165; 1 at s166 (two leave), 2 at s167-170, 1-2 after.
  标枪在家: 1 to s31, 2 at s32, 3 at s43, 4 at s54, stays 4 THROUGH the teleport (s102) to s122; 3 at s123-s146, 4 at
    s147, 5 at s150, 2 at s166 (three leave, same second as the Peacekeepers), 1-2 after. No drop at the teleport
    second: the count has other soldiers besides the named one -- read it with 标枪近院, not alone.
  Reading: the named Javelin soldier teleported 1200 away at 90 s after the wake is inside 300 again at ~s155 (so the
    AI does not leave it out there), then is out again from s162, just before the first team (Peacekeepers + Javelins)
    leaves at s166.
  B's reading (round 51): the s21-32 walk is the defense team taking it (MinUnits 1) and placing it; it is brought
    back after the teleport, but in ~53 s, not the ~18 s aidefense b's StaticDefense team took for the same 1200 --
    so likely not held the whole time (re-recruited by a later defense team copy, SortByDistance). It then seems to
    leave with the first attack team (out of 300 at s162, three Javelins leave at s166): the general recruit path
    never takes a unit of another team, so at ~s162 it was in no team -- defense membership is not sticky (disband /
    re-recruit), which is candidate 2 of handoff-b 50, not a gate on AlwaysRecruit. The preplaced soldier also moves
    the first team out from s139 to s158-166 (it gets Javelins: the type mix changed). Not proven: which team it left
    with (no team read on the bench).

  g / h  AI teams counted by name (missions/aiskirm_bench.AI_TEAMS; 99 = no team of that name answered that frame).
     g: 池兵 = the pool's CAN_ATTACK members, 防御型 / 防御名 = LandDefense_MEDIUM_<StaticDefense | Defense>_0_0,
     兵数 = army owned (as d). h: 池全 = all the pool's members, 地图队 = teamSoviet_1, 进攻型 / 进攻名 =
     BalancedAttackGround_MEDIUM_<DefenseAvoidanceAttack | Attack>_0_0. aiskirmnl = aiskirm with Soviet_1's
     Lib_Skirmish_Setup emptied.
RESULTS g / h (bench 2026-11-10, aiskirm g / h and aiskirmnl g, all PASS (weak); bench s):
  names: the tactic's TYPE is the name ('..._StaticDefense_0_0', '..._DefenseAvoidanceAttack_0_0' answer), the
    Tactic id never does (防御名 / 进攻名 99 the whole run). An empty team flickers 0 / 99 (instance made and gone).
  aiskirm g: every new combat unit goes into LandDefense _0_0 within ~1-2 s (池兵 1 for a second, then 0):
    防御型 = 兵数 from s26 (1) to s69 (8); 7 at s79, 6 from s80 (two leave it -- dogs, b's scouts, likely), 7 at
    s121, 8 at s131-134; then 0 at s136 (all eight at once, ~the second the first attack team leaves: a a/c) and
    it stays 0 / 99 to s203; new units after s136 sit in the pool 1-2 s and go to some other team (not _0_0).
  aiskirm h: pool = 2 at the start (the yard + one more), grows with the buildings and the passing units (14 at
    s150); 地图队 0 the whole run (the library's transfer: handoff.md round 135); 进攻型 _0_0 0 / 99 every ~5 s and
    never a member, also when the attack leaves -- the team that leaves is another instance (other indices).
  aiskirmnl g: the same story ~2-8 s earlier (8 in defense at s62, 0 at s128): the library does not change it.
  Reading: the defense team DOES take every new unit (the model's keep_on=True is right about the pool); the first
    attack team is made of the defense team's eight, released all at once at ~132 s after the wake.

  i / j / k / l  other instances and states (aiskirm; bench 2026-11-10, all PASS (weak); bench s). Labels are words:
     '进攻0_1'-style labels read back as '?' on the bench.
     i / j: BalancedAttackGround_MEDIUM_DefenseAvoidanceAttack and LandDefense_MEDIUM_StaticDefense _0_1 / _1_0 /
       _0_2 / _1_1: 99 the whole run (no such team). 0x8d8f25 names '<state>_<tactic type>_<the tactic's index in
       the state>_<copy>' -- both states have one tactic, so the first index is 0.
     k: BalancedAttackOverwhelm_MEDIUM _0_0 flickers 0 / 99 every ~5 s (never a member), BalancedDefense and
       LandEmergencyDefense_MEDIUM 99; **BalancedCleanup_SimpleAttack_0_0 99 -> 8 at s131** (the defense team's
       eight at once), 9 s138, 10 s139, 11 s149, 12 s155, 13 s159, 14 s161 (MaxUnits 14) and stays.
     l: AlliedScout _0_0 1 from s72 (the defense team drops 8 -> 7 -> 6 then: a dog leaves for it), _1_0 and
       EscortMCV 99; LandDefense _0_0 8 -> 0 at s128 in this run.
  Reading: the first team out is BalancedCleanup (OpeningMove complete, no enemy within 700, income and power
    advantage >= 3: the player has no army and no refinery), not BalancedAttackGround; it takes the LandDefense
    team's members whole the moment it is drawn (~123 s after the wake).

  m  池兵 (pool CAN_ATTACK) / 防御型 (LandDefense _0_0) / 清扫 (BalancedCleanup _0_0) / 池峰 (the most CAN_ATTACK pool
     members seen in any single frame from s110, latched by per-frame scripts). Bench 2026-11-10, aiskirm m PASS (weak):
     防御型 8 at s128-130, **s131: 防御型 0, 清扫 8, 池峰 stays 1** (it reached 1 at s112, a new unit); the pool never
     held more than 1 in any frame, so the eight went defense -> Cleanup within one frame (no script pass saw them in
     the pool). After: the defense team exists empty (0, 99 every ~6 s as at s10-s22), new units sit 1-2 s in the
     pool and go to Cleanup (10 s138, 14 s161 = MaxUnits); only then one goes to defense (1 at s166, gone at s167).
  Reading: not a pool round trip a script could see. With the code (a running StaticDefense instance is never
    reselected: 0x8c7020 returns false while +0x14 started; handoff-b 95 / aiar9-10: a quiet base never releases),
    the release is caused by Cleanup turning on: Cleanup (STANDARD, RELEASE_TO_PRIORITY) takes the DEFENSE team's
    members in one commit, and wins the pool over the defense team until full.

  n  防御型 (LandDefense _0_0) / 清扫 (BalancedCleanup _0_0) / 清扫二 (BalancedCleanup _0_1) / 防御二 (LandDefense _0_1)
     to s203. Bench 2026-11-10, aiskirm n PASS (weak; the first try hung at bench_stop, log b102_n.log; this is
     b102_n2.log): 防御型 8 at s126, 0 from s130; 清扫 8 s130, 10 s137, 14 s158 and stays; 防御型 1 at s165 only;
     **清扫二 and 防御二 99 the whole run** -- no second copy of either team is ever made.
  Reading (corrected round 103, B handoff 105): the second index is not a slot copy. 0x8d8e30 builds the AI's team
    name table once: for each state, each tactic (index a), each of that tactic's TeamTemplates (index b, count at
    tactic +0x38) one name '<state>_<tactic type>_<a>_<b>' (no TeamTemplate: '_default'). BalancedCleanup and
    LandDefense have one TeamTemplate each, so their '_0_1' names do not exist (99 always): n says nothing about a
    second slot, whose team would share the name '_0_0' (MaxTargets 3: the model's (..., 0, 1) / (..., 0, 2)).
    A name answers for one of the same-named teams only; o counts around the names instead.

  o  兵数 (the AI's Peacekeepers + Javelins + Riptides, no dogs) / 清扫 (Cleanup _0_0) / 防御型 / 池兵 to s203:
     兵数 - 清扫 - 防御型 - 池兵 = units in teams no name reads (another Cleanup slot; a dog in Cleanup is noise).
     The model (b100_keep.log): Cleanup's second slot team holds 1 at ~s157 (148.5 s after the wake), 7 by ~s183.
     Bench 2026-11-10, aiskirm o PASS (weak): 清扫 8 s128, 14 from s157 and stays; 兵数 one behind 清扫 to s160 (a
     dog in Cleanup), then 14 s161 -> 15 s166 -> 18 s178 -> 21 s189; 防御型 0 (1 at s162 only), 池兵 0-1.
  Reading: after Cleanup _0_0 is full the new units go to a team no name reads -- about 1 at s162, 7 at s188 (dog
    corrected), as the model's second Cleanup slot. Round 102's mismatch was the name, not the model.
"""
from parts import Script, Test, counted, square

AREA = 'CNV AI Base Area'
RIPTIDE = 'AlliedAntiInfantryVehicle_Ground'     # the one a Riptide on land is (aiopen b counts both alike)
YOURS = ('AlliedConstructionYard', 'AlliedWarFactory', 'AlliedPowerPlant')
DOG = 'AlliedScoutInfantry'
SECONDS = 310.0                     # after the wake


def a(m):
    t = Test()
    m.spawns.add(RIPTIDE)               # published for the contract: the AI makes it, the check counts it
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[AREA] = square(*m.site('east base'), 600.0)
    counted('CNV_AK_Total', '激流总数', t, template=RIPTIDE, player=s1)
    counted('CNV_AK_Home', '激流在家', t, template=RIPTIDE, area=AREA, player=s1)
    t.counters.append(('CNV_AK_OutFrames', '出门帧'))
    t.counters.append(('CNV_AK_Built', '我方建筑'))
    p1 = m.player('p1')
    t.scripts.append(Script('Test - built zero', [], [('SET_COUNTER', 'CNV_AK_Built', 0)], once=False))
    for i, tpl in enumerate(YOURS):
        m.spawns.add(tpl)
        t.scripts += [Script(f'Test - own {i}', [], [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', tpl, p1, f'CNV_AK_Own{i}')],
                             once=False),
                      Script(f'Test - built {i}', [('COUNTER', f'CNV_AK_Own{i}', 3, 1)],
                             [('INCREMENT_COUNTER', 1, 'CNV_AK_Built')], once=False)]
    t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AK_Tick')], once=False),
                  Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AK_Tick', 3, 30)],
                         [('SET_FLAG', 'Test Woke', 1)])]
    for n in range(1, 9):                # more of them owned than at home = one is out
        t.scripts.append(Script(f'Test - out {n}', [('COUNTER', 'CNV_AK_Total', 2, n), ('COUNTER', 'CNV_AK_Home', 0, n)],
                                [('SET_FLAG', 'Test Out', 1)], once=False))
    t.scripts.append(Script('Test - wait out', [('FLAG', 'Test Woke', 1), ('FLAG', 'Test Out', 0)],
                            [('INCREMENT_COUNTER', 1, 'CNV_AK_OutFrames')], once=False))
    w = m.facts['wake at']
    t.expect += [('激流总数', w + 150.0, 'ever>=', 1, w + SECONDS)]
    t.bench = [('bench_watch', dict(seconds=w + SECONDS + 4.0, every=1, sheet=False, lines=len(t.counters)))]
    return t


def b(m):
    """Same wake and area as a; reads the Riptides together with the dogs (AlliedScoutInfantry): do the dogs leave in
    the same second as the two Riptides?  出圈帧 stops at the first dog out (dogs owned > dogs at home)."""
    t = Test()
    m.spawns.add(RIPTIDE)
    m.spawns.add(DOG)
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[AREA] = square(*m.site('east base'), 600.0)
    counted('CNV_AK_Home', '激流在家', t, template=RIPTIDE, area=AREA, player=s1)
    counted('CNV_AK_DogTotal', '警犬总数', t, template=DOG, player=s1)
    counted('CNV_AK_DogHome', '警犬在家', t, template=DOG, area=AREA, player=s1)
    t.counters.append(('CNV_AK_OutFrames', '出圈帧'))
    t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AK_Tick')], once=False),
                  Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AK_Tick', 3, 30)],
                         [('SET_FLAG', 'Test Woke', 1)])]
    for n in range(1, 9):                # more dogs owned than at home = one is out
        t.scripts.append(Script(f'Test - out {n}', [('COUNTER', 'CNV_AK_DogTotal', 2, n), ('COUNTER', 'CNV_AK_DogHome', 0, n)],
                                [('SET_FLAG', 'Test Out', 1)], once=False))
    t.scripts.append(Script('Test - wait out', [('FLAG', 'Test Woke', 1), ('FLAG', 'Test Out', 0)],
                            [('INCREMENT_COUNTER', 1, 'CNV_AK_OutFrames')], once=False))
    w = m.facts['wake at']
    t.expect += [('警犬总数', w + 150.0, 'ever>=', 1, w + 170.0)]
    t.bench = [('bench_watch', dict(seconds=w + 174.0, every=1, sheet=False, lines=len(t.counters)))]
    return t


def c(m):
    """Same wake and area as a; counts the barracks' infantry: Peacekeepers (AlliedAntiInfantryInfantry) total and at
    home, Javelin soldiers (AlliedAntiVehicleInfantry) total, Engineers (AlliedEngineer) total. Runs to ~170 s after
    the wake. Home = inside 600 around the east base."""
    t = Test()
    PK, JAV, ENG = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry', 'AlliedEngineer'
    for tpl in (PK, JAV, ENG):
        m.spawns.add(tpl)
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[AREA] = square(*m.site('east base'), 600.0)
    counted('CNV_AK_PkTotal', '维和总数', t, template=PK, player=s1)
    counted('CNV_AK_PkHome', '维和在家', t, template=PK, area=AREA, player=s1)
    counted('CNV_AK_JavTotal', '标枪总数', t, template=JAV, player=s1)
    counted('CNV_AK_EngTotal', '工程师总数', t, template=ENG, player=s1)
    w = m.facts['wake at']
    t.expect += [('维和总数', w + 150.0, 'ever>=', 1, w + 170.0)]
    t.bench = [('bench_watch', dict(seconds=w + 174.0, every=1, sheet=False, lines=len(t.counters)))]
    return t


TOWERS = ('AlliedBaseDefense', 'AlliedBaseDefenseAdvanced')
BUILDINGS = ('AlliedConstructionYard', 'AlliedPowerPlant', 'AlliedBarracks', 'AlliedRefinery', 'AlliedWarFactory')
ARMY = ('AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry', RIPTIDE, DOG)
CAP = 24                            # a sum reads at most this many per template


def _sum(t, m, s1, counter, label, templates):
    """A shown counter that is the total of what s1 owns over `templates`: each template is counted into a hidden
    counter every frame, the shown one is zeroed first and gets +1 per unit (hidden >= n for n = 1..CAP)."""
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
    for i, tpl in enumerate(templates):
        m.spawns.add(tpl)
        h = f'{counter}_H{i}'
        t.scripts.append(Script(f'Test - {counter} own {i}', [], [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', tpl, s1, h)],
                                once=False))
        for n in range(1, CAP + 1):
            t.scripts.append(Script(f'Test - {counter} {i} >= {n}', [('COUNTER', h, 3, n)],
                                    [('INCREMENT_COUNTER', 1, counter)], once=False))


def _spend(m, give=False):
    """d / f: money, towers, buildings, army of s1."""
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.counters.append(('CNV_AK_Money', 'AI钱'))
    t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AK_Money')], once=False))
    _sum(t, m, s1, 'CNV_AK_Towers', '塔数', TOWERS)
    _sum(t, m, s1, 'CNV_AK_Built', '建筑数', BUILDINGS + TOWERS)
    _sum(t, m, s1, 'CNV_AK_Army', '兵数', ARMY)
    w = m.facts['wake at']
    t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AK_Tick')], once=False),
                  Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AK_Tick', 3, 30)],
                         [('SET_FLAG', 'Test Woke', 1)])]
    run = 230.0 if give else 200.0
    if give:
        t.scripts += [Script('Test - give set', [('FLAG', 'Test Woke', 1)], [('SET_MILLISECOND_TIMER', 'Test Give', 160.0)]),
                      Script('Test - give', [('FLAG', 'Test Woke', 1), ('TIMER_EXPIRED', 'Test Give')],
                             [('PLAYER_GIVE_MONEY', s1, 20000)])]
    t.expect += [('兵数', w + 150.0, 'ever>=', 1, w + run)]
    t.bench = [('bench_watch', dict(seconds=w + run + 4.0, every=1, sheet=False, lines=len(t.counters)))]
    return t


def d(m):
    """s1's money every frame, towers (AlliedBaseDefense + AlliedBaseDefenseAdvanced), all buildings (yard, power,
    barracks, refinery, war factory, towers) and army (Peacekeeper + Javelin + Riptide + dog). To ~200 s after wake."""
    return _spend(m)


def f(m):
    """Same as d, plus PLAYER_GIVE_MONEY 20000 to s1 160 s after the wake; to ~230 s after the wake."""
    return _spend(m, give=True)


JAV_OUT_AT = 100.0                  # mission second the named Javelin soldier is teleported out (e)


def e(m):
    t = Test()
    PK, JAV = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry'
    for tpl in (PK, JAV, RIPTIDE):
        m.spawns.add(tpl)
    s1 = m.player('s1')
    jav = m.role('ai jav').name
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[AREA] = square(*m.site('east base'), 600.0)
    t.areas['CNV AI Yard 300'] = square(*m.site('east base'), 300.0)
    counted('CNV_AK_JavNear', '标枪近院', t, named=jav, area='CNV AI Yard 300')
    counted('CNV_AK_Total', '激流总数', t, template=RIPTIDE, player=s1)
    counted('CNV_AK_Home', '激流在家', t, template=RIPTIDE, area=AREA, player=s1)
    t.counters[1:3] = []                # the two Riptide counters work, they are not shown (four lines fit)
    t.counters.append(('CNV_AK_OutFrames', '出门帧'))
    counted('CNV_AK_PkHome', '维和在家', t, template=PK, area=AREA, player=s1)
    counted('CNV_AK_JavHome', '标枪在家', t, template=JAV, area=AREA, player=s1)
    t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AK_Tick')], once=False),
                  Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AK_Tick', 3, 30)],
                         [('SET_FLAG', 'Test Woke', 1)])]
    for n in range(1, 9):
        t.scripts.append(Script(f'Test - out {n}', [('COUNTER', 'CNV_AK_Total', 2, n), ('COUNTER', 'CNV_AK_Home', 0, n)],
                                [('SET_FLAG', 'Test Out', 1)], once=False))
    t.scripts += [Script('Test - wait out', [('FLAG', 'Test Woke', 1), ('FLAG', 'Test Out', 0)],
                         [('INCREMENT_COUNTER', 1, 'CNV_AK_OutFrames')], once=False),
                  Script('Test - jav timer', [], [('SET_MILLISECOND_TIMER', 'Test Jav Out', JAV_OUT_AT)]),
                  Script('Test - jav out', [('TIMER_EXPIRED', 'Test Jav Out')],
                         [('UNIT_TELEPORT_TO_WAYPOINT', jav, 'CNV AI Out')])]
    t.expect += [('标枪近院', 20.0, '>=', 0, 21.0)]            # weak: the readings exist
    t.bench = [('bench_watch', dict(seconds=174.0, every=1, sheet=False, lines=len(t.counters)))]
    return t


UNKNOWN = 99                        # g / h: a team count shows this when no team of that name answered this frame
POOL_MOST = 20
PEAK_FROM = 110.0                   # m: mission second the pool peak latch starts (the eight leave ~s128-136)


def _members(t, counter, label, team, most=POOL_MOST):
    """`team`'s member count (TEAM_COMPARE_NUM_MEMBERS ==), UNKNOWN when it is none of 0 .. most-1."""
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter} unknown', [], [('SET_COUNTER', counter, UNKNOWN)], once=False))
    t.scripts += [Script(f'Test - {counter} {n}', [('TEAM_COMPARE_NUM_MEMBERS', team, 2, n)],
                         [('SET_COUNTER', counter, n)], once=False) for n in range(most)]


def _kind_members(t, counter, label, team, kind, most=POOL_MOST):
    """How many of `team`'s members have KindOf `kind` (TEAM_HAS_FEWER_THAN_X_UNITS_WITH_KINDOF, tried from `most`
    down: the last that holds is n = count + 1); UNKNOWN when none holds (count >= most, or no such team)."""
    from model import kindof
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter} unknown', [], [('SET_COUNTER', counter, UNKNOWN)], once=False))
    t.scripts += [Script(f'Test - {counter} <{n}', [('TEAM_HAS_FEWER_THAN_X_UNITS_WITH_KINDOF', team, n, kindof(kind))],
                         [('SET_COUNTER', counter, n - 1)], once=False) for n in range(most, 0, -1)]


def _teams(m, which):
    """g / h: AI team sizes read by name. The engine names a strategic state's team instances '%s_%s_%u_%u'
    (0x8d8f25: state, a tactic string, two indices; retail maps query e.g. 'Player_2/AIState_J09_LandAttack_
    SimpleAttack_0_0'); the pool is 'defaultSkirmishTeam' + player (0x87e320). Which tactic string (the Tactic id
    'Defense' / 'Attack' or its type 'StaticDefense' / 'DefenseAvoidanceAttack') is what g / h tell apart."""
    t = Test()
    for tpl in ARMY:
        m.spawns.add(tpl)
    s1 = m.player('s1')
    ai = {k[3:]: v for k, v in m.map.TEAMS.items() if k.startswith('ai ')}      # missions/aiskirm_bench.AI_TEAMS
    pool = ai['pool']
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    if which == 'g':
        _kind_members(t, 'CNV_AK_Pool', '池兵', pool, 'CAN_ATTACK')
        _members(t, 'CNV_AK_DefT', '防御型', ai['defense type'])
        _members(t, 'CNV_AK_DefI', '防御名', ai['defense id'])
        _sum(t, m, s1, 'CNV_AK_Army', '兵数', ARMY)
    elif which in ('i', 'j'):          # other instances of the same tactic type: '<state>_<type>_<a>_<b>'
        kind = 'attack type' if which == 'i' else 'defense type'
        word = '进攻' if which == 'i' else '防御'
        # labels in words: '进攻0_1'-style labels read back as '?' on the bench (2026-11-10)
        for idx, say in (('0_1', '二份'), ('1_0', '乙头'), ('0_2', '三份'), ('1_1', '乙二')):
            _members(t, f'CNV_AK_{which.upper()}{idx.replace("_", "")}', f'{word}{say}', ai[f'{kind} {idx}'])
    elif which == 'k':
        for key, ctr, say in (('overwhelm', 'Ovw', '压倒'), ('bal defense', 'BDef', '均防'),
                              ('cleanup', 'Cln', '清扫'), ('emergency', 'Emg', '急防')):
            _members(t, f'CNV_AK_{ctr}', say, ai[key])
    elif which == 'l':
        for key, ctr, say in (('scout', 'Sct', '侦察'), ('scout 2', 'Sct2', '侦察乙'), ('escort', 'Esc', '护送')):
            _members(t, f'CNV_AK_{ctr}', say, ai[key])
        _members(t, 'CNV_AK_DefT', '防御型', ai['defense type'])
    elif which == 'm':                 # does the defense team's eight pass through the pool on the way to Cleanup?
        _kind_members(t, 'CNV_AK_Pool', '池兵', pool, 'CAN_ATTACK')
        _members(t, 'CNV_AK_DefT', '防御型', ai['defense type'])
        _members(t, 'CNV_AK_Cln', '清扫', ai['cleanup'])
        # 池峰: the most CAN_ATTACK pool members any single frame from PEAK_FROM s (scripts run every frame; the 1 s
        # sheet would miss a pool that holds the eight for under a second)
        t.counters.append(('CNV_AK_Peak', '池峰'))
        t.scripts.append(Script('Test - peak timer', [], [('SET_MILLISECOND_TIMER', 'Test Peak From', PEAK_FROM)]))
        t.scripts += [Script(f'Test - peak {n}', [('TIMER_EXPIRED', 'Test Peak From'), ('COUNTER', 'CNV_AK_Pool', 3, n),
                                                  ('COUNTER', 'CNV_AK_Peak', 0, n), ('COUNTER', 'CNV_AK_Pool', 0, UNKNOWN)],
                             [('SET_COUNTER', 'CNV_AK_Peak', n)], once=False) for n in range(1, POOL_MOST)]
    elif which == 'n':                 # Cleanup full (14 at s161): does the next unit go to Cleanup _0_1 or to defense?
        _members(t, 'CNV_AK_DefT', '防御型', ai['defense type'])
        _members(t, 'CNV_AK_Cln', '清扫', ai['cleanup'])
        _members(t, 'CNV_AK_Cln2', '清扫二', ai['cleanup 0_1'])
        _members(t, 'CNV_AK_Def2', '防御二', ai['defense type 0_1'])
    elif which == 'o':                 # units outside every team a name reads (a second Cleanup slot shares _0_0)
        _sum(t, m, s1, 'CNV_AK_Army', '兵数', ARMY[:3])
        _members(t, 'CNV_AK_Cln', '清扫', ai['cleanup'])
        _members(t, 'CNV_AK_DefT', '防御型', ai['defense type'])
        _kind_members(t, 'CNV_AK_Pool', '池兵', pool, 'CAN_ATTACK')
    else:
        _members(t, 'CNV_AK_PoolAll', '池全', pool, most=40)
        _members(t, 'CNV_AK_Map', '地图队', f'{s1}/team{s1}')
        _members(t, 'CNV_AK_AtkT', '进攻型', ai['attack type'])
        _members(t, 'CNV_AK_AtkI', '进攻名', ai['attack id'])
    w = m.facts['wake at']
    t.expect += [(t.counters[0][1], w + 20.0, '>=', 0, w + 21.0)]      # weak: the readings exist
    t.bench = [('bench_watch', dict(seconds=w + (175.0 if which in ('n', 'o') else 160.0), every=1, sheet=False,
                                    lines=len(t.counters)))]
    return t


def g(m):
    """Pool CAN_ATTACK members / LandDefense_MEDIUM team by tactic type / by tactic id / army owned (as d)."""
    return _teams(m, 'g')


def h(m):
    """Pool all members / the map team teamSoviet_1 / BalancedAttackGround_MEDIUM by tactic type / by tactic id."""
    return _teams(m, 'h')


def i(m):
    """BalancedAttackGround_MEDIUM_DefenseAvoidanceAttack _0_1 / _1_0 / _0_2 / _1_1: who takes the defense team's 8."""
    return _teams(m, 'i')


def j(m):
    """LandDefense_MEDIUM_StaticDefense _0_1 / _1_0 / _0_2 / _1_1: the defense team's other copies."""
    return _teams(m, 'j')


def k(m):
    """_0_0 of the other MEDIUM land states: Overwhelm / BalancedDefense / BalancedCleanup / LandEmergencyDefense."""
    return _teams(m, 'k')


def l(m):  # noqa: E743
    """AlliedScout _0_0 / _1_0 / EscortMCV _0_0 / LandDefense _0_0 (the time base: 8 -> 0 at ~s136)."""
    return _teams(m, 'l')


def m(mm):
    """Pool CAN_ATTACK members / LandDefense _0_0 / BalancedCleanup _0_0 / the pool's per-frame peak from PEAK_FROM s."""
    return _teams(mm, 'm')


def n(m):
    """LandDefense _0_0 / BalancedCleanup _0_0 / BalancedCleanup _0_1 / LandDefense _0_1 to s185: where the unit
    after Cleanup's 14th goes (the model: Cleanup _0_1; m saw one in defense at s166)."""
    return _teams(m, 'n')


def o(m):
    """Army owned (no dogs) / BalancedCleanup _0_0 / LandDefense _0_0 / pool CAN_ATTACK to s185: the difference is
    held by teams no name reads -- do Cleanup's other slots (same name _0_0) take the units after the 14th?"""
    return _teams(m, 'o')


CHECKS = {'aiskirm': {'a': a, 'b': b, 'c': c, 'd': d, 'g': g, 'h': h, 'i': i, 'j': j, 'k': k, 'l': l, 'm': m,
                      'n': n, 'o': o},
          'aiskirmnl': {'g': g, 'h': h},
          'aiskjav': {'e': e},
          'aiskirmlow': {'d': d, 'f': f}}
