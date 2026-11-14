"""experimental/cnv/inject.py ("注入看", engine line D round 135): ra3ext log lines -> one kind of record (frame, unit,
what, program piece). The log here is made up in the bench's line shapes (work/re/d133_airevk2.md, d132_whenidle.md:
the airevk2 reverse order and the aibdi1 garrison order); the program places are fake tokens and the names table is
passed in, so nothing private is spelled here."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'experimental', 'cnv'))
import inject  # noqa: E402

LOG = """\
team: frame=241 list=1 proto=P1 name1='Soviet_1' name2='c2bd8cee_SimpleAttack_0_0' rel=1 pri=7 slot=0 team=T1 active=1 n=2 ids=3170@0:0,3171@0:0
tstate: frame=241 team=T1 mstate=2 prev=8 secs=0.00 tgt=3176 chosen=-1 tact=-1 idle=0 ready=0 mem=3170:1:0,3171:1:0 dest= aim= hd=
tstate: frame=256 team=T1 mstate=2 prev=8 secs=1.00 tgt=3176 chosen=-1 tact=-1 idle=0 ready=0 mem=3170:1:0,3171:1:0 dest= aim= hd=
goal: frame=272 team=T1 mem=3171 st=1 old=0 new=3262 want=3262 lock=0 ra=xG1 bt= n=0
cmd: frame=302 msg=M1 type=1f5 player=4 n=3 args=2:1,2:0,4:3171 src=xR1
cmd: frame=302 msg=M2 type=236 player=4 n=1 args=7:3622.3:3361.5:212.5 src=xR2
cmd: frame=332 msg=M3 type=1f5 player=4 n=3 args=2:1,2:0,4:3170 src=xS1
cmd: frame=332 msg=M4 type=1f5 player=4 n=3 args=2:0,2:0,4:3171 src=xS1
cmd: frame=332 msg=M5 type=210 player=4 n=2 args=4:0,4:3169 src=xE1
sst: frame=333 mem=3170 old=1 new=16 goal=0 p300=x0 lastcmd=0x5@1 ra=xT1 bt=
"""

NAMES = {'xR2': 'ReverseMove', 'xE1': 'EnterBaseDefensesWhenIdle'}


def _log(tmp_path):
    p = tmp_path / 'ra3ext.log'
    p.write_text(LOG, encoding='utf-8')
    return str(tmp_path)


def test_an_order_is_given_to_the_unit_selected_just_before_it(tmp_path):
    evs = inject.look(_log(tmp_path), kinds=('command',))
    assert [(e.frame, e.unit) for e in evs] == [(302, '3171'), (332, '3170,3171')]
    assert evs[0].what == '移动(倒车)到 (3622.3, 3361.5)'
    assert evs[1].what.endswith('对象 3169')


def test_the_program_piece_is_named_from_the_private_table_or_shown_raw(tmp_path):
    out = inject.text(inject.look(_log(tmp_path)), names=NAMES)
    assert 'f302 3171 command 移动(倒车)到 (3622.3, 3361.5) <- ReverseMove' in out
    assert '<- EnterBaseDefensesWhenIdle' in out
    assert 'f272 3171 goal 目标 0 -> 3262 <- xG1' in out          # not in the table: raw, on screen only


def test_team_lines_only_when_state_or_target_change_and_named_by_template(tmp_path):
    evs = inject.look(_log(tmp_path), kinds=('team',))
    assert len(evs) == 1 and evs[0].unit == 'team:c2bd8cee_SimpleAttack_0_0'
    assert evs[0].what.startswith('队伍状态 2 目标 3176')


def test_unit_and_frame_filters(tmp_path):
    run = _log(tmp_path)
    assert [e.kind for e in inject.look(run, unit=3170)] == ['command', 'state']
    assert [e.frame for e in inject.look(run, frames=(300, 332))] == [302, 332]


def test_unknown_kind_is_refused(tmp_path):
    try:
        inject.look(_log(tmp_path), kinds=('garrisons',))
    except AssertionError as e:
        assert 'unknown kinds' in str(e)
    else:
        raise AssertionError('no refusal')


# "注入摆" (round 135b): plan lines, the build's plan file, the bench's hand-over, the dll's poke lines read back
POKES = """cmd: at 250 queued 'pos UNIT - CNV AI Rev Foe 1 3530.0 3230.0' frame=0
poke: frame=250 op=pos id=-1 name='UNIT - CNV AI Rev Foe 1'
poke: frame=250 op=pos id=3177 was=3505.0:3420.0 now=3553.0:3304.0 name='UNIT - CNV AI Rev Foe 2'
"""


def test_a_plan_line_names_the_frame_the_object_and_the_place():
    assert inject.pos(250, 'UNIT - CNV AI Rev Foe 2', 3553, 3304) == 'at 250 pos UNIT - CNV AI Rev Foe 2 3553.0 3304.0'
    for bad in ((-1, 'A', 0, 0), (2.5, 'A', 0, 0), (1, ' A', 0, 0), (1, "A'B", 0, 0), (1, '', 0, 0)):
        try:
            inject.pos(*bad)
        except AssertionError:
            continue
        raise AssertionError(f'accepted {bad}')


def test_poke_lines_read_back_as_records(tmp_path):
    (tmp_path / 'ra3ext.log').write_text(POKES, encoding='utf-8')
    evs = inject.look(str(tmp_path), kinds=('poke',))
    assert [(e.frame, e.unit, e.what) for e in evs] == [
        (250, '-1', '摆 UNIT - CNV AI Rev Foe 1 没找到'),
        (250, '3177', '摆 UNIT - CNV AI Rev Foe 2 3505.0,3420.0 -> 3553.0,3304.0')]
    assert inject.look(str(tmp_path), kinds=('command',)) == []        # the dll's own 'cmd: at' line is no order


def test_the_build_writes_the_plan_only_with_lines_and_the_bench_hands_it_over(tmp_path):
    import package
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'experimental',
                                    'testbench'))
    import harness
    mod, run = tmp_path / 'mod', tmp_path / 'run'
    mod.mkdir()
    run.mkdir()
    args = ['game.exe', '-modConfig', str(mod / 'x.skudef')]
    line = inject.pos(250, 'UNIT - CNV AI Rev Foe 2', 3553, 3304)
    package.mark_plan(str(mod), [line])
    assert (mod / package.PLAN).read_text(encoding='ascii') == line + '\n'
    assert harness.hand_plan(args, str(run))
    assert (run / 'ra3ext_cmd.txt').read_text(encoding='ascii') == line + '\n'
    package.mark_plan(str(mod), ())
    assert not (mod / package.PLAN).exists()
    assert not harness.hand_plan(args, str(tmp_path / 'other'))
    assert not package.ra3ext_plan_ok(['x' * 200]) and not package.ra3ext_plan_ok(['a\nb'])


def test_a_test_parts_plan_lines_join_the_missions():
    import model
    m = model.Mission(inject=['at 1 pos A 0.0 0.0'])
    t = model.Test(inject=['at 2 pos B 0.0 0.0'])
    assert model.merged(m, t).inject == ['at 1 pos A 0.0 0.0', 'at 2 pos B 0.0 0.0']
