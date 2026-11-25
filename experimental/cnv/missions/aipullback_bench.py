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
BEAR = 'SovietScoutInfantry'           # airevb*: war bears, they bite infantry only (no hostile can fire at a tank)
BEAR_AT = ((-200.0, 320.0), (-320.0, 320.0))   # north of the column (-260, -90..90), 230+ off its nearest tank


def mission(mod, factory=False, faction=None, close=False, observe=False, **fields):
    """faction 'Soviet' / 'Japan': s1 that faction's player, its repair place that faction's VehicleRepairFacility
    (REPAIR) -- the pull-back looks the ArmyDefinition up by the player's faction (its Side; work/re handoff-b 71).
    close: no guards, and the team's target (the far plant) stands beside the tanks at the start (CLOSE_AT) -- the
    ReverseMove read (work/re/l4_micro_engage.md 1.4): a member 0 < d < range - 10 from its target backs off to range - 10.
    close='turret': a player's turret beside the tanks instead (TURRET_AT), the plant behind it.
    close='unit': two of the player's Guardian tanks beside the tanks (FOE_AT), the far plant where it was.
    close='bear': two of the player's war bears off the tanks' way (BEAR_AT), the far plant where it was."""
    m = ac.mission(mod, observe=observe, Crush='false', **fields)
    if close:
        m.objects = [o for o in m.objects if not o.name.startswith('UNIT - CNV AI Guard')]
        m.cast = {k: r for k, r in m.cast.items() if not k.startswith('guard ')}
    if close in ('unit', 'bear'):
        foe, at = (FOE, FOE_AT) if close == 'unit' else (BEAR, BEAR_AT)
        m.spawns |= {foe}
        for k, (dx, dy) in enumerate(at):
            m.put(foe, 'east base', dx, dy, angle=0.0, name=f'UNIT - CNV AI Rev Foe {k + 1}', role=f'rev foe {k + 1}')
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


def guardians(m, tank=GUARDIAN, angle=None):
    """The AI's Hammers swapped for Allied Guardian tanks (as aicrush_bench swaps Peacekeepers for Hammers), or for
    `tank`; angle (radians): the tanks' starting facing instead of west."""
    (fname, xml, asset), = m.assets
    m.assets = [(fname, xml.replace(f'<IncludeThing>{ac.TANK}</IncludeThing>',
                                    f'<IncludeThing>{tank}</IncludeThing>'), asset)]
    for o in m.objects:
        if o.template == ac.TANK:
            o.template = tank
            if angle is not None:
                o.angle = angle
    m.cast = {k: (r.__class__(tank, r.name, r.side) if r.template == ac.TANK else r) for k, r in m.cast.items()}
    m.cnv_units = (m.cnv_units[0], tank)
    m.spawns |= {tank}
    return m


APOCALYPSE = 'SovietAntiVehicleVehicleTech3'
CONSCRIPT = 'SovietAntiInfantryInfantry'


SECOND = 's6'                          # airevidx: a second AI side, a player index of its own (s1 logs index=4)
SECOND_AT = (450.0, -500.0)            # its yard off 'east base' (4300, 2900), its four tanks 260 west of it


def second_ai(m, side=SECOND, at=SECOND_AT):
    """B round 196 (handoff-b 195 C3): a second AI side with s1's faction and personality, its yard, four tanks and a
    teams host laid out as s1's are (`at` off 'east base'), woken with s1 -- do the slot team's first draw (s1 f16) and
    its fill (s1 f21 = draw + 5) move with the player index?"""
    from parts import Script
    from missions.aiteams_bench import HOST
    m.sides[side] = dict(m.sides['s1'])
    ox, oy = at
    k = 0
    for o in list(m.objects):
        if o.side != 's1':
            continue
        dx, dy = o.x - 3850.0, o.y - 3400.0           # off 'east base', as mission() placed them
        k += 1
        kw = {} if getattr(o, 'angle', None) is None else {'angle': o.angle}
        m.put(o.template, 'east base', ox + dx, oy + dy, side=side, name=f'UNIT - CNV AI2 {k}' if o.name else '',
              role=f'second ai {k}' if o.name else '', **kw)
    p = m.player(side)
    base = 'CNV AI Base 2'
    m.waypoint('ai base 2', base, 'east base', ox, oy)
    m.scripts += [
        # run 1 (B196): s6's units stayed in the map's teamSoviet_6 (s1's are in defaultSkirmishTeamSoviet_1 from f1),
        # so nothing was recruited before the wake's transfer (f151 -> full f152): hand them over at the start
        Script('CNV AI2 - Start', [], [('PLAYER_SET_MONEY', p, 0), ('UNIT_AI_TRANSFER_ALL', p, 1)]),
        Script('CNV AI2 - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
               [('UNIT_AI_TRANSFER_ALL', p, 1), ('SKIRMISH_AI_MAKE_BASE', p, base),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', p, 20), ('SKIRMISH_AI_USE_REPAIRS', p, 0),
                ('SKIRMISH_AI_USE_REBUILD_SYSTEM', p, 0), ('PLAYER_SET_MONEY', p, 0)])]
    assert any(o.template == HOST and o.side == side for o in m.objects)
    return m


MISSION = {
    'aipull1':lambda: mission('CampAIPull1', factory=True),
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
    # B round 196: airev1t with a second AI side (s6, its own index) laid out the same -- the recruit delay by index
    'airevidx': lambda: second_ai(mission('CampAIRevIdx', observe=True)),
    # A round 227: airev1t's form-up with another locomotor -- the turn in place (Hammer TurnTimeSeconds 1.25 s:
    # 19 deg / frame on the bench). Guardians (1.0 s) start facing north-west, so the go order turns them < 90 deg
    # (TurnThresholdHS 90: do they drive while turning?); Apocalypses (3 s) as airev1t, facing west
    'airevgt': lambda: guardians(mission('CampAIRevGT', observe=True), angle=-2.3562),
    'airevat': lambda: guardians(mission('CampAIRevAT', observe=True), tank=APOCALYPSE),
    # A round 231: airev1t's form-up with infantry -- Conscripts (TestReactiveLocomotorHUMAN, TurnTimeSeconds 0.5 s,
    # no TurnThresholdHS; Peacekeepers and every engineer walk on it too), facing west as airev1t (the form-up turn
    # ~150 deg): do they turn in place before they walk, as the tanks do, and at 48 deg a frame?
    'airevit': lambda: guardians(mission('CampAIRevIT', observe=True), tank=CONSCRIPT),
    # airev1 / 0 too alike: the target beside the tanks from the start, no guards (handoff-b 69's measure)
    'airevp1': lambda: mission('CampAIRevP1', close=True),
    'airevp0': lambda: mission('CampAIRevP0', close=True, ReverseMove='false'),
    # B 11-23: airevp1 observed (the host: ra3ext alone logs no cmd: lines here): the simulator's AI casts its
    # precision strike f166 at the plant, counting its own four Hammers 100 off -- does the game (24e / 1fe / 1ff)?
    'airevp1t': lambda: mission('CampAIRevP1T', close=True, observe=True),
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
    # D round 182: airevk1 with the two foes' health % read before the frame's keep (how the near foe dies s13)
    'airevkh': lambda: mission('CampAIRevKH', close='unit', observe=True, CleanupPowerAdvantage='1000.0',
                               UseGatherState='false'),
    # the same with the AI's own Guardians (another weapon template: d131 1 gate 4, the weapon field not read)
    'airevkg1': lambda: guardians(mission('CampAIRevKG1', close='unit', observe=True,
                                          CleanupPowerAdvantage='1000.0', UseGatherState='false')),
    # D round 133: airevk1's start (the team forms f213, state 2 f242 with aim = a far foe 166+ off), then at LATE_AT
    # the check deletes the two foes and spawns one of the player's Guardians on each Hammer (checks/engine_aipullback
    # LATE_*): every member's nearest -- and only -- foe a few tens off, far inside d < R - 10 = 135
    'airevk2': lambda: mission('CampAIRevK2', close='unit', observe=True, CleanupPowerAdvantage='1000.0',
                               UseGatherState='false'),
    'airevk2o': lambda: mission('CampAIRevK2Off', close='unit', observe=True, CleanupPowerAdvantage='1000.0',
                                UseGatherState='false', ReverseMove='false'),
    # D round 135b ("注入摆"): airevk1 / 0 as they are (nothing deleted or spawned), plus the host's CNVCmd; the check's
    # plan moves the two foes beside the two team members at f250 (checks/engine_aipullback POKE_*)
    'airevkp1': lambda: mission('CampAIRevKP1', close='unit', observe='cmd', CleanupPowerAdvantage='1000.0',
                                UseGatherState='false'),
    'airevkp0': lambda: mission('CampAIRevKP0', close='unit', observe='cmd', CleanupPowerAdvantage='1000.0',
                                UseGatherState='false', ReverseMove='false'),
    # B 11-24 SiegeWeaponBuffer (work/re l4_micro_retreat.md 1.1): airev1t with two war bears for the guards, off the
    # tanks' way -- 1.5 x a bear's reach is under the Hammer's 150: state 4, each tank attacks the nearest bear;
    # at 1000 no siege, UseGatherState on: state 5
    'airevb1': lambda: mission('CampAIRevB1', close='bear', observe=True, CleanupPowerAdvantage='1000.0'),
    'airevb0': lambda: mission('CampAIRevB0', close='bear', observe=True, CleanupPowerAdvantage='1000.0',
                               SiegeWeaponBuffer='1000.0'),
}
