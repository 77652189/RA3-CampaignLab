"""The AutoHealBehavior module (engine/modules/autoheal.py, step K1): its data read from the block, one module a
block on the things whose template has one, the gated blocks as the XML says (step K3: the upgrade trigger, the status
check; the ones healing others a gap), a thing taken out of the world off the schedule, and its state in the frame
record where the body's fields were. The healing itself: tests/test_simheal.py; on the bench: test_simbench.py."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simrecord  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.modules import autoheal  # noqa: E402

APOC = 'SovietAntiVehicleVehicleTech3'        # AutoHealBehavior: 2 points every 7 frames, 15 frames after a hurt
GUARDIAN = 'AlliedAntiVehicleVehicleTech1'    # one AutoHealBehavior: BaseVehicle's heroic heal
PLANT = 'AlliedPowerPlant'                    # none


def heals(b):
    """b's update modules of the autoheal cell (the Apocalypse has a toggle module too since step M5)."""
    return tuple(m for m in b.find(interfaces.Update) if m.PHASE == 'autoheal')


def test_the_apocalypse_reads_2_points_every_7_frames_15_after_a_hurt_the_guardians_is_gated_a_plant_has_none():
    s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0), ('g', GUARDIAN, 'Player_1', 300.0, 0.0),
                              ('p', PLANT, 'Player_1', 600.0, 0.0)])
    a, g, p = s.bodies['a'], s.bodies['g'], s.bodies['p']
    # Compiled Apocalypse: Upgrade_HeroicHeal (inactive, 3/.5s/1s), then Upgrade_PassiveHeal (active, 2/.5s/1s).
    heroic, m = heals(a)
    assert not heroic.data.active and heroic.data.trigger.by == {'Upgrade_Veterancy_HEROIC'}
    assert heroic.data.rule == (3, 7, 15)
    assert isinstance(m, autoheal.AutoHeal) and m.data.rule == (2, 7, 15) and m.thing is a and m.world is s.world
    (h,) = heals(g)                   # BaseVehicle's heroic heal: idle until Upgrade_Veterancy_HEROIC
    assert not h.data.active and h.data.trigger.by == {'Upgrade_Veterancy_HEROIC'} and h.data.rule[1:] == (7, 15)
    assert heals(p) == () and not [m for m in p.modules if isinstance(m, autoheal.AutoHeal)]   # (it unpacks, sells)


def test_the_block_is_read_as_the_xml_says_intervals_truncated_as_float32():
    d = autoheal.AutoHealData.parse(' InitiallyActive="false" HealingAmount="1" HealingDelay=".5s" '
                                    'StartHealingDelay="1s" ConflictsWith="X Y"',
                                    '<TriggeredBy>A</TriggeredBy><TriggeredBy>B</TriggeredBy>')
    assert d.rule == (1, 7, 15) and not d.active and d.trigger.by == {'A', 'B'} and d.trigger.conflicts == {'X', 'Y'}
    assert d.trigger.wants({'B'}) and not d.trigger.wants({'A', 'Y'}) and not d.trigger.wants(set())
    d = autoheal.AutoHealData.parse(' HealingAmount="3" HealingDelay=".25s" StartHealingDelay="0s"',
                                    '<ObjectStatusValidation RequiredStatus="GENERIC_TOGGLE_STATE" ForbiddenStatus="X" />')
    assert d.rule == (3, 3, 0) and d.active and d.required == {'GENERIC_TOGGLE_STATE'} and d.forbidden == {'X'}
    assert not d.unmodelled
    assert autoheal.frames('1.4s') == 20                # float32 1.4 x 15 = 20.99999.. (a double's int(21.0) is 21)
    for head in (' Radius="50"', ' AffectsWholePlayer="true"', ' HealOnlyIfNotInCombat="true"'):
        assert autoheal.AutoHealData.parse(' HealingAmount="5"' + head, '').unmodelled


def _hurt_guardian():
    s = simsmall.small_world([('g', GUARDIAN, 'Player_1', 0.0, 0.0)])
    g = s.bodies['g']
    (m,) = heals(g)
    s.world.schedule.run('autoheal', 0)
    g.damage(30)
    return s, g, m


def test_an_idle_heroic_heal_ignores_hurts_mends_two_frames_after_its_upgrade_and_stops_when_it_is_taken_back():
    s, g, m = _hurt_guardian()
    s.world.schedule.run('autoheal', 1)
    assert m.hurt is False and m.heal_at is None        # idle: the hurt was not heard
    s.world.frame = 30
    g.upgrades.add('Upgrade_Veterancy_HEROIC')
    s.modify(g)                                         # the upgrade broadcast (simmodifier.modify)
    assert m.upgraded and m.heal_at == 32               # two frames on (bench f)
    hp = g.hp
    s.world.schedule.run('autoheal', 31)
    assert g.hp == hp
    s.world.schedule.run('autoheal', 32)
    assert g.hp == hp + m.data.rule[0] and m.heal_at == 39
    g.upgrades.discard('Upgrade_Veterancy_HEROIC')
    s.modify(g)
    assert not m.upgraded and m.heal_at is None
    for f in range(33, 60):
        s.world.schedule.run('autoheal', f)
    assert g.hp == hp + m.data.rule[0]


def test_a_status_gated_heal_sleeps_while_the_status_fails_and_a_later_status_does_not_wake_it():
    s = simsmall.small_world([('t', 'JapanAntiVehicleVehicleTech1', 'Player_1', 0.0, 0.0)])   # the Tsunami
    t = s.bodies['t']
    # Compiled Tsunami: Upgrade_HeroicHeal (inactive), then ModuleTag_ActiveArmorHeal (GENERIC_TOGGLE_STATE, 3/.25s/0s).
    heroic, m = heals(t)
    assert not heroic.data.active and m.data.required == {'GENERIC_TOGGLE_STATE'}
    s.world.schedule.run('autoheal', 0)
    t.damage(76)
    s.world.schedule.run('autoheal', 0)
    hp = t.hp
    t.status = set(t.status) | {'GENERIC_TOGGLE_STATE'}
    for f in range(1, 10):
        s.world.schedule.run('autoheal', f)
    assert t.hp == hp                                   # asleep: the state on does not wake it
    s.world.frame = 10
    t.damage(1)                                         # a hurt does: no StartHealingDelay, the next frame
    s.world.schedule.run('autoheal', 10)
    s.world.schedule.run('autoheal', 11)
    assert t.hp == hp - 1 + 3 and m.next_ok == 14


def test_a_block_healing_others_is_a_gap_and_heals_nobody():
    s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0)])
    a = s.bodies['a']
    wide = autoheal.AutoHeal(a, autoheal.AutoHealData.parse(' HealingAmount="5" Radius="50"', ''), s.world)
    a.damage(10)
    assert wide.update(1) is interfaces.SLEEP and ('物体模块', 'AutoHealBehavior/Radius') in s.world.gaps


def test_a_thing_taken_out_of_the_world_leaves_the_schedule():
    s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0)])
    proto = s.proto('p', APOC, 'Player_1')             # the AI's figures body: made, then out of the registry
    assert 'p' not in s.bodies and proto.modules
    assert set(s.world.schedule.cells['autoheal']) == set(heals(s.bodies['a']))
    s.delete(s.bodies['a'], 'test')                     # (Sim.add refuses a living one's name)
    s.add('a', APOC, 'Player_1', 10.0, 0.0)            # a new body under the name: the old one leaves
    assert set(s.world.schedule.cells['autoheal']) == set(heals(s.bodies['a']))


def test_the_record_shows_the_modules_state_among_the_bodys_fields():
    s = simsmall.small_world([('a', APOC, 'Player_1', 0.0, 0.0)])
    b = s.bodies['a']
    assert 'heal_at' not in simrecord.body_state(b) and 'modules' not in simrecord.body_state(b)
    s.world.schedule.run('autoheal', 0)
    b.damage(10)
    s.world.schedule.run('autoheal', 1)
    d = simrecord.body_state(b)
    assert d['heal_at'] == 16 and d['hurt'] is False and d['hp'] == b.hp
