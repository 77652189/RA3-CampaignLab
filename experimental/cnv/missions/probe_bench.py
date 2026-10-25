"""Engine probe for plan-driven missions (docs/story/plans): what a level plan's standard operations rely on, each
read back as a counter by checks/probe.py.

  - difficulty: three copies of a script, each with one difficulty bit (retail's only switch), set a counter to
    1 / 2 / 3 -- which one runs is the difficulty the game was started on;
  - money: PLAYER_SET_MONEY, read back with SET_PLAYER_MONEY_TO_COUNTER;
  - borders: the festival map's second border (west of the canal) at the start, back to the whole map (0) at
    `open at`; a Guardian sent east past the canal at once must not get there before;
  - autosave: CAMPAIGN_CREATE_AUTO_SAVE once a few seconds in (save=False: none -- the bench 2026-10-24 crashed
    ~4 s in, but every start that day failed alike: another game held the screen, see harness.DEVICE_HINT).

Published (the cast): guardian (the player's runner); marks: beyond (past the canal); facts: open at, money.
"""
from maps import festival
from parts import Mission, Script

OPEN_AT, MONEY = 25.0, 4321


def mission(name='CampProbe', save=True):
    m = Mission(name=name, map=festival, facts={'open at': OPEN_AT, 'money': MONEY})
    west = list(festival.BORDERS).index('west of the canal')
    m.put('AlliedAntiVehicleVehicleTech1', 'west field', 250, 30, name='UNIT - CNV Probe Runner', role='guardian')
    m.waypoint('beyond', 'CNV Probe Beyond', 'road exit')
    m.strings['AUTOSAVE:CNVCAMPAIGN'] = '新战役（自动存档）'
    m.scripts += [
        Script('CNV Probe - Start', [], [('MAP_SWITCH_BORDER', west),('PLAYER_SET_MONEY', m.player('p1'), MONEY),
                                         ('MOVE_NAMED_UNIT_TO', 'UNIT - CNV Probe Runner', 'CNV Probe Beyond'),
                                         ('SET_MILLISECOND_TIMER', 'CNV Probe Open', OPEN_AT),
                                         ('SET_MILLISECOND_TIMER', 'CNV Probe Save', 5.0)]),
        Script('CNV Probe - Open', [('TIMER_EXPIRED', 'CNV Probe Open')],
               [('MAP_SWITCH_BORDER', 0), ('MOVE_NAMED_UNIT_TO', 'UNIT - CNV Probe Runner', 'CNV Probe Beyond')]),
        *([Script('CNV Probe - Save', [('TIMER_EXPIRED', 'CNV Probe Save')],
                  [('CAMPAIGN_CREATE_AUTO_SAVE', 'AUTOSAVE:CNVCAMPAIGN')])] if save else []),
        *[Script(f'CNV Probe - Difficulty {k}', [], [('SET_COUNTER', 'CNV_Probe_Difficulty', k)],
                 levels=tuple(j == k for j in (1, 2, 3))) for k in (1, 2, 3)],
        Script('CNV Probe - Money', [], [('SET_PLAYER_MONEY_TO_COUNTER', m.player('p1'), 'CNV_Probe_Money')],
               once=False)]
    return m
