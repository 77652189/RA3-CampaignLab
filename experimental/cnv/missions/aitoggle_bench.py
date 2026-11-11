"""Engine probe: when the skirmish AI's micro manager raises and lowers the Peacekeepers' riot shield (TOGGLE,
TOGGLE_DEFENSE_SELF_ONLY; read back by checks/engine_aitoggle.py; engine line B).

The data (SDK AlliedAntiInfantryInfantry): SpecialPower_ToggleRiotShield, two toggle states, TOGGLE_DEFAULT then
TOGGLE_DEFENSE_SELF_ONLY with DontUseIfInRange; shield on = ObjectStatus GENERIC_TOGGLE_STATE (the check reads it with
UNIT_HAS_OBJECT_STATUS). The program (work/re l4_toggle.md): on when an enemy targets the unit and (with
DontUseIfInRange) its own target is not in its range; off on the same test negated, no hysteresis -- off the next micro
round after nobody targets it. The model: RA3-EngineModel ra3model/ai/micro.py toggle / self_defence.

The enemy s1 runs the same one-state personality as aimicro_bench.py (StaticDefense of its yard, team of exactly two
Peacekeepers, StandardMicroManager: UpdateTime 0.5 s). The Peacekeepers stand 200 west of the s1 yard, 100 apart.
The attacker is a player Twinblade (SovietAntiGroundAircraft, gun 150): a Peacekeeper's shotgun cannot hit the air
(AntiMask ANTI_GROUND ...), so it has no target of its own in range and DontUseIfInRange never blocks the shield.
At ATTACK_AT the script creates it 250 west of Peacekeeper 1 and orders it to attack Peacekeeper 1; at STOP_AT it is
deleted (nobody targets anyone). Peacekeeper 2 is never targeted: its shield should stay down.
The Peacekeepers must be known to the AI as units with powers (l4_specials.md: registered when made or
changed hands with the AI awake; yet aimicro's hand-over 1 s after the wake did not make the warriors charge), so
two builds:
  aitogglehand  the Peacekeepers start as the player's, handed to s1 at GIVE_AT (as aimicro_bench.py)
  aitogglemade  none placed: the script creates them on s1's team at GIVE_AT
  aitogglehunt  as aitogglemade, the team's tactic a Targetless Hunt instead of StaticDefense (round 18: does the micro
                manager run only under some tactics? the Peacekeepers walk off towards the player; the Twinblade follows)
  aitogglexfer  as aitogglemade (StaticDefense), UNIT_AI_TRANSFER_ALL again right after making them (work/re
                l4_micro_gate.md: units left on teamSoviet_1 are never recruited)
Facts: wake at, give at, attack at, stop at, hunt (1: the Hunt tactic).
"""
from maps import niagara
from missions import aimicro_bench as am
from parts import Mission, Script

WAKE_AT = am.WAKE_AT
GIVE_AT = am.HAND_AT
ATTACK_AT, STOP_AT = 20.0, 35.0
PK, GUNSHIP = 'AlliedAntiInfantryInfantry', 'SovietAntiGroundAircraft'
GUNSHIP_NAME = 'UNIT - CNV AT Gunship'
WEST, APART, STANDOFF = 200.0, 100.0, 250.0


def mission(name, made, tactic='StaticDefense', xfer=False):
    facts = {'wake at': WAKE_AT, 'give at': GIVE_AT, 'attack at': ATTACK_AT, 'stop at': STOP_AT, 'hunt': float(tactic == 'Hunt')}
    m = Mission(name=name, map=niagara, facts=facts)
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{am.PID}'}
    m.assets.append((f'{am.PID}.xml', am.personality_xml('StandardMicroManager', PK, tactic),
                     f'AIPersonalityDefinition:{am.PID}'))
    m.cnv_units = (PK,)
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    m.spawns |= {PK, GUNSHIP}
    m.cnv_named = {'gunship': GUNSHIP_NAME}
    pks = []
    for k in range(2):
        dy = APART * (k - 0.5)
        n = f'UNIT - CNV AT Peacekeeper {k + 1}'
        pks.append(n)
        if made:
            m.waypoint(f'peacekeeper {k + 1} spot', f'CNV AT Peacekeeper Spot {k + 1}', 'east base', -WEST, dy)
            m.cnv_named[f'peacekeeper {k + 1}'] = n
        else:
            m.put(PK, 'east base', -WEST, dy, side='p1', angle=3.1416, name=n, role=f'peacekeeper {k + 1}')
    m.waypoint('gunship spot', 'CNV AT Gunship Spot', 'east base', -WEST - STANDOFF, -APART / 2)
    base = 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
    give = ([('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', n, PK, m.team('s1'), m.mark(f'peacekeeper {k + 1} spot'))
             for k, n in enumerate(pks)] if made else [('NAMED_TRANSFER_OWNERSHIP_PLAYER', n, s1) for n in pks])
    give += [('UNIT_AI_TRANSFER_ALL', s1, 1)] if xfer else []   # round 18: as aimicro_bench.py xfer
    m.scripts += [
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT),
                                      ('SET_MILLISECOND_TIMER', 'CNV AI Give', GIVE_AT),
                                      ('SET_MILLISECOND_TIMER', 'CNV AT Attack', ATTACK_AT),
                                      ('SET_MILLISECOND_TIMER', 'CNV AT Stop', STOP_AT)]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)]),
        Script('CNV AI - Give', [('TIMER_EXPIRED', 'CNV AI Give')], give),
        Script('CNV AT - Attack', [('TIMER_EXPIRED', 'CNV AT Attack')],
               [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', GUNSHIP_NAME, GUNSHIP, m.team('p1'), m.mark('gunship spot')),
                *m.order('attack', [GUNSHIP_NAME], pks[0], 'p1')]),
        Script('CNV AT - Stop', [('TIMER_EXPIRED', 'CNV AT Stop')], [('NAMED_DELETE', GUNSHIP_NAME)])]
    return m


# bench 2026-11-07 first run (attack 30 / stop 45): the Allied barracks gave the second Peacekeeper only at ~s51
BUILT_ATTACK_AT, BUILT_STOP_AT = 70.0, 85.0
HUNT_DELAY = 12.0   # aitogglebltf: seconds after s1 owns two before the gunship (the Hunt recruits ~10-20 s after)


def built(name, tactic='StaticDefense'):
    """aitogglebuilt (round 19): the AI builds the two Peacekeepers itself (aimicro_bench.py built_base: an opening
    move, an Allied barracks 400 south of the yard). The units are unnamed: the check counts by player. Once s1 owns
    two, the barracks is deleted (nothing but the Peacekeepers for the gunship to hit near there); at BUILT_ATTACK_AT
    the gunship is made 300 south of the barracks spot and attack-moves to it; deleted at BUILT_STOP_AT.
    tactic 'Hunt' (aitogglebltf, round 20, as aimicro_bench.py aimicbuiltf): a Targetless Hunt team recruits them and
    walks them off; once s1 owns two, all three of s1's structures are deleted and HUNT_DELAY later the gunship is
    made at the barracks spot and HUNTs (TEAM_HUNT) -- the Peacekeepers are the only thing of s1's left to aim at.
    (Bench 11-07: TEAM_HUNT at s70 never hit them; attack-move at the moment of two owned killed both by s41 with no
    shield -- likely before the Hunt took them.) The check's 帧数 still counts from BUILT_ATTACK_AT; 曾盾 counts from
    the first shield whenever."""
    hunt = tactic == 'Hunt'
    facts = {'wake at': WAKE_AT, 'give at': 0.0, 'attack at': BUILT_ATTACK_AT, 'stop at': BUILT_STOP_AT,
             'hunt': float(hunt), 'built': 1.0}
    m = Mission(name=name, map=niagara, facts=facts)
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{am.PID}'}
    m.assets.append((f'{am.PID}.xml', am.personality_xml('StandardMicroManager', PK, tactic, built=True),
                     f'AIPersonalityDefinition:{am.PID}'))
    m.cnv_units = (PK,)
    m.spawns |= {PK, GUNSHIP}
    m.cnv_named = {'gunship': GUNSHIP_NAME}
    am.built_base(m, 'AlliedBarracks')
    m.waypoint('gunship spot', 'CNV AT Gunship Spot', 'east base', 0, am.BARRACKS_DY - 300)
    m.scripts += [
        Script('CNV AT - Timers', [], [('SET_MILLISECOND_TIMER', 'CNV AT Attack', BUILT_ATTACK_AT),
                                       ('SET_MILLISECOND_TIMER', 'CNV AT Stop', BUILT_STOP_AT)]),
        Script('CNV AT - Clear', [('COUNTER', 'CNV_AI_Owned', 3, 2)],
               [('NAMED_DELETE', n) for n in ('UNIT - CNV AI Factory',
                                              *(('UNIT - CNV AI Plant', 'UNIT - CNV AI Yard') if hunt else ()))]),
        *([Script('CNV AT - Go timer', [('COUNTER', 'CNV_AI_Owned', 3, 2)],
                  [('SET_MILLISECOND_TIMER', 'CNV AT Go', HUNT_DELAY)])] if hunt else []),
        Script('CNV AT - Attack', [('TIMER_EXPIRED', 'CNV AT Go')] if hunt else [('TIMER_EXPIRED', 'CNV AT Attack')],
               [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', GUNSHIP_NAME, GUNSHIP, m.team('p1'),
                 m.mark('factory spot' if hunt else 'gunship spot')),
                *(m.order('hunt', [GUNSHIP_NAME], None, 'p1') if hunt else
                  m.order('attack_move', [GUNSHIP_NAME], m.mark('factory spot'), 'p1'))]),
        Script('CNV AT - Stop', [('TIMER_EXPIRED', 'CNV AT Stop')], [('NAMED_DELETE', GUNSHIP_NAME)])]
    return m


MISSION = {'aitogglebuilt': lambda: built('CampAITogBuilt'),
           'aitogglebltf': lambda: built('CampAITogBltF', tactic='Hunt'),
           'aitogglehand':lambda: mission('CampAITogHand', made=False),
           'aitogglemade': lambda: mission('CampAITogMade', made=True),
           'aitogglehunt': lambda: mission('CampAITogHunt', made=True, tactic='Hunt'),
           'aitogglexfer': lambda: mission('CampAITogXfer', made=True, xfer=True)}
