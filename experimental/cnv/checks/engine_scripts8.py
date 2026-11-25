"""Scene and script helpers shared by the script, UI and other benches."""
from maps import probe_border
from parts import Mission, Script

TANK = 'AlliedAntiVehicleVehicleTech1'
O = (1300.0, 4300.0)                            # probe_border's 'stop row': every place below is absolute
RUN = {'team': 8.0, 'idle': 30.0, 'merge': 30.0, 'spawn': 6.0, 'status': 20.0, 'power': 10.0}
TEAM_ROW = {'Del': 800.0, 'Kil': 1300.0, 'Liv': 1800.0}
IDLE_ROW = {'Idl': 2000.0, 'Idf': 2200.0, 'Ctl': 2400.0}
MERGE_ROW = {'Src': (3200.0, 2), 'Dst': (3400.0, 1), 'Sr2': (3700.0, 2), 'Ds2': (3900.0, 1)}
GOALS = {'idle Idl': (2100.0, 2000.0), 'idle Idf': (2100.0, 2200.0), 'idle Ctl': (2100.0, 2400.0),
         'merge M': (2000.0, 3300.0), 'merge N': (2000.0, 3800.0)}
STATUS = {'hold': ((3500.0, 1000.0), (3500.0, 1150.0), (3620.0, 1075.0)), 'free': ((3500.0, 2300.0), None,
                                                                                    (3620.0, 2300.0))}
ANCHOR = (3500.0, 3500.0)
SPAWNED = 'UNIT - CNV S8 Spawned'


def _n(part):
    return f'UNIT - CNV S8 {part}'


def _put(m, template, x, y, **kw):
    m.put(template, 'stop row', x - O[0], y - O[1], **kw)


def mission(name='CampScr8'):
    m = Mission(name=name, map=probe_border, units=[], facts={})
    m.spawns |= {TANK}
    for crew, x in TEAM_ROW.items():
        c = m.crew(crew)
        for k in (1, 2):
            _put(m, TANK, x + 150.0 * (k - 1), 1000.0, angle=0.0, name=_n(f'{crew} {k}'), role=f'{crew} {k}',
                 props={'originalOwner': c})
    for crew, y in IDLE_ROW.items():
        c = m.crew(crew)
        for k in (1, 2):
            _put(m, TANK, 700.0 + 150.0 * k, y, angle=0.0, name=_n(f'{crew} {k}'), role=f'{crew} {k}',
                 props={'originalOwner': c})
    for crew, (y, n) in MERGE_ROW.items():
        c = m.crew(crew)
        for k in range(1, n + 1):
            _put(m, TANK, 700.0 + 150.0 * k, y, angle=0.0, name=_n(f'{crew} {k}'), role=f'{crew} {k}',
                 props={'originalOwner': c})
    for part, (x, y) in GOALS.items():
        m.waypoint(part, f'CNV S8 {part.title()}', 'stop row', x - O[0], y - O[1])
    hold = m.crew('Hold')
    for part, (a, b, e) in STATUS.items():      # pending_scripts8 status's scene
        kw = {'props': {'originalOwner': hold}} if part == 'hold' else {}
        _put(m, TANK, *a, angle=0.0, name=_n(f'{part.title()} 1'), role=f'{part} 1', **kw)
        if b:
            _put(m, TANK, *b, angle=0.0, name=_n(f'{part.title()} 2'), role=f'{part} 2', **kw)
        _put(m, TANK, *e, side='s1', angle=3.1416, name=_n(f'{part.title()} Foe'), role=f'{part} foe')
    _put(m, TANK, *ANCHOR, angle=1.5708, name=_n('Anchor'), role='anchor')
    return m


def at(t, key, secs, actions):
    timer = f'Test S8 {key} Timer'
    t.scripts += [Script(f'Test - S8 {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                  Script(f'Test - S8 {key}', [('TIMER_EXPIRED', timer)], actions)]


def total(t, counter, label, parts):
    """counter = the sum of the weights whose condition holds, recounted every frame. parts: [(weight, condition)]."""
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
    t.scripts += [Script(f'Test - {counter} {k}', [c], [('INCREMENT_COUNTER', w, counter)], once=False)
                  for k, (w, c) in enumerate(parts)]


def frames(t, counter, label, cond):
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter}', cond, [('INCREMENT_COUNTER', 1, counter)], once=False))


def watch(t, run, every=1.0):
    t.bench = [('bench_watch', dict(seconds=run, every=every, sheet=False, lines=len(t.counters)))]
