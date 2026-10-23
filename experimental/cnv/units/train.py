"""装甲列车 (S2, campaign only, a scripted vehicle; docs/story/units.md 4 and 5: the "October" armoured train, a moving
fortress that a mission's scripts drive along the track; work/story/unit_roster.md mechanism 2). Retail's campaign
train (RussianTrain: the SUTrain_SKN model, the Sickle's locomotor, no weapon) under our id, armoured to `health`, with
a Tesla gun on a fixed mount that fires all round and on the move (the Tesla tank's gun, AcceptableAimDelta 360d --
the train has no turret -- and `reach`; retail's coil gun cannot fire while moving). The track is the mission's: a
route of waypoints it is sent along one after another (missions/train_bench.py).

Not settled: the player aiming its guns but never steering it; cars that come off.

Published: what and params; no ability (it is sent: MOVE_NAMED_UNIT_TO).
"""
import os
import re

import make_campnew2 as c2
from parts import Unit

SAGE = c2.SDK + '/SageXML'


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def gun(id, reach):
    w = open(os.path.join(SAGE, 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
    m = re.search(r'<WeaponTemplate\s+id="SovietAntiVehicleVehicleTech2TeslaGun".*?</WeaponTemplate>', w, flags=re.S)
    g = sub1(m.group(0), 'id="SovietAntiVehicleVehicleTech2TeslaGun"', f'id="{id}"')
    g = sub1(g, 'AttackRange="150.0"', f'AttackRange="{reach}.0"')
    return sub1(g, 'AcceptableAimDelta="20d"', 'AcceptableAimDelta="360d"')


def train(id='CNV_Train', health=3000, reach=250):
    weapon = f'{id}_TeslaGun'
    x = open(os.path.join(SAGE, 'Soviet', 'Units_Campaign', 'RussianTrain.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="RussianTrain"', f'id="{id}"')
    x = sub1(x, 'EditorName="RussianTrain"', f'EditorName="{id}"')
    x = sub1(x, 'MaxHealth="300"', f'MaxHealth="{health}"')
    x = re.sub(r'\s*<GameDependency>.*?</GameDependency>', '', x, count=1, flags=re.S)
    # retail's prop train picks no targets of its own; ours must, on the move (bench 2026-10-22: with false it never
    # fired at the conscripts shooting it from 150 away)
    x = sub1(x, 'CanPickDynamicTargets="false"', 'CanPickDynamicTargets="true"')
    # sees as far as it shoots: with retail's 500 it went for enemies 300 away while still standing at its start
    x = sub1(x, 'VisionRange="500"', f'VisionRange="{reach}"')
    x = sub1(x, '<Behaviors>', f'''<Behaviors>
			<WeaponSetUpdate id="ModuleTag_CNV_Guns">
				<WeaponSlotHardpoint ID="1">
					<Weapon Ordering="PRIMARY_WEAPON" Template="{weapon}"/>
				</WeaponSlotHardpoint>
			</WeaponSetUpdate>''')
    x = sub1(x, '</AssetDeclaration>', f'\t{gun(weapon, reach)}\n</AssetDeclaration>')
    return Unit(id, x, link=[f'WeaponTemplate:{weapon}'],
                what=f'装甲列车：原版战役火车，{health} 血，固定挂点磁暴炮（射程 {reach}，全向、边走边打）；由任务脚本沿路点开',
                params=dict(health=health, reach=reach))
