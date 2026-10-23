"""式神护卫 (J5, campaign only; docs/story/units.md 4: a folded-paper guard that takes the bullets meant for Yuriko;
work/story/unit_roster.md mechanism 11). One toggle: on guard, every enemy within `radius` aims at it instead, and
enemy shells in flight there bend onto it (retail's Assault Destroyer's black-hole armor: MagneticEffectUpdate, here
on a foot soldier, without the shield's scalable draw); its armor takes `armor` of the damage meanwhile.
Stand-in: the Imperial Warrior (art last).

Published: abilities guard = the toggle's command button (NAMED_USE_COMMANDBUTTON_ABILITY presses it).
"""
import os

import make_campnew2 as c2
from parts import Unit

SAGE = os.path.join(c2.SDK, 'SageXML', 'Japan', 'Units')
TOGGLE_POWER, TOGGLE_COMMAND = 'SpecialPower_ToggleTargetPainter', 'Command_ToggleTargetPainter'   # the Guardian's


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def shikigami(id='CNV_Shikigami', radius=200, armor='65%'):
    on, commands = f'AttributeModifier_{id}_Guard', f'{id}CommandSet'
    x = open(os.path.join(SAGE, 'JapanAntiInfantryInfantry.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="JapanAntiInfantryInfantry"', f'id="{id}"')
    x = sub1(x, 'EditorName="JapanAntiInfantryInfantry"', f'EditorName="{id}"')
    x = sub1(x, 'CommandSet="JapanAntiInfantryInfantryCommandSet"', f'CommandSet="{commands}"')
    x = sub1(x, '</Behaviors>', f'''	<SpecialPower id="ModuleTag_CNV_GuardTrigger" SpecialPowerTemplate="{TOGGLE_POWER}"/>
			<ToggleStatusSpecialAbilityUpdate id="ModuleTag_CNV_Guard" Options="RECONSTITUTE_STORED_COMMAND"
				SpecialPowerTemplate="{TOGGLE_POWER}">
				<ToggleState>
					<SkirmishAiInfo ToggleHint="TOGGLE_DEFAULT"/>
				</ToggleState>
				<ToggleState ObjectStatus="GENERIC_TOGGLE_STATE" AttributeModifier="{on}">
					<SkirmishAiInfo ToggleHint="TOGGLE_DEFENSE_PROTECT_OTHERS"/>
				</ToggleState>
			</ToggleStatusSpecialAbilityUpdate>
			<MagneticEffectUpdate id="ModuleTag_CNV_Draw" Radius="{radius}">
				<ObjectStatusValidation RequiredStatus="GENERIC_TOGGLE_STATE"/>
				<ObjectFilter Rule="ANY" Relationship="ENEMIES" Include="PROJECTILE SMALL_MISSILE INFANTRY VEHICLE"
					StatusBitFlagsExclude="MAGNETIZED"/>
			</MagneticEffectUpdate>
		</Behaviors>''')
    x = sub1(x, '</AssetDeclaration>', f'''	<AttributeModifier id="{on}" Category="NONE">
		<Modifier Type="ARMOR" Value="{armor}"/>
	</AttributeModifier>
	<LogicCommandSet id="{commands}">
		<Cmd>{TOGGLE_COMMAND}</Cmd>
		<Cmd>Command_AttackMove</Cmd>
	</LogicCommandSet>
</AssetDeclaration>''')
    return Unit(id, x, link=[f'AttributeModifier:{on}', f'LogicCommandSet:{commands}'],
                abilities={'guard': TOGGLE_COMMAND},
                what=f'式神护卫：帝国武士底；guard 切换护卫（{radius} 内敌人改打它、炮弹改道，护甲 {armor}）',
                params=dict(radius=radius, armor=armor))
