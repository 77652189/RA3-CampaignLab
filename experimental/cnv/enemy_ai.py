"""A level's enemy run by the game's skirmish AI (plan section 敌方AI, docs/story/plans/README.md): the engine's
builder and attacker with a personality of the level's own, the way the retail missions give each enemy theirs
(docs/story/plans/retail/README.md 1).

The personality is generated, not hand-written: it inherits the faction's co-op skirmish base (build states,
unit caps by difficulty, no taunts at enemies) and takes from one of the faction's skirmish commanders (the
style: 平衡, 空军 ...) only its opening moves and strategic states -- the commander's videos and taunts stay out.
On top: the level's unit preferences (UnitModifier). Everything else comes from the SDK files at build time.
Caps are not here: a SpecificUnitCap on a power plant did not hold (bench 2026-10-25, ai_plan/capped: capped at
2, it built 4); the plan caps by script, the retail way (plan.py compile_ai).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'campaign'))
import labpaths                                 # noqa: E402

PERSONALITIES = os.path.join(labpaths.SDK3, 'SageXML', 'SkirmishAI', 'Personalities')
SIDE = {'盟军': 'Allied', '苏联': 'Soviet', '帝国': 'Japan'}
PLAYER_TEMPLATE = {'盟军': 'PlayerTemplate:Allies', '苏联': 'PlayerTemplate:Soviet', '帝国': 'PlayerTemplate:Japan'}
STYLES = {                                      # the faction's skirmish commanders (SDK file names)
    '盟军': {'平衡': 'AlliedBalanced', '空军': 'AlliedSquadronLeader', '特种': 'AlliedSpecialForces'},
    '苏联': {'平衡': 'SovietBalanced', '突击': 'SovietShockSpecialist', '空军': 'SovietAirMarshall'},
    '帝国': {'平衡': 'JapanBalanced', '机甲': 'JapanMechaWarfare', '海军': 'JapanFleetCommand'},
}


def styles(faction):
    return sorted(STYLES[faction])


def taken(style_file):
    """The commander's opening moves and strategic states, as written in its file (comments dropped)."""
    with open(os.path.join(PERSONALITIES, style_file + '.xml'), encoding='utf-8-sig') as f:
        text = re.sub(r'<!--.*?-->', '', f.read(), flags=re.S)
    return re.findall(r'<OpeningMove\b.*?</OpeningMove>|<StrategicState\b[^>]*/>', text, re.S)


def personality(pid, faction, style='平衡', prefer=None):
    """The personality's XML: id pid, the faction's co-op skirmish base, the style's moves and states, prefer
    {template: factor} (how keen it is on that unit, attacking and defending; 0 never)."""
    if faction not in SIDE:
        raise ValueError(f'faction {faction!r}: one of {sorted(SIDE)}')
    if style not in STYLES[faction]:
        raise ValueError(f'style {style!r}: {faction} has {styles(faction)}')
    base = f'{SIDE[faction]}CoopBaseSkirmishPersonality'
    body = ['    ' + x.strip() for x in taken(STYLES[faction][style])]
    body += [f'    <UnitModifier Unit="{u}" OffensiveModifier="{k:g}" DefensiveModifier="{k:g}"/>'
             for u, k in (prefer or {}).items()]
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{base}.xml" />',
        '  </Includes>',
        f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{base}">',
        *body,
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])
