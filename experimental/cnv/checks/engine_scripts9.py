"""Inventory batch 4: the relation overrides (TEAM_SET_OVERRIDE_RELATION_TO_PLAYER,
PLAYER_SET_OVERRIDE_RELATION_TO_TEAM, TEAM_SET_OVERRIDE_RELATION_TO_TEAM) and the attacks on a team (TEAM_ATTACK_TEAM,
NAMED_ATTACK_TEAM), benched in round 134 on engine_scripts9b (the enemy crews on Soviet_4 / 5: placed units on a
Soviet_1 / 2 / 3 crew are on no team, rounds 130-133 below). Was checks/pending_scripts9.py, builds pend_scripts9*
(the bench_results files of rounds 130-133 carry those names); now engine_scripts9*. Run with run_queue
engine_scripts9b:rel engine_scripts9b:atk engine_scripts9b:atkr.
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

BENCH 11-09 (round 130). rel, the relation argument fixed (mapscript.encode_arg now writes index + name; before it a bare
  'Neutral' went out as 0 = Enemy): still 甲乙丙丁 all alike, 87 at s1, 12 from s12 (= dead: the minimap shows each read
  tank gone; a weapon-killed unit's health counter keeps its last value, sim.py now does so too).
  memb: 留 23 from s1 -- TEAM_KILL of the player's crew MeC killed it, of the enemy crews FoeA / Tgt killed nobody: the
  units placed on an ENEMY crew are not members of it (the map has them: originalOwner 'Soviet_1/teamCNVFoeA', the team
  in Teams). atk / atkr (health read, with and without MAP_REVEAL_ALL_PERM): all 100 to s61 -- the target crews are
  empty, so the attacks have nobody to attack. Not an answer on the five actions yet.
BENCH 11-09 (round 131): why the enemy crews are empty. (The bench's s1 is past the 2 s kill: memb's 23 is the kill's.)
  memb again with every crew written as retail's a02 'TEAM - Dock 01' (24 keys, teamIsSingleton 0, byte for byte):
    23, the same -- the team's shape is not it (mapxml.add_team left as it was).
  memb2 (UNIT_SET_TEAM of each onto its crew at the start, as Mission.order does): 23, the same.
  memb3 (member counts): 甲 (FoeA + 10 x Tgt) 0, 丙 teamSoviet_1 0 while the dummy (placed on it) lives: Soviet_1's
    units are on none of the map's teams.
  memb4 (pend_scripts9b: FoeX on Soviet_4, Tgt / Tg2 on Soviet_5, both DefaultPersonality): 留 16 -- TEAM_KILL takes
    the enemy crews. Soviet_4's AI modules are all 255 like Soviet_1's, so it is the personality: the container
    (Heidelberg, maps/island.py) gives Soviet_1 retail's AIP_A03_Soviet01BaseMarshall, which takes its player's units
    off every team at the start. Retail a02's scripted Soviet04 (whose 'TEAM - Dock 01' its TEAM_KILL takes) is
    DefaultPersonality, base / unit builder 240.
BENCH 11-09 (round 132): the personality is NOT it. Soviet_1 (and every crew owner) written DefaultPersonality by
  package.write_map (tried, reverted): the change took (engine_protocol pts 敌方点数 1 from s1, was 0: a Default
  player keeps its point), yet memb 23, memb3 甲 0 / 丙 0, rel 甲乙丙丁 alike (87 -> dead), atk / atkr 100 to s61 --
  the enemy crews on Soviet_1 still empty. Only the test's own script names Soviet_1 in the merged mission. Left
  between Soviet_1 and Soviet_4 / 5 in the container: playerAllies 'Soviet_2 Soviet_3' (4 / 5: none), the
  container's own Soviet_1 teams / build lists (Teams, BuildLists chunks), Soviet_4 enemies also StartingUnits.
BENCH 11-09 (round 133): it is Soviet_1 / 2 / 3 as such, not personality or alliance. memb's 留 (16 = crews killed):
  memb5 (9c: FoeX on Soviet_2, Tgt / Tg2 on Soviet_6, both Marshalls, only 2 allied) 17: Soviet_2's A foe lives,
  Soviet_6's crew dies. memb10 (9h: FoeX on Soviet_3, InnerBaseMarshall like Soviet_6 but allied) 17, the same.
  memb6 (9d: Soviet_1 playerAllies '') 23; memb7 (9e: allies '' on 1 / 2 / 3) 23; memb8 (9f: 2 / 3 Default) 23;
  memb9 (9g: 1 / 2 / 3 Default and no allies) 23. owner (pend_scripts9): the placed A foe and dummy ARE Soviet_1's
  (NAMED_OWNED_BY_PLAYER), so they are owned but on no team. Script-made Soviet_1 units do join a crew
  (engine_reorder / kingref: CREATE_NAMED_ON_TEAM teamSoviet_1 + UNIT_SET_TEAM, PASS). The container's BuildLists
  are per faction (no player names); its other files name no player. Left: what places Soviet_1..3 apart from 4..6
  -- their place in SidesList (before PlyrCivilian), anything SidesList carries per side past the property dict.
  The memb family's expectations are these readings (留 from s4; the bench's s1 is past the 2 s kill, so the 31
  before it is not read): they pin the Soviet_1..3 crews' emptiness, the simulator (16 on any side) differs there.
  rel / atk / atkr left the Soviet_1 build (their readings there are above) for engine_scripts9b.
BENCH 11-09 (round 134): rel / atk / atkr on engine_scripts9b (FoeX on Soviet_4, Tgt / Tg2 on Soviet_5): PASS, all
  five actions as the simulator has them.
  rel: 甲乙丙 100 to s8, 87 at s9 (the bench's seconds run one ahead of the timers, engine_scripts8b), then ~6 a second,
    12 (= dead) from s21: each of the three overrides holds fire at Neutral and lets it go at Enemy. 丁 (no override)
    87 at s1, 12 from s13. Simulator before this round: 丁 100 to the end -- its fallback took Soviet_2..6 as the
    player's enemies only once their AI was woken; the container's Player_1 has all six in playerEnemies (and they
    fire unprompted), so sim.Sim.enemy now takes every published player as the human's enemy.
  atk / atkr alike (MAP_REVEAL_ALL_PERM changes nothing): 甲 Tgt 1 and 乙 Tg2 1 from s4, ~6 a second, 12 from s16
    (Att's two take Tgt's two side by side: Tgt 1 falls at one tank's rate, like Tg2 1 under solo); 丙 Tg2 2 from s20,
    12 from s32 -- solo goes on to the team's next member; 丁 the dummy 100 to s61. Simulator: the same order, the
    kills at s20 / s37 (first fire s6), 2-4 s behind the bench.
BENCH 11-09 (round 135): the cause. SidesList decoded whole (u8 1, u32 12 sides, each the property dict + u32 0: no
  build list, nothing else per side); Teams ordinary (teamSoviet_1 like teamSoviet_4). LibraryMapLists (one per side,
  SidesList order) gives Player_2 and Soviet_1 / 2 / 3 Lib_Skirmish_Setup, Soviet_4 / 5 / 6 none -- and
  package.write_map clears every side's scripts but not their libraries. The library's 'Skirmish AI - Transfer Units'
  runs UNIT_AI_TRANSFER_ALL('<This Player>', 1) at the start (with SKIRMISH_AI_MAKE_BASE, _USE_REPAIRS, ...), which
  takes the player's placed units off every team (memb2's start-up UNIT_SET_TEAM did not survive it).
  memb11 (9i: Soviet_1's library list emptied): 留 16 from s1 -- the s1 crews die like Soviet_4's.
  memb12 (9j: 9b's sides with Lib_Skirmish_Setup copied onto Soviet_4 and 5): 留 23 -- their crews go empty.
  Simulator: neither runs the container's libraries nor takes units off teams on UNIT_AI_TRANSFER_ALL (16 on s1).
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


def mission(name='CampPend9', foe='s1', moved=None, map=probe_border):
    """foe: the side of the FoeX crews; moved: {crew: side} for an ATK crew moved off its side (pend_scripts9b)."""
    m = Mission(name=name, map=map, units=[], facts={})
    m.spawns |= {TANK}
    for k, y in REL.items():
        me, foe_c = m.crew(f'Me{k}'), m.crew(f'Foe{k}', side=foe)
        _put(m, TANK, 1000.0, y, angle=0.0, name=_n(f'{k} Me'), role=f'{k} me', props={'originalOwner': me})
        _put(m, TANK, 1120.0, y, side=foe, angle=3.1416, name=_n(f'{k} Foe'), role=f'{k} foe',
             props={'originalOwner': foe_c})
    for crew, (side, x, ys) in ATK.items():
        side = (moved or {}).get(crew, side)
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


def atk(m, reveal=False):
    t = Test()
    t.scripts.append(Script('Test - S9 hold', [], _hold(m, ['Tgt 1', 'Tgt 2', 'Tg2 1', 'Tg2 2', 'dummy']) +
                            ([('MAP_REVEAL_ALL_PERM', m.player())] if reveal else [])))
    s8.at(t, 'attack', 1.0, [('TEAM_ATTACK_TEAM', m.teams['Att'], m.teams['Tgt']),
                             ('NAMED_ATTACK_TEAM', m.role('solo').name, m.teams['Tg2'])])
    for k, (role, label) in enumerate(zip(('Tgt 1', 'Tg2 1', 'Tg2 2', 'dummy'), '甲乙丙丁')):  # a dead one's counter keeps its last value
        counter = f'CNV_S9_H{k}'
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter}', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',
                                                           m.role(role).name, counter)], once=False))
    t.expect += [('甲', 20, '<', 100), ('乙', 20, '<', 100), ('丙', RUN['atk'] - 2, '<', 100), ('丁', 0, '==', 100)]
    s8.watch(t, RUN['atk'])
    return t


def atkr(m):
    return atk(m, reveal=True)


LEFT = {'memb': 23, 'memb2': 23, 'memb3': 23, 'memb4': 16, 'memb5': 17, 'memb6': 23, 'memb7': 23, 'memb8': 23,
        'memb9': 23, 'memb10': 17, 'memb11': 16, 'memb12': 23}        # 留 on the bench (rounds 130-133); members everywhere would be 16


def memb(m, left=23):
    """Are the placed units members of their crews? Everyone holds fire; at 2 s TEAM_KILL the enemy crews FoeA and Tgt
    and the player's crew MeC. 留 = alive: A foe x1, Tgt 1 x2, Tgt 2 x4, C me x8, dummy (no crew) x16. Members: 16.
    left: the bench's 留 (LEFT)."""
    t = Test()
    every = [f'{k} {w}' for k in REL for w in ('me', 'foe')] + [f'{c} {k}' for c in ATK for k in (1, 2)] + \
        ['solo', 'idle', 'dummy']
    t.scripts.append(Script('Test - S9 hold all', [], _hold(m, every)))
    s8.at(t, 'kill', 2.0, [('TEAM_KILL', m.teams[c]) for c in ('FoeA', 'Tgt', 'MeC')])
    names = [m.role(r).name for r in ('A foe', 'Tgt 1', 'Tgt 2', 'C me', 'dummy')]
    s8.total(t, 'CNV_S9_Alive', '留', [(2 ** k, ('NAMED_NOT_DESTROYED', n)) for k, n in enumerate(names)])
    t.expect += [('留', 4, '==', left)]
    s8.watch(t, 10.0)
    return t


def memb2(m, left=23):
    """memb with every crew's units put on their crew by script at the start (UNIT_SET_TEAM, as Mission.order does
    before an order): does a script-made membership of an enemy crew hold where the placed originalOwner did not?
    Members: 16, as in memb."""
    t = memb(m, left)
    crews = {'A foe': 'FoeA', 'Tgt 1': 'Tgt', 'Tgt 2': 'Tgt', 'C me': 'MeC'}
    t.scripts.insert(0, Script('Test - S9 set teams', [],
                               [('UNIT_SET_TEAM', m.role(r).name, m.teams[c]) for r, c in crews.items()]))
    return t


def memb3(m):
    """memb2 and each crew's member count read every frame (TEAM_COMPARE_NUM_MEMBERS ==): 甲 = FoeA's (1 placed) +
    10 x Tgt's (2), 乙 MeC's (1), 丙 the enemy's default team teamSoviet_1's (dummy, and whoever is not on a crew).
    Before the kill at 2 s a member count says whether the enemy crews have members at all; after it, whether
    TEAM_KILL emptied them."""
    return _members(m, [m.teams['MeC'], _default(m, 's1')], LEFT['memb3'])


def _default(m, side):
    p = m.player(side)
    return f'{p}/team{p}'


def _members(m, teams, left):
    """memb2 with 甲 = FoeA's members + 10 x Tgt's, and 乙 / 丙 the member counts of `teams`."""
    t = memb2(m, left)
    s8.total(t, 'CNV_S9_NA', '甲', [(w * n, ('TEAM_COMPARE_NUM_MEMBERS', m.teams[c], 2, n))
                                    for c, w in (('FoeA', 1), ('Tgt', 10)) for n in range(1, 10)])
    for team, counter, label in zip(teams, ('CNV_S9_NC', 'CNV_S9_ND'), '乙丙'):
        t.counters.append((counter, label))
        t.scripts += [Script(f'Test - {counter} {n}', [('TEAM_COMPARE_NUM_MEMBERS', team, 2, n)],
                             [('SET_COUNTER', counter, n)], once=False) for n in range(10)]
    return t


def memb4(m):
    """pend_scripts9b: the FoeX crews on Soviet_4 (DefaultPersonality, AI modules 255), Tgt / Tg2 on Soviet_5
    (DefaultPersonality, base / unit builder 240 like retail a02's scripted Soviet04); the dummy stays on Soviet_1
    (the container's BaseMarshall). 甲 = FoeA's + 10 x Tgt's members, 乙 MeC's, 丙 teamSoviet_1's (as memb3; the
    spare players' default teams are not published)."""
    return _members(m, [m.teams['MeC'], _default(m, 's1')], LEFT['memb4'])


def memb5(m):
    """pend_scripts9c: FoeX on Soviet_2 (the container's Marshall, allied to Soviet_1 / 3), Tgt / Tg2 on Soviet_6
    (a Marshall too, no allies). 留's bits split them: A foe x1 is Soviet_2's, Tgt x2 / x4 Soviet_6's."""
    return memb(m, LEFT['memb5'])


def memb6(m):
    """pend_scripts9d: memb with Soviet_1's playerAllies emptied (the container: 'Soviet_2 Soviet_3')."""
    return memb(m, LEFT['memb6'])


def memb7(m):
    """pend_scripts9e: memb with playerAllies emptied on Soviet_1, 2 and 3 (nobody allied to Soviet_1 either way)."""
    return memb(m, LEFT['memb7'])


def memb8(m):
    """pend_scripts9f: memb with Soviet_2 and 3 (Soviet_1's allies) made DefaultPersonality, the alliances kept."""
    return memb(m, LEFT['memb8'])


def memb9(m):
    """pend_scripts9g: memb with Soviet_1, 2 and 3 all DefaultPersonality and none allied (9e and 9f at once)."""
    return memb(m, LEFT['memb9'])


def memb10(m):
    """pend_scripts9h: FoeX on Soviet_3 (InnerBaseMarshall like Soviet_6, but allied to Soviet_1 / 2), Tgt / Tg2 on
    Soviet_6 again (the control). A foe x1 is Soviet_3's."""
    return memb(m, LEFT['memb10'])


OWNERS = ['Player_1', 'Soviet_1', 'Soviet_2', 'Soviet_3', 'Soviet_4', 'Soviet_5', 'Soviet_6']    # the published ones


def owner(m):
    """Who owns the placed enemy units (NAMED_OWNED_BY_PLAYER, every frame; the counter = 1 + the owner's place in
    OWNERS, 0 = none of them): 甲 'A foe' (Soviet_1, crew FoeA), 乙 the dummy (Soviet_1's default team), 丙 'C me'
    (the player's, crew MeC: the control, 1). Everyone holds fire, nobody is killed."""
    t = Test()
    every = [f'{k} {w}' for k in REL for w in ('me', 'foe')] + [f'{c} {k}' for c in ATK for k in (1, 2)] + \
        ['solo', 'idle', 'dummy']
    t.scripts.append(Script('Test - S9 hold all', [], _hold(m, every)))
    for role, counter, label in (('A foe', 'CNV_S9_OA', '甲'), ('dummy', 'CNV_S9_OB', '乙'), ('C me', 'CNV_S9_OC', '丙')):
        s8.total(t, counter, label, [(k + 1, ('NAMED_OWNED_BY_PLAYER', p, m.role(role).name))
                                     for k, p in enumerate(OWNERS)])
    t.expect += [('甲', 2, '==', 2), ('乙', 2, '==', 2), ('丙', 2, '==', 1)]
    s8.watch(t, 6.0)
    return t


def memb11(m):
    """engine_scripts9i: memb with Soviet_1's library list emptied (the container gives Soviet_1 / 2 / 3 and Player_2
    Lib_Skirmish_Setup, whose 'Skirmish AI - Transfer Units' runs UNIT_AI_TRANSFER_ALL on its player at the start)."""
    return memb(m, LEFT['memb11'])


def memb12(m):
    """engine_scripts9j: memb on engine_scripts9b's sides (FoeX Soviet_4, Tgt / Tg2 Soviet_5) with Soviet_1's library
    list (Lib_Skirmish_Setup) given to Soviet_4 and Soviet_5 as well: the other half of memb11."""
    return memb(m, LEFT['memb12'])


def _libraries(players):
    """probe_border with the container's LibraryMaps (one per side, SidesList order, the nameless side first) changed:
    {player: 'none' | 'skirmish'} -- 'skirmish' copies Soviet_1's list (Lib_Skirmish_Setup)."""
    import types
    import mapstudy
    mod = types.ModuleType(probe_border.__name__)
    mod.__dict__.update({k: v for k, v in vars(probe_border).items() if not k.startswith('__')})

    def terrain(m):
        probe_border.terrain(m)
        names = [''] + list(mapstudy.players(m))
        libs = [n for _, n in m.walk() if n.name == 'LibraryMaps']
        skirmish = libs[names.index('Soviet_1')].head
        for player, what in players.items():
            libs[names.index(player)].head = bytes(4) if what == 'none' else skirmish
    mod.terrain = terrain
    return mod


def _sides(name, **sides):
    m = mission(name)
    for side, props in sides.items():
        m.sides[side] = dict(m.sides.get(side, {}), **props)
    return m


def _no_allies():
    return _sides('CampP9d', s1={'playerAllies': ''})


MISSION = {'engine_scripts9': mission,
           'engine_scripts9b': lambda: mission('CampP9b', foe='s4', moved={'Tgt': 's5', 'Tg2': 's5'}),
           'engine_scripts9c': lambda: mission('CampP9c', foe='s2', moved={'Tgt': 's6', 'Tg2': 's6'}),
           'engine_scripts9d': _no_allies,
           'engine_scripts9e': lambda: _sides('CampP9e', **{s: {'playerAllies': ''} for s in ('s1', 's2', 's3')}),
           'engine_scripts9f': lambda: _sides('CampP9f', **{s: {'aiPersonality': 'AIPersonalityDefinition:DefaultPersonality'}
                                                          for s in ('s2', 's3')}),
           'engine_scripts9g': lambda: _sides('CampP9g', **{s: {'playerAllies': '', 'aiPersonality':
                                                              'AIPersonalityDefinition:DefaultPersonality'}
                                                          for s in ('s1', 's2', 's3')}),
           'engine_scripts9h': lambda: mission('CampP9h', foe='s3', moved={'Tgt': 's6', 'Tg2': 's6'}),
           'engine_scripts9i': lambda: mission('CampP9i', map=_libraries({'Soviet_1': 'none'})),
           'engine_scripts9j': lambda: mission('CampP9j', foe='s4', moved={'Tgt': 's5', 'Tg2': 's5'},
                                               map=_libraries({'Soviet_4': 'skirmish', 'Soviet_5': 'skirmish'}))}
CHECKS = {'engine_scripts9': {'memb': memb, 'memb2': memb2, 'memb3': memb3,
                            'owner': owner},
          'engine_scripts9b': {'memb4': memb4, 'rel': rel, 'atk': atk, 'atkr': atkr},
          'engine_scripts9c': {'memb5': memb5}, 'engine_scripts9d': {'memb6': memb6},
          'engine_scripts9e': {'memb7': memb7}, 'engine_scripts9f': {'memb8': memb8},
          'engine_scripts9g': {'memb9': memb9}, 'engine_scripts9h': {'memb10': memb10},
          'engine_scripts9i': {'memb11': memb11}, 'engine_scripts9j': {'memb12': memb12}}
