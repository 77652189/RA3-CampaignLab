"""Isolated EngageTacticalTarget replay: checks/engine_aitactical.py."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)
pytestmark = pytest.mark.skipif(not simai.available(), reason='requires private engine model')


@pytest.mark.parametrize('name,enabled', [('aitacon', True), ('aitacoff', False)])
def test_engage_tactical_dispatch_and_plant_health(name, enabled):
    """Replay the on/off bench's plant health and four living infantry at 40-42 s.

    The plant has no weapon; hostile/passive dispatch are both off. Also observe
    explicit micro orders, so a matching HP reading alone cannot pass as dispatch.
    Final snapshots are 0%/100%; exact shot damage and start frame are outside
    this replay's scope.
    """
    import build
    m, t, _ = build.resolve(name, 'a')
    w = simai.SimAI(simai.sim.Sim(m, t, 'normal'), 'normal', 1, None, None, simai.BLOCKS)
    # Brains appear when the mission's wake script runs; capture their orders as
    # soon as they exist, before the first recruited team's micro update.
    orders = []
    wrapped = set()
    while w.frame < 42 * simai.FPS:
        for brain in w.brains.values():
            if id(brain) not in wrapped:
                old = brain.tactics.order

                def record(u, kind, arg, old=old):
                    orders.append((kind, arg))
                    return old(u, kind, arg)

                brain.tactics.order = record
                wrapped.add(id(brain))
        w.advance(1)
    brain, = w.brains.values()
    target_id = brain.tid(w.sim.body('Tac Plant'))
    attacks = [arg for kind, arg in orders if kind == 'attack']
    assert (target_id in attacks) is enabled, orders
    labels = [label for _, label in t.counters]
    readings = [dict(zip(labels, values)) for at, values in w.sim.series if 40 <= at <= 42]
    assert readings
    assert all(row['步兵存活'] == 4 for row in readings), readings
    assert all(row['目标血量'] == (0 if enabled else 100) for row in readings), readings
