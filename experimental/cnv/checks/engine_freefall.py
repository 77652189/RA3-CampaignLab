"""Engine line A round 157: FreefallUpdate -- does it carry a man the Bullfrog's man cannon throws down to the ground?

Every infantry of ours has it (SDK BaseInfantry.xml: ModuleTag_FreefallUpdate, ModelConditionsToSet STUNNED_FLAILING,
InitialVelocity 5, Acceleration 1, TerminalVelocity 15; the comment: 'for objects that don't have Dynamics but that
still may fall out of the sky on death'). In our 9 levels a man is in the air when the Bullfrog throws him
(a01's waves: SovietAntiAirShip, EjectPassengersSpecialAbilityUpdate Height 200 ApexHeight 20 Speed 20,
TimePerPassenger 0.5 s; engine_transport: down on the spot ~2 s after the press). Whether that descent is the
eject's own arc or this module's fall is what the probe tells, by changing the module and nothing else:

On maps/probe_border.py, three rows, each a Bullfrog of the player with one man put in at LOAD, holding fire;
at GO each Bullfrog throws its man at its own waypoint THROW east (NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT):
  A  a retail conscript (SovietAntiInfantryInfantry)
  S  CNVFallSlow: the conscript under a new id, its FreefallUpdate (same id, overriding BaseInfantry's)
     InitialVelocity 0, Acceleration 0.05, TerminalVelocity 1 -- a fall of 200 would take ~200 frames
  F  CNVFallFast: the same with Acceleration 5, TerminalVelocity 60
Counters (four lines fit), frames counted from GO on (the press's frame is frame 1):
  帧数        frames since GO + 1000 x frames A's man holds PARACHUTING
  A / S / F  frames the man holds AIRBORNE_TARGET + 1000 x frames until he is first inside the 120 square at his
             waypoint (a man never there counts every frame)
Prediction: if the module carries the descent, S's AIRBORNE frames and its square wait far exceed A's, F's
are fewer; if the eject's arc does (the module only for the dead and the lifted), the three rows read alike.

Bench 11-11 (round 157, CampFallFall_mcp_1111_032014, PASS -- readings only):
  A, S and F read the same every half second: AIRBORNE_TARGET from frame 1 to 125 (then never), inside the square
  from frame 22 (the throw's flat run, as engine_transport's ~2 s); final 22125 / 22125 / 22125.
  帧数 96xxx at the end: A's man PARACHUTING frames ~44-139 (96 frames), after he is over the spot.
  So the module's parameters do not change a thrown man's fall: the parachute does it, airborne ~8 s after the
  press, ~6 s over the spot. FreefallUpdate then acts on the dead and the lifted only (not benched: line C's lift
  is paused; a dead man's fall is presentation). Not ruled out: the copies' same-id FreefallUpdate not overriding
  BaseInfantry's (a copy whose FreefallUpdate is renamed / removed would tell).
"""
import os

from maps import probe_border
from parts import Mission, Script, Test, Unit, square, status
import checks.engine_scripts8 as s8

FROG, MAN = 'SovietAntiAirShip', 'SovietAntiInfantryInfantry'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
X0 = 900.0
THROW = 300.0                                   # the waypoint east of each Bullfrog
BOX = 120.0
FALLS = {'S': ('CNVFallSlow', 0.0, 0.05, 1.0), 'F': ('CNVFallFast', 0.0, 5.0, 60.0)}
ROWS = {'A': (MAN, 3900.0), 'S': (FALLS['S'][0], 4200.0), 'F': (FALLS['F'][0], 4500.0)}
LOAD, GO, RUN = 2.0, 3.0, 25.0


def _n(part):
    return f'UNIT - CNV FF {part}'


def fall_unit(new, v0, acc, top):
    """The conscript (SDK Soviet/Units/SovietAntiInfantryInfantry.xml) under `new`, with a FreefallUpdate of its own
    (the inherited module's id, so it replaces BaseInfantry's): only the fall changed."""
    import labpaths
    path = os.path.join(labpaths.SDK3, 'SageXML', 'Soviet', 'Units', f'{MAN}.xml')
    x = open(path, encoding='utf-8').read()
    for old in (f'id="{MAN}"', f'EditorName="{MAN}"'):
        assert x.count(old) == 1, old
        x = x.replace(old, old.replace(MAN, new))
    end = '\t\t</Behaviors>'
    assert x.count(end) == 1
    module = (f'\t\t\t<FreefallUpdate id="ModuleTag_FreefallUpdate" ModelConditionsToSet="STUNNED_FLAILING" '
              f'InitialVelocity="{v0:g}" Acceleration="{acc:g}" TerminalVelocity="{top:g}"/>\n')
    x = x.replace(end, module + end)
    return Unit(new, x, what=f'对照：动员兵换了 id，下落 v0={v0:g} a={acc:g} 终速={top:g}')


def mission(name='CampFall'):
    m = Mission(name=name, map=probe_border, units=[fall_unit(*f) for f in FALLS.values()], facts={})
    m.spawns |= {FROG, MAN}
    for row, (man, y) in ROWS.items():
        m.put(FROG, 'stop row', X0 - O[0], y - O[1], angle=0.0, name=_n(f'{row} Box'), role=f'{row} box')
        c = m.crew(f'FF{row}')
        m.put(man, 'stop row', X0 - 100.0 - O[0], y - 90.0 - O[1], angle=0.0, name=_n(f'{row} Man'),
              role=f'{row} man', props={'originalOwner': c})
        m.waypoint(f'throw {row}', f'CNV FF Throw {row}', 'stop row', X0 + THROW - O[0], y - O[1])
    return m


def fall(m):
    t = Test()
    hold = [('UNIT_CHANGE_OBJECT_STATUS', _n(f'{r} {k}'), status('NO_ATTACK'), 1) for r in ROWS for k in ('Box', 'Man')]
    s8.at(t, 'hold', 0.1, hold + [('MAP_REVEAL_ALL_PERM', m.player('p1'))])
    s8.at(t, 'load', LOAD, [('TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY', m.teams[f'FF{r}'], _n(f'{r} Box'))
                            for r in ROWS])
    s8.at(t, 'go', GO, [('SET_FLAG', 'Test FF Going', 1)]
          + [('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', _n(f'{r} Box'),
              'Command_ActivateEjectPassengersSpecialPower', m.mark(f'throw {r}')) for r in ROWS])
    going = ('FLAG', 'Test FF Going', 1)
    s8.frames(t, 'CNV_FF_Frames', '帧数', [going])
    t.scripts.append(Script('Test - FF A para', [going, ('UNIT_HAS_OBJECT_STATUS', _n('A Man'), status('PARACHUTING'))],
                            [('INCREMENT_COUNTER', 1000, 'CNV_FF_Frames')], once=False))
    for r in ROWS:
        man = _n(f'{r} Man')
        area = f'Test FF Throw {r}'
        t.areas[area] = square(*m.point(f'throw {r}'), BOX)
        c = f'CNV_FF_{r}'
        t.counters.append((c, r))
        t.scripts.append(Script(f'Test - {c} air', [going, ('UNIT_HAS_OBJECT_STATUS', man, status('AIRBORNE_TARGET'))],
                                [('INCREMENT_COUNTER', 1, c)], once=False))
        t.scripts.append(Script(f'Test - {c} wait', [going, ('FLAG', f'Test FF In {r}', 0)],
                                [('INCREMENT_COUNTER', 1000, c)], once=False))
        t.scripts.append(Script(f'Test - {c} in', [going, ('NAMED_INSIDE_AREA', man, area)],   # after the counts
                                [('SET_FLAG', f'Test FF In {r}', 1)], once=False))
    t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN))]
    return t


MISSION = {'engine_freefall': mission}
CHECKS = {'engine_freefall': {'fall': fall}}
