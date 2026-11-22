"""experimental/cnv/readings.py, the bench readings' format and the conformance runner's logic, on made-up runs (no
simulator): one run per scene, prefixes per until, each / scenes / let, the mismatch mark both ways."""
import ast
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location('readings', ROOT / 'experimental' / 'cnv' / 'readings.py')
rd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rd)


def write(tmp_path, text, name='engine_x'):
    p = tmp_path / f'{name}{rd.SUFFIX}'
    p.write_text(text, encoding='utf-8')
    return p


class Fake:
    """A world whose counter n reads its frame // FPS each second (the 'n' row of mission second t is t)."""
    started = []

    def __init__(self, b, c, **opts):
        self.frame, self.series, self.key, self.opts = 0, [], (b, c), opts
        Fake.started.append((b, c, opts) if opts else (b, c))

    def advance(self, frames):
        for _ in range(frames):
            self.frame += 1
            if self.frame % rd.FPS == 0:
                t = self.frame // rd.FPS
                self.series.append((t, {'n': t, 'k': 10 * t if self.key[0] == 'b2' else t}))


def run(readings, model=True):
    Fake.started = []
    out = []
    for keys, group in rd.groups(readings):
        out += rd.run_group(keys, group, Fake, lambda w, f: w.advance(f),
                            lambda w: ([t for t, _ in w.series], [r for _, r in w.series], {'frame': w.frame, **w.opts},
                                       [(w.frame % 2 == 0, f'frame {w.frame}')])
                            + (([{'frame': w.frame}],) if w.opts.get('teams') else ()), model)
    return out


DATA = '''
[[reading]]
id = "short"
scene = {build = "b1", check = "a", until = 5}
bench = "n 5 at the end"
proves = "x: y"
expect = ["rows[-1]['n'] == 5", "len(rows) == 5", "first('n', lambda v: v >= 3) == 2"]

[[reading]]
id = "long"
scene = {build = "b1", check = "a", until = 9}
bench = "-"
proves = "x: y"
let = {last = "rows[-1]", f = "lambda r: r['n'] * 2"}
expect = "f(last) == 18 and win(2, 4, 'n') == [2, 3, 4]"

[[reading]]
id = "each"
scene = {build = "b1", check = "a", until = 3}
each = [{build = "b1", want = 3}, {build = "b2", want = 30}]
bench = "-"
proves = "x: y"
expect = "rows[-1]['k'] == want"

[[reading]]
id = "pair"
scenes = {one = {build = "b1", check = "a", until = 4}, two = {build = "b3", check = "a", until = 4}}
bench = "-"
proves = "x: y"
expect = "one == two and first('n', rows=one) == 0"

[[reading]]
id = "b3_alone"
scene = {build = "b3", check = "a", until = 2}
bench = "-"
proves = "x: y"
expect = "rows[-1]['n'] == 2"

[[reading]]
id = "still_off"
scene = {build = "b1", check = "a", until = 9}
bench = "n 99"
proves = "x: y"
expect = "rows[-1]['n'] == 99"
mismatch = "sim 9, bench 99"
'''


def test_each_scene_runs_once_and_every_reading_sees_its_own_until(tmp_path):
    rs = rd.load(write(tmp_path, DATA))
    assert [r['id'] for r in rs] == ['short', 'long', 'each[b1]', 'each[b2]', 'pair', 'b3_alone', 'still_off']
    assert run(rs) == []
    assert sorted(Fake.started) == [('b1', 'a'), ('b2', 'a'), ('b3', 'a')]      # b1: four readings, one run
    assert [k for k, _ in rd.groups(rs)] == [[('b1', 'a', ()), ('b3', 'a', ())], [('b2', 'a', ())]]   # the pair joins
    # b1 and b3


def test_a_reading_that_does_not_hold_is_reported_and_a_mismatch_that_holds_too(tmp_path):
    bad = DATA.replace("rows[-1]['n'] == 5", "rows[-1]['n'] == 6").replace("== 99", "== 9")
    problems = run(rd.load(write(tmp_path, bad)))
    assert len(problems) == 2
    assert problems[0].startswith('short: does not hold') and 'drop the mark' in problems[1]


def test_a_reading_that_raises_fails_mismatch_mark_or_not(tmp_path):
    text = DATA.replace("len(rows) == 5", "rows[40]['n'] == 0")
    assert run(rd.load(write(tmp_path, text))) == ["short: IndexError: list index out of range"]
    marked = DATA.replace("rows[-1]['n'] == 99", "rows[40]['n'] == 99")      # a broken run is not "still off"
    assert run(rd.load(write(tmp_path, marked))) == ["still_off: IndexError: list index out of range"]
    in_let = DATA.replace('mismatch = "sim 9', 'let = {x = "1 / 0"}\nmismatch = "sim 9')
    assert run(rd.load(write(tmp_path, in_let))) == ["still_off: ZeroDivisionError: division by zero"]


NOMODEL = '''
[[reading]]
id = "off_without_model"
scene = {build = "b1", check = "a", until = 9}
bench = "n 99"
proves = "x: y"
expect = "rows[-1]['n'] == 99"
mismatch_nomodel = "sim 9 without the model, bench 99"
'''


def test_mismatch_nomodel_marks_a_reading_only_without_the_model(tmp_path):
    marked = rd.load(write(tmp_path, NOMODEL))
    assert run(marked, model=False) == []
    assert run(marked) == ["off_without_model: does not hold: rows[-1]['n'] == 99"]     # with the model: no mark
    bare = rd.load(write(tmp_path, NOMODEL.replace('mismatch_nomodel = "sim 9 without the model, bench 99"\n', '')))
    assert run(bare, model=False) == ["off_without_model: does not hold: rows[-1]['n'] == 99"]
    holds = rd.load(write(tmp_path, NOMODEL.replace('== 99', '== 9')))
    assert run(holds, model=False) == ['off_without_model: marked mismatch_nomodel but now holds -- drop the mark']
    assert run(holds) == []


EACH_SCENES = '''
[[reading]]
id = "same_as_b1"
scenes = {base = {build = "b1", check = "a", until = 4}, got = {build = "b1", check = "a", until = 4}}
each = [{got = {build = "b3"}, n = 4}, {got = {build = "b2"}, n = 40}]
bench = "-"
proves = "x: y"
expect = "got[-1]['k'] == n and first('n', rows=got) == 0"
'''


def test_each_overrides_a_named_scene_of_scenes(tmp_path):
    rs = rd.load(write(tmp_path, EACH_SCENES))
    assert [r['id'] for r in rs] == ['same_as_b1[b3]', 'same_as_b1[b2]']
    assert rs[0]['scenes'] == {'base': ('b1', 'a', 4.0, ()), 'got': ('b3', 'a', 4.0, ())} and rs[1]['vars'] == {'n': 40}
    assert run(rs) == []
    assert sorted(Fake.started) == [('b1', 'a'), ('b2', 'a'), ('b3', 'a')]
    assert run(rd.load(write(tmp_path, EACH_SCENES.replace('n = 40', 'n = 41')))) == [
        "same_as_b1[b2]: does not hold: got[-1]['k'] == n and first('n', rows=got) == 0"]


COUNTERS = '''
[[reading]]
id = "by_name"
scene = {build = "b1", check = "a", until = 4}
bench = "-"
proves = "x: y"
expect = ["counter('frame') == 60", "verdicts() == [(True, 'frame 60')]"]

[[reading]]
id = "by_name_later"
scene = {build = "b1", check = "a", until = 5}
bench = "-"
proves = "x: y"
expect = "counter('frame') == 75 and not verdicts()[0][0]"

[[reading]]
id = "by_scene"
scenes = {one = {build = "b1", check = "a", until = 4}, two = {build = "b2", check = "a", until = 2}}
bench = "-"
proves = "x: y"
expect = "counter('frame', 'one') - counter('frame', 'two') == 30 and verdicts('two')[0][0]"
'''


def test_counters_by_name_and_the_checks_verdicts_at_each_until(tmp_path):
    assert run(rd.load(write(tmp_path, COUNTERS))) == []
    missing = COUNTERS.replace("counter('frame') == 75", "counter('nope') == 75")
    assert run(rd.load(write(tmp_path, missing))) == ["by_name_later: KeyError: 'nope'"]
    unnamed = COUNTERS.replace("counter('frame', 'one')", "counter('frame')")
    assert run(rd.load(write(tmp_path, unnamed)))[0].startswith('by_scene: ReadingError: by_scene: name the scene')


RUN_OPTS = '''
[[reading]]
id = "plain"
scene = {build = "b1", check = "a", until = 3}
bench = "-"
proves = "x: y"
expect = "counter('frame') == 45 and 'script' not in vars()"

[[reading]]
id = "defaults_written_out"
scene = {build = "b1", check = "a", until = 2, script = "", shot_clock = false}
bench = "-"
proves = "x: y"
expect = "counter('frame') == 30"

[[reading]]
id = "scripted"
scene = {build = "b1", check = "a", until = 3, script = "5 摧毁 camp"}
bench = "-"
proves = "x: y"
expect = "counter('script') == '5 摧毁 camp'"

[[reading]]
id = "clocked"
scene = {build = "b1", check = "a", until = 4, shot_clock = true}
bench = "-"
proves = "x: y"
expect = "counter('shot_clock') is True and counter('frame') == 60"

[[reading]]
id = "per_entry"
scene = {build = "b1", check = "a", until = 2}
each = [{script = "不打"}, {script = "不打", shot_clock = true}, {build = "b2"}]
bench = "-"
proves = "x: y"
expect = "rows[-1]['n'] == 2"

[[reading]]
id = "compared"
scenes = {off = {build = "b1", check = "a", until = 2}, on = {build = "b1", check = "a", until = 2, shot_clock = true}}
bench = "-"
proves = "x: y"
expect = "off == on and 'shot_clock' not in vars() and counter('shot_clock', 'on')"
'''


def test_script_and_shot_clock_make_a_run_of_their_own(tmp_path):
    rs = rd.load(write(tmp_path, RUN_OPTS))
    assert [r['id'] for r in rs] == ['plain', 'defaults_written_out', 'scripted', 'clocked', 'per_entry[b1~script=不打]',
                                     'per_entry[b1~script=不打~shot_clock]', 'per_entry[b2]', 'compared']
    assert rs[1]['scenes']['rows'] == ('b1', 'a', 2.0, ())          # a default written out is the default
    assert rs[4]['scenes']['rows'] == ('b1', 'a', 2.0, (('script', '不打'),))
    assert run(rs) == []
    # one run per (build, check, options): the defaults share plain's, the entries' and the comparison's join the rest
    assert sorted(Fake.started, key=str) == sorted([
        ('b1', 'a'), ('b1', 'a', {'script': '5 摧毁 camp'}), ('b1', 'a', {'shot_clock': True}),
        ('b1', 'a', {'script': '不打'}), ('b1', 'a', {'script': '不打', 'shot_clock': True}), ('b2', 'a')], key=str)
    keys = [k for k, _ in rd.groups(rs)]
    assert [rd.label(k) for ks in keys for k in ks] == [
        'b1.a', 'b1.a~shot_clock', 'b1.a~script=5 摧毁 camp', 'b1.a~script=不打', 'b1.a~script=不打~shot_clock', 'b2.a']
    assert [len(ks) for ks in keys] == [2, 1, 1, 1, 1]               # the comparison joins b1.a and b1.a~shot_clock


TEAMS = '''
[[reading]]
id = "kept"
scene = {build = "b1", check = "a", until = 3, teams = true}
bench = "-"
proves = "x: y"
expect = "teams() == [{'frame': 45}]"

[[reading]]
id = "not_kept"
scene = {build = "b1", check = "a", until = 3}
bench = "-"
proves = "x: y"
expect = "teams() == []"
'''


def test_teams_is_a_run_of_its_own_and_teams_reads_its_trail(tmp_path):
    rs = rd.load(write(tmp_path, TEAMS))
    assert run(rs) == []
    assert sorted(Fake.started, key=str) == [('b1', 'a'), ('b1', 'a', {'teams': True})]


@pytest.mark.parametrize('scene, why', [('shot_clock = 1', 'shot_clock is a bool'), ('script = 5', 'script is a str'),
                                        ('shot = true', 'a scene is')])
def test_run_options_are_typed(tmp_path, scene, why):
    text = f'[[reading]]\nid = "a"\nscene = {{build = "b", until = 1, {scene}}}\nbench = "-"\nproves = "-"\nexpect = "1"\n'
    with pytest.raises(rd.ReadingError, match=why):
        rd.load(write(tmp_path, text))


@pytest.mark.parametrize('entry', ['{n = 4}', '{got = "b3"}', '{build = "b3", got = {build = "b3"}}'])
def test_an_each_entry_of_scenes_must_override_a_scene_by_table(tmp_path, entry):
    text = EACH_SCENES.replace('{got = {build = "b3"}, n = 4}', entry)
    with pytest.raises(rd.ReadingError, match='overrides a scene by name'):
        rd.load(write(tmp_path, text))


@pytest.mark.parametrize('text, why', [
    ('[[reading]]\nid = "a"\nbench = "-"\nproves = "-"\nexpect = "1"\n', 'one of scene / scenes'),
    ('[[reading]]\nid = "a"\nscene = {build = "b"}\nbench = "-"\nproves = "-"\nexpect = "1"\n', 'a scene is'),
    ('[[reading]]\nid = "a"\nscene = {build = "b", until = 1}\nproves = "-"\nexpect = "1"\n', 'missing'),
    ('[[reading]]\nid = "a"\nscene = {build = "b", until = 1}\nbench = "-"\nproves = "-"\nexpect = "1"\nwhy = 1\n',
     'unknown'),
    ('[[reading]]\nid = "a"\nscene = {build = "b", until = 1}\nbench = "-"\nproves = "-"\nexpect = "1"\n' * 2,
     'twice'),
    ('[foo]\n', 'only'),
    ('[[reading]]\nid = "a"\nscene = {build = "b", until = 1}\nbench = "-"\nproves = "-"\nexpect = "1"\n'
     'mismatch_nomodel = " "\n', 'non-empty'),
    ('[[reading]]\nid = "a"\nscene = {build = "b", until = 1}\nbench = "-"\nproves = "-"\nexpect = "1"\n'
     'mismatch_nomodel = true\n', 'non-empty'),
])
def test_the_format_is_checked_on_load(tmp_path, text, why):
    with pytest.raises(rd.ReadingError, match=why):
        rd.load(write(tmp_path, text))


ITEM = '[[reading]]\nid = "a"\nscene = {build = "b", until = 1}\nbench = "-"\nproves = "-"\nexpect = "1"\n'


def test_item_is_a_part_and_a_name_or_a_list_of_them_the_same_for_every_each_entry(tmp_path):
    one = rd.load(write(tmp_path, ITEM + 'item = "脚本动作 TEAM_HUNT"\n'))
    assert one[0]['items'] == [('脚本动作', 'TEAM_HUNT')]
    assert rd.load(write(tmp_path, ITEM))[0]['items'] == []
    many = rd.load(write(tmp_path, ITEM + 'item = ["物体模块 AI/AIUpdate", "AI 人格/x"]\n'
                                          'each = [{build = "b1"}, {build = "b2"}]\n'))
    assert [r['items'] for r in many] == [[('物体模块', 'AI/AIUpdate'), ('AI', '人格/x')]] * 2


@pytest.mark.parametrize('value', ['"TEAM_HUNT"', '"脚本动作  TEAM_HUNT"', '"脚本动作 TEAM HUNT"', '" TEAM_HUNT"', '[]',
                                   '3', '["脚本动作 X", 3]'])
def test_an_item_that_is_not_one_part_and_one_name_fails_on_load(tmp_path, value):
    with pytest.raises(rd.ReadingError, match='item'):
        rd.load(write(tmp_path, ITEM + f'item = {value}\n'))


def test_an_expression_that_does_not_compile_fails_on_load(tmp_path):
    with pytest.raises(SyntaxError):
        rd.load(write(tmp_path, DATA.replace("len(rows) == 5", "len(rows) ==")))


def test_the_repository_readings_load_and_sit_beside_their_bench():
    for p in rd.files():
        rs = rd.load(p)
        assert rs, p
        assert (Path(rd.CHECKS) / f'{rd.bench_of(p)}.py').is_file(), p


def _simai_constant(name):
    tree = ast.parse((ROOT / 'experimental' / 'cnv' / 'engine/ai/core.py').read_text(encoding='utf-8'))
    return [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and
            any(getattr(t, 'id', None) == name for t in n.targets)]


def test_the_runner_steps_at_the_simulators_frame_rate():
    assert _simai_constant('FPS') == [rd.FPS]


def test_the_default_blocks_are_the_simulators():
    assert _simai_constant('BLOCKS') == [rd.BLOCKS]


BLOCKS = '''
[[reading]]
id = "all"
scene = {build = "b1", check = "a", until = 2, blocks = ["specials", "targets", "micro", "defense"]}
bench = "-"
proves = "x: y"
expect = "counter('frame') == 30"

[[reading]]
id = "none"
scene = {build = "b1", check = "a", until = 2, blocks = []}
bench = "-"
proves = "x: y"
expect = "counter('blocks') == ()"

[[reading]]
id = "some"
scene = {build = "b1", check = "a", until = 3}
each = [{blocks = ["micro", "targets"]}, {blocks = []}]
bench = "-"
proves = "x: y"
expect = "counter('blocks') in [('targets', 'micro'), ()]"
'''


def test_blocks_empty_is_a_run_of_its_own_and_all_of_them_is_the_default(tmp_path):
    """blocks = [] (the opening benches' simai blocks=()) is not the default, as script "" is: its own run."""
    rs = rd.load(write(tmp_path, BLOCKS))
    assert [r['id'] for r in rs] == ['all', 'none', 'some[b1~blocks=targets+micro]', 'some[b1~blocks=none]']
    assert rs[0]['scenes']['rows'] == ('b1', 'a', 2.0, ())                       # every block, any order: the default
    assert rs[1]['scenes']['rows'] == ('b1', 'a', 2.0, (('blocks', ()),))
    assert rs[2]['scenes']['rows'] == ('b1', 'a', 3.0, (('blocks', ('targets', 'micro')),))   # in BLOCKS order
    assert run(rs) == []
    assert sorted(Fake.started, key=str) == sorted([('b1', 'a'), ('b1', 'a', {'blocks': ()}),
                                                    ('b1', 'a', {'blocks': ('targets', 'micro')})], key=str)
    assert [rd.label(k) for ks, _ in rd.groups(rs) for k in ks] == ['b1.a', 'b1.a~blocks=none',
                                                                     'b1.a~blocks=targets+micro']


@pytest.mark.parametrize('blocks', ['"targets"', '["targets", "targets"]', '["tactics"]'])
def test_blocks_names_simai_blocks_each_at_most_once(tmp_path, blocks):
    text = f'[[reading]]\nid = "a"\nscene = {{build = "b", until = 1, blocks = {blocks}}}\nbench = "-"\nproves = "-"\nexpect = "1"\n'
    with pytest.raises(rd.ReadingError, match='blocks'):
        rd.load(write(tmp_path, text))
