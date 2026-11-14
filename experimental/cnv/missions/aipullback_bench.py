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


CLOSE_AT = (-360.0, 0.0)               # airevp*: the far plant moved here off 'east base' -- 100 west of the tanks'
                                       # column (-260, -90..90): every tank 100-135 from its centre, well in range
TURRET = 'AlliedBaseDefense'           # airevt*: a hostile target -- the plant is only a tactical one (state 6), and
TURRET_NAME = 'UNIT - CNV AI Rev Turret'   # the reverse-move routine runs in states 2 and 4 only (work/re l4_micro_engage 1.4)
TURRET_AT = (-340.0, 0.0)              # 80-120 from the tanks
TURRET_PLANT_AT = (-480.0, 0.0)        # the plant behind it, out of the way
FOE = 'AlliedAntiVehicleVehicleTech1'  # airevk*: the player's Guardian tanks, a moving unit target (work/re/d131 1)
FOE_AT = ((-305.0, -60.0), (-305.0, 60.0))   # ~54 centre to centre from each of the column's tanks (-260, -90..90),
                                       # far inside the reverse gate d < R - 10 (cannon AttackRange 150: R 145)


def mission(mod, factory=False, faction=None, close=False, observe=False, **fields):
    """faction 'Soviet' / 'Japan': s1 that faction's player, its repair place that faction's VehicleRepairFacility
    (REPAIR) -- the pull-back looks the ArmyDefinition up by the player's faction (its Side; work/re handoff-b 71).
    close: no guards, and the team's target (the far plant) stands beside the tanks at the start (CLOSE_AT) -- the
    ReverseMove read (work/re/l4_micro_engage.md 1.4): a member 0 < d < range - 10 from its target backs off to range - 10.
    close='turret': a player's turret beside the tanks instead (TURRET_AT), the plant behind it.
    close='unit': two of the player's Guardian tanks beside the tanks (FOE_AT), the far plant where it was."""
    m = ac.mission(mod, observe=observe, Crush='false', **fields)
    if close:
        m.objects = [o for o in m.objects if not o.name.startswith('UNIT - CNV AI Guard')]
        m.cast = {k: r for k, r in m.cast.items() if not k.startswith('guard ')}
    if close == 'unit':
        m.spawns |= {FOE}
        for k, (dx, dy) in enumerate(FOE_AT):
            m.put(FOE, 'east base', dx, dy, angle=0.0, name=f'UNIT - CNV AI Rev Foe {k + 1}', role=f'rev foe {k + 1}')
    elif close:
        o = m.find(m.role('far plant').name)
        o.x, o.y = m.site('east base', *(TURRET_PLANT_AT if close == 'turret' else CLOSE_AT))[:2]
        if close == 'turret':
            m.put(TURRET, 'east base', *TURRET_AT, name=TURRET_NAME, role='rev turret')
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
    # the garrison routine's gates all pass statically (work/re handoff-b 69): hurt the tanks at the wake, ~1000 from any enemy
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
    # Identical passive carriers on both sides; body heading and goal object are
    # observations, while region counts alone cannot identify reverse travel.
    'airev1t': lambda: mission('CampAIRev1T', observe=True),
    'airev0t': lambda: mission('CampAIRev0T', observe=True, ReverseMove='false'),
    # airev1 / 0 too alike: the target beside the tanks from the start, no guards (handoff-b 69's measure)
    'airevp1': lambda: mission('CampAIRevP1', close=True),
    'airevp0': lambda: mission('CampAIRevP0', close=True, ReverseMove='false'),
    # airevp1 / 0 alike (no back-up): a plant is a tactical target, the team in state 6. A hostile turret instead, and
    # state 2 forced: CleanupPowerAdvantage out of reach (no state 3), UseGatherState off (no state 5)
    'airevt1': lambda: mission('CampAIRevT1', close='turret', CleanupPowerAdvantage='1000.0', UseGatherState='false'),
    'airevt0': lambda: mission('CampAIRevT0', close='turret', CleanupPowerAdvantage='1000.0', UseGatherState='false',
                               ReverseMove='false'),
    # D round 132 (work/re/d131_triggers.md 1): airevt's state 2 with a MOVING target of the player's, ~54 centre to
    # centre (a structure's radius kept the centre distance outside d < R - 10), the host observed (aim / dest / hd)
    'airevk1': lambda: mission('CampAIRevK1', close='unit', observe=True, CleanupPowerAdvantage='1000.0',
                               UseGatherState='false'),
    'airevk0': lambda: mission('CampAIRevK0', close='unit', observe=True, CleanupPowerAdvantage='1000.0',
                               UseGatherState='false', ReverseMove='false'),
    # the same with the AI's own Guardians (another weapon template: d131 1 gate 4, the weapon field not read)
    'airevkg1': lambda: guardians(mission('CampAIRevKG1', close='unit', observe=True,
                                          CleanupPowerAdvantage='1000.0', UseGatherState='false')),
}
