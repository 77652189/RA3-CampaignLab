"""Passive search radius contrast; raw team states distinguish selection from damage.

The side plant is 250 west of the route, outside the Peacekeepers' weapon range.
EngageTacticalTarget is disabled; the named far plant only drives the tactic's
movement. INFERRED predictions: 0 disables passive selection, 200 misses the
side plant and 600 permits it. Zero semantics and distance origin are unproven.
See work/re/e104_passive_distance.md for predictions and same-run evidence.

MEASURED: 0/1/200/600 all select the side plant at logic frame 140, with
four members, state 6; state 0 begins at 320. This route does not expose a
consumer of the field. The predicted distance contrast was rejected; do not
infer a global no-op or add a cutoff to the model from the field's name.
"""
from missions import airetreat_bench as ar
from missions.aiteams_bench import host_unit, HOST


def mission(name, distance):
    m = ar.mission(name, side=True, PassiveTargetSearchDistance=str(distance),
                   EngagePassiveTargets='true', EngageTacticalTarget='false',
                   UseSpecialPowers='false', DodgeThreats='false',
                   PullbackInjured='false', EnterGarrisons='false',
                   EnterBaseDefenses='false', ReverseMove='false')
    m.units.append(host_unit())
    m.put(HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
    m.ext = True
    m.facts['passive search distance'] = distance
    return m


MISSION = {
    'aipsdz': lambda: mission('CampPasZero', 0),
    'aipsdt': lambda: mission('CampPasTiny', 1),
    'aipsds': lambda: mission('CampPasSmall', 200),
    'aipsdl': lambda: mission('CampPasLarge', 600),
}
