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


def new_units_state(pid, new_units):
    """The build state that makes the AI build units of ours, or '' for none: new_units {template: CountModifier}.
    The AI builds no template no build state lists, even from a factory that makes it (bench 2026-11-11
    checks/engine_aiskirm.py y, aisknew: 0 to s168); listed FEWEST_UNIT in a ConstantHeuristic state it builds it
    from the first second it can (aisknew2: CountModifier 1 -> 9 of the barracks' 19 by s167). FEWEST_UNIT scores
    100 / (count / CountModifier + 1) (program read, B handoff 126): a bigger CountModifier, more of them."""
    if not new_units:
        return ''
    entries = [f'    <BuildEntry Build="{u}" Heuristic="FEWEST_UNIT" CountModifier="{k:g}"/>'
               for u, k in new_units.items()]
    return '\n'.join([f'  <AIBuildStateDefinition id="{pid}New">', '    <Heuristic>', '      <ConstantHeuristic/>',
                      '    </Heuristic>', *entries, '  </AIBuildStateDefinition>'])


def personality(pid, faction, style='平衡', prefer=None, new_units=None):
    """The personality's XML: id pid, the faction's co-op skirmish base, the style's moves and states, prefer
    {template: factor} (UnitModifier, attacking and defending -- it does not change what is built: bench
    engine_aiskirm u, B handoff 118), new_units {template of ours: CountModifier} (new_units_state; the AI still
    needs a factory of its own that makes them)."""
    if faction not in SIDE:
        raise ValueError(f'faction {faction!r}: one of {sorted(SIDE)}')
    if style not in STYLES[faction]:
        raise ValueError(f'style {style!r}: {faction} has {styles(faction)}')
    base = f'{SIDE[faction]}CoopBaseSkirmishPersonality'
    body = ['    ' + x.strip() for x in taken(STYLES[faction][style])]
    body += [f'    <UnitModifier Unit="{u}" OffensiveModifier="{k:g}" DefensiveModifier="{k:g}"/>'
             for u, k in (prefer or {}).items()]
    state = new_units_state(pid, new_units)
    if state:
        body.append(f'    <BuildState id="{pid}New" State="{pid}New" Difficulty="EASY MEDIUM HARD BRUTAL"/>')
    return '\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xai="uri:ea.com:eala:asset:instance">',
        '  <Tags></Tags>',
        '  <Includes>',
        f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{base}.xml" />',
        *[f'    <Include type="all" source="DATA:CNVUnits/Data/{u}.xml" />' for u in (new_units or {})],
        '  </Includes>',
        *([state] if state else []),
        f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{base}">',
        *body,
        '  </AIPersonalityDefinition>',
        '</AssetDeclaration>', ''])
