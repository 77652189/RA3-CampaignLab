"""How fast a unit turns, from its Locomotor (simunits.turning), against the bench's per-frame headings.

Bench (A round 227; B round 195 found it): the skirmish AI's form-up orders (airev1t and its variants in
benches/ai/tactics/scenes.py#aipullback_bench) logged every member's body heading and place frame by frame (tests/fixtures/a_turn,
taken from the runs' ra3ext.log). A turn goes 360 / TurnTimeSeconds degrees a second, i.e. that / 15 a frame, the
last step whatever is left; a turn over the Locomotor's TurnThresholdHS is done in place -- the unit does not move
while its heading changes.
"""
from pathlib import Path

import pytest
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.data.units as simunits  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

FIXTURES = ROOT / 'tests/fixtures/a_turn'
BUILDS = {'airev1t': 'SovietAntiVehicleVehicleTech1',     # build -> the AI's tank in it: Hammer 1.25 s (19.2 a frame)
          'airevgt': 'AlliedAntiVehicleVehicleTech1',     # Guardian 1.0 s (24), facing north-west: a 51 deg turn
          'airevat': 'SovietAntiVehicleVehicleTech3'}     # Apocalypse 3 s (8)
DRIVE_WITHIN = 9.0      # a unit drives on a frame that starts this near its way (INFERRED: 8 drove, 10 / 15 did not)


def frames(build):
    """{frame: {member: (heading, x, y)}}"""
    out = {}
    for line in (FIXTURES / f'{build}.txt').read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        fr, *cells = line.split()
        row = {}
        for c in cells:
            member, heading, xy = c.split(':')
            x, y = xy.split(',')
            row[member] = (float(heading), float(x), float(y))
        out[int(fr)] = row
    return out


def wrap(d):
    return (d + 180.0) % 360.0 - 180.0


def turns(build):
    """Every logged one-frame step of a member's heading: (member, frame, step degrees, moved?, last of its turn?)."""
    rows = frames(build)
    out = []
    for f in sorted(rows):
        if f + 1 not in rows:
            continue
        for member, (h0, x0, y0) in rows[f].items():
            h1, x1, y1 = rows[f + 1][member]
            step = abs(wrap(h1 - h0))
            if step < 0.5:
                continue
            nxt = rows.get(f + 2, {}).get(member)
            after = 0.0 if nxt is None else wrap(nxt[0] - h1)
            # not logged next: may be the last; turned back the next frame: a new order (airevat f97 -> f98)
            last = nxt is None or abs(after) < 0.5 or after * wrap(h1 - h0) < 0
            out.append((member, f + 1, step, (x1, y1) != (x0, y0), last))
    return out


@pytest.mark.parametrize('build', sorted(BUILDS))
def test_a_turn_goes_the_locomotors_rate_a_frame(build):
    rate = simunits.turning(BUILDS[build]).turn_rate
    per_frame = rate / 15.0
    steps = turns(build)
    assert len(steps) >= 10, build
    for member, frame, step, _, last in steps:
        if last:
            assert step <= per_frame + 1.0, (member, frame, step)
        else:                                       # the log rounds headings to whole degrees
            assert abs(step - per_frame) <= 1.0, (member, frame, step, per_frame)


@pytest.mark.parametrize('build', sorted(BUILDS))
def test_a_turn_is_made_in_place(build):
    """Ordered from standing (form-up, go, and the turn to the form-up facing on arrival), a unit turns in place: it
    drives only on a frame that starts within DRIVE_WITHIN of its way, the rest of the turn made as it drives
    (airevat 3173 f38: -84 -> -76 moving; Hammer 3172 f32: 15 off, still in place; Apocalypse 3170 f37: 10 off, in
    place). Also for the Guardians' 51 deg turn -- under TurnThresholdHS 90 it is not driven round either. Not
    covered: a turn ordered while driving (airevgt f170, the attack order: turned 24 deg on a moving frame)."""
    limit = simunits.turning(BUILDS[build]).limit
    assert limit == 90.0
    assert not [s for s in turns(build) if s[3] and s[2] > DRIVE_WITHIN]
    assert len([s for s in turns(build) if not s[3]]) >= 10


def test_infantry_walk_off_turning():
    """Bench airevit (A round 231): airev1t's form-up with Conscripts (TestReactiveLocomotorHUMAN, TurnTimeSeconds 0.5,
    no TurnThresholdHS). Ordered from standing (f26, a ~110 deg turn) every member moves on the turn's first frame,
    at the walking pace it keeps after it (~3.2 a frame): no turn in place (sim.Body.turn_first False). Turning to
    the form-up facing once it stands (3170 f45-47) it does not move. The step is 45 a frame, not 720 / 15 = 48
    (not modelled: the simulator turns infantry at the data's rate)."""
    assert simunits.turning('SovietAntiInfantryInfantry').limit is None
    rows = frames('airevit')
    steps = turns('airevit')
    assert 22 not in rows and 25 not in rows                # nothing changed f22-25 (the log writes changes)
    for member, (h0, x0, y0) in rows[21].items():           # standing until the order: f26 one step on
        h1, x1, y1 = rows[26][member]
        assert abs(abs(wrap(h1 - h0)) - 45.0) <= 1.0 and 2.5 < ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 < 4.5, member
    for member, frame, step, moved, last in steps:
        if not last:
            assert abs(step - 45.0) <= 1.0, (member, frame, step)
    assert [s for s in steps if s[0] == '3170' and s[1] in (45, 46, 47) and not s[3]] and \
        not [s for s in steps if s[0] == '3170' and s[1] in (45, 46, 47) and s[3]]


def test_the_data_rates():                         # the simulator's turn (locomotion.turn): tests/test_sim.py test_*turn*
    def turning(template):
        loco = simunits.turning(template)
        return loco and (loco.turn_rate, loco.limit)
    assert turning('SovietAntiVehicleVehicleTech1') == (288.0, 90.0)   # 1.25 s: 19.2 a frame (bench 19)
    assert turning('AlliedAntiVehicleVehicleTech1') == (360.0, 90.0)
    assert turning('SovietAntiVehicleVehicleTech3') == (120.0, 90.0)
    assert turning('SovietAntiInfantryInfantry') == (720.0, None)
    assert turning('AlliedPowerPlant') is None
