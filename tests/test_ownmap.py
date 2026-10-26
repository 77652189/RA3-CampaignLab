"""Our own Pathfinder map (experimental/music/ownmap.py): the spy map reads back through the writer, every event
jumps to a section looping on its own stream, and the menu section's router pairs play the right transition into
the right section."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from experimental.music import ownmap, pfdx  # noqa: E402

RETAIL = ROOT / 'work' / 'music' / 'retail'


@pytest.fixture(scope='module')
def spy():
    if not (RETAIL / 'map.bin').exists():
        pytest.skip('run experimental/music/extract.py first (needs the game)')
    names = json.loads((RETAIL / 'event_hashes.json').read_text())
    base = pfdx.parse((RETAIL / 'map.bin').read_bytes(), names)
    b, lengths = ownmap.spy(base)
    m = b.build([(k, ms) for k, ms in enumerate(lengths)])
    return base, pfdx.parse(pfdx.build(m), names), lengths


def test_name_table_names_the_events(spy):
    """extract.event_hashes reads every PathMusicEvent, also those with an XferAlternateEvent (bigger instances)."""
    base, _, _ = spy
    names = [e.name for e in base.events]
    assert 'S_A01BrightonIntro' in names and sum(not n for n in names) <= 5


def test_mission_music_events_are_held_to_the_pack():
    """parts.contract: with Mission.music set, PATH_MUSIC_PLAY_EVENT may name only the events the pack plays."""
    sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
    import parts
    from missions import music_bench
    m = music_bench.mission()
    assert parts.contract(parts.merged(m)) == []
    m.scripts.append(parts.Script('Typo', [], [('PATH_MUSIC_PLAY_EVENT', 'S_A01BrightonCombatt')]))
    assert parts.contract(parts.merged(m)) == ["Typo: PATH_MUSIC_PLAY_EVENT music event 'S_A01BrightonCombatt' "
                                               "not published"]


def test_timing_map(spy):
    base, _, _ = spy
    b, lengths = ownmap.timing(base)
    names = [e.name for e in b.m.events]
    for kind, e in ownmap.TIMING.items():
        i = names.index(e)
        prep = [(ownmap.TRACK, ownmap.PREP)] * (kind == 'cut')
        assert [a[:2] for a in b.m.events[i].actions] == prep + [(ownmap.TRACK, ownmap.GOTO)]
        assert lengths[i] == ownmap.TIMING_SECONDS * 1000
    plain = b.m.nodes[b.m.nodes[goto(b.m.events[names.index(ownmap.TIMING_PLAIN)])].branches[0][2]]
    assert plain.router == 2


def goto(e):
    return next(c & 0xFFFF for _, op, c in e.actions if op == ownmap.GOTO)


def test_spy_reads_back(spy):
    base, m, lengths = spy
    assert [e.hash24 for e in m.events] == [e.hash24 for e in base.events]
    assert m.variables == base.variables and len(m.samples) == len(lengths)


def test_every_event_loops_on_its_own_stream(spy):
    _, m, _ = spy
    for i, e in enumerate(m.events):
        prep = [(ownmap.TRACK, ownmap.PREP)] * (e.name != 'BriefingTrack')
        assert [a[:2] for a in e.actions] == prep + [(ownmap.TRACK, ownmap.GOTO)]
        assert pfdx.walk(m, goto(e), 3) == [i, i, i]


def test_menu_router_transitions(spy):
    _, m, _ = spy
    E = len(m.events)
    menu = next(e for e in m.events if e.name == 'MenuTrack')
    seg = m.nodes[m.nodes[goto(menu)].branches[0][2]]
    assert seg.is_segment and seg.router == 2
    targets = {goto(e) for e in m.events} - {goto(menu)}
    for routers, stream in ((m.routers[1], E), (m.routers[2], E + 1)):
        assert {b for a, b in routers} == targets
        for a, b in routers:
            assert pfdx.walk(m, a, 2) == [stream, m.nodes[m.nodes[b].branches[0][2]].stream]
