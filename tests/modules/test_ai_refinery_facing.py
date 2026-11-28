"""node_facing: the AI sets a refinery down facing its nearest ore node, in 45-degree steps (the bench's six, B 11-27:
work/bench_results aiskirm / aiskin0c / aiskirmrc rpx, the team trail's tstate hd)."""
import math
from types import SimpleNamespace as NS

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.ai.core as simai  # noqa: E402

YARD = NS(template='AlliedConstructionYard', x=3850.0, y=3400.0)
EAST = [NS(template='OreNode', x=4173.0, y=2987.0), NS(template='OreNode', x=4279.0, y=3093.0)]


def test_a_refinery_faces_its_nearest_node_to_the_step():
    bodies = [YARD] + EAST
    got = [round(math.degrees(simai.node_facing(bodies, x, y))) for x, y in
           ((4362, 2829), (4426, 3253), (3875, 2786), (3938, 3126))]
    assert got == [135, -135, 45, -45]
    assert simai.node_facing([YARD], 4362, 2829) is None
