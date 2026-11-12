"""The Liberty that will not die (A8, user 11-11): on a fatal blow it goes back to where it was BACK seconds ago, with
that health -- Tanya's time belt (AlliedCommandoTech1: StoreCurrentStateUpdate keeps her state every SleepTime for
MaxTime, ReconstituteStateSpecialAbility puts it back TimeStepsBack ago when its power fires) on the carrier.

The belt is a button; nothing in the data fires it on death. Here the body keeps the carrier at 1 hit point
(HighlanderBody: only UNRESISTABLE damage takes the last one) and the mission presses the button when its health is
down to 1 % (missions/rewind_bench.py). Engine line D's bench, checks/engine_rewind.py.

Published: abilities rewind = the belt's command (NAMED_USE_COMMANDBUTTON_ABILITY); params back, reload, body.
"""
from units import liberty as lib
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
WARP_SCALE = 3.0    # bench CampRwSSwap_mcp_1111_163719 s11.5: retail's FX_TanyaTimeWarp covered ~1/3 of the hull


def warp_fx(id, scale=WARP_SCALE):
    """Tanya's time-warp FX made `scale` times larger: retail's particle system Allied_Tanya_Chrono (20 lightning
    models, FXChronoSphereLightning) with StartSize / SizeRate times scale and its cylinder's lift too -- the FXList
    nugget has no size of its own (AssetTypeFXList.xsd). Returns (FXList id, {file: text})."""
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
				<Offset x="0" y="0" z="{15 * scale:g}"/>
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


def swap_carrier(id='CNV_LibRwS', wreck_id='CNV_LibRwW'):
    """The carrier of the show version, which stays on as "the new one" (round 49: its spot, facing and name are
    the old one's by construction; round 47 spawned a new one, which faced east whatever the old one did):
    ImmortalBody (bench CampRwSSwap_mcp_1111_163449: with retail's ActiveBody a 5200 blow at 56 % killed it before
    the mission's swap ran; ImmortalBody holds it at 1 hp, so the swap always runs). Its button `wreck` (an
    OCLSpecialPower, CreateLocation USE_OWNER_OBJECT) drops `wreck_id` on its spot and facing (CreateObject
    Disposition LIKE_EXISTING): the wreck plays the time-warp FX and crashes (wreck())."""
    u = lib.liberty(id, tag='RwS', drone_range=1, drones_home=False, model=None)
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
    u.what = '自由号（演出版回溯）：换船时它自己留下当新船，按钮 wreck 在原地按原朝向丢下一具残骸'
    return u


WRECK_LIFE = 1.5    # s: a once-a-second counter sees it alive, then retail's death plays (the crash)


def wreck(id='CNV_LibRwW', scale=WARP_SCALE, life=WRECK_LIFE):
    """The old carrier's wreck: the same Kirov with retail's body and death (it falls and crashes), no drones; the
    carrier's wreck button drops it on its spot (swap_carrier). It plays the time-warp FX `scale` times larger as it
    is made (FXListBehavior onCreate; scale 1: retail's FX_TanyaTimeWarp) and dies `life` s later (LifetimeUpdate:
    it has no name, so no NAMED_KILL)."""
    u = lib.liberty(id, tag='RwW', drone_range=1, drones_home=False, model=None)
    fx = 'FX_TanyaTimeWarp'
    if scale != 1:
        fx, files, link = warp_fx(id, scale)
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
