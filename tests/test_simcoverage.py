"""What the plan simulator does not understand (experimental/cnv/simcoverage.py): every level's list of things it makes and
the simulator silently ignores must be the register of known gaps (KNOWN) -- a new unmodelled thing turns this red, and a
register entry nothing matches any more is stale. Skipped where the engine model is not on this computer (the script
engine's own names are told from it)."""
import importlib.util
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# loaded by file: simcoverage.py puts the cnv folders on the path itself (no new sys.path edit here: guard G4's ceiling)
_spec = importlib.util.spec_from_file_location('simcoverage', ROOT / 'experimental' / 'cnv' / 'simcoverage.py')
sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sc)

pytestmark = pytest.mark.skipif(sc.sim.engine_model() is None, reason='no ra3model.scripts (labpaths.ENGINE_MODEL)')

SIX = [('a6', '命令', '技能 SpecialPower_AthenaCannonTrigger'),
       # (11-08: the Athena's weapon is read -- its OCL; Tanya no longer fires at what she cannot hurt -- d4297bd;
       # a9's dark shield and a3's stasis zone are modelled -- simunits.effect, Sim.modify / aura_tick)
       ('a7', '命令', '占领'), ('j7', '脚本动作', 'NAMED_USE_COMMANDBUTTON_ABILITY:Command_CNV_Jammer_jam')]


@pytest.fixture(scope='module')
def census():
    t0 = time.time()
    items = sc.census()
    return items, time.time() - t0


def test_every_unmodelled_thing_of_every_level_is_registered(census):
    items, _ = census
    new, _ = sc.verdict(items)
    assert not new, 'not in simcoverage.KNOWN (register it with owner, repro, note -- or model it):\n' + \
        '\n'.join(f'  {i.level} | {i.line()}' for i in new)


def test_no_register_entry_is_stale(census):
    items, _ = census
    _, stale = sc.verdict(items)
    assert not stale, f'in simcoverage.KNOWN but no level shows it any more (delete them): {stale}'


def test_the_census_is_quick(census):
    assert census[1] < 90, f'{census[1]:.0f} s: only the levels are compiled and a probe Sim poked, nothing is run'


def test_every_register_entry_says_who_how_and_why():
    for key, row in sc.KNOWN.items():
        assert len(key) in (2, 3) and key[-2] in sc.CATEGORIES, key
        assert set(row) == {'owner', 'repro', 'note'} and all(isinstance(v, str) and v for v in row.values()), key
        if len(key) == 3:
            assert key[0] in sc.build_levels(), key


def test_the_six_known_gaps_are_found_and_registered(census):
    items, _ = census
    got = {(i.level, i.category, i.name) for i in items}
    for k in SIX:
        assert k in got, f'{k}: the census no longer finds this known gap'
        assert k in sc.KNOWN


def test_every_category_finds_something(census):
    items, _ = census
    seen = {i.category for i in items}
    # (STUCK: none left since d4297bd -- a unit takes no target its weapon does nothing to; the verdict tests below
    # still cover the category)
    assert {sc.WEAPON, sc.UPGRADE, sc.ACTION, sc.IGNORED_ACTION, sc.DEVICE, sc.COMMAND} <= seen


def test_a_new_unmodelled_item_turns_the_check_red():
    fake = sc.Item('zz9', sc.WEAPON, 'FakeGun', 'an invented unit whose weapon reads empty')
    new, _ = sc.verdict([fake], known={})
    assert new == [fake]
    new, _ = sc.verdict([fake], known={('zz9', sc.WEAPON, 'FakeGun'): dict(owner='x', repro='y', note='z')})
    assert not new
    new, _ = sc.verdict([fake], known={(sc.WEAPON, 'FakeGun'): dict(owner='x', repro='y', note='z')})
    assert not new                                  # a (category, name) key covers every level
    new, _ = sc.verdict([fake], known={('a1', sc.WEAPON, 'FakeGun'): dict(owner='x', repro='y', note='z')})
    assert new == [fake]                            # another level's key does not


def test_a_stale_register_entry_is_reported():
    key = ('zz9', sc.WEAPON, 'GoneGun')
    _, stale = sc.verdict([], known={key: dict(owner='x', repro='y', note='z')})
    assert stale == [key]


def test_the_probe_tells_a_known_name_from_a_made_up_one():
    inf = sc.info('a1')
    assert sc.name_state('act', 'SET_COUNTER', ['C', 1], inf) == 'core'         # the engine model's own
    assert sc.name_state('act', 'SET_FLAG', ['F', 1], inf) == 'handled'         # both (the timeline's notes on it)
    assert sc.name_state('act', 'NAMED_KILL', ['nobody'], inf) == 'handled'
    assert sc.name_state('act', 'DISPLAY_COUNTER', ['c', 'k'], inf) == 'core'   # the model shows counters itself
    assert sc.name_state('act', 'SKIRMISH_AI_USE_REPAIRS', ['p', 1], inf) == 'ignored'   # sim.IGNORED, the model's not
    assert sc.name_state('act', 'MADE_UP_ACTION', [], inf) == 'unknown'
    assert sc.name_state('cond', 'MADE_UP_CONDITION', [], inf) == 'unknown'
    assert sc.name_state('cond', 'NAMED_DESTROYED', ['nobody'], inf) == 'handled'


def test_a_weapon_read_as_none_is_caught():
    # a weapon the simulator reads empty although the XML declares it: the aircraft carrier's drones (an OCL nugget
    # making a unit; the Athena's OCL, an effect firing a weapon, is read since 11-08)
    got = [i for i in sc.weapon_items(sc.info('a5')) if i.name == 'AlliedAntiStructureShip']
    assert got and 'WeaponOCLNugget' in got[0].text
    assert not [i for i in sc.weapon_items(sc.info('a6')) if i.name == 'AlliedAntiStructureVehicle']
    inf = sc.info('a6')
    # and one that really has none (an engineer, a miner) is not
    assert not [i for i in sc.weapon_items(inf) if i.name in ('AlliedEngineer', 'AlliedMiner')]
