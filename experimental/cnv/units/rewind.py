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
