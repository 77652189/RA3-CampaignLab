"""钻地运兵车 (S5, campaign only; docs/story/units.md 4, work/story/unit_roster.md mechanism 3): a Soviet transport
that drives underground. One toggle button: burrowed, it cannot be targeted or fire (UNATTACKABLE NO_ATTACK -- the
time-lag cannon showed UNATTACKABLE alone keeps it off every target list) and drives slower; surfaced, it is the
Bullfrog it was made from (five seats, its flak gun). Retail has no unit that moves underground: the tank hunter's
spider hole stops it (SpiderHoleUpdate), a submarine's SUBMERGED is a water locomotor's. Rough: no model under the
ground yet (art comes last).

Published: abilities burrow = the toggle's command button, unload = everyone out (NAMED_USE_COMMANDBUTTON_ABILITY
presses them).
"""
import os
import re

import make_campnew2 as c2
from parts import Unit
from units import look

SAGE = os.path.join(c2.SDK, 'SageXML', 'Soviet', 'Units')
TOGGLE_POWER, TOGGLE_COMMAND = 'SpecialPower_ToggleTargetPainter', 'Command_ToggleTargetPainter'   # the Guardian's
# everyone out where it stands (retail's Bullfrog has only the man cannon, which throws them at a point;
# NAMED_EXIT_BUILDING left the passengers aboard, bench 2026-10-22)
UNLOAD_COMMAND = 'Command_Evacuate'


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


@look.named('burrower')
def burrower(id='CNV_Burrower', speed='75%', status='UNATTACKABLE NO_ATTACK', payload=None):
    """speed: underground, of the surface speed. status: what being underground sets. payload: (template, count)
    aboard from the start (TransportContain's InitialPayload, as retail's campaign bombers carry paratroopers)."""
    under, commands = f'AttributeModifier_{id}_Under', f'{id}CommandSet'
    x = open(os.path.join(SAGE, 'SovietAntiAirShip.xml'), encoding='utf-8').read()
    if payload:
        x = sub1(x, '\t\t\t</TransportContain>', f'\t\t\t\t<InitialPayload Name="{payload[0]}" Count="{payload[1]}"/>\n'
                                                 '\t\t\t</TransportContain>')
    x = re.sub(r'\s*<GameObject\s+id="SovietAntiAirShip_Ground".*?</GameObject>', '', x, flags=re.S)
    x = sub1(x, 'id="SovietAntiAirShip"', f'id="{id}"')
    x = sub1(x, 'EditorName="SovietAntiAirShip"', f'EditorName="{id}"')
    x = sub1(x, 'CommandSet="SovietAntiAirShipCommandSet"', f'CommandSet="{commands}"')
    x = sub1(x, '</Behaviors>', f'''			<SpecialPower id="ModuleTag_CNV_BurrowTrigger" SpecialPowerTemplate="{TOGGLE_POWER}"/>
			<ToggleStatusSpecialAbilityUpdate id="ModuleTag_CNV_Burrow" Options="RECONSTITUTE_STORED_COMMAND"
				SpecialPowerTemplate="{TOGGLE_POWER}">
				<ToggleState>
					<SkirmishAiInfo ToggleHint="TOGGLE_DEFAULT"/>
				</ToggleState>
				<ToggleState ObjectStatus="GENERIC_TOGGLE_STATE" AttributeModifier="{under}">
					<SkirmishAiInfo ToggleHint="TOGGLE_DEFAULT"/>
				</ToggleState>
			</ToggleStatusSpecialAbilityUpdate>
		</Behaviors>''')
    x = sub1(x, '</AssetDeclaration>', f'''	<AttributeModifier id="{under}" Category="NONE" ObjectStatusToSet="{status}">
		<Modifier Type="SPEED" Value="{speed}"/>
	</AttributeModifier>
	<LogicCommandSet id="{commands}">
		<Cmd>{TOGGLE_COMMAND}</Cmd>
		<Cmd>{UNLOAD_COMMAND}</Cmd>
		<Cmd>Command_ActivateEjectPassengersSpecialPower</Cmd>
		<Cmd>Command_AttackMove</Cmd>
	</LogicCommandSet>
</AssetDeclaration>''')
    return Unit(id, x, link=[f'AttributeModifier:{under}', f'LogicCommandSet:{commands}'],
                abilities={'burrow': TOGGLE_COMMAND, 'unload': UNLOAD_COMMAND},
                what='钻地运兵车：牛蛙底，5 个座位；burrow 切换钻地（不能被瞄准、不能开火、变慢）/ 出地面；unload 原地卸兵',
                params=dict(speed=speed, status=status, payload=payload))
