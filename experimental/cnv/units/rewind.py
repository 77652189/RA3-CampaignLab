"""The Liberty that will not die (A8, user 11-11): on a fatal blow it goes back to where it was BACK seconds ago, with
that health -- Tanya's time belt (AlliedCommandoTech1: StoreCurrentStateUpdate keeps her state every SleepTime for
MaxTime, ReconstituteStateSpecialAbility puts it back TimeStepsBack ago when its power fires) on the carrier.

The belt is a button; nothing in the data fires it on death. Here the body keeps the carrier at 1 hit point
(HighlanderBody: only UNRESISTABLE damage takes the last one) and the mission presses the button when its health is
down to 1 % (missions/rewind_bench.py). Engine line D's bench, checks/engine_rewind.py.

Published: abilities rewind = the belt's command (NAMED_USE_COMMANDBUTTON_ABILITY); params back, reload, body.
"""
import os
import re
import types

from units import liberty as lib
from units.icewall import cut
from units.liberty import sub1


def rewind(id='CNV_LibRw', back='3s', reload='20s', body='HighlanderBody', store='5s', every='0.25s', probe=0):
    """body: the carrier's body module (ActiveBody: retail's, it dies). back: TimeStepsBack; store / every: the
    StoreCurrentStateUpdate's MaxTime / SleepTime (retail Tanya: 10 s back, 5 s kept, every 0.25 s). probe: that
    many lines of ra3ext's CNVProbe (its position every frame it changes; the mission needs ext=True), 0: none."""
    u = lib.liberty(id, tag='Rw', drone_range=1, drones_home=False, model=None)
    ids = dict(belt=f'SpecialPower_{id}_Rewind', belt_cmd=f'Command_{id}_Rewind', belt_button=f'Button_{id}_Rewind')
    x = u.xml
    x = sub1(x, '<ActiveBody\n\t\t\t\tid="ModuleTag_Body"', f'<{body}\n\t\t\t\tid="ModuleTag_Body"')
    x = sub1(x, '\t\t</Behaviors>', f'''			<SpecialPower id="ModuleTag_CNV_Rewind" SpecialPowerTemplate="{ids['belt']}"
				UpdateModuleStartsAttack="false" DisabledTypesToIgnore="HELD PARALYZED"/>
			<ReconstituteStateSpecialAbility id="ModuleTag_CNV_RewindUpdate" Options="RECONSTITUTE_STORED_COMMAND"
				SpecialPowerTemplate="{ids['belt']}" UpdateModuleId="ModuleTag_CNV_RewindStore" TimeStepsBack="{back}"
				LeavePositionFX="FX_TanyaTimeWarp" ReturnPositionFX="FX_TanyaTimeWarp"
				DisabledTypesToProcess="HELD PARALYZED"/>
			<StoreCurrentStateUpdate id="ModuleTag_CNV_RewindStore" SleepTime="{every}" MaxTime="{store}"/>
''' + (f'''			<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="150" MaxFrames="{probe}"/>
''' if probe else '') + '''		</Behaviors>''')
    x = sub1(x, f'<Cmd>Command_AttackMove</Cmd>', f'<Cmd>Command_AttackMove</Cmd>\n\t\t<Cmd>{ids["belt_cmd"]}</Cmd>')
    x = sub1(x, '</AssetDeclaration>', f'''	<SpecialPowerTemplate id="{ids['belt']}" ReloadTime="{reload}" TargetType="NONE"
		WaypointModeTerminal="false"/>
	<LogicCommand Type="SPECIAL_POWER" id="{ids['belt_cmd']}">
		<SpecialPower>{ids['belt']}</SpecialPower>
	</LogicCommand>
</AssetDeclaration>''')
    u.xml = x
    ui = next(iter(u.files))
    u.files[ui] = sub1(u.files[ui], '</AssetDeclaration>', f'''	<UnitAbilityButtonTemplate id="{ids['belt_button']}" LogicCommand="{ids['belt_cmd']}">
		<Data>
			<SpecialPower StateData="ButtonStateAbilityTimeBelt"/>
		</Data>
	</UnitAbilityButtonTemplate>
</AssetDeclaration>''')
    u.link += [f'SpecialPowerTemplate:{ids["belt"]}', f'LogicCommand:{ids["belt_cmd"]}',
               f'UnitAbilityButtonTemplate:{ids["belt_button"]}']
    u.names.update(ids)
    u.abilities['rewind'] = ids['belt_cmd']
    u.what = f'不死的自由号（试验）：{body}，rewind 退回 {back} 前的位置和血量（谭雅时空腰带的两个模块）'
    u.params.update(back=back, reload=reload, body=body)
    return u


# The show version (user 11-11: no real rewind): the carrier stays on as "the new one" and drops a wreck of the old
# one on its spot, which plays the belt's time-warp FX as it is made and crashes there.
# Round 53: both wear the carrier's real look (liberty.dress; user: the Kirov's model shows nothing of the real build)
# and the FX's size follows the model's, not a guess: the lightning mesh FXCHRONOSPHERELIGHTNING.SPHERE03 is 47.1
# across at StartSize 1 (retail_mesh bounding box; the Kirov SUBOMBERAIRCRAFT_SKN is 73 x 41 x 45); CNLiberty.w3x's
# platform is 280 x 274 across, its body 0..156 up (the statue to 215). So scale = width / 47.1, the ball centred at
# half the body's height.
LIGHTNING_D = 47.1                  # the time-warp lightning's diameter at size 1
HULL_W, HULL_H = 280.0, 156.3       # CNLiberty: platform width, body height (its origin at the bottom)
WARP_FILL = 1.5     # round 54: at width / 47.1 (5.94) the ball covered ~2/3 of the deck (bench CampRwSWreck_mcp_1111_201655
                    # frame 21: the drawn lightning reaches less far than the mesh's box) -- so 1.5 times that
WARP_SCALE = round(HULL_W / LIGHTNING_D * WARP_FILL, 2)     # 8.92 (round 53: 5.94; round 47-49: 3, on the Kirov)
WARP_LIFT = round(HULL_H / 2, 1)


def warp_fx(id, scale=WARP_SCALE, lift=WARP_LIFT):
    """Tanya's time-warp FX made `scale` times larger: retail's particle system Allied_Tanya_Chrono (20 lightning
    models, FXChronoSphereLightning) with StartSize / SizeRate times scale -- the FXList nugget has no size of its
    own (AssetTypeFXList.xsd) -- and its cylinder `lift` above the object (None: retail's 15, times scale).
    Returns (FXList id, {file: text})."""
    lift = 15 * scale if lift is None else lift
    ps, fx = f'{id}_Chrono', f'FX_{id}_Warp'
    v = lambda a: f'<x High="{a:g}" Low="{a:g}"/>\n\t\t\t\t\t<y High="{a:g}" Low="{a:g}"/>\n\t\t\t\t\t<z High="{a:g}" Low="{a:g}"/>'
    return fx, {f'{ps}.xml': f'''<?xml version="1.0" encoding="UTF-8"?>
<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<Includes>
		<Include source="art:fxchronospherelightning.w3x" type="instance"/>
	</Includes>
	<FXParticleSystemTemplate Drawable="FXChronoSphereLightning" PerParticleAttachedSystem="" Priority="ALWAYS_RENDER" Shader="W3D_ALPHA" SystemLifetime="1" Type="DRAWABLE" id="{ps}">
		<Lifetime High="15" Low="10"/>
		<BurstCount High="20" Low="20"/>
		<Alphas>
			<Alpha Frame="1" High="1" Low="1" RelativeAge="0"/>
			<Alpha Frame="2" High="0" Low="0" RelativeAge="100"/>
		</Alphas>
		<Physics>
			<Default>
				<VelocityDamping High="1" Low="1"/>
			</Default>
		</Physics>
		<Draw>
			<RenderObject>
				<ObjectSet/>
				<ObjectSet/>
				<ObjectSet/>
			</RenderObject>
		</Draw>
		<Volume>
			<Cylinder>
				<Offset x="0" y="0" z="{lift:g}"/>
			</Cylinder>
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
			<RenderObject Rotation="ROTATE_IN_WORLD_SPACE">
				<AngleX High="7" Low="0"/>
				<AngleY High="7" Low="0"/>
				<AngleZ High="7" Low="-7"/>
				<AngularDamping High="1" Low="1"/>
				<StartSize>
					{v(scale)}
				</StartSize>
				<SizeRate>
					{v(-0.1 * scale)}
				</SizeRate>
				<SizeDamping>
					<x High="1.1" Low="0.5"/>
					<y High="1.1" Low="0.5"/>
					<z High="1.1" Low="0.5"/>
				</SizeDamping>
			</RenderObject>
		</Update>
	</FXParticleSystemTemplate>
	<FXList id="{fx}">
		<NuggetList>
			<Sound Value="ALL_Commando_TimeBeltMS"/>
			<ParticleSystem Particle="{ps}" OrientToObject="true">
				<Offset x="0.0" y="0.0" z="0.0"/>
			</ParticleSystem>
		</NuggetList>
	</FXList>
</AssetDeclaration>
'''}, [f'FXParticleSystemTemplate:{ps}', f'FXList:{fx}']


def swap_carrier(id='CNV_LibRwS', wreck_id='CNV_LibRwW', model=lib.LOOK[0]):
    """The carrier of the show version, which stays on as "the new one" (round 49: its spot, facing and name are
    the old one's by construction; round 47 spawned a new one, which faced east whatever the old one did):
    ImmortalBody (bench CampRwSSwap_mcp_1111_163449: with retail's ActiveBody a 5200 blow at 56 % killed it before
    the mission's swap ran; ImmortalBody holds it at 1 hp, so the swap always runs). Its button `wreck` (an
    OCLSpecialPower, CreateLocation USE_OWNER_OBJECT) drops `wreck_id` on its spot and facing (CreateObject
    Disposition LIKE_EXISTING): the wreck plays the time-warp FX and crashes (wreck()). Round 54: its deck jump
    (liberty's TeleportSpecialAbilityUpdate, published `jump`) takes it aside off the wreck and back -- reload 1 s
    and a deck of radius 1, so it carries no one along; the wreck left out of the deck's filter (riders: an
    ExcludeThing): bench CampRwSJump_mcp_1111_203929 frames 18-20, it sat at distance 0, ours and a VEHICLE, and
    jumped along and fell at the far spot. model: its look (dress; None: the Kirov's)."""
    u = lib.liberty(id, tag='RwS', drone_range=1, drones_home=False, model=model, reload='1s', deck_radius=1,
                    riders=wreck_id)
    u.xml = sub1(u.xml, '<ActiveBody\n\t\t\t\tid="ModuleTag_Body"', '<ImmortalBody\n\t\t\t\tid="ModuleTag_Body"')
    ids = dict(shed=f'SpecialPower_{id}_Wreck', shed_cmd=f'Command_{id}_Wreck', shed_button=f'Button_{id}_Wreck',
               shed_ocl=f'OCL_{id}_Wreck')
    u.xml = sub1(u.xml, '\t\t</Behaviors>', f'''			<OCLSpecialPower id="ModuleTag_CNV_Wreck" SpecialPowerTemplate="{ids['shed']}"
				UpdateModuleStartsAttack="false" AvailableAtStart="true" OCL="{ids['shed_ocl']}"
				CreateLocation="USE_OWNER_OBJECT"/>
		</Behaviors>''')
    u.xml = sub1(u.xml, '<Cmd>Command_AttackMove</Cmd>', f'<Cmd>Command_AttackMove</Cmd>\n\t\t<Cmd>{ids["shed_cmd"]}</Cmd>')
    u.xml = sub1(u.xml, '</AssetDeclaration>', f'''	<ObjectCreationList id="{ids['shed_ocl']}">
		<CreateObject Options="IGNORE_ALL_OBJECTS" Disposition="LIKE_EXISTING RELATIVE_ANGLE" DispositionAngle="0d"
			Count="1">
			<CreateObject>{wreck_id}</CreateObject>
		</CreateObject>
	</ObjectCreationList>
	<SpecialPowerTemplate id="{ids['shed']}" ReloadTime="1s" TargetType="NONE" WaypointModeTerminal="false"/>
	<LogicCommand Type="SPECIAL_POWER" id="{ids['shed_cmd']}">
		<SpecialPower>{ids['shed']}</SpecialPower>
	</LogicCommand>
</AssetDeclaration>''')
    ui = next(iter(u.files))
    u.files[ui] = sub1(u.files[ui], '</AssetDeclaration>', f'''	<UnitAbilityButtonTemplate id="{ids['shed_button']}" LogicCommand="{ids['shed_cmd']}">
		<Data>
			<SpecialPower StateData="ButtonStateAbilityTimeBelt"/>
		</Data>
	</UnitAbilityButtonTemplate>
</AssetDeclaration>''')
    u.link += [f'ObjectCreationList:{ids["shed_ocl"]}', f'SpecialPowerTemplate:{ids["shed"]}',
               f'LogicCommand:{ids["shed_cmd"]}', f'UnitAbilityButtonTemplate:{ids["shed_button"]}']
    u.names.update(ids)
    u.abilities['wreck'] = ids['shed_cmd']
    u.what = '自由号（演出版回溯）：换船时它自己留下当新船，按钮 wreck 在原地按原朝向丢下一具残骸，jump 跳开再跳回'
    return u


WRECK_LIFE = 1.5    # s: a once-a-second counter sees it alive, then retail's death plays (the crash)


KIROV_FALL = 'SUBomberAircraft_Dying_OCL'      # retail Kirov's death: its falling body + its flying parts
FALL_SRC = os.path.join(lib.SAGE, 'Soviet', 'Props', 'SovietBomberAircraft_Dying.xml')


def falling(id, model=lib.LOOK[0]):
    """The falling body of a dressed carrier: retail's SovietBomberAircraft_Dying (ProjectileUpdate MoveToGround:
    it sinks at up to 2.5 a frame; its fire / smoke particle systems; on the ground FX_SOV_KirovCrash, the death
    weapon, ShipSlowDeath 10 s) drawing `model` with statue and rings (liberty.dress) in place of the Kirov's skinned
    dying mesh and its nose-down animation -- so it falls level. Its ground wreck SovietBomberAircraft_Collapse (a
    Kirov) is left out. Returns (OCL id, {file: text}, link) -- the OCL replaces the Kirov's death OCL, without its
    debris (the gondola and engines)."""
    with open(FALL_SRC, encoding='utf-8') as f:
        x = f.read()
    x = sub1(x, 'id="SovietBomberAircraft_Dying"', f'id="{id}"')
    x = sub1(x, 'EditorName="SovietBomberAircraft_Dying"', f'EditorName="{id}"')
    fires = ''.join(re.findall(r'\s*<ParticleSysBone.*?/>', x, flags=re.S))
    x = re.sub(r'<Include\s+type="all"\s+source="ART:SUBomberAircraft_(?:Dying_SKN\.w3x|DYING\.w3x|D\.xml)"\s*/>',
               '', x)
    shim = types.SimpleNamespace(xml=x, params={})
    x = lib.dress(shim, model).xml
    x = sub1(x, '<WeaponLaunchBone WeaponSlotType="PRIMARY_WEAPON" BoneName="FX_WEAPON" />', fires.strip())
    x = cut(x, 'CreateObjectDie', 'ModuleTag_CreateObjectDie')
    assert 'SUBomberAircraft' not in x, re.findall(r'.{40}SUBomberAircraft.{40}', x)
    ocl = f'OCL_{id}'
    x = sub1(x, '</AssetDeclaration>', f'''	<ObjectCreationList id="{ocl}">
		<CreateObject Options="IGNORE_ALL_OBJECTS" Disposition="LIKE_EXISTING INHERIT_VELOCITY" Count="1"
			VelocityScale="1.0" MinForceMagnitude="1.0" MaxForceMagnitude="1.0" MinForcePitch="90d" MaxForcePitch="75d">
			<CreateObject>{id}</CreateObject>
		</CreateObject>
	</ObjectCreationList>
</AssetDeclaration>''')
    return ocl, {f'{id}.xml': x}, [f'GameObject:{id}', f'ObjectCreationList:{ocl}']


def wreck(id='CNV_LibRwW', scale=WARP_SCALE, life=WRECK_LIFE, model=lib.LOOK[0]):
    """The old carrier's wreck: the carrier with retail's body and death (it falls and crashes), no drones; the
    carrier's wreck button drops it on its spot (swap_carrier). It plays the time-warp FX `scale` times larger as it
    is made (FXListBehavior onCreate; scale 1: retail's FX_TanyaTimeWarp) and dies `life` s later (LifetimeUpdate:
    it has no name, so no NAMED_KILL). model: its look (None: the Kirov's, falling as the Kirov does); dressed, it
    falls as falling() (the Kirov's way, our model)."""
    u = lib.liberty(id, tag='RwW', drone_range=1, drones_home=False, model=model)
    if model:
        ocl, files, link = falling(f'{id}_Fall', model)
        u.xml = sub1(u.xml, f'CreationList="{KIROV_FALL}"', f'CreationList="{ocl}"')
        u.files.update(files)
        u.also += list(files)
        u.link += link
    fx = 'FX_TanyaTimeWarp'
    if scale != 1:
        fx, files, link = warp_fx(id, scale, WARP_LIFT if model else None)
        u.files.update(files)
        u.also += list(files)
        u.link += link
    u.xml = sub1(u.xml, '\t\t</Behaviors>', f'''			<FXListBehavior id="ModuleTag_CNV_RewindFX">
				<DieMuxData DeathTypes="ALL"/>
				<Event Index="onCreate" FX="{fx}"/>
			</FXListBehavior>
			<LifetimeUpdate id="ModuleTag_CNV_WreckLife" MinLifetime="{life:g}s" MaxLifetime="{life:g}s"/>
		</Behaviors>''')
    u.what = f'自由号残骸：旧船按钮原地丢下，播谭雅时空腰带特效（放大 {scale:g} 倍），{life:g} 秒后播原版坠毁'
    u.params.update(scale=scale, life=life)
    return u
