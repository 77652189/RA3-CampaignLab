"""Self-healing as a rule (AutoHealBehavior, engine/modules/autoheal.py since step K1; ADR 0029 "测试分两层"): on the
minimal world, only the frame order's autoheal cell runs. The whole-mission version against the bench is
test_simbench.py::test_autoheal_an_apocalypse_mends_two_points_every_7_frames_after_a_15_frame_wait (engine_heal a).
The module's own tests: tests/modules/test_autoheal.py."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simsmall  # noqa: E402
from engine.kernel import interfaces  # noqa: E402

APOC = 'SovietAntiVehicleVehicleTech3'        # AutoHealBehavior: 2 points every 7 frames, 15 frames after a hurt


def autoheal(s, frame):
    s.world.frame = frame                              # as the frame loop sets it before each cell
    s.world.schedule.run('autoheal', frame)


def awake(s):
    return set(s.world.schedule.awake('autoheal'))


def test_a_hurt_apocalypse_waits_15_frames_then_mends_2_every_7():
    s = simsmall.small_world([('apoc', APOC, 'Player_1', 0.0, 0.0)])
    b = s.bodies['apoc']
    full = b.max_hp
    autoheal(s, 0)                                     # seen at full health
    b.damage(600)
    hp = {}
    for frame in range(1, 101):
        autoheal(s, frame)
        hp[frame] = b.hp
    assert hp[15] == full - 600                        # the wait: hurt at frame 1, first mend at 16
    assert hp[16] == full - 598 and hp[22] == full - 598 and hp[23] == full - 596
    assert hp[100] == full - 600 + 2 * 13              # mends at 16, 23, ..., 100
    assert 'autoheal' in s.used


def test_a_fresh_hurt_restarts_the_wait_and_full_health_stops_it():
    s = simsmall.small_world([('apoc', APOC, 'Player_1', 0.0, 0.0)])
    b = s.bodies['apoc']
    full = b.max_hp
    autoheal(s, 0)
    b.damage(3)
    for frame in range(1, 20):
        autoheal(s, frame)
    assert b.hp == full - 1                            # mended at 16
    b.damage(1)                                        # hurt again at frame 20: next mend at 35, not 23
    for frame in range(20, 35):
        autoheal(s, frame)
    assert b.hp == full - 2
    autoheal(s, 35)
    assert b.hp == full
    for frame in range(36, 60):
        autoheal(s, frame)
    assert b.hp == full and b.find(interfaces.Update)[0].heal_at is None


def test_asleep_at_full_health_and_woken_by_a_hurt_a_heal_to_full_or_a_raised_maximum():
    """Step K2: the module sleeps at full health and between mends; Body.damage / mend / health_moved wake it (at
    the frame of the cell that told it), as the every-frame module of step K1 saw the health move."""
    s = simsmall.small_world([('apoc', APOC, 'Player_1', 0.0, 0.0)])
    b = s.bodies['apoc']
    (m,) = (m for m in b.find(interfaces.Update) if m.PHASE == 'autoheal')   # it has CrusherInfo, a toggle too
    for frame in range(0, 6):
        autoheal(s, frame)
    assert awake(s) == set() and m.heal_at is None                  # full health: asleep from its first run
    b.damage(4)
    autoheal(s, 6)                                                  # hurt at 5: waits to 6 + 15
    assert s.world.schedule.awake('autoheal') == {m: 21} and m.heal_at == 21
    b.mend(3)
    assert s.world.schedule.awake('autoheal') == {m: 21}            # healed, not to full: still waits for 21
    b.mend(1)                                                       # to full by another hand: woken, heal_at cleared
    autoheal(s, 7)
    assert awake(s) == set() and m.heal_at is None
    b.max_hp += 10                                                  # a raised maximum (named_set_max_health)
    b.health_moved(b.hp, b.hp)
    autoheal(s, 8)
    assert m.heal_at == 15 and s.world.schedule.awake('autoheal') == {m: 15}
    b.alive = False
    b.damage(1)
    autoheal(s, 9)
    assert awake(s) == set()                                        # dead: asleep for good
