"""The FireWeaponWhenDead module (engine/modules/fireweaponwhendead.py, step B5c): InitiallyActive and the DieMuxData
(death types; RequiredStatus / ExemptStatus against the thing's status, AIRBORNE_TARGET in the air) decide whether a
death fires its DeathWeapon (World.fire -> simbody.Life.fire: the weapon's DamageNuggets queued as death blasts); a
deletion fires nothing; a falling wreck's weapons come from its template's module data (Life.wreck_blasts). On the
bench: checks/engine_spawn.py refill (the exploding MiG), checks/engine_crash_fall.py (the Apollo's wreck)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.testing.small as simsmall  # noqa: E402
from engine.kernel import interfaces, module  # noqa: E402
from engine.modules import fireweaponwhendead as fw  # noqa: E402
from engine.modules import locomotor  # noqa: E402

BURST = ('<WeaponTemplate id="CNV_TestBurst" RadiusDamageAffects="ALLIES ENEMIES NEUTRALS"><Nuggets>'
         '<DamageNugget Damage="100" DamageType="UNRESISTABLE" Radius="10" DelayTimeSeconds="0.2s"/></Nuggets>'
         '</WeaponTemplate>')


def _bomb(name, mux):
    return (f'<GameObject id="{name}" KindOf="INFANTRY"><Body><ActiveBody MaxHealth="100"/></Body><Behaviors>'
            f'<FireWeaponWhenDead id="ModuleTag_Burst" InitiallyActive="true" DeathWeapon="CNV_TestBurst">{mux}'
            f'</FireWeaponWhenDead></Behaviors></GameObject>')


def test_the_data_reads_active_death_types_and_status():
    d = fw.FireWeaponWhenDeadData.parse(' InitiallyActive="true" DeathWeapon="W"',
                                        '<DieMuxData DeathTypes="ALL -CRUSHED" RequiredStatus="PLAYER_POWER_1" '
                                        'ExemptStatus="AIRBORNE_TARGET" />')
    assert d.weapon == 'W' and d.active
    assert d.fires('NORMAL', {'PLAYER_POWER_1'}) and not d.fires('NORMAL', set())
    assert not d.fires('CRUSHED', {'PLAYER_POWER_1'}) and not d.fires('NORMAL', {'PLAYER_POWER_1', 'AIRBORNE_TARGET'})
    off = fw.FireWeaponWhenDeadData.parse(' DeathWeapon="W"', '')
    assert not off.active and not off.fires('NORMAL')               # upgrade-activated: never on


def test_an_empty_death_types_fires_on_no_death():
    """DeathTypes="" written empty names no death: the death weapon never goes off (the parent's reader,
    simunits.death_weapons by _dies_of; review h P3), in a world as well as in the data."""
    d = fw.FireWeaponWhenDeadData.parse(' InitiallyActive="true" DeathWeapon="W"', '<DieMuxData DeathTypes="" />')
    assert not d.fires('NORMAL', set()) and not d.fires('CRUSHED', set())
    s = simsmall.small_world()
    s.own.update(CNV_TestBomb=_bomb('CNV_TestBomb', '<DieMuxData DeathTypes="" />') + BURST)
    s.add('shot', 'CNV_TestBomb', 'Player_1', 0.0, 0.0)
    s.world.kill(s.bodies['shot'], 'test')
    assert s.death_blasts == []


class _Host:
    def __init__(self):
        self.fired = []

    def fire(self, thing, weapon):
        self.fired.append(weapon)


def test_the_time_bomb_fires_its_level_on_the_ground_and_the_weaker_in_the_air():
    """alliedtimebomblvl2 (retail): ExemptStatus AIRBORNE_TARGET for AlliedTimeBomb_Level2, RequiredStatus for
    _Level1 -- the old reader (simunits.death_weapons) fired both."""
    s = simsmall.small_world()
    s.add('bomb', 'AlliedTimeBombLvl2', 'Player_1', 100.0, 100.0)
    b = s.bodies['bomb']
    mods = b.find(interfaces.DeathWeapon)
    host = _Host()
    for m in mods:
        m.world = host
    for surface in ('ground', 'air'):
        locomotor.write(s.world, b, surface=surface)
        for m in mods:
            m.on_die(module.Death(10, 'shot'))
    assert host.fired == ['AlliedTimeBomb_Level2', 'AlliedTimeBomb_Level1']


def test_an_inherited_player_power_weapon_needs_its_status():
    """The 47 Japanese templates' EnhancedKamikazeDeathPlayerPowerWeapon (RequiredStatus PLAYER_POWER_1), which the
    template data port merges in: no blast without the bit."""
    s = simsmall.small_world()
    s.add('tank', 'JapanAntiVehicleVehicleTech1', 'Player_1', 100.0, 100.0)
    b = s.bodies['tank']
    assert 'EnhancedKamikazeDeathPlayerPowerWeapon' in [m.death_weapon() for m in b.find(interfaces.DeathWeapon)]
    s.world.kill(b, 'test')
    assert s.death_blasts == []
    s.add('tank2', 'JapanAntiVehicleVehicleTech1', 'Player_1', 100.0, 100.0)
    b2 = s.bodies['tank2']
    b2.status = set(b2.status) | {'PLAYER_POWER_1'}
    s.world.kill(b2, 'test')
    assert [blast[8].name for blast in s.death_blasts][:1] == ['tank2']


def test_a_falling_wreck_fires_what_a_normal_death_of_no_status_sets_off():
    """Life.wreck_blasts: JapanAntiAirShipAirborne_Dying's inherited kamikaze weapon (PLAYER_POWER_1) stays out --
    only its crash weapon (150 EXPLOSIVE radius 20, allies 50 %), as the old reader read it."""
    import engine.objects.body as simbody
    s = simsmall.small_world()
    blasts = simbody.Life().wreck_blasts(s, 'JapanAntiAirShipAirborne_Dying')
    assert [(d[0], d[1], d[2], d[5]) for d in blasts] == [(150.0, 'EXPLOSIVE', 20.0, 0.5)]


def test_a_death_queues_the_weapon_where_it_died_and_a_deletion_nothing():
    s = simsmall.small_world()
    s.own.update(CNV_TestBomb=_bomb('CNV_TestBomb', '') + BURST)
    s.add('bomb', 'CNV_TestBomb', 'Player_1', 100.0, 50.0)
    s.add('gone', 'CNV_TestBomb', 'Player_1', 0.0, 0.0)
    s.world.remove(s.bodies['gone'], 'test')
    assert s.death_blasts == []
    now = s.frame_now()
    s.world.kill(s.bodies['bomb'], 'test')
    ((frame, x, y, dmg, typ, reach, affects, owner, by, ally, crash),) = s.death_blasts
    assert (frame - now, x, y, dmg, typ, reach, owner, by.name, ally, crash) == (
        3, 100.0, 50.0, 100.0, 'UNRESISTABLE', 10.0, 'Player_1', 'bomb', 1.0, False)


def test_the_death_s_own_type_decides_a_crush_its_crushed():
    """The module asks the death's type (the old reader always asked NORMAL): a crush passes CRUSHED
    (World.kill(..., death='CRUSHED') from locomotion.crush, step B5a)."""
    s = simsmall.small_world()
    s.own.update(CNV_TestBomb=_bomb('CNV_TestBomb', '<DieMuxData DeathTypes="CRUSHED" />') + BURST)
    s.add('shot', 'CNV_TestBomb', 'Player_1', 0.0, 0.0)
    s.world.kill(s.bodies['shot'], 'test')
    assert s.death_blasts == []
    s.add('flat', 'CNV_TestBomb', 'Player_1', 0.0, 0.0)
    s.world.kill(s.bodies['flat'], 'test', 'CRUSHED')
    assert [blast[8].name for blast in s.death_blasts] == ['flat']


def test_a_collide_weapon_goes_off_at_the_crusher_on_a_crush_only():
    """FireWeaponCollide WHEN_BEING_CRUSHED (E217, checks/engine_fwcollide.readings.toml): a crush fires its
    CollideWeapon on the crusher (its last attacker), any other death nothing; a RequiredStatus it lacks holds it."""
    def mine(name, required=''):
        return (f'<GameObject id="{name}" KindOf="INFANTRY"><Body><ActiveBody MaxHealth="100"/></Body><Behaviors>'
                f'<FireWeaponCollide id="ModuleTag_Revenge" CollideWeapon="CNV_TestBurst" Flags="WHEN_BEING_CRUSHED" '
                f'RequiredStatus="{required}" FireOnce="true"/></Behaviors></GameObject>')
    s = simsmall.small_world()
    s.own.update(CNV_TestMine=mine('CNV_TestMine') + BURST, CNV_TestHeld=mine('CNV_TestHeld', 'GENERIC_TOGGLE_STATE'))
    for n, t in (('crushed', 'CNV_TestMine'), ('shot', 'CNV_TestMine'), ('held', 'CNV_TestHeld')):
        s.add(n, t, 'Player_1', 0.0, 0.0)
    s.add('tank', 'CNV_TestMine', 'Player_2', 12.0, 0.0)
    for n, death in (('crushed', 'CRUSHED'), ('shot', 'NORMAL'), ('held', 'CRUSHED')):
        s.bodies[n].set_last_damage('Player_2', s.bodies['tank'])
        s.world.kill(s.bodies[n], 'test', death=death)
    assert [(d[1], d[2]) for d in s.death_blasts] == [(12.0, 0.0)]
