"""The SlowDeath module (engine/modules/slowdeath.py, step B5a): its delay read from the block, the body's `lies` the
first block naming no death types, a death its DieMuxData takes lying it out (NAMED_DYING; E228), the port
a commented-out block not read (the port merges as the SDK compiler, which reads no XML comments) and the body's
fields in the frame record where they were. On the bench: benches/body_death/state/checks.py#engine_crush (a crushed conscript lay 127 frames)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simrecord  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
from engine.kernel import interfaces, module  # noqa: E402
from engine.modules import slowdeath  # noqa: E402

GUY = '''<GameObject id="CNV_TestGuy" Side="Soviet" KindOf="INFANTRY">
  <Behaviors>
    <SlowDeath id="ModuleTag_Toppled" DeathTypes="TOPPLED" DestructionDelay="4s" />
    <SlowDeath id="ModuleTag_Death" DestructionDelay="8.5s"><DieMuxData DeathTypes="ALL" DeathTypesForbidden="BURNED" /></SlowDeath>
    <DestroyDie id="ModuleTag_FrozenDie"><DieMuxData DeathTypes="ALL" RequiredStatus="UNDER_FROZEN" /></DestroyDie>
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
    assert len(mods) == 3 and isinstance(mods[2], slowdeath.DestroyDie)
    assert (guy.lies, guy.linger) == (8.5, slowdeath.LINGER)
    assert stump.find(interfaces.SlowDeath) == () and (stump.lies, stump.linger) == (0.0, slowdeath.LINGER)


def test_a_death_its_die_mux_takes_lies_the_delay_and_a_destroy_die_ends_it():
    """E228 (engine_teleport b, engine_crush, engine_sighted): a crush and a plain kill both lie 8.5 s; a type the
    block forbids lies nothing (the TOPPLED one does not take it either); a frozen one's DestroyDie: gone at once."""
    s = _world()
    for i, name in enumerate(('crushed', 'killed', 'burned', 'frozen')):
        s.add(name, 'CNV_TestGuy', 'Player_1', 100.0 * (i + 1), 100.0)
    crushed, killed, burned, frozen = (s.bodies[n] for n in ('crushed', 'killed', 'burned', 'frozen'))
    frozen.status = frozen.status | {'UNDER_FROZEN'}
    s.world.kill(crushed, 'crushed', death='CRUSHED')
    s.world.kill(killed, 'killed')
    s.world.kill(burned, 'burned', death='BURNED')
    s.world.kill(frozen, 'shattered')
    assert not crushed.alive and crushed.linger == 8.5 and s.dying(crushed) and s.present(crushed)
    assert (killed.linger, burned.linger, frozen.linger) == (8.5, slowdeath.LINGER, 0.0)
    for b in (crushed, killed, burned, frozen):     # the dead counted by each death's own lie (review 1125 S)
        b.kinds, b.died_at = b.kinds | {'SELECTABLE'}, s.t - 1.0
    s.act('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER_INCLUDE_DEAD', ['CNV_TestGuy', 'Player_1', 'D'], None)
    assert s.counters['D'] == 2
    crushed.died_at = killed.died_at = frozen.died_at = s.t - 8.6                 # past the lie
    assert not s.dying(crushed) and not s.present(crushed) and not s.present(killed)
    crushed.died_at, frozen.died_at = s.t - 8.4, s.t - 0.1
    assert s.dying(crushed) and not s.dying(frozen)
    s.world.remove(crushed, 'delete')                # mid-lie (review vv P3): its name kept this frame, not after
    assert s.present(crushed) and not s.dying(crushed)
    crushed.died_at -= 0.1
    assert not s.present(crushed) and s.holds(('NAMED_DESTROYED', 'crushed'))


def test_a_named_block_takes_only_its_own_death_type():
    s = _world()
    s.add('guy2', 'CNV_TestGuy', 'Player_1', 300.0, 100.0)
    named, plain, _ = s.bodies['guy2'].find(interfaces.SlowDeath)
    assert not named.is_plain() and plain.is_plain()
    named.begin(module.Death(10, 'crushed', 'CRUSHED'))
    assert named.lie() is None
    named.begin(module.Death(10, 'felled', 'TOPPLED'))
    assert named.lie() == 4.0


FIRST = '''<GameObject id="CNV_TestFirst" Side="Soviet" KindOf="INFANTRY">
  <Behaviors>
    <CreateObjectDie id="ModuleTag_Before" CreationList="OCL_None" />
    <SlowDeath id="ModuleTag_Death" DestructionDelay="2s" />
    <CreateObjectDie id="ModuleTag_After" CreationList="OCL_None" />
  </Behaviors>
</GameObject>'''


def test_a_die_module_before_the_slow_death_reads_this_deaths_lie(monkeypatch):
    """B5 review e #7 (the parent's order): the lie is set before the Die broadcast, so a Die module ahead of the
    SlowDeath in module order reads the crush's 2 s, not LINGER."""
    from engine.modules import createobjectdie
    s = _world()
    s.own['CNV_TestFirst'] = FIRST
    s.add('first', 'CNV_TestFirst', 'Player_1', 600.0, 100.0)
    read = []
    monkeypatch.setattr(createobjectdie.CreateObjectDie, 'on_die', lambda self, info: read.append(self.thing.linger))
    s.world.kill(s.bodies['first'], 'crushed', death='CRUSHED')
    assert read == [2.0, 2.0]


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
    s.world.kill(guy, 'crushed', death='CRUSHED')
    assert simrecord.body_state(guy)['linger'] == 8.5
