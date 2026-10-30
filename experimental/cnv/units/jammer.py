"""协调器干扰车 (S6, campaign only; docs/story/units.md 4, outline.md S6: it slows the Empire's mechs charging the launch
pad; work/story/unit_roster.md mechanism 4). A Soviet vehicle with one toggle: jamming, it stands still and every
unit within `radius`, ours too (docs/story/units.md 6), moves at `speed` of its own (AttributeModifierAuraUpdate, the
way the emperor's statue hastens friends; never CryoBeam_10, which freezes). Stand-in: the Sickle (art last).

Published: abilities jam = the toggle's command button (NAMED_USE_COMMANDBUTTON_ABILITY presses it).
"""
import os

import make_campnew2 as c2
from parts import Unit
from units import look

SAGE = os.path.join(c2.SDK, 'SageXML', 'Soviet', 'Units')
TOGGLE_POWER, TOGGLE_COMMAND = 'SpecialPower_ToggleTargetPainter', 'Command_ToggleTargetPainter'   # the Guardian's


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


@look.named('jammer')
def jammer(id='CNV_Jammer', radius=250, speed='40%', friends=True):
    """friends: our own units within `radius` are slowed too (the user's decision, 2026-10-22: where it stands becomes
    a choice -- in front of the line, not on our own counter-attack's way); False = enemies only."""
    on, slow, commands = f'AttributeModifier_{id}_On', f'AttributeModifier_{id}_Slow', f'{id}CommandSet'
    x = open(os.path.join(SAGE, 'SovietAntiInfantryVehicle.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="SovietAntiInfantryVehicle"', f'id="{id}"')
    x = sub1(x, 'EditorName="SovietAntiInfantryVehicle"', f'EditorName="{id}"')
    x = sub1(x, 'CommandSet="SovietAntiInfantryVehicleCommandSet"', f'CommandSet="{commands}"')
    x = sub1(x, '</Behaviors>', f'''	<SpecialPower id="ModuleTag_CNV_JamTrigger" SpecialPowerTemplate="{TOGGLE_POWER}"/>
			<ToggleStatusSpecialAbilityUpdate id="ModuleTag_CNV_Jam" Options="RECONSTITUTE_STORED_COMMAND"
				SpecialPowerTemplate="{TOGGLE_POWER}">
				<ToggleState>
					<SkirmishAiInfo ToggleHint="TOGGLE_DEFAULT"/>
				</ToggleState>
				<ToggleState ObjectStatus="GENERIC_TOGGLE_STATE" AttributeModifier="{on}">
					<SkirmishAiInfo ToggleHint="TOGGLE_DEFAULT"/>
				</ToggleState>
			</ToggleStatusSpecialAbilityUpdate>
			<AttributeModifierAuraUpdate id="ModuleTag_CNV_JamAura" AttributeModifierName="{slow}" RefreshDelay="0.5s"
				Range="{radius}" InitiallyActive="true" AllowSelf="false" RequiredObjectStatusFlags="GENERIC_TOGGLE_STATE">
				<ObjectFilter Rule="ANY" Relationship="{'ALLIES ENEMIES NEUTRAL' if friends else 'ENEMIES'}"
					Include="VEHICLE INFANTRY"/>
			</AttributeModifierAuraUpdate>
		</Behaviors>''')
    x = sub1(x, '</AssetDeclaration>', f'''	<AttributeModifier id="{on}" Category="NONE" ObjectStatusToSet="IMMOBILE"/>
	<AttributeModifier id="{slow}" Category="NONE" Duration="1s">
		<Modifier Type="SPEED" Value="{speed}"/>
	</AttributeModifier>
	<LogicCommandSet id="{commands}">
		<Cmd>{TOGGLE_COMMAND}</Cmd>
		<Cmd>Command_AttackMove</Cmd>
	</LogicCommandSet>
</AssetDeclaration>''')
    return Unit(id, x, link=[f'AttributeModifier:{on}', f'AttributeModifier:{slow}', f'LogicCommandSet:{commands}'],
                abilities={'jam': TOGGLE_COMMAND},
                what=f'协调器干扰车：镰刀底；jam 切换干扰（原地不动，{radius} 内' + ('所有单位' if friends else '敌方') +
                     f'速度 {speed}）',
                params=dict(radius=radius, speed=speed, friends=friends))
