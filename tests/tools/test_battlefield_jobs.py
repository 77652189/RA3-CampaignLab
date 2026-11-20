"""Battlefield's placing of factory jobs (experimental/cnv/simbattlefield.py place_things; step S 11d step 7, work/re/
sim_split/bf_pack/plan.md): a run cut with the player's barracks part way through a scout (some of its 200 paid), its file
placed onto an empty run of the same map: the job reads back whole, and run on the host pays only what is left and
comes out as many frames after the cut as on the source; a job full and waiting at its door at the cut comes out at
the source's frame too; an upgrade bought at a yard goes on the same. The sample barracks (ai_open) reads back at half,
paid 100. A job the source holds for a ban is named by the export (the file does not carry the ban: placed, it goes
on); a job the host's factory does not build is named and not placed, the job behind it placed; paid over the host's
cost is named."""
import json
from pathlib import Path

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simbattlefield  # noqa: E402
import simsmall  # noqa: E402
from engine.ports.observe import Observe  # noqa: E402
from maps import niagara, probe_range  # noqa: E402

P1 = 'Player_1'
BARRACKS, SCOUT, YARD, REFINERY = 'AlliedBarracks', 'AlliedScoutInfantry', 'AlliedConstructionYard', 'AlliedRefinery'
TECH2 = 'Upgrade_AlliedTech2'
DATA = Path(__file__).resolve().parent.parent / 'fixtures' / 'battlefield'


def _source(cut, objects=(('barracks', BARRACKS, P1, 2000.0, 2000.0), ('plant', 'AlliedPowerPlant', P1, 2400.0, 2000.0)), order=SCOUT, money=5000):
    w = simsmall.small_world(list(objects), model=False, map=probe_range)
    w.money[P1] = money
    assert w.order_build(P1, order)
    w.run(cut)
    return w


def _host(doc, m=probe_range):
    host = simsmall.small_world(model=False, map=m)
    return host, simbattlefield.place(host, doc)


def _go_on(w, seconds):
    """Money spent and the frames (from now) things came out at, after `seconds` more."""
    frame0, money0 = w.frame_now(), w.money[P1]
    before = {b.serial for b in w.living()}
    w.run(w.t + seconds)
    out = sorted(round(b.made_at * w.fps) - frame0 for b in w.living() if b.serial not in before and b.made_by)
    return money0 - w.money[P1], out


def _job(doc, thing):
    return next(t for t in doc['things'] if t['id'] == thing)['queue']


def test_a_part_built_scout_goes_on_paying_what_is_left():
    src = _source(0.5)
    doc = simbattlefield.export(Observe(src))
    assert simbattlefield.check(doc) == []
    [job] = _job(doc, 'barracks')
    assert (job['template'], job['full']) == (SCOUT, None) and 0 < job['progress'] < 1 and 0 < job['paid'] < 200
    host, gaps = _host(doc)
    assert gaps == []
    assert _job(simbattlefield.export(Observe(host)), 'barracks') == [job]
    host.money[P1] = src.money[P1]
    spent_src, out_src = _go_on(src, 3.0)
    spent_host, out_host = _go_on(host, 3.0)
    assert spent_src == spent_host == 200 - job['paid']
    assert out_host == out_src and len(out_src) == 1


def test_a_full_job_at_its_door_comes_out_at_the_sources_frame():
    src = _source(1.5)
    doc = simbattlefield.export(Observe(src))
    [job] = _job(doc, 'barracks')
    assert job['progress'] == 1 and job['full'] is not None and job['full'] <= doc['frame']
    host, gaps = _host(doc)
    assert gaps == []
    assert _job(simbattlefield.export(Observe(host)), 'barracks')[0]['full'] == job['full'] + host.frame_now() - doc['frame']
    host.money[P1] = src.money[P1] = 0          # all paid: nothing left to pay, out with none
    spent_s, out_s = _go_on(src, 2.0)
    assert _go_on(host, 2.0) == (spent_s, out_s) == (0, out_s) and len(out_s) == 1 and out_s[0] < 10


def test_an_upgrade_bought_at_a_yard_goes_on_the_same():
    objects = (('yard', YARD, P1, 2000.0, 2000.0), ('refinery', REFINERY, P1, 2600.0, 2600.0))
    src = _source(3.0, objects, TECH2)
    doc = simbattlefield.export(Observe(src))
    [job] = _job(doc, 'yard')
    assert job['template'] == TECH2 and 0 < job['progress'] < 1 and 0 < job['paid']
    host, gaps = _host(doc)
    assert gaps == []
    host.money[P1] = src.money[P1]
    for w in (src, host):
        money0 = w.money[P1]
        w.run(w.t + 120.0)
        assert TECH2 in w.bodies['yard'].upgrades
        w.spent = money0 - w.money[P1]
    assert host.spent == src.spent > 0


def test_the_sample_barracks_reads_back_at_half_paid_100():
    doc = json.loads((DATA / 'ai_open.json').read_text(encoding='utf-8'))
    host = simsmall.small_world(model=False, map=niagara)
    assert simbattlefield.place_things(host, doc) == []
    [job] = host.queues[host.bodies['#ai 285 AlliedBarracks'].serial]
    assert (job['template'], job['owner'], job['paid'], job['full'], job['cost']) == (SCOUT, 'Soviet_1', 100, None, 200)
    host.money['Soviet_1'] = 1000
    host.run(host.t + 3.0)
    assert host.money['Soviet_1'] == 900
    assert [b.template for b in host.living() if b.made_by == '#ai 285 AlliedBarracks'] == [SCOUT]


def test_a_job_held_for_a_ban_is_named_and_goes_on_where_placed():
    src = _source(0.5)
    src.banned.add((P1, SCOUT.lower()))
    src.run(src.t + 0.5)
    doc = simbattlefield.export(Observe(src))
    i = next(k for k, t in enumerate(doc['things']) if t['id'] == 'barracks')
    assert f'things[{i}].queue[0]: {SCOUT} held by a build ban the file does not carry (placed, it goes on)' \
        in doc['gaps']
    host, gaps = _host(doc)
    assert gaps == []
    host.money[P1] = src.money[P1]
    assert _go_on(src, 3.0) == (0, [])
    spent, out = _go_on(host, 3.0)
    assert spent == 200 - _job(doc, 'barracks')[0]['paid'] and len(out) == 1


def test_a_job_the_host_does_not_build_is_named_the_one_behind_placed():
    doc = simbattlefield.export(Observe(_source(1.0)))
    i = next(k for k, t in enumerate(doc['things']) if t['id'] == 'barracks')
    [job] = doc['things'][i]['queue']
    doc['things'][i]['queue'] = [dict(job, template='AlliedPowerPlant'), dict(job, paid=500)]
    host, gaps = _host(doc)
    assert gaps[:2] == [f"things[{i}].queue[0]: a {BARRACKS} builds no AlliedPowerPlant in the host's data (not placed)",
                        f"things[{i}].queue[1].paid: 500 over the host's cost 200 (held to it)"]
    assert [(j['template'], j['paid']) for j in host.queues[host.bodies['barracks'].serial]] == [(SCOUT, 200)]
    assert gaps[2].startswith(f'things[{i}].queue: ')


def test_a_job_full_before_the_placing_reads_back_before_frame_0_and_places_again():
    """Review 1120cc P2: a scout full at frame 30 of a cut at 38, placed onto a run at frame 0, filled at -8 on the
    host's clock; its export is a file the check takes, and placed again it comes out at the same frame."""
    src = _source(2.0)
    doc = simbattlefield.export(Observe(src))
    [job] = _job(doc, 'barracks')
    assert job['full'] is not None and doc['frame'] - job['full'] > 0
    host, gaps = _host(doc)
    assert gaps == [] and host.frame_now() == 0
    back = simbattlefield.export(Observe(host))
    assert _job(back, 'barracks') == [dict(job, full=job['full'] - doc['frame'])] and _job(back, 'barracks')[0]['full'] < 0
    assert simbattlefield.check(back) == []
    again, gaps = _host(back)
    assert gaps == [] and _job(simbattlefield.export(Observe(again)), 'barracks') == _job(back, 'barracks')
    src.money[P1] = host.money[P1] = again.money[P1] = 0
    out = _go_on(src, 2.0)
    assert _go_on(host, 2.0) == _go_on(again, 2.0) == out and len(out[1]) == 1
