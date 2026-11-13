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
     Mission aiskirm (50000) and aiskirmlow (15000, CampAISkLow). f = d + PLAYER_GIVE_MONEY 20000 to s1, aiskirmlow only.
     aiskirm20 (20000, CampAISk20): B handoff 120 hypothesis 3 -- does the DEFENSE share build up from the budget
     switch (a tower some time after the opening although 5 % x the money stays under 800), or is it 5 % x the money
     now (no tower: the opening leaves ~11000)? Simulator (round 119, before the bench): no tower.
RESULTS d aiskirm20 (bench 2026-11-10, CampAISk20D; PASS; first money at s8, so after-wake = bench s minus 8):
  NO tower in the whole run (塔数 0 to s229 = ~221 s after wake). AI钱 at 0/60/100/120/140/160/180/200 s after wake:
    19993, 13089, 10949, ~10314, 6936, 5098, 3118, 770; under 100 at s214, 2 at s215-217, then income only (~945 at
    s229). 建筑数 2 at 10 s, 3 at 21, 4 at 41, 5 at 61, 6 at 70, 7 at 91,
    8 at 130, 9 at 140 (not towers). 兵数 8 from 52 s to 104, 10 at 114, 12 at 126, 15 at 148, 18 at 164, 24 at 189,
    26 at 203.
  Reading: 5 % x the money is under 800 from the opening's end on and no tower comes in ~90 s after it -- the share
    does not build up from the budget switch fast enough to matter; the simulator (5 % x the money now) agrees.)
RESULTS d (bench 2026-11-07; PASS; after-wake seconds = bench s minus the first-money second: s8 for aiskirm, s9 for
  aiskirmlow; the run ends ~245 s after wake, longer than the 200 s asked):
  aiskirm d, AI钱 at 0/60/100/110/120/130/140/160/180/200 s after wake: 49996, 43050, 41063, 40810, 40790, 40389,
    39740, 38300, 35685, 33608. Per 10 s: ~1160 (0-60 s), ~500 (60-100), ~260 (100-110), ~0-20 (110-120), ~400 (120-130),
    ~650 (130-140), ~720 (140-160), ~1300 (160-180), ~1040 (180-200). No cliff at 120 s: money goes out steadily.
    Towers: first at s184 (176 s after wake), second at s204 (196 s) [re-run 2026-11-10 (b121_bench2.log, PASS): towers
    s150 / s170 = 141 / 161 s after the wake s9, 建筑数 8 at 131 s, 10 at 142 s, 11 at 161 s; see x]. 建筑数 1, 2 at 11 s, 3 at 21, 4 at 41, 5 at 61,
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
       _0_2 / _1_1: 99 the whole run (no such team). the program (work/re/l4_states.md) names '<state>_<tactic type>_<the tactic's index in
       the state>_<copy>' -- both states have one tactic, so the first index is 0.
     k: BalancedAttackOverwhelm_MEDIUM _0_0 flickers 0 / 99 every ~5 s (never a member), BalancedDefense and
       LandEmergencyDefense_MEDIUM 99; **BalancedCleanup_SimpleAttack_0_0 99 -> 8 at s131** (the defense team's
       eight at once), 9 s138, 10 s139, 11 s149, 12 s155, 13 s159, 14 s161 (MaxUnits 14) and stays.
     l: AlliedScout _0_0 1 from s72 (the defense team drops 8 -> 7 -> 6 then: a dog leaves for it), _1_0 and
       EscortMCV 99; LandDefense _0_0 8 -> 0 at s128 in this run.
     l again, stock aiskirm and carrier aiskirmc side by side (bench 2026-11-13, same head, both PASS; log
       a199_l.log): stock AlliedScout _0_0 1 from s72 (defense 8 -> 7 -> 6 at s72-74), as before; **carrier
       AlliedScout _0_0 0 the whole run, defense 9 from s67 to s127** -- the dogs stay in defense. The carrier yard
       (CNVSkirmTeamsYard, a renamed copy of the yard) changes the scout teams, so aiskirmc readings say nothing
       about them (its team log: both scout teams made ~s13, tgt -1 and n 0 throughout, never expire).
     D round 105 (bench 2026-11-13, same head): the rename alone does it -- aiskxn (renamed copy, no behavior, no
       ra3ext) scout 0 / defense 9 from s68 like the old carrier; aiskxo (stock yard, ra3ext loaded, no host) scout 1
       from s71, defense 8 -> 7 -> 6 like stock. Retail data names AlliedConstructionYard (AlliedPowerPlant's
       GameDependency, budget-state filters). The carrier now recompiles the retail yard under its own id with the
       behavior: aiskirmc l scout 1 from s71, defense 8 -> 7 -> 6 at s71-73, 0 at s129 -- stock aiskirm l beside it
       s71 / s71-74 / s128 (one-second jitter). Its log (pri= = the team template's stored Priority): DEFAULT 0, DEFENSE 1, LOW 2,
       STANDARD 3, SCRIPTED 7 -- the xsd order; the scout team (LOW) takes dog 3172 from LandDefense (DEFENSE) at f1101.
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
    reselected: the re-pick check returns false while the instance has started; handoff-b 95 / aiar9-10: a quiet base never releases),
    the release is caused by Cleanup turning on: Cleanup (STANDARD, RELEASE_TO_PRIORITY) takes the DEFENSE team's
    members in one commit, and wins the pool over the defense team until full.

  n  防御型 (LandDefense _0_0) / 清扫 (BalancedCleanup _0_0) / 清扫二 (BalancedCleanup _0_1) / 防御二 (LandDefense _0_1)
     to s203. Bench 2026-11-10, aiskirm n PASS (weak; the first try hung at bench_stop, log b102_n.log; this is
     b102_n2.log): 防御型 8 at s126, 0 from s130; 清扫 8 s130, 10 s137, 14 s158 and stays; 防御型 1 at s165 only;
     **清扫二 and 防御二 99 the whole run** -- no second copy of either team is ever made.
  Reading (corrected round 103, B handoff 105): the second index is not a slot copy. the team-naming routine builds the AI's team
    name table once: for each state, each tactic (index a), each of that tactic's TeamTemplates (index b, count at
    tactic's index field) one name '<state>_<tactic type>_<a>_<b>' (no TeamTemplate: '_default'). BalancedCleanup and
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

  p  我方建筑 / 清扫 (Cleanup _0_0) / 防御型 (LandDefense _0_0) / 兵数 (no dogs) to s249. Bench 2026-11-10, aiskirm p
     PASS (weak; log work/logs/b104_p.log): 清扫 8 s129, 14 from s159; 兵数 26 by s230; player buildings 3 to s205,
     2 s206, 1 s222, **0 s224**; 防御型 2 at s224 (the dogs' team ended), **s226: 清扫 99, 防御型 14** and so to s249.
  Reading: the player's last building gone, the Cleanup teams end within ~2 s and their units go to the defense
    team (to its MaxUnits 14); no Cleanup team holds anyone again for 23 s (a new one would answer to _0_0). The
    model ends them the same way (B handoff 106), but its third Cleanup copy, still gathering, takes the 14 back
    from defense at once -- not modelled yet (dropping gathering teams whose slot lost its target also killed
    the defense teams: tried and reverted).

  q  进攻型 (BalancedAttackGround _0_0) / 进攻次 (times it appeared, 99 -> a count, latched per frame) / 压倒
     (BalancedAttackOverwhelm _0_0) / 压倒次, to s174. aiskirm (Base personality: SecondsTillTargetsExpire 5) and
     aiskexp (CampAISkExp: a personality = 1AlliedBalanced with SecondsTillTargetsExpire 12). Bench 2026-11-10, both
     PASS (weak; bench s):
     aiskirm: from s9 (the wake) one of the two answers (0 members) for exactly 5 s, then the other: BAG s9-13,
       Overwhelm s14-18, BAG s19-23 ... to s174 -- 17 BAG + 18 Overwhelm instances, each 5 s, never both, never a
       member (LandDefense holds every unit).
     aiskexp: the same with 12 s blocks: Overwhelm s9-20, BAG s21-32, Overwhelm s33-44, **Overwhelm again s45-56**
       (a new instance: the count goes 2 -> 3), BAG s57-67 ... to s174.
  Reading: a not-started instance (its team still gathering) is ended and its slot drawn again every
    SecondsTillTargetsExpire (the re-pick check's interval half, l4_states.md 1.2), the new draw in the same second; the
    draw is the weighted one (Overwhelm twice in a row at 12 s), not a turn-about. So BAG's gathering team is
    replaced every 5 s in a retail skirmish (Base writes 5; the XSD default 15 is never used by the stock AIs).

  r  进攻型 / 进攻帧 / 压倒 / 压倒帧: 帧 = script passes the instance's team answered (0 when it appears, +1 a frame,
     kept once it is gone, so a 99 row shows the last instance's whole life). Bench 2026-11-10, aiskirm r PASS (weak):
     of ~34 instances to s174, most lived **76** frames, a few 75 / 74 / 73 (s34, s139, s159); the next state's team
     is there in the same second (often the same frame) the old one goes.
  Reading: life = 75 frames (5 s x 15) counted from the team's first frame, + 1 for counting both ends (the script
    pass order against the AI update is not known); the 73-74 ones read as the slot assigned (work/re/l4_states.md) a frame or
    two before its team appears. The model (Team.made = the team's frame, ends after 75) is within a frame.

  u  维和总数 / 标枪总数 / 警犬总数 / 工程师总数 to 80 s after the wake. aiskmod (CampAISkMod: 1AlliedBalanced +
     UnitModifier Peacekeeper and Javelin soldier at OffensiveModifier = DefensiveModifier = 0). Bench 2026-11-10,
     aiskmod u PASS (bench s): dogs 1 s23, 2 s26; Javelins 1 s32, 2 s37, 3 s60; Peacekeepers 1 s43, 2 s49, 3 s54;
     no Engineer -- the same seconds as aiskirm c's stock run.
  Reading: UnitModifier at 0 changes nothing in what the barracks builds: the zeroed units are drawn as before. It
    scales only the builder's score (work/re/l4_unitbuilder.md), which no SDK personality's draw uses (no UnitBuilderUnitChoiceStrategy;
    l4_unitbuilder.md round 35). A level cannot steer or forbid a unit with it (caps / build states do that).

  v  步兵 / 塔数 / 建筑数 / AI钱 to ~110 s after the wake. aiskacp / aiskacd (1AlliedBalanced rebuilt on
     AlliedCoopBaseSkirmishPersonality, its one opening = retail AlliedStandard with the Time 10s Deposit 2000 into
     PRODUCTION / DEFENSE). Bench 2026-11-10, both PASS (bench s):
  aiskacp: 步兵 1 s25, 2 s26, 3 s33, 4 s38, 5 s44, 6 s50, 7 s56, 8 s62, then 8 to s134 (9 s136); 塔数 0 throughout;
    建筑数 2 s20, 3 s30, 4 s50, 5 s71, 6 s81, 7 s100, 8 s144 -- aiskirm c's timeline: the rebuilt AI is the stock one.
  aiskacd: 步兵 0 to the end (s128); 塔数 1 at s49, 2 at s69 (2 x 800 of the 2000), no third; 建筑数 2 s19, 3 s29,
    5 s49, 7 s69, 8 s85, 9 s106; AI钱 ~41100 at s128 (aiskacp ~41000 at s128: the same spend, towers for infantry).
  Reading: the opening's Account picks what the Deposit buys: PRODUCTION feeds the barracks, DEFENSE buys towers
    (the base defense builder spends DEFENSE) and the barracks stays idle through the opening (its budget gives
    PRODUCTION 0 %). The simulator matches the infantry, not the towers (keeps the DEFENSE 2000).
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


def u(m):
    """UnitModifier (aiskmod: Peacekeeper and Javelin soldier at OffensiveModifier = DefensiveModifier = 0; aiskirm
    the stock one, same check): totals of the barracks' four -- Peacekeepers, Javelin soldiers, dogs, Engineers --
    to 80 s after the wake. The model's guess: the zeros change nothing (no choice strategy in the SDK chain), so
    both builds make Peacekeepers and Javelins in the first minute (aiskirm c: 3 + 3 by ~52 s after the wake)."""
    t = Test()
    PK, JAV, ENG = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry', 'AlliedEngineer'
    for tpl in (PK, JAV, ENG, DOG):
        m.spawns.add(tpl)
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('CNV_AK_UPk', '维和总数', t, template=PK, player=s1)
    counted('CNV_AK_UJav', '标枪总数', t, template=JAV, player=s1)
    counted('CNV_AK_UDog', '警犬总数', t, template=DOG, player=s1)
    counted('CNV_AK_UEng', '工程师总数', t, template=ENG, player=s1)
    w = m.facts['wake at']
    t.expect += [('维和总数', w + 70.0, 'ever>=', 1, w + 80.0), ('标枪总数', w + 70.0, 'ever>=', 1, w + 80.0)]
    t.bench = [('bench_watch', dict(seconds=w + 84.0, every=1, sheet=False, lines=len(t.counters)))]
    return t


def v(m):
    """Order Account (aiskacp / aiskacd: 1AlliedBalanced rebuilt with retail AlliedStandard as its one opening, the
    `Time 10s` line's Deposit 2000 into PRODUCTION (retail) / DEFENSE): 步兵 = the barracks' four (Peacekeeper, Javelin,
    dog, Engineer) s1 owns, 塔数 (the two Allied towers), 建筑数 (yard, power, barracks, refinery, war factory, towers),
    AI钱, to 110 s after the wake. The model's guess (private ai/player.py UNIT_ACCOUNT, the barracks spends PRODUCTION
    only; OpeningMoveBudget gives PRODUCTION / DEFENSE 0 %): PRODUCTION builds as aiskirm c (8 infantry by ~52 s after
    the wake), DEFENSE builds no infantry while the opening runs (to ~120 s)."""
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    _sum(t, m, s1, 'CNV_AK_VInf', '步兵', ('AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry', DOG,
                                           'AlliedEngineer'))
    _sum(t, m, s1, 'CNV_AK_VTow', '塔数', TOWERS)
    _sum(t, m, s1, 'CNV_AK_VBlt', '建筑数', BUILDINGS + TOWERS)
    t.counters.append(('CNV_AK_VMoney', 'AI钱'))
    t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AK_VMoney')], once=False))
    w = m.facts['wake at']
    if m.facts['production deposit']:
        t.expect += [('步兵', w + 10.0, 'ever>=', 6, w + 70.0)]
    else:
        t.expect += [('步兵', w + 5.0, '<=', 0, w + 100.0)]
    t.bench = [('bench_watch', dict(seconds=w + 114.0, every=1, sheet=False, lines=len(t.counters)))]
    return t


TOWERS = ('AlliedBaseDefense', 'AlliedBaseDefenseAdvanced')
BUILDINGS = ('AlliedConstructionYard', 'AlliedPowerPlant', 'AlliedBarracks', 'AlliedRefinery', 'AlliedWarFactory')
ARMY = ('AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry', RIPTIDE, DOG)
CAP = 24                            # a sum reads at most this many per template


def _sum(t, m, s1, counter, label, templates, weights=None, cap=CAP):
    """A shown counter that is the total of what s1 owns over `templates`: each template is counted into a hidden
    counter every frame, the shown one is zeroed first and gets +weight per unit (hidden >= n for n = 1..cap;
    weights default 1 each)."""
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
    for i, tpl in enumerate(templates):
        m.spawns.add(tpl)
        h = f'{counter}_H{i}'
        wt = weights[i] if weights else 1
        t.scripts.append(Script(f'Test - {counter} own {i}', [], [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', tpl, s1, h)],
                                once=False))
        for n in range(1, cap + 1):
            t.scripts.append(Script(f'Test - {counter} {i} >= {n}', [('COUNTER', h, 3, n)],
                                    [('INCREMENT_COUNTER', wt, counter)], once=False))


def _spend(m, give=None):
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
        t.scripts += [Script('Test - give set', [('FLAG', 'Test Woke', 1)], [('SET_MILLISECOND_TIMER', 'Test Give', give)]),
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
    return _spend(m, give=160.0)


def w(m):
    """Same as f with the gift earlier: PLAYER_GIVE_MONEY 20000 at timer 128 s (~125 s after the wake, f's 160 gave at
    ~157). B handoff 121 hypothesis 1: a tower ~20 s after the gift (~145 s) = no fixed gate after the opening; still
    ~176 s = a gate (in f the tower came 20 s after the gift, at the same ~176 s as aiskirm d). Simulator (round 120,
    before the bench): the tower at 148.1 s.

    RESULTS w (bench 2026-11-10, aiskirmlow, CampAISkLowW; PASS; first money at s9, after-wake = bench s minus 9):
      the gift: 4292 -> 24063 at s135 (126 s after wake). The tower: 塔数 1 at s156 (147 s after wake, 21 s after the
      gift), one only to s253 (244 s). 建筑数 8 at s138 (129 s), 9 at s149 (140), 10 at s156 (the tower). Money after:
      ~20770 at the tower, ~16450 at 191 s, ~9950 at 244 s.
      Reading: no fixed gate after the opening -- the tower comes ~20 s after the money is there (as f: 20 s after its
      gift), as the simulator. aiskirm d's late first tower (176 s with the money there from 120) is something else:
      there the 8th building is at 163 s, here at 129 -- the tower follows the post-opening buildings (round 120)."""
    return _spend(m, give=128.0)


KINDS = ('AlliedPowerPlant', 'AlliedRefinery', 'AlliedBarracks', 'AlliedWarFactory')   # 建筑码 digits, ones first
TECH = ('AlliedTechStructure', 'AlliedSuperWeaponAdvanced', 'AlliedNavalYard')


def x(m):
    """Which buildings s1 builds after the opening (B handoff 122 (1): aiskirm d's 8th building at 163 s and the one
    with the first tower at 176 s are not known). 建筑码 = power plants + 10 x refineries + 100 x barracks + 1000 x war
    factories (each read to 9; four counters at most, so the four kinds share one), 空军 = AlliedAirfield, 科技 =
    AlliedTechStructure + AlliedSuperWeaponAdvanced + AlliedNavalYard, 塔数 as d. To ~200 s after the wake. The
    candidates are 1AlliedBalanced's build states after OpeningMove Complete (private ai/data.py):
    NonPathDependentStructure (power POWER, refinery REFINERY, barracks / airfield FACTORY) and Tech (airfield /
    tech structure / superweapon TECH, no enemy within 700); the simulator builds none of them (towers only):
    建筑码 1122 from ~91 s after the wake, towers 140.1 / 160.2 s (work/logs/b121_pred.log).

    RESULTS x (bench 2026-11-10, aiskirm, CampAISkirmX; two runs, both PASS and the same to the second; wake ~s8, so
      after-wake = bench s minus 8; logs work/logs/b121_bench.log, b121_bench2.log):
      建筑码 100 s19 (barracks), 101 s29, 111 s49, 121 s69, 122 s79, 1122 s99 (war factory: the opening's six, as the
      simulator), **1123 s138, 1124 s148** (a 3rd and 4th power plant, ~130 / ~140 s after the wake); 塔数 1 s148, 2
      s168 (~140 / ~160 s); **空军 1 at s202** (~194 s); 科技 0 to s219.
      Reading: the post-opening buildings are two power plants (NonPathDependentStructure's POWER line) and an airfield
      (FACTORY or TECH); no refinery, barracks, war factory, tech structure. The towers come at 140 / 160 as the
      simulator; a d re-run the same day (b121_bench2.log) too: towers s150 / s170 with the money at s9 = 141 / 161 s,
      建筑数 8 at s140 (131 s). The 2026-11-07 d run's 176 / 196 (8th building 163 s) is the one run that differs.

    RESULTS x on aiskpw0 / aiskpw3 (bench 2026-11-10, both PASS; log work/logs/b122_bench.log): the same AI with
      DesiredExcessPowerBuffer 0 / 300 (retail BasePersonality 100). The opening's six as above (1122 s99-s102).
      aiskpw0: **no plant after the opening** (1122 to s228), 塔数 1 s154, 2 s174, **空军 0 to s228**.
      aiskpw3: **four plants** -- 1123 s138, 1124 s148, 1125 s158, 1126 s168 (to s220); 塔数 1 s147, 2 s167; 空军 1 s219.
      Reading: the post-opening plants follow the buffer: 0 -> 0, 100 -> 2, 300 -> 4. Excess after the opening = 250 -
      175 = 75 (yard 50 counted) or 25 (not): "build while excess < buffer + 100" fits 100 and 300 either way, but not 0
      (75 < 100 would build one) unless 0 turns POWER off; B handoff 124 has the table."""
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    _sum(t, m, s1, 'CNV_AK_XKind', '建筑码', KINDS, weights=(1, 10, 100, 1000), cap=9)
    _sum(t, m, s1, 'CNV_AK_XAir', '空军', ('AlliedAirfield',), cap=9)
    _sum(t, m, s1, 'CNV_AK_XTech', '科技', TECH, cap=9)
    _sum(t, m, s1, 'CNV_AK_XTow', '塔数', TOWERS, cap=9)
    w = m.facts['wake at']
    t.expect += [('建筑码', w + 100.0, 'ever>=', 1, w + 200.0)]
    t.bench = [('bench_watch', dict(seconds=w + 204.0, every=1, sheet=False, lines=len(t.counters)))]
    return t


def y(m):
    """Does the AI build a unit of ours (aisknew / aisknew2: s1 owns, besides what it builds, a copied barracks that
    also builds CNVNewPK = the Peacekeeper under a new id)? Totals of s1's new Peacekeepers, retail Peacekeepers,
    Javelin soldiers, and 兵营码 = retail barracks + 10 x copied ones, to 150 s after the wake.
    Data's prediction (B handoff 126, l4_buildstate.md, l4_unitbuilder.md): the build states list units by template
    (none lists CNVNewPK), so aisknew builds none of it -- unless the UnitBuilder, whose candidates are 'the templates
    the player can build' (work/re/l4_unitready.md), takes it from the copied barracks; aisknew2 lists it in a build state of its own
    (FEWEST_UNIT), so >= 1 there.

    RESULTS y (bench 2026-11-11, both PASS; log work/logs/b125_bench.log, work/bench_results/aisknew*__y.json; wake
      ~s9; 兵营码 10 from s1 = the copied barracks, 11 from s19 = the opening's retail one too):
      aisknew (stock personality): **新维和 0 to s168**; 维和 6, 标枪 12 by s168 (from both barracks).
      aisknew2 (+ CNVNewBuild): 新维和 1 at s27 (the first infantry), 4 by s44, **9 by s167**; 维和 4, 标枪 6.
      Reading: the AI builds a unit of ours only when a build state of its personality lists it by template -- owning
      a factory that builds it is not enough (the UnitBuilder's candidates do not take it either). With one listed it
      takes about half the barracks' output (FEWEST_UNIT among four). So a level's 偏好 / UnitModifier cannot make it
      build our units (aiskmod u: no effect at all); plan.py would need a BuildState line, and the AI a factory of its
      own that builds the unit (the copies are the player's only).

    RESULTS y on aiskcap (bench 2026-11-12, PASS; run work/testbench/runs/CampAISkCapY_mcp_1112_043040): aisknew2 +
      the child personality's SpecificUnitCap CNVNewPK Cap 2 at all four difficulties (no parent lists CNVNewPK; the
      simulator predicted 2 to s167, work/logs/b145_pred.log). 新维和 1 s27, **2 from s33 to s149** (aisknew2: 3 s38,
      4 s44) while 标枪 went 1 -> 6 and 维和 0 -> 2; then **3 at s150, 4 from s155** to s168 (维和 5, 标枪 9).
      Reading: the cap binds (template match, the MEDIUM bit, the value) -- the barracks' other units take the
      capped one's turns; after ~s150 the capped unit is built again with none lost, so what the engine counts
      against the cap is not simply the units owned (not known; tests/test_simai_bench_b.py strict xfail).

    RESULTS y on aiskblk* (bench 2026-11-12, all three PASS; runs work/testbench/runs/CampAISkBlk{N,F,R}Y_mcp_1112_*):
      aisknew2 whose CNVNewPK entry carries BlockIfThingNearFactory Rule ANY Relationship NEUTRAL IncludeThing <a
      neutral blocker north of the copied barracks>, default distance 150.
      aiskblkn (bear 120 away): **新维和 0 to s168**; 维和 6, 标枪 11 (the barracks build the rest).
      aiskblkf (bear 400 away): 新维和 1 s28, 4 s45, **9 s167** -- as aisknew2 (1 s27, 9 s167).
      aiskblkr (an allied power plant whose centre is 190 away): **新维和 0 to s168**; 维和 9, 标枪 9.
      Reading: as D59 read it -- an entry scores 0 while a thing passing the filter is within the distance of the
      factory; 'within' adds the thing's bounding circle (centre 190 > 150, circle in reach), and NEUTRAL matches a
      neutral thing.

    RESULTS y on aiskoff (bench 2026-11-12, PASS; run work/testbench/runs/CampAISkOffY_mcp_1112_111724): aisknew2
      whose build state's heuristic is ScriptedFlagHeuristic on a flag nobody sets (the state never scores, CNVNewPK
      still listed): **新维和 0 to s168**; 维和 6, 标枪 12 (as aisknew). Reading: the unit builder never takes our
      unit, even listed in a build state of the mission's own -- every new Peacekeeper of aisknew2 / aiskblkf is the
      build state's, and aiskblkn / aiskblkr's 0 is the block alone."""
    NEW_PK, NEW_BARRACKS = 'CNVNewPK', 'CNVAIBarracks'      # missions/aiskirm_bench.py's (G5: no content import)
    t = Test()
    PK, JAV = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry'
    for tpl in (PK, JAV):
        m.spawns.add(tpl)
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('CNV_AK_YNew', '新维和', t, template=NEW_PK, player=s1)
    counted('CNV_AK_YPk', '维和总数', t, template=PK, player=s1)
    counted('CNV_AK_YJav', '标枪总数', t, template=JAV, player=s1)
    _sum(t, m, s1, 'CNV_AK_YBar', '兵营码', ('AlliedBarracks', NEW_BARRACKS), weights=(1, 10), cap=9)
    w = m.facts['wake at']
    t.expect += [('兵营码', w + 140.0, 'ever>=', 10, w + 150.0)]
    t.bench = [('bench_watch', dict(seconds=w + 154.0, every=1, sheet=False, lines=len(t.counters)))]
    return t


def yc(m):
    """aiskcu / aiskcs (check yc): does a unit counted as a structure by the personality's
    CountAsStructureForBuildPurposesFilter block the AI's other unit orders? Both builds: aisknew2 + CNVDearPK (the
    Peacekeeper at build cost 100000, from a second copied barracks, CONSTANT 1 in the build state); aiskcs also adds
    CNVDearPK to the filter. Counters: 新维和 (CNVNewPK), 贵维和 (CNVDearPK, expected 0), 维和总数, 标枪总数, per second
    to 170 s after the wake. Prediction: aiskcu builds CNVNewPK as aisknew2; aiskcs builds none from the state."""
    NEW_PK, DEAR_PK = 'CNVNewPK', 'CNVDearPK'      # missions/aiskirm_bench.py's (G5: no content import)
    t = Test()
    PK, JAV = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry'
    for tpl in (PK, JAV):
        m.spawns.add(tpl)
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('CNV_AK_YCNew', '新维和', t, template=NEW_PK, player=s1)
    counted('CNV_AK_YCDear', '贵维和', t, template=DEAR_PK, player=s1)
    counted('CNV_AK_YCPk', '维和总数', t, template=PK, player=s1)
    counted('CNV_AK_YCJav', '标枪总数', t, template=JAV, player=s1)
    w = m.facts['wake at']
    t.expect += [('贵维和', w + 160.0, 'ever>=', 0, w + 170.0)]
    t.bench = [('bench_watch', dict(seconds=w + 170.0, every=1, sheet=False, lines=len(t.counters)))]
    return t


def ycm(m):
    """yc with AI钱 (s1's money, each frame) in place of 标枪总数: B handoff 157's K1 / K2 -- when CNVDearPK
    (100000 against the 50000 the AI holds) is ordered (yc: s134 aiskcu / s138 aiskcs), is the money at some gate,
    and after it does aiskcs's barracks stay idle while the money sits?
    Bench 11-12 (work/bench_results/aiskc[su]__ycm.json, both PASS): AI钱 50000 -> ~41000 by s120 (the opening and
    two new Peacekeepers), then ~36000 paid within s128-s133 and 贵维和 1 at s133 (cs) / s134 (cu), the money ~5300
    after; 新维和 3 at s133 / s134, 4 at s196 (cs) / s172 (cu), 6 at s216 / s184. So the dear one is paid fast at the
    end, not refused for want of 100000 (K1 / K3); aiskcs did not stall this time (yc's 3-to-the-end not repeated).
    aiskcu3 (the same at 30000, bench 11-12 work/bench_results/aiskcu3__ycm.json, PASS): money 41055 at s127, paid
    down to 9585 by s132 (~31500 in the same five seconds), 贵维和 1 at s133 -- the same order time as at 100000, so the
    cost does not gate the order; at 100000 the payment stops ~36000 in (money ~5300 left) and the unit still comes."""
    t = yc(m)
    t.counters = [c for c in t.counters if c[1] != '标枪总数']
    t.counters.append(('CNV_AK_YCMoney', 'AI钱'))
    t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', m.player('s1'), 'CNV_AK_YCMoney')],
                            once=False))
    return t


def yb(m):
    """aiskcap diagnosis (B handoff 148): is the SpecificUnitCap overrun at s150 / s155 (check y: 新维和 3, 4) a second
    barracks? Counters, each as owned objects of s1 by template (counted(); whether one under construction counts is
    what the reading shows): 兵营 = retail AlliedBarracks, 复制兵营 = CNVAIBarracks (the player's copy), 新维和 =
    CNVNewPK, 标枪总数. Per second to 170 s after the wake (read from the watch rows).
    RESULTS (bench 2026-11-12, run CampAISkCapYb_mcp_1112_095845, PASS): 兵营 0 to s18, 1 from s19 to the end; 复制兵营 1
    throughout; 新维和 2 from s33 to s149, 3 at s150, 4 at s156; 标枪 6 at s150, 7-9 by s172. No barracks appears near the
    overrun: the AI has the same two (retail + copy) from s19 on."""
    NEW_PK, NEW_BARRACKS = 'CNVNewPK', 'CNVAIBarracks'
    t = Test()
    JAV = 'AlliedAntiVehicleInfantry'
    m.spawns.add(JAV)
    for tpl in ('AlliedBarracks', NEW_BARRACKS):
        try:
            m.spawns.add(tpl)
        except Exception:
            pass
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('CNV_AK_YBBar', '兵营', t, template='AlliedBarracks', player=s1)
    counted('CNV_AK_YBCopy', '复制兵营', t, template=NEW_BARRACKS, player=s1)
    counted('CNV_AK_YBNew', '新维和', t, template=NEW_PK, player=s1)
    counted('CNV_AK_YBJav', '标枪总数', t, template=JAV, player=s1)
    w = m.facts['wake at']
    t.expect += [('兵营', w + 140.0, 'ever>=', 1, w + 150.0)]
    t.bench = [('bench_watch', dict(seconds=w + 170.0, every=1, sheet=False, lines=len(t.counters)))]
    return t


def s(m):
    """RANDOM_UNIT percents and BuildState.Difficulty (aiskrand / aiskdiff: s1 owns, besides what it builds, a copied
    barracks that also builds CNVNewPK / CNVNewJav = Peacekeeper / Javelin under new ids). Totals of s1's new
    Peacekeepers, new Javelins, retail Peacekeepers and Javelins, to 150 s after the wake.
    Data's prediction (l4_buildstate.md 2: RANDOM 10000 when PercentLow < roll < PercentHigh, one roll in [0, 1) an
    evaluation): aiskrand -- 新维和 (0%..30%) wins about 3 evaluations in 10; 新标枪 ("30".."100", no '%') never if a
    bare number is read as itself (the engine model's _percent), about 7 in 10 if it is a percent. aiskdiff -- the
    HARD-only state never runs at MEDIUM: 新维和 0; the MEDIUM one does: 新标枪 >= 1 (FEWEST_UNIT, as aisknew2).

    RESULTS s (bench 2026-11-11, both PASS; runs CampAISkRandS_mcp_1111_223512, CampAISkDiffS_mcp_1111_223815):
      aiskrand: 新维和 1 s38, 4 s161; **新标枪 1 s27, 4 s167**; 维和 4, 标枪 7 beside (the retail barracks).
      Reading: a bare "30" is 30 % (the Percentage type), not 30 -- retail AlliedBarracksBuildState_RANDOM's bare
      0..100 are percents. The split 4 : 4 (30 : 70 predicted) is too few to tell more.
      aiskdiff: **新维和 0 to s169**; 新标枪 1 s27, 8 s167; 维和 5, 标枪 6.
      Reading: a build state hung at HARD only does not run at MEDIUM; Difficulty gates the state."""
    NEW_PK, NEW_JAV = 'CNVNewPK', 'CNVNewJav'      # missions/aiskirm_bench.py's (G5: no content import)
    t = Test()
    PK, JAV = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry'
    for tpl in (PK, JAV):
        m.spawns.add(tpl)
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('CNV_AK_SPk', '新维和', t, template=NEW_PK, player=s1)
    counted('CNV_AK_SJav', '新标枪', t, template=NEW_JAV, player=s1)
    counted('CNV_AK_SRPk', '维和总数', t, template=PK, player=s1)
    counted('CNV_AK_SRJav', '标枪总数', t, template=JAV, player=s1)
    w = m.facts['wake at']
    t.expect += [('新标枪' if m.facts['difficulty gate'] else '新维和', w + 140.0, 'ever>=', 1, w + 150.0)]
    t.bench = [('bench_watch', dict(seconds=w + 154.0, every=1, sheet=False, lines=len(t.counters)))]
    return t


def z(m):
    """Does the AI build against the player's army (aiskvinf: the player owns 10 conscripts, aiskvveh: 10 Hammer
    tanks, idle behind its yard on the west bank; otherwise aiskirm)? Totals of s1's Peacekeepers, Javelin soldiers,
    Guardian tanks and Riptides, to 150 s after the wake. Data's prediction (l4_buildstate.md 1): 1AlliedBalanced
    at MEDIUM lists those in AlliedLandUnitBuildState as BEST_UNIT_EXPECTED (score = the expected efficiency against
    the enemy), so vs conscripts more Peacekeepers, vs tanks more Javelins (and Guardians once a war factory stands)
    than the other build -- beside the UnitBuilder's uniform draw (l4_unitbuilder.md)."""
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    names = (('AlliedAntiInfantryInfantry', 'CNV_AK_ZPk', '维和总数'), ('AlliedAntiVehicleInfantry', 'CNV_AK_ZJav', '标枪总数'),
             ('AlliedAntiVehicleVehicleTech1', 'CNV_AK_ZGrd', '守护者总数'),
             ('AlliedAntiInfantryVehicle', 'CNV_AK_ZRip', '激流总数'))     # four counter lines at most
    for tpl, counter, label in names:
        m.spawns.add(tpl)
        counted(counter, label, t, template=tpl, player=s1, most=16)
    w = m.facts['wake at']
    t.expect += [('标枪总数' if m.facts['player vehicles'] else '维和总数', w + 140.0, 'ever>=', 4, w + 150.0)]
    t.bench = [('bench_watch', dict(seconds=w + 154.0, every=1, sheet=False, lines=len(t.counters)))]
    return t
# RESULTS z (bench 2026-11-11, work/logs/b128_counter.log, work/bench_results/aiskv*__z.json; wake ~s10):
#   aiskvinf (10 conscripts): 维和 1 s32, 4 s60, 7 s164; **标枪 0 to s169**; 守护者 0; 激流 1 s111 .. 6 s165.
#   aiskvveh (10 Hammers):    **维和 0 to s185**; 标枪 1 s29, 6 s57, 14 s185; 守护者 0; 激流 1 s112 .. 3 s133.
#   Reading: the barracks builds only the counter -- no draw among its units (the unit builder's uniform pick would
#   give ~1/3 Peacekeepers vs the tanks): BEST_UNIT_EXPECTED decides the barracks (l4_efficiency.md). (The first
#   aiskvinf run expected a Javelin and FAILed on it; the expectation is now the counter's.)


def t(m):
    """Where does the opening's last 200 go (aiskvveh: six Javelins = 1800 of the PRODUCTION Deposit 2000)? z counts
    no dogs or engineers; this counts s1's Peacekeepers, Javelins, attack dogs and engineers to 150 s after the wake.
    The model (unit builder: a uniform draw among the barracks' units, the drawn one bought if it fits the account)
    spends it on a Peacekeeper or a dog (200 each; 5 of 6 seeds a Peacekeeper) about s58-s85; z's bench had no
    Peacekeeper. Prediction: one dog, no Peacekeeper -- the draw, not a rule; no dog either = the 200 stays."""
    tt = Test()
    s1 = m.player('s1')
    tt.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    names = (('AlliedAntiInfantryInfantry', 'CNV_AK_TPk', '维和总数'), ('AlliedAntiVehicleInfantry', 'CNV_AK_TJav', '标枪总数'),
             ('AlliedScoutInfantry', 'CNV_AK_TDog', '警犬总数'), ('AlliedEngineer', 'CNV_AK_TEng', '工程师总数'))
    for tpl, counter, label in names:
        m.spawns.add(tpl)
        counted(counter, label, tt, template=tpl, player=s1, most=16)
    w = m.facts['wake at']
    tt.expect += [('警犬总数', w + 140.0, 'ever>=', 1, w + 150.0)]
    tt.bench = [('bench_watch', dict(seconds=w + 154.0, every=1, sheet=False, lines=len(tt.counters)))]
    return tt
# RESULTS t (bench 2026-11-12, work/testbench/runs/CampAISkVVehT_mcp_1112_011517): PASS. 警犬 1 s23 (before the first
#   Javelin, s29), 标枪 6 s57 .. 11 s166, 维和 0 to s168, 工程师 1 s144. The barracks' first unit is the unit builder's
#   draw; the build states then take it (B handoff 142).


JAV_OUT_AT = 100.0                 # mission second the named Javelin soldier is teleported out (e)


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


def _built(t, m):
    """我方建筑: how many of the player's yard / war factory / power plant are alive (0-3), as in a."""
    p1 = m.player('p1')
    t.counters.append(('CNV_AK_Built', '我方建筑'))
    t.scripts.append(Script('Test - built zero', [], [('SET_COUNTER', 'CNV_AK_Built', 0)], once=False))
    for i, tpl in enumerate(YOURS):
        m.spawns.add(tpl)
        t.scripts += [Script(f'Test - own {i}', [], [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', tpl, p1, f'CNV_AK_Own{i}')],
                             once=False),
                      Script(f'Test - built {i}', [('COUNTER', f'CNV_AK_Own{i}', 3, 1)],
                             [('INCREMENT_COUNTER', 1, 'CNV_AK_Built')], once=False)]


def _members(t, counter, label, team, most=POOL_MOST):
    """`team`'s member count (TEAM_COMPARE_NUM_MEMBERS ==), UNKNOWN when it is none of 0 .. most-1."""
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter} unknown', [], [('SET_COUNTER', counter, UNKNOWN)], once=False))
    t.scripts += [Script(f'Test - {counter} {n}', [('TEAM_COMPARE_NUM_MEMBERS', team, 2, n)],
                         [('SET_COUNTER', counter, n)], once=False) for n in range(most)]


def _appearances(t, counter, n_counter, label):
    """How many times the team `counter` reads (_members) has appeared (99 -> a count), latched every frame."""
    seen = n_counter + 'S'
    t.counters.append((n_counter, label))
    t.scripts += [Script(f'Test - {n_counter} on', [('COUNTER', counter, 0, UNKNOWN), ('COUNTER', seen, 2, 0)],
                         [('INCREMENT_COUNTER', 1, n_counter), ('SET_COUNTER', seen, 1)], once=False),
                  Script(f'Test - {n_counter} off', [('COUNTER', counter, 2, UNKNOWN)], [('SET_COUNTER', seen, 0)],
                         once=False)]


def _lifetime(t, counter, f_counter, label):
    """Frames the team `counter` reads has answered since it last appeared (reset to 0 when it appears, +1 every frame
    it answers, kept while it is gone): read while it shows 99, it is the last instance's whole life in frames."""
    seen = f_counter + 'S'
    t.counters.append((f_counter, label))
    t.scripts += [Script(f'Test - {f_counter} new', [('COUNTER', counter, 0, UNKNOWN), ('COUNTER', seen, 2, 0)],
                         [('SET_COUNTER', f_counter, 0), ('SET_COUNTER', seen, 1)], once=False),
                  Script(f'Test - {f_counter} tick', [('COUNTER', counter, 0, UNKNOWN)],
                         [('INCREMENT_COUNTER', 1, f_counter)], once=False),
                  Script(f'Test - {f_counter} off', [('COUNTER', counter, 2, UNKNOWN)], [('SET_COUNTER', seen, 0)],
                         once=False)]


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
    (work/re/l4_states.md: state, a tactic string, two indices; retail maps query e.g. 'Player_2/AIState_J09_LandAttack_
    SimpleAttack_0_0'); the pool is 'defaultSkirmishTeam' + player (work/re/l4_states.md). Which tactic string (the Tactic id
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
    elif which == 'q':                 # is a gathering (not started) instance re-picked every SecondsTillTargetsExpire?
        for key, ctr, say, nsay in (('attack type', 'AtkT', '进攻型', '进攻次'), ('overwhelm', 'Ovw', '压倒', '压倒次')):
            _members(t, f'CNV_AK_{ctr}', say, ai[key])
            _appearances(t, f'CNV_AK_{ctr}', f'CNV_AK_{ctr}N', nsay)
    elif which == 'r':                 # how many frames does one gathering instance last (team made -> gone)?
        for key, ctr, say, fsay in (('attack type', 'AtkT', '进攻型', '进攻帧'), ('overwhelm', 'Ovw', '压倒', '压倒帧')):
            _members(t, f'CNV_AK_{ctr}', say, ai[key])
            _lifetime(t, f'CNV_AK_{ctr}', f'CNV_AK_{ctr}F', fsay)
    elif which == 'p':                 # past the player's last building: do the attack teams end and hand back?
        _built(t, m)
        _members(t, 'CNV_AK_Cln', '清扫', ai['cleanup'])
        _members(t, 'CNV_AK_DefT', '防御型', ai['defense type'])
        _sum(t, m, s1, 'CNV_AK_Army', '兵数', ARMY[:3])
    else:
        _members(t, 'CNV_AK_PoolAll', '池全', pool, most=40)
        _members(t, 'CNV_AK_Map', '地图队', f'{s1}/team{s1}')
        _members(t, 'CNV_AK_AtkT', '进攻型', ai['attack type'])
        _members(t, 'CNV_AK_AtkI', '进攻名', ai['attack id'])
    w = m.facts['wake at']
    t.expect += [(t.counters[0][1], w + 20.0, '>=', 0, w + 21.0)]      # weak: the readings exist
    t.bench = [('bench_watch', dict(seconds=w + {'n': 175.0, 'o': 175.0, 'p': 232.0}.get(which, 160.0), every=1, sheet=False,
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


ORE_TARGET = (4278.8, 3093.3)       # et: the ore node the model's ClosestTechBuildingHeuristic picks (model fca219e)


def et(m):
    """Where does AlliedCaptureTech_MEDIUM's Engineer tactic take its engineer, and does it capture? (line A round
    203). 工程队 = the team by its engine name (AlliedCaptureTech_MEDIUM_EngineerTactic_0_0), 油井 = OilDerricks s1 owns (the map's one, neutral, at niagara DERRICKS), 到油井 / 到矿点 =
    s1's engineers inside 250 of the derrick / 120 of ORE_TARGET. Two predictions: the model (fca219e) sends the engineer
    to the ore node ~s155 and captures nothing (its act is a no-op); the data (the state's TechBuildingShare reads
    the derrick, KindOf of the tech buildings) -- to the derrick, which turns s1's and the engineer is gone.
    MEASURED (bench 2026-11-13, head 7020cbfc, work/bench_results/aiskirm__et.json, PASS): s1-127 99 0 0 0 |
    s128-143 0 0 0 0 | s144-215 1 0 0 0 | s216-221 1 0 1 0 | s222 0 1 0 0 | s223-284 99 1 0 0 -- the derrick: the
    engineer reaches it s216, s1 owns it s222 and the team is gone that second; never at the ore node. The model
    gets the team (s131 / s145), not the target or the capture (tests/test_simai_engineer_tactic.py)."""
    t = Test()
    for tpl in ARMY:
        m.spawns.add(tpl)
    s1 = m.player('s1')
    m.spawns |= {'AlliedEngineer', 'OilDerrick'}          # the scripts' contract: templates the counters name
    team = {k[3:]: v for k, v in m.map.TEAMS.items() if k.startswith('ai ')}['capture tech']
    (dx, dy), = m.map.DERRICKS
    t.areas['Test Derrick'] = square(dx, dy, 250)
    t.areas['Test Ore'] = square(*ORE_TARGET, 120)      # small: the AI's base is ~600 away
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    _members(t, 'CNV_AK_ETeam', '工程队', team)
    counted('CNV_AK_EOil', '油井', t, template='OilDerrick', player=s1)
    counted('CNV_AK_EAtD', '到油井', t, template='AlliedEngineer', area='Test Derrick', player=s1)
    counted('CNV_AK_EAtO', '到矿点', t, template='AlliedEngineer', area='Test Ore', player=s1)
    w = m.facts['wake at']
    t.expect += [('工程队', w + 20.0, '>=', 0, w + 21.0)]      # weak: the readings exist
    t.bench = [('bench_watch', dict(seconds=w + 260.0, every=1, sheet=False, lines=len(t.counters)))]
    return t


def n(m):
    """LandDefense _0_0 / BalancedCleanup _0_0 / BalancedCleanup _0_1 / LandDefense _0_1 to s185: where the unit
    after Cleanup's 14th goes (the model: Cleanup _0_1; m saw one in defense at s166)."""
    return _teams(m, 'n')


def o(m):
    """Army owned (no dogs) / BalancedCleanup _0_0 / LandDefense _0_0 / pool CAN_ATTACK to s185: the difference is
    held by teams no name reads -- do Cleanup's other slots (same name _0_0) take the units after the 14th?"""
    return _teams(m, 'o')


def q(m):
    """BalancedAttackGround _0_0 / its appearances / BalancedAttackOverwhelm _0_0 / its appearances to s170: is a
    not-started instance re-picked every SecondsTillTargetsExpire (work/re/l4_states.md 1.2; Base writes 5 s; aiskexp writes 12)?"""
    return _teams(m, 'q')


def r(m):
    """BalancedAttackGround _0_0 / frames its last instance lived / Overwhelm _0_0 / the same: does a gathering
    instance last exactly SecondsTillTargetsExpire x 15 = 75 frames from its team's first frame (the model's rule)?"""
    return _teams(m, 'r')


def p(m):
    """我方建筑 / BalancedCleanup _0_0 / LandDefense _0_0 / army owned (no dogs) to ~s240: when the player's last
    building dies, do the attack teams end at once and hand their units back to the defense team (the model, ~197 s
    after the wake: AlliedScout target gone -> DISBAND, both Cleanups 'rampage: nobody left', LandDefense takes them)?"""
    return _teams(m, 'p')


def pt(m):
    """Which name does PLAYER_IS_HUMAN_OR_AI_PERSONALITY match (aiskpt: s1's personality has the id CNVPtId and the
    PersonalityType CNVPtType; aiskpti: the same id, no PersonalityType written)? 人格位 = the sum, every frame, of
    1 (s1, CNVPtType), 2 (s1, CNVPtId), 4 (s1, 1AlliedBalanced = the parent's id and type), 8 (Player_1, Human);
    to 30 s after the wake.
    Data's prediction (D59, work/re/d59_b_fields.md 1: the condition compares the AI's PersonalityType by name; what
    a child that writes none holds was not read): aiskpt 1 + 8 = 9 (the simulator, comparing the side's asset id,
    says 2 + 8 = 10); aiskpti 8 if an unwritten type is empty, 4 + 8 if it inherits, 2 + 8 if it falls back to the
    id. Before the wake the bits may differ (Lib_Skirmish_Setup hands s1 to its AI at frame 0).

    RESULTS pt (bench 2026-11-12, both PASS; runs work/testbench/runs/CampAISkPtPt_mcp_1112_115516,
      CampAISkPtIPt_mcp_1112_115743): aiskpt **人格位 10 every second s1-s41**, aiskpti **10 s1-s42** -- (s1, CNVPtId)
      and (Player_1, Human) hold, (s1, CNVPtType) and (s1, 1AlliedBalanced) never. Reading: the condition matches the
      personality's asset id (the side's aiPersonality), not its PersonalityType (D59's reading does not hold), and
      whether PersonalityType is written changes nothing; the simulator (comparing the id) gives 10 on both."""
    t = Test()
    s1, p1 = m.player('s1'), m.player('p1')
    counter = 'CNV_AK_PtBits'
    t.counters.append((counter, '人格位'))
    parts = [(1, ('PLAYER_IS_HUMAN_OR_AI_PERSONALITY', s1, 'CNVPtType')),
             (2, ('PLAYER_IS_HUMAN_OR_AI_PERSONALITY', s1, 'CNVPtId')),
             (4, ('PLAYER_IS_HUMAN_OR_AI_PERSONALITY', s1, '1AlliedBalanced')),
             (8, ('PLAYER_IS_HUMAN_OR_AI_PERSONALITY', p1, 'Human'))]
    t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
    t.scripts += [Script(f'Test - {counter} {k}', [c], [('INCREMENT_COUNTER', wt, counter)], once=False)
                  for k, (wt, c) in enumerate(parts)]
    w = m.facts['wake at']
    t.expect += [('人格位', w + 5.0, '>=', 8)]          # Player_1 is Human the whole run (scripts1 cond)
    t.bench = [('bench_watch', dict(seconds=w + 30.0, every=1, sheet=False, lines=len(t.counters)))]
    return t

def mt(m):
    """When does s1 start its first AlliedTechStructure (aiskmt: its own ConstantHeuristic state's one entry, TECH
    MinTime 150 s ForceTime 151 s; aiskmto: MinTime 250 s ForceTime 151 s; s1 owns an airfield and a refinery from
    s0, the tech building's prerequisites)? 科技楼 = how many s1 owns; 科技帧 = frames from the wake (+30) while it
    owns none (stops at the first); 电厂 = power plants owned (3 placed); AI钱. To 300 s after the wake.
    First run (2026-11-12, without the 3 plants, run CampAISkMTMt_mcp_1112_122317): no tech building to s322 -- the
    opening + the airfield + the refinery draw 275 against 250, so the power gate held it (the plants added since).
    Second run (with the 3 plants, run CampAISkMTMt_mcp_1112_123106, PASS): **still no tech building to s377**
    (~365 s after the wake, past ForceTime 151); 电厂 3 -> 4 at s29 -> 5 at s80 (the opening's two), money 50000 ->
    8900 on units. Power is not what holds it: some other gate (B handoff 154's table). aiskmto not run yet.
    aiskmtc (CONSTANT 300 tower, run CampAISkMTCMt_mcp_1112_125012): towers at s148 / s172 / s258; aiskmtt (the same
    tower TECH MinTime 200 ForceTime 201, run CampAISkMTTMt_mcp_1112_125641): s149 / s169 / s265 -- the same, so the
    towers are the inherited stock state's, not this entry's: neither run tells (B handoff 155; the yard's gate is
    asked of D). A rerun needs a building no stock state builds.
    Data's prediction (D59, work/re/d59_b_fields.md 3): aiskmt forced (200) from t > 151 s after the wake -> 科技帧
    stops at ~151 x 15 (plus the yard's queue: the opening may still hold it); aiskmto: if t < MinTime is tested
    first, ~250 s; if ForceTime first, ~151 s as aiskmt. The stock tech state (MinTime 360 s) cannot come first. The
    simulator scores no TECH entry: none in either.
    aiskmt0 (TECH MinTime 0 ForceTime 1, three more plants = 6, D82 G1 + G2 in one run; bench 11-12
    work/bench_results/aiskmt0__mt.json, PASS): 科技帧 stops at 2256 (~150 s after the wake), 科技楼 1 by s177, money
    50000 -> ~9800 by s376 -- the TECH entry does build here. G1 / G2 not yet split (next: 0 / 1 with 3 plants).
    aiskmt03 (TECH 0 / 1, the three plants only; bench 11-12 work/bench_results/aiskmt03__mt.json, PASS): 科技帧
    stops at 2256 again, 科技楼 1 at s227 (电厂 3 -> 5 by s102) -- the very frame of aiskmt0: power is not the gate
    (G1 no). aiskmt2 (TECH 200 / 201, six plants; aiskmt2__mt.json, PASS): no tech building to s367 (科技帧 4721,
    ~315 s after the wake) -- MinTime 200 is not "200 s after the wake" (G2: the evaluator's clock or MinTime's unit
    differs; next MinTime 20 / 21: ~150 s -> seconds, ~300 s -> MinTime counted x15).
    aiskmt20 (TECH 20 / 22, six plants, watched 600 s; bench 11-12 aiskmt20__mt.json, PASS; 20 / 21 compiled a map
    stream the game crashed on, see the build list): 科技帧 stops at 2256 again, 科技楼 1 at s158 -- the very
    frame of 0 / 1 (MinTime x15 = 300 s is out). MinTime <= 20 all start at f2256, 150 / 200 never: as if the
    entry were judged once, near f2256, and a t < MinTime then never came back (next: 140 / 142 against 160 / 162).
    aiskmt14 / aiskmt16 (140 / 142, 160 / 162, six plants, 600 s; aiskmt14__mt.json / aiskmt16__mt.json, PASS): both
    stop at 科技帧 5857 (3601 frames ~ 240 s after 2256). aiskmt15 (150 / 152) and aiskmt40 (400 / 402), six plants
    (bench 11-13 aiskmt15__mt.json / aiskmt40__mt.json, PASS): BOTH stop at 5857 too, though 5857 frames after the
    wake is ~390 s < 400. So the TECH entry starts at one of two frames, 2256 (MinTime <= 20) or 5857 (140 .. 400);
    a gate "seconds since the wake >= MinTime" fits neither 140 (no at 2256, ~150 s) nor 400 (yes at 5857, ~390 s).
    aiskmt99 (1000 / 1002, six plants; aiskmt99__mt.json, PASS): 5857 again, 科技楼 1 -- the second look (~240 s
    after the first) builds whatever MinTime says (INFERRED: MinTime is checked at the first look only, or that
    later look is a path that does not read it). Between 20 and 140 the first-look threshold is not measured."""
    t = Test()
    s1 = m.player('s1')
    if m.facts['min time'] is None and m.facts.get('const') == 'AlliedTechStructure':   # aiskmtk: CONSTANT tech
        _sum(t, m, s1, 'CNV_AK_Tech', '科技楼', ('AlliedTechStructure',))
    elif m.facts['build'] != 'AlliedTechStructure' or m.facts['min time'] is None:   # aiskmtc / aiskmtt: the tower
        _sum(t, m, s1, 'CNV_AK_Tech', '塔', ('AlliedBaseDefense',))
    else:
        _sum(t, m, s1, 'CNV_AK_Tech', '科技楼', ('AlliedTechStructure',))
    _sum(t, m, s1, 'CNV_AK_Pow', '电厂', ('AlliedPowerPlant',))
    t.counters.append(('CNV_AK_Money', 'AI钱'))
    t.counters.append(('CNV_AK_TechF', '科技帧'))
    t.scripts += [Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AK_Money')], once=False),
                  Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AK_Tick')], once=False),
                  Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AK_Tick', 3, 30)],
                         [('SET_FLAG', 'Test Woke', 1)]),
                  Script('Test - tech frames', [('FLAG', 'Test Woke', 1), ('COUNTER', 'CNV_AK_Tech', 0, 1)],
                         [('INCREMENT_COUNTER', 1, 'CNV_AK_TechF')], once=False)]
    w = m.facts['wake at']
    t.expect += [('电厂', w + 5.0, '>=', 3)]
    t.bench = [('bench_watch', dict(seconds=w + m.facts.get('mt secs', 300.0), every=1, sheet=False,
                                    lines=len(t.counters)))]
    return t


WEST = 'CNV AI West Area'
PK = 'AlliedAntiInfantryInfantry'


def fm(m):
    """aiskfon / aiskfof (the global AIData overridden in the map stream, UseFormations true / false; aiskad's canary
    first): the first attack team (2 Riptides + 3 Peacekeepers, check a / c) leaving home and reaching the player's
    base. 激流在家 / 维和在家 = s1's inside 600 around the east base, 激流到 / 维和到 = inside 600 around the player's
    yard; 1-s rows to 250 s after the wake: who leaves and who arrives in which second (the team's spread in time).
    Not run: aiskad's canary (TeamSeconds 100000, MaxRecruitDistance 1; bench 2026-11-12, aiskad a PASS,
    CampAISkADA_mcp_1112_130959) read as the stock run -- first Riptide s113, 出门帧 stops at 1992 (stock 1992), the
    player's buildings gone s209-s231 -- although the built map stream carries our AIData:AIData: the map-stream
    override of AIData does not take (or neither field is read), so this pair would read the same (pathing.md 5b)."""
    t = Test()
    m.spawns.add(RIPTIDE)
    m.spawns.add(PK)
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[AREA] = square(*m.site('east base'), 600.0)
    t.areas[WEST] = square(*m.site('base yard'), 600.0)
    counted('CNV_AK_Home', '激流在家', t, template=RIPTIDE, area=AREA, player=s1)
    counted('CNV_AK_PkHome', '维和在家', t, template=PK, area=AREA, player=s1)
    counted('CNV_AK_West', '激流到', t, template=RIPTIDE, area=WEST, player=s1)
    counted('CNV_AK_PkWest', '维和到', t, template=PK, area=WEST, player=s1)
    w = m.facts['wake at']
    t.expect += [('激流在家', w + 150.0, 'ever>=', 1, w + 250.0)]
    t.bench = [('bench_watch', dict(seconds=w + 250.0, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {'aiskirm': {'a': a, 'b': b, 'c': c, 'd': d, 'g': g, 'h': h, 'i': i, 'j': j, 'k': k, 'l': l, 'm': m,
                      'n': n, 'o': o, 'p': p, 'q': q, 'r': r, 'u': u, 'x': x, 'et': et},
          'aiskirmc': {'l': l, 'm': m, 'u': u},  # opt-in carrier diagnostic; stock aiskirm stays unchanged
          'aiskxn': {'l': l}, 'aiskxo': {'l': l},  # D 105: which half of the carrier moves the scout team
          'aiskexp': {'q': q},
          'aiskmod': {'u': u},
          'aiskacp': {'v': v},
          'aiskacd': {'v': v},
          'aiskirmnl': {'g': g, 'h': h},
          'aiskjav': {'e': e},
          'aiskirmlow': {'d': d, 'f': f, 'w': w},
          'aiskirm20': {'d': d},
          'aiskpw0': {'x': x},
          'aiskpw3': {'x': x},
          'aisknew': {'y': y},
          'aisknew2': {'y': y},
          'aiskcap': {'y': y, 'yb': yb},
          'aiskblkn': {'y': y},
          'aiskblkf': {'y': y},
          'aiskblkr': {'y': y},
          'aiskoff': {'y': y},
          'aiskcu': {'yc': yc, 'ycm': ycm},
          'aiskcs': {'yc': yc, 'ycm': ycm},
          'aiskcu3': {'ycm': ycm},
          'aiskpt': {'pt': pt},
          'aiskpti': {'pt': pt},
          'aiskmt': {'mt': mt},
          'aiskmto': {'mt': mt},
          'aiskmt0': {'mt': mt},
          'aiskmt03': {'mt': mt},
          'aiskmt2': {'mt': mt},
          'aiskmt20': {'mt': mt},
          'aiskmt14': {'mt': mt},
          'aiskmt16': {'mt': mt},
          'aiskmt15': {'mt': mt},
          'aiskmt40': {'mt': mt},
          'aiskmt99': {'mt': mt},
          'aiskmtc': {'mt': mt},
          'aiskmtt': {'mt': mt},
          'aiskmtk': {'mt': mt},
          'aiskmtl': {'mt': mt},
          'aiskrand': {'s': s},
          'aiskdiff': {'s': s},
          'aiskvinf': {'z': z, 't': t},
          'aiskvveh': {'z': z, 't': t},
          'aiskad': {'a': a},
          'aiskfon': {'fm': fm},
          'aiskfof': {'fm': fm}}
