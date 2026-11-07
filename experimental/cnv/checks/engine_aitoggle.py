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
"""
from parts import NOT, Script, Test, status

LAG = 4.0
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
    t.counters += [('CNV_AT_Frames', '帧数'), ('CNV_AT_Up1', '盾1开'), ('CNV_AT_Down1', '盾1关'), ('CNV_AT_Up2', '盾2')]
    t.scripts += [Script('Test - frames', [('TIMER_EXPIRED', 'CNV AT Attack')],
                         [('INCREMENT_COUNTER', 1, 'CNV_AT_Frames')], once=False)]
    for k, n in enumerate(pks, 1):
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
        t.expect += [('盾1开', attack + LAG, 'ever>=', 1, stop), ('盾1关', stop + LAG, 'ever>=', 1),
                     ('盾2', attack + LAG, '==', 0)]
    t.bench = [('bench_watch', dict(seconds=stop + AFTER, every=10, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {'aitogglehand': {'r': probe}, 'aitogglemade': {'r': probe, 'c': lambda m: probe(m, press=True)}}
