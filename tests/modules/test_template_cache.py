"""The template reads are kept per process (simunits._xml, T9): the SDK's by name, a mission's by its file's text. Two
worlds built one after the other in one process, each overriding the same template its own way, each read their own
override -- through the unit's own file and through a GameObject that only another of the mission's files defines."""
import dataclasses

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import model  # noqa: E402
import parts  # noqa: E402
import simsmall  # noqa: E402
import simunits  # noqa: E402

UNIT = 'AlliedAntiInfantryVehicle'          # a retail unit a mission may override
BASE = 'CNVCacheBase'                       # a template defined only inside a mission file (not under its own key)


def _world(cost, base_cost):
    unit = (f'<GameObject id="{UNIT}" inheritFrom="{BASE}"><BuildCost Amount="{cost}"/></GameObject>\n'
            f'<GameObject id="{BASE}"><BuildCost Amount="{base_cost}"/></GameObject>')
    holder = f'<GameObject id="CNVCacheHolder"></GameObject>\n<GameObject id="{BASE}x"></GameObject>\n{unit}'
    m = dataclasses.replace(parts.Mission(name='T', map=simsmall.island, scripts=[]),
                            units=[model.Unit(id=UNIT, xml=unit), model.Unit(id='CNVCacheHolder', xml=holder)])
    return simsmall.sim.Sim(m, model=False)


def test_two_worlds_overriding_one_template_each_read_their_own():
    retail = simunits.production(UNIT)
    first, second = _world(111, 1000), _world(222, 2000)
    assert simunits.production(UNIT, first.own) == (111, 0.0)
    assert simunits.production(UNIT, second.own) == (222, 0.0)
    assert simunits.production(BASE, first.own)[0] == 1000          # found inside another of the mission's files
    assert simunits.production(BASE, second.own)[0] == 2000
    assert simunits.production(UNIT) == retail != (111, 0.0)        # the SDK's own answer untouched by either
    assert simunits.production(BASE) == (0, 0.0)                     # nor taught the mission-only template


def test_two_worlds_overriding_one_structure_each_get_their_command_set():
    structure = 'AlliedConstructionYard'
    mission = parts.Mission(name='T', map=simsmall.island, scripts=[])
    first, second = [
        simsmall.sim.Sim(dataclasses.replace(mission, units=[
            model.Unit(id=structure, xml=f'<GameObject id="{structure}" CommandSet="{commands}"></GameObject>'),
        ]), model=False)
        for commands in ('CacheCommandsFirst', 'CacheCommandsSecond')
    ]
    assert simunits.command_set(structure, own=first.own) == 'CacheCommandsFirst'
    assert simunits.command_set(structure, own=second.own) == 'CacheCommandsSecond'


def test_production_cache_reuses_only_template_data(monkeypatch):
    factory = 'CNVCacheFactory'
    base = 'CNVCacheFactoryBase'
    definition = f"""
        <GameObject id="{base}" CommandSet="CNVCacheNormal" BuildTime="3">
            <BuildCost Amount="450"/>
            <GameDependency><RequiredObject>Refinery</RequiredObject><NeededUpgrade>Tier</NeededUpgrade></GameDependency>
            <CommandSetUpgrade CommandSet="CNVCacheUpgraded"><TriggeredBy>Tier</TriggeredBy></CommandSetUpgrade>
            <TechUpgradeReceiver Radius="600" DistanceType="RECTANGULAR">
                <TriggeredBy>Tier</TriggeredBy><IncludeThing>Yard</IncludeThing>
            </TechUpgradeReceiver>
            <ProductionUpdate DoorOpeningTime="0.66s"/>
        </GameObject>
        <LogicCommandSet id="CNVCacheNormal"><Cmd>BuildTank</Cmd><Cmd>BuyTier</Cmd></LogicCommandSet>
        <LogicCommandSet id="CNVCacheUpgraded" inheritFrom="CNVCacheNormal"><Cmd>BuildPlane</Cmd></LogicCommandSet>
        <LogicCommand id="BuildTank" Type="UNIT_BUILD"><Object>Tank</Object></LogicCommand>
        <LogicCommand id="BuildPlane" Type="UNIT_BUILD"><Object>Plane</Object></LogicCommand>
        <LogicCommand id="BuyTier" Type="OBJECT_UPGRADE"><Upgrade>Tier</Upgrade></LogicCommand>
    """
    own = {factory: f'<GameObject id="{factory}" inheritFrom="{base}"></GameObject>', 'Library': definition}

    objects, upgrades = simunits.needs(factory, own)
    assert (objects, upgrades) == (['Refinery'], ['Tier'])
    objects.clear()
    upgrades.append('OtherTier')
    assert simunits.production(factory, own) == (450, 3.0)
    assert simunits.exit_of(factory, own) == ((0.0, 0.0), None, 10)
    receivers = simunits.tech_receivers(factory, own)
    assert receivers == [({'tier'}, 600.0, True, {'yard'})]
    receivers[0][3].clear()
    menu = simunits.menu(factory, own)
    assert menu == ['Tank']
    menu.clear()
    assert simunits.menu(factory, own, {'TIER'}) == ['Tank', 'Plane']

    def unexpected_read(*args, **kwargs):
        raise AssertionError('production data was read again')

    with monkeypatch.context() as patch:
        patch.setattr(simunits, '_inherited', unexpected_read)
        patch.setattr(simunits, '_commands', unexpected_read)
        assert simunits.needs(factory, own) == (['Refinery'], ['Tier'])
        assert simunits.production(factory, own) == (450, 3.0)
        assert simunits.exit_of(factory, own) == ((0.0, 0.0), None, 10)
        assert simunits.tech_receivers(factory, own) == [({'tier'}, 600.0, True, {'yard'})]
        assert simunits.menu(factory, own) == ['Tank']
        assert simunits.build_button(factory, 'Plane', own) is None
        assert simunits.build_button(factory, 'Plane', own, {'Tier'}) == 'BuildPlane'
        assert simunits.built(factory, 'BuildPlane', own, {'Tier'}) == 'Plane'
        assert simunits.upgrade_menu(factory, own) == [('Tier', 'OBJECT')]

    own['Library'] = definition.replace('Refinery', 'Outpost').replace('450', '300').replace('>Tank<', '>Scout<')
    assert simunits.needs(factory, own) == (['Outpost'], ['Tier'])
    assert simunits.production(factory, own) == (300, 3.0)
    assert simunits.menu(factory, own) == ['Scout']
