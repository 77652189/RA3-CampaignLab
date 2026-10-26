"""Router probe: what the engine does after a jump without PREP whose router has no pair for it (bench 2026-10-26,
CampMusDynT: Combat took a4's prep, whose router knows only escort, to fierce; fierce played one segment and went
on to final, with no event, past its own transition). Tracers: each segment its own stream (SECTIONS order).

  P1   router 1: [(T_P1E, E)]                   lacks F and G
  P2   router 2: [(T_P2F, F)]                   has F
  F    router 3: [(T_FE, E), (T_FX, X), (T_FY, Y)]
  G    router 4: [(T_GY, Y), (T_GE, E), (T_GX, X)]   F's targets in another order
  E X Y          loops, no router

SCHEDULE fires, at known mission seconds: cuts (PREP) to P1 / P2 and plain jumps to F / G from them. Expected if a
pending jump ends once taken: F (or G) then loops on itself. Facts: '<event key> <n>' = seconds.
"""
import os
import sys

from maps import island
from parts import Mission, Script

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from experimental.music import ownmap, pack  # noqa: E402

SEG_MS, T_MS = 4000, 1500
LOOPS = ['P1', 'P2', 'F', 'G', 'E', 'X', 'Y']           # two segments each
ROUTES = {'P1': [('E', 'T_P1E')], 'P2': [('F', 'T_P2F')],
          'F': [('E', 'T_FE'), ('X', 'T_FX'), ('Y', 'T_FY')], 'G': [('Y', 'T_GY'), ('E', 'T_GE'), ('X', 'T_GX')]}
EVENTS = {'P1': ('S_A01BrightonThreat', True), 'P2': ('S_A02CannesBegin', True),
          'F': ('S_A01BrightonCombat', False), 'G': ('S_A01BrightonExplore', False)}
SCHEDULE = [(2.0, 'P1'), (10.3, 'F'), (42.0, 'P2'), (50.3, 'F'), (82.0, 'P1'), (90.3, 'G'), (122.0, 'P2'),
            (130.3, 'G')]


def streams():
    """[(section, ms)] in stream order: two segments per loop, then one per transition."""
    out = [(s, SEG_MS) for s in LOOPS for _ in range(2)]
    return out + [(t, T_MS) for routes in ROUTES.values() for _, t in routes]


def music_map(base):
    b = ownmap.Builder(base)
    secs, k = {}, 0
    route_of = {s: i + 1 for i, s in enumerate(ROUTES)}
    for s in LOOPS:
        secs[s] = b.section([k, k + 1], router=route_of.get(s, 0))
        b.loop(secs[s])
        k += 2
    for routes in ROUTES.values():
        for target, t in routes:
            secs[t] = b.section([k])
            k += 1
    for routes in ROUTES.values():
        for target, t in routes:
            b.link(secs[t], secs[target])
    b.m.routers = [[(secs[t].entry, secs[target].entry) for target, t in routes] for routes in ROUTES.values()]
    for key, (event, prep) in EVENTS.items():
        b.on(event, secs[key], prep=prep)
    for shell in ('MenuTrack', 'BriefingTrack'):
        b.on(shell, secs['E'], prep=True)
    return b, [ms for _, ms in streams()]


def _pack():
    from experimental.music import extract
    b, lengths = music_map(extract.retail_map())
    return pack.make(b.m, pack.tracer_tracks(b.m, lengths))


def facts():
    seen, out = {}, {}
    for t, key in SCHEDULE:
        seen[key] = seen.get(key, 0) + 1
        out[f'{key} {seen[key]}'] = t
    return out


def mission(name='CampMusRoute'):
    m = Mission(name=name, map=island, facts=facts(), music=pack.Later(_pack, {e for e, _ in EVENTS.values()}))
    m.put('AlliedAntiVehicleVehicleTech1', 'west field', 0, 0, name='UNIT - CNV Music Route Guardian', role='listener')
    m.scripts.append(Script('CNV Music Route - Start', [], [('SET_MILLISECOND_TIMER', f'CNV Music Route {k}', t)
                                                            for k, (t, _) in enumerate(SCHEDULE)]))
    m.scripts += [Script(f'CNV Music Route - {k} {key}', [('TIMER_EXPIRED', f'CNV Music Route {k}')],
                         [('PATH_MUSIC_PLAY_EVENT', EVENTS[key][0])]) for k, (_, key) in enumerate(SCHEDULE)]
    return m
