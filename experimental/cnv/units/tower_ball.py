"""原子球 (A9 布鲁塞尔, docs/story/plans/a9.md): one of the nine balls of the atomic tower. A plain building (a disc of
the bunker's logic without its garrison, units/icewall.wall) that is **invulnerable while dark** and hurts like any
building while lit. The mission's scripts hand it one of two upgrades and take the other away
(devices/rhythm.py: NAMED_RECEIVE_UPGRADE / NAMED_REMOVE_UPGRADE):

  off  (dark)  -- the upgrade whose attribute modifier is INVULNERABLE 100% plus retail's Iron Curtain status bits
                  (GlobalData/AttributeModifier.xml: no Duration here, so it lasts as long as the upgrade). Shots land on
                  the shield (the Iron Curtain shader) and do nothing: "白打了".
  on   (lit)   -- no modifier: the ball can be shot to pieces. A removed upgrade's modifier goes and a re-granted one
                  comes back (bench 2026-11-04, docs/engine/upgrades.md 1, for RANGE: the same modifier machinery).

It starts with neither, so the rhythm's first step ("begin": every unit of every group to `off`) darkens it; the device
does that at its start, so a ball of a not-yet-started device is plain vulnerable until then.

Bench-verified (engine line 44bb8f5, docs/engine/upgrades.md 4): INVULNERABLE alone through an AttributeModifierUpgrade
does NOT stop damage; the modifier also has to set retail Iron Curtain's status bits (ObjectStatusToSet="NO_BRIBE
UNDER_IRON_CURTAIN") -- then the dark ball takes no damage, taking the upgrade away makes it hurt-able, granting it
again makes it invulnerable again. The modifier must have no Duration (it would run out under the upgrade too).
`cnv_check a9 dark` is the same probe on the real ball (a sentry gun at a dark ball and at the lit one).

Published: names on / off = the two upgrade ids a rhythm device grants (lit / dark). params health, size.
"""
from parts import Unit
from units import icewall, look

SHADER = 'ShaderOverride_ObjectsIronCurtain'


@look.named('tower_ball')
def tower_ball(id='CNV_TowerBall', health=4000, size=90, shield=True):
    """health: MaxHealth. size: the disc's diameter. shield: the Iron Curtain shader on the dark ball (what shows it is
    dark: the player reads lit / dark off the ball itself)."""
    base = icewall.wall(id, length=size, thick=size, lifetime=None, health=health, shape='disc', model=None, look_as=None)
    up_on, up_off = f'Upgrade_{id}_Lit', f'Upgrade_{id}_Dark'
    mod_off = f'AttributeModifier_{id}_Dark'
    x = icewall.sub1(base.xml, '<Behaviors>', f'''<Behaviors>
			<AttributeModifierUpgrade id="ModuleTag_CNV_BallDark" AttributeModifier="{mod_off}">
				<TriggeredBy>{up_off}</TriggeredBy>
			</AttributeModifierUpgrade>''')
    shade = f'\n\t\tShader="{SHADER}"' if shield else ''
    x = icewall.sub1(x, '</AssetDeclaration>', f'''	<UpgradeTemplate id="{up_on}" Type="OBJECT"/>
	<UpgradeTemplate id="{up_off}" Type="OBJECT"/>
	<AttributeModifier id="{mod_off}" Category="NONE" ObjectStatusToSet="NO_BRIBE UNDER_IRON_CURTAIN"{shade}>
		<Modifier Type="INVULNERABLE" Value="100%"/>
	</AttributeModifier>
</AssetDeclaration>''')
    return Unit(id, x, link=[f'UpgradeTemplate:{up_on}', f'UpgradeTemplate:{up_off}', f'AttributeModifier:{mod_off}'],
                names={'on': up_on, 'off': up_off},
                what='原子球塔的球：暗着时无敌（炮打在护盾上），亮着时能打碎；任务脚本给它升级来切换亮暗',
                params=dict(health=health, size=size, shield=shield))
