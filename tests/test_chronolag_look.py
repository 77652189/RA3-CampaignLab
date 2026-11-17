"""时滞炮车 deployed look (user 2026-11-17): the toggle's states (USER_1, also damaged) wear the deployed model, every
other state the packed one; the deployed model's W3X is included; deployed=None keeps the packed model everywhere."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'experimental' / 'cnv'), str(ROOT / 'experimental' / 'campaign')]
from units import chronolag  # noqa: E402

STATE = re.compile(r'<ModelConditionState\b([^>]*)>.*?<Model\s+Name="([^"]*)"', re.S)


def states(xml):
    return [(re.search(r'ConditionsYes="([^"]*)"', a).group(1) if 'ConditionsYes' in a else 'DEFAULT', m)
            for a, m in STATE.findall(xml)]


def test_deployed_states_wear_the_deployed_model():
    got = states(chronolag.chronolag().xml)
    dep = [m for c, m in got if 'USER_1' in c.split()]
    other = [m for c, m in got if 'USER_1' not in c.split()]
    assert dep and set(dep) == {chronolag.DEPLOYED.upper()}
    assert other and set(other) == {chronolag.LOOK.upper()}


def test_deployed_model_is_included():
    x = chronolag.chronolag().xml
    assert f'source="ART:{chronolag.DEPLOYED}.w3x"' in x
    assert f'source="ART:{chronolag.LOOK}.w3x"' in x


def test_no_deployed_model_keeps_the_packed_one():
    u = chronolag.dress(chronolag.chronolag(model=None), deployed=None)
    assert {m for _, m in states(u.xml)} == {chronolag.LOOK.upper()}
    assert 'CNChronoDep' not in u.xml
