"""Retail-campaign actions, batch 4 (round 214; the gaps of `inventory_retail.py --part 脚本动作`): powers, the context
attack, buildability. Mission on maps/probe_border.py as checks/engine_acts3.py ('stop row' offsets, enemies on
Soviet_4, nobody fires unless told). What the simulator predicts is in brackets.

  pow   X = SpecialPowerOrbitalRefuse_Rank1, Y = SpecialPower_DesolatorBomb_Level1 (PlayerSpellBook powers, each
          RequiredPlayerTech PlayerTech_Soviet_<..>_Rank1 and RequiredObject SovietConstructionYard). Player_1 and
          Soviet_4 each own a SovietConstructionYard ('syard', 'syard4').
          2 s: PLAYER_GRANT_SPECIAL_POWER(X, Player_1), (X, Soviet_4); PLAYER_SET_SPECIAL_POWER_COUNTDOWN(Player_1, Y, 0)
               (Y not granted yet)
          5 s: COUNTDOWN(Player_1, X, 0)          8 s: GRANT(Y, Player_1)        11 s: NAMED_DELETE syard
          14 s: COUNTDOWN(Soviet_4, X, 0)         17 s: COUNTDOWN(Soviet_4, X, 5)  26 s: COUNTDOWN(Soviet_4, X, 0)
          技能 (every frame) = SKIRMISH_SPECIAL_POWER_READY (P1, X) 1 (P1, Y) 2 (s4, X) 4 + PLAYER_HAS_PLAYER_TECH
            (P1, X's tech) 8 (P1, Y's tech) 16 (s4, X's tech) 32
  ctx   UNIT_CONTEXT_SENSITIVE_ATTACK at 2 s: the player's engineer 'eng' -> Soviet_4's power plant 'cplant'; tank 'ctank'
          -> Soviet_4's plant 'tplant'; tank 'ftank' -> the player's own plant 'fplant'; engineer 'eng2' -> Soviet_4's
          plant 'dplant', which got UNIT_CHANGE_OBJECT_STATUS(SKIRMISH_AI_DO_NOT_TAKE, 1) at 1 s. 'eng0' next to
          Soviet_4's 'cplant0', no order (control).
          旗 (every frame) = NAMED_OWNED_BY_PLAYER(Player_1, ...) cplant 1 cplant0 2 dplant 4 + NAMED_ATTACKED_BY_
            OBJECTTYPE(tplant, tank) 8 (fplant, tank) 16
  bld   the player's barracks bk1 / bk2 / bk3 (Allied, a power plant by them, money 20000 at the start).
          bk1: press the spy (AlliedInfiltrationInfantry, needs Upgrade_AlliedTech2) at 1 s; TECHTREE_MODIFY_
               BUILDABILITY_OBJECT(spy, 1 IGNORE_PREREQUISITES) at 3 s; press again at 4 s.
          bk2: modify(peacekeeper AlliedAntiInfantryInfantry, 2 NO) at 1 s; press at 2 s; modify(peacekeeper, 0 YES) at
               8 s; press at 9 s.
          bk3: modify(dog AlliedScoutInfantry, 3 ONLY_BY_AI) at 1 s; press at 2 s.
          造 (every frame) = PLAYER_HAS_OBJECT_COMPARISON(Player_1, >=, 1, ...) spy 1 peacekeeper 10 dog 100
          钱 = Player_1's money
  [simulator before the bench: no READY (技能 0), the context attack and buildability not modelled (旗 0, 造 100 110
  with the spy never: NO ignored, the spy's prerequisite asked)]
  BENCH 11-13 (round 214, run_queue, CampActsUActs_mcp_1113_215338; tests/test_simbench.py test_acts_u_as_the_bench):
    技能 / 旗 / 造 / 钱  s1 45 0 0 19868 | s2 45 0 0 19728 | s3-s5 45 5 100 ~19300 | s6-s8 63 5 110 | s9-s12 60 5 110 |
    s13-s14 60 5 111 18400 | s15-s19 56 5 111 | s20-s33 60 5 111 18400. The bench's seconds run 1-2 ahead.
    Powers: the grant gives the protocol (8, 32) and the power READY at once (1, 4), no countdown needed; Y's countdown
    0 before its grant did nothing seen, its grant at 8 s ready at once (+2 +16); the yard deleted at 11 s: P1's READY
    both gone (-3), the protocols kept; s4's countdown 5 at 17 s: not ready s15-s19, ready again from s20 -- a positive
    countdown DID come back here (engine_power / engine_aispecial never saw it: a building's power, not chased).
    Context attack: both engineers took their plants (旗 5: DO_NOT_TAKE no bar), the uncommanded one not; the tank on
    the enemy plant 210 off never fired in 30 s (prediction: attack), on its own plant neither.
    Buildability: the dog (ONLY_BY_AI) and the peacekeeper (NO) were built by the script's presses at once; the spy's
    press at 1 s refused (no Upgrade_AlliedTech2), at 4 s after IGNORE_PREREQUISITES built (s13 = 4 + 10 s); money
    1600 = 200 + 2 x 200 + 1000. The player's own button under NO / ONLY_BY_AI not benched (simulator: refused).
"""
from maps import probe_border
from parts import Mission, Script, Test, status
import checks.engine_scripts8 as s8

TANK, PLANT, ENG, CY = 'AlliedAntiVehicleVehicleTech1', 'SovietPowerPlant', 'AlliedEngineer', 'SovietConstructionYard'
BARRACKS, APLANT = 'AlliedBarracks', 'AlliedPowerPlant'
SPY, PK, DOG = 'AlliedInfiltrationInfantry', 'AlliedAntiInfantryInfantry', 'AlliedScoutInfantry'
PRESS = {SPY: 'Command_ConstructAlliedInfiltrationInfantry', PK: 'Command_ConstructAlliedAntiInfantryInfantry',
         DOG: 'Command_ConstructAlliedScoutInfantry'}
X, Y = 'SpecialPowerOrbitalRefuse_Rank1', 'SpecialPower_DesolatorBomb_Level1'
TX, TY = 'PlayerTech_Soviet_OrbitalRefuse_Rank1', 'PlayerTech_Soviet_DesolatorBomb_Rank1'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
RUN = 32.0
YARDS = {'syard': ('p1', (700.0, 4650.0)), 'syard4': ('s4', (1700.0, 4650.0))}
# (who, its template, its side, where) -> (target, its template, its side, where)
PAIRS = {'eng': (ENG, (2050.0, 4000.0), 'cplant', 's4'), 'eng0': (ENG, (2050.0, 4700.0), 'cplant0', 's4'),
         'ctank': (TANK, (2790.0, 4000.0), 'tplant', 's4'), 'ftank': (TANK, (2790.0, 4700.0), 'fplant', 'p1'),
         'eng2': (ENG, (3650.0, 4000.0), 'dplant', 's4')}
BKS = {'bk1': (2600.0, 2700.0), 'bk2': (3100.0, 2700.0), 'bk3': (3600.0, 2700.0), 'bpow': (4100.0, 2700.0)}


def _n(part):
    return f'UNIT - CNV Act4 {part.title()}'


def _unit(m, role, side, template, x, y):
    m.put(template, 'stop row', x - O[0], y - O[1], side=side, angle=0.0 if side == 'p1' else 3.1416,
          name=_n(role), role=role)


def mission():
    m = Mission(name='CampActsU', map=probe_border, units=[], facts={})
    m.spawns |= {TANK, PLANT, ENG, CY, BARRACKS, APLANT, SPY, PK, DOG}
    for role, (side, at) in YARDS.items():
        _unit(m, role, side, CY, *at)
    for who, (template, (x, y), target, side) in PAIRS.items():
        _unit(m, who, 'p1', template, x, y)
        _unit(m, target, side, PLANT, x + (150.0 if template == ENG else 210.0), y)
    for role, at in BKS.items():
        _unit(m, role, 'p1', APLANT if role == 'bpow' else BARRACKS, *at)
    return m


def acts(m):
    t = Test()
    p1, s4 = m.player(), m.player('s4')
    t.scripts.append(Script('Test - Act4 start', [], [('PLAYER_SET_MONEY', p1, 20000)]))
    s8.at(t, 'a1', 1.0, [('UNIT_CHANGE_OBJECT_STATUS', _n('dplant'), status('SKIRMISH_AI_DO_NOT_TAKE'), 1),
                         ('NAMED_USE_COMMANDBUTTON_ABILITY', _n('bk1'), PRESS[SPY]),
                         ('TECHTREE_MODIFY_BUILDABILITY_OBJECT', PK, 2),
                         ('TECHTREE_MODIFY_BUILDABILITY_OBJECT', DOG, 3)])
    s8.at(t, 'a2', 2.0, [('PLAYER_GRANT_SPECIAL_POWER', X, p1), ('PLAYER_GRANT_SPECIAL_POWER', X, s4),
                         ('PLAYER_SET_SPECIAL_POWER_COUNTDOWN', p1, Y, 0),
                         ('UNIT_CONTEXT_SENSITIVE_ATTACK', _n('eng'), _n('cplant')),
                         ('UNIT_CONTEXT_SENSITIVE_ATTACK', _n('ctank'), _n('tplant')),
                         ('UNIT_CONTEXT_SENSITIVE_ATTACK', _n('ftank'), _n('fplant')),
                         ('UNIT_CONTEXT_SENSITIVE_ATTACK', _n('eng2'), _n('dplant')),
                         ('NAMED_USE_COMMANDBUTTON_ABILITY', _n('bk2'), PRESS[PK]),
                         ('NAMED_USE_COMMANDBUTTON_ABILITY', _n('bk3'), PRESS[DOG])])
    s8.at(t, 'a3', 3.0, [('TECHTREE_MODIFY_BUILDABILITY_OBJECT', SPY, 1)])
    s8.at(t, 'a4', 4.0, [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('bk1'), PRESS[SPY])])
    s8.at(t, 'a5', 5.0, [('PLAYER_SET_SPECIAL_POWER_COUNTDOWN', p1, X, 0)])
    s8.at(t, 'a8', 8.0, [('PLAYER_GRANT_SPECIAL_POWER', Y, p1), ('TECHTREE_MODIFY_BUILDABILITY_OBJECT', PK, 0)])
    s8.at(t, 'a9', 9.0, [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('bk2'), PRESS[PK])])
    s8.at(t, 'a11', 11.0, [('NAMED_DELETE', _n('syard'))])
    s8.at(t, 'a14', 14.0, [('PLAYER_SET_SPECIAL_POWER_COUNTDOWN', s4, X, 0)])
    s8.at(t, 'a17', 17.0, [('PLAYER_SET_SPECIAL_POWER_COUNTDOWN', s4, X, 5)])
    s8.at(t, 'a26', 26.0, [('PLAYER_SET_SPECIAL_POWER_COUNTDOWN', s4, X, 0)])
    s8.total(t, 'CNV_Act4_Pow', '技能', [
        (1, ('SKIRMISH_SPECIAL_POWER_READY', p1, X)), (2, ('SKIRMISH_SPECIAL_POWER_READY', p1, Y)),
        (4, ('SKIRMISH_SPECIAL_POWER_READY', s4, X)), (8, ('PLAYER_HAS_PLAYER_TECH', p1, TX)),
        (16, ('PLAYER_HAS_PLAYER_TECH', p1, TY)), (32, ('PLAYER_HAS_PLAYER_TECH', s4, TX))])
    s8.total(t, 'CNV_Act4_Flags', '旗', [
        (1, ('NAMED_OWNED_BY_PLAYER', p1, _n('cplant'))), (2, ('NAMED_OWNED_BY_PLAYER', p1, _n('cplant0'))),
        (4, ('NAMED_OWNED_BY_PLAYER', p1, _n('dplant'))),
        (8, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('tplant'), TANK)),
        (16, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('fplant'), TANK))])
    s8.total(t, 'CNV_Act4_Made', '造', [(w, ('PLAYER_HAS_OBJECT_COMPARISON', p1, 3, 1, u))
                                        for w, u in ((1, SPY), (10, PK), (100, DOG))])
    t.counters.append(('CNV_Act4_M', '钱'))
    t.scripts.append(Script('Test - CNV_Act4_M', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'CNV_Act4_M')], once=False))
    s8.watch(t, RUN)
    return t


MISSION = {'engine_acts_u': mission}
CHECKS = {'engine_acts_u': {'acts': acts}}
