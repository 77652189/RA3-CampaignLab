"""w3x.rig_model: our units are click-selectable only through a W3DCollisionBox sub-object of the container (without
one they could be box-selected but not clicked, CampNew30 bench); the box must cover every part, pivots included."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'experimental' / 'campaign'))
import w3x  # noqa: E402

TRI = ([(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 1.0, 3.0)], [(0.0, 0.0, 1.0)] * 3, [(0.0, 0.0)] * 3, [(0, 1, 2)])


def test_container_has_collision_box_covering_all_parts():
    # hull on ROOTTRANSFORM, turret on a pivot 10 up, barrel on a pivot 5 forward of the turret
    text = w3x.rig_model('Probe', [('Turret', 0, (0.0, 0.0, 10.0)), ('Barrel', 1, (5.0, 0.0, 0.0))],
                         [('Hull', 0, TRI), ('Gun', 2, TRI)], ('Probe', 'Probe_NRM', 'Probe_SPM'))
    box = re.search(r'<W3DCollisionBox id="PROBE\.OBBOX01">\s*<Center X="([^"]+)" Y="([^"]+)" Z="([^"]+)"/>\s*'
                    r'<Extent X="([^"]+)" Y="([^"]+)" Z="([^"]+)"/>', text)
    assert box, 'no collision box'
    c, e = [float(v) for v in box.groups()[:3]], [float(v) for v in box.groups()[3:]]
    lo, hi = [a - b for a, b in zip(c, e)], [a + b for a, b in zip(c, e)]
    assert lo == [0.0, 0.0, 0.0] and hi == [7.0, 1.0, 13.0]     # gun: (5, 0, 10) + (2, 1, 3)
    container = text[text.index('<W3DContainer'):]
    assert '<CollisionBox>PROBE.OBBOX01</CollisionBox>' in container
