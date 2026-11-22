"""The LevelUpUpgrade module (engine/modules/levelup.py, step M12): its data read from the block (id, the TriggeredBy
elements -- not an attribute --, LevelsToGain, LevelCap, Permanent), several on one thing in block order, whether a
grant has it in force, and the body's level_modules forward (the ids in force) where the field was. The grant itself
(rank, upgrades, elite health) is benched in tests/test_simbench_c.py (engine_levelup a / b / c)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.objects.level as simlevel  # noqa: E402
import simrecord  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.modules import levelup  # noqa: E402
import engine.objects.modifier as simmodifier  # noqa: E402

HEAD = ' id="ModuleTag_Vet" LevelsToGain="3" LevelCap="4" Permanent="true" TriggeredBy="Ignored"'
INNER = '<TriggeredBy>Upgrade_A Upgrade_B</TriggeredBy>\n<TriggeredBy>Upgrade_C</TriggeredBy>'
UNIT = f'''<GameObject id="CNV_TestVet" KindOf="VEHICLE">
  <Behaviors>
    <LevelUpUpgrade{HEAD}>{INNER}</LevelUpUpgrade>
    <LevelUpUpgrade id="ModuleTag_Second" LevelsToGain="1" LevelCap="2"><TriggeredBy>Upgrade_D</TriggeredBy></LevelUpUpgrade>
  </Behaviors>
</GameObject>'''


def test_the_block_is_read_triggers_from_the_elements_only():
    d = levelup.LevelUpData.parse(HEAD, INNER)
    assert (d.mid, d.triggers, d.gain, d.cap, d.permanent) == (
        'ModuleTag_Vet', {'Upgrade_A', 'Upgrade_B', 'Upgrade_C'}, 3, 4, True)
    d = levelup.LevelUpData.parse('', '')
    assert (d.mid, d.triggers, d.gain, d.cap, d.permanent) == (None, frozenset(), 0, 0, False)


def test_several_in_block_order_and_the_forward_shows_those_in_force():
    s = simsmall.small_world()
    s.own['CNV_TestVet'] = UNIT
    s.add('vet', 'CNV_TestVet', 'Player_1', 100.0, 100.0)
    b = s.bodies['vet']
    first, second = b.find(interfaces.LevelUp)
    assert (first.module_id(), second.module_id()) == ('ModuleTag_Vet', 'ModuleTag_Second')
    assert second.rules() == (frozenset({'Upgrade_D'}), 1, 2, False)
    assert b.level_modules == set() and not first.active()
    second.set_active(True)
    assert b.level_modules == {'ModuleTag_Second'}
    assert simrecord.body_state(b)['level_modules'] == {'ModuleTag_Second'}
    second.set_active(False)
    assert b.level_modules == set()


PERMANENT = '''<GameObject id="CNV_TestVetP" KindOf="VEHICLE">
  <Behaviors>
    <LevelUpUpgrade id="ModuleTag_P" LevelsToGain="1" LevelCap="4" Permanent="true"><TriggeredBy>Upgrade_A</TriggeredBy></LevelUpUpgrade>
  </Behaviors>
</GameObject>'''


def test_a_permanent_module_stays_in_force_and_a_new_grant_gains_no_more(monkeypatch):
    """The removal of a Permanent module's trigger is a gap and leaves it in force: given again, it gains nothing."""
    monkeypatch.setattr(simlevel, 'profiles', lambda: {'cnv_testvetp': {2: ((), ()), 3: ((), ())}})
    s = simsmall.small_world()
    s.own['CNV_TestVetP'] = PERMANENT
    s.add('vet', 'CNV_TestVetP', 'Player_1', 100.0, 100.0)
    b = s.bodies['vet']
    simmodifier.upgrade(s, b, 'Upgrade_A', True)
    assert b.level_rank == 2 and b.level_modules == {'ModuleTag_P'}
    simmodifier.upgrade(s, b, 'Upgrade_A', False)
    assert b.level_modules == {'ModuleTag_P'}
    simmodifier.upgrade(s, b, 'Upgrade_A', True)
    assert b.level_rank == 2


def test_a_thing_without_one_reads_no_modules_in_force():
    s = simsmall.small_world()
    s.add('p', 'AlliedPowerPlant', 'Player_1', 100.0, 100.0)
    b = s.bodies['p']
    assert b.find(interfaces.LevelUp) == () and b.level_modules == set()
