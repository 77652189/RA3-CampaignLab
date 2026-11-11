"""Whole bridge proxy only; generated segments and shared health remain gaps."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('manager_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_manager_body_script_damage_preserves_retail_bridge_proxy():
    """engine_managerbody:a: untouched / NAMED_DAMAGE 200, HP and live retail proxy."""
    import build
    import inventory
    import sim
    import simunits
    from parts import contract, merged

    # Reading a dependency's config must not promote its unimplemented behavior.
    assert inventory.NOTES[inventory.MODULE, 'Behaviors/BridgeBuilder'][0] == inventory.TODO
    assert inventory.NOTES[inventory.MODULE, 'Body/ManagerBody'][0] == inventory.GUESSED
    assert (inventory.MODULE, 'Body/ManagerBody') not in inventory.BENCHED_TESTS

    m, t, mod = build.resolve('engine_managerbody', 'a')
    assert len(mod) <= 15 and mod.isalnum()
    assert not contract(merged(m, t))
    # Both real bridge pairs, with start/end adjacent and matching retail flags.
    assert [o.flags for o in m.objects] == [16, 32, 16, 32]
    assert all(o.template == 'HB_Bridge_02' for o in m.objects)
    assert all(m.objects[k + 1].x - m.objects[k].x == 270 for k in (0, 2))
    s = sim.Sim(m, t).run(24)
    for start, end, wanted in ((2, 7, [100, 100, 11, 11]), (15, 23, [100, 80, 11, 11])):
        rows = [values for second, values in s.series if start <= second <= end]
        assert rows and all(row == wanted for row in rows), rows
    for role in ('control', 'hit'):
        body = s.body(m.role(role).name)
        assert body.alive and body.template == 'HB_Bridge_02'
        assert body.immortal and body.max_hp == 1000
        assert body.health == (100 if role == 'control' else 80)
    assert ('ManagerBody', 'HB_Bridge_02') in s.unmodeled
    # A child's explicit different body must stop ManagerBody inheritance.
    own = {'ManagerOverride': '<GameObject id="ManagerOverride" inheritFrom="HB_Bridge_02">'
                             '<Body><ActiveBody id="Body" MaxHealth="75" /></Body></GameObject>'}
    assert not simunits.manager_body('ManagerOverride', own)
    assert simunits.immortal_body('ManagerOverride', own) == (False, None)
    assert simunits.manager_proxy_health('ManagerOverride', own) is None

    # b: the same readings at 270 and 700; lethal script damage leaves 1%, alive.
    m, t, _ = build.resolve('engine_managerbody_b', 'b')
    assert not contract(merged(m, t))
    assert [m.objects[k + 1].x - m.objects[k].x for k in (0, 2)] == [270, 700]
    s = sim.Sim(m, t).run(34)
    for start, end, hp in ((2, 7, 100), (14, 17, 80), (24, 33, 1)):
        rows = [values for second, values in s.series if start <= second <= end]
        assert rows and all(row == [hp, hp, 11, 11] for row in rows), rows
    assert all(s.body(m.role(role).name).alive for role in ('control', 'hit'))
