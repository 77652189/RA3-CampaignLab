"""The decoupled build layer (experimental/cnv): unit variants keep apart, a check merges into its mission, the
verdict follows the counters, the counter reader reads back its calibration -- all without the game."""
import dataclasses
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'experimental', 'cnv'))
sys.path.insert(1, os.path.join(ROOT, 'experimental', 'testbench'))
import build  # noqa: E402
import lint  # noqa: E402  (experimental/campaign, put on the path by parts)
import parts  # noqa: E402
import registry  # noqa: E402
from missions import a8_rough as a8, liberty_bench  # noqa: E402
from units import liberty as lib  # noqa: E402


def test_liberty_variants_keep_apart():
    a, b = lib.liberty('CNV_Liberty_A', tag='A'), lib.liberty('CNV_Liberty_B', tag='B')
    assert not set(a.names.values()) & set(b.names.values())
    assert 'SpecialPower_CNV_ChronoDeck_B' not in a.xml + a.files['CNV_Liberty_A_UI.xml']
    # every name it links is its own (in its XML or files: its look's buttons are in <id>_Look.xml); the Art's
    # textures (Texture:<image>_tex) are in the SDK's Art, not here
    text = b.xml + ''.join(b.files.values())
    assert all(n.split(':')[1] in text for n in b.link if not n.startswith('Texture:'))


def test_riders_left_out_of_the_deck(tmp_path):
    u = lib.liberty(riders='CNV_DeckGuardian')
    assert u.xml.count('<ExcludeThing>CNV_DeckGuardian</ExcludeThing>') == 3        # the filter and both templates
    assert '<ExcludeThing>' not in lib.liberty().xml
    p = tmp_path / 'CNV_Liberty.xml'
    p.write_text(u.xml, encoding='utf-8')
    assert [f for f in lint.check([str(p)]) if f[0] == 'ERROR'] == []


def test_check_merges_into_its_mission():
    m = liberty_bench.mission(riders=True)
    t = build.MISSIONS['liberty_riders'][1]['jump'](m)
    mm = parts.merged(m, t)
    assert len(mm.objects) == len(m.objects) and 'Test Jump Target' in mm.waypoints
    shown = [s for s in mm.scripts if s.name == 'Test - counters'][0]
    assert [a[1] for a in shown.do] == ['Test Crew', 'Test Landed', 'Test Deck']
    assert mm.strings['SCRIPT:CNVTEST_COUNTER2'] == '乘员在甲板'
    assert len(m.scripts) == 0                                   # the mission itself untouched


def test_areas_count_and_merge():
    m = liberty_bench.mission(riders=True)
    t = build.MISSIONS['liberty_riders'][1]['jump'](m)
    mm = parts.merged(m, t)
    assert list(mm.areas) == ['Test Landing'] and not m.areas
    assert parts.missing_areas(mm) == []
    landed = [s for s in mm.scripts if s.name.startswith('Test - count Test Landed')]
    assert len(landed) == 9 and landed[3].when[0][1:] == ('Player_1', 2, 3, m.role('crew').template, 'Test Landing')
    assert landed[8].when[0][1:3] == ('Player_1', 3) and landed[8].do == [('SET_COUNTER', 'Test Landed', 8)]
    del mm.areas['Test Landing']
    assert len(parts.missing_areas(mm)) == 9                     # assemble refuses to build that
    ab, _ = build.PAIRS['liberty_ride_ab']()
    b = parts.side_by_side(parts.Mission(areas={'X': parts.square(0, 0, 10)}), parts.Mission(areas={'Y': [(1, 2)]}), 5)
    assert b.areas == {'X': [(-10, -10), (10, -10), (10, 10), (-10, 10)], 'Y': [(6, 2)]}


def test_trigger_areas_round_trip():
    import mapscript
    m = object.__new__(mapscript.MapFile)
    m.nodes = [mapscript.Node('TriggerAreas', 1, b'\0\0\0\0', [])]
    areas = {'Test Landing': parts.square(1480, 2315, 150), 'B': [(1.5, 2.5), (3, 4), (5, 6)]}
    m.set_trigger_areas(areas)
    assert m.trigger_areas() == {k: [(float(x), float(y)) for x, y in v] for k, v in areas.items()}
    assert len(m.nodes[0].head) == 4 + sum(2 + len(k) + 2 + 8 + 8 * len(v) + 4 for k, v in areas.items())


def test_a8_assault_same_for_both():
    names = {}
    for build_name in ('a8_rough', 'a8_rough_control'):
        m, t, mod = build.resolve(build_name, 'assault')
        names[build_name] = mod
        mm = parts.merged(m, t)
        assert not [s for s in mm.scripts if s.name in ('CNV A8 - Win', 'CNV A8 - Lost')]
        assert parts.missing_areas(mm) == []
        labels = [label for _, label in t.counters]
        assert labels[:3] == ['平台剩余', '敌方铁锤', '守护者']
        jumps = [s for s in t.scripts if s.name.startswith('Test - jump ')]
        assert len(jumps) == (3 if build_name == 'a8_rough' else 0) and labels[3:] == (['自由号'] if jumps else ['多功能车'])
        assert t.bench[0][0] == 'bench_camera'
        order = [s.name for s in t.scripts]
        assert order.index('Test - order again') > order.index('Test - attack 3')   # the tick resets after the orders
    assert names == {'a8_rough': 'CampA8RAssault', 'a8_rough_control': 'CampA8RCAssault'}
    assert parts.kindof('VEHICLE')[2] == 'VEHICLE'


def test_a8_lose_moves_the_carrier():
    m = a8.mission()
    build.MISSIONS['a8_rough'][1]['lose'](m)
    c = m.find(m.role('carrier').name)
    assert (c.x, c.y) == m.site('west shore') and c.props == {'objectInitialHealth': 1}
    assert a8.mission().find(a8.CARRIER).props == {}


def test_every_build_keeps_the_contract():
    """Every object placed by a map site, every name a script uses published (offline: what assemble asserts)."""
    for n, (_, checks) in build.MISSIONS.items():
        for c in [''] + list(checks):
            m, t, _ = build.resolve(n, c)
            assert parts.contract(parts.merged(m, t)) == [], (n, c)
    for n in build.PAIRS:
        m, t, _ = build.resolve(n, '')
        assert parts.contract(parts.merged(m, t)) == [], n
    assert build.show('a8_rough', 'assault').endswith('contract: ok')


def test_a7_publishes_marks_facts_and_counts_by_name():
    m, t, mod = build.resolve('a7', 'jumps')         # a7 is its plan: the carrier device's landing points and timings
    assert {'carrier home', 'base edge', 'base ore', 'front'} <= set(m.marks) and m.point('base edge') == m.site('base edge')
    assert {'jump every', 'warning', 'stay', 'jump delay'} <= set(m.facts) and m.role('carrier').side == 's1'
    assert mod == 'CampA7Jumps'
    home = [s for s in t.scripts if s.name.startswith('Test - count Test At carrier home')]
    assert [s.when[0][0] for s in home] == ['NAMED_INSIDE_AREA', 'NAMED_OUTSIDE_AREA']
    assert any(a[0] == 'UNIT_SET_HEALTH' for s in t.scripts for a in s.do)       # pacing, not the fight
    assert a8.mission().role('hammer').sites == ['east 1', 'east 2', 'east 3']    # one part, every site it stands on


def test_contract_catches_what_nobody_published():
    from maps import island
    m = a8.mission()
    m.objects.append(parts.Obj('AlliedWarFactory', 100, 100))                          # raw coordinates
    m.scripts.append(parts.Script('X', [('NAMED_DESTROYED', 'UNIT - Nobody')],          # no such object
                                  [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', a8.CARRIER, 'SpecialPower_X', 'WP X'),
                                   ('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', 'JapanNavalYard', 'Player_9', 'c'),
                                   ('SHOW_MILITARY_CAPTION', 'SCRIPT:NONE', 1.0)]))
    got = parts.contract(m)
    assert len(got) == 8, got                          # the 7 it names, and the caption outside the dialogue outlet
    assert any('dialogue outlet' in p for p in got)
    assert any('raw coordinates' in p for p in got) and any("object 'UNIT - Nobody'" in p for p in got)
    assert any("power 'SpecialPower_X'" in p for p in got) and any("waypoint 'WP X'" in p for p in got)
    assert any("template 'JapanNavalYard'" in p for p in got) and any("player 'Player_9'" in p for p in got)
    assert any("string 'SCRIPT:NONE'" in p for p in got)
    other = lib.liberty('CNV_Other', tag='O')                                           # someone else's ability
    m2 = parts.Mission(name='X', map=island, units=[a8.mission().units[0], other])
    m2.put(m2.units[0].id, 'west shore', name='C', role='carrier')
    m2.scripts.append(parts.Script('Y', [], [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', 'C', other.abilities['jump'], 'W')]))
    m2.waypoints['W'] = m2.site('east 1')
    assert parts.contract(m2) == [f"Y: C (CNV_Liberty) fired {other.abilities['jump']}, an ability of CNV_Other"]
    import pytest
    with pytest.raises(AssertionError, match='no site'):
        m2.put('AlliedWarFactory', 'the moon')
    with pytest.raises(AssertionError, match='publishes no ability'):
        m2.ability('carrier', 'fly')


def test_ab_pair():
    m, t = build.PAIRS['liberty_ride_ab']()
    ids = [u.id for u in m.units]
    assert len(ids) == len(set(ids)) == 4
    carriers = [o for o in m.objects if o.template.startswith('CNV_Liberty')]
    assert [o.name for o in carriers] == ['UNIT - CNV Liberty', 'UNIT - CNV Liberty B']
    assert carriers[1].x - carriers[0].x == 500
    assert len(t.counters) == 4


def test_judge():
    t = parts.Test(counters=[('a', 'A'), ('b', 'B')], expect=[('A', 10, '>=', 3), ('B', 0, '==', 1)])
    v = build.judge(t, [(5, [1, 1]), (12, [4, 1]), (15, [None, None])])
    assert [ok for ok, _ in v] == [False, False]                 # every counter gone at s15: the mission ended
    # B unread to the end while A still reads: covered (the rank-up chevrons over the short lines), not gone
    v = build.judge(t, [(5, [1, 1]), (12, [4, 1]), (15, [3, None])])
    assert [ok for ok, _ in v] == [True, True]
    covered = [(5, [1, 1]), (12, [4, None]), (15, [3, 1])]       # unread a moment (the rank-up over the counters)
    assert [ok for ok, _ in build.judge(t, covered)] == [True, True]
    assert build.judge(t, [(5, [1, 1]), (12, [4, None]), (15, [3, 2])])[1][0] is False
    assert build.judge(parts.Test(counters=[('a', 'A')], expect=[('A', 99, '==', 1)]), [(5, [1])])[0][0] is False
    ended = [(5, [1]), (8, [0]), (9, [None])]                    # the mission ended: its counters went with it
    assert build.judge(parts.Test(counters=[('a', 'A')], expect=[('A', 6, 'ever==', 0)]), ended)[0][0] is True


def test_judge_until_and_the_bench_round_trip():
    t = parts.Test(counters=[('a', 'A')], expect=[('A', 0, '==', 0, 15), ('A', 19, '>=', 3)])
    lines, status = build.report(t, build.parse_counters('s3: 0 | s12: 0 | s18: 2 | s21: 4'))
    assert status == 0 and lines[-1] == 'RESULT PASS'           # s18's 2 is in neither window
    assert lines[1] == 'PASS A == 0 from s0 until s15: s3-s12: 0'
    assert lines[0] == 'counters (A): s3-s12: 0 | s18: 2 | s21: 4'
    assert build.report(t, build.parse_counters('s3: 0 | s14: 1 | s21: 4'))[1] == 1
    plan = build.steps('CampX', build.resolve('liberty_riders', 'jump')[1])
    assert plan[0] == ['bench_start', {'mod': 'CampX', 'look': False}] and plan[-1] == ['bench_counters', {'lines': 3}]
    assert 'liberty_riders --check jump -> CampLibRJump' in build.listing()


def test_every_build_name_fits():
    """Mod names over 15 characters crash the game before the main menu (bench 2026-10-21), and so does one with an
    underscore (bench 2026-10-25: CampA7East_What, from a check named east_what)."""
    names = [build.resolve(n, c)[2] for n, (_, checks) in build.MISSIONS.items() for c in [''] + list(checks)]
    names += [build.resolve(n, '')[2] for n in build.PAIRS]
    assert all(len(n) <= parts.MAX_NAME for n in names), [n for n in names if len(n) > parts.MAX_NAME]
    assert not [n for n in names if '_' in n]


def test_every_until_names_a_counter_shown():
    """bench_watch's until counts counter lines from 1: c0 silently read the last one (Python's [-1]) -- the ice-wall
    smash watch ran its full 70 s on the health line (bench 2026-10-22)."""
    import re
    seen = 0
    for n, (_, checks) in build.MISSIONS.items():
        for c in checks:
            _, t, _ = build.resolve(n, c)
            for tool, kw in t.bench:
                for k in re.findall(r'c(\d+)', kw.get('until', '')):
                    seen += 1
                    assert 1 <= int(k) <= kw.get('lines', 0), (n, c, kw['until'], kw.get('lines'))
    assert seen, 'no until found: the walk over the checks is empty'


def test_judge_mission_ended():
    t = parts.Test(counters=[('a', 'A')], expect=[(build.ENDED, 5, '', None)])
    assert build.judge(t, [(1, [1]), (4, [1]), (6, [None])])[0][0] is True
    assert build.judge(t, [(1, [1]), (6, [1])])[0][0] is False
    assert build.judge(t, [(6, [None])])[0][0] is False                  # never up: no counters at all, not an end


def test_judge_mission_ended_before():
    """ENDED with an until: it must end before then (S5 escape: lost soon after the fleet sets out, not won late)."""
    t = parts.Test(counters=[('a', 'A')], expect=[(build.ENDED, 5, '', None, 20)])
    assert build.judge(t, [(1, [1]), (10, [1]), (15, [None])])[0][0] is True
    assert build.judge(t, [(1, [1]), (10, [1]), (25, [None])])[0][0] is False


def test_counter_reader_reads_its_calibration():
    import counters
    frames = os.path.join(ROOT, 'work', 'testbench', 'runs')
    shots = sorted(d for d in os.listdir(frames) if d.startswith('CampDigits_mcp_')) if os.path.isdir(frames) else []
    if not shots or len(counters.templates()) < 10:
        import pytest
        pytest.skip('no calibration frame or templates on this machine (work/ is local)')
    from PIL import Image
    im = Image.open(os.path.join(frames, shots[-1], '0001.png')).convert('RGB')
    assert counters.read(im, 3) == counters.CALIBRATION
    assert counters.read_line(im, counters.line_box(4)) is None   # under the bottom bar: nothing to read
    x1 = counters.glyphs(im, counters.line_box(2))[-1][1]         # a sparkle 6 px right of the 90's 0
    im.putpixel((x1 + 6, counters.line_box(2)[1] + 7), (255, 255, 120))
    assert counters.read_line(im, counters.line_box(2)) == 90


def test_not_is_read_off_a_flag_the_scripts_keep_first():
    """The game ignores a condition's inverted bit in a map's own scripts (bench 2026-10-29, probe align): a NOT
    condition is compiled to a flag that two every-frame scripts at the head of the list keep, one per test."""
    area = ('SKIRMISH_PLAYER_HAS_UNITS_IN_AREA', 'Player_2', 'Here')
    out = parts.unnot([parts.Script('a', [area + (parts.NOT,), ('FLAG', 'Go', 1)], [('SET_FLAG', 'A', 1)]),
                       parts.Script('b', [area + (parts.NOT,)], [('SET_FLAG', 'B', 1)])])
    assert [s.name for s in out] == ['CNV Not 0 - set', 'CNV Not 0 - holds', 'a', 'b']
    assert out[0].when == [] and out[0].do == [('SET_FLAG', 'CNV Not 0', 1)] and not out[0].once
    assert out[1].when == [area] and out[1].do == [('SET_FLAG', 'CNV Not 0', 0)] and not out[1].once
    assert out[2].when == [('FLAG', 'CNV Not 0', 1), ('FLAG', 'Go', 1)] and out[3].when == [('FLAG', 'CNV Not 0', 1)]
    assert all(c[-1] != parts.NOT for s in out for c in s.when)
    assert parts.unnot(out[2:]) == out[2:]                                  # nothing left to unnot


def test_a_voice_line_must_be_in_the_voice_pack():
    """A sound named CNV_* (PLAY_SOUND_EFFECT, HAS_FINISHED_AUDIO) is one of Mission.voice's events; retail's are free."""
    from types import SimpleNamespace
    from missions import probe_bench
    m = probe_bench.mission()
    m.scripts += [parts.Script('say', [], [('PLAY_SOUND_EFFECT', 'CNV_A4_007')]),
                  parts.Script('eva', [], [('PLAY_SOUND_EFFECT', 'Aeva_EnemyAircraftDet')])]
    assert [p for p in parts.contract(m) if 'voice' in p] == ["say: PLAY_SOUND_EFFECT voice line 'CNV_A4_007' not in "
                                                              "the voice pack"]
    m.voice = SimpleNamespace(events={'CNV_A4_007'})
    assert not [p for p in parts.contract(m) if 'voice' in p]


# the registry of builds (registry.py): every mission and check module declares its own
def test_every_registered_build_and_check_resolves():
    reg = registry.get()
    assert len(reg.builds) >= 80 and 'a4' in reg.builds and 'digits' in reg.pairs
    assert set(reg.checks) <= set(reg.builds)
    assert not set(reg.builds) & set(reg.pairs)
    assert build.MISSIONS.keys() == reg.builds.keys() and build.PAIRS is reg.pairs
    # build.py list makes every mission and every check's test (the mission and the check merge, or this raises)
    listed = build.listing().splitlines()
    assert len(listed) >= len(reg.builds) + len(reg.pairs)


def fake_modules(monkeypatch, **tables):
    """Put modules declaring `tables` ({'MISSION': {...}, 'CHECKS': {...}}) in place of the real ones for registry.load."""
    import types
    names = []
    for name, table in tables.items():
        module = types.ModuleType(name)
        module.__dict__.update(table)
        monkeypatch.setitem(sys.modules, name, module)
        names.append(name)
    monkeypatch.setattr(registry, 'modules', lambda: names)


def test_registry_refuses_a_build_made_twice(monkeypatch):
    import pytest
    fake_modules(monkeypatch, x1={'MISSION': {'dup': lambda: None}}, x2={'MISSION': {'dup': lambda: None}})
    with pytest.raises(registry.RegistryError, match='made twice'):
        registry.load()


def test_registry_refuses_checks_for_a_build_nobody_makes(monkeypatch):
    import pytest
    fake_modules(monkeypatch, x1={'MISSION': {'real': lambda: None}}, x2={'CHECKS': {'ghost': {'c': print}}})
    with pytest.raises(registry.RegistryError, match='no mission module makes'):
        registry.load()


def test_registry_refuses_checks_declared_twice_or_not_callable(monkeypatch):
    import pytest
    fake_modules(monkeypatch, x1={'MISSION': {'b': lambda: None}}, x2={'CHECKS': {'b': {'c': print}}},
                 x3={'CHECKS': {'b': {'c': print}}})
    with pytest.raises(registry.RegistryError, match='declared twice'):
        registry.load()
    fake_modules(monkeypatch, x1={'MISSION': {'b': lambda: None}}, x2={'CHECKS': {'b': {'c': 'nope'}}})
    with pytest.raises(registry.RegistryError, match='not callable'):
        registry.load()


def test_registry_finds_only_modules_that_declare(monkeypatch):
    mods = registry.modules()
    assert 'missions.a4' in mods and 'checks.a4' in mods and 'missions.count_probes' in mods
    assert 'missions.music_bench' not in mods and 'missions.festival_parts' not in mods


def test_ctx_outlets_hand_over_the_same_actions():
    from ctx import Ctx
    from plantime import PlanError
    import pytest
    import types
    m = parts.Mission(name='X', map=types.SimpleNamespace(PLAYERS={'p1': 'Player_1', 's1': 'Soviet_2'}, TEAMS={}))
    ctx = Ctx(mission=m, tag='T')
    assert ctx.say('SCRIPT:K', 5.0) == ('SET_FLAG', 'CNV_T_Show_0', 1)      # a line only asks; its caption is up at once
    said = [s for s in ctx.talk_scripts() if s.name == 'CNV T - Now 0'][0]
    assert ('SHOW_MILITARY_CAPTION', 'SCRIPT:K', 5.0) in said.do
    assert ctx.final('SCRIPT:E', 10.0) == ('SHOW_MILITARY_CAPTION', 'SCRIPT:E', 10.0)
    # K6: a group is a team of the map's own, ordered as one; the units join it in the same script (UNIT_SET_TEAM)
    acts = ctx.order('attack', ['a', 'b'], 't', 's1')
    team = acts[-1][1]
    assert team.startswith('Soviet_2/teamCNVG') and team in m.teams.values()
    assert acts == [('UNIT_SET_TEAM', 'a', team), ('UNIT_SET_TEAM', 'b', team), ('TEAM_ATTACK_NAMED', team, 't')]
    assert ctx.order('attack', ['b', 'a'], 't', 's1')[-1] == acts[-1]        # the same group, the same team
    assert ctx.order('guard', ['a'], 'z', 's1')[-1][:1] == ('TEAM_GUARD_AREA',)
    assert ctx.order('hunt', ['a', 'b'], side='s1')[-1] == ('TEAM_HUNT', team)
    assert ctx.order('move', ['a'], 'w', 'p1', crew='Fleet') == [('UNIT_SET_TEAM', 'a', 'Player_1/teamCNVFleet'),
                                                                 ('MOVE_TEAM_TO', 'Player_1/teamCNVFleet', 'w')]
    assert ctx.order('stop', ['a'], side='p1', crew='Fleet') == [('TEAM_STOP', 'Player_1/teamCNVFleet')]   # joins nobody
    assert ctx.order('attack', [], 't', 's1') == []
    with pytest.raises(PlanError, match='no kind'):
        ctx.order('flee', ['a'], 't')
    with pytest.raises(PlanError, match='needs a target'):
        ctx.order('attack', ['a'])
    for ask in (lambda: ctx.camera({}, 1.0, 0, 0), lambda: ctx.mark('s'), lambda: ctx.side('我')):
        with pytest.raises(PlanError, match='written by hand'):
            ask()
    with pytest.raises(PlanError, match='needs a compiler or a mission'):
        Ctx()


def test_ctx_forwards_the_missions_own_writes():
    from ctx import Ctx
    m = parts.Mission(name='X', map=None)
    ctx = Ctx(mission=m, tag='T')
    ctx.string('K', 'a')
    ctx.string('K', 'b', keep=True)
    ctx.add_area('A', 'area')
    ctx.add_point('P', (1.0, 2.0))
    ctx.spawns_add('u1', 'u2')
    ctx.countdown('timer')
    assert (m.strings['K'], m.areas['A'], m.waypoints['P'], m.countdowns) == ('a', 'area', (1.0, 2.0), ['timer'])
    assert {'u1', 'u2'} <= set(m.spawns)
    assert ctx.voice_has('anything')          # no voice pack: nothing is missing


def test_container_libraries_are_the_containers():
    """model.CONTAINER_LIBRARIES (what the simulator and contract G6c take the container to hand the skirmish AI) is
    the container map's LibraryMapLists; package.set_libraries writes the same bytes for the same names."""
    import make_campnew18 as c18
    import mapstudy
    import model
    import package
    import retail
    from mapscript import MapFile
    data = next(d for p, d in c18.c6._map_files() if p.lower().endswith('.map'))
    m = MapFile(data)
    order = [''] + list(mapstudy.players(m))
    have = dict(zip(order, retail.library_names(m)))
    assert have == {p: tuple(n.lower() for n in model.libraries(None).get(p, ())) for p in order}
    before = [n.head for _, n in m.walk() if n.name == 'LibraryMaps']
    package.set_libraries(m, model.CONTAINER_LIBRARIES)
    assert [n.head for _, n in m.walk() if n.name == 'LibraryMaps'] == before
    assert model.handed_to_ai(None) == {'Player_2', 'Soviet_1', 'Soviet_2', 'Soviet_3'}


def test_a_reinforcement_team_is_written_as_a_template_and_read_back():
    """Mission.reinforcement -> mapxml.add_team writes a team template (not a singleton, the unit lines, retail's other
    properties); retail.team_templates (what the simulator reads of a retail map) reads the same lines back; contract
    G6b counts CREATE_REINFORCEMENT_TEAM as a join (bench 11-10 engine_reinf)."""
    import make_campnew18 as c18
    import contract
    import mapxml
    import retail
    from mapscript import MapFile
    from maps import niagara
    from parts import Mission
    m = Mission(name='CampT', map=niagara, units=[], facts={})
    team = m.reinforcement('Wave', [('AlliedAntiInfantryInfantry', 2, 3), ('AlliedAntiVehicleVehicleTech1', 2)], 's1')
    assert team == 'Soviet_1/teamCNVRWave' and m.teams['RWave'] == team
    assert {'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleVehicleTech1'} <= m.spawns
    data = next(d for p, d in c18.c6._map_files() if p.lower().endswith('.map'))
    mf = MapFile(data)
    spec = m.templates[team]
    mapxml.add_team(mf, 'teamCNVRWave', 'Soviet_1', units=spec['units'], instances=spec['instances'])
    got = next(t for t in mapxml.teams(mf) if t['teamName'][1] == 'teamCNVRWave')
    assert got['teamIsSingleton'] == (0, 0) and got['teamUnitType1'] == (5, 'GameObject:AlliedAntiInfantryInfantry')
    assert (got['teamUnitMinCount1'], got['teamUnitMaxCount1'], got['teamUnitMaxCount3']) == ((1, 2), (1, 3), (1, 0))
    assert retail.team_templates(mf)[team] == {'units': [('AlliedAntiInfantryInfantry', 2, 3),
                                                          ('AlliedAntiVehicleVehicleTech1', 2, 2)], 'instances': 1}
    assert contract.JOINS_TEAM['CREATE_REINFORCEMENT_TEAM'] == 0


def test_contract_g6c_placed_ai_units_take_no_team_order():
    """G6c: a placed unit of Soviet_1 (handed to the skirmish AI by the container) is on no team after the start, so a
    level order to its team is an error -- not on s4, not once a level script (not a first-frame one) fills the team."""
    import types
    import contract
    import mapscript
    from maps import island
    cat = mapscript.catalog()

    def broken(side, *more, libraries=None, placed=True):
        mp = types.SimpleNamespace(**{k: getattr(island, k) for k in ('PLAYERS', 'TEAMS')})
        if libraries is not None:
            mp.LIBRARIES = libraries
        team = f'{island.PLAYERS[side]}/team{island.PLAYERS[side]}'
        m = types.SimpleNamespace(name='CampG6c', map=mp, objects=[parts.Obj('SovietWarFactory', 1, 1, side=side,
                                                                              name='UNIT - G6c')][:int(placed)],
                                  scripts=[parts.Script('CNV G6c - Go', [('TIMER_EXPIRED', 'g')], [('TEAM_HUNT', team)]),
                                           *more])
        return contract.placed_ai_units_unordered(m, cat)
    assert broken('s1') and 'teamSoviet_1' in broken('s1')[0]
    assert broken('s4') == []
    assert broken('s1', libraries={'Soviet_1': ()}) == []
    fill = ('UNIT_SET_TEAM', 'UNIT - G6c', 'Soviet_1/teamSoviet_1')
    assert broken('s1', parts.Script('CNV G6c - Join', [('TIMER_EXPIRED', 'j')], [fill])) == []
    assert broken('s1', parts.Script('CNV G6c - Join', [], [fill]))       # the first frame's join is undone
    made = parts.Script('CNV G6c - Made', [], [('CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT', 'SovietWarFactory',
                                                'Soviet_1/teamSoviet_1', 'W')])
    assert broken('s1', made, placed=False)                    # made in the first frame: taken off alike
    assert broken('s1', placed=False) == []
