"""Retail-campaign actions, batch 6 (round 216): TEAM_HUNT / NAMED_HUNT (203 + 66 uses in the 27 retail missions).
Mission on maps/probe_border.py as checks/engine_acts5.py ('stop row' offsets). What the simulator predicts is in
brackets.

Why these sides. Retail a01's second wave (TEAM - Wave 02 - Infantry Invaders 01..08, Soviet_1's) runs
TEAM_ALLOW_AI_AUTOACQUIRE(team, 1) + TEAM_HUNT(team) with Soviet_1 never handed to the AI (no UNIT_AI_TRANSFER_ALL /
SKIRMISH_AI_* on it till wave 4's SKIRMISH_AI_TRANSFER_ALL('Soviet_1', 0)); Soviet_1 has an aiPersonality
(AIP_A01_SovietHuntMarshall) and its aiTeamBuilder / aiTactical switches 255, the other seven 240. The program
(work/re l2_scripts1 4): TEAM_HUNT sets each member's hunt bit and hangs a HuntTactic on the team only when its
player has an AI (two player fields non-zero). Round 11-08's hunt bench put its team on Soviet_1, whose team this
container empties at the start (engine_scripts9 memb), so it said nothing on TEAM_HUNT. The container (Heidelberg)
gives Soviet_4 DefaultPersonality with aiTeamBuilder / aiTactical 255 (as a01's Soviet_1) and Soviet_5
DefaultPersonality with both 240: the pair asks whether those switches gate the hunt.

  hunt  s4's crew H4 (two conscripts) at (3800, 4000), s5's crew H5 at (3800, 4700); s4's lone conscript l4 at
        (3000, 4700), s5's l5 at (3000, 4000). The player's barracks pb at (2200, 4350) -- the nearest enemy structure
        -- and tank pt at (4600, 4350), nearer to the crews (~800) than pb (~1650). 2 s: TEAM_ALLOW_AI_AUTOACQUIRE +
        TEAM_HUNT on H4 and H5 (a01's pair), NAMED_HUNT on l4 and l5.
          家 (every frame) = H4's men within 250 of home (ones) + H5's (tens) + l4 (hundreds) + l5 (thousands)
          到 (every frame) = the same by pb (within 400 of it)
          打 (every frame) = pb attacked by a conscript 1, pt attacked by a conscript 2, + 10 x living conscripts of
            the four (H4, H5, l4, l5: 0..6)
  [simulator before the bench: 家 1122 throughout, 到 0, 打 60 -- nobody moves (TEAM_HUNT / NAMED_HUNT only noted)]
  BENCH 11-14 (round 216, run_queue once, CampActsWHunt; tests/test_simbench.py test_acts_w_hunt_as_the_bench):
    家 / 到 / 打  s1-s6 1122 0 60 | s7-s14 1120 0 60 | s15-s30 1120 0 62 | s31-s48 1120 0 52 | s49-s56 1120 0 42 |
    s57-s66 1120 0 40. The bench's seconds run ~1 behind the scripts'.
    TEAM_HUNT: Soviet_4's crew (255) left home ~4 s after the order and went for the tank (the nearest enemy, a unit),
    never the barracks (the nearest structure); it fought the tank from s15 and both died (s31, s49). Soviet_5's crew
    (240) stayed. NAMED_HUNT: neither lone conscript moved in 60 s. After the bench the simulator reads 1122 -> 1120
    at 8 s, 62 at 17 s, 52 at 33 s, 42 at 50 s (Sim.tactical + an attack-move to the nearest hostile object).
"""
from maps import probe_border
from parts import Mission, Test, square
import checks.engine_scripts8 as s8

TANK, MAN, BARRACKS = 'AlliedAntiVehicleVehicleTech1', 'SovietAntiInfantryInfantry', 'AlliedBarracks'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
RUN = 60.0
HOME = {'H4': (3800.0, 4000.0), 'H5': (3800.0, 4700.0), 'l4': (3000.0, 4700.0), 'l5': (3000.0, 4000.0)}
PB, PT = (2200.0, 4350.0), (4600.0, 4350.0)


def _n(part):
    return f'UNIT - CNV Act6 {part.title()}'


def _unit(m, role, side, template, x, y, crew=None):
    props = {'originalOwner': m.crew(crew, side=side)} if crew else {}
    m.put(template, 'stop row', x - O[0], y - O[1], side=side, angle=0.0 if side == 'p1' else 3.1416,
          name=_n(role), role=role, props=props)


def mission():
    m = Mission(name='CampActsW', map=probe_border, units=[], facts={})
    m.spawns |= {TANK, MAN, BARRACKS}
    for crew in ('H4', 'H5'):
        x, y = HOME[crew]
        for k in range(2):
            _unit(m, f'{crew} {k}', 's' + crew[1], MAN, x, y - 30.0 + 60.0 * k, crew=crew)
    for lone in ('l4', 'l5'):
        _unit(m, lone, 's' + lone[1], MAN, *HOME[lone])
    _unit(m, 'pb', 'p1', BARRACKS, *PB)
    _unit(m, 'pt', 'p1', TANK, *PT)
    return m


def men(key):
    return [_n(f'{key} {k}') for k in range(2)] if key.startswith('H') else [_n(key)]


def hunt(m):
    t = Test()
    for key, at in HOME.items():
        t.areas[f'Test Act6 Home {key}'] = square(*at, 250.0)
    t.areas['Test Act6 Pb'] = square(*PB, 400.0)
    s8.at(t, 'h2', 2.0, [a for crew in ('H4', 'H5') for a in (('TEAM_ALLOW_AI_AUTOACQUIRE', m.teams[crew], 1),
                                                            ('TEAM_HUNT', m.teams[crew]))]
          + [('NAMED_HUNT', _n(lone)) for lone in ('l4', 'l5')])
    weight = {'H4': 1, 'H5': 10, 'l4': 100, 'l5': 1000}
    s8.total(t, 'CNV_Act6_Home', '家', [(w, ('NAMED_INSIDE_AREA', u, f'Test Act6 Home {k}'))
                                        for k, w in weight.items() for u in men(k)])
    s8.total(t, 'CNV_Act6_At', '到', [(w, ('NAMED_INSIDE_AREA', u, 'Test Act6 Pb'))
                                      for k, w in weight.items() for u in men(k)])
    s8.total(t, 'CNV_Act6_Hit', '打', [(1, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('pb'), MAN)),
                                       (2, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('pt'), MAN))]
             + [(10, ('NAMED_NOT_DESTROYED', u)) for k in weight for u in men(k)])
    s8.watch(t, RUN)
    return t


MISSION = {'engine_acts_w': mission}
CHECKS = {'engine_acts_w': {'hunt': hunt}}
