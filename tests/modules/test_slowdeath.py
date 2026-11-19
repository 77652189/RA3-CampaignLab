"""The SlowDeath module (engine/modules/slowdeath.py, step B5a): its delay read from the block, the body's `lies` the
first block naming no death types, a crush's death lying it out (NAMED_DYING) and any other death LINGER, the port
a commented-out block not read (the port merges as the SDK compiler, which reads no XML comments) and the body's
fields in the frame record where they were. On the bench: checks/engine_crush.py (a crushed conscript lay 127 frames)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simrecord  # noqa: E402
import simsmall  # noqa: E402
from engine.kernel import interfaces, module  # noqa: E402
from engine.modules import slowdeath  # noqa: E402

GUY = '''<GameObject id="CNV_TestGuy" Side="Soviet" KindOf="INFANTRY">
  <Behaviors>
    <SlowDeath id="ModuleTag_Toppled" DeathTypes="TOPPLED" DestructionDelay="4s" />
    <SlowDeath id="ModuleTag_Death" DestructionDelay="8.5s"><DieMuxData DeathTypes="ALL" /></SlowDeath>
  </Behaviors>
</GameObject>'''
GUN = '''<GameObject id="CNV_TestGun" Side="Soviet" KindOf="STRUCTURE">
  <Behaviors>
    <!-- <SlowDeath id="ModuleTag_Death" DestructionDelay="10s" /> -->
  </Behaviors>
</GameObject>'''
STUMP = '<GameObject id="CNV_TestStump" Side="Neutral" KindOf="IMMOBILE"><Behaviors /></GameObject>'


def test_the_block_gives_its_delay_and_whether_it_names_death_types():
    d = slowdeath.SlowDeathData.parse(' DestructionDelay="8.5s"', '')
    assert (d.delay, d.plain) == (8.5, True)
    d = slowdeath.SlowDeathData.parse(' DeathTypes="TOPPLED" DestructionDelay="4s"', '')
    assert (d.delay, d.plain) == (4.0, False)
    assert slowdeath.SlowDeathData.parse('', '').delay == 0.0


_WORLD = []


def _world():
    """One small world for the file (a world takes about a second to make: tests/guards/test_time_budget.py); each
    test adds bodies of its own names."""
    if not _WORLD:
        s = simsmall.small_world()
        s.own.update({'CNV_TestGuy': GUY, 'CNV_TestGun': GUN, 'CNV_TestStump': STUMP})
        _WORLD.append(s)
    return _WORLD[0]


def test_the_body_lies_by_its_first_plain_block_and_nothing_without_one():
    s = _world()
    for name, tmpl in (('guy', 'CNV_TestGuy'), ('stump', 'CNV_TestStump')):
        s.add(name, tmpl, 'Player_1', 100.0, 100.0)
    guy, stump = s.bodies['guy'], s.bodies['stump']
    mods = guy.find(interfaces.SlowDeath)
    assert len(mods) == 2 and all(isinstance(m, slowdeath.SlowDeath) for m in mods)
    assert (guy.lies, guy.linger) == (8.5, slowdeath.LINGER)
    assert stump.find(interfaces.SlowDeath) == () and (stump.lies, stump.linger) == (0.0, slowdeath.LINGER)


def test_a_crushed_body_lies_its_delay_out_and_a_script_kill_lies_nothing():
    s = _world()
    s.add('crushed', 'CNV_TestGuy', 'Player_1', 100.0, 100.0)
    s.add('killed', 'CNV_TestGuy', 'Player_1', 200.0, 100.0)
    crushed, killed = s.bodies['crushed'], s.bodies['killed']
    s.destroy(crushed, 'crushed', death='CRUSHED')
    s.destroy(killed, 'killed')
    assert not crushed.alive and crushed.linger == 8.5 and s.dying(crushed) and s.present(crushed)
    assert not killed.alive and killed.linger == 0.0
    crushed.died_at = killed.died_at = s.t - 8.6                 # past the crushed one's lie
    assert not s.dying(crushed) and not s.present(crushed)
    crushed.died_at = s.t - 8.4
    assert s.dying(crushed) and not s.dying(killed)


def test_a_plain_module_takes_only_the_crush_and_a_named_one_none():
    s = _world()
    s.add('guy2', 'CNV_TestGuy', 'Player_1', 300.0, 100.0)
    named, plain = s.bodies['guy2'].find(interfaces.SlowDeath)
    assert not named.is_plain() and plain.is_plain()
    plain.on_die(module.Death(10, 'shot'))
    named.on_die(module.Death(10, 'crushed', 'CRUSHED'))
    assert plain.lie() == slowdeath.LINGER and named.lie() == slowdeath.LINGER
    plain.on_die(module.Death(10, 'crushed', 'CRUSHED'))
    assert plain.lie() == 8.5


def test_a_commented_out_block_is_not_read():
    """Step B5a, a behaviour change (有意改行为): the old reader slow_death read 25 templates' commented-out SlowDeath;
    the port merges as the SDK compiler does, and the compiler reads no XML comments -- they lie 0.0."""
    s = _world()
    s.add('gun', 'CNV_TestGun', 'Player_1', 500.0, 100.0)
    gun = s.bodies['gun']
    assert gun.find(interfaces.SlowDeath) == () and gun.lies == 0.0


def test_the_fields_are_in_the_frame_record_where_the_body_had_them():
    s = _world()
    s.add('guy3', 'CNV_TestGuy', 'Player_1', 400.0, 100.0)
    guy = s.bodies['guy3']
    state = simrecord.body_state(guy)
    assert (state['lies'], state['linger']) == (8.5, 0.0)
    s.destroy(guy, 'crushed', death='CRUSHED')
    assert simrecord.body_state(guy)['linger'] == 8.5
