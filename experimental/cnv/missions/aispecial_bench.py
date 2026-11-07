"""Engine probe: when the skirmish AI fires its superweapon and at what (read back by checks/engine_aispecial.py).

Same Niagara map as aiopen_bench.py. The enemy (s1) is Allied, AlliedBalanced, a construction yard and a power plant
at the east base plus an AlliedSuperWeaponAdvanced (the proton collider, SpecialPowerParticleCannon: PLAYER_AOE_ATTACK
at STRUCTUREs only, not CONSTRUCTION_YARD / SUPER_WEAPON, MinTargetsHit 4; weapon ParticleCannonWeapon -> 400 damage,
radius 250, taper 200, on the SDK's ParticleAcceleratorFinalWeapon). No money (0 all along), so the AI builds nothing.
Asleep until WAKE_AT, then the retail wake set.

The player (p1) piles (spacing inside a pile < 250, the piles >= 640 apart; costs from the SDK's BuildCost):
  A  4 x AlliedBarracks (500)    = 2000  at outpost 1, 150 apart   (cheapest, 4 buildings)
  B  3 x AlliedWarFactory (2000) = 6000  at outpost 2, 200 apart   (dearest, only 3 buildings)
  C  5 x AlliedBaseDefense (800) = 4000  at front, 120 apart       (in between, 5 buildings)
Builds:
  aispecial     the three piles, all revealed to s1 (checks a, b, c, t)
  aispecialhid  one pile of 5 AlliedBaseDefense at west field, far from the AI and NOT revealed to s1 (check d)
Facts: wake at.
"""
from maps import niagara
from parts import Mission, Script

WAKE_AT = 10.0
PERSONALITY = 'AIPersonalityDefinition:1AlliedBalanced'
SUPER, POWER, PLANT = 'AlliedSuperWeaponAdvanced', 'SpecialPowerParticleCannon', 'AlliedPowerPlant'
SUPER_NAME = 'UNIT - CNV AS Collider'
# pile: (letter, template, site, spacing, count, hit weight)
PILES = (('A', 'AlliedBarracks', 'outpost 1', 150.0, 4, 1), ('B', 'AlliedWarFactory', 'outpost 2', 200.0, 3, 10),
         ('C', 'AlliedBaseDefense', 'front', 120.0, 5, 100))
HIDDEN = (('H', 'AlliedBaseDefense', 'west field', 120.0, 5, 1),)


def names(pile):
    return [f'UNIT - CNV AS {pile[0]} {k + 1}' for k in range(pile[4])]


def mission(name='CampAISpecial', piles=PILES):
    # facts for the check (it may not import this module): the power, which piles (letters, cast 'A 1' ...) with their
    # hit weights, and whether the piles are revealed to the AI
    facts = {'wake at': WAKE_AT, 'power': POWER, 'piles': {p[0]: p[5] for p in piles}, 'reveal to ai': piles is PILES}
    m = Mission(name=name, map=niagara, facts=facts)
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': PERSONALITY}
    m.spawns |= {SUPER}
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put(PLANT, 'east power', 0, 0, side='s1', name='UNIT - CNV AS Plant', role='ai plant')
    m.put(SUPER, 'east base', -150.0, -250.0, side='s1', name=SUPER_NAME, role='collider')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    for pile in piles:
        letter, tpl, site, step, n, _ = pile
        for k, nm in enumerate(names(pile)):
            m.put(tpl, site, step * (k - (n - 1) / 2.0), 0.0, name=nm, role=f'{letter} {k + 1}')
    base = 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
    m.scripts += [
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0)])]
    return m


MISSION = {'aispecial': mission, 'aispecialhid': lambda: mission('CampAIHid', HIDDEN)}
