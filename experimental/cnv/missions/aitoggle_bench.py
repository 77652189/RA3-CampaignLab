"""Engine probe: when the skirmish AI's micro manager raises and lowers the Peacekeepers' riot shield (TOGGLE,
TOGGLE_DEFENSE_SELF_ONLY; read back by checks/engine_aitoggle.py; engine line B).

The data (SDK AlliedAntiInfantryInfantry): SpecialPower_ToggleRiotShield, two toggle states, TOGGLE_DEFAULT then
TOGGLE_DEFENSE_SELF_ONLY with DontUseIfInRange; shield on = ObjectStatus GENERIC_TOGGLE_STATE (the check reads it with
UNIT_HAS_OBJECT_STATUS). The program (work/re l4_toggle.md, 0x8c3600): on when an enemy targets the unit and (with
DontUseIfInRange) its own target is not in its range; off on the same test negated, no hysteresis -- off the next micro
round after nobody targets it. The model: RA3-EngineModel ra3model/ai/micro.py toggle / self_defence.

The enemy s1 runs the same one-state personality as aimicro_bench.py (StaticDefense of its yard, team of exactly two
Peacekeepers, StandardMicroManager: UpdateTime 0.5 s). The Peacekeepers stand 200 west of the s1 yard, 100 apart.
The attacker is a player Twinblade (SovietAntiGroundAircraft, gun 150): a Peacekeeper's shotgun cannot hit the air
(AntiMask ANTI_GROUND ...), so it has no target of its own in range and DontUseIfInRange never blocks the shield.
At ATTACK_AT the script creates it 250 west of Peacekeeper 1 and orders it to attack Peacekeeper 1; at STOP_AT it is
deleted (nobody targets anyone). Peacekeeper 2 is never targeted: its shield should stay down.
The Peacekeepers must be known to the AI as units with powers (l4_specials.md 0x9025e0: registered when made or
changed hands with the AI awake; yet aimicro's hand-over 1 s after the wake did not make the warriors charge), so
two builds:
  aitogglehand  the Peacekeepers start as the player's, handed to s1 at GIVE_AT (as aimicro_bench.py)
  aitogglemade  none placed: the script creates them on s1's team at GIVE_AT
Facts: wake at, give at, attack at, stop at.
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


def mission(name, made):
    facts = {'wake at': WAKE_AT, 'give at': GIVE_AT, 'attack at': ATTACK_AT, 'stop at': STOP_AT}
    m = Mission(name=name, map=niagara, facts=facts)
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{am.PID}'}
    m.assets.append((f'{am.PID}.xml', am.personality_xml('StandardMicroManager', PK), f'AIPersonalityDefinition:{am.PID}'))
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


MISSION = {'aitogglehand': lambda: mission('CampAITogHand', made=False),
           'aitogglemade': lambda: mission('CampAITogMade', made=True)}
