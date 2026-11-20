"""Battlefield's placing of the script's state (experimental/cnv/engine/state/battlefield.py place_script / place; step S 11d
step 5, work/re/sim_split/bf_pack/plan.md): a run cut while one timer runs, one has run out and one is stopped, its
file placed onto a run of the same map whose clock reads another time: each table reads back on the file's clock, and
the scripts that wait on those timers fire as many frames after the placing as the source's did after the cut (the
time base is the cut, not either clock). Placing writes the tables, runs no script, notes nothing and decides no
ending, even for a file whose won flag is up; a deadline the host cannot hold as the file has it is named."""
import json
from pathlib import Path

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import parts  # noqa: E402
import sim  # noqa: E402
import engine.state.battlefield as simbattlefield  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
from engine.ports.observe import Observe  # noqa: E402
from maps import probe_range  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / 'fixtures' / 'battlefield'
CUT = 3.0
ARM = parts.Script('Arm', [], [('SET_MILLISECOND_TIMER', 'Fuse', 4.0), ('SET_MILLISECOND_TIMER', 'Two', 2.0),
                               ('SET_MILLISECOND_TIMER', 'Held', 6.0), ('SET_FLAG', 'Armed', 1),
                               ('SET_COUNTER', 'Score', 7), ('SET_MISSION_OBJECTIVE_STATUS', 'Goal', 1)])
STOP = parts.Script('Stop', [('TIMER_EXPIRED', 'Two')], [('STOP_TIMER', 'Held')])
# what waits on the timers: the source has them from the start, the host only these (the ones that ran are history)
WAIT = [parts.Script('Out', [('TIMER_EXPIRED', 'Fuse')], [('SET_FLAG', 'Blown', 1), ('RESTART_TIMER', 'Held')]),
        parts.Script('Late', [('TIMER_EXPIRED', 'Held')], [('SET_FLAG', 'Late', 1)])]


def _run(scripts):
    w = sim.Sim(parts.Mission(name='T', map=probe_range, scripts=scripts), model=False)
    for name in list(w.bodies):              # the map's own things: an empty host (simsmall.small_world)
        w.world.drop(w.bodies.pop(name))
    return w


def _cut():
    w = _run([ARM, STOP] + WAIT)
    w.run(CUT)
    return w, simbattlefield.export(Observe(w))


def _frames_to(w, flags, seconds):
    """Run `w` on `seconds`; the executor's frames after now at which each of `flags` first reads up."""
    seen, steps, step = {}, [0], w.executor.step

    def counted():
        step()
        steps[0] += 1
        for f in flags:
            if w.flags.get(f) == 1:
                seen.setdefault(f, steps[0])
    w.executor.step = counted
    w.run(w.t + seconds)
    return seen


def test_the_cut_holds_a_running_an_out_and_a_stopped_timer():
    w, doc = _cut()
    s = doc['script']
    assert s['timers']['Fuse'] > doc['t'] >= s['timers']['Two']      # running, out
    assert 'Held' not in s['timers'] and s['counters']['Held'] > 0     # stopped: its frames left a counter
    assert (s['flags'], s['objectives'], s['counters']['Score']) == ({'Armed': True}, {'Goal': 1}, 7)
    assert simbattlefield.check(doc) == []


def test_each_table_reads_back_on_the_files_clock():
    _, doc = _cut()
    host = simsmall.small_world(model=False, map=probe_range)
    host.counters['Old'] = 3                # the host's own state goes: the tables are the file's
    host.flags['Old'] = 1
    host.objectives['Old'] = 2
    assert host.t != doc['t']
    assert simbattlefield.place(host, doc) == []
    ex = host.executor
    assert (ex.timer_expired('Fuse'), ex.timer_expired('Two'), ex.timer_expired('Held')) == (False, True, False)
    assert ex.counters['Held'] == [doc['script']['counters']['Held'], False]
    assert 'Old' not in ex.counters and 'Old' not in host.flags and 'Old' not in host.objectives
    got = simbattlefield.export(Observe(host))['script']   # on the host's clock: the same frames left
    assert {k: round((d - host.t) * host.fps) for k, d in got['timers'].items()} == \
        {k: round((d - doc['t']) * host.fps) for k, d in doc['script']['timers'].items()}


def test_the_timers_run_out_as_many_frames_after_the_placing_as_after_the_cut():
    w, doc = _cut()
    host = _run(WAIT)
    assert simbattlefield.place(host, doc) == []
    want = _frames_to(w, ('Blown', 'Late'), 8)
    assert set(want) == {'Blown', 'Late'} and want['Late'] > want['Blown']     # the stopped one ran on after
    assert _frames_to(host, ('Blown', 'Late'), 8) == want


def test_placing_runs_no_script_notes_nothing_and_decides_no_ending():
    doc = json.loads((DATA / 'levelvision_a.json').read_text(encoding='utf-8'))
    doc['script']['flags'] = {'Mission Won': True, 'Armed': False}
    doc['script']['objectives'] = {'Goal': 2, 'Bonus': 3}
    host = _run([parts.Script('Any', [], [('SET_FLAG', 'Ran', 1)])])
    before = (host.t, host.frame_now(), host.executor.steps, list(host.log))
    assert simbattlefield.place(host, doc) == [
        'script.flags.Mission Won: placed, the host does not end on it (placing decides no ending)']
    assert (host.t, host.frame_now(), host.executor.steps, list(host.log)) == before
    assert (host.ending, 'Ran' in host.flags) == (None, False)
    assert (host.flags['Mission Won'], host.objectives) == (1, {'Goal': 2, 'Bonus': 3})


def test_a_deadline_the_host_cannot_hold_is_named():
    doc = json.loads((DATA / 'levelvision_a.json').read_text(encoding='utf-8'))
    t = doc['t']
    doc['script']['timers'] = {'Long out': t - 10, 'Between': t + 0.01, 'On a frame': t + 2}
    host = simsmall.small_world(model=False, map=probe_range)
    gaps = simbattlefield.place_script(host, doc)
    assert [g.split(':')[0] for g in gaps] == ['script.timers.Between', 'script.timers.Long out']
    assert all("held to the host's frame" in g for g in gaps)
    c = host.executor.counters
    assert (c['Long out'], c['Between'], c['On a frame']) == ([-1, True], [0, True], [30, True])


def test_a_file_the_host_cannot_take_places_no_script():
    doc = json.loads((DATA / 'levelvision_a.json').read_text(encoding='utf-8'))
    doc['map'] = 'niagara'
    host = simsmall.small_world(model=False, map=probe_range)
    try:
        simbattlefield.place_script(host, doc)
    except ValueError as e:
        assert "map: 'niagara', the host is 'probe_range'" in str(e)
    else:
        raise AssertionError('placed')
    assert dict(host.counters) == {} and dict(host.timers) == {}


def _host_with_state():
    """An empty run of the map whose script has written a counter, a flag and an objective (to be kept or replaced)."""
    host = simsmall.small_world(model=False, map=probe_range)
    review = parts.Script('Review', [], [])
    host.act('SET_COUNTER', ['Original', 9], review)
    host.act('SET_FLAG', ['Up', 1], review)
    host.act('SET_MISSION_OBJECTIVE_STATUS', ['Goal', 1], review)
    return host


def test_a_deadline_no_whole_number_of_host_frames_is_refused_before_anything_is_written():
    """Review 1120bb P2: a finite deadline so far from the cut that x the host's frame rate it is infinite (1.3e308,
    -1.3e308, or a cut that far from it) is named by preflight; placing it raises the refusal and the host's exact
    snapshot is as it was (it raised OverflowError after the counters were already the file's)."""
    import engine.state.snapshot as simsnap
    for at, deadline in (('Huge', 1.3e308), ('Huge', -1.3e308), ('t', 1.3e308)):
        doc = json.loads((DATA / 'levelvision_a.json').read_text(encoding='utf-8'))
        if at == 't':
            doc['t'] = deadline
        else:
            doc['script']['timers'][at] = deadline
        doc['script']['counters']['FromFile'] = 7
        assert simbattlefield.check(doc) == [], at
        host = _host_with_state()
        bad = simbattlefield.preflight(host, doc, things=False)
        named = sorted(doc['script']['timers']) if at == 't' else [at]
        assert [b.split(':')[0] for b in bad] == [f'script.timers.{k}' for k in named], bad
        assert all("no whole number of the host's frames" in b for b in bad)
        before = simsnap.snapshot(host)
        for place in (simbattlefield.place_script, simbattlefield.place):
            try:
                place(host, doc)
            except ValueError as e:
                assert 'script.timers.' in str(e)
            else:
                raise AssertionError(f'{place.__name__} placed {at}={deadline!r}')
            assert simsnap.snapshot(host) == before, place.__name__


def test_the_tables_are_worked_out_before_any_is_written(monkeypatch):
    """A table entry that cannot be worked out (here a timer's frames left raising) leaves all four tables as they
    were: none is written before every one is worked out."""
    doc = json.loads((DATA / 'levelvision_a.json').read_text(encoding='utf-8'))
    doc['script']['counters']['FromFile'] = 7
    assert doc['script']['timers']
    host = _host_with_state()
    tables = lambda: (dict(host.executor.counters), dict(host.flags), dict(host.objectives))  # noqa: E731
    before = tables()

    def broken(sim, doc, deadline):
        raise OverflowError('cannot convert float infinity to integer')
    monkeypatch.setattr(simbattlefield, '_frames_left', broken)
    try:
        simbattlefield._set_script(host, doc)
    except OverflowError:
        pass
    else:
        raise AssertionError('worked out')
    assert tables() == before
