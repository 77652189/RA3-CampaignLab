"""The game adapter's step 1 (experimental/testbench/gameport.py; work/re/sim_split/adapter_pack/plan.md 会话 1): a
fixed bench map's reading contract read back off a recorded transcript, no bench.

The transcript (tests/fixtures/gameport/formss_1112_222747.json) is `gameport.py record` on the archived run
CampFormSS_mcp_1112_222747 (bench D 94, PASS): its 29 frames' index entries and counter lines as counters.read reads
the PNGs. The acceptance reads it as it is; the refusal cases change a copy of it (a value dropped, a frame taken
out, a presence line given) -- they test the adapter's refusals, they are not bench readings."""
import copy
import dataclasses
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location('gameport', ROOT / 'experimental' / 'testbench' / 'gameport.py')
gp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gp)

TRANSCRIPT = json.loads((ROOT / 'tests' / 'fixtures' / 'gameport' / 'formss_1112_222747.json').read_text('utf-8'))
TANK, MAN = 'UNIT - CNV Form Plain 0', 'UNIT - CNV Form Plain 2'


def run_all(adapter):
    out = []
    while (s := adapter.step()) is not None:
        out.append(s)
    return out


def answers(tr):
    return [c['answer'] for c in tr['calls'] if c['answer'] is not None]


def test_the_recorded_run_reads_back_as_the_bench_read_it():
    a = gp.replay(gp.FORMSS, TRANSCRIPT)
    samples = run_all(a)
    assert len(samples) == 29 and a.transport.left() == 0
    assert all(s.fresh and s.source == 'archive' and s.run == 'CampFormSS_mcp_1112_222747' for s in samples)
    assert [s.seq for s in samples] == list(range(1, 30)) and [s.archive_id for s in samples] == list(range(1, 30))
    # cnv_result: counters s1-s40: 0 0 0 0 | s56-s78: 22 0 86 0 | s80-s118: 22 22 86 18
    by_second = {s.second: s.values for s in samples}
    assert by_second[40.0] == (0, 0, 0, 0) and by_second[56.2] == (22, 0, 86, 0) and by_second[118.3] == (22, 22, 86, 18)
    o = a.observe
    assert o.counters() == {'CNV_Form_Plain': 22, 'CNV_Form_Formation': 22, 'CNV_Form_Plain_Ahead': 86,
                            'CNV_Form_Formation_Ahead': 18}
    assert (o.t, o.frame(), o.fps, o.human) == (118.3, 1047, 15, 'Player_1')
    # the two clocks are two sources: the bench's second (wall time x rate) runs ahead of the logic frames here
    assert o.frame() / o.fps < o.t
    # a frame skipped over is delivered as it is: 1026 -> 1047
    assert samples[-1].skipped == 1047 - 1026 - 1


def test_bound_things_are_references_with_the_fields_the_bench_does_not_read_missing():
    a = gp.replay(gp.FORMSS, TRANSCRIPT)
    a.step()
    o = a.observe
    tank = o.thing(TANK)
    assert (tank.template, tank.owner, tank.serial) == ('CNV_FormTank', 'Player_1',
                                                        gp.Ref('CampFormSS_mcp_1112_222747', TANK, 1))
    assert o.is_thing(tank) and not o.is_thing(TANK) and o.thing('nobody') is None
    assert [t.name for t in o.things()] == [f'UNIT - CNV Form {lane} {k}' for lane in ('Plain', 'Formation')
                                            for k in range(4)]
    assert o.thing(MAN).template == 'CNV_FormMan'
    assert tank.hp is gp.MISSING and tank.x is gp.MISSING and tank.alive is gp.MISSING
    with pytest.raises(gp.NotRead):
        tank.hp < 100
    with pytest.raises(gp.NotRead):
        bool(tank.alive)
    with pytest.raises(AttributeError):
        tank.no_such_field
    assert a.resolve(tank.serial) == tank


def test_calls_with_no_bench_channel_are_refused():
    a = gp.replay(gp.FORMSS, TRANSCRIPT)
    a.step()
    o = a.observe
    with pytest.raises(gp.Unsupported, match='presence'):
        o.living()
    with pytest.raises(gp.Unsupported, match='does not report its end'):
        o.ending()
    for call in ('sees', 'money', 'timers', 'state', 'firing', 'queues'):
        with pytest.raises(gp.Unsupported):
            getattr(o, call)


def test_the_replay_refuses_an_ask_out_of_order_or_past_the_end():
    r = gp.Replay(TRANSCRIPT)
    with pytest.raises(gp.TranscriptError, match='call 1'):
        r.call(dict(tool='sample', lines=3))
    a = gp.replay(gp.FORMSS, TRANSCRIPT)
    run_all(a)
    with pytest.raises(gp.TranscriptError, match='after the transcript'):
        a.step()


def test_a_transcript_answers_only_the_contract_it_was_read_with():
    """Review 1120aa P2: a contract of as many lines (here the same four reversed, under another map's name) replayed
    the run and filed the plain lane's 22 under CNV_Form_Formation_Ahead. The sample ask names the lines in order,
    and the map is checked: another order, other names or another map are refused before a reading is taken."""
    assert TRANSCRIPT['calls'][0]['ask'] == dict(tool='sample', lines=[ln.counter for ln in gp.FORMSS.lines])
    reversed_lines = dataclasses.replace(gp.FORMSS, lines=gp.FORMSS.lines[::-1])
    with pytest.raises(gp.TranscriptError, match='call 1'):
        gp.replay(reversed_lines, TRANSCRIPT).step()
    renamed = dataclasses.replace(gp.FORMSS, lines=gp.FORMSS.lines[:3]
                                  + (dataclasses.replace(gp.FORMSS.lines[3], counter='CNV_Other'),))
    with pytest.raises(gp.TranscriptError, match='call 1'):
        gp.replay(renamed, TRANSCRIPT).step()
    with pytest.raises(gp.TranscriptError, match="a transcript of 'CampFormSS', the contract is 'DifferentMap'"):
        gp.replay(dataclasses.replace(gp.FORMSS, mod='DifferentMap'), TRANSCRIPT)


def test_a_recorder_keeps_what_it_passed_on():
    rec = gp.Recorder(gp.Replay(TRANSCRIPT).call, mod='CampFormSS', run=TRANSCRIPT['run'], source='archive')
    run_all(gp.GameAdapter(gp.FORMSS, rec, TRANSCRIPT['run']))
    assert rec.transcript['calls'] == TRANSCRIPT['calls']


def test_a_line_not_read_is_missing_not_zero():
    tr = copy.deepcopy(TRANSCRIPT)
    answers(tr)[6]['values'][1] = None              # frame 7 (s56.2): the formation line not read
    a = gp.replay(gp.FORMSS, tr)
    s = run_all(a)[6]
    assert s.values == (22, gp.MISSING, 86, 0)
    assert s.covers == frozenset({'CNV_Form_Plain', 'CNV_Form_Plain_Ahead', 'CNV_Form_Formation_Ahead'})


def test_frames_skipped_repeated_or_going_back():
    tr = copy.deepcopy(TRANSCRIPT)
    del tr['calls'][2:5]                            # frames 3-5 taken out: 56 -> 371
    s = run_all(gp.replay(gp.FORMSS, tr))
    assert (s[2].archive_id, s[2].skipped, s[2].fresh) == (6, 371 - 56 - 1, True)
    tr = copy.deepcopy(TRANSCRIPT)
    answers(tr)[1].update(frame=44, second=1.1)     # frame 2 a repeat of frame 1: not a fresh sample
    s = run_all(gp.replay(gp.FORMSS, tr))
    assert (s[1].fresh, s[1].skipped, s[2].fresh) == (False, 0, True)
    tr = copy.deepcopy(TRANSCRIPT)
    answers(tr)[2]['frame'] = 40
    with pytest.raises(gp.SampleError, match='logic frame 40 before 56'):
        run_all(gp.replay(gp.FORMSS, tr))
    tr = copy.deepcopy(TRANSCRIPT)
    answers(tr)[2]['second'] = 1.0
    with pytest.raises(gp.SampleError, match='second 1.0 before 2.1'):
        run_all(gp.replay(gp.FORMSS, tr))
    tr = copy.deepcopy(TRANSCRIPT)                  # no ra3ext: the clock is the second alone
    for x in answers(tr):
        x['frame'] = None
    s = run_all(gp.replay(gp.FORMSS, tr))
    assert all(x.frame is gp.MISSING and x.skipped is gp.MISSING and x.fresh for x in s)


def test_menu_frames_and_frames_with_no_second_are_no_samples():
    tr = copy.deepcopy(TRANSCRIPT)
    answers(tr)[3].update(menu=True, note='menu: hold')
    with pytest.raises(gp.SampleError, match='menu frame'):
        run_all(gp.replay(gp.FORMSS, tr))
    tr = copy.deepcopy(TRANSCRIPT)
    answers(tr)[3]['second'] = None
    with pytest.raises(gp.SampleError, match='no mission second'):
        run_all(gp.replay(gp.FORMSS, tr))
    with pytest.raises(gp.SampleError, match='no sample yet'):
        gp.replay(gp.FORMSS, TRANSCRIPT).observe.counters()


def test_a_thing_made_again_under_its_name_does_not_take_the_old_reference():
    # the plain lane's line taken as the tank's presence (a refusal test: the map publishes none)
    contract = dataclasses.replace(gp.FORMSS, things=(dataclasses.replace(gp.FORMSS.things[0],
                                                                          presence='CNV_Form_Plain'),),
                                   groups=(), goals=())
    tr = copy.deepcopy(TRANSCRIPT)
    for k in (8, 9):                                # frames 9-10 read 0: gone; frame 11 on 22: made again
        answers(tr)[k]['values'][0] = 0
    a = gp.replay(contract, tr)
    for _ in range(7):
        a.step()                                    # frame 7: 22, the first generation alive
    first = a.observe.thing(TANK)
    assert first.alive is True and first.serial.generation == 1 and a.observe.living() == [first]
    a.step()
    a.step()                                        # frame 9: 0
    assert a.observe.thing(TANK).alive is False and a.observe.living() == []
    with pytest.raises(gp.StaleRef, match='gone'):
        a.resolve(first.serial)
    a.step()
    a.step()                                        # frame 11: back
    again = a.observe.thing(TANK)
    assert again.serial.generation == 2 and a.resolve(again.serial) == again
    with pytest.raises(gp.StaleRef, match='generation 1'):
        a.resolve(first.serial)
    with pytest.raises(gp.StaleRef, match='run'):
        a.resolve(dataclasses.replace(again.serial, run='another'))
    with pytest.raises(gp.StaleRef, match='not a thing this map binds'):
        a.resolve(gp.Ref(a.run, MAN, 1))
    tr = copy.deepcopy(TRANSCRIPT)                  # a presence line not read: living() says which thing, where
    answers(tr)[0]['values'][0] = None
    a = gp.replay(contract, tr)
    a.step()
    with pytest.raises(gp.Unsupported, match='not read in archive frame 1'):
        a.observe.living()


def test_the_ending_stops_the_samples():
    # the plain lane all in taken as a win (a refusal test: the map reports no end)
    contract = dataclasses.replace(gp.FORMSS, ending=gp.Ending('CNV_Form_Plain', 22, '赢', 'all four in'))
    a = gp.replay(contract, TRANSCRIPT)
    for _ in range(6):
        a.step()
        assert a.observe.ending() is None
    a.step()
    assert a.observe.ending() == ('赢', 56.2, 'all four in')
    with pytest.raises(gp.SampleError, match='after the ending'):
        a.step()


def test_a_transcript_is_made_from_an_archived_runs_index(tmp_path):
    (tmp_path / 'index.json').write_text(json.dumps(dict(mod='CampFormSS', frames=[
        dict(id=1, second=None, note='menu: walk', view=None), dict(id=2, second=3.0, note='watch', view=None,
                                                                    frame=40)])), 'utf-8')
    tr = gp.transcript_from_archive(str(tmp_path), gp.FORMSS, read=lambda p, n: [p.endswith('0002.png')] * n)
    assert [c['answer'] for c in tr['calls']] == [
        dict(id=1, second=None, frame=None, note='menu: walk', menu=True, values=[None] * 4),
        dict(id=2, second=3.0, frame=40, note='watch', menu=False, values=[True] * 4), None]
    with pytest.raises(ValueError, match='a run of CampFormSS'):
        gp.transcript_from_archive(str(tmp_path), dataclasses.replace(gp.FORMSS, mod='Other'))


def test_a_contract_names_only_its_own_lines():
    with pytest.raises(ValueError, match='twice'):
        gp.Contract('m', 'P', (gp.Line('c', 'a'), gp.Line('c', 'b')))
    with pytest.raises(ValueError, match='presence'):
        gp.Contract('m', 'P', (gp.Line('c', 'a'),), (gp.Bound('u', 'T', 'P', presence='d'),))
    with pytest.raises(ValueError, match='ending'):
        gp.Contract('m', 'P', (gp.Line('c', 'a'),), ending=gp.Ending('d', 1, '赢', ''))


# --- step 2 (plan.md 会话 2): the player's group move as the bench's inputs, confirmed by the map's own count.
# tests/fixtures/gameport/formss_1112_222747_inputs.json is `gameport.py record ... --steps` on the same run, the steps
# engine_formation_player.sync_moves(formation_bench.sync_mission()) hands the bench (unchanged since the run, fb2d917c):
# its view, two boxes and two right clicks are asks answered by their archived pause records.
INPUTS = json.loads((ROOT / 'tests' / 'fixtures' / 'gameport' / 'formss_1112_222747_inputs.json').read_text('utf-8'))
_cspec = importlib.util.spec_from_file_location('command_port_for_gameport',
                                                ROOT / 'experimental' / 'cnv' / 'engine' / 'ports' / 'command.py')
cp = importlib.util.module_from_spec(_cspec)
_cspec.loader.exec_module(cp)
PLAIN = tuple(f'UNIT - CNV Form Plain {k}' for k in range(4))
FORMATION = tuple(f'UNIT - CNV Form Formation {k}' for k in range(4))


def move(units, **kw):
    return cp.Command('move', units=units, **kw)


def started(tr=INPUTS, contract=gp.FORMSS):
    a = gp.replay(contract, tr)
    for _ in range(3):                  # the run's first watch: 3 samples, then its inputs
        a.step()
    return a


def test_the_players_two_group_moves_go_as_the_bench_gave_them_and_the_maps_count_confirms_each():
    a = started()
    plain, formation = move(PLAIN, place='@1000.0,1230.0'), move(FORMATION[::-1], pos=(1000.0, 1390.0))
    ok, why = a.commands.do(plain)
    assert ok is None and 'click archive frame 6 (frame 371)' in why     # issued, not yet known
    assert a.commands.do(formation)[0] is None
    samples = run_all(a)
    assert a.transport.left() == 0 and a.sample.seq == 29 and len(samples) == 21
    (f1, c1, ok1, why1), (f2, c2, ok2, why2) = a.commands.sent()
    # plain: all four in by the formation box's record (frame 491); formation: by s80.3 (frame 670), not at s78.3
    assert (f1, c1, ok1) == (371, plain, True) and why1.endswith('CNV_Form_Plain reads 22 at archive frame 7 (frame 491)')
    assert (f2, c2, ok2) == (593, formation, True) and why2.endswith('reads 22 at archive frame 10 (frame 670)')
    assert a.commands.kinds() == {'move'}


def test_a_move_the_bench_cannot_give_is_refused_with_nothing_sent():
    a = started()
    left = a.transport.left()
    for cmd, why in [(move(PLAIN[:3], pos=(1000.0, 1230.0)), 'not one group'),          # a box takes the whole group
                     (move(PLAIN[:2] + FORMATION[:2], pos=(1000.0, 1230.0)), 'not one group'),
                     (move(PLAIN, place='Test Form Plain Goal'), 'no named place'),
                     (cp.Command('move', by='ai:Player_2', units=PLAIN, pos=(1000.0, 1230.0)), 'human player only'),
                     (cp.Command('attack', units=PLAIN, target='enemy'), 'no archived bench run'),
                     (cp.Command('stop', units=PLAIN), 'no bench route')]:
        ok, got = a.commands.do(cmd)
        assert ok is False and why in got
    assert a.transport.left() == left and all(ok is False for *_, ok, _ in a.commands.sent())
    fresh = gp.replay(gp.FORMSS, INPUTS)
    assert fresh.commands.do(move(PLAIN, pos=(1000.0, 1230.0))) == (False, 'no sample yet')
    with pytest.raises(gp.Unsupported):
        a.commands.post(move(PLAIN, pos=(1000.0, 1230.0)), 5)


def test_a_group_is_not_sent_twice_and_another_order_is_checked_against_the_recorded_one():
    a = started()
    a.commands.do(move(PLAIN, pos=(1000.0, 1230.0)))
    ok, why = a.commands.do(move(PLAIN, pos=(1000.0, 1230.0)))       # no receipt yet: no blind retry
    assert ok is False and 'no blind retry' in why
    a.commands.do(move(FORMATION, pos=(1000.0, 1390.0)))              # its box record reads plain 22: confirmed
    ok, why = a.commands.do(move(PLAIN, pos=(900.0, 1230.0)))
    assert ok is False and 'no box selects it now' in why
    other = started()
    with pytest.raises(gp.TranscriptError, match='bench_box'):        # formation first: not the recorded input
        other.commands.do(move(FORMATION, pos=(1000.0, 1390.0)))


def test_a_move_with_no_receipt_stays_unknown_to_the_end():
    # refusal tests on changed copies (not bench readings): the plain click asked 100 west of the goal; the plain
    # lane never reading 22
    tr = copy.deepcopy(INPUTS)
    tr['calls'][5]['ask']['x'] = 900.0
    tr['calls'][5]['answer']['note'] = 'right click at screen (767, 431)'     # where the bench draws (900, 1230)
    a = started(tr)
    ok, why = a.commands.do(move(PLAIN, pos=(900.0, 1230.0)))
    assert ok is None and 'no receipt route' in why
    tr = copy.deepcopy(INPUTS)
    for c in tr['calls']:
        if c['answer']:
            c['answer']['values'][0] = 0
    b = started(tr)
    b.commands.do(move(PLAIN, pos=(1000.0, 1230.0)))
    b.commands.do(move(FORMATION, pos=(1000.0, 1390.0)))
    run_all(b)
    (_, _, ok1, why1), (_, _, ok2, _) = b.commands.sent()
    assert ok1 is None and why1.endswith("no receipt by the run's end") and ok2 is True


def test_an_input_answered_by_another_record_is_not_taken_as_given():
    tr = copy.deepcopy(INPUTS)
    tr['calls'][4]['answer']['note'] = 'right click at screen (1, 2)'     # the box's record is not a box select
    a = started(tr)
    ok, why = a.commands.do(move(PLAIN, pos=(1000.0, 1230.0)))
    assert ok is False and 'bench_box: archive frame 5' in why and a.sample.archive_id == 4
    tr = copy.deepcopy(INPUTS)
    tr['calls'][5]['answer']['paused'] = False                           # the click not followed by the pause
    a = started(tr)
    ok, why = a.commands.do(move(PLAIN, pos=(1000.0, 1230.0)))
    assert ok is None and 'click unsure' in why
    assert 'no blind retry' in a.commands.do(move(PLAIN, pos=(1000.0, 1230.0)))[1]


def archived(tmp_path, tr=INPUTS):
    """An archived run folder put back from a transcript with inputs (the run's own folder is no longer on disk):
    index.json's frames, cnv_result.txt's step lines (`; paused` as recorded), and a reader that gives each frame's
    recorded values."""
    got = [c for c in tr['calls'] if c['answer'] is not None]
    (tmp_path / 'index.json').write_text(json.dumps(dict(mod=tr['mod'], frames=[
        {k: c['answer'][k] for k in ('id', 'second', 'frame', 'note')} for c in got])), 'utf-8')
    (tmp_path / 'cnv_result.txt').write_text('\n'.join(
        f'{c["ask"]["tool"]}: {c["answer"]["note"]} frame {c["answer"]["id"]} at mission second '
        f'{c["answer"]["second"]}{"; paused" if c["answer"]["paused"] else ""}'
        for c in got if c['ask']['tool'] != 'sample') + '\n', 'utf-8')
    values = {c['answer']['id']: c['answer']['values'] for c in got}
    return str(tmp_path), (lambda p, n: values[int(Path(p).stem)])


def test_an_archived_runs_inputs_convert_only_as_the_bench_drew_them(tmp_path):
    # review 1120bb P2 #4: the converter checked a record's note by its start only, so the first click's step moved
    # from (1000, 1230) to (1010, 1230) still took the record of a click drawn at (924, 421), and the replay then
    # confirmed the changed point with the run's real count
    run, read = archived(tmp_path)
    tr = gp.transcript_with_inputs(run, gp.FORMSS, INPUTS['steps'], read=read)
    assert {k: v for k, v in tr.items() if k != 'run'} == {k: v for k, v in INPUTS.items() if k != 'run'}
    for i, key, value, frame in [(3, 'x', 1010.0, 6), (3, 'y', 1231.0, 6), (2, 'x1', 700.0, 5), (1, 'x', 826.0, 4),
                                 (5, 'y', 1380.0, 8)]:
        steps = copy.deepcopy(INPUTS['steps'])
        steps[i][1][key] = value
        with pytest.raises(ValueError, match=f'archive frame {frame}: records .* -- not the input given then'):
            gp.transcript_with_inputs(run, gp.FORMSS, steps, read=read)
    with pytest.raises(ValueError, match='no archived frame left'):
        gp.transcript_with_inputs(run, gp.FORMSS, INPUTS['steps'] + [INPUTS['steps'][3]], read=read)


def test_a_record_of_another_point_confirms_no_move():
    # the same change made in the transcript itself (the ask at 1010, the record still the click drawn at 1000): the
    # click's record is not the input asked, the move stays unknown -- the plain count reaching 22 confirms nothing
    tr = copy.deepcopy(INPUTS)
    tr['calls'][5]['ask']['x'] = 1010.0
    a = started(tr)
    ok, why = a.commands.do(move(PLAIN, pos=(1010.0, 1230.0)))
    assert ok is None and "click unsure: bench_click: archive frame 6 records 'right click at screen (924, 421)'" in why
    assert "the input asked draws 'right click at screen (939, 420)'" in why
    a.commands.do(move(FORMATION, pos=(1000.0, 1390.0)))
    run_all(a)
    (_, _, ok1, why1), (_, _, ok2, _) = a.commands.sent()
    assert ok1 is None and why1.endswith("no receipt by the run's end") and ok2 is True
    tr = copy.deepcopy(INPUTS)
    tr['calls'][4]['ask']['x1'] = 700.0                                   # the box's ask, its record kept
    a = started(tr, dataclasses.replace(gp.FORMSS, groups=(dataclasses.replace(gp.FORMSS.groups[0], box=(
        560.0, 1175.0, 700.0, 1285.0)),) + gp.FORMSS.groups[1:]))
    ok, why = a.commands.do(move(PLAIN, pos=(1000.0, 1230.0)))
    assert ok is False and 'bench_box: archive frame 5' in why and 'the input asked draws' in why


def test_a_member_not_here_is_not_moved():
    # the plain lane's line taken as its first tank's presence (a refusal test: the map publishes none); it reads 0
    things = (dataclasses.replace(gp.FORMSS.things[0], presence='CNV_Form_Plain'),) + gp.FORMSS.things[1:]
    a = started(contract=dataclasses.replace(gp.FORMSS, things=things))
    ok, why = a.commands.do(move(PLAIN, pos=(1000.0, 1230.0)))
    assert ok is False and 'UNIT - CNV Form Plain 0: not here' in why
