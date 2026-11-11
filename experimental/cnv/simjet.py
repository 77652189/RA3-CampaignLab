"""E53/D43: measured Vindicator eastbound startup, not the full JetAI state machine.

The first horizontal step 2.7 is INFERRED (measured, mechanism unknown). The
remaining steps use NORMAL Speed and AccelerationSeconds. Turning, other jets,
runways, parking, ammo, altitude and idle circling remain outside this slice.
"""
import math

import simunits


def is_jet(template, own):
    return simunits._chain(template, own, lambda x: True if '<JetAIUpdate' in (x or '') else None)


def start(e, b, path):
    """Gate the measured configuration and first straight eastbound plain order."""
    if not is_jet(b.template, e.own):
        return None
    import simtopple
    speed, acceleration = simtopple.motion(b.template, e.own)
    measured = (b.template == 'AlliedAntiGroundAircraft' and not e.own.get(b.template)
                and speed == 180 and acceleration == 1 and b.speed == speed
                and b.mode == 'move' and not b.path and not b.jet_started
                and math.isclose(b.angle % (2 * math.pi), 0, abs_tol=1e-9)
                and len(path) == 1 and path[0][0] > b.x
                and math.isclose(path[0][1], b.y, abs_tol=1e-9) and e.eng is not None)
    b.jet_started = True
    if not measured:
        e.gap('jet movement', b.template,
              'Only the first stationary retail Vindicator eastbound plain move is measured; '
              'turning, repeated orders, modified configuration and other JetAI states are unmodeled')
        return None
    e.gap('JetAIUpdate', b.template,
          'Measured horizontal startup only; altitude, idle circling, airfields, ammo and attack states are unmodeled')
    return dict(step=None, speed=speed, acceleration=acceleration)


def distance(e, b):
    """One 15 Hz frame; no endpoint-specific correction."""
    fps = simunits.LIFE_FPS
    state = b.jet_motion
    if b.speed != state['speed'] or b.mode != 'move' or state.get('unsupported'):
        state['unsupported'] = True
        e.gap('jet movement', b.template, 'Mid-flight speed or order change is unmeasured; using coarse speed fallback')
        return b.speed / fps
    cap = state['speed'] / fps
    step = (2.7 if state['step'] is None else
            min(cap, state['step'] + cap / (state['acceleration'] * fps)))
    state['step'] = step
    return step
