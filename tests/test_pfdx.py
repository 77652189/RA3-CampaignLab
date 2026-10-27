"""The Pathfinder music map reader/writer (experimental/music/pfdx.py): the retail map reads back byte for byte, every
retail segment plays a stream that exists, and a map built from scratch reads back the same."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from experimental.music import pfdx  # noqa: E402

RETAIL = ROOT / 'work' / 'music' / 'retail' / 'map.bin'


@pytest.fixture(scope='module')
def retail():
    if not RETAIL.exists():
        pytest.skip('run experimental/music/extract.py first (needs the game)')
    return pfdx.strip_asset_header(RETAIL.read_bytes())


def test_retail_round_trip(retail):
    assert pfdx.build(pfdx.parse(retail)) == retail


def test_retail_segments_cover_every_stream(retail):
    m = pfdx.parse(retail)
    streams = {n.stream for n in m.nodes if n.is_segment}
    assert streams == set(range(len(m.samples)))
    for n in m.nodes:
        for _, _, to in n.branches:
            assert to == 0xFFFF or to < len(m.nodes)


def test_new_map_reads_back():
    entry = pfdx.Node(0, 0, 0, 0, 0, 0x10, 1, 0, 0, 0, [(0, 127, 1)])
    seg = pfdx.Node(1, 0, 0, 0, 0, 0x40, 1, 0, 4, 0, [(0, 127, 2)])
    exit_ = pfdx.Node(0xFFFF, 0, 0, 0, 0, 0x10, 1, 1, 0, 0, [(0, 127, 0)])
    m = pfdx.PathMap(0, 0, 0, 1, 0, bytes(12), nodes=[entry, seg, exit_],
                     events=[pfdx.Event([0, 0, 0, 0x123456, 0], [(0x11000001, 0x00030400, 0x00FF0000)])],
                     variables=[b'player'.ljust(20, b'\0')], routers=[[(1, 0)]],
                     tracks=[bytes(20)], samples=[(0, 1000)])
    data = pfdx.build(m)
    back = pfdx.parse(data)
    assert pfdx.build(back) == data
    assert [n.stream for n in back.nodes] == [None, 0, None]
    assert back.events[0].hash24 == 0x123456 and back.events[0].actions == m.events[0].actions
    assert back.variable_names() == ['player']
    assert back.routers == [[(1, 0)]]               # the last router too: the table ends with an offset of its own


def test_retail_routers_end_with_an_offset(retail):
    """The router table's last offset is its end, not a router (CampMusRoute 2026-10-26: a map without it lost its
    last router in game): retail has 131, and its segments use router values 1..131."""
    m = pfdx.parse(retail)
    assert len(m.routers) == 131 and all(m.routers)
    assert max(n.router for n in m.nodes) == len(m.routers)
