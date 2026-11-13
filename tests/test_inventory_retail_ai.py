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


def test_every_retail_computer_player_personality_is_compiled():
    reach = json.load(open(AI_JSON, encoding='utf-8'))
    missing = [(m, p['name'], p['personality']) for m, stem in R.missions().items() for p in R.ai_players(stem)
               if p['personality'] not in reach]
    assert not missing
    assert any(n == 'AIP_A01_SovietHuntMarshall' and t == 'AIPersonalityDefinition'
               for t, n, _ in reach['AIP_A01_SovietHuntMarshall'])
