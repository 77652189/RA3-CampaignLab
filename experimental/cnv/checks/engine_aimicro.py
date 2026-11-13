"""Engine probe: when the AI's micro manager fires the Imperial Warriors' Bonzai charge (missions/aimicro_bench.py).

s1's StaticDefense team is the two warriors; an unarmed player engineer stands D west of each (90 or 140), kept at
full health every frame. The charge is read as the warrior's ObjectStatus WEAPON_UPGRADED_02 (10 s; reload 30 s).
One check per build, r (aimicnear also c: the control, the script presses warrior 2's charge at frame PRESS_AT):
  aimicnear (D 90, HARD)   aimicmed (D 90, MEDIUM)   aimicfar (D 140, HARD)   aimichurt (D 140, HARD, health 70 %)
  aimicmade (D 90, HARD, the warriors created on s1's team by script 1 s after the wake)
The verdicts after 帧数 are the model's answer (FIRES): 冲1 / 冲2 ever >= 1 where it charges, == 0 throughout where it
does not -- a FAIL there is the bench reading otherwise, the charge count readable without the rows.
Counters (four lines), from the wake on (run 60 s after it):
  帧数   frames since the wake (the wake frame is +-1)
  冲1    frames since warrior 1 was first seen charging  -> charged at frame = 帧数 - 冲1
  冲2    the same for warrior 2
  再冲1  frames since warrior 1 was seen charging again, once 冲1 >= 200 (the first charge ends at 150)
Before the wake: a charge seen before the wake makes 冲k > 帧数.

读数
Bench 2026-11-06 (one run each; charged at = 帧数 - 冲k at the last row):
  aimicpre r (first design: the warriors s1's from the start, as aimicnear but no hand-over; run as CampAIMicNearR):
    冲1 冲2 再冲1 all 0 through 帧数 947 -- never charged, though the engineer stood 90 away in gun range. Read
    afterwards: a unit's AI powers are registered only when it is made / changes hands with the AI brain awake.
Bench 2026-11-07 (Sonnet, one run each, no dropout):
  aimicnear c: 冲2 counting from about frame 300 (100 at s51, 404 at s71 of 帧数 704) -- the scripted press is seen,
    so the status reads a charge.
  aimicnear r / aimicmed r / aimicfar r / aimichurt r: 冲1 冲2 再冲1 all 0 through 帧数 949 / 940 / 948 / 933 --
    nobody charged, the hand-over 1 s after the wake did not help. The model fires in near / med / hurt (strict xfail
    in RA3-EngineModel tests/test_ai_bench.py); far agrees. Not known yet why: the hand-over not registering either,
    the StaticDefense team not taking handed-over units, or one of the 6 preconditions (l4_micro_powers.md 1).
  aimicmade r (Sonnet): 冲1 冲2 再冲1 all 0 through 帧数 939 -- warriors created on s1's team after the wake did not
    charge either: not the hand-over. Same in engine_aitoggle (no shield). INFERRED: StaticDefense runs no micro.
  aimichunt r (Sonnet, round 18): 冲1 冲2 再冲1 all 0 through 帧数 943 -- a Targetless Hunt team did not charge either:
    not the tactic. Left: the units never joined the team, or a gate of the power-use routine (work/re/l4_specials.md) / the power registration.
    (engine_aitoggle aitogglehunt: the Hunt team never took the script-made units -- they stood at their spots.)
  aimicxfer r / aimicnearx r (Sonnet, round 18): 冲1 冲2 再冲1 all 0 through 帧数 951 / 943 -- UNIT_AI_TRANSFER_ALL
    run again right after the make / hand-over did not help. Program (work/re l4_micro_gate.md): the recruiter
    refuses a unit whose team's recruitable flag is 0 (teamSoviet_1; only defaultSkirmishTeam is 1), the powers live in the
    unit's own team's library -- so (INFERRED) aimicpre (placed s1's, recruited at the wake, powers never registered: made
    with the AI asleep) and the made / handed-over builds (registered, never recruited) each miss one half.
    Next: the AI produces the warriors itself.
  aimicbuilt r (Sonnet, round 19; counters 帧数 造出 冲 曾冲): the opener built both warriors by s21 (造出 2), the
    conscripts walked in and both warriors were dead by s41 (造出 0) -- 曾冲 0 throughout, the AI's own warriors never
    charged though hurt and fighting infantry. The control (named warrior made on s1's team at wake + 45 s, button
    pressed 1 s later): 冲 1 at s61, 曾冲 100 -- the by-player status count reads a charge. So not the hand-over, the
    tactic, or the team the unit was made on: even units the AI builds do not charge (whether they were recruited at
    all: aimicbuilth).
  aimicbuilth r PASS (Sonnet, round 19, mod CampAIMicBltHR; counters 帧数 造出 在家 曾冲): 造出 2 from s21, 在家 2 -> 1
    @ s31 -> 0 @ s41 -- the Targetless Hunt team took the AI-built warriors and walked them off: AI-built units ARE
    recruited (unlike the script-made ones). So the aimicbuilt silence is past recruitment: the power entry check
    (the tactic's power-use routine / the heuristic's virtual method, work/re/l4_specials.md) or the power registration, not the team.
  aimicbuiltf r PASS (B, round 20, mod CampAIMicBltFR; counters 帧数 造出 冲 曾冲): 造出 2 from s21; 冲 2 @ s41,
    曾冲 145 @ 帧数 499 -> first charge at frame ~354 after the wake; the control read at s61. AI-built warriors that a
    Hunt team took, hurt by conscripts, DO charge. Read (work/re l4_micro_gate.md 7): a team change carries the
    unit's power entries along (the team-building routines, work/re/l4_specials.md), so the aimicbuilt silence is the StaticDefense team
    (not taking them, or not running the round there) -- not followed (the layer 4 closing line).
  aimicspon / aimicspoff r PASS both (B, round 113, 2026-11-10; mods CampAIMicSpOnR / CampAIMicSpOffR): aimicbuiltf
    on this probe's own micro manager (StandardMicroManager flattened, missions/aimicro_bench.py _spow_xml), only
    UseSpecialPowers differing. On: 造出 2 from s21, 冲 2 @ s41, 曾冲 127 @ 帧数 489 (first charge ~362 frames after
    the wake), the warriors alive to the end (造出 3 from s61). Off: 造出 2 s21-s41 -> 0 @ s51 (both died fighting),
    曾冲 0 until the control (冲 1 @ s61, 曾冲 108) -- a scripted press still fires. UseSpecialPowers false = the micro
    manager never uses a unit power (the model: no round, work/re/l4_specials.md). The simulator (simai) fires in neither: its Hunt
    team walks the two warriors west from s21, before the conscripts set out, so they never fight (work/logs
    b113_sim3.log) -- and its micro block reads only the retail micro library (a probe's own AIMicroManagerData
    reaches only 'tactics micro', simai.own_personalities).
    Simulator since B round 114 (tests/test_simai.py): the probe's micro data reaches the micro block, and state 2's
    per-member pick (EngageHostileTargets; tactics._assign) turns the Hunt team on the conscripts from ~s28 -- on:
    the micro wants the charge from 275 frames after the wake (bench ~362), off: never. The charge itself is not
    applied in the simulator (recorded only), so its warriors still lose the fight.
  aimicengoff r FAIL against the prediction (B, round 115, 2026-11-10; mod CampAIMicEgOffR): aimicspon with only
    EngageHostileTargets="false". Predicted: the Hunt team walks on, never fights, no charge. Bench: 造出 2 from
    s21, 曾冲 75 @ 帧数 333 -> first charge ~258 frames after the wake (on: ~362), the warriors alive to the end (造出 3
    from s61). w (where; 在家 in place of 冲): aimicengoff 在家 2 at s21-s41, 0 @ s51, 曾冲 81 @ 帧数 339; aimicspon w
    PASS the same way (在家 2 s21-s41, 0 @ s51, 曾冲 130 @ 帧数 492). So on the bench the Hunt team does not walk
    its warriors off before the conscripts arrive (they fight at home, on or off) and EngageHostileTargets off does
    not keep them out of the fight or the charge -- the fight is not the micro manager's engage pick.
"""
from parts import Script, Test, counted, square, status

LAG = 4.0
RUN = 60.0
CHARGE = 'WEAPON_UPGRADED_02'


COMMAND = 'Command_JapanAntiInfantryInfantryBonzai'
PRESS_AT = 300     # control c: frames after the wake at which the script presses warrior 2's charge


def names(m, group):
    """A group's unit names in order: the cast's roles, or (units the mission's scripts create) m.cnv_named."""
    made = getattr(m, 'cnv_named', {})
    return [r.name for r in m.roles(group)] or [made[k] for k in sorted(made) if k.startswith(group + ' ')]


# what the model (RA3-EngineModel ra3model/ai/micro.py) expects of each build: does each warrior charge within the run
FIRES = {'aimicpre': False, 'aimicnear': True, 'aimicmed': True, 'aimicfar': False, 'aimichurt': True,
         'aimicmade': True, 'aimichunt': True, 'aimicxfer': True, 'aimicnearx': True, 'aimicbuilt': True,
         'aimicbuilth': False, 'aimicbuiltf': True,
         'aimicspon': True, 'aimicspoff': False,
         'aimicengoff': True}   # round 115: aimicspon, EngageHostileTargets off -- predicted False, the bench charges
         # round 113 (aimicspon / aimicspoff): aimicbuiltf on this probe's micro manager, UseSpecialPowers on / off; builth: the Hunt walks them off to no infantry -- nothing to charge at
HOME, HOME_R = 'CNV AM Home Area', 400.0   # aimicbuilth: round the barracks (the units come out within it)


def probe(m, press=False, build=''):
    t = Test()
    p1 = m.player('p1')
    wake = m.facts['wake at']
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
    t.scripts.append(Script('Test - keep the engineers up', [],
                            [('UNIT_SET_HEALTH', r.name, 100.0) for r in m.roles('engineer')], once=False))
    t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AM_Tick')], once=False),
                  Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AM_Tick', 3, 30)],
                         [('SET_FLAG', 'Test Woke', 1)])]
    t.counters += [('CNV_AM_Frames', '帧数'), ('CNV_AM_Rush1', '冲1'), ('CNV_AM_Rush2', '冲2'),
                   ('CNV_AM_Again1', '再冲1')]
    t.scripts.append(Script('Test - frames', [('FLAG', 'Test Woke', 1)], [('INCREMENT_COUNTER', 1, 'CNV_AM_Frames')],
                            once=False))
    warriors = names(m, 'warrior')
    for k, w in enumerate(warriors, 1):
        on = ('UNIT_HAS_OBJECT_STATUS', w, status(CHARGE))
        t.scripts += [
            Script(f'Test - rush seen {k}', [on], [('SET_FLAG', f'Test Rush {k}', 1)]),
            Script(f'Test - rush count {k}', [('FLAG', f'Test Rush {k}', 1)],
                   [('INCREMENT_COUNTER', 1, f'CNV_AM_Rush{k}')], once=False)]
    if press:
        t.scripts.append(Script('Test - press 2', [('FLAG', 'Test Woke', 1), ('COUNTER', 'CNV_AM_Frames', 2, PRESS_AT)],
                                [('NAMED_USE_COMMANDBUTTON_ABILITY', warriors[1], COMMAND)]))
    w1 = warriors[0]
    t.scripts += [
        Script('Test - again seen 1', [('UNIT_HAS_OBJECT_STATUS', w1, status(CHARGE)),
                                       ('COUNTER', 'CNV_AM_Rush1', 3, 200)], [('SET_FLAG', 'Test Again 1', 1)]),
        Script('Test - again count 1', [('FLAG', 'Test Again 1', 1)], [('INCREMENT_COUNTER', 1, 'CNV_AM_Again1')],
               once=False)]
    t.expect += [('帧数', wake + LAG, 'ever>=', 1, wake + RUN)]
    # did they charge (the model's answer; FAIL = the bench reads otherwise): 冲k > 0 once warrior k was seen charging
    if press:
        t.expect += [('冲2', wake + LAG, 'ever>=', 1)]
    elif build in FIRES:
        t.expect += [(f'冲{k}', wake + LAG, 'ever>=' if FIRES[build] else '==', 1 if FIRES[build] else 0)
                     for k in (1, 2)]
    t.bench = [('bench_watch', dict(seconds=wake + RUN + LAG, every=10, sheet=False, lines=len(t.counters)))]
    return t


CTRL_S = 45.0      # built: seconds after the wake at which the check makes a named warrior on s1's team (the control)
CONTROL = 'UNIT - CNV AM Control'


def probe_built(m, build='aimicbuilt', where=False):
    """aimicbuilt (round 19): the AI's own warriors are unnamed, so count by player. Counters from the wake:
      帧数  frames since the wake
      造出  warriors s1 owns (the opener built them: >= 2)
      冲    s1's objects charging now (WEAPON_UPGRADED_02)
      曾冲  frames since s1 first had one charging -> first charge at frame 帧数 - 曾冲
    Control: CTRL_S after the wake the check makes a named warrior on s1's team at the control spot and presses its
    charge one second later -- 冲 must read it (the by-player count sees the status), and 曾冲 starting only then
    means the AI's own never charged. where (check w, round 115): 冲 gives way to 在家 (as aimicbuilth) and only
    曾冲 is judged -- did the Hunt team walk its warriors off before the fight."""
    t = Test()
    p1, s1 = m.player('p1'), m.player('s1')
    wake = m.facts['wake at']
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
    t.scripts.append(Script('Test - keep the conscripts up', [],
                            [('UNIT_SET_HEALTH', r.name, 100.0) for r in m.roles('conscript')], once=False))
    t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AM_Tick')], once=False),
                  Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AM_Tick', 3, 30)],
                         [('SET_FLAG', 'Test Woke', 1)])]
    t.counters.append(('CNV_AM_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [('FLAG', 'Test Woke', 1)], [('INCREMENT_COUNTER', 1, 'CNV_AM_Frames')],
                            once=False))
    counted('CNV_AM_Owned', '造出', t, template=m.cnv_units[0], player=s1)
    hunt = bool(m.facts.get('hunt')) and not m.facts.get('foes')
    if hunt or where:   # aimicbuilth: 冲 gives way to 在家 -- s1's warriors within HOME_R of the barracks (left = recruited)
        x, y = m.point('factory spot')
        t.areas[HOME] = square(x, y, HOME_R)
        counted('CNV_AM_Home', '在家', t, template=m.cnv_units[0], area=HOME, player=s1)
    else:
        counted('CNV_AM_Rush', '冲', t, status=status(CHARGE), player=s1)
    t.counters.append(('CNV_AM_Ever', '曾冲'))
    t.scripts += [
        Script('Test - rush seen any', [('PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', s1, 3, 1, status(CHARGE))],
               [('SET_FLAG', 'Test Rush Any', 1)]),
        Script('Test - rush count any', [('FLAG', 'Test Rush Any', 1)], [('INCREMENT_COUNTER', 1, 'CNV_AM_Ever')],
               once=False)]
    ctrl = int(CTRL_S * 15)
    t.scripts += [
        Script('Test - control make', [('FLAG', 'Test Woke', 1), ('COUNTER', 'CNV_AM_Frames', 2, ctrl)],
               [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', CONTROL, m.cnv_units[0], m.team('s1'), m.mark('control spot'))]),
        Script('Test - control press', [('FLAG', 'Test Woke', 1), ('COUNTER', 'CNV_AM_Frames', 2, ctrl + 15)],
               [('NAMED_USE_COMMANDBUTTON_ABILITY', CONTROL, COMMAND)])]
    fires = FIRES[build]
    t.expect += [('帧数', wake + LAG, 'ever>=', 1, wake + RUN), ('造出', wake + LAG, 'ever>=', 2, wake + CTRL_S),
                 ('曾冲', wake + LAG, 'ever>=' if fires else '==', 1 if fires else 0, wake + CTRL_S)]
    # hunt: the model recruits the built warriors -- they leave (在家 0 while 造出 is 2); else the control's charge
    t.expect += ([] if where else [('在家', wake + LAG, 'ever==', 0, wake + CTRL_S)] if hunt
                 else [('冲', wake + CTRL_S + 2, 'ever>=', 1)])
    t.bench = [('bench_watch', dict(seconds=wake + RUN + LAG, every=10, sheet=False, lines=len(t.counters)))]
    return t


def probe_update_time(m):
    """Latch the first AI charge on the script clock, with live-unit controls.

    There is no scripted power press in this check. A positive first charge
    proves the AI-built units entered a functioning micro/power path. This does
    not expose team identity or the internal dispatch frame. Only the micro
    UpdateTime differs between builds; no Tactic.UpdateTime is changed.

    MEASURED aimicupfast:a / aimicupslow:a: first latch 363 / 317, alive 2
    in both (three checks PASS each). Model latch 271 / 309: precise replay
    remains strict xfail. Eligibility/update phase unresolved; see
    work/re/c_update_time_report.md. Longer period is not a fixed delay.
    """
    t = probe_built(m, 'aimicspon')
    t.scripts = [s for s in t.scripts if not s.name.startswith('Test - control')]
    t.counters = [('CNV_AM_Frames', '帧数'), ('CNV_AM_Owned', '造出'),
                  ('CNV_UP_First', '首冲帧'), ('CNV_UP_Alive', '首活')]
    t.scripts.append(Script('Test - latch first charge',
                            [('PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', m.player('s1'), 3, 1, status(CHARGE))],
                            [('SET_COUNTER_TO_COUNTER', 'CNV_UP_First', 'CNV_AM_Frames'),
                             ('SET_COUNTER_TO_COUNTER', 'CNV_UP_Alive', 'CNV_AM_Owned')]))
    t.expect = [('造出', 14, 'ever>=', 2, 45), ('首冲帧', 14, 'ever>=', 1, 55),
                ('首活', 14, 'ever>=', 2, 55)]
    t.bench = [('bench_watch', dict(seconds=56, every=5, sheet=False, lines=4))]
    return t


CHECKS = {b: {'r': lambda m, b=b: probe(m, build=b)} for b in FIRES if not b.startswith(('aimicbuilt', 'aimicsp'))}
CHECKS['aimicupfast'] = {'a': probe_update_time}
CHECKS['aimicupslow'] = {'a': probe_update_time}
CHECKS['aimicupft'] = {'a': probe_update_time}
CHECKS['aimicupst'] = {'a': probe_update_time}
CHECKS['aimicbuilt'] = {'r': probe_built}
CHECKS['aimicbuilth'] = {'r': lambda m: probe_built(m, 'aimicbuilth')}
CHECKS['aimicbuiltf'] = {'r': lambda m: probe_built(m, 'aimicbuiltf')}
CHECKS['aimicspon'] = {'r': lambda m: probe_built(m, 'aimicspon')}
CHECKS['aimicspoff'] = {'r': lambda m: probe_built(m, 'aimicspoff')}
CHECKS['aimicengoff'] = {'r': lambda m: probe_built(m, 'aimicengoff'),
                         'w': lambda m: probe_built(m, 'aimicengoff', where=True)}
CHECKS['aimicspon']['w'] = lambda m: probe_built(m, 'aimicspon', where=True)
CHECKS['aimicnear']['c'] = lambda m: probe(m, press=True)


def probe_engage_clock(m):
    """No scripted charge: latch first AI power and the live warrior count.

    First charge is a measurement, not an invented prediction threshold. Both
    sides must produce two warriors and charge before the 55-second deadline.
    Initial movement replay is tested separately; work/re/e107_engage_clock.md.
    """
    return probe_update_time(m)


CHECKS['aiegon'] = {'a': probe_engage_clock}
CHECKS['aiegoff'] = {'a': probe_engage_clock}
