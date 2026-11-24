"""The StoreCurrentStateUpdate module (engine/modules/storestate.py, E223): its thing's place and health every SleepTime,
the oldest kept MaxTime + SPAN frames back -- where Tanya's time belt takes her. On the bench: checks/engine_storestate_e.py
(the belt's press itself: its readings, tests/conformance)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.testing.small as simsmall  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.modules import storestate  # noqa: E402

KEEPER = '''<GameObject id="CNV_TestKeeper" Side="Neutral" KindOf="INFANTRY">
  <Behaviors><StoreCurrentStateUpdate id="ModuleTag_Store" SleepTime="0.25s" MaxTime="2s"/></Behaviors>
</GameObject>'''


def test_the_oldest_state_kept_is_max_time_and_span_frames_old():
    s = simsmall.small_world()
    s.own['CNV_TestKeeper'] = KEEPER
    s.add('k', 'CNV_TestKeeper', 'Player_1', 100.0, 100.0)
    b = s.bodies['k']
    (m,) = b.find(interfaces.Rewind)
    assert (m.data.every, m.data.keep) == (3, 30)
    for f in range(200):
        b.x = 100.0 + f                     # its place says the frame
        s.world.schedule.run('expire', f)
    x, y, hp = m.oldest()
    last = m.kept[-1][0]                    # its latest state's frame (one every 3)
    assert last >= 197 and 30 + storestate.SPAN - 3 < last - (x - 100.0) <= 30 + storestate.SPAN and hp == b.hp
