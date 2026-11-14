"""Retail-campaign actions, batch 1 (round 211; the gaps of `inventory_retail.py --part 脚本动作`, the program read in
work/re/d115_script_semantics.md 10, 11, 13, 18-20, 23). Mission on maps/probe_border.py (level ground, every place
absolute, as checks/engine_conds.py); enemy crews on Soviet_4 (a crew on Soviet_1 / 2 / 3 has nobody). Each act on a
slot of its own (SLOT: clear of probe_range's lanes and start, 800 apart -- beyond a Guardian's sight -- the pair's
second 150 east). What the simulator predicts is in brackets.

  flow    money: Player_1 and Soviet_5 made allies both ways at the start, both sharing (PLAYER_TOGGLE_RESOURCE_SHARING
          1), all money 0; PLAYER_GIVE_MONEY(Player_1, 1001) at 3 s, (Soviet_5, 1000) at 6 s; Soviet_5 stops sharing at
          9 s; (Player_1, 1000) at 12 s.
          reveal: Soviet_4's 'hide' and 'hide 2' far from every unit of the player's; SHROUD_REVEAL_TO_ALL on 'hide'
          at SWITCH_AT.
          no-AI: the player's 'bait' (SKIRMISH_AI_DO_NOT_ATTACK at the start) and 'bait 2' (without), both NO_ATTACK,
          each 150 from an idle Soviet_4 Guardian of its own.
          autoacquire: the player's crews Sieger and Idler (a Guardian each) 150 from a Soviet_4 power plant each;
          TEAM_ALLOW_AI_AUTOACQUIRE(Sieger, 1) at SWITCH_AT.
          force: the player's 'gunner' and 'friend' (NO_ATTACK) 150 apart; NAMED_ATTACK_NAMED(gunner, friend) at 2 s,
          NAMED_FORCE_ATTACK_NAMED(gunner, friend) at 8 s.
          disable: the player's crew Stuck (one Guardian): NAMED_SET_DISABLED(stuck, EMP, 1) at the start, a move into
          the area SA (300 east) at 2 s, NAMED_SET_DISABLED(stuck, EMP, 0) at 8 s.
          stance: the player's crews Calm / Calm2 / Calm3 (a Guardian each) 150 from Soviet_4's 'mark 1 / 2 / 3'
          (NO_ATTACK): Calm TEAM_SET_STANCE 3 (HOLD_FIRE) at the start, 0 at 12 s; Calm2 nothing; Calm3 the same by
          UNIT_SET_STANCE (benched in round 1xx, docs/engine/stance.md).
          甲钱 / 乙钱 = Player_1's / Soviet_5's money; 友血 = friend's health %
          旗 (every frame) = 1 TEAM_DISCOVERED(Player_1, Hide) 2 NAMED_ATTACKED_BY_OBJECTTYPE(bait, Guardian)
            4 (bait 2, Guardian) 8 (plant 1, Guardian) 16 (plant 2, Guardian) 32 TEAM_INSIDE_AREA_PARTIALLY(Stuck, SA, 0)
            64 NAMED_ATTACKED_BY_OBJECTTYPE(mark 1, Guardian) 128 (mark 2, ...) 256 (mark 3, ...)
            512 TEAM_DISCOVERED(Player_1, Hide2)
          [simulator before this round: 旗 134 from s1 (the hunters' and Calm2's fire), 142 from s7 (plant 1 after the
          switch, INFERRED: the switch lets a structure be taken too), 174 s11 (Stuck in), 494 s13 (Calm, Calm3 fire
          after stance 0), 360 s16 / 40 s28 (the NO_ATTACK ones dead); 友血 falling from s3 (the plain attack fires on
          its own side); money 1001 / 1000 / 2001 (GIVE_MONEY not shared, INFERRED); hide never discovered (d115 18:
          the bit only redraws)]
  BENCH 11-13 (round 211, run_queue; tests/test_simbench.py test_acts_flow_as_the_bench): 甲钱 / 乙钱 / 友血 / 旗
    s1-s4 1001 0 100 134 | s5-s6 1001 1000 100 143 | s7-s8 1001 1000 86 143 | s9 1001 1000 72 175 | s10 2001 1000 72
    175 | s11-s12 2001 1000 58 495 | s13 .. s24 falling to 3 (friend dead, its counter kept), 361 from s14 | s25-s31 41.
    The bench's seconds run 1-2 s ahead of the scripts' timers. Against the prediction: SHROUD_REVEAL_TO_ALL makes the
    far 'hide' discovered by the player from the second it is set (旗&1; 'hide 2' never: &512), not only redrawn; the
    plain NAMED_ATTACK_NAMED on one of its own side fires nothing (友血 100 until the force attack at 8 s). The rest as
    predicted. The simulator fixed to both (sim.Sim.cond_retail2 TEAM_DISCOVERED, Sim.order_attack). A first run with
    the Calm row off the map's 5000 border and rows across probe_range's lanes read nothing usable (dropped).
"""
from maps import probe_border
from parts import Mission, Script, Test, square, status
import checks.engine_scripts8 as s8

TANK, PLANT = 'AlliedAntiVehicleVehicleTech1', 'SovietPowerPlant'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
RUN = {'flow': 30.0}
SLOT = {'bait': (600.0, 4000.0), 'bait 2': (1400.0, 4000.0), 'sieger': (2200.0, 4000.0), 'idler': (3000.0, 4000.0),
        'force': (3800.0, 4000.0), 'stuck': (600.0, 4700.0), 'calm': (1400.0, 4700.0), 'calm 2': (2200.0, 4700.0),
        'calm 3': (3000.0, 4700.0)}
GAP = 150.0
HIDE, HIDE2 = (4500.0, 3000.0), (4500.0, 2200.0)
SA = (SLOT['stuck'][0] + 300.0, SLOT['stuck'][1])
SWITCH_AT = 6.0


def _n(part):
    return f'UNIT - CNV Act {part.title()}'


def _put(m, template, x, y, **kw):
    m.put(template, 'stop row', x - O[0], y - O[1], **kw)


def mission():
    m = Mission(name='CampActs', map=probe_border, units=[], facts={})
    m.spawns |= {TANK, PLANT}

    def unit(role, side, template, x, y, crew=None):
        props = {'originalOwner': m.crew(crew, side=side)} if crew else {}
        _put(m, template, x, y, side=side, angle=0.0 if side == 'p1' else 3.1416, name=_n(role), role=role,
             props=props)

    unit('hide', 's4', TANK, *HIDE, crew='Hide')
    unit('hide 2', 's4', TANK, *HIDE2, crew='Hide2')
    for k, role in enumerate(('bait', 'bait 2'), 1):
        x, y = SLOT[role]
        unit(role, 'p1', TANK, x, y)
        unit(f'hunter {k}', 's4', TANK, x + GAP, y)
    for k, (crew, role) in enumerate((('Sieger', 'sieger'), ('Idler', 'idler')), 1):
        x, y = SLOT[role]
        unit(role, 'p1', TANK, x, y, crew=crew)
        unit(f'plant {k}', 's4', PLANT, x + GAP + 60.0, y)
    x, y = SLOT['force']
    unit('gunner', 'p1', TANK, x, y)
    unit('friend', 'p1', TANK, x + GAP, y)
    unit('stuck', 'p1', TANK, *SLOT['stuck'], crew='Stuck')
    m.waypoint('stuck to', 'Test Act Stuck To', 'stop row', SA[0] - O[0], SA[1] - O[1])
    for k, (crew, role) in enumerate((('Calm', 'calm'), ('Calm2', 'calm 2'), ('Calm3', 'calm 3')), 1):
        x, y = SLOT[role]
        unit(role, 'p1', TANK, x, y, crew=crew)
        unit(f'mark {k}', 's4', TANK, x + GAP, y)
    return m


def flow(m):
    t = Test()
    p1, s5 = m.player(), m.player('s5')
    name = lambda r: m.role(r).name                                                     # noqa: E731
    na = status('NO_ATTACK')
    t.areas['Test Act SA'] = square(*SA, 100.0)
    t.scripts.append(Script('Test - Act start', [], [
        ('PLAYER_RELATES_PLAYER', p1, s5, (2, 0.0, 'Friend')), ('PLAYER_RELATES_PLAYER', s5, p1, (2, 0.0, 'Friend')),
        ('PLAYER_TOGGLE_RESOURCE_SHARING', p1, 1), ('PLAYER_TOGGLE_RESOURCE_SHARING', s5, 1),
        ('PLAYER_SET_MONEY', p1, 0), ('PLAYER_SET_MONEY', s5, 0),
        *[('UNIT_CHANGE_OBJECT_STATUS', name(r), na, 1)
          for r in ('bait', 'bait 2', 'friend', 'mark 1', 'mark 2', 'mark 3', 'hide', 'hide 2')],
        ('UNIT_CHANGE_OBJECT_STATUS', name('bait'), status('SKIRMISH_AI_DO_NOT_ATTACK'), 1),
        ('NAMED_SET_DISABLED', name('stuck'), 'EMP', 1),
        ('TEAM_SET_STANCE', m.teams['Calm'], 3), ('UNIT_SET_STANCE', name('calm 3'), 3)]))
    s8.at(t, 'two', 2.0, [('NAMED_ATTACK_NAMED', name('gunner'), name('friend')),
                          ('MOVE_NAMED_UNIT_TO', name('stuck'), m.mark('stuck to'))])
    s8.at(t, 'switch', SWITCH_AT, [('UNIT_CHANGE_OBJECT_STATUS', name('hide'), status('SHROUD_REVEAL_TO_ALL'), 1),
                                   ('TEAM_ALLOW_AI_AUTOACQUIRE', m.teams['Sieger'], 1)])
    s8.at(t, 'give1', 3.0, [('PLAYER_GIVE_MONEY', p1, 1001)])
    s8.at(t, 'give2', 6.0, [('PLAYER_GIVE_MONEY', s5, 1000)])
    s8.at(t, 'eight', 8.0, [('NAMED_FORCE_ATTACK_NAMED', name('gunner'), name('friend')),
                            ('NAMED_SET_DISABLED', name('stuck'), 'EMP', 0)])
    s8.at(t, 'unshare', 9.0, [('PLAYER_TOGGLE_RESOURCE_SHARING', s5, 0)])
    s8.at(t, 'twelve', 12.0, [('PLAYER_GIVE_MONEY', p1, 1000), ('TEAM_SET_STANCE', m.teams['Calm'], 0),
                              ('UNIT_SET_STANCE', name('calm 3'), 0)])
    for counter, label, player in (('CNV_Act_M1', '甲钱', p1), ('CNV_Act_M5', '乙钱', s5)):
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter}', [], [('SET_PLAYER_MONEY_TO_COUNTER', player, counter)],
                                once=False))
    t.counters.append(('CNV_Act_HP', '友血'))
    t.scripts.append(Script('Test - CNV_Act_HP', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name('friend'),
                                                       'CNV_Act_HP')], once=False))
    s8.total(t, 'CNV_Act_Flags', '旗', [
        (1, ('TEAM_DISCOVERED', p1, m.teams['Hide'])),
        (2, ('NAMED_ATTACKED_BY_OBJECTTYPE', name('bait'), TANK)),
        (4, ('NAMED_ATTACKED_BY_OBJECTTYPE', name('bait 2'), TANK)),
        (8, ('NAMED_ATTACKED_BY_OBJECTTYPE', name('plant 1'), TANK)),
        (16, ('NAMED_ATTACKED_BY_OBJECTTYPE', name('plant 2'), TANK)),
        (32, ('TEAM_INSIDE_AREA_PARTIALLY', m.teams['Stuck'], 'Test Act SA', 0)),
        (64, ('NAMED_ATTACKED_BY_OBJECTTYPE', name('mark 1'), TANK)),
        (128, ('NAMED_ATTACKED_BY_OBJECTTYPE', name('mark 2'), TANK)),
        (256, ('NAMED_ATTACKED_BY_OBJECTTYPE', name('mark 3'), TANK)),
        (512, ('TEAM_DISCOVERED', p1, m.teams['Hide2']))])
    s8.watch(t, RUN['flow'])
    return t


MISSION = {'engine_acts': mission}
CHECKS = {'engine_acts': {'flow': flow}}
