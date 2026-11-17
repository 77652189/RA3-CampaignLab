"""Bridge generation counts only; no implied world geometry/repair support."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('bridge_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_bridgebuilder_counts_short_and_long_retail_bridges():
    """engine_bridgebuilder:a: exact five-template counts, 270 / 700, four rows."""
    import build
    import simunits
    from parts import contract, merged

    m, t, mod = build.resolve('engine_bridgebuilder', 'a')
    assert len(mod) <= 15 and mod.isalnum()
    assert not contract(merged(m, t))
    assert [o.flags for o in m.objects] == [16, 32, 16, 32]
    assert not any(o.template.startswith('HB_Bridge') for o in m.map.OBJECTS)
    assert len(t.counters) == 4
    for k, wanted in ((0, (1, 1, 1, 0, 2)), (2, (1, 1, 2, 2, 2))):
        length = m.objects[k+1].x - m.objects[k].x
        got = simunits.bridge_generation_counts('HB_Bridge_02', length)
        assert list(got.values()) == list(wanted)
        assert set(got) == {'HB_Bridge_02_' + suffix for suffix in
                            ('End', 'End2', 'Center', 'Center2', 'GateHouse')}
        ends = (wanted[4]+1)*100 + (wanted[1]+1)*10 + wanted[0]+1
        centers = (wanted[3]+1)*10 + wanted[2]+1
        assert [e[3] for e in t.expect[k:k+2]] == [ends, centers]
    # A supported zero is digit 1; a missing query leaves digit 0 and must fail.
    assert [e[3] for e in t.expect] == [322, 12, 322, 33]
    actions = [a[0] for s in t.scripts for a in s.do]
    assert set(actions) == {'MAP_REVEAL_ALL_PERM', 'SET_COUNTER', 'INCREMENT_COUNTER'}
    queries = [s for s in t.scripts if s.when]
    assert len(queries) == 2*5*8
    assert all(s.when[0][2] == 2 for s in queries)  # equality, not saturating >=
    # Exercise the published readout scripts with recorded template counts.
    # This is a count fixture, not a claim that Sim creates/positions bridge bodies.
    counts_by_area = {}
    for role, length in (('short', 270), ('long', 700)):
        counts_by_area['Bridge ' + role] = simunits.bridge_generation_counts('HB_Bridge_02', length)
    def readout(missing=None):
        counters = {}
        for script in t.scripts:
            if script.when:
                _, _, _, n, template, area = script.when[0]
                if (area, template) == missing or counts_by_area[area][template] != n:
                    continue
            for action in script.do:
                if action[0] == 'SET_COUNTER':
                    counters[action[1]] = action[2]
                elif action[0] == 'INCREMENT_COUNTER':
                    counters[action[2]] += action[1]
        return [counters[name] for name, _ in t.counters]
    rows = readout()
    assert rows == [322, 12, 322, 33]
    assert build.report(t, [(second, rows) for second in range(4, 19)])[1] == 0
    # Missing B query must fail, even though short-bridge B's valid count is zero.
    blind = readout(('Bridge short', 'HB_Bridge_02_Center2'))
    assert blind == [322, 2, 322, 33]
    assert build.report(t, [(second, blind) for second in range(4, 19)])[1] != 0
    assert simunits.bridge_generation_counts('HB_Bridge_02', 400) is None
    assert simunits.bridge_generation_counts('HB_Bridge_02a', 270) is None
    override = {'HB_Bridge_02': '<GameObject id="HB_Bridge_02"><Behaviors>'
                               '<BridgeBuilder EndCap="other" /></Behaviors></GameObject>'}
    assert simunits.bridge_generation_counts('HB_Bridge_02', 270, override) is None


def test_bridgebuilder_mixed_retail_end_marker_counts():
    """engine_bridgebuilder_b:b: HB start / Bridge1a end, four measured rows."""
    import build
    import simunits
    from parts import contract, merged

    m, t, mod = build.resolve('engine_bridgebuilder_b', 'b')
    assert len(mod) <= 15 and mod.isalnum()
    assert not contract(merged(m, t))
    assert [(o.template, o.flags) for o in m.objects] == [
        ('HB_Bridge_02', 16), ('Bridge1a', 32)] * 2
    assert [m.cast[role].template for role in ('short 1', 'long 1')] == ['Bridge1a'] * 2
    assert len(t.counters) == 4
    foreign = tuple('Bridge1_' + s for s in ('End', 'End2', 'Center', 'Center2', 'GateHouse'))
    counts = {}
    for role, k, wanted in (('short', 0, [1, 1, 1, 0, 2]), ('long', 2, [1, 1, 2, 2, 2])):
        length = m.objects[k+1].x - m.objects[k].x
        got = simunits.bridge_pair_generation_counts('HB_Bridge_02', 'Bridge1a', length)
        assert list(got.values()) == wanted + [0] * 5
        assert set(got) == set(foreign) | {'HB_Bridge_02_' + s for s in
                                         ('End', 'End2', 'Center', 'Center2', 'GateHouse')}
        counts['Bridge ' + role] = got
    def readout(missing=None, unexpected=None):
        counters = {}
        for script in t.scripts:
            ok = True
            for _, _, comparison, n, template, area in script.when:
                assert comparison == 2
                value = 1 if (area, template) == unexpected else counts[area][template]
                ok &= (area, template) != missing and value == n
            if not ok:
                continue
            for action in script.do:
                if action[0] == 'SET_COUNTER':
                    counters[action[1]] = action[2]
                elif action[0] == 'INCREMENT_COUNTER':
                    counters[action[2]] += action[1]
        return [counters[name] for name, _ in t.counters]
    rows = readout()
    assert rows == [1322, 12, 1322, 33] == [e[3] for e in t.expect]
    assert build.report(t, [(s, rows) for s in range(4, 19)])[1] == 0
    for template in foreign:
        for broken in (readout(missing=('Bridge short', template)),
                       readout(unexpected=('Bridge short', template))):
            assert broken == [322, 12, 1322, 33]
            assert build.report(t, [(s, broken) for s in range(4, 19)])[1] != 0
    assert simunits.bridge_pair_generation_counts('HB_Bridge_02', 'Bridge1a', 400) is None
    assert simunits.bridge_pair_generation_counts('Bridge1a', 'HB_Bridge_02', 270) is None
    # A changed width or different end configuration is outside the observed pair.
    for template, field in (('Bridge1a', 'Width="180.0"'), ('HB_Bridge_02', 'Width="190.0"')):
        xml = simunits._xml(template).replace(field, 'Width="181.0"')
        assert simunits.bridge_pair_generation_counts('HB_Bridge_02', 'Bridge1a', 270,
                                                       {template: xml}) is None
