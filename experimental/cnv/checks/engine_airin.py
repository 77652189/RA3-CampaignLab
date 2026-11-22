"""engine_airin:go -- TEAM_ENTER_NAMED(team, object) (retail a01: two cryocopter teams of Allied02 told to enter Allied01's
two airfields, made under them a moment before; a08's line names a team and an airfield its map never makes).
AlliedAirfield's CanParkHereFilter takes SAME_PLAYER ALLIES but excludes AlliedSupportAircraft (the cryocopter).

On probe_range five lanes, each a Player_1 airfield at a gun pad and two aircraft 700 north of it, ordered at 2 s:
  己机 (base)    Player_1's two Apollos, their team told to enter the airfield
  友机 (high)    the same, Soviet_2's (made Player_1's friend both ways)
  己直 (removed) Player_1's two cryocopters, told to enter
  友直 (switch)  Soviet_2's two cryocopters, told to enter (a01's case)
  闲机 (order)   Player_1's two Apollos, no order (does an idle jet go home by itself?)
A lane's reading: its aircraft inside 300 of the airfield + 10 x those AIRBORNE_TARGET + 100 x PARKED_AT_AIRFIELD;
the friend's lane x 1000 on its own lane's counter (four counter lines at most)."""
from maps import probe_range
from parts import Mission, Test, square, status
from checks import engine_scripts8 as s8

JET, COPTER = 'AlliedFighterAircraft', 'AlliedSupportAircraft'
LANES = {'base': ('己机', JET, 'p1', 'order'), 'high': ('友机', JET, 's2', 'order'),
         'removed': ('己直', COPTER, 'p1', 'order'), 'switch': ('友直', COPTER, 's2', 'order'),
         'order': ('闲机', JET, 'p1', None)}


def _n(lane, k):
    return f'UNIT - CNV AirIn {lane.title()} {k}'


def mission():
    m = Mission(name='CampAirIn', map=probe_range, units=[], facts={})
    for lane, (_, kind, side, _) in LANES.items():
        m.put('AlliedAirfield', f'{lane} gun', role=f'{lane} field', name=f'UNIT - CNV AirIn {lane.title()} Field')
        for k in (1, 2):
            m.put(kind, f'{lane} gun', 120.0 * k - 180.0, 700.0, side=side, role=f'{lane} {k}', name=_n(lane, k))
    return m


def go(m):
    t = Test()
    p, ally = m.player('p1'), m.player('s2')
    orders = [('MAP_REVEAL_ALL_PERM', p), ('PLAYER_RELATES_PLAYER', p, ally, (2, 0.0, 'Friend')),
              ('PLAYER_RELATES_PLAYER', ally, p, (2, 0.0, 'Friend'))]
    s8.at(t, 'friend', 0.1, orders)
    enter = []
    for lane, (_, _, side, order) in LANES.items():
        if order:
            crew = m.crew(f'AirIn{lane.title()}', side)
            enter += [('UNIT_SET_TEAM', _n(lane, k), crew) for k in (1, 2)]
            enter.append(('TEAM_ENTER_NAMED', crew, m.role(f'{lane} field').name))
    s8.at(t, 'enter', 2.0, enter)
    for counter, lanes in (('Jet', ('base', 'high')), ('Copter', ('removed', 'switch')), ('Idle', ('order',))):
        parts = []
        for scale, lane in zip((1, 1000), lanes):
            area = f'Test AirIn {lane.title()} Near'
            t.areas[area] = square(*m.site(f'{lane} gun'), 300.0)
            for k in (1, 2):
                parts += [(scale, ('NAMED_INSIDE_AREA', _n(lane, k), area)),
                          (10 * scale, ('UNIT_HAS_OBJECT_STATUS', _n(lane, k), status('AIRBORNE_TARGET'))),
                          (100 * scale, ('UNIT_HAS_OBJECT_STATUS', _n(lane, k), status('PARKED_AT_AIRFIELD')))]
        s8.total(t, f'CNV_AirIn_{counter}', '+千'.join(LANES[lane][0] for lane in lanes), parts)
    s8.watch(t, 50.0, 1.0)
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_airin': mission}
CHECKS = {'engine_airin': {'go': go}}
