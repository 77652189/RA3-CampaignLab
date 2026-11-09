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
REPAIR = {'Soviet': 'SovietCrane', 'Japan': 'JapanWarFactory'}   # ArmyDef*.xml VehicleRepairFacility
FACTORY_AT = (0.0, 300.0)              # off the yard's east base site, clear of the yard and the tanks' way west


def mission(mod, factory=False, faction=None, **fields):
    """faction 'Soviet' / 'Japan': s1 that faction's player, its repair place that faction's VehicleRepairFacility
    (REPAIR) -- the pull-back looks the ArmyDefinition up by the player's faction (its Side; work/re handoff-b 71)."""
    m = ac.mission(mod, Crush='false', **fields)
    if faction:
        m.sides['s1'] = dict(m.sides['s1'], playerFaction=f'PlayerTemplate:{faction}')
    if factory:
        m.put(REPAIR.get(faction, FACTORY), 'east base', *FACTORY_AT, side='s1', name=FACTORY_NAME, role='ai factory')
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
    # 0x8df430's gates all pass statically (work/re handoff-b 69): hurt the tanks at the wake, ~1000 from any enemy
    # (no AlphaStrike state 0), with a health counter (did UNIT_SET_HEALTH take?); aipullr1 also turns the AI's
    # repair switch on (aitarget_bench's wake sets SKIRMISH_AI_USE_REPAIRS 0)
    'aipulli1': lambda: mission('CampAIPullI1', factory=True),
    'aipullr1': lambda: mission('CampAIPullR1', factory=True),
    # aipulli1 / r1 no tank went home: hurt BEFORE the wake (the tanks idle ~400 from the factory) and count 近家
    # (within 600) for 到远厂 -- a tank sent home then recruited again would linger near home
    'aipullp1': lambda: mission('CampAIPullP1', factory=True),
    # aipullp1 none either (they join the team at 30 % and drive off): is Body slot 0x40 a 0..1 ratio? any health
    # passes a PullbackInjuredHealthPct this big
    'aipullbig': lambda: mission('CampAIPullBig', factory=True, PullbackInjuredHealthPct='100000.0'),
    # aipulli1 with a Soviet AI and a SovietCrane: the lookup is by faction (s1 Allied -> AlliedArmy, AlliedWarFactory,
    # as the probe has it) -- does another faction / facility draw them home?
    'aipullsov': lambda: mission('CampAIPullSov', factory=True, faction='Soviet'),
    'aipulljp': lambda: mission('CampAIPullJp', factory=True, faction='Japan'),
    'airev1': lambda: mission('CampAIRev1'),
    'airev0': lambda: mission('CampAIRev0', ReverseMove='false'),
}
