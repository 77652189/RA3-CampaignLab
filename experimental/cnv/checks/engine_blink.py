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
"""
from maps import island
from parts import Mission, Test
from units import beacon as bc

LIMIT = 400
MOVE, PULL, MOVE2 = (200.0, 0.0), (-200.0, 100.0), (0.0, 150.0)   # from the west field site, all on screen
SQUAD = (250.0, -60.0)                                              # four Guardians on land east of him


def mission():
    # look_as=None: retail's button picture (11-22: our CNA_* icons are gone from the SDK's Art; dressed, the button
    # never showed on the panel)
    unit = bc.beacon('CNV_BlinkHost', look_as=None)
    assert unit.xml.count('<Behaviors>') == 1
    unit.xml = unit.xml.replace('<Behaviors>', f'''<Behaviors>
			<DeletionUpdate id="ModuleTag_CNVBlink" MinFrames="1" MaxFrames="{LIMIT}"/>''', 1)
    m = Mission(name='CampBlink', map=island, units=[unit], facts={})
    m.ext = True
    m.put(unit.id, 'west field', 0, 0, name='UNIT - CNV Blink', role='beacon')
    m.put('AlliedAntiInfantryInfantry', 'west field', *PULL, role='pulled')
    for dx, dy in ((-40, -40), (40, -40), (-40, 40), (40, 40)):     # the 10-22 hand pull aimed on Guardians on land
        m.put('AlliedAntiVehicleVehicleTech1', 'west field', SQUAD[0] + dx, SQUAD[1] + dy, role='squad')
    return m


def read(m):
    # screen pixels: the bench's world -> screen is off for infantry on this camera (11-22: the trooper drawn at
    # (527, 510), the Peacekeeper at (265, 410), not where to_screen put them)
    t = Test()
    t.bench = [('bench_box', dict(x0=480, y0=460, x1=575, y1=560, world=False, look=True)),
               ('bench_click', dict(x=820, y=470, world=False, right=True, look=True)),
               ('bench_watch', dict(seconds=6, every=3, sheet=False, lines=2)),
               # the ground beside the Peacekeeper: aimed on him, the click selected him (11-22)
               ('bench_ability', dict(x=335, y=425, world=False, look=True)),
               ('bench_watch', dict(seconds=6, every=3, sheet=False, lines=2)),
               ('bench_click', dict(x=640, y=300, world=False, right=True, look=True)),
               ('bench_watch', dict(seconds=6, every=3, sheet=False, lines=2))]
    t.expect = []
    return t


def pull(m):
    # the way of the 10-22 hand pull: he stands where he was put, the ability aimed on the Guardians (land, east)
    t = Test()
    t.bench = [('bench_box', dict(x0=480, y0=460, x1=575, y1=560, world=False, look=True)),
               ('bench_ability', dict(x=880, y=570, world=False, look=True)),
               ('bench_watch', dict(seconds=6, every=2, sheet=False, lines=2))]
    t.expect = []
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_blink': mission}
CHECKS = {'engine_blink': {'read': read, 'pull': pull}}
