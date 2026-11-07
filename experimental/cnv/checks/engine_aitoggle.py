"""Engine probe: when the AI's micro manager raises / lowers the Peacekeepers' riot shield (missions/aitoggle_bench.py).

s1's StaticDefense team is two Peacekeepers; a player Twinblade attacks Peacekeeper 1 from ATTACK_AT (20 s) and is
deleted at STOP_AT (35 s). Shield up = ObjectStatus GENERIC_TOGGLE_STATE. Both Peacekeepers kept at full health.
Checks: r (both builds) and c (aitogglemade: the control, the script presses Peacekeeper 2's toggle PRESS_AT frames
after the attack starts, to show the status reads a raised shield).
Counters (four lines), from the attack on (run to STOP_AT + 15 s):
  帧数   frames since the attack order (the order frame is +-1)
  盾1开  frames since Peacekeeper 1 was first seen shielded   -> raised at frame = 帧数 - 盾1开
  盾1关  frames since Peacekeeper 1 was seen unshielded after that -> lowered at frame = 帧数 - 盾1关
         (the stop is at frame (STOP_AT - ATTACK_AT) * 15 = 225)
  盾2    frames since Peacekeeper 2 (never targeted) was first seen shielded
  在家   aitogglehunt only, in 盾2's place: how many of s1's Peacekeepers stand within 150 of their spots (2 = the
         Hunt team never took them; it walks off with them)
A shield seen before the attack makes 盾k > 帧数.
The verdicts after 帧数 are the model's answer (RA3-EngineModel micro.py toggle, UpdateTime 0.5 s): 盾1 raised within
the attack, lowered after the stop, 盾2 never -- a FAIL is the bench reading otherwise.

读数
Bench 2026-11-07 (Sonnet, one run each, no dropout):
  aitogglemade c PASS: 盾2 463 at 帧数 493 -> raised 30 frames after the order, the frame of the press: the status
    reads a raised shield.
  aitogglemade r / aitogglehand r FAIL: 盾1开 盾1关 盾2 all 0 through 帧数 426 / 495 -- the AI never raised the
    shield of the attacked Peacekeeper (made after the wake or handed over alike). With aimicmade (warriors made
    after the wake never charged) the silence is not the hand-over: INFERRED the StaticDefense team runs no micro,
    or a precondition (work/re l4_micro_powers.md 1) fails. Model: raises at the first round (strict xfail in
    RA3-EngineModel tests/test_ai_bench.py).
  aitogglehunt r FAIL (Sonnet, round 18): 盾1开 盾1关 盾2 all 0 through 帧数 493 -- a Targetless Hunt team never raised
    the shield either: not the StaticDefense tactic.
  aitogglehunt r again with 在家 (Sonnet, round 18): 在家 2 from s11 to s51 -- the Peacekeepers never left their spots:
    the Hunt team never took them (aistate aihunt: Peacekeepers s1's from the start left 4 s after the wake). So the
    units the script creates on s1's team after the wake are not recruited; the micro manager never had them.
  aitogglexfer r FAIL (Sonnet, round 18): 盾1开 盾1关 盾2 all 0 through 帧数 489 -- UNIT_AI_TRANSFER_ALL again right
    after the make did not help either (see engine_aimicro: next, the AI produces the units itself).
  aitogglebuilt r (Sonnet, round 19; counters 帧数 造出 盾 曾盾): first run (attack 30 s) the Allied barracks gave the
    second Peacekeeper only at ~s51, after the attack -- moved to attack 70 / stop 85. Rerun: 造出 2 from s21, the
    gunship's attack 70-85 s: 盾 / 曾盾 0 throughout; the control (named Peacekeeper made on s1's team 5 s after the
    stop, toggle pressed 1 s later): 盾 1, 曾盾 8 at s91 -- the by-player count reads a shield. NOT conclusive: 造出 stayed
    2 through 15 s of a Twinblade "attacking" them, so it most likely never shot at them (attack-move to the deleted
    barracks' spot; where the AI put them is not known). A fair try needs the gunship ordered at them (they are
    unnamed: a team hunt, or a player-area attack) -- the warriors' aimicbuilt reading is the firm one.
  aitogglebltf r (B, round 20, mod CampAITogBltFR; a Targetless Hunt team, s1's structures deleted once it owns two),
    three gunship placements, all NOT conclusive: (1) TEAM_HUNT at s70: 造出 2 throughout, never hit; (2) attack-move
    to the barracks spot the moment s1 owned two (s21): both dead by s41, 曾盾 0 -- but most likely before the Hunt
    team took them (the warriors were taken 10-20 s after being built); (3) TEAM_HUNT from the barracks spot 12 s
    after two owned: 造出 2 throughout, never hit. The control read each time (盾 1 at s91). Not followed further (the
    layer 4 closing line); engine_aimicro aimicbuiltf is the firm answer for AI-built units.
"""
from parts import NOT, Script, Test, counted, square, status

LAG = 4.0
HOME, HOME_R = 'CNV AT Home Area', 150.0   # aitogglehunt: the square of half-side 150 round the two spots
AFTER = 15.0
SHIELD = 'GENERIC_TOGGLE_STATE'
COMMAND = 'Command_ToggleRiotShieldSpecialPower'
PRESS_AT = 30      # control c: frames after the attack order at which the script presses Peacekeeper 2's toggle


def names(m, group):
    made = getattr(m, 'cnv_named', {})
    return [r.name for r in m.roles(group)] or [made[k] for k in sorted(made) if k.startswith(group + ' ')]


def probe(m, press=False):
    t = Test()
    p1 = m.player('p1')
    attack, stop = m.facts['attack at'], m.facts['stop at']
    pks = names(m, 'peacekeeper')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
    t.scripts.append(Script('Test - keep them up', [], [('UNIT_SET_HEALTH', n, 100.0) for n in pks], once=False))
    hunt = bool(m.facts.get('hunt'))
    t.counters += [('CNV_AT_Frames', '帧数'), ('CNV_AT_Up1', '盾1开'), ('CNV_AT_Down1', '盾1关')]
    if hunt:   # 盾2 gives way to 在家: did the Hunt team take the Peacekeepers (they walk off) or not (they stand)
        (x1, y1), (x2, y2) = m.point('peacekeeper 1 spot'), m.point('peacekeeper 2 spot')
        t.areas[HOME] = square((x1 + x2) / 2, (y1 + y2) / 2, HOME_R)
        counted('CNV_AT_Home', '在家', t, template=m.cnv_units[0], area=HOME, player=m.player('s1'))
    else:
        t.counters.append(('CNV_AT_Up2', '盾2'))
    t.scripts += [Script('Test - frames', [('TIMER_EXPIRED', 'CNV AT Attack')],
                         [('INCREMENT_COUNTER', 1, 'CNV_AT_Frames')], once=False)]
    for k, n in enumerate(pks if not hunt else pks[:1], 1):
        t.scripts += [
            Script(f'Test - up seen {k}', [('UNIT_HAS_OBJECT_STATUS', n, status(SHIELD))], [('SET_FLAG', f'Test Up {k}', 1)]),
            Script(f'Test - up count {k}', [('FLAG', f'Test Up {k}', 1)],
                   [('INCREMENT_COUNTER', 1, f'CNV_AT_Up{k}')], once=False)]
    t.scripts += [
        Script('Test - down seen 1', [('FLAG', 'Test Up 1', 1), ('UNIT_HAS_OBJECT_STATUS', pks[0], status(SHIELD), NOT)],
               [('SET_FLAG', 'Test Down 1', 1)]),
        Script('Test - down count 1', [('FLAG', 'Test Down 1', 1)], [('INCREMENT_COUNTER', 1, 'CNV_AT_Down1')],
               once=False)]
    if press:
        t.scripts.append(Script('Test - press 2', [('COUNTER', 'CNV_AT_Frames', 2, PRESS_AT)],
                                [('NAMED_USE_COMMANDBUTTON_ABILITY', pks[1], COMMAND)]))
    t.expect += [('帧数', attack + LAG, 'ever>=', 1)]
    if press:
        t.expect += [('盾2', attack + LAG, 'ever>=', 1)]
    else:
        t.expect += [('盾1开', attack + LAG, 'ever>=', 1, stop), ('盾1关', stop + LAG, 'ever>=', 1)]
        t.expect += [] if hunt else [('盾2', attack + LAG, '==', 0)]
    t.bench = [('bench_watch', dict(seconds=stop + AFTER, every=10, sheet=False, lines=len(t.counters)))]
    return t


CONTROL = 'UNIT - CNV AT Control'
CTRL_AFTER = 5.0   # built: seconds after the stop at which the check makes a named Peacekeeper on s1's team


def probe_built(m):
    """aitogglebuilt (round 19): the AI's own Peacekeepers are unnamed, so count by player. Counters from the attack:
      帧数  frames since the attack order
      造出  Peacekeepers s1 owns (the opener built them: >= 2 before the attack)
      盾    s1's objects with the shield up now (GENERIC_TOGGLE_STATE)
      曾盾  frames since s1 first had one up -> first raised at frame 帧数 - 曾盾 (> 帧数: before the attack)
    The model raises one within the attack and lowers it after the stop (盾 back to 0). Control: CTRL_AFTER after the
    stop the check makes a named Peacekeeper on s1's team at the control spot and presses its toggle one second later
    -- 盾 must read it."""
    t = Test()
    p1, s1 = m.player('p1'), m.player('s1')
    attack, stop = m.facts['attack at'], m.facts['stop at']
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
    t.counters.append(('CNV_AT_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [('TIMER_EXPIRED', 'CNV AT Attack')],
                            [('INCREMENT_COUNTER', 1, 'CNV_AT_Frames')], once=False))
    counted('CNV_AT_Owned', '造出', t, template=m.cnv_units[0], player=s1)
    counted('CNV_AT_Up', '盾', t, status=status(SHIELD), player=s1)
    t.counters.append(('CNV_AT_Ever', '曾盾'))
    t.scripts += [
        Script('Test - up seen any', [('PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', s1, 3, 1, status(SHIELD))],
               [('SET_FLAG', 'Test Up Any', 1)]),
        Script('Test - up count any', [('FLAG', 'Test Up Any', 1)], [('INCREMENT_COUNTER', 1, 'CNV_AT_Ever')],
               once=False)]
    ctrl = int((stop - attack + CTRL_AFTER) * 15)
    t.scripts += [
        Script('Test - control make', [('COUNTER', 'CNV_AT_Frames', 2, ctrl)],
               [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', CONTROL, m.cnv_units[0], m.team('s1'), m.mark('control spot'))]),
        Script('Test - control press', [('COUNTER', 'CNV_AT_Frames', 2, ctrl + 15)],
               [('NAMED_USE_COMMANDBUTTON_ABILITY', CONTROL, COMMAND)])]
    t.expect += [('帧数', attack + LAG, 'ever>=', 1), ('造出', attack, 'ever>=', 2, stop),
                 ('曾盾', attack + LAG, 'ever>=', 1, stop), ('盾', stop + LAG, '==', 0, stop + CTRL_AFTER),
                 ('盾', stop + CTRL_AFTER + 2, 'ever>=', 1)]
    t.bench = [('bench_watch', dict(seconds=stop + CTRL_AFTER + AFTER, every=10, sheet=False,
                                    lines=len(t.counters)))]
    return t


CHECKS = {'aitogglebuilt': {'r': probe_built}, 'aitogglebltf': {'r': probe_built},
          'aitogglehand': {'r': probe}, 'aitogglemade': {'r': probe, 'c': lambda m: probe(m, press=True)},
          'aitogglehunt': {'r': probe}, 'aitogglexfer': {'r': probe}}
