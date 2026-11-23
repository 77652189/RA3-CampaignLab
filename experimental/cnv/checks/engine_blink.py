"""Engine extension D, beacon trooper right-click -> blink probe (work/re/d_beacon1_rightclick.md), step 1: what the
human player's move and point-ability messages look like on ra3ext's command walk. The host: the beacon trooper
(units/beacon.py, a ground-point ability the player clicks) with ra3ext's read-only CNVBlink, which turns the walk on
for every player's messages (the `pcmd:` lines of ra3ext's log; what each message holds: the private notes).
No expectations: the simulator plays no bench clicks.
  read  select him (a box), right-click a point, the ability on the shore beside a Peacekeeper in the shallows, a
        second right-click
  pull  select him, the ability aimed on four Guardians on land ~250 east (the 10-22 hand pull's way)
bench 2026-11-22 (run_queue, look_as=None: retail's button picture -- dressed, the button never showed on the panel,
our CNA_* icons being gone from the SDK's Art):
  read  CampBlinkRead_mcp_1122_204246 / _210306: the selection and both moves are on the log; the ability gave nothing
        -- aimed on the Peacekeeper it selected him, aimed on the shore nothing happened (no message, no pull)
  pull  CampBlinkPull_mcp_1122_211119: all four Guardians land round him ~1 s after the click, the button greys into
        its reload; the cast is one message on the log, carrying the power, the point, the Guardian under the cursor
        and the caster
(read / pull were dropped in round 189: button 1 is now his blink and a right-click is rewritten.)
Round 189, step 2-3: ra3ext rewrites a right-click move given with him alone selected into his own point blink
(button 1, a 5 s reload); several selected are left alone.
  blink CampBlinkBlink_mcp_1122_213603: all four right-clicks land him on the clicked point, no walk before or after,
        each hop given after he landed works; a hand click on button 1 sends the very message the rewrite makes
        (_213058); a blink sometimes drops him from the selection (message 1f9 right after it), so each hop
        selects him again; the box of five gets the plain move and everyone walks. The reload is not measured:
        the bench's box and click take ~200 frames each, longer than it.
Round 190: the right-click now stays as it is (everyone selected walks) and ra3ext adds his blink right after it,
only while the blink is ready (60 s reload, 200 max distance here); a deselect sent by his fade-out right after a hop
is made to deselect nothing.
  blink CampBlinkBlink_mcp_1122_221252 (the boxed version): alone, short -> he blinks; all six boxed in his reload ->
        no blink, he walks with the rest; all six boxed once reloaded -> he blinks (181 away), the tanks walk
        CampBlinkBlink_mcp_1122_221709 (this list): alone -> a blink; the next right-click, not boxed again, in his
        reload -> he walks; reloaded, 297 away (past 200) -> no blink, he walks all the way
"""
from maps import island
from parts import Mission, Test
from units import beacon as bc

LIMIT = 3000
BLINK = 'SpecialPower_CNV_BlinkHost_Blink'
PULL = (-200.0, 100.0)                                              # a Peacekeeper in the shallows
SQUAD = (250.0, -60.0)                                              # four Guardians on land east of him


def mission():
    # look_as=None: retail's button picture (11-22: our CNA_* icons are gone from the SDK's Art; dressed, the button
    # never showed on the panel)
    unit = bc.beacon('CNV_BlinkHost', look_as=None)
    assert unit.xml.count('<Behaviors>') == 1
    unit.xml = unit.xml.replace('<Behaviors>', f'''<Behaviors>
			<DeletionUpdate id="ModuleTag_CNVBlink" MinFrames="1" MaxFrames="{LIMIT}"/>
			<SpecialPower id="ModuleTag_CNV_Blink" SpecialPowerTemplate="{BLINK}" UpdateModuleStartsAttack="true"/>
			<TeleportSpecialAbilityUpdate id="ModuleTag_CNV_BlinkUpdate" SpecialPowerTemplate="{BLINK}"
				StartAbilityRange="99999.0" UnpackTime="0s" PackTime="0s" MaxDistance="200" FadeInTime="0.5s"/>''', 1)
    # round 189: his own point jump, the rewrite's target (ra3ext's BLINK_POWER = this id's FastHash), button 1
    cmd = 'Command_CNV_BlinkHost_Blink'
    unit.xml = unit.xml.replace('</AssetDeclaration>', f'''	<SpecialPowerTemplate id="{BLINK}" ReloadTime="60s" TargetType="LOCATION"
		Flags="FOGGED_SHROUDED_CELLS_OK CAN_NOT_BE_SCRAMBLED" WaypointModeTerminal="false"/>
	<LogicCommand Type="SPECIAL_POWER" id="{cmd}">
		<SpecialPower>{BLINK}</SpecialPower>
	</LogicCommand>
</AssetDeclaration>''', 1).replace('<LogicCommandSet id="CNV_BlinkHostCommandSet">',
                                   f'<LogicCommandSet id="CNV_BlinkHostCommandSet">\n\t\t<Cmd>{cmd}</Cmd>', 1)
    ui = 'CNV_BlinkHost_UI.xml'
    unit.files[ui] = unit.files[ui].replace('</AssetDeclaration>', f'''	<UnitAbilityButtonTemplate id="Button_CNV_BlinkHost_Blink" LogicCommand="{cmd}">
		<Data>
			<TargetedSpecialPower StateData="ButtonStateAbilityLeap" ValidTargetCursor="TargetAbility"/>
		</Data>
	</UnitAbilityButtonTemplate>
</AssetDeclaration>''', 1)
    unit.link += [f'SpecialPowerTemplate:{BLINK}', f'LogicCommand:{cmd}', 'UnitAbilityButtonTemplate:Button_CNV_BlinkHost_Blink']
    assert unit.xml.count(BLINK) == 4 and unit.files[ui].count(cmd) == 1
    m = Mission(name='CampBlink', map=island, units=[unit], facts={})
    m.ext, m.ext_logs = True, ("entrydeselect190",)   # private entry set: which code sends the deselect 1f9
    m.put(unit.id, 'west field', 0, 0, name='UNIT - CNV Blink', role='beacon')
    m.put('AlliedAntiInfantryInfantry', 'west field', *PULL, role='pulled')
    for dx, dy in ((-40, -40), (40, -40), (-40, 40), (40, 40)):     # the 10-22 hand pull aimed on Guardians on land
        m.put('AlliedAntiVehicleVehicleTech1', 'west field', SQUAD[0] + dx, SQUAD[1] + dy, role='squad')
    return m


def blink(m):
    # screen pixels: the bench's world -> screen is off for infantry on this camera (11-22: the trooper drawn at
    # (527, 510), the Peacekeeper at (265, 410), not where to_screen put them)
    w = lambda s: ('bench_watch', dict(seconds=s, every=2, sheet=False, lines=2))
    rc = lambda x, y: ('bench_click', dict(x=x, y=y, world=False, right=True, look=True))
    t = Test()
    box = lambda x0, y0, x1, y1: ('bench_box', dict(x0=x0, y0=y0, x1=x1, y1=y1, world=False, look=True))
    # round 190: a right-click with him selected stays (all selected walk) and a blink of his follows it while ready
    # (60 s reload, 200 max distance); a blink may drop him from the selection (1f9), so each step boxes again
    t.bench = [box(480, 460, 575, 560), rc(640, 470), w(3),             # alone, short: a blink
               rc(600, 420), w(4),                                      # not boxed again, in his reload: he walks
               w(60), rc(1050, 620), w(6)]                              # reloaded, ~300 away (past 200)
    t.expect = []
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_blink': mission}
CHECKS = {'engine_blink': {'blink': blink}}
