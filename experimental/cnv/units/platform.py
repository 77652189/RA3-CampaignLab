"""浪涌炮塔 (A8 海上发布会): the guns of a power platform, whose reach follows the swell. Retail's Soviet sentry gun
(SovietBaseDefenseGround: one weapon, a plain structure) under our id, with two upgrades that each apply an attribute
modifier: `high` (the swell is up: RANGE x`high`) and `low` (RANGE x`low`). The mission's scripts hand it one and take
the other away (devices/rhythm.py: NAMED_RECEIVE_UPGRADE / NAMED_REMOVE_UPGRADE); it starts with neither, so at its
base reach.

Published: names on / off = the two upgrade ids a rhythm device grants (swell up / swell down).

Not tested on the bench (2026-11-04, paper stage): whether an AttributeModifierUpgrade's modifier goes away when the
upgrade is removed (the device removes one and grants the other, so either way the later one stands only if the
modifiers replace each other -- the same Category), and whether RANGE moves what the turret may target as well as
what the weapon reaches. The first run of `a8 swell` (checks/a8.py) answers both.
"""
import os

import labpaths
from parts import Unit
from units import look

SAGE = labpaths.SDK3 + '/SageXML'


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


@look.named('tide_gun')
def tide_gun(id='CNV_TideGun', high=2.0, low=0.6, health=None):
    """The turret. high / low: the range multipliers of the two states (1.0 is retail's reach). health: its MaxHealth
    (None keeps retail's)."""
    up_on, up_off = f'Upgrade_{id}_High', f'Upgrade_{id}_Low'
    mod_on, mod_off = f'AttributeModifier_{id}_High', f'AttributeModifier_{id}_Low'
    x = open(os.path.join(SAGE, 'Soviet', 'Structures', 'SovietBaseDefenseGround.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="SovietBaseDefenseGround"', f'id="{id}"')
    x = sub1(x, 'EditorName="SovietBaseDefenseGround"', f'EditorName="{id}"')
    x = sub1(x, '<GameDependency>\n\t\t\t<RequiredObject>SovietPowerPlant</RequiredObject>\n\t\t</GameDependency>', '')
    x = sub1(x, '<Behaviors>', f'''<Behaviors>
			<AttributeModifierUpgrade id="ModuleTag_CNV_SwellHigh" AttributeModifier="{mod_on}">
				<TriggeredBy>{up_on}</TriggeredBy>
			</AttributeModifierUpgrade>
			<AttributeModifierUpgrade id="ModuleTag_CNV_SwellLow" AttributeModifier="{mod_off}">
				<TriggeredBy>{up_off}</TriggeredBy>
			</AttributeModifierUpgrade>''')
    x = sub1(x, '</AssetDeclaration>', f'''	<UpgradeTemplate id="{up_on}" Type="OBJECT"/>
	<UpgradeTemplate id="{up_off}" Type="OBJECT"/>
	<AttributeModifier id="{mod_on}" Category="NONE">
		<Modifier Type="RANGE" Value="{round(high * 100)}%"/>
	</AttributeModifier>
	<AttributeModifier id="{mod_off}" Category="NONE">
		<Modifier Type="RANGE" Value="{round(low * 100)}%"/>
	</AttributeModifier>
</AssetDeclaration>''')
    if health:
        import re
        x, n = re.subn(r'MaxHealth="\d+"', f'MaxHealth="{int(health)}"', x, count=1)
        assert n == 1, 'no MaxHealth'
    return Unit(id, x,
                link=[f'UpgradeTemplate:{up_on}', f'UpgradeTemplate:{up_off}', f'AttributeModifier:{mod_on}',
                      f'AttributeModifier:{mod_off}'],
                names={'on': up_on, 'off': up_off},
                what=f'海上平台的炮塔：原版哨戒炮，射程随浪（高 x{high:g}、低 x{low:g}）；任务脚本给它升级来切换',
                params=dict(high=high, low=low, health=health))
