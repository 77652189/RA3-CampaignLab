"""C-line probe: REDALERT_DISABLE_THREAT_LEVEL_BONUS(player), 20 retail uses in six missions.

SDK GlobalData/RedAlerts.xml: deaths contribute threat at 3 times their value; orange/red thresholds
12500/37500, capped at 50000, decay 150/300 per second; protocol XP multipliers 1/1.5/2.
System/PlayerTechRanks.xml: rank 2 needs 360 XP, normally 1 XP/s. INFERRED: scripted NAMED_KILL
contributes death threat too. Two players lose ten 2000-cost Apocalypses at 2, 62, 122, 182,
242, 302 seconds, with an anchor surviving. A disables p1's bonus, B disables s5's.
Prediction before measuring: disabled rank at frame 5400; enabled before frame 4500 if scripted
deaths activate the threat multiplier. Do not promote the action on an equal baseline alone.
Counters A: p1 rank-2 frame, s5 rank-2 frame, living sacrifice count, completed loss waves.
Counters B: the same first three, then the script logic frame. B stops at frame 5700 rather than
assuming captured seconds are mission seconds. A ended after only three waves (both ranks still 0).
B also uses HOLD_FIRE (3); A used HOLD_POSITION (2), with the two sides outside weapon range.
BENCH 11-16 B: both players reach rank 2 at frame 2893, even disabled s5; final counters
2893/2893/0/5708. The simulator's 5400/5400 is retained as a strict xfail. The script's
unit-experience bonus scope and actual player threat/multiplier remain gaps; no promotion.
No combat or AI world input is assumed. Evidence and unresolved inputs: work/re/c_threatbonus_report.md.
"""
from maps import probe_border
from parts import Mission, Script, Test
from checks import engine_scripts8 as s8

TANK = 'SovietAntiVehicleVehicleTech3'
SIDES = ('p1', 's5')
WAVES = (2., 62., 122., 182., 242., 302.)
RUN = 375.


def _name(side, wave, k):
    return f'CNV TB {side} {wave} {k}'


def mission():
    m = Mission(name='CampThreat', map=probe_border, units=[], facts={})
    m.spawns.add(TANK)
    for side, x in (('p1', 700.), ('s5', 3000.)):
        for wave in range(len(WAVES)):
            for k in range(10):
                m.put(TANK, 'stop row', x + k % 5 * 130 - 1300.,
                      700. + wave * 400 + k // 5 * 140 - 4300., side=side,
                      name=_name(side, wave, k))
        m.put(TANK, 'stop row', x - 1300., 4500. - 4300., side=side, name=f'CNV TB {side} anchor')
    return m


def check(m, disabled):
    t = Test()
    names = [_name(side, wave, k) for side in SIDES for wave in range(len(WAVES)) for k in range(10)]
    t.scripts.append(Script('Test - threat setup', [],
                            [('REDALERT_DISABLE_THREAT_LEVEL_BONUS', m.player(disabled)),
                             ('MAP_REVEAL_ALL_PERM', m.player('p1'))] +
                            [('UNIT_SET_STANCE', n, 2 if disabled == 'p1' else 3)
                             for n in names + [f'CNV TB {s} anchor' for s in SIDES]]))
    t.scripts.append(Script('Test - threat clock', [], [('INCREMENT_COUNTER', 1, 'CNV_TB_Clock')], once=False))
    for side, label in (('p1', '甲升级帧'), ('s5', '乙升级帧')):
        counter = f'CNV_TB_{side}'
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - threat rank {side}',
                                [('PLAYER_HAS_PLAYER_TECH', m.player(side), 'PlayerTech_Generic_Rank_2')],
                                [('SET_COUNTER_TO_COUNTER', counter, 'CNV_TB_Clock')]))
    s8.total(t, 'CNV_TB_Alive', '余车', [(1, ('NAMED_NOT_DESTROYED', n)) for n in names])
    t.counters.append(('CNV_TB_Waves', '批次') if disabled == 'p1' else ('CNV_TB_Clock', '逻辑帧'))
    for wave, secs in enumerate(WAVES):
        s8.at(t, f'threat loss {wave}', secs,
              [('NAMED_KILL', _name(side, wave, k)) for side in SIDES for k in range(10)] +
              [('INCREMENT_COUNTER', 1, 'CNV_TB_Waves')])
    s8.watch(t, RUN, 10.)
    if disabled == 's5':
        t.bench = [('bench_watch', dict(seconds=1500., every=10., sheet=False, lines=4, until='c4>=5700'))]
    return t


def a(m):
    return check(m, 'p1')


def b(m):
    return check(m, 's5')


MISSION = {'engine_threatbonus': mission}
CHECKS = {'engine_threatbonus': {'a': a, 'b': b}}
