"""The SuppressionUpdate module (engine/modules/suppression.py, step M6): its data read from the block (UpdateDelay and
SuppressionDuration seconds x 15 rounded up, UpdateDelay at least a frame), samples on its birth phase every
UpdateDelay, entering leaves the end untouched, an already suppressed high sample sets the end on, only a low sample
strictly after the end clears it, the host told on each change (World.modify), the fields asked of the host every
frame (World.suppression_at), a Remove block taking the inherited module away, and its state in the frame record where
the body's fields were. On the bench: engine_suppress_probe tail / lifetime / duration / expiry
(tests/test_simbench_c.py)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simrecord  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
import engine.data.units as simunits  # noqa: E402
from engine.kernel import interfaces, module, world as kernel_world  # noqa: E402
from engine.modules import suppression  # noqa: E402

HEAD = ' id="ModuleTag_Supp" Suppressability="50" UpdateDelay="1s" SuppressionDuration="5s"' \
       ' AttributeModifierSuppressed="Modifier_Test"'
MAN = '''<GameObject id="CNV_TestSuppMan" KindOf="INFANTRY">
  <Behaviors>
    <SuppressionUpdate''' + HEAD + ''' />
  </Behaviors>
</GameObject>'''
FREE = '''<GameObject id="CNV_TestSuppFree" inheritFrom="CNV_TestSuppMan" KindOf="INFANTRY">
  <Behaviors>
    <SuppressionUpdate id="ModuleTag_Supp" xai:joinAction="Remove" />
  </Behaviors>
</GameObject>'''


def test_the_block_is_read_seconds_x_15_rounded_up():
    d = suppression.SuppressionData.parse(HEAD, '')
    assert d.rules() == dict(threshold=50.0, every=15, duration=75, modifier='Modifier_Test')
    d = suppression.SuppressionData.parse(' UpdateDelay="1.1s" SuppressionDuration="0.01s"', '')
    assert (d.every, d.duration) == (17, 1)
    d = suppression.SuppressionData.parse(' UpdateDelay="0s"', '')
    assert (d.threshold, d.every, d.duration, d.modifier) == (0.0, 1, 0, None)


class Man(module.Thing):
    name, template, alive = 'man', 'CNV_TestSuppMan', True


def _man(made, fields):
    told = []
    w = kernel_world.World(lambda t, tag: [(HEAD, '')] if tag == 'SuppressionUpdate' else [],
                           modify=told.append, suppression_at=lambda thing, f: [p for p in fields if f < p[0]])
    thing = Man()
    thing.modules = w.build(thing, made)
    return thing.find(interfaces.Suppression), told


def _run(m, frames):
    return {f: (m.is_suppressed(), m.until()) for f in frames if m.update(f) == 1}


def test_samples_on_its_birth_phase_entering_keeps_the_end_and_a_high_sample_sets_it_on():
    fields = [(1000, 50)]
    m, told = _man(7, fields)
    assert (m.next_sample(), m.until(), m.is_suppressed()) == (7, 0, False)
    got = _run(m, range(1, 7))
    assert all(v == (False, 0) for v in got.values()) and m.hits() == [(1000, 50)]     # hits every frame, no sample
    assert _run(m, [7]) == {7: (True, 0)} and m.next_sample() == 22                     # entering: the end untouched
    assert told == [m.thing]
    assert _run(m, range(8, 22))[21] == (True, 0)
    assert _run(m, [22]) == {22: (True, 97)}                                            # refreshed: 22 + 75
    assert told == [m.thing]


def test_only_a_low_sample_strictly_after_the_end_clears_it():
    fields = [(23, 50)]
    m, told = _man(1, fields)
    _run(m, range(1, 17))           # samples 1 (enter), 16 (refresh: end 91)
    assert (m.is_suppressed(), m.until()) == (True, 91)
    _run(m, range(17, 91))          # fields gone at 23; low samples at 31 .. 76 are not after the end
    assert (m.is_suppressed(), m.until(), m.hits()) == (True, 91, [])
    assert _run(m, [91]) == {91: (True, 91)}                                            # 91 > 91 is false: held
    _run(m, range(92, 106))
    assert m.is_suppressed() and _run(m, [106]) == {106: (False, 91)}                   # the next sample clears it
    assert told == [m.thing, m.thing]


def test_a_late_sample_keeps_the_phase_and_below_the_threshold_nothing_enters():
    fields = [(1000, 49.5)]
    m, told = _man(4, fields)
    _run(m, [40])                   # samples 4, 19, 34 missed: the next on the phase after 40
    assert m.next_sample() == 49 and not m.is_suppressed() and told == []


def test_a_dead_man_samples_nothing():
    m, told = _man(1, [(1000, 50)])
    m.thing.alive = False
    assert m.update(1) == 1 and not m.is_suppressed() and m.hits() == [] and told == []


def test_a_remove_block_takes_the_inherited_module_away_and_the_record_keeps_the_fields():
    s = simsmall.small_world()
    s.own.update({'CNV_TestSuppMan': MAN, 'CNV_TestSuppFree': FREE})
    assert simunits.module_blocks('CNV_TestSuppFree', 'SuppressionUpdate', s.own) == []
    s.add('man', 'CNV_TestSuppMan', 'Player_1', 100.0, 100.0)
    s.add('free', 'CNV_TestSuppFree', 'Player_1', 300.0, 100.0)
    man, free = s.bodies['man'], s.bodies['free']
    assert free.find(interfaces.Suppression) is None
    state = simrecord.body_state(free)
    assert [state[k] for k in ('suppression_rule', 'suppression_hits', 'suppressed', 'suppressed_until',
                               'suppression_next')] == [None, (), False, -1, 0]
    made = s.eng.frame if s.eng is not None else 0
    state = simrecord.body_state(man)
    assert state['suppression_rule'] == man.suppression_rule == dict(threshold=50.0, every=15, duration=75,
                                                                    modifier='Modifier_Test')
    assert [state[k] for k in ('suppression_hits', 'suppressed', 'suppressed_until', 'suppression_next')] == \
        [[], False, 0, max(1, made)]
    now = max(1, made)
    s.suppression_fields = [(now, 70, 100.0, 100.0, 20), (made + 100, 60, 100.0, 100.0, 20),
                            (made + 100, 60, 300.0, 100.0, 20), (made + 100, 80, 125.0, 100.0, 20)]
    s.world.schedule.run('suppression', now)    # its lifetime out at `now`; 25 away is out of a radius of 20
    assert man.suppression_hits == [(made + 100, 60)] and free.suppression_hits == ()
