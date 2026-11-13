"""Engine line D round 77: aiskcap's check y (new Peacekeepers past their SpecificUnitCap 2 at ~s150) on aiskcapo =
aiskcap with the AI yard carrying ra3ext's CNVOrders (missions/aiorders_bench.py). The bench asserts y's counters; the
orders (which path placed the overrun Peacekeeper) are read off the run folder's ra3ext.log after the run.

Round 79 (H4): yl = y watched to 300 s after the wake (the AI's building orders, AlliedBaseDefense among them, are in
the CNVOrders log), on aiskcapo / aiskcapp / aiskcapd. aiskcapo makes its infantry in two waves (s28-s42, then from s135; the overrun is in
the second); with owned plants (aiskcapp / aiskcapd) the first wave starts ~30 s later and y's window ends before the
second.
"""
from checks.engine_aiskirm import y


def yl(m):
    t = y(m)
    t.bench = [('bench_watch', dict(seconds=m.facts['wake at'] + 300.0, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {'aiskcapo': {'y': y, 'yl': yl}, 'aiskcapd': {'y': y, 'yl': yl}, 'aiskcapp': {'y': y, 'yl': yl},
          'aiskcapy': {'y': y}, 'aiskcapt': {'yl': yl}}
