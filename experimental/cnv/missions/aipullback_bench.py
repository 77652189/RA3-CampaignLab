"""Engine probe: the skirmish AI team's PullbackInjured and ReverseMove (engine line B, layer 4; read back by
checks/engine_aipullback.py; model: an injured member (health ratio < PullbackInjuredHealthPct, MEDIUM 0.35) leaves the
team for the AI's nearest VehicleRepairFacility (ArmyDefAllied: AlliedWarFactory); a member whose distance d to its
target is 0 < d < longest range - 10 backs up to range - 10 from it, staying in the team).

aicrush_bench's aicrush0 (Crush false; 4 Hammers against 12 Peacekeepers round the far plant -- the tanks are shot at
and some get hurt) with:
  aipull1   an AlliedWarFactory of s1 beside the base yard; PullbackInjured true (default) -> the model: a hurt tank goes home
  aipull0   the same, PullbackInjured false -> they stay at the far plant
  airev1    no factory; ReverseMove true (default)
  airev0    no factory; ReverseMove false
Facts: wake at.
"""
from missions import aicrush_bench as ac

FACTORY = 'AlliedWarFactory'
FACTORY_NAME = 'UNIT - CNV AI War Factory'
FACTORY_AT = (0.0, 300.0)               # off the yard's east base site, clear of the yard and the tanks' way west


def mission(mod, factory=False, **fields):
    m = ac.mission(mod, Crush='false', **fields)
    if factory:
        m.put(FACTORY, 'east base', *FACTORY_AT, side='s1', name=FACTORY_NAME, role='ai factory')
    return m


GUARDIAN = 'AlliedAntiVehicleVehicleTech1'


def guardians(m):
    """The AI's Hammers swapped for Allied Guardian tanks (as aicrush_bench swaps Peacekeepers for Hammers)."""
    (fname, xml, asset), = m.assets
    m.assets = [(fname, xml.replace(f'<IncludeThing>{ac.TANK}</IncludeThing>',
                                    f'<IncludeThing>{GUARDIAN}</IncludeThing>'), asset)]
    for o in m.objects:
        if o.template == ac.TANK:
            o.template = GUARDIAN
    m.cast = {k: (r.__class__(GUARDIAN, r.name, r.side) if r.template == ac.TANK else r) for k, r in m.cast.items()}
    m.cnv_units = (m.cnv_units[0], GUARDIAN)
    m.spawns |= {GUARDIAN}
    return m


MISSION = {
    'aipull1': lambda: mission('CampAIPull1', factory=True),
    'aipull0': lambda: mission('CampAIPull0', factory=True, PullbackInjured='false'),
    # the first aipull1 run: no tank went home (a tank shot down from 35 % in under one 2 s micro update?) -- so the
    # check's script sets the tanks to HURT % at HURT_AT, on the road, before the fight (checks/engine_aipullback.py)
    'aipullh1': lambda: mission('CampAIPullH1', factory=True),
    'aipullh0': lambda: mission('CampAIPullH0', factory=True, PullbackInjured='false'),
    # aipullh1 too: no tank went home -- the same with the AI's own faction's tank (an Allied AI, Soviet Hammers)
    'aipullga': lambda: guardians(mission('CampAIPullGa', factory=True)),
    'airev1': lambda: mission('CampAIRev1'),
    'airev0': lambda: mission('CampAIRev0', ReverseMove='false'),
}
