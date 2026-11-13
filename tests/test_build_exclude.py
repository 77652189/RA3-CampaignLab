"""CountAsStructure ExcludeThing: named two-factory contrast."""
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)


def test_build_exclude_single_input():
    import build
    views = []
    for name in ('aibex', 'aibin'):
        m, _, build_name = build.resolve(name, 'r')
        assert len(build_name) <= 15 and '_' not in build_name
        assert m.ext
        root = ET.fromstring(m.assets[-1][1])
        filt = next(e for e in root.iter() if e.tag.endswith('}CountAsStructureForBuildPurposesFilter'))
        nodes = [e for e in filt if e.tag.endswith('}ExcludeThing') and e.text == 'CNVDearPK']
        assert len(nodes) == (name == 'aibex')
        for node in nodes:
            filt.remove(node)
        views.append((ET.tostring(root), m.objects, m.scripts, [u.xml for u in m.units]))
    assert views[0] == views[1]


def test_build_exclude_category_single_input():
    import build
    views = []
    for name in ('aibxo', 'aibxi'):
        m, _, build_name = build.resolve(name, 'x')
        assert len(build_name) <= 15 and '_' not in build_name and m.ext
        root = ET.fromstring(m.assets[-1][1])
        filt = next(e for e in root.iter() if e.tag.endswith('}CountAsStructureForBuildPurposesFilter'))
        assert 'INFANTRY' in filt.get('Include').split()
        assert not any(e.tag.endswith('}IncludeThing') for e in filt)
        nodes = [e for e in filt if e.tag.endswith('}ExcludeThing') and e.text == 'CNVDearPK']
        assert len(nodes) == (name == 'aibxo')
        for node in nodes:
            filt.remove(node)
        views.append((ET.tostring(root), m.objects, m.scripts, [u.xml for u in m.units]))
    assert views[0] == views[1]


def test_build_exclude_log_reader(tmp_path):
    import teamlog
    path = tmp_path / 'ra3ext.log'
    path.write_text(
        'unrelated: line\n'
        'bpick: frame=4 fac=factoryA obj=0 tmpl=dear a=asset score=0.167 flt=1\n'
        'bpick: frame=5 fac=factoryB obj=0 tmpl=new a=asset score=166.667 flt=0\n'
        'bpick: frame=6 fac=factoryC obj=0 tmpl=upgrade a=asset score=140 flt=-\n'
        'border: frame=4 site=SD fac=factoryA obj=0 tmpl=dear a=asset ok=0 '
        'picks=0:dear:0.167:1,0:new:166.667:0,0:upgrade:140:-1\n'
        'border: frame=5 site=U fac=factoryB obj=0 tmpl=new a=asset ok=1 picks=\n', encoding='utf-8')
    picks, orders = teamlog.build_picks(path), teamlog.build_orders(path)
    assert [p['filter'] for p in picks] == [True, False, None]
    assert [p['factory'] for p in picks] == ['factoryA', 'factoryB', 'factoryC']
    assert [o['ok'] for o in orders] == [False, True]
    assert orders[0]['picks'] == [dict(object=p['object'], template=p['template'],
                                     score=p['score'], filter=p['filter']) for p in picks]
    assert orders[1]['picks'] == []


@pytest.mark.skipif(not simai.available(), reason='private AI model unavailable')
@pytest.mark.parametrize('name,dear_pass,new_pass,chosen', [
    ('aibex', True, False, 'CNVDearPK'), ('aibin', True, False, 'CNVDearPK'),
    ('aibxo', False, True, 'CNVNewPK'), ('aibxi', True, True, 'CNVNewPK'),
])
def test_build_exclude_named_factory_replay(name, dear_pass, new_pass, chosen):
    """Replay the observed same-pass idle-factory picks, not whole-game clocks.

    Work/re/c_buildexclude_follow_report.md records the original D103 and new
    category probes. Account eligibility/production timing remain a separate
    strict-xfail comparison below.
    """
    import build
    mod = simai.model()
    m, _, _ = build.resolve(name, 'r' if name in ('aibex', 'aibin') else 'x')
    data = mod['data'].AIData()
    data.add_text(m.assets[-1][1])
    root = ET.fromstring(m.assets[-1][1])
    pid = next(e.get('id') for e in root if e.tag.endswith('}AIPersonalityDefinition'))
    ai = mod['player'].AIPlayer(data, pid, rng=None)
    kinds = frozenset({'INFANTRY'})
    filt = ai.personality.structure_filter
    passes = lambda t: mod['states']._filter_passes(t, filt, {'kindof': lambda _: kinds})
    assert passes('CNVDearPK') == dear_pass
    assert passes('CNVNewPK') == new_pass
    offers = [
        mod['teams'].Offer('CNVDearPK', kindof=kinds, cost=200, facilities=('dear factory',)),
        mod['teams'].Offer('CNVNewPK', kindof=kinds, cost=200, facilities=('new factory',))]
    ai.offers = lambda _, frame: offers
    attempted = []
    ai.builder = lambda t: attempted.append(t) or False
    ai.accounts['PRODUCTION'] = 2000
    ai.money = 2000
    basket = ai.build_units(4, [])
    assert basket == 'S'
    assert attempted == [chosen]
    # The successful engine orders had only that factory in the candidate
    # snapshot: New at frame 343, Dear at 409. Replay those observed gates,
    # without claiming the model predicts when a factory becomes eligible.
    for template, frame, passed in [('CNVNewPK', 343, new_pass), ('CNVDearPK', 409, dear_pass)]:
        offers[:] = [mod['teams'].Offer(template, kindof=kinds, cost=200, facilities=(template,))]
        attempted.clear()
        assert ai.build_units(frame, []) == ('S' if passed else 'U')
        assert attempted == [template]


@pytest.mark.parametrize('name,dear_pass,new_pass,new_site,dear_site', [
    ('aibex', True, False, 'U', 'SD'), ('aibin', True, False, 'U', 'SD'),
    ('aibxo', False, True, 'SD', 'U'), ('aibxi', True, True, 'SD', 'SD'),
])
def test_build_exclude_direct_original_readings(name, dear_pass, new_pass, new_site, dear_site):
    path = Path(simai.labpaths.WORK) / 're/c_buildexclude_follow_measured.json'
    if not path.exists():
        pytest.skip('private direct factory archive unavailable')
    evidence = json.loads(path.read_text(encoding='utf-8'))[name]
    assert evidence['filters'] == {'CNVNewPK': [new_pass], 'CNVDearPK': [dear_pass]}
    assert evidence['first_ok'] == {'CNVNewPK': dict(frame=343, site=new_site),
                                    'CNVDearPK': dict(frame=409, site=dear_site)}
    from sagehash import asset_id
    first = evidence['orders'][0]
    chosen = 'CNVNewPK' if new_pass else 'CNVDearPK'
    assert (first['frame'], first['site'], first['template'], first['ok']) == (
        4, 'SD', f'{asset_id(chosen):x}', False)


@pytest.mark.parametrize('name', ['aibex', 'aibin'])
def test_build_exclude_original_readings(name):
    path = Path(simai.labpaths.WORK) / 're/c_buildexclude_measured.json'
    if not path.exists():
        pytest.skip('private original bench archive unavailable')
    evidence = json.loads(path.read_text(encoding='utf-8'))[name]
    assert evidence['first_owned'] == {'CNVNewPK': 501, 'CNVDearPK': 570}
    assert evidence['orders'] == []  # registry observer did not see the factory's requests
    rows = [row[2] for row in evidence['rows'] if 36 <= row[0] <= 40]
    assert rows and all(row[:2] == [1, 1] for row in rows), rows


@pytest.mark.skipif(not simai.available(), reason='private AI model unavailable')
@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'Both engine variants first own CNVNewPK then CNVDearPK; whole-game early '
    'production timing still differs. Filter/basket precedence is independently '
    'covered by named_factory_replay, not by these counters. '
    'See work/re/c_buildexclude_follow_report.md and handoff-c.md.'))
@pytest.mark.parametrize('name', ['aibex', 'aibin'])
def test_build_exclude_named_first_wave_replay(name):
    # Only the first production wave is compared. Later team losses and
    # replenishment do not identify the basket used for an initial request.
    w = simai.run(name, 'r', until=40)
    rows = [(second, values[:2]) for second, values in w.sim.series if any(values[:2])]
    # Original engine counters: s32..35 = 1/0, s36..40 = 1/1 in both
    # variants. Compare production, not model request logs, with that fact.
    assert rows and rows[0][1] == [1, 0], rows[:8]
