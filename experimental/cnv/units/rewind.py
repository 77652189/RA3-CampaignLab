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


# The show version (user 11-11: no real rewind): a new carrier spawned where the old one was, with the belt's
# time-warp FX as it is made, and a wreck of the old one that crashes there.
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


def swap_carrier(id='CNV_LibRwS', scale=WARP_SCALE):
    """The carrier of the show version: ImmortalBody (bench CampRwSSwap_mcp_1111_163449: with retail's ActiveBody
    a 5200 blow at 56 % killed it before the mission's swap ran; ImmortalBody holds it at 1 hp, so the swap always
    runs -- and deletes it: NAMED_KILL cannot kill this body), the time-warp FX `scale` times larger as it is made
    (FXListBehavior onCreate; scale 1: retail's FX_TanyaTimeWarp)."""
    u = lib.liberty(id, tag='RwS', drone_range=1, drones_home=False, model=None)
    u.xml = sub1(u.xml, '<ActiveBody\n\t\t\t\tid="ModuleTag_Body"', '<ImmortalBody\n\t\t\t\tid="ModuleTag_Body"')
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
		</Behaviors>''')
    u.what = f'自由号（演出版回溯）：出生时播谭雅时空腰带的特效（放大 {scale:g} 倍）'
    u.params.update(scale=scale)
    return u


def wreck(id='CNV_LibRwW'):
    """The old carrier's wreck: the same Kirov with retail's body and death (it falls and crashes), no drones; the
    mission spawns it where the old carrier was and kills it at once."""
    u = lib.liberty(id, tag='RwW', drone_range=1, drones_home=False, model=None)
    u.what = '自由号残骸：换船时原地生成并立即击毁，播原版坠毁'
    return u
