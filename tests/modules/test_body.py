"""The Body family's port and data (engine/modules/body.py, simunits.module_blocks BODY, step B2a): the 7 Body tags --
ActiveBody, ImmortalBody, PropBody, ManagerBody, ManagedActiveBody, ManagedImmortalBody, HighlanderBody -- read
from the nearest non-empty <Body> up the chain, taken whole, defines spelled out. The census against the readers it
replaces (immortal_body / manager_body / prop_body / max_health and Sim.add's health) is
work/re/sim_split/b2_draft/b2_census.py: 3448 retail + 520 own templates, no difference."""
import pytest

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.data.units as simunits  # noqa: E402
from engine.modules import body  # noqa: E402

BASE = ('<GameObject id="CNVBodyBase"><Body><ActiveBody id="B" MaxHealth="400"/></Body>'
        '<Behaviors><SlowDeath id="S"/></Behaviors></GameObject>')


def test_bare_body_health_defaults_and_writes_require_body_module():
    import sim

    bare = sim.Body('bare', 'ProbeBare', 'P', 0., 0.)
    assert bare.hp == bare.max_hp == bare.health == 100.0
    for write in (bare.damage, bare.mend, bare.set_hp):
        with pytest.raises(RuntimeError, match="'bare' is missing a Body module"):
            write(10.0)


def answer(template, own=None):
    """{tag: [MaxHealth, ...]} of the Body tags the port answers for the template."""
    got = {tag: [body.BodyData.parse(*b).max_health for b in simunits.module_blocks(template, tag, own)]
           for tag in body.TAGS}
    return {tag: v for tag, v in got.items() if v}


def test_the_port_and_the_data_name_the_same_seven_tags():
    assert set(body.TAGS) == simunits.BODY and len(body.TAGS) == 7


def test_the_data_reads_max_health_a_literal_with_an_equals_sign_too():
    assert body.BodyData.parse(' id="B" MaxHealth="1500"', '').max_health == 1500.0
    assert body.BodyData.parse(' id="B" MaxHealth="=50000"', '').max_health == 50000.0
    assert body.BodyData.parse(' id="DefaultBody"', '').max_health is None


def test_the_nearest_body_is_taken_whole():
    own = {'CNVBodyBase': BASE,
           'CNVBodyImm': ('<GameObject id="CNVBodyImm" inheritFrom="CNVBodyBase"><Body>'
                          '<ImmortalBody id="B" MaxHealth="900"/></Body></GameObject>'),
           'CNVBodyHeir': '<GameObject id="CNVBodyHeir" inheritFrom="CNVBodyBase"><Behaviors/></GameObject>'}
    assert answer('CNVBodyImm', own) == {'ImmortalBody': [900.0]}       # not the base's ActiveBody as well
    assert answer('CNVBodyHeir', own) == {'ActiveBody': [400.0]}        # no Body of its own: the base's


def test_an_empty_body_is_skipped_and_a_define_spelled_out():
    own = {'CNVBodyBase': BASE,
           'CNVBodyEmpty': ('<GameObject id="CNVBodyEmpty" inheritFrom="CNVBodyBase"><Body>\n'
                            '<!-- <ImmortalBody id="B"/> --></Body></GameObject>')}
    assert answer('CNVBodyEmpty', own) == {'ActiveBody': [400.0]}       # a commented-out block is no block
    # retail: AM_Apartments_01 writes <Body></Body>; BaseCivilianStructureMedium's =$CIV_HEALTH_MEDIUM is 3000
    assert answer('AM_Apartments_01') == {'ActiveBody': [3000.0]}
    assert answer('AM_FutureTech_02') == {'ActiveBody': [50000.0]}      # MaxHealth="=50000"


def test_a_removed_prop_body_gives_way_to_the_active_body():
    # Compiled JapanAntiVehicleShipTorpedoSpreadProjectile: ActiveBody MaxHealth="100.0", zero PropBody.
    assert answer('JapanAntiVehicleShipTorpedoSpreadProjectile') == {'ActiveBody': [100.0]}
    assert answer('BaseProjectile') == {'PropBody': [None]}
    own = {'CNVBodyBase': BASE,
           'CNVBodyGone': ('<GameObject id="CNVBodyGone" inheritFrom="CNVBodyBase"><Body>'
                           '<ActiveBody id="B" xai:joinAction="Remove"/><ImmortalBody id="I" MaxHealth="50"/>'
                           '</Body></GameObject>')}
    assert answer('CNVBodyGone', own) == {'ImmortalBody': [50.0]}       # another Remove block is just left out


def test_the_managed_and_the_other_bodies_are_their_own_tags():
    assert answer('BaseBridge') == {'ManagerBody': [1.0]}
    # Compiled BaseCivilianBridge: one ManagerBody, MaxHealth="1.0", InitialHealth="1.0".
    assert answer('BaseCivilianBridge') == {'ManagerBody': [1.0]}
    assert set(answer('BaseBridgeEnd')) == {'ManagedImmortalBody'}      # not an ImmortalBody
    assert set(answer('BaseMountRushmoreHead')) == {'HighlanderBody'}


def test_a_campaign_override_is_read_first_as_max_health_reads_it():
    # CampaignOverrides: the Yari's 2000 over its file's 1500; Sim.add's health still takes fight's 1500 (B2b keeps it)
    assert answer('JapanAntiStructureShip') == {'ActiveBody': [2000.0]}
    assert simunits.max_health('JapanAntiStructureShip') == 2000.0
    assert simunits.fight('JapanAntiStructureShip')['hp'] == 1500.0


# --- step B2b: the module (one a thing, made by Sim.add; hp / max_hp / health_floor its state)

def _world(*objects):
    import engine.testing.small as simsmall
    return simsmall.small_world([(n, t, 'Player_1', 0.0, 0.0) for n, t in objects], model=False)


def _one(b):
    from engine.kernel import interfaces
    return b.find(interfaces.Body)


def test_sim_add_makes_one_body_module_of_the_tag_and_keeps_the_old_health():
    s = _world(('p', 'AlliedPowerPlant'), ('y', 'JapanAntiStructureShip'), ('f', 'RallyFlag'), ('g', 'AGenericSound'))
    assert _one(s.bodies['p']).kind() == 'ActiveBody' and not s.bodies['p'].immortal
    # fight's hp over the block's: the Yari's file 1500, not the campaign override's 2000 (B2a; 有意改行为 later)
    assert (s.bodies['y'].hp, s.bodies['y'].max_hp) == (1500.0, 1500.0)
    flag = s.bodies['f']        # no Body block up the chain (10 retail templates): an ActiveBody attached, a guess
    assert _one(flag).kind() == 'ActiveBody' and flag.max_hp in (300.0, 2000.0) and flag.hp == flag.max_hp
    snd = s.bodies['g']
    assert _one(snd).kind() == 'ImmortalBody' and snd.immortal and snd.health_floor == 1.0


def test_damage_stops_at_the_floor_a_prop_takes_none_a_heal_at_the_maximum():
    s = _world(('p', 'AlliedPowerPlant'), ('g', 'AGenericSound'), ('c', 'A09_IronCurtainEffect'))
    p, g, c = (s.bodies[n] for n in 'pgc')
    full = p.max_hp
    p.damage(full + 50)
    assert p.hp == 0.0 and p.health == 0.0
    p.mend(30.0)
    p.mend(float('inf'))
    assert p.hp == full
    p.health = 25
    assert p.hp == full / 4
    g.damage(1e9)
    assert g.hp == 1.0
    g.health = 0
    assert g.hp == 1.0                  # a script's 0 % holds an immortal at its floor
    assert c.prop == 'dies' and _one(c).kind() == 'PropBody'      # a NORMAL death up its chain
    assert _world(('l', 'AM_StreetSegment01')).bodies['l'].prop == 'stays'      # engine_propbody's street
    was = c.hp
    c.damage(50.0)
    assert c.hp == was and c.health == 0.0


def test_a_change_tells_the_damage_modules_a_making_does_not():
    from engine.kernel import interfaces, module
    s = _world(('p', 'AlliedPowerPlant'))
    p = s.bodies['p']
    heard = []

    class Ear(module.Module, interfaces.Damage):
        def on_damaged(self, was):
            heard.append(('hurt', was))

        def on_healed(self, was):
            heard.append(('healed', was))
    p.modules = tuple(p.modules) + (Ear(p, None),)
    full = p.max_hp
    p.damage(100.0)
    p.mend(30.0)
    p.set_hp(5.0, tell=False)
    assert heard == [('hurt', full), ('healed', full - 100.0)]


def test_the_fields_live_on_the_module_read_only_on_the_body_and_recorded_by_their_old_names():
    import pytest
    from engine.ports.observe import Observe
    s = _world(('p', 'AlliedPowerPlant'))
    p = s.bodies['p']
    assert not {'hp', 'max_hp', 'health_floor', 'immortal', 'prop'} & set(vars(p))
    assert vars(_one(p))['hp'] == p.hp
    with pytest.raises(AttributeError):
        p.hp = 1.0
    with pytest.raises(AttributeError):
        p.immortal = True
    d = Observe.state(p)
    assert (d['hp'], d['max_hp'], d['health_floor'], d['immortal'], d['prop']) == (p.max_hp, p.max_hp, 1.0, False, None)


def test_the_last_damage_and_the_indestructible_flag_live_on_the_module_step_b3():
    import pytest
    import sim
    import engine.script.act_object as simact_object
    from engine.ports.observe import Observe
    s = _world(('p', 'AlliedPowerPlant'), ('q', 'AlliedPowerPlant'))
    p, q = s.bodies['p'], s.bodies['q']
    assert (p.last_hit, p.last_by, p.indestructible) == (None, None, False)
    assert not {'last_hit', 'last_by', 'indestructible'} & set(vars(p))
    p.set_last_damage('Player_2', q)
    assert _one(p).last_damage() == ('Player_2', 'q') and (p.last_hit, p.last_by) == ('Player_2', 'q')
    assert (q.last_hit, q.last_by) == (None, None)                 # one a thing
    for field in ('last_hit', 'last_by', 'indestructible'):
        with pytest.raises(AttributeError):
            setattr(p, field, None)
    d = Observe.state(p)
    assert (d['last_hit'], d['last_by'], d['indestructible']) == ('Player_2', 'q', False)
    simact_object.unit_affect_object_panel_flags(s, 'UNIT_AFFECT_OBJECT_PANEL_FLAGS', ['p', 'Indestructible', 1], None)
    assert p.indestructible is True and _one(p).is_indestructible() and not q.indestructible
    was = p.hp
    simact_object.named_damage(s, 'NAMED_DAMAGE', ['p', '10'], None)
    assert p.hp == was - 10.0                       # a script's damage goes through the flag (engine_scripts7 panel)
    assert (p.last_hit, p.last_by) == (None, None)  # and comes from nobody
    q.set_last_damage('Player_2', p)
    simact_object.named_kill(s, 'NAMED_KILL', ['q'], None)
    assert not q.alive and (q.last_hit, q.last_by) == (None, None)     # the game's kill comes from nobody too
    bare = sim.Body('b', 'AlliedPowerPlant', 'Player_1', 0.0, 0.0)
    assert (bare.last_hit, bare.last_by, bare.indestructible) == (None, None, False)


def test_a_damage_kill_keeps_its_bits_readable_that_frame_on_the_module_step_b4a():
    import pytest
    import engine.script.act_object as simact_object
    import engine.script.cond_object as simcond_object
    from engine.ports.observe import Observe
    s = _world(('p', 'AlliedPowerPlant'), ('q', 'AlliedPowerPlant'), ('r', 'AlliedPowerPlant'))
    p, q, r = s.bodies['p'], s.bodies['q'], s.bodies['r']
    assert p.read_until is None and 'read_until' not in vars(p)
    with pytest.raises(AttributeError):
        p.read_until = 0
    for b in (p, q, r):
        b.status.add('IMMOBILE')
    simact_object.named_damage(s, 'NAMED_DAMAGE', ['p', '10'], None)
    assert p.alive and p.read_until is None                 # not killed: nothing kept
    simact_object.named_damage(s, 'NAMED_DAMAGE', ['p', str(p.hp + 1.0)], None)
    assert not p.alive and p.read_until == s.frame_now() == _one(p).bits_read_until()
    assert q.read_until is None                             # one a thing
    assert Observe.state(p)['read_until'] == s.frame_now()
    simact_object.named_kill(s, 'NAMED_KILL', ['q'], None)
    assert not q.alive and q.read_until is None             # a kill of any other kind keeps nothing
    has = simcond_object.unit_has_object_status
    assert has(s, 'UNIT_HAS_OBJECT_STATUS', ['p', 'IMMOBILE'])      # engine_sell e: a damage kill still reads
    assert not has(s, 'UNIT_HAS_OBJECT_STATUS', ['q', 'IMMOBILE'])  # its bits in that frame; a kill does not
    _one(p).set_bits_read_until(s.frame_now() - 1)                   # killed a frame before: reads false now
    assert not has(s, 'UNIT_HAS_OBJECT_STATUS', ['p', 'IMMOBILE'])
    _one(r).set_bits_read_until(s.frame_now())                       # a living thing reads its bits anyway
    assert has(s, 'UNIT_HAS_OBJECT_STATUS', ['r', 'IMMOBILE'])


def test_a_killed_prop_that_stays_is_counted_until_deleted():
    """engine_block gk: a killed GV_Ring02 (no die module) stays with NO_COLLISIONS and a status count sees it; a
    NAMED_DELETE after the kill takes it out of the count (review tt P2 #4)."""
    import engine.testing.small as simsmall
    from engine.script.cond_object import player_has_number_objects_with_object_status as count
    s = simsmall.small_world([('cage', 'GV_Ring02', 'Player_1', 300, 300)], model=False)
    cage, ask = s.bodies['cage'], ('Player_1', 2, 1, 'NO_COLLISIONS')
    s.destroy(cage, 'kill')
    assert not cage.alive and count(s, 'c', ask)
    s.delete(cage, 'delete')
    assert not count(s, 'c', ask) and count(s, 'c', ask[:2] + (0,) + ask[3:])
