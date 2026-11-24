"""E206: the Tengu transform is a modelled player power, not a coverage gap (work/re/e206_transform.md). The player's
press against the script's: tests/modules/test_toggle.py."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_transform_gap_has_measured_player_route():
    spec = importlib.util.spec_from_file_location('coverage_e206', ROOT / 'experimental/cnv/simcoverage.py')
    sc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sc)
    assert ('命令', '技能 SpecialPower_JAIV_Transform') not in sc.KNOWN
    inf = sc.info('j7')
    assert sc.simunits.power_rules('JapanAntiInfantryVehicle', 'SpecialPower_JAIV_Transform', inf.own)
    own = {'JapanAntiInfantryVehicle': '<GameObject id="JapanAntiInfantryVehicle" '
           'inheritFrom="JapanAntiInfantryVehicle" />'}
    assert sc.simunits.power_rules('JapanAntiInfantryVehicle', 'SpecialPower_JAIV_Transform', own)['reload'] == 225
    assert sc.power_modelled('SpecialPower_JAIV_Transform', inf)
    assert not any(item.name == '技能 SpecialPower_JAIV_Transform' for item in sc.command_items(inf))
