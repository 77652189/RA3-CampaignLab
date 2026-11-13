"""inventory_retail's AI part: which retail players count as computer players, and every one's personality is found in
the game's compiled stream (retailref ai.json). Reads the local retail cache (work/retailref), skipped without it."""
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'experimental' / 'cnv'), str(ROOT / 'experimental' / 'campaign')]

import inventory as I  # noqa: E402
import inventory_retail as R  # noqa: E402

AI_JSON = os.path.join(I.RETAIL_SCRIPTS, 'ai.json')
pytestmark = pytest.mark.skipif(not os.path.exists(AI_JSON), reason='no retail AI cache (retailref.py cache)')


def test_a01_computer_players_are_the_two_with_their_own_personality():
    stem = R.missions()['a01']
    got = {p['name']: p['personality'] for p in R.ai_players(stem)}
    assert got == {'Player_2': 'AIP_A01_Coop_AlliedSpecialForces', 'Soviet_1': 'AIP_A01_SovietHuntMarshall'}


STATES = os.path.join(I.RETAIL_SCRIPTS, 'ai_states.xml')
needs_states = pytest.mark.skipif(not os.path.exists(STATES), reason='no decoded states (retailref.py cache-ai-states)')


@needs_states
def test_a01_own_attack_state_reads_back_from_its_compiled_form():
    st = R.compiled_states()['AIState_A01_AttackInvaders']
    assert st.get('MaxTargets') == '4'
    assert [(t.get('TargetHeuristic'), t.get('Priority')) for t in st.findall('TargetHeuristic')] == \
        [('ClosestGroundUnitHeuristic', '20'), ('ClosestGroundStructureHeuristic', None)]
    team = st.find('Tactic/TeamTemplate')
    assert (team.get('MinUnits'), team.get('MaxUnits'), team.get('MicroManager')) == ('8', '12', 'FearlessMicroManager')


@needs_states
def test_decoded_sdk_states_write_nothing_their_xml_does_not():
    """The ~175 states the SDK ships as xml are also in the compiled stream: what the decoder reads back from them is
    a subset of what their xml writes (it only misses attributes written at their default value)."""
    import inventory_ai as A
    index = A.assets()

    def names(el, idx):
        chain, kids = A._effective(el, idx)
        out = {n for c in chain for n, _ in A.element_names(c, None)}
        for k in kids:
            par = {c: p for p in k.iter() for c in p}
            out |= {n for d in k.iter() for n, _ in A.element_names(d, par.get(d, chain[0]))}
        return out
    states = R.compiled_states()
    for typ, least in (('AIStrategicStateDefinition', 150), ('AIPersonalityDefinition', 30),
                       ('AIBuildStateDefinition', 60), ('AIBudgetStateDefinition', 5)):   # b171: the last three
        pairs = [(k, el) for k, el in states.items() if k in index and A._local(index[k].tag) == typ]
        assert len(pairs) >= least, typ
        extra = {(k, n) for k, el in pairs for n in names(el, {}) - names(index[k], index)}
        assert not extra, typ


@needs_states
def test_the_maps_own_ai_assets_are_all_read_back():
    """Every personality / state the 27 maps carry themselves (no SDK xml) is decoded from the compiled stream: none
    is left counted only by the SDK assets it references (engine line B round 171: 92 personalities, 44 build and 5
    budget states were)."""
    assert not set().union(*R.ai_scope()[1].values())


@needs_states
def test_items_only_the_compiled_maps_write_are_in_the_inventory():
    """原版编译状态 is a census source: what only the maps' own compiled states write is an inventory item, and the 27's
    AI scope names nothing the inventory does not know."""
    import inventory_ai as A
    got = A.census()
    for name in ('战术/Tactic.UseTransports', '战术/Tactic.GatherWaypoint', '战术/Tactic.UpdateTime',
                 '战术/Tactic.CombatLeashSlack', '战术/Tactic.Tactic=SimpleDefense',
                 '启发条件/StructureOrHarvesterUnderAttackHeuristic',
                 '启发条件/StructureOrHarvesterUnderAttackHeuristic.TimeSinceAttacked'):
        assert got.get(name, [0])[0] > 0, name
    assert not [u for u in R.used_items()[1] if u[0] == I.AI]


def test_every_retail_computer_player_personality_is_compiled():
    reach = json.load(open(AI_JSON, encoding='utf-8'))
    missing = [(m, p['name'], p['personality']) for m, stem in R.missions().items() for p in R.ai_players(stem)
               if p['personality'] not in reach]
    assert not missing
    assert any(n == 'AIP_A01_SovietHuntMarshall' and t == 'AIPersonalityDefinition'
               for t, n, _ in reach['AIP_A01_SovietHuntMarshall'])
