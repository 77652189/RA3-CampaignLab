"""Data and collision timing for topple props (engine_topple, bench 2026-11-09).

The SDK's ToppleUpdate defaults supply the angular velocity, acceleration and bounce. The angular fall / settling
rule follows the reference ToppleUpdate.cpp under work/downloads/cnc_generals_src; RA3's observed removal includes
SlowDeath.DestructionDelay, with no script-visible DYING. DynamicsDraw.Lifetime only controls the visual debris.
"""
import math
import re

import simunits

_rules, _shapes, _motion = {}, {}, {}


def _key(template, own):
    return template, (own or {}).get(template)


def rules(template, own=None):
    """None without ToppleUpdate, else its inherited kill flags, angular parameters and removal delay in frames."""
    key = _key(template, own)
    if key not in _rules:
        def read(xml):
            return next(simunits._blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'ToppleUpdate'), None)
        module = simunits._chain(template, own, read)
        if module is None:
            _rules[key] = None
        else:
            def attr(name, default):
                return simunits._chain(template, own, lambda xml: next(
                    (v for h, _ in simunits._blocks(xml or '', 'ToppleUpdate')
                     if (v := simunits._attr(h, name)) is not None), None)) or default
            _rules[key] = dict(start=attr('KillWhenStartToppled', 'false') == 'true',
                               finish=attr('KillWhenToppled', 'false') == 'true',
                               velocity=float(attr('InitialVelocityPercent', '20%').rstrip('%')) / 100,
                               accel=float(attr('InitialAccelPercent', '1%').rstrip('%')) / 100,
                               bounce=float(attr('BounceVelocityPercent', '20%').rstrip('%')) / 100,
                               minimum=float(attr('MinimumToppleSpeed', '0.5')),
                               delay=int(round(simunits.slow_death(template, own) * simunits.LIFE_FPS)))
    return _rules[key]


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


def fall_frames(speed, data):
    """Angular fall, then damped bounces until resting (reference source's 0.01 rad/frame stop threshold)."""
    if data['start']:
        return 0
    speed = max(speed, data['minimum'])
    velocity, accel = speed * data['velocity'], speed * data['accel']
    if velocity <= 0 and accel <= 0:
        return None                                 # no force to bring it down
    angle, limit = 0.0, math.pi / 2 - math.pi / 64
    for frame in range(1, 10001):
        angle += min(velocity, limit - angle)
        if angle >= limit and velocity > 0:
            velocity *= -data['bounce']
            if abs(velocity) < 0.01:
                return frame
        else:
            velocity += accel
    return None                                     # no settling, no removal


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
