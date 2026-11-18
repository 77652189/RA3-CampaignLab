"""Collision timing for topple props (engine_topple, bench 2026-11-09): their footprints, the swept boxes a crusher
drives into them by and the knocker's speed. The rules, the fall and the removal are the ToppleUpdate module's
(engine/modules/topple.py, step M2).

The SDK's ToppleUpdate defaults supply the angular velocity, acceleration and bounce. The angular fall / settling
rule follows the reference ToppleUpdate.cpp under work/downloads/cnc_generals_src; RA3's observed removal includes
SlowDeath.DestructionDelay, with no script-visible DYING. DynamicsDraw.Lifetime only controls the visual debris.
"""
import math
import re

import simunits

_shapes, _motion = {}, {}


def _key(template, own):
    return template, (own or {}).get(template)


def shape(template, own=None):
    """First Geometry Shape's half sides and local offset; inherited (CS_Tree01's box is in BaseTree)."""
    key = _key(template, own)
    if key not in _shapes:
        def read(xml):
            geometry = next(simunits._blocks(xml or '', 'Geometry'), None)
            if geometry is None:
                return None
            h, inner = next(simunits._blocks(geometry[1], 'Shape'), ('', ''))
            def num(text, name):
                m = re.search(rf'\b{name}\s*=\s*"([\d.eE+-]+)"', text)
                return float(m[1]) if m else 0.0
            major = num(h, 'MajorRadius')
            minor = num(h, 'MinorRadius') if re.search(r'Type\s*=\s*"BOX"', h) else major
            offset = next(simunits._blocks(inner, 'Offset'), ('', ''))[0]
            return major, minor, num(offset, 'x'), num(offset, 'y')
        _shapes[key] = simunits._chain(template, own, read) or (0.0, 0.0, 0.0, 0.0)
    return _shapes[key]


def crosses(b, o, start, end, own):
    """Swept oriented boxes: whether this straight movement touches a prop, including both footprints and offsets."""
    def box(body, angle):
        a, c, x, y = shape(body.template, own)
        co, si = math.cos(angle), math.sin(angle)
        return a, c, (co, si), (-si, co), (co * x - si * y, si * x + co * y)
    dx, dy = end[0] - start[0], end[1] - start[1]
    a, c, u, v, off = box(b, math.atan2(dy, dx) if dx or dy else b.angle)
    oa, oc, ou, ov, oo = box(o, o.angle)
    rx, ry = start[0] + off[0] - o.x - oo[0], start[1] + off[1] - o.y - oo[1]
    lo, hi = 0.0, 1.0
    for nx, ny in (u, v, ou, ov):
        extent = sum(h * abs(nx * ax + ny * ay) for h, (ax, ay) in ((a, u), (c, v), (oa, ou), (oc, ov)))
        distance, travel = nx * rx + ny * ry, nx * dx + ny * dy
        if abs(travel) < 1e-9:
            if abs(distance) > extent:
                return False
        else:
            t0, t1 = sorted(((-extent - distance) / travel, (extent - distance) / travel))
            lo, hi = max(lo, t0), min(hi, t1)
            if lo > hi:
                return False
    return True


def motion(template, own=None):
    """NORMAL speed (including CampaignOverrides) and acceleration seconds for frame-resolved prop collisions."""
    key = _key(template, own)
    if key not in _motion:
        def read(xml):
            for h, _ in simunits._blocks(xml or '', 'LocomotorSet'):
                if simunits._attr(h, 'Condition', 'NORMAL') == 'NORMAL' and simunits._attr(h, 'Speed') is not None:
                    return float(simunits._attr(h, 'Speed')), simunits._attr(h, 'Locomotor')
            return None
        speed, locomotor = simunits._chain(template, own, read) or (None, None)
        text = open(simunits.LOCOMOTORS, encoding='utf-8').read()
        h = next((h for h, _ in simunits._blocks(text, 'LocomotorTemplate') if simunits._attr(h, 'id') == locomotor), '')
        _motion[key] = speed, simunits._secs(simunits._attr(h, 'AccelerationSeconds'))
    return _motion[key]
