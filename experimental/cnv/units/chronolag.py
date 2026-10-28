"""盟军「时滞炮车」 (the phase tank; docs/story/units.md, user 2026-10-20), moved here as it was worked out in
experimental/campaign/make_campnew35.py (its docstring and docs/plan.md hold the bench history): the Allied ground
siege piece. It deals no damage; a hit takes the target out of time -- a unit for 8 s, a structure for 15 s: it cannot
move or fire and cannot be hurt, then comes back as it was. One shot every 30 s. Siege by tempo.

A copy of the Guardian (its turret, painter toggle) with the cannon replaced by its phase shell: the Guardian's shell
flight, range 400, a warhead carrying 1 damage and the phase modifiers (UNATTACKABLE NO_ATTACK NON_AUTOACQUIRABLE
IN_STASIS, speed 0 %, the retail Chrono Rift shader). The 30 s cooldown is CampNew34's trick: the shot gives its owner
COOLDOWN_BIT for 30 s and the weapon does not fire under it. 展开 (deploy=True): the Guardian's painter toggle becomes
deploy / pack up; deployed (GENERIC_TOGGLE_STATE) it is IMMOBILE and the shell is its only weapon, packed it drives
and cannot fire.

Two traps from the bench (make_campnew35): with the phase modifiers only, the tank turned to its target and never
fired -- hence the 1 damage; and it fires only at what its own vision reaches (the Guardian sees 200) -- hence 450.

It wears the units line's look by default (dress): CNChrono, the Tripo model make_campchrono.py writes into the SDK's
Art (experimental/units). Moved 2026-10-27 by the units line (总控's one-off); the mechanics are the levels line's.

Published: abilities deploy = the toggle's command button (NAMED_USE_COMMANDBUTTON_ABILITY presses it).
"""
import os
import re

import make_campnew2 as c2
from parts import Unit

SAGE = os.path.join(c2.SDK, 'SageXML')
RETAIL = 'AlliedAntiVehicleVehicleTech1'        # the Guardian
TOGGLE_COMMAND = 'Command_ToggleTargetPainter'   # its painter toggle: deploy / pack up
COOLDOWN_BIT = 'DOES_CONTAIN_TIBERIUM'           # a C&C3 bit no RA3 XML uses (as in CampNew34)
PHASE_STATUS = 'UNATTACKABLE NO_ATTACK NON_AUTOACQUIRABLE IN_STASIS'
LOOK = 'CNChrono'                               # experimental/units/make_campchrono.py's model


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def nugget(modifier, include, owner=None):
    own = f'\n\t\t\t\tAttributeModifierOwnerName="{owner}"' if owner else ''
    return f'''			<AttributeModifierNugget Radius="10" PartitionFilterTestType="SPHERE"
				AttributeModifierName="{modifier}"{own}>
				<SpecialObjectFilter Rule="ANY" Relationship="ENEMIES" Include="{include}"/>
			</AttributeModifierNugget>
'''


def dress(unit, model=LOOK):
    """The tank wearing `model` (make_campnew23.unit_xml's swap): every model of the Guardian's, its still idle
    animation, no tread scrolling (the model has no tread texture of its own); its own production button and
    selection portrait (Button_<model> / Portrait_<model>, written into the SDK's Art by experimental/units/ui_kit.py);
    its name and description. Look only: weapons, turret, toggle, locomotor, health stay."""
    x = re.sub(r'(<Model\s+Name=")[^"]*(")', lambda m: m.group(1) + model.upper() + m.group(2), unit.xml)
    x = re.sub(r'AnimationName="[^"]*"', f'AnimationName="{model.upper()}_IDLE"', x)
    x = re.sub(r'\s*<TreadScrollingMap\b[^>]*/>', '', x)
    x = sub1(x, '<Includes>', f'<Includes>\n\t\t<Include type="all" source="ART:{model}.w3x" />'
                              f'\n\t\t<Include type="all" source="ART:{model}_IDLE.w3x" />'
                              f'\n\t\t<Include type="all" source="ART:{model}Button.xml" />'
                              f'\n\t\t<Include type="all" source="ART:{model}Portrait.xml" />')
    x = sub1(x, f'ButtonImage="Button_{RETAIL}_on"', f'ButtonImage="Button_{model}"')
    x = sub1(x, f'SelectPortrait="Portrait_{RETAIL}"', f'SelectPortrait="Portrait_{model}"')
    for k in ('Button', 'Portrait'):
        unit.link += [f'PackedTextureImage:{k}_{model}', f'Texture:{model}{k}_tex']
    # deployed (USER_1, the painter toggle's state) the Guardian lights its painter laser: a pink flare, drawn at the
    # middle of the hull (our model has no FX_Laser bone); the same looping flare in the phase shell's cyan
    glow = f'{unit.id}_DeployGlow'
    x, n = re.subn(r'FXParticleSystemTemplate="Allied_Target_Laser"', f'FXParticleSystemTemplate="{glow}"', x)
    assert n == 3, n
    x = sub1(x, '<Includes>', '<Includes>\n\t\t<Include type="instance" source="ART:FXLenzFlare03.xml" />')
    x = sub1(x, '</AssetDeclaration>', f'''	<FXParticleSystemTemplate IsEmitAboveGroundOnly="true" ParticleTexture="FXLenzFlare03"
		PerParticleAttachedSystem="" Priority="ALWAYS_RENDER" Type="GPU_PARTICLE" id="{glow}">
		<Lifetime High="5" Low="3"/>
		<Size High="75" Low="50"/>
		<BurstCount High="1" Low="1"/>
		<Colors>
			<Color Frame="1" RelativeAge="0">
				<Color b="1" g="0.90" r="0.35"/>
			</Color>
			<Color Frame="2" RelativeAge="50">
				<Color b="1" g="0.75" r="0.15"/>
			</Color>
			<Color Frame="3" RelativeAge="100">
				<Color b="0" g="0" r="0"/>
			</Color>
			<ColorScale High="2" Low="1"/>
		</Colors>
		<Physics>
			<Default>
				<VelocityDamping High="0.95" Low="0.9"/>
			</Default>
		</Physics>
		<Draw>
			<Gpu RandTex="1" SingleRow="1" SpeedMultiplier="1"/>
		</Draw>
		<Volume>
			<Point/>
		</Volume>
		<Velocity>
			<Ortho>
				<Position>
					<x High="0" Low="0"/>
					<y High="0" Low="0"/>
					<z High="0" Low="0"/>
				</Position>
			</Ortho>
		</Velocity>
		<Event/>
		<Update>
			<Default>
				<SizeRateDamping High="0.9" Low="0.85"/>
				<AngleZ High="7" Low="0"/>
				<AngularRateZ High="0.05" Low="-0.05"/>
				<AngularDampingXY High="1" Low="1"/>
			</Default>
		</Update>
	</FXParticleSystemTemplate>
</AssetDeclaration>''')
    unit.link.append(f'FXParticleSystemTemplate:{glow}')
    x = sub1(x, f'Description="Desc:{RETAIL}"', f'Description="Desc:{unit.id}"')
    x = sub1(x, f'TypeDescription="Type:{RETAIL}"', f'TypeDescription="Type:{unit.id}"')
    x = sub1(x, f'>Name:{RETAIL}<', f'>Name:{unit.id}<')
    assert set(re.findall(r'<Model\s+Name="([^"]*)"', x)) == {model.upper()}, re.findall(r'<Model\s+Name="([^"]*)"', x)
    unit.xml = x
    unit.strings.update({f'Name:{unit.id}': '时滞炮车', f'Type:{unit.id}': '时滞支援炮车',
                         f'Desc:{unit.id}': '不造成伤害：时滞弹把目标暂时推出时间，期间它不能移动、不能开火，也打不坏。'})
    unit.params['look'] = model
    return unit


def chronolag(id='CNV_ChronoLag', unit_time='8s', structure_time='15s', reload='30s', reach=400, vision=450,
              status=PHASE_STATUS, phase=True, deploy=True, model=LOOK):
    """make_campnew35's defaults, its environment switches as options: phase False = the same shell without the
    phase (its CNV_NO_PHASE control); deploy False = always armed (CNV_DEPLOY=0). model: its look (dress); None keeps
    the Guardian's."""
    m = dict(unit=f'AttributeModifier_{id}_Unit', structure=f'AttributeModifier_{id}_Structure',
             tag=f'AttributeModifier_{id}_Tag', deploy=f'AttributeModifier_{id}_Deploy',
             cooldown=f'AttributeModifier_{id}_Cooldown', shell=f'{id}_Shell', warhead=f'{id}_Warhead')
    hits = (nugget(m['unit'], 'VEHICLE INFANTRY') + nugget(m['structure'], 'STRUCTURE')) if phase else ''
    decl = f'''	<AttributeModifier id="{m['unit']}" Category="NONE" Duration="{unit_time}"
		StackingLimit="1" ObjectStatusToSet="{status}" Shader="ShaderOverride_ObjectsChronoRift">
		<Modifier Type="SPEED" Value="0%"/>
	</AttributeModifier>
	<AttributeModifier id="{m['structure']}" Category="NONE" Duration="{structure_time}"
		StackingLimit="1" ObjectStatusToSet="{status}" Shader="ShaderOverride_ObjectsChronoRift">
	</AttributeModifier>
	<AttributeModifier id="{m['tag']}" Category="NONE" Duration="0.1s">
	</AttributeModifier>
	<AttributeModifier id="{m['deploy']}" Category="NONE" ObjectStatusToSet="IMMOBILE">
		<Modifier Type="VISION" Value="100%"/>
	</AttributeModifier>
	<AttributeModifier id="{m['cooldown']}" Category="NONE" Duration="{reload}"
		StackingLimit="1" ObjectStatusToSet="{COOLDOWN_BIT}">
	</AttributeModifier>
	<WeaponTemplate id="{m['warhead']}" RadiusDamageAffects="ENEMIES"
		RequiredAntiMask="ANTI_GROUND ANTI_STRUCTURE ANTI_WATER" Flags="NOT_ATTRACTED_BY_MAGNETS">
		<Nuggets>
			<DamageNugget Damage="1.0" DamageType="CANNON" DamageFXType="ALLIED_CANNON" DeathType="EXPLODED"/>
{hits}		</Nuggets>
	</WeaponTemplate>
'''
    # the shell: the Guardian's cannon under our id, our range and warhead, the owner cooldown
    w = open(os.path.join(SAGE, 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
    s = re.search(rf'\t*<WeaponTemplate\s+id="{RETAIL}Cannon".*?</WeaponTemplate>\n', w, re.S).group(0)
    s = s.replace(f'id="{RETAIL}Cannon"', f'id="{m["shell"]}"')
    s = sub1(s, 'AttackRange="150.0"', f'AttackRange="{reach}.0"')
    s = sub1(s, 'CanFireWhileMoving="true"', f'CanFireWhileMoving="true"\n\t\tForbiddenFiringObjectStatus="{COOLDOWN_BIT}"')
    s = s.replace(f'WarheadTemplate="{RETAIL}Warhead"', f'WarheadTemplate="{m["warhead"]}"')
    s = sub1(s, '\t\t\t<InformTargetNugget />', nugget(m['tag'], 'VEHICLE INFANTRY STRUCTURE', owner=m['cooldown'])
             + '\t\t\t<InformTargetNugget />')

    x = open(os.path.join(SAGE, 'Allied', 'Units', RETAIL + '.xml'), encoding='utf-8').read()
    x = sub1(x, f'id="{RETAIL}"', f'id="{id}"')
    x = sub1(x, f'EditorName="{RETAIL}"', f'EditorName="{id}"')
    x = sub1(x, f'Template="{RETAIL}Cannon"', f'Template="{m["shell"]}"')
    x = sub1(x, 'VisionRange="200"', f'VisionRange="{vision}"')
    if deploy:
        x, n = re.subn(rf'Template="{m["shell"]}"\s*ForbiddenObjectStatus="GENERIC_TOGGLE_STATE"/>\s*<Weapon\s*'
                       rf'Ordering="SECONDARY_WEAPON"\s*Template="{RETAIL}TargetPainter"\s*'
                       r'ObjectStatus="GENERIC_TOGGLE_STATE"/>',
                       f'Template="{m["shell"]}"\n\t\t\t\t\t\tObjectStatus="GENERIC_TOGGLE_STATE"/>', x)
        assert n == 1, n
        x = sub1(x, 'AttributeModifier="AttributeModifier_TargetPaintVisionBonus"', f'AttributeModifier="{m["deploy"]}"')
    x = sub1(x, '</AssetDeclaration>', decl + s + '</AssetDeclaration>')
    u = Unit(id, x, link=[f'AttributeModifier:{v}' for k, v in m.items() if k not in ('shell', 'warhead')]
             + [f'WeaponTemplate:{m["shell"]}', f'WeaponTemplate:{m["warhead"]}'],
             names=dict(m, unit=id), abilities={'deploy': TOGGLE_COMMAND} if deploy else {},
             what=f'时滞炮车：守护者底，不造成伤害；时滞弹把目标推出时间（单位 {unit_time}、建筑 {structure_time}），'
                  f'{reload} 一发，射程 {reach}' + ('；deploy 展开后才能开炮、展开时不能动' if deploy else '')
                  + ('' if phase else '（对照：炮弹不带时滞）'),
             params=dict(unit_time=unit_time, structure_time=structure_time, reload=reload, reach=reach,
                         vision=vision, status=status, phase=phase, deploy=deploy))
    return dress(u, model) if model else u
