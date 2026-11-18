"""Self-healing as a rule (AutoHealBehavior, engine/modules/autoheal.py since step K1; ADR 0029 "测试分两层"): on the
minimal world, only the frame order's autoheal cell runs. The whole-mission version against the bench is
test_simbench.py::test_autoheal_an_apocalypse_mends_two_points_every_7_frames_after_a_15_frame_wait (engine_heal a).
The module's own tests: tests/modules/test_autoheal.py."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simsmall  # noqa: E402

APOC = 'SovietAntiVehicleVehicleTech3'        # AutoHealBehavior: 2 points every 7 frames, 15 frames after a hurt


def autoheal(s, frame):
    s.world.schedule.run('autoheal', frame)


def test_a_hurt_apocalypse_waits_15_frames_then_mends_2_every_7():
    s = simsmall.small_world([('apoc', APOC, 'Player_1', 0.0, 0.0)])
    b = s.bodies['apoc']
    full = b.max_hp
    autoheal(s, 0)                                     # seen at full health
    b.hp = full - 600
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
    b.hp = full - 3
    for frame in range(1, 20):
        autoheal(s, frame)
    assert b.hp == full - 1                            # mended at 16
    b.hp -= 1                                          # hurt again at frame 20: next mend at 35, not 23
    for frame in range(20, 35):
        autoheal(s, frame)
    assert b.hp == full - 2
    autoheal(s, 35)
    assert b.hp == full
    for frame in range(36, 60):
        autoheal(s, frame)
    assert b.hp == full and b.modules[0].heal_at is None
