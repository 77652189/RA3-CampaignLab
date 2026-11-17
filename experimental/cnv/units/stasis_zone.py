"""时停区物体 (A3 格林尼治时差, docs/engine/upgrades.md 5): the invisible object that is a time-stop zone. Retail's
IronCurtainEffect (no collision, unattackable, a prop body) with its lifetime and infantry-killing weapon dropped and its
aura replaced: every `refresh` it gives every infantry / vehicle / structure within `radius`, of any relationship to the
zone's owner (ALLIES ENEMIES NEUTRAL, as units/jammer.py's friends aura), the phase tank's out-of-time modifier
(units/chronolag.py PHASE_STATUS: UNATTACKABLE NO_ATTACK NON_AUTOACQUIRABLE IN_STASIS, SPEED 0 %, the Chrono Rift
shader) with a short Duration, so a unit no longer refreshed comes back at most `hold` later.

Put it where the zone is, or make it by script (CREATE_NAMED_ON_TEAM_AT_WAYPOINT: a zone made mid-mission works at
once); NAMED_DELETE it when time is up. The zone is a circle; a bigger or oddly shaped area is several objects
(devices/stasis.py does that). Whoever owns it, it stops everyone: the probe measured the enemy's (the engine line,
checks/engine_stasis.py: mine, theirs, neutral all stop; a chaser driving in stops; stopped units can neither be hurt
nor fire; the frozen leave the circle or the object goes -> back within `hold`; an order given while frozen is kept;
two frozen MCVs plug a 60-wide gap for good).

Not measured: aircraft (include has no AIRCRAFT), buildings placed inside, the edge (to a unit's centre or its
outline), whether a thawed unit remembers its target.

Published: params radius, hold, refresh. The model is retail's iron-curtain sphere (the probe's; the look is the unit
line's business).
"""
import os
import re

import labpaths
from parts import Unit
from units import chronolag

ID = 'CNV_StasisZone'
RADIUS = 200.0
HOLD = '1s'                 # the modifier's Duration: how long a unit stays stopped once the aura stops refreshing it
REFRESH = '0.25s'
STATUS = chronolag.PHASE_STATUS
INCLUDE = 'INFANTRY VEHICLE STRUCTURE'


def _sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def zone(id=ID, radius=RADIUS, hold=HOLD, refresh=REFRESH, include=INCLUDE):
    """The time-stop zone object. radius: the aura's reach from the object (a circle). hold: how long a unit stays
    stopped after it was last refreshed. include: the KindOf it stops."""
    mod = f'AttributeModifier_{id}'
    x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Soviet', 'Props', 'IronCurtainEffect.xml'),
             encoding='utf-8').read()
    x = _sub1(x, 'id="IronCurtainEffect"', f'id="{id}"')
    x = _sub1(x, 'EditorName="IronCurtainEffect"', f'EditorName="{id}"')
    x = _sub1(x, '<DisplayName>IronCurtainEffect</DisplayName>', f'<DisplayName>{id}</DisplayName>')
    for module, tag in (('LifetimeUpdate', 'ModuleTag_LifetimeUpdate'), ('FireWeaponUpdate', 'ModuleTag_FireWeaponUpdate'),
                        ('AttributeModifierAuraUpdate', 'ModuleTag_AttributeModifierAuraUpdate')):
        x, n = re.subn(rf'\s*<{module}\s+id="{tag}"(?:[^>]*/>|.*?</{module}>)', '', x, count=1, flags=re.S)
        assert n == 1, module
    # no UNATTACKABLE in StatusBitFlagsExclude (retail's has it): the modifier sets it, the next refresh would skip
    x = _sub1(x, '<Behaviors>', f'''<Behaviors>
			<AttributeModifierAuraUpdate id="ModuleTag_CNV_StasisAura" AttributeModifierName="{mod}"
				RefreshDelay="{refresh}" Range="{radius:g}" InitiallyActive="true" AllowSelf="false">
				<ObjectFilter Rule="ANY" Relationship="ALLIES ENEMIES NEUTRAL" Include="{include}"/>
			</AttributeModifierAuraUpdate>''')
    x = _sub1(x, '</AssetDeclaration>', f'''	<AttributeModifier id="{mod}" Category="NONE" Duration="{hold}"
		StackingLimit="1" ObjectStatusToSet="{STATUS}" Shader="ShaderOverride_ObjectsChronoRift">
		<Modifier Type="SPEED" Value="0%"/>
	</AttributeModifier>
</AssetDeclaration>''')
    return Unit(id, x, link=[f'AttributeModifier:{mod}'],
                what=f'时停区：隐形光环物体，{radius:g} 内敌我中立的步兵、车辆、建筑推出时间（不能动、不能开火、打不坏），'
                     f'离开或删掉物体后 {hold} 内恢复', params=dict(radius=radius, hold=hold, refresh=refresh))
