"""Battlefield's AI yards (experimental/cnv/simbattlefield.py step 9; step S 11d after step 8, the coordinator's 11-20
scope): a yard builds its structures in the skirmish AI's own queue (simai Brain.yard_q), so ai_open's cut at 41 s lost
the three its yard had queued (a refinery 55 % built, a refinery and a power plant not started). With the run's AI the
export lists them in the yard's queue; placed onto an empty run of the map with its AI they go into the host AI's
queue and come back whole; the half refinery goes on from where it was, paying only what is left, and fills the same
frame after the cut as on the source. With no AI on the host each is named by its path, not placed."""
import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import build  # noqa: E402
import sim  # noqa: E402
import simai  # noqa: E402
import simbattlefield  # noqa: E402
import simrecord  # noqa: E402
import simsmall  # noqa: E402
from engine.ports.observe import Observe  # noqa: E402
from test_battlefield_export import CUTS, _run  # noqa: E402

YARD = 'UNIT - CNV AI Yard'
AI = 'Soviet_1'


@pytest.fixture(scope='module')
def cut():
    m, w, _, doc, _ = _run('ai_open')
    return m, w, doc


def _host(m):
    """An empty run of the map whose mission seats the AI as the source's does (its sides: which players the AI runs
    is not in the file), and its AI."""
    host = simsmall.small_world(model=False, map=m.map)
    host.m.sides.update(m.sides)
    return host, simai.SimAI(host)


def _yard(doc):
    return next((i, t) for i, t in enumerate(doc['things']) if t['id'] == YARD)


def test_the_export_lists_the_ai_yards_queue(cut):
    m, w, doc = cut
    _, row = _yard(doc)
    assert [j['template'] for j in row['queue']] == ['AlliedRefinery', 'AlliedRefinery', 'AlliedPowerPlant']
    half = row['queue'][0]
    assert 0.5 < half['progress'] < 0.6 and half['paid'] > 0 and half['full'] is None
    assert all(j == {'template': j['template'], 'progress': 0.0, 'paid': 0, 'full': None} for j in row['queue'][1:])
    without = simbattlefield.export(Observe(w))     # no AI given: the yard's own queue only (it has none)
    assert _yard(without)[1]['queue'] == []
    assert simbattlefield.check(doc) == []


def test_the_yards_queue_comes_back_whole_with_the_hosts_ai(cut):
    m, _, doc = cut
    host, ai = _host(m)
    diffs = simbattlefield.round_trip(host, doc, ai)
    i, _ = _yard(doc)
    assert [p for p, why in diffs if p.startswith(f'things[{i}].queue')] == []
    assert [p for p, why in diffs if why is None] == []
    q = ai.brains[AI].yard_q
    assert [j['template'] for jobs in q.values() for j in jobs] == ['AlliedRefinery', 'AlliedRefinery',
                                                                     'AlliedPowerPlant']


def test_without_an_ai_on_the_host_each_structure_is_named(cut):
    m, _, doc = cut
    host = simsmall.small_world(model=False, map=m.map)
    i, row = _yard(doc)
    gaps = simbattlefield.place(host, doc)
    named = [g for g in gaps if g.startswith(f'things[{i}].queue[')]
    assert [g.split(':', 1)[0] for g in named] == [f'things[{i}].queue[{j}]' for j in range(len(row['queue']))]
    assert all('builds no' in g for g in named)
    diffs = simbattlefield.round_trip(simsmall.small_world(model=False, map=m.map), doc)
    assert dict(diffs)[f'things[{i}].queue'] is not None       # the difference has its gap


def test_a_host_ai_that_runs_no_such_player_names_each(cut):
    m, _, doc = cut
    host, ai = _host(m)
    i, row = _yard(doc)
    bad = dict(doc, things=[dict(t, owner='Player_1') if t['id'] == YARD else t for t in doc['things']])
    gaps = simbattlefield.place_things(host, bad, ai)
    named = [g for g in gaps if g.startswith(f'things[{i}].queue[')]
    assert len(named) == len(row['queue']) and all('-- ' in g for g in named), named


def test_a_defence_goes_into_the_yards_defence_queue_and_reads_after_its_structures(cut):
    """A base defence (FS_BASE_DEFENSE) is queued in the yard's defence queue beside its structures' (Brain.queue_of):
    one the file lists first comes back after the structures, the difference named by the queue's gap."""
    m, _, doc = cut
    i, row = _yard(doc)
    tower = {'template': 'AlliedBaseDefense', 'progress': 0.25, 'paid': 100, 'full': None}
    file_ = dict(doc, things=[dict(t, queue=[tower] + t['queue']) if t['id'] == YARD else t for t in doc['things']])
    host, ai = _host(m)
    diffs = dict(simbattlefield.round_trip(host, file_, ai))
    y = host.bodies[YARD]
    assert [j['template'] for j in ai.brains[AI].yard_q[(y.serial, 'defense')]] == ['AlliedBaseDefense']
    assert [j['template'] for j in ai.brains[AI].yard_q[y.serial]] == [j['template'] for j in row['queue']]
    assert ai.yard_jobs(y)[-1] == ('AlliedBaseDefense', 0.25, 100, None)
    assert f'things[{i}].queue' in diffs and diffs[f'things[{i}].queue'] is not None


def _source():
    """ai_open run to its cut with its AI kept (to go on with): (Sim, SimAI)."""
    kind, where, _ = simrecord.TASKS['ai_open']
    m, t, _ = build.resolve(*where)
    w = sim.Sim(m, t, model=False)
    ai = simai.SimAI(w)
    while w.t <= CUTS['ai_open']:
        ai.advance(1)
    return w, ai


def test_the_half_refinery_goes_on_and_fills_the_same_frame_after_the_cut(cut):
    """The source and the host each run on a frame at a time from the cut: the refinery's progress and paid step
    alike every frame, and it fills as many frames after the cut on both."""
    m, _, doc = cut
    src, src_ai = _source()
    host, ai = _host(m)
    simbattlefield.place(host, doc, ai)
    h0 = host.frame_now()

    def first(a, w):        # the job itself: it stays the same dict once taken out of the queue
        return a.brains[AI].yard_q[w.bodies[YARD].serial][0]
    js, jh = first(src_ai, src), first(ai, host)
    assert js['template'] == jh['template'] == 'AlliedRefinery' and js['full'] is None
    # each run's (frames after the cut -> (progress, paid)): a run goes a DT tick at a time, whose frames depend on
    # its clock's phase, so the two are compared at the frames both read
    s, h = {}, {}
    for _ in range(400):
        if js['full'] is None:
            s[src.frame_now() - doc['frame']] = (float(js['progress']), js['paid'])
            src_ai.advance(1)
        if jh['full'] is None:
            h[host.frame_now() - h0] = (float(jh['progress']), jh['paid'])
            ai.advance(1)
        if js['full'] is not None and jh['full'] is not None:
            break
    both = sorted(set(s) & set(h))
    assert len(both) > 5 and [s[f] for f in both] == [h[f] for f in both]
    assert js['full'] - doc['frame'] == jh['full'] - h0
    assert js['paid'] == jh['paid'] == js['cost']


@pytest.mark.parametrize('job, paid', [(dict(progress=0.1, paid=1000), 1000), (dict(progress=1.0, paid=100), 2000)])
def test_a_placed_yard_job_is_never_refunded_and_placed_only_paid_up(cut, job, paid):
    """Review 1120ee P2: 1000 paid at 10 % got 746 back; full but 100 of 2000 paid was placed free. Broke, the first
    builds free to the 50 % it paid for, the second waits; given 5000, the second pays its 1900 before it is placed."""
    m, _, doc = cut
    i, row = _yard(doc)
    things = list(doc['things'])
    things[i] = dict(row, queue=[dict(row['queue'][0], full=None if job['progress'] < 1 else doc['frame'] - 50, **job)])
    host, ai = _host(m)
    assert simbattlefield.place(host, dict(doc, things=things), ai) == []
    host.money[AI] = 0
    q = ai.brains[AI].yard_q[host.bodies[YARD].serial]
    first = q[0]
    ai.advance(60)
    assert host.wallet.held(AI) == 0 and first['paid'] == job['paid'] and q[0] is first
    host.money[AI] = 5000
    ai.advance(1)
    assert first['paid'] == paid if job['progress'] == 1 else first['paid'] >= 1000
    assert host.wallet.held(AI) <= 5000 - (paid - job['paid'])
