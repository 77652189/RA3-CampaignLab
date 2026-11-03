"""信号烟 (A4's spawn hint, docs/design/flow/a4.md 出兵口提示): a prop that smokes for `life` seconds and goes, a column
of red smoke (retail's Amsterdam smoke, Amsterdam_01_Smoke6 -- the long one -- its sprites tinted red; the retail props'
own smoke is white and the beacon's flare and smoke did not draw on the bench 2026-11-02) on a flare's model, made by a
script on a team.

Published: what it is, params life.
"""
from parts import Unit

SIGNAL = 'CNV_SignalSmoke'

# r, g, b of the smoke's sprites (retail's are white, the texture its own grey)
RED = (1.6, 0.2, 0.12)


def particles(fx, color=RED, size=(80, 100), rise=1.0):
    r, g, b = color
    c = lambda frame, age: (f'<Color Frame="{frame}" RelativeAge="{age}"><Color b="{b}" g="{g}" r="{r}"/></Color>')
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<Includes>
		<Include source="art:fxfire04.xml" type="instance"/>
	</Includes>
	<FXParticleSystemTemplate ParticleTexture="FXFire04" PerParticleAttachedSystem="" Priority="ALWAYS_RENDER" Shader="ALPHA" SortLevel="2" Type="GPU_PARTICLE" id="{fx}">
		<Lifetime High="300" Low="300"/>
		<Size High="{size[1]}" Low="{size[0]}"/>
		<BurstDelay High="8" Low="4"/>
		<BurstCount High="1" Low="1"/>
		<Alphas>
			<Alpha Frame="2" High="0.85" Low="0.85" RelativeAge="9"/>
			<Alpha Frame="3" High="0.85" Low="0.85" RelativeAge="75"/>
			<Alpha Frame="4" High="0" Low="0" RelativeAge="100"/>
		</Alphas>
		<Colors>
			{c(1, 0)}
			{c(2, 15)}
			{c(3, 75)}
			{c(4, 100)}
		</Colors>
		<Physics>
			<Default>
				<VelocityDamping High="1" Low="1"/>
				<DriftVelocity x="0" y="0" z="{rise}"/>
			</Default>
		</Physics>
		<Draw>
			<Gpu FramesPerRow="6" SpeedMultiplier="0.1" TotalFrames="36"/>
		</Draw>
		<Volume>
			<Cylinder Radius="25">
				<Offset x="0" y="0" z="50"/>
			</Cylinder>
		</Volume>
		<Velocity>
			<Ortho>
				<Position>
					<x High="0.3" Low="0"/>
					<y High="0" Low="0"/>
					<z High="0" Low="0"/>
				</Position>
			</Ortho>
		</Velocity>
		<Event/>
		<Update>
			<Default Rotation="ROTATE_AROUND_VELOCITY">
				<SizeRateDamping High="0.99" Low="0.95"/>
				<AngleZ High="0.5" Low="-0.5"/>
				<AngularDamping High="1" Low="1"/>
				<AngularDampingXY High="1" Low="1"/>
			</Default>
		</Update>
	</FXParticleSystemTemplate>
</AssetDeclaration>
'''


def smoke(id=SIGNAL, life=11.0):
    fx = f'{id}_FX'
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<Tags></Tags>
	<Includes>
		<Include type="all" source="ART:GPFlareGeo.w3x" />
	</Includes>
	<GameObject id="{id}" Side="Neutral" EditorSorting="SYSTEM" TransportSlotCount="0" CommandSet="EmptyCommandSet"
		KindOf="IMMOBILE NO_COLLIDE INERT NOT_AUTOACQUIRABLE IGNORE_FOR_VICTORY CANNOT_BE_DETECTED RESIST_EMP"
		RadarPriority="NOT_ON_RADAR" EditorName="{id}">
		<DisplayName>Name:{id}</DisplayName>
		<ArmorSet Armor="NoArmor" />
		<Draws>
			<ScriptedModelDraw id="ModuleTag_Draw" OkToChangeModelColor="true">
				<ModelConditionState ParseCondStateType="PARSE_DEFAULT">
					<Model Name="GPFlareGeo" />
					<ParticleSysBone BoneName="None" FXParticleSystemTemplate="{fx}" />
				</ModelConditionState>
			</ScriptedModelDraw>
		</Draws>
		<Behaviors>
			<LifetimeUpdate id="ModuleTag_LifetimeUpdate" MinLifetime="{life:g}s" MaxLifetime="{life:g}s"
				DeathType="NORMAL" />
			<DestroyDie id="ModuleTag_DestroyDie">
				<DieMuxData DeathTypes="ALL" />
			</DestroyDie>
		</Behaviors>
		<Body>
			<PropBody id="ModuleTag_Body" />
		</Body>
		<Geometry IsSmall="true">
			<Shape Type="CYLINDER" MajorRadius="1.0" Height="1.0" />
		</Geometry>
		<VisionInfo VisionRange="0" ShroudClearingRange="0" />
	</GameObject>
</AssetDeclaration>
'''
    return Unit(id, xml, files={f'{fx}.xml': particles(fx)}, also=[f'{fx}.xml'], link=[f'FXParticleSystemTemplate:{fx}'],
                what=f'信号烟：冒红烟的信号弹，{life:g} 秒后消失', params=dict(life=life))
