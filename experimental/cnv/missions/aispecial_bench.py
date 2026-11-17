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
import resources
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
# pile letter -> (dx, dy) off its site: A and B stood on niagara's trees (barracks 4 at (1925, 3350) on YP_Tree02,
# war factory 1 at (1700, 1650) on MR_Tree04; test_maps' scenery check). Moved 2026-11-06 (B round 16) to the
# nearest spots clear by 40+ of every tree. The readings of 11-06 (checks a-h, aispecialhid d) were taken before the
# move; they need no rerun: the piles keep their counts, spacing and costs, A moves 56 and B 56 units, still well
# apart (> 600) and far from the AI base, and the result (C is hit: A and B fail MinTargetsHit / value) does not hang
# on where inside the outpost a pile stands.
SHIFT = {'A': (-50.0, 25.0), 'B': (50.0, -25.0)}


def names(pile):
    return [f'UNIT - CNV AS {pile[0]} {k + 1}' for k in range(pile[4])]


POWERS_PID = 'CNVPowers'              # aispecoff / aispechb: 1AlliedBalanced with UsePlayerPowersAtDifficulty changed


def powers_xml(at):
    """1AlliedBalanced with UsePlayerPowersAtDifficulty=`at` (a difficulty bit set; D126: the AI fires its powers only
    at a difficulty in it; 1AlliedBalanced inherits the XSD default, all four)."""
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        '    <Include type="instance" source="DATA:SkirmishAI/Personalities/AlliedBalanced.xml" />',
        '  </Includes>',
        f'  <AIPersonalityDefinition id="{POWERS_PID}" PersonalityType="{POWERS_PID}" inheritFrom="1AlliedBalanced"'
        f' UsePlayerPowersAtDifficulty="{at}"/>',
        '</AssetDeclaration>', ''])


def mission(name='CampAISpecial', piles=PILES, use_at=None):
    # facts for the check (it may not import this module): the power, which piles (letters, cast 'A 1' ...) with their
    # hit weights, and whether the piles are revealed to the AI
    facts = {'wake at': WAKE_AT, 'power': POWER, 'piles': {p[0]: p[5] for p in piles}, 'reveal to ai': piles is PILES}
    m = Mission(name=name, map=resources.measured(niagara), facts=facts)
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': PERSONALITY}
    if use_at is not None:               # aispecoff / aispechb (check t): the bench plays MEDIUM
        m.facts['powers at medium'] = int('MEDIUM' in use_at.split())
        m.sides['s1']['aiPersonality'] = f'AIPersonalityDefinition:{POWERS_PID}'
        m.assets.append((f'{POWERS_PID}.xml', powers_xml(use_at), f'AIPersonalityDefinition:{POWERS_PID}'))
    m.spawns |= {SUPER}
    s1 = m.player('s1')
    m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
    m.put(PLANT, 'east power', 0, 0, side='s1', name='UNIT - CNV AS Plant', role='ai plant')
    m.put(SUPER, 'east base', -150.0, -250.0, side='s1', name=SUPER_NAME, role='collider')
    m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
    for pile in piles:
        letter, tpl, site, step, n, _ = pile
        dx, dy = SHIFT.get(letter, (0.0, 0.0))
        for k, nm in enumerate(names(pile)):
            m.put(tpl, site, dx + step * (k - (n - 1) / 2.0), dy, name=nm, role=f'{letter} {k + 1}')
    base = 'CNV AI Base'
    m.waypoint('ai base', base, 'east base')
    m.scripts += [
        Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
        Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0)])]
    return m


MISSION = {'aispecial': mission, 'aispecialhid': lambda: mission('CampAIHid', HIDDEN),
           'aispecoff': lambda: mission('CampAISpecOff', use_at=''),           # check t: powers at no difficulty
           'aispechb': lambda: mission('CampAISpecHB', use_at='HARD BRUTAL')}  # check t: not at MEDIUM
