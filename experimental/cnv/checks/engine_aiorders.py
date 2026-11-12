"""Engine line D round 77: aiskcap's check y (new Peacekeepers past their SpecificUnitCap 2 at ~s150) on aiskcapo =
aiskcap with the AI yard carrying ra3ext's CNVOrders (missions/aiorders_bench.py). The bench asserts y's counters; the
orders (which path placed the overrun Peacekeeper) are read off the run folder's ra3ext.log after the run.
"""
from checks.engine_aiskirm import y

CHECKS = {'aiskcapo': {'y': y}, 'aiskcapy': {'y': y}}
