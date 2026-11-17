"""A round 274: the all-enemies action after s5 turns enemy at 5 s (missions/aiallflip_bench.py).

The same observation as C's engine_aiallbuild.a (four counters, 150 s watch); the readings that matter are the
ra3ext bpick / border lines (teamlog.build_picks / build_orders), compared at the same logical frames.
"""
from checks.engine_aiallbuild import a

CHECKS = {name: {'a': a} for name in ('aiallflipon', 'aiallflipoff', 'aiallfliplate', 'aiallflipnever',
                                                    'aiallflipwoff', 'aiallflipwon')}
