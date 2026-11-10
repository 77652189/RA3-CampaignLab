"""Inventory batch 4, NOT yet on the bench (the user is playing Red Alert 2, 11-09): the relation overrides
(TEAM_SET_OVERRIDE_RELATION_TO_PLAYER, PLAYER_SET_OVERRIDE_RELATION_TO_TEAM, TEAM_SET_OVERRIDE_RELATION_TO_TEAM) and
the attacks on a team (TEAM_ATTACK_TEAM, NAMED_ATTACK_TEAM). Not an engine_ file on purpose: inventory.bench_sources
reads only checks/engine_*.py, so nothing here counts as measured. Run with run_queue pend_scripts9:rel
pend_scripts9:atk, write the readings in, then move it to checks/engine_scripts9.py (build name engine_scripts9).
Mission on maps/probe_border.py (level ground; every place absolute, scenes >= 1000 apart). What the simulator
(sim.py hostile / the two attack branches, INFERRED from Generals' Team::getRelationship and groupAttackTeam)
predicts is in brackets.

  rel     four pairs, each the player's Guardian at x 1000 and an enemy (s1) Guardian 120 east of it, rows y 1000 /
          2000 / 3000 / 4000; the one whose health is read has NO_ATTACK, so only the side asked about can fire.
            A  the enemy's team FoeA to the player: Neutral at the start, Enemy at OFF_AT. 甲 = the player's health %
            B  the player to the enemy team FoeB: Neutral, Enemy at OFF_AT. 乙 = the enemy's health %
            C  the enemy team FoeC to the player's team MeC: Neutral, Enemy at OFF_AT. 丙 = the player's health %
            D  the control: no override. 丁 = the player's health %
          [simulator 11-09 PASS: 甲 乙 丙 100 to s10, 94 at s11, down ~6 a second (38 at s20); 丁 94 at s1, 0 from s16]
  atk     the player's crew Att (two Guardians, x 3000, y 1000 / 1150) and an enemy crew Tgt (two, x 3500, NO_ATTACK);
          the player's lone 'solo' (3000, 2500) and an enemy crew Tg2 (two, x 3500, y 2500 / 2650, NO_ATTACK); the
          control: the player's 'idle' (3000, 3500) and an enemy 'dummy' (3500, 3500, NO_ATTACK), no order (500 apart:
          nobody fires on his own, engine_scripts8's first status run). At 1 s TEAM_ATTACK_TEAM(Att, Tgt),
          NAMED_ATTACK_TEAM(solo, Tg2). 靶 = not destroyed: Tgt 1 x1, Tgt 2 x2, Tg2 1 x4, Tg2 2 x8, dummy x16
          [simulator 11-09 PASS: 31 to s20; 24 from s21 (Att's two kill Tgt's two side by side, solo kills Tg2 1);
          16 from s38 (solo goes on to Tg2 2: an attack on a team takes the next member); dummy untouched. Without
          the 'next member' rule solo stopped after one (24 to the end): that is what the bench decides]
"""
from maps import probe_border
from parts import Mission, Script, Test, status
import checks.engine_scripts8 as s8

TANK = 'AlliedAntiVehicleVehicleTech1'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
OFF_AT = 10.0
RUN = {'rel': 20.0, 'atk': 60.0}
REL = {'A': 1000.0, 'B': 2000.0, 'C': 3000.0, 'D': 4000.0}
ASKED = {'A': 'me', 'B': 'foe', 'C': 'me', 'D': 'me'}       # whose health is read; the other side holds fire
ATK = {'Att': ('p1', 3000.0, (1000.0, 1150.0)), 'Tgt': ('s1', 3500.0, (1000.0, 1150.0)),
       'Tg2': ('s1', 3500.0, (2500.0, 2650.0))}


def _n(part):
    return f'UNIT - CNV S9 {part}'


def _put(m, template, x, y, **kw):
    m.put(template, 'stop row', x - O[0], y - O[1], **kw)


def mission(name='CampPend9'):
    m = Mission(name=name, map=probe_border, units=[], facts={})
    m.spawns |= {TANK}
    for k, y in REL.items():
        me, foe = m.crew(f'Me{k}'), m.crew(f'Foe{k}', side='s1')
        _put(m, TANK, 1000.0, y, angle=0.0, name=_n(f'{k} Me'), role=f'{k} me', props={'originalOwner': me})
        _put(m, TANK, 1120.0, y, side='s1', angle=3.1416, name=_n(f'{k} Foe'), role=f'{k} foe',
             props={'originalOwner': foe})
    for crew, (side, x, ys) in ATK.items():
        c = m.crew(crew, side=side)
        for k, y in enumerate(ys, 1):
            kw = {'side': side} if side != 'p1' else {}
            _put(m, TANK, x, y, angle=0.0 if side == 'p1' else 3.1416, name=_n(f'{crew} {k}'), role=f'{crew} {k}',
                 props={'originalOwner': c}, **kw)
    _put(m, TANK, 3000.0, 2500.0, angle=0.0, name=_n('Solo'), role='solo')
    _put(m, TANK, 3000.0, 3500.0, angle=0.0, name=_n('Idle'), role='idle')
    _put(m, TANK, 3500.0, 3500.0, side='s1', angle=3.1416, name=_n('Dummy'), role='dummy')
    return m


def _hold(m, roles):
    return [('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, status('NO_ATTACK'), 1) for r in roles]


def rel(m):
    t = Test()
    p1 = m.player()
    held = [f'{k} {ASKED[k]}' for k in REL]      # the one read is the one shot at: it does not shoot back
    over = lambda r: [('TEAM_SET_OVERRIDE_RELATION_TO_PLAYER', m.teams['FoeA'], p1, r),
                      ('PLAYER_SET_OVERRIDE_RELATION_TO_TEAM', p1, m.teams['FoeB'], r),
                      ('TEAM_SET_OVERRIDE_RELATION_TO_TEAM', m.teams['FoeC'], m.teams['MeC'], r)]
    t.scripts.append(Script('Test - S9 start', [], _hold(m, held) + over('Neutral')))
    s8.at(t, 'off', OFF_AT, over('Enemy'))
    for k, label in zip(REL, '甲乙丙丁'):
        counter = f'CNV_S9_{k}'
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter}', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',
                                                           m.role(f'{k} {ASKED[k]}').name, counter)], once=False))
    t.expect += [(x, 0, '==', 100, OFF_AT - 2) for x in '甲乙丙'] + [('丁', OFF_AT - 2, '<', 100)]
    t.expect += [(x, RUN['rel'] - 2, '<', 100) for x in '甲乙丙']
    s8.watch(t, RUN['rel'])
    return t


def atk(m):
    t = Test()
    t.scripts.append(Script('Test - S9 hold', [], _hold(m, ['Tgt 1', 'Tgt 2', 'Tg2 1', 'Tg2 2', 'dummy'])))
    s8.at(t, 'attack', 1.0, [('TEAM_ATTACK_TEAM', m.teams['Att'], m.teams['Tgt']),
                             ('NAMED_ATTACK_TEAM', m.role('solo').name, m.teams['Tg2'])])
    names = [m.role(r).name for r in ('Tgt 1', 'Tgt 2', 'Tg2 1', 'Tg2 2', 'dummy')]
    s8.total(t, 'CNV_S9_Left', '靶', [(2 ** k, ('NAMED_NOT_DESTROYED', n)) for k, n in enumerate(names)])
    t.expect += [('靶', RUN['atk'] - 2, '==', 16)]
    s8.watch(t, RUN['atk'])
    return t


MISSION = {'pend_scripts9': mission}
CHECKS = {'pend_scripts9': {'rel': rel, 'atk': atk}}
