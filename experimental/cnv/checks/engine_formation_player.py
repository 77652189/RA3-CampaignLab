"""Engine line D, round 80 (coordinator 11-12, the user's ask): does the PLAYER's own group move keep its members at
the slowest one's pace, and how far apart do they stand? docs/engine/pathing.md 3/5 measured only scripted team moves
(the fast never waits); 5 (a) read that the formation path runs only for units the player put in a formation. This
mission gives the player two identical mixed groups on open ground (the probe map's pace lanes): two Guardian tanks
(speed 80) and two Peacekeepers (50), each a copy with ra3ext's read-only CNVProbe (a `probe` line per frame the
host moved: per-unit trajectory, the step is its actual speed). The bench then plays the player:

  plain       box-select the north group, right-click the goal 600 east: the ordinary group move
  formation   box-select the south group, right-DRAG at the goal (bench_box right=true, a short north-south front):
              the formation move with its preview (FormationAssistant)

Counters (every frame): per lane +1 for each tank inside the goal square (half 150), +10 for each Peacekeeper.
No expectations: the readings are the probe lines (scripts/d80_formation.py in work/re reads them).
"""
import os

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, square

TANK, MAN = 'AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'
PROBE = {TANK: 'CNV_FormTank', MAN: 'CNV_FormMan'}
EVERY, LINES = 150, 6000
# one camera sees ~500 x 380 here (bench 1112_122439: a 600-long layout fell off the screen), so both lanes, starts and
# goals fit in it: placed from the pace lane's start (500, 1200)
LANES = {'plain': 1230.0, 'formation': 1390.0}
X0, X1 = 650.0, 1000.0
SPOTS = [(TANK, 0.0, 25.0), (TANK, 0.0, -25.0), (MAN, -45.0, 25.0), (MAN, -45.0, -25.0)]
VIEW = ((X0 + X1) / 2, 1300.0)
RUN = 40.0


def probe_copy(template):
    pid = PROBE[template]
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', template + '.xml'), encoding='utf-8') as f:
        x = f.read()
    assert x.count(f'id="{template}"') == 1 and x.count('<Behaviors>') == 1
    x = x.replace(f'id="{template}"', f'id="{pid}"', 1).replace(f'EditorName="{template}"', f'EditorName="{pid}"')
    x = x.replace('<Behaviors>', f'''<Behaviors>
			<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>''', 1)
    return Unit(pid, x, names=dict(unit=pid), what=f'原版 {template} 的复制（探针）：多一个 ra3ext 的 CNVProbe，逐帧记位置',
                params=dict(of=template, every=EVERY, lines=LINES))


def mission():
    m = Mission(name='CampFormP', map=probe_range, units=[probe_copy(TANK), probe_copy(MAN)], facts={})
    m.ext = True
    for lane, y in LANES.items():
        for k, (tpl, dx, dy) in enumerate(SPOTS):
            m.put(PROBE[tpl], 'pace start', X0 - 500.0 + dx, y - 1200.0 + dy, role=f'{lane} {k}',
                  name=f'UNIT - CNV Form {lane.title()} {k}')
    return m


def player_moves(m, both=False):
    """f: the formation lane right-drags (D 84: that pans the camera in RA3, the units do not move); b: it drags with
    both buttons held, a longer front -- a try at the formation preview."""
    t = Test()
    t.waypoints['Test Form View'] = VIEW
    t.scripts.append(Script('Test - view', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                ('MOVE_CAMERA_TO', 'Test Form View', 0.1, 0.0, 0.0, 0.0)]))
    steps = [('bench_watch', dict(seconds=2, every=1, sheet=False, lines=2)),
             ('bench_view', dict(x=VIEW[0], y=VIEW[1], look=True))]
    for lane, y in LANES.items():
        counter = f'CNV_Form_{lane.title()}'
        t.counters.append((counter, lane))
        goal = f'Test Form {lane.title()} Goal'
        t.areas[goal] = square(X1, y, 70.0)
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        for k, (tpl, _, _) in enumerate(SPOTS):
            t.scripts.append(Script(f'Test - {counter} {k}', [('NAMED_INSIDE_AREA', m.role(f'{lane} {k}').name, goal)],
                                    [('INCREMENT_COUNTER', 1 if tpl == TANK else 10, counter)], once=False))
        steps.append(('bench_box', dict(x0=X0 - 90, y0=y - 55, x1=X0 + 40, y1=y + 55, look=True)))
        if lane == 'plain':
            steps.append(('bench_click', dict(x=X1, y=y, right=True, look=True)))
        else:
            half = 60 if both else 30
            steps.append(('bench_box', dict(x0=X1, y0=y - half, x1=X1, y1=y + half, look=True,
                                            **(dict(both=True) if both else dict(right=True)))))
    t.expect = []
    steps.append(('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=3)))
    t.bench = steps
    return t


HOTKEYS = 'UIMouseTacticalMiscHotKeys'
HOTKEY_SLOT, HOTKEY_VK = 'CycleHarvesters', 0x4E      # KEY_N (DefaultHotKeys); the probe map has no harvester to cycle


class HotkeyPack:
    """D 85 canary: retail leaves the Create Formation hotkey ("keep formation when moving", MiscHotKeys.xsd) unbound.
    This pack is retail's UIMouseTacticalMiscHotKeys (SDK UI/Mouse/Settings.xml, static stream) with CreateFormation
    bound to the CycleHarvesters slot (key N), compiled into the static stream where splice_assets puts it over
    retail's (as a music pack's map). Made on first use: the offline contract never writes the SDK."""
    FOLDER = 'CNVFormKeys'
    files = ()

    @property
    def include(self):
        with open(os.path.join(labpaths.SDK3, 'SageXML', 'UI', 'Mouse', 'Settings.xml'), encoding='utf-8-sig') as f:
            x = f.read()
        head = f'<{HOTKEYS}\n\t\tid="{HOTKEYS}"'
        body = x[x.index(head):x.index(f'</{HOTKEYS}>') + len(f'</{HOTKEYS}>')]
        assert 'CreateFormation=' not in body
        body = body.replace(f'id="{HOTKEYS}"', f'id="{HOTKEYS}"\n\t\tCreateFormation="{HOTKEY_SLOT}"', 1)
        data = os.path.join(labpaths.SDK3, 'Mods', self.FOLDER, 'Data')
        os.makedirs(data, exist_ok=True)
        with open(os.path.join(data, 'hotkeys.xml'), 'w', encoding='utf-8', newline='\r\n') as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n<AssetDeclaration xmlns="uri:ea.com:eala:asset">\n\t'
                    + body + '\n</AssetDeclaration>\n')
        return f'DATA:{self.FOLDER}/Data/hotkeys.xml'

    def check(self, files):
        """The spliced static streams carry our hotkey table (an instance retail has: it replaced retail's)."""
        from ra3voice import manifest, refpack
        unpack = lambda b: refpack.decompress(b) if refpack.is_refpack(b) else b
        where = [n for n, b in files if n.lower().startswith('data\\static') and n.lower().endswith('.manifest')
                 and any(a.name == f'{HOTKEYS}:{HOTKEYS}' for a in manifest.parse(unpack(b)))]
        assert where, f'{HOTKEYS} is in no spliced static stream: the binding never reaches the game'
        print(f'hotkeys: {HOTKEYS} spliced into {where}')


def hotkey_mission():
    m = mission()
    m.name = 'CampFormH'
    m.statics = [HotkeyPack()]
    return m


def hotkey_moves(m):
    """h: the formation lane is box-selected, gets Create Formation (key N, bound by HotkeyPack), then a plain
    right-click at its goal; the plain lane as in f. Same pace (tanks held to 50) = the hotkey is the same-pace entry."""
    t = player_moves(m)
    lane = [k for k, s in enumerate(t.bench) if s[0] == 'bench_box' and s[1].get('right')]
    assert len(lane) == 1
    x, y = t.bench[lane[0]][1]['x0'], (t.bench[lane[0]][1]['y0'] + t.bench[lane[0]][1]['y1']) / 2
    t.bench[lane[0]:lane[0] + 1] = [('bench_key', dict(vk=HOTKEY_VK, look=True)),
                                    ('bench_click', dict(x=x, y=y, right=True, look=True))]
    return t


MISSION = {'engine_formation_player': mission, 'engine_formation_hotkey': hotkey_mission}
CHECKS = {'engine_formation_player': {'f': player_moves, 'b': lambda m: player_moves(m, both=True)},
          'engine_formation_hotkey': {'h': hotkey_moves}}
