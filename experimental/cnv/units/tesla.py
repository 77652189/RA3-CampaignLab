"""磁暴坦克 (S7, campaign only; docs/story/units.md 4 and 5.3): retail's deleted Tesla tank
(SovietAntiVehicleVehicleTech2, "aka The Tesla Tank": TESLA 100, range 150, the Tesla trooper's surge toggle), taken
under our id -- retail ships its data in the SDK and the RVTeslaTank model in the game's art.

Retail's surge toggle only stops the tank: the Tesla trooper's FireWeaponUpdate, which fires the short circuit (EMP,
radius 50) while the toggle is on, was never given to the tank. fire=True adds the trooper's module.

Published: abilities surge (its toggle's command button: NAMED_USE_COMMANDBUTTON_ABILITY).
"""
import os

import make_campnew2 as c2
from parts import Unit

SAGE = os.path.join(c2.SDK, 'SageXML', 'Soviet', 'Units')
SURGE_COMMAND = 'Command_ToggleShortCircuitTank'
TOGGLE_END = '</ToggleStatusSpecialAbilityUpdate>'
FIRE = '''
			<FireWeaponUpdate
				id="ModuleTag_FireWeaponUpdate"
				FireInterval="0.13s"
				AliveOnly="true"
				ActiveWhenDisabled="HELD">
				<FireWeaponNugget
					WeaponName="SovietHeavyAntiVehicleInfantryShortCircuit"
					OneShot="false" />
				<ObjectStatusValidation
					RequiredStatus="GENERIC_TOGGLE_STATE" />
			</FireWeaponUpdate>'''                  # the Tesla trooper's (SovietHeavyAntiVehicleInfantry.xml)


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def tesla(id='CNV_TeslaTank', fire=True):
    x = open(os.path.join(SAGE, 'SovietAntiVehicleVehicleTech2.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="SovietAntiVehicleVehicleTech2"', f'id="{id}"')
    x = sub1(x, 'EditorName="SovietAntiVehicleVehicleTech2"', f'EditorName="{id}"')
    if fire:
        x = sub1(x, TOGGLE_END, TOGGLE_END + FIRE)
    return Unit(id, x, abilities={'surge': SURGE_COMMAND},
                what='磁暴坦克（原版删除单位）：磁暴线圈射程 150；surge 切换电涌（原地不动，半径 50 内敌方车辆瘫痪）')
