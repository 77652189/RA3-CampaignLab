"""The CreateObjectDie module (engine/modules/createobjectdie.py, step B5b): its DieMuxData read as the private model's
DieMux.applies (death types, forbidden, required / exempt status), a death of age making its list where the thing
stood (only one read off the template: the skirmish AI's late lifetime leaves nothing), any other death nothing, and a
death in the air making the first airborne module's wrecks fall (World.create airborne). On the bench:
checks/engine_life.py (the ice core's wall), checks/engine_crash_fall.py (the Apollo's wreck)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simbody  # noqa: E402
import simsmall  # noqa: E402
from engine.kernel import interfaces, module  # noqa: E402
from engine.modules import createobjectdie as cod  # noqa: E402

CORE = '''<GameObject id="CNV_TestCore" Side="Neutral" KindOf="IMMOBILE">
  <Behaviors>
    <LifetimeUpdate id="ModuleTag_Life" MinLifetime="1s" MaxLifetime="1s" DeathType="FADED" />
    <CreateObjectDie id="ModuleTag_Wall" CreationList="OCL_CNV_TestWall"><DieMuxData DeathTypes="FADED" /></CreateObjectDie>
    <CreateObjectDie id="ModuleTag_Rubble" CreationList="OCL_CNV_TestRubble"><DieMuxData DeathTypes="ALL -FADED" /></CreateObjectDie>
  </Behaviors>
</GameObject>
<ObjectCreationList id="OCL_CNV_TestWall"><CreateObject><CreateObject>CNV_TestWall</CreateObject></CreateObject></ObjectCreationList>
<ObjectCreationList id="OCL_CNV_TestRubble"><CreateObject><CreateObject>CNV_TestWall</CreateObject></CreateObject></ObjectCreationList>'''
WALL = '<GameObject id="CNV_TestWall" Side="Neutral" KindOf="IMMOBILE"><Behaviors /></GameObject>'
ROCK = '''<GameObject id="CNV_TestRock" Side="Neutral" KindOf="IMMOBILE"><Behaviors>
  <CreateObjectDie id="ModuleTag_Wall" CreationList="OCL_CNV_TestWall"><DieMuxData DeathTypes="ALL" /></CreateObjectDie>
</Behaviors></GameObject>'''


def _world():
    s = simsmall.small_world()
    s.own.update({'CNV_TestCore': CORE, 'CNV_TestWall': WALL})
    return s


def _walls(s):
    return [b for b in s.bodies.values() if b.template == 'CNV_TestWall']


def test_the_die_mux_takes_death_types_and_status_as_the_model_s_applies():
    d = cod.CreateObjectDieData.parse(' CreationList="X"', '<DieMuxData DeathTypes="ALL -CRUSHED" '
                                      'DeathTypesForbidden="SUICIDED" RequiredStatus="AIRBORNE_TARGET" />')
    assert d.ocl == 'X' and d.takes('NORMAL') and not d.takes('CRUSHED') and not d.takes('SUICIDED')
    assert d.holds({'AIRBORNE_TARGET'}) and not d.holds(set())
    named = cod.CreateObjectDieData.parse(' CreationList="Y"', '<DieMuxData DeathTypes="FADED" ExemptStatus="AIRBORNE_TARGET" />')
    assert named.takes('FADED') and not named.takes('NORMAL')
    assert named.holds(set()) and not named.holds({'AIRBORNE_TARGET'})
    bare = cod.CreateObjectDieData.parse('', '')
    assert bare.ocl == '' and bare.takes('NORMAL') and bare.holds({'AIRBORNE_TARGET'})


def test_a_death_of_age_makes_the_list_its_death_type_takes_where_it_stood_that_frame():
    s = _world()
    s.add('core', 'CNV_TestCore', 'Player_1', 100.0, 100.0)
    core = s.bodies['core']
    assert [m.creation_list() for m in core.find(interfaces.CreateOnDeath)] == ['OCL_CNV_TestWall', 'OCL_CNV_TestRubble']
    s.world.schedule.run('expire', core.life_end)
    (wall,) = _walls(s)                                 # FADED: the wall's, not the rubble's (ALL -FADED)
    assert not core.alive and wall.alive and (wall.x, wall.y, wall.owner) == (100.0, 100.0, 'Player_1')


def test_any_other_death_makes_nothing():
    s = _world()
    s.add('core', 'CNV_TestCore', 'Player_1', 100.0, 100.0)
    s.destroy(s.bodies['core'], 'test')                 # NORMAL, no cause: the rubble's types take it, still nothing
    s.add('core2', 'CNV_TestCore', 'Player_1', 0.0, 0.0)
    s.destroy(s.bodies['core2'], 'test', 'FADED')       # the wall's type, but no death of age
    assert _walls(s) == []


def test_the_skirmish_ai_s_late_lifetime_is_no_death_of_age():
    s = _world()
    s.own['CNV_TestRock'] = ROCK
    s.add('core', 'CNV_TestRock', 'Player_1', 100.0, 100.0)
    core = s.bodies['core']
    assert core.find(interfaces.Lifetime) is None
    s.world.frame = 10
    simbody.last_until(s, core, 20)
    assert not core.find(interfaces.Lifetime).data.read
    s.world.schedule.run('expire', 20)
    assert not core.alive and _walls(s) == []


class _Host:
    def __init__(self):
        self.made = []

    def create(self, thing, ocl, airborne):
        self.made.append((ocl, airborne))


def test_a_death_in_the_air_makes_the_first_airborne_module_s_wrecks_fall_and_on_the_ground_none():
    s = simsmall.small_world()
    s.add('apollo', 'AlliedFighterAircraft', 'Player_1', 100.0, 100.0)
    b = s.bodies['apollo']
    mods = b.find(interfaces.CreateOnDeath)
    assert [m.takes_airborne() for m in mods] == [True, False]
    host = _Host()
    for m in mods:
        m.world = host
    b.surface = 'air'
    for m in mods:
        m.on_die(module.Death(10, 'shot'))
    assert host.made == [('AUFighterAircraft_Dying_OCL', True)]
    b.surface = 'ground'
    for m in mods:
        m.on_die(module.Death(10, 'shot'))
    assert host.made == [('AUFighterAircraft_Dying_OCL', True)]


def test_of_two_airborne_modules_only_the_first_makes_its_wrecks_fall():
    """INFERRED, kept from simunits.air_wrecks (which read one list): JapanAntiAirShip has two."""
    s = simsmall.small_world()
    s.add('ship', 'JapanAntiAirShip', 'Player_1', 100.0, 100.0)
    b = s.bodies['ship']
    mods = b.find(interfaces.CreateOnDeath)
    assert sum(m.takes_airborne() for m in mods) == 2
    host = _Host()
    for m in mods:
        m.world = host
    b.surface = 'air'
    for m in mods:
        m.on_die(module.Death(10, 'shot'))
    assert len(host.made) == 1 and host.made[0][1]


PLANE = '''<GameObject id="CNV_TestPlane" Side="Allies" KindOf="AIRCRAFT">
  <Behaviors>
    <CreateObjectDie id="ModuleTag_Frozen" CreationList="OCL_Frozen">
      <DieMuxData DeathTypes="ALL" RequiredStatus="UNDER_FROZEN" /></CreateObjectDie>
    <CreateObjectDie id="ModuleTag_First" CreationList="OCL_First">
      <DieMuxData DeathTypes="ALL" RequiredStatus="AIRBORNE_TARGET SPECIAL_ARMOR_ACTIVE" /></CreateObjectDie>
    <CreateObjectDie id="ModuleTag_Second" CreationList="OCL_Second">
      <DieMuxData DeathTypes="ALL" RequiredStatus="AIRBORNE_TARGET" /></CreateObjectDie>
  </Behaviors>
</GameObject>'''


def test_the_airborne_pick_matches_the_status_the_thing_has():
    """B5 review e #6 (the parent's pick): RequiredStatus is matched against the thing's status as it is
    (module.status_now), not a status of the one bit AIRBORNE_TARGET -- a plane holding both of the first module's bits
    takes the first list, one without the second's; a module whose RequiredStatus does not name AIRBORNE_TARGET is no
    airborne one (the old air_wrecks skipped it), whatever the thing holds."""
    s = simsmall.small_world()
    s.own['CNV_TestPlane'] = PLANE
    s.add('plane', 'CNV_TestPlane', 'Player_1', 100.0, 100.0)
    b = s.bodies['plane']
    mods = b.find(interfaces.CreateOnDeath)
    host = _Host()
    for m in mods:
        m.world = host
    b.surface = 'air'
    made = []
    for status in ({'SPECIAL_ARMOR_ACTIVE', 'UNDER_FROZEN'}, {'UNDER_FROZEN'}):
        b.status = set(status)
        host.made = []
        for m in mods:
            m.on_die(module.Death(10, 'shot'))
        made.append(host.made)
    assert made == [[('OCL_First', True)], [('OCL_Second', True)]]
    assert module.status_now(b) == {'UNDER_FROZEN', 'AIRBORNE_TARGET'}
