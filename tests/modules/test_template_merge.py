"""Template merge expectations from work/re/sim_split/xml_merge.md."""
import re
import threading
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, TimeoutError, wait
from xml.etree import ElementTree

import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import model  # noqa: E402
import parts  # noqa: E402
import simsmall  # noqa: E402
import simunits  # noqa: E402


BASE = 'CNVMergeBase'
CHILD = 'CNVMergeChild'
ECONOMIC = '<xi:include href="DATA:Includes/InfiltratorContainEconomic.xml"/>'
AURA = '<AttributeModifierAuraUpdate id="A" Range="200"/>'
PROP_REMOVE = '<PropBody id="B" xai:joinAction="Remove"/>'


def _asset(*objects, defines=''):
    return ('<AssetDeclaration xmlns="uri:ea.com:eala:asset" '
            'xmlns:xai="uri:ea.com:eala:asset:instance" xmlns:xi="http://www.w3.org/2001/XInclude">'
            f'{defines}{"".join(objects)}</AssetDeclaration>')


def _object(name, behaviors='', *, parent=None, body=None, command_set=None):
    inherit = f' inheritFrom="{parent}"' if parent else ''
    commands = f' CommandSet="{command_set}"' if command_set else ''
    if body is None:
        body = '' if parent else '<Body><ActiveBody id="B" MaxHealth="800"/></Body>'
    behavior_group = f'<Behaviors>{behaviors}</Behaviors>' if behaviors else ''
    return f'<GameObject id="{name}"{inherit}{commands}>{behavior_group}{body}</GameObject>'


def _sim(**files):
    mission = parts.Mission(name='Merge', map=simsmall.island, scripts=[],
                            units=[model.Unit(id=name, xml=xml) for name, xml in files.items()])
    return simsmall.sim.Sim(mission, model=False)


def _inherit(base, child, *, child_defines=''):
    return _sim(**{BASE: _asset(base), CHILD: _asset(child, defines=child_defines)})


def _blocks(sim, name, tag):
    return [ElementTree.fromstring(
        f'<Block xmlns:xai="uri:ea.com:eala:asset:instance"><{tag}{head}>{inner}</{tag}></Block>')[0]
        for head, inner in simunits.module_blocks(name, tag, sim.own)]


def _attrs(sim, name, tag, key):
    return [block.get(key) for block in _blocks(sim, name, tag)]


def _health(sim, tag):
    return [data.max_health for data in sim.world.data_of(CHILD, tag)]


def _level(level_id, gain, trigger):
    return (f'<LevelUpUpgrade id="{level_id}" LevelsToGain="{gain}" LevelCap="4">'
            f'<TriggeredBy>{trigger}</TriggeredBy></LevelUpUpgrade>')


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="port omits UnpackTime / SDK compiles 8s, xml_merge.md case a")
def test_a_same_id_inherits_omitted_unpack_time():
    sim = _inherit(
        _object(BASE, '<StructureUnpackUpdate id="U" UnpackTime="8s"/>'),
        _object(CHILD, '<StructureUnpackUpdate id="U"/>', parent=BASE))
    assert _attrs(sim, CHILD, 'StructureUnpackUpdate', 'UnpackTime') == ['8s']


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="port keeps only child blocks / SDK keeps parent then child, xml_merge.md case b")
def test_b_new_ids_append_with_their_own_attributes_and_children():
    sim = _inherit(
        _object(BASE, _level('ParentLevel', 1, 'Upgrade_CreationVeterancy_VETERAN')
                + '<InfiltratorContain id="ParentSpy" Effect="RESET"/>'),
        _object(CHILD, _level('ChildLevel', 2, 'Upgrade_CreationVeterancy_ELITE')
                + '<InfiltratorContain id="ChildSpy" Effect="KILL"/>', parent=BASE))
    levels = [(b.get('id'), b.get('LevelsToGain'), b.findtext('{*}TriggeredBy'))
              for b in _blocks(sim, CHILD, 'LevelUpUpgrade')]
    spies = [(b.get('id'), b.get('Effect')) for b in _blocks(sim, CHILD, 'InfiltratorContain')]
    assert (levels, spies) == (
        [('ParentLevel', '1', 'Upgrade_CreationVeterancy_VETERAN'),
         ('ChildLevel', '2', 'Upgrade_CreationVeterancy_ELITE')],
        [('ParentSpy', 'RESET'), ('ChildSpy', 'KILL')])


def test_c_replace_resets_time_while_empty_body_inherits():
    sim = _inherit(
        _object(BASE, '<StructureUnpackUpdate id="U" UnpackTime="8s"/>',
                body='<Body><ImmortalBody id="B" MaxHealth="800"/></Body>'),
        _object(CHILD, '<StructureUnpackUpdate id="U" xai:joinAction="Replace"/>',
                parent=BASE, body='<Body/>'))
    assert [data.frames for data in sim.world.data_of(CHILD, 'StructureUnpackUpdate')] == [0]
    assert _health(sim, 'ImmortalBody') == [800]
    assert _health(sim, 'ActiveBody') == []


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="port gives RESET, KILL, STEAL_MONEY / SDK compiles RESET, STEAL_MONEY, KILL, "
                          "xml_merge.md case d")
def test_d_include_is_inserted_at_its_position():
    sim = _sim(**{CHILD: _asset(_object(CHILD, '<InfiltratorContain id="R" Effect="RESET"/>'
                                       + ECONOMIC + '<InfiltratorContain id="K" Effect="KILL"/>'))})
    assert _attrs(sim, CHILD, 'InfiltratorContain', 'Effect') == ['RESET', 'STEAL_MONEY', 'KILL']


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="port finds no aura on the embedded child / SDK inherits its same-file parent's aura, "
                          "xml_merge.md case e")
def test_e_explicit_inheritance_works_between_objects_in_one_file():
    sim = _sim(**{BASE: _asset(_object(BASE, AURA), _object(CHILD, parent=BASE))})
    assert _attrs(sim, CHILD, 'AttributeModifierAuraUpdate', 'id') == ['A']


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="port leaves inherited MaxHealth unresolved / SDK compiles 725 from the source file, "
                          "xml_merge.md case f")
def test_f_inherited_value_uses_its_source_files_define():
    sim = _sim(**{
        BASE: _asset(_object(BASE, body='<Body><ActiveBody id="B" MaxHealth="=$CNV_MERGE_HP"/></Body>'),
                     defines='<Defines><Define name="CNV_MERGE_HP" value="725"/></Defines>'),
        CHILD: _asset(_object(CHILD, parent=BASE),
                      defines='<Defines><Define name="CNV_MERGE_HP" value="800"/></Defines>'),
    })
    assert _health(sim, 'ActiveBody') == [725]


# Case g has no test because the compiler's two contain blocks leave the engine's runtime choice unknown.


@pytest.mark.xfail(strict=True, raises=pytest.fail.Exception,
                   reason="port accepts the template and supplies an ActiveBody / SDK rejects the empty Body, "
                          "xml_merge.md case c (review A #1)")
def test_c_review_a1_remove_only_body_is_rejected():
    sim = _inherit(
        _object(BASE, body='<Body><PropBody id="B"/></Body>'),
        _object(CHILD, parent=BASE, body=f'<Body>{PROP_REMOVE}</Body>'))
    with pytest.raises(ValueError):
        sim.add('child', CHILD, 'Player_1', 0, 0)


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="port relabels ActiveBody as PropBody / SDK compiles only ActiveBody, "
                          "xml_merge.md case c (review A #1)")
def test_c_review_a1_removed_prop_body_does_not_relabel_active_body():
    sim = _inherit(
        _object(BASE, body='<Body><PropBody id="B"/></Body>'),
        _object(CHILD, parent=BASE, body=f'<Body>{PROP_REMOVE}<ActiveBody id="A" MaxHealth="100"/></Body>'))
    assert (_health(sim, 'PropBody'), _health(sim, 'ActiveBody')) == ([], [100])


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="port omits MaxHealth / SDK compiles 800, xml_merge.md case a (review A #2)")
def test_a_review_a2_partial_body_keeps_parent_health_even_with_new_id():
    sim = _inherit(_object(BASE),
                   _object(CHILD, parent=BASE, body='<Body><ActiveBody id="ChildBody"/></Body>'))
    assert _health(sim, 'ActiveBody') == [800]


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="port leaves local MaxHealth unresolved / SDK compiles 725, "
                          "xml_merge.md case f (review A #2)")
def test_f_review_a2_local_define_sets_health():
    sim = _sim(**{CHILD: _asset(
        _object(CHILD, body='<Body><ActiveBody id="B" MaxHealth="=$CNV_MERGE_HP"/></Body>'),
        defines='<Defines><Define name="CNV_MERGE_HP" value="725"/></Defines>')})
    assert _health(sim, 'ActiveBody') == [725]


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="port caches an empty CommandSet during indexing / SDK compiles ReviewOrders, "
                          "xml_merge.md case e (review A #4)")
def test_e_review_a4_command_set_is_available_after_indexing(monkeypatch):
    xml = _asset(_object(BASE), _object(CHILD, command_set='ReviewOrders'))
    sim = _sim(**{BASE: xml})
    finditer = re.finditer
    scanning = Future()
    resume = threading.Event()

    def pause_object_scan(pattern, text, *args, **kwargs):
        if pattern == r'<GameObject\b.*?</GameObject>' and text == xml and not scanning.done():
            scanning.set_result(None)
            if not resume.wait(timeout=10):
                raise RuntimeError('template scan was not resumed')
        return finditer(pattern, text, *args, **kwargs)

    monkeypatch.setattr(simunits.re, 'finditer', pause_object_scan)
    with ThreadPoolExecutor(max_workers=2) as pool:
        scan = pool.submit(simunits._xml, CHILD, sim.own)
        concurrent_read = None
        try:
            done, _ = wait((scan, scanning), timeout=5, return_when=FIRST_COMPLETED)
            if not done:
                raise RuntimeError('template scan did not start')
            if scan not in done:
                concurrent_read = pool.submit(simunits.command_set, CHILD, own=sim.own)
                try:
                    concurrent_read.result(timeout=2)
                except TimeoutError:
                    pass  # A reader may wait for the scan before returning.
        finally:
            resume.set()
        scan.result()
        if concurrent_read is not None:
            concurrent_read.result()
    assert simunits.command_set(CHILD, own=sim.own) == 'ReviewOrders'


@pytest.mark.xfail(strict=True, raises=pytest.fail.Exception,
                   reason="port accepts two Cold blocks with standalone Replace / SDK rejects standalone Replace, "
                          "xml_merge.md case c (review B #1)")
def test_c_review_b1_standalone_replace_is_rejected():
    cold = ('<SecondaryDamageTracker id="Cold" DissipateAmount="10"/>'
            '<SecondaryDamageTracker id="Cold" xai:joinAction="Replace" DissipateAmount="50"/>')
    sim = _sim(**{CHILD: _asset(_object(CHILD, cold))})
    with pytest.raises(ValueError):
        simunits.module_blocks(CHILD, 'SecondaryDamageTracker', sim.own)


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="port keeps Cold values 10 and 50 / SDK compiles only Cold 50, "
                          "xml_merge.md case c (review B #1)")
def test_c_review_b1_replace_of_earlier_child_block_leaves_one_tracker():
    cold = ('<SecondaryDamageTracker id="Cold" DissipateAmount="10"/>'
            '<SecondaryDamageTracker id="Cold" xai:joinAction="Replace" DissipateAmount="50"/>')
    sim = _inherit(_object(BASE), _object(CHILD, cold, parent=BASE))
    assert _attrs(sim, CHILD, 'SecondaryDamageTracker', 'DissipateAmount') == ['50']


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="port loses the inherited Veteran trigger / SDK keeps it with the appended upgrade, "
                          "xml_merge.md case b (review B #2)")
def test_b_review_b2_new_upgrade_keeps_veteran_trigger():
    veteran = 'Upgrade_CreationVeterancy_VETERAN'
    elite = 'Upgrade_CreationVeterancy_ELITE'
    sim = _inherit(_object(BASE, _level('Veteran', 1, veteran)),
                   _object(CHILD, _level('NewUpgrade', 1, elite), parent=BASE))
    assert [(b.findtext('{*}TriggeredBy'), b.get('LevelsToGain'))
            for b in _blocks(sim, CHILD, 'LevelUpUpgrade')] == [(veteran, '1'), (elite, '1')]


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="port loses both upgrades / SDK removes only the matching id, "
                          "xml_merge.md case c (review B #2)")
def test_c_review_b2_remove_leaves_other_inherited_upgrade():
    sim = _inherit(
        _object(BASE, _level('Veteran', 1, 'Upgrade_CreationVeterancy_VETERAN')
                + _level('Elite', 1, 'Upgrade_CreationVeterancy_ELITE')),
        _object(CHILD, '<LevelUpUpgrade id="Elite" xai:joinAction="Remove"/>', parent=BASE))
    assert _attrs(sim, CHILD, 'LevelUpUpgrade', 'id') == ['Veteran']


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="port gives RESET, STEAL_MONEY / SDK compiles STEAL_MONEY, RESET, "
                          "xml_merge.md case d (review B #3)")
def test_d_review_b3_leading_include_precedes_reset():
    sim = _sim(**{CHILD: _asset(_object(CHILD, ECONOMIC + '<InfiltratorContain id="R" Effect="RESET"/>'))})
    assert _attrs(sim, CHILD, 'InfiltratorContain', 'Effect') == ['STEAL_MONEY', 'RESET']


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="port gives 0 frames / SDK compiles 8s (120 frames), xml_merge.md case a (review B #5)")
def test_a_review_b5_same_id_omission_keeps_120_unpack_frames():
    sim = _inherit(
        _object(BASE, '<StructureUnpackUpdate id="U" UnpackTime="8s"/>'),
        _object(CHILD, '<StructureUnpackUpdate id="U"/>', parent=BASE))
    assert [data.frames for data in sim.world.data_of(CHILD, 'StructureUnpackUpdate')] == [120]


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="port gives main and embedded aura counts 1, 0 / SDK compiles 0, 1, "
                          "xml_merge.md case e (review B #7)")
def test_e_review_b7_independent_objects_keep_separate_auras():
    sim = _sim(**{BASE: _asset(_object(BASE), _object(CHILD, AURA))})
    tag = 'AttributeModifierAuraUpdate'
    assert [_attrs(sim, name, tag, 'id') for name in (BASE, CHILD)] == [[], ['A']]
